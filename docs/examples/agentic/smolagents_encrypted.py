"""Smolagents encrypted data example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import EncryptedAttribute, StringAttribute
from smolagents import tool


class Employee(Model):
    model_config = ModelConfig(table="employees")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    department = StringAttribute()
    ssn = EncryptedAttribute(key_id="alias/hr-encryption-key")


@tool
def get_employee(employee_id: str) -> dict:
    """Get employee info (excludes sensitive data)."""
    emp = Employee.sync_get(pk=f"EMP#{employee_id}", sk="PROFILE")

    if not emp:
        return {"error": "Not found"}

    # Don't return salary or SSN!
    return {
        "name": emp.name,
        "email": emp.email,
        "department": emp.department,
    }


@tool
def verify_ssn_last_four(employee_id: str, last_four: str) -> dict:
    """Verify the last 4 digits of an employee's SSN.

    Args:
        employee_id: The employee ID.
        last_four: Last 4 digits to verify.

    Returns:
        Whether the SSN matches.
    """
    emp = Employee.sync_get(pk=f"EMP#{employee_id}", sk="PROFILE")

    if not emp:
        return {"error": "Not found"}

    # SSN is decrypted automatically
    matches = emp.ssn.endswith(last_four)
    return {"verified": matches}
