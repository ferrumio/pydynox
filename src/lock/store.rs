//! AWS requests and the adapter for the existing testing backend.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use aws_sdk_dynamodb::Client;
use aws_sdk_dynamodb::error::{ProvideErrorMetadata, SdkError};
use aws_sdk_dynamodb::types::{AttributeValue, ReturnConsumedCapacity};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::errors::{ConditionalCheckFailedException, map_sdk_error};

type Item = HashMap<String, AttributeValue>;

#[derive(Clone, Debug)]
pub(super) struct Row {
    pub owner: String,
    pub version: String,
    pub lease: Duration,
}

impl Row {
    fn item(&self, key: &str) -> Item {
        HashMap::from([
            ("key".into(), AttributeValue::S(key.into())),
            ("owner".into(), AttributeValue::S(self.owner.clone())),
            ("version".into(), AttributeValue::S(self.version.clone())),
            (
                "lease_ms".into(),
                AttributeValue::N(self.lease.as_millis().to_string()),
            ),
            ("protocol".into(), AttributeValue::N("1".into())),
        ])
    }

    fn parse(item: Item) -> PyResult<Self> {
        let invalid = || PyValueError::new_err("Invalid or unsupported distributed lock record");
        let string = |name: &str| -> PyResult<String> {
            match item.get(name) {
                Some(AttributeValue::S(value)) if !value.is_empty() => Ok(value.clone()),
                _ => Err(invalid()),
            }
        };
        if item.get("protocol") != Some(&AttributeValue::N("1".into())) {
            return Err(invalid());
        }
        let millis = match item.get("lease_ms") {
            Some(AttributeValue::N(value)) => value.parse::<u64>().map_err(|_| invalid())?,
            _ => return Err(invalid()),
        };
        if !(100..=86_400_000).contains(&millis) {
            return Err(invalid());
        }
        Ok(Self {
            owner: string("owner")?,
            version: string("version")?,
            lease: Duration::from_millis(millis),
        })
    }
}

#[derive(Debug)]
pub(super) enum Failure {
    Contended,
    Error(PyErr),
}

impl From<PyErr> for Failure {
    fn from(error: PyErr) -> Self {
        Self::Error(error)
    }
}

fn aws_error<E, R>(error: SdkError<E, R>, table: &str) -> Failure
where
    E: ProvideErrorMetadata + std::fmt::Debug + std::fmt::Display,
    R: std::fmt::Debug,
{
    if error
        .as_service_error()
        .is_some_and(|error| error.code() == Some("ConditionalCheckFailedException"))
    {
        Failure::Contended
    } else {
        Failure::Error(map_sdk_error(error, Some(table)))
    }
}

#[derive(Clone)]
pub(super) enum Store {
    Aws(Client),
    // MemoryBackend is a testing adapter, never used by the production client.
    Memory(Arc<Py<PyAny>>),
}

fn key_item(key: &str) -> Item {
    HashMap::from([("key".into(), AttributeValue::S(key.into()))])
}

fn expected_values(owner: &str, version: Option<&str>) -> Item {
    let mut values = HashMap::from([(":owner".into(), AttributeValue::S(owner.into()))]);
    if let Some(version) = version {
        values.insert(":version".into(), AttributeValue::S(version.into()));
    }
    values
}

impl Store {
    pub async fn get(&self, table: &str, key: &str) -> Result<(Option<Row>, f64), Failure> {
        match self {
            Self::Aws(client) => {
                let response = client
                    .get_item()
                    .table_name(table)
                    .set_key(Some(key_item(key)))
                    .consistent_read(true)
                    .return_consumed_capacity(ReturnConsumedCapacity::Total)
                    .send()
                    .await
                    .map_err(|error| aws_error(error, table))?;
                let capacity = response
                    .consumed_capacity()
                    .and_then(|capacity| capacity.capacity_units())
                    .unwrap_or_default();
                Ok((response.item.map(Row::parse).transpose()?, capacity))
            }
            Self::Memory(client) => Python::attach(|py| {
                let result = client.bind(py).call_method1("_lock_get", (table, key))?;
                if result.is_none() {
                    return Ok((None, 0.0));
                }
                let item = crate::conversions::py_dict_to_attribute_values(
                    py,
                    result.cast::<PyDict>().map_err(PyErr::from)?,
                )?;
                Ok((Some(Row::parse(item)?), 0.0))
            }),
        }
    }

