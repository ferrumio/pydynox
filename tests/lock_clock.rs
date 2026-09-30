// Pure clock tests do not need a Python interpreter or DynamoDB.
#[path = "../src/lock/clock.rs"]
mod clock;

#[test]
fn new_stamp_is_valid() {
    assert!(clock::Stamp::now().valid(std::time::Duration::from_secs(30)));
}
