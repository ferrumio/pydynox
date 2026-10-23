//! Request building for batch get. Pure, so it can be tested without Python.

use aws_sdk_dynamodb::error::BuildError;
use aws_sdk_dynamodb::types::{AttributeValue, KeysAndAttributes};
use std::collections::HashMap;

/// Build the `KeysAndAttributes` for one request (first attempt or retry).
pub(super) fn build_keys_and_attributes(
    keys: Vec<HashMap<String, AttributeValue>>,
    consistent_read: bool,
    projection_expression: Option<&str>,
    expression_attribute_names: Option<&HashMap<String, String>>,
) -> Result<KeysAndAttributes, BuildError> {
    let mut builder = KeysAndAttributes::builder().set_keys(Some(keys));
    if consistent_read {
        builder = builder.consistent_read(true);
    }
    if let Some(projection) = projection_expression {
        builder = builder.projection_expression(projection);
    }
    if let Some(names) = expression_attribute_names {
        for (placeholder, attr_name) in names {
            builder = builder.expression_attribute_names(placeholder, attr_name);
        }
    }
    builder.build()
}
