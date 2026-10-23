// Request building does not need a Python interpreter or DynamoDB.
#[path = "../src/batch_operations/request.rs"]
mod request;

use aws_sdk_dynamodb::types::AttributeValue;
use std::collections::HashMap;

fn key(pk: &str) -> HashMap<String, AttributeValue> {
    HashMap::from([("pk".to_string(), AttributeValue::S(pk.to_string()))])
}

fn names(pairs: &[(&str, &str)]) -> HashMap<String, String> {
    pairs
        .iter()
        .map(|(placeholder, name)| (placeholder.to_string(), name.to_string()))
        .collect()
}

#[test]
fn without_projection_request_has_no_projection_fields() {
    let request =
        request::build_keys_and_attributes(vec![key("a"), key("b")], false, None, None).unwrap();

    assert_eq!(request.keys().len(), 2);
    assert_eq!(request.projection_expression(), None);
    assert!(request.expression_attribute_names().is_none());
    assert_eq!(request.consistent_read(), None);
}

#[test]
fn projection_with_reserved_word_placeholders_is_set() {
    let attr_names = names(&[("#p0", "name"), ("#p1", "status")]);
    let request = request::build_keys_and_attributes(
        vec![key("a")],
        false,
        Some("#p0, #p1"),
        Some(&attr_names),
    )
    .unwrap();

    assert_eq!(request.projection_expression(), Some("#p0, #p1"));
    let placeholders = request.expression_attribute_names().unwrap();
    assert_eq!(placeholders.get("#p0").map(String::as_str), Some("name"));
    assert_eq!(placeholders.get("#p1").map(String::as_str), Some("status"));
}

#[test]
fn retry_request_for_unprocessed_keys_keeps_projection() {
    let attr_names = names(&[("#p0", "name")]);
    let unprocessed = vec![key("b")];
    let request =
        request::build_keys_and_attributes(unprocessed, false, Some("#p0"), Some(&attr_names))
            .unwrap();

    assert_eq!(request.keys().len(), 1);
    assert_eq!(request.projection_expression(), Some("#p0"));
    assert_eq!(
        request
            .expression_attribute_names()
            .and_then(|placeholders| placeholders.get("#p0"))
            .map(String::as_str),
        Some("name")
    );
}

#[test]
fn consistent_read_is_kept_with_projection() {
    let attr_names = names(&[("#p0", "name")]);
    let request =
        request::build_keys_and_attributes(vec![key("a")], true, Some("#p0"), Some(&attr_names))
            .unwrap();

    assert_eq!(request.consistent_read(), Some(true));
    assert_eq!(request.projection_expression(), Some("#p0"));
}
