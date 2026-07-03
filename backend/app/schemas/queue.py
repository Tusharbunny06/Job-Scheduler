from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class RetryPolicyBase(BaseModel):
    max_retries: int = 3
    strategy: str = "fixed_delay"
    delay_seconds: int = 60
    backoff_multiplier: float = 2.0

class RetryPolicyResponse(RetryPolicyBase):
    id: UUID
    queue_id: UUID

    class Config:
        from_attributes = True

class QueueBase(BaseModel):
    name: str
    priority: int = 1
    concurrency_limit: Optional[int] = None
    is_paused: bool = False
    default_execution_timeout: int = 3600

class QueueCreate(QueueBase):
    project_id: UUID
    retry_policy: Optional[RetryPolicyBase] = None

class QueueUpdate(BaseModel):
    name: Optional[str] = None
    priority: Optional[int] = None
    concurrency_limit: Optional[int] = None
    is_paused: Optional[bool] = None
    default_execution_timeout: Optional[int] = None
    retry_policy: Optional[RetryPolicyBase] = None

class QueueResponse(QueueBase):
    id: UUID
    project_id: UUID

    class Config:
        from_attributes = True
