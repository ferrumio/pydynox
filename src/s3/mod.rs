//! S3 operations module for large file storage.
//!
//! Provides S3 upload/download operations for S3Attribute.
//! The S3 client inherits all config from the DynamoDB client,
//! only allowing region override (same pattern as KMS).

mod client;
mod operations;

pub use client::S3Client as S3Operations;
pub use operations::S3Metadata;

use pyo3::prelude::*;

/// Register S3 classes in the Python module.
pub fn register_s3(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<S3Operations>()?;
    m.add_class::<S3Metadata>()?;
    Ok(())
}
