from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base

class Queue(Base):
    __tablename__ = "queues"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    concurrency_limit = Column(Integer, nullable=True)
    is_paused = Column(Boolean, default=False, nullable=False)
    default_execution_timeout = Column(Integer, default=3600, nullable=False)

class RetryPolicy(Base):
    __tablename__ = "retry_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, unique=True)
    max_retries = Column(Integer, default=3, nullable=False)
    strategy = Column(String, default="fixed_delay", nullable=False) # fixed_delay, linear_backoff, exponential_backoff
    delay_seconds = Column(Integer, default=60, nullable=False)
    backoff_multiplier = Column(Float, default=2.0, nullable=False)
