"""Smolagents department queries example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from smolagents import tool


class Employee(Model):
    model_config = ModelConfig(table="employees")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    email = StringAttribute()
    department = StringAttribute()


@tool
def search_by_department(department: str) -> list:
    """Find all employees in a department."""
    employees = Employee.sync_scan(
        filter_condition=Employee.department == department,
    )

    return [
        {
            "employee_id": emp.pk.replace("EMP#", ""),
            "name": emp.name,
            "email": emp.email,
        }
        for emp in employees
    ]


@tool
def transfer_employee(employee_id: str, new_department: str) -> dict:
    """Transfer an employee to a new department."""
    emp = Employee.sync_get(pk=f"EMP#{employee_id}", sk="PROFILE")

    if not emp:
        return {"error": "Not found"}

    old_dept = emp.department
    emp.sync_update(department=new_department)

    return {
        "success": True,
        "old_department": old_dept,
        "new_department": new_department,
    }