    pub async fn put(
        &self,
        table: &str,
        key: &str,
        row: &Row,
        expected: Option<&Row>,
    ) -> Result<f64, Failure> {
        let (condition, names, values) = match expected {
            None => (
                "attribute_not_exists(#key)",
                HashMap::from([("#key".into(), "key".into())]),
                None,
            ),
            Some(old) => (
                "#owner = :owner AND #version = :version",
                HashMap::from([
                    ("#owner".into(), "owner".into()),
                    ("#version".into(), "version".into()),
                ]),
                Some(expected_values(&old.owner, Some(&old.version))),
            ),
        };
        match self {
            Self::Aws(client) => {
                let response = client
                    .put_item()
                    .table_name(table)
                    .set_item(Some(row.item(key)))
                    .condition_expression(condition)
                    .set_expression_attribute_names(Some(names))
                    .set_expression_attribute_values(values)
                    .return_consumed_capacity(ReturnConsumedCapacity::Total)
                    .send()
                    .await
                    .map_err(|error| aws_error(error, table))?;
                Ok(response
                    .consumed_capacity()
                    .and_then(|capacity| capacity.capacity_units())
                    .unwrap_or_default())
            }
            Self::Memory(client) => Python::attach(|py| {
                let item = crate::conversions::attribute_values_to_py_dict(py, row.item(key))?;
                client
                    .bind(py)
                    .call_method1(
                        "_lock_put",
                        (
                            table,
                            item,
                            expected.map(|old| old.owner.as_str()),
                            expected.map(|old| old.version.as_str()),
                        ),
                    )
                    .map(|_| 0.0)
                    .map_err(|error| memory_error(py, error))
            }),
        }
    }

    pub async fn renew(
        &self,
        table: &str,
        key: &str,
        old: &Row,
        new: &Row,
    ) -> Result<f64, Failure> {
        match self {
            Self::Aws(client) => {
                let mut values = expected_values(&old.owner, Some(&old.version));
                values.insert(":new".into(), AttributeValue::S(new.version.clone()));
                let response = client
                    .update_item()
                    .table_name(table)
                    .set_key(Some(key_item(key)))
                    .update_expression("SET #version = :new")
                    .condition_expression("#owner = :owner AND #version = :version")
                    .expression_attribute_names("#owner", "owner")
                    .expression_attribute_names("#version", "version")
                    .set_expression_attribute_values(Some(values))
                    .return_consumed_capacity(ReturnConsumedCapacity::Total)
                    .send()
                    .await
                    .map_err(|error| aws_error(error, table))?;
                Ok(response
                    .consumed_capacity()
                    .and_then(|capacity| capacity.capacity_units())
                    .unwrap_or_default())
            }
            Self::Memory(_) => self.put(table, key, new, Some(old)).await,
        }
    }

    pub async fn delete(&self, table: &str, key: &str, owner: &str) -> Result<f64, Failure> {
        match self {
            Self::Aws(client) => {
                let response = client
                    .delete_item()
                    .table_name(table)
                    .set_key(Some(key_item(key)))
                    .condition_expression("#owner = :owner")
                    .expression_attribute_names("#owner", "owner")
                    .set_expression_attribute_values(Some(expected_values(owner, None)))
                    .return_consumed_capacity(ReturnConsumedCapacity::Total)
                    .send()
                    .await
                    .map_err(|error| aws_error(error, table))?;
                Ok(response
                    .consumed_capacity()
                    .and_then(|capacity| capacity.capacity_units())
                    .unwrap_or_default())
            }
            Self::Memory(client) => Python::attach(|py| {
                client
                    .bind(py)
                    .call_method1("_lock_delete", (table, key, owner))
                    .map(|_| 0.0)
                    .map_err(|error| memory_error(py, error))
            }),
        }
    }
}

fn memory_error(py: Python<'_>, error: PyErr) -> Failure {
    if error.is_instance_of::<ConditionalCheckFailedException>(py) {
        Failure::Contended
    } else {
        Failure::Error(error)
    }
}
