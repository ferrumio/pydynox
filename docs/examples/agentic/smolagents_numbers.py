"""Smolagents NumberAttribute example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from smolagents import tool


class TimeOff(Model):
    model_config = ModelConfig(table="timeoff")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    request_type = StringAttribute()
    days = NumberAttribute()
    status = StringAttribute()


@tool
def get_time_off_balance(employee_id: str) -> dict:
    """Get employee's time off balance.

    Args:
        employee_id: The employee ID.
    """
    requests = list(
        TimeOff.sync_query(
            partition_key=f"EMP#{employee_id}",
        )
    )

    # Sum up days using NumberAttribute
    approved_days = sum(r.days or 0 for r in requests if r.status == "approved")
    pending_days = sum(r.days or 0 for r in requests if r.status == "pending")

    return {
        "approved_days_used": approved_days,
        "pending_days": pending_days,
        "remaining": 20 - approved_days,  # Assuming 20 days/year
    }


@tool
def submit_time_off(
    employee_id: str,
    request_date: str,
    request_type: str,
    days: int,
) -> dict:
    """Submit a time off request.

    Args:
        employee_id: The employee ID.
        request_date: Start date in YYYY-MM-DD format.
        request_type: Type of leave, such as vacation or sick leave.
        days: Number of days requested, between 1 and 30.
    """
    if days < 1 or days > 30:
        return {"error": "Days must be between 1 and 30"}

    request = TimeOff(
        pk=f"EMP#{employee_id}",
        sk=f"REQUEST#{request_date}",
        request_type=request_type,
        days=days,  # NumberAttribute handles int/float
        status="pending",
    )
    request.sync_save()

    return {"success": True, "days": days, "status": "pending"}
