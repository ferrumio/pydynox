"""Smolagents integration with pydynox.

Use case: HR assistant agent with encrypted employee data.
"""

from __future__ import annotations

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import EncryptedAttribute, NumberAttribute, StringAttribute
from smolagents import LiteLLMModel, ToolCallingAgent, tool

# Create client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


# Define models with encrypted fields
class Employee(Model):
    model_config = ModelConfig(table="employees")

    pk = StringAttribute(partition_key=True)  # EMP#<id>
    sk = StringAttribute(sort_key=True)  # PROFILE
    name = StringAttribute()
    email = StringAttribute()
    department = StringAttribute()
    salary = EncryptedAttribute(
        key_id="arn:aws:kms:us-east-1:193482298196:key/37b7efcb-650b-4af9-8b73-1f106309f595"
    )
    ssn = EncryptedAttribute(
        key_id="arn:aws:kms:us-east-1:193482298196:key/37b7efcb-650b-4af9-8b73-1f106309f595"
    )


class TimeOff(Model):
    model_config = ModelConfig(table="timeoff")

    pk = StringAttribute(partition_key=True)  # EMP#<id>
    sk = StringAttribute(sort_key=True)  # REQUEST#<date>
    request_type = StringAttribute()  # vacation, sick, personal
    days = NumberAttribute()
    status = StringAttribute()  # pending, approved, denied
    notes = StringAttribute(default=None)


class Department(Model):
    model_config = ModelConfig(table="departments")

    pk = StringAttribute(partition_key=True)  # DEPT#<name>
    sk = StringAttribute(sort_key=True)  # METADATA
    name = StringAttribute()
    manager = StringAttribute()
    headcount = NumberAttribute(default=0)
    budget = NumberAttribute(default=0)


# Define tools using @tool decorator
@tool
def get_employee(employee_id: str) -> dict:
    """Get employee information by ID.

    Args:
        employee_id: The employee's unique identifier.

    Returns:
        Employee info with name, email, and department.
        Sensitive data like salary and SSN are not returned.
    """
    emp = Employee.sync_get(pk=f"EMP#{employee_id}", sk="PROFILE")

    if not emp:
        return {"error": f"Employee {employee_id} not found"}

    return {
        "employee_id": employee_id,
        "name": emp.name,
        "email": emp.email,
        "department": emp.department,
    }


