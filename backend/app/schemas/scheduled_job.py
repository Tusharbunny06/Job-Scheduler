from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Dict


class ScheduledJobCreate(BaseModel):
    """Schema for creating a new recurring cron job."""
    queue_id: UUID
    name: Optional[str] = None
    payload: Dict[str, Any]
    cron_expression: str

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate the cron expression using croniter."""
        from croniter import croniter
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: '{v}'")
        return v


class ScheduledJobUpdate(BaseModel):
    """Schema for updating a recurring cron job."""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    cron_expression: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from croniter import croniter
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: '{v}'")
        return v


class ScheduledJobResponse(BaseModel):
    """Schema for returning a recurring cron job."""
    id: UUID
    queue_id: UUID
    name: Optional[str] = None
    payload: Dict[str, Any]
    cron_expression: str
    next_run_at: datetime
    last_run_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
