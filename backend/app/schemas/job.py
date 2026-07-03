from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Dict, List

class JobBase(BaseModel):
    queue_id: UUID
    payload: Dict[str, Any]
    status: str = "queued"
    priority: int = 0

class JobCreate(BaseModel):
    queue_id: UUID
    payload: Dict[str, Any]
    scheduled_at: Optional[datetime] = None
    priority: int = 0  # Higher value = picked up first by worker
    execution_timeout: Optional[int] = None # Will inherit from queue if None

class JobBatchCreate(BaseModel):
    """Create multiple jobs in a single atomic request."""
    jobs: List[JobCreate]

class JobResponse(JobBase):
    id: UUID
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    max_retries: int
    current_retries: int
    priority: int
    execution_timeout: int
    
    model_config = ConfigDict(from_attributes=True)

class JobLogResponse(BaseModel):
    id: UUID
    job_id: UUID
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class JobExecutionResponse(BaseModel):
    id: UUID
    job_id: UUID
    worker_id: Optional[UUID] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_stack: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
