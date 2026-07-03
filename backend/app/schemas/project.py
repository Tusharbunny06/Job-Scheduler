from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    organization_id: Optional[UUID] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: UUID
    organization_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