@tool
def search_employees_by_department(department: str) -> list:
    """Find all employees in a department.

    Args:
        department: Department name (e.g., "Engineering", "Sales").

    Returns:
        List of employees with name and email.
    """
    employees = list(
        Employee.sync_scan(
            filter_condition=Employee.department == department,
        )
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
def get_time_off_balance(employee_id: str) -> dict:
    """Get employee's time off balance and recent requests.

    Args:
        employee_id: The employee's unique identifier.

    Returns:
        Time off balance and list of recent requests.
    """
    requests = list(
        TimeOff.sync_query(
            partition_key=f"EMP#{employee_id}",
            scan_index_forward=False,
            limit=10,
        )
    )

    approved_days = sum(r.days for r in requests if r.status == "approved")
    pending_days = sum(r.days for r in requests if r.status == "pending")

    return {
        "employee_id": employee_id,
        "approved_days_used": approved_days,
        "pending_days": pending_days,
        "recent_requests": [
            {
                "date": r.sk.replace("REQUEST#", ""),
                "type": r.request_type,
                "days": r.days,
                "status": r.status,
            }
            for r in requests[:5]
        ],
    }


@tool
def submit_time_off_request(
    employee_id: str,
    request_date: str,
    request_type: str,
    days: int,
    notes: str = None,
) -> dict:
    """Submit a new time off request.

    Args:
        employee_id: The employee's unique identifier.
        request_date: Start date (YYYY-MM-DD format).
        request_type: Type of time off (vacation, sick, personal).
        days: Number of days requested.
        notes: Optional notes for the request.

    Returns:
        Confirmation of the submitted request.
    """
    if request_type not in ["vacation", "sick", "personal"]:
        return {"error": "Invalid request type. Use: vacation, sick, or personal"}

    if days < 1 or days > 30:
        return {"error": "Days must be between 1 and 30"}

    request = TimeOff(
        pk=f"EMP#{employee_id}",
        sk=f"REQUEST#{request_date}",
        request_type=request_type,
        days=days,
        status="pending",
        notes=notes,
    )
    request.sync_save()

    return {
        "success": True,
        "employee_id": employee_id,
        "date": request_date,
        "type": request_type,
        "days": days,
        "status": "pending",
    }


@tool
def get_department_info(department_name: str) -> dict:
    """Get department information and headcount.

    Args:
        department_name: Name of the department.

    Returns:
        Department info with manager, headcount, and budget.
    """
    dept = Department.sync_get(pk=f"DEPT#{department_name}", sk="METADATA")

    if not dept:
        return {"error": f"Department {department_name} not found"}

    return {
        "name": dept.name,
        "manager": dept.manager,
        "headcount": dept.headcount,
        "budget": dept.budget,
    }


@tool
def update_employee_department(employee_id: str, new_department: str) -> dict:
    """Transfer an employee to a new department.

    Args:
        employee_id: The employee's unique identifier.
        new_department: Name of the new department.

    Returns:
        Confirmation of the department change.
    """
    emp = Employee.sync_get(pk=f"EMP#{employee_id}", sk="PROFILE")

    if not emp:
        return {"error": f"Employee {employee_id} not found"}

    old_department = emp.department
    emp.sync_update(department=new_department)

    return {
        "success": True,
        "employee_id": employee_id,
        "old_department": old_department,
        "new_department": new_department,
    }


# Create the agent with Bedrock via LiteLLM
model = LiteLLMModel(model_id="bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0")

agent = ToolCallingAgent(
    tools=[
        get_employee,
        search_employees_by_department,
        get_time_off_balance,
        submit_time_off_request,
        get_department_info,
        update_employee_department,
    ],
    model=model,
)


# Example usage
if __name__ == "__main__":

    def create_tables():
        """Create DynamoDB tables if they don't exist."""
        if not client.table_exists("employees"):
            client.create_table(
                table_name="employees",
                partition_key=("pk", "S"),
                sort_key=("sk", "S"),
                wait=True,
            )
            print("Table 'employees' created!")

        if not client.table_exists("timeoff"):
            client.create_table(
                table_name="timeoff",
                partition_key=("pk", "S"),
                sort_key=("sk", "S"),
                wait=True,
            )
            print("Table 'timeoff' created!")

        if not client.table_exists("departments"):
            client.create_table(
                table_name="departments",
                partition_key=("pk", "S"),
                sort_key=("sk", "S"),
                wait=True,
            )
            print("Table 'departments' created!")

    def seed_data():
        """Insert sample employees, time off requests, and departments."""
        sample_employees = [
            Employee(
                pk="EMP#001",
                sk="PROFILE",
                name="Ana Costa",
                email="ana.costa@company.com",
                department="Engineering",
                salary="85000",
                ssn="123-45-6789",
            ),
            Employee(
                pk="EMP#002",
                sk="PROFILE",
                name="Carlos Silva",
                email="carlos.silva@company.com",
                department="Engineering",
                salary="92000",
                ssn="987-65-4321",
            ),
            Employee(
                pk="EMP#003",
                sk="PROFILE",
                name="Maria Santos",
                email="maria.santos@company.com",
                department="Sales",
                salary="78000",
                ssn="456-78-9012",
            ),
        ]

        sample_timeoff = [
            TimeOff(
                pk="EMP#001",
                sk="REQUEST#2025-01-10",
                request_type="vacation",
                days=5,
                status="approved",
                notes="Family trip",
            ),
            TimeOff(
                pk="EMP#001",
                sk="REQUEST#2025-01-20",
                request_type="sick",
                days=2,
                status="approved",
                notes=None,
            ),
            TimeOff(
                pk="EMP#002",
                sk="REQUEST#2025-01-15",
                request_type="personal",
                days=1,
                status="pending",
                notes="Doctor appointment",
            ),
        ]

        sample_departments = [
            Department(
                pk="DEPT#Engineering",
                sk="METADATA",
                name="Engineering",
                manager="Ana Costa",
                headcount=15,
                budget=2000000,
            ),
            Department(
                pk="DEPT#Sales",
                sk="METADATA",
                name="Sales",
                manager="Pedro Lima",
                headcount=10,
                budget=1500000,
            ),
        ]

        for emp in sample_employees:
            emp.sync_save()
        for req in sample_timeoff:
            req.sync_save()
        for dept in sample_departments:
            dept.sync_save()

        print("Sample data inserted!")

    # Create tables and seed data
    create_tables()
    seed_data()

    # Run the agent
    response = agent.run(
        "How many vacation days has employee EMP001 used this year? "
        "Also, submit a 3-day vacation request starting 2025-02-15."
    )
    print(response)
