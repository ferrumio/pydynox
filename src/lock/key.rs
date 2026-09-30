//! Compile templates once; bind arguments and build each resource key in Rust.

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyTuple};

use super::{duration, validate_key};

struct Parameter {
    name: String,
    kind: u8,
    default: Option<Py<PyAny>>,
}

enum Part {
    Literal(String),
    Parameter(usize),
}

#[pyclass]
pub struct LockKeyTemplate {
    parameters: Vec<Parameter>,
    parts: Vec<Part>,
    frame_values: bool,
}

#[pymethods]
impl LockKeyTemplate {
    #[new]
    fn new(
        template: &str,
        parameters: Vec<(String, u8, bool, Py<PyAny>)>,
        lease_duration: f64,
        wait_timeout: f64,
    ) -> PyResult<Self> {
        duration(lease_duration, "lease_duration", false)?;
        duration(wait_timeout, "wait_timeout", true)?;
        let parameters: Vec<Parameter> = parameters
            .into_iter()
            .map(|(name, kind, has_default, default)| Parameter {
                name,
                kind,
                default: has_default.then_some(default),
            })
            .collect();
        let mut chars = template.chars().peekable();
        let mut literal = String::new();
        let mut parts = Vec::new();
        while let Some(ch) = chars.next() {
            match ch {
                '{' if chars.peek() == Some(&'{') => {
                    chars.next();
                    literal.push('{');
                }
                '}' if chars.peek() == Some(&'}') => {
                    chars.next();
                    literal.push('}');
                }
                '{' => {
                    parts.push(Part::Literal(std::mem::take(&mut literal)));
                    let mut name = String::new();
                    let mut closed = false;
                    for next in chars.by_ref() {
                        if next == '}' {
                            closed = true;
                            break;
                        }
                        name.push(next);
                    }
                    if !closed {
                        return Err(PyValueError::new_err("Unclosed lock key placeholder"));
                    }
                    let index = parameters
                        .iter()
                        .position(|parameter| {
                            parameter.name == name && matches!(parameter.kind, 0 | 1 | 3)
                        })
                        .ok_or_else(|| {
                            PyValueError::new_err(format!(
                                "Lock key placeholder '{name}' must name a regular function argument"
                            ))
                        })?;
                    parts.push(Part::Parameter(index));
                }
                '}' => return Err(PyValueError::new_err("Unmatched '}' in lock key")),
                other => literal.push(other),
            }
        }
        parts.push(Part::Literal(literal));
        if !parts.iter().any(|part| matches!(part, Part::Parameter(_))) {
            let key: String = parts
                .iter()
                .filter_map(|part| match part {
                    Part::Literal(value) => Some(value.as_str()),
                    _ => None,
                })
                .collect();
            validate_key(&key)?;
        }
        let frame_values = parts
            .iter()
            .filter(|part| matches!(part, Part::Parameter(_)))
            .count()
            > 1;
        Ok(Self {
            parameters,
            parts,
            frame_values,
        })
    }

    fn resolve(
        &self,
        py: Python<'_>,
        args: &Bound<'_, PyTuple>,
        kwargs: &Bound<'_, PyDict>,
    ) -> PyResult<String> {
        let mut bound: Vec<Option<Bound<'_, PyAny>>> =
            (0..self.parameters.len()).map(|_| None).collect();
        let positional: Vec<usize> = self
            .parameters
            .iter()
            .enumerate()
            .filter_map(|(index, parameter)| matches!(parameter.kind, 0 | 1).then_some(index))
            .collect();
        let varargs = self.parameters.iter().any(|parameter| parameter.kind == 2);
        let varkw = self.parameters.iter().any(|parameter| parameter.kind == 4);
        if args.len() > positional.len() && !varargs {
            return Err(PyTypeError::new_err("Too many positional arguments"));
        }
        for (index, value) in positional.into_iter().zip(args.iter()) {
            bound[index] = Some(value);
        }
        for (name, value) in kwargs.iter() {
            let name: String = name.extract()?;
            match self
                .parameters
                .iter()
                .position(|parameter| parameter.name == name && matches!(parameter.kind, 1 | 3))
            {
                Some(index) => {
                    if bound[index].is_some() {
                        return Err(PyTypeError::new_err(format!(
                            "Multiple values for argument '{name}'"
                        )));
                    }
                    bound[index] = Some(value);
                }
                None if !varkw => {
                    return Err(PyTypeError::new_err(format!(
                        "Unexpected keyword argument '{name}'"
                    )));
                }
                None => {}
            }
        }
        for (parameter, value) in self.parameters.iter().zip(bound.iter_mut()) {
            if value.is_none() && matches!(parameter.kind, 0 | 1 | 3) {
                match &parameter.default {
                    Some(default) => *value = Some(default.bind(py).clone()),
                    None => {
                        return Err(PyTypeError::new_err(format!(
                            "Missing required argument '{}'",
                            parameter.name
                        )));
                    }
                }
            }
        }
        let mut key = String::new();
        for part in &self.parts {
            match part {
                Part::Literal(literal) => key.push_str(literal),
                Part::Parameter(index) => {
                    let value = bound[*index].as_ref().unwrap();
                    let text = value.cast::<PyString>().map_err(|_| {
                        PyTypeError::new_err(format!(
                            "Lock key argument '{}' must be a string",
                            self.parameters[*index].name
                        ))
                    })?;
                    // Escape delimiters to prevent adjacent argument tuples
                    // from accidentally resolving to the same resource name.
                    // Length framing is required when several fields are used;
                    // single-field templates preserve the familiar key text.
                    let text = text.to_str()?;
                    if self.frame_values {
                        key.push_str(&text.len().to_string());
                        key.push(':');
                    }
                    key.push_str(text);
                }
            }
        }
        validate_key(&key)?;
        Ok(key)
    }
}
