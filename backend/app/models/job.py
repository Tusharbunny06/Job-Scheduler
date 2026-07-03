from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.models.base import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(String, default="queued", nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False, index=True)  # Higher = picked up first
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    max_retries = Column(Integer, default=0, nullable=False)
    current_retries = Column(Integer, default=0, nullable=False)
    execution_timeout = Column(Integer, default=3600, nullable=False)  # 1 hour default

class JobExecution(Base):
    __tablename__ = "job_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_stack = Column(Text, nullable=True)
    result = Column(JSONB, nullable=True)

class JobLog(Base):
    __tablename__ = "job_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class DeadLetterQueue(Base):
    __tablename__ = "dead_letter_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    reason = Column(Text, nullable=False)
    moved_at = Column(DateTime(timezone=True), server_default=func.now())

class ScheduledJob(Base):
    """
    Represents a recurring cron job definition.
    The CronScheduler reads this table every tick and dispatches new Job instances
    when next_run_at has passed. Only active scheduled jobs are dispatched.
    """
    __tablename__ = "scheduled_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=True)  # Optional human-readable label
    payload = Column(JSONB, nullable=False)
    cron_expression = Column(String, nullable=False)
    next_run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)  # Audit: when was it last dispatched
    is_active = Column(Boolean, default=True, nullable=False)     # Allow disabling without deleting
    created_at = Column(DateTime(timezone=True), server_default=func.now())
