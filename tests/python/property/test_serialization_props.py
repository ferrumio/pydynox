"""Property-based tests for serialization round-trip.

**Feature: pydynox, Property 1: Serialization Round-Trip**
**Validates: Requirements 1.6, 12.1, 12.2**

For any valid Python value (string, number, boolean, list, dict),
converting it to DynamoDB format and back to Python should produce
an equivalent value.
"""

from hypothesis import given, settings
from hypothesis import strategies as st
from pydynox._rust import dynamo_to_py, py_to_dynamo

# Strategy for generating valid Python values that DynamoDB supports
# Note: DynamoDB has some constraints:
# - Numbers are stored as strings, so we use reasonable ranges
# - Empty sets are not allowed
# - Sets must be homogeneous (all same type)


def dynamo_compatible_values():
    """Generate Python values that can round-trip through DynamoDB."""
    return st.recursive(
        # Base cases: simple types
        st.one_of(
            st.none(),
            st.booleans(),
            st.text(min_size=0, max_size=100),
            # Integers within safe range for DynamoDB
            st.integers(min_value=-(10**15), max_value=10**15),
            # Floats - avoid special values like inf, nan
            st.floats(
                min_value=-(10**10),
                max_value=10**10,
                allow_nan=False,
                allow_infinity=False,
            ),
            # Binary data
            st.binary(min_size=0, max_size=100),
        ),
        # Recursive cases: lists and dicts
        lambda children: st.one_of(
            st.lists(children, max_size=10),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=children,
                max_size=10,
            ),
        ),
        max_leaves=20,
    )


def compare_values(original, result):
    """Compare values accounting for DynamoDB type conversions.

    DynamoDB stores numbers as strings, so:
    - int and float may be converted (42.0 -> 42)
    - We need to compare numerically for numbers
    """
    if original is None:
        return result is None

    if isinstance(original, bool):
        return result is original

    if isinstance(original, (int, float)):
        if isinstance(result, (int, float)):
            # Compare numerically - DynamoDB may convert 42.0 to 42
            return float(original) == float(result)
        return False

    if isinstance(original, str):
        return result == original

    if isinstance(original, bytes):
        return result == original

    if isinstance(original, list):
        if not isinstance(result, list):
            return False
        if len(original) != len(result):
            return False
        return all(compare_values(o, r) for o, r in zip(original, result))

    if isinstance(original, dict):
        if not isinstance(result, dict):
            return False
        if set(original.keys()) != set(result.keys()):
            return False
        return all(compare_values(original[k], result[k]) for k in original)

    if isinstance(original, (set, frozenset)):
        if not isinstance(result, (set, frozenset)):
            return False
        # Sets need special handling - convert to comparable form
        orig_list = sorted(str(x) for x in original)
        result_list = sorted(str(x) for x in result)
        return orig_list == result_list

    return original == result


@given(value=dynamo_compatible_values())
@settings(max_examples=100)
def test_serialization_round_trip(value):
    """Property 1: Serialization Round-Trip.

    For any valid Python value, converting to DynamoDB format and back
    should produce an equivalent value.

    **Feature: pydynox, Property 1: Serialization Round-Trip**
    **Validates: Requirements 1.6, 12.1, 12.2**
    """
    # Convert Python -> DynamoDB
    dynamo_value = py_to_dynamo(value)

    # Convert DynamoDB -> Python
    result = dynamo_to_py(dynamo_value)

    # Values should be equivalent
    assert compare_values(value, result), (
        f"Round-trip failed: {value!r} -> {dynamo_value!r} -> {result!r}"
    )
