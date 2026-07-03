from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import Project
from app.schemas.project import ProjectCreate
from typing import List, Optional
from uuid import UUID

class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Project]:
        stmt = select(Project).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, project_in: ProjectCreate) -> Project:
        db_project = Project(
            organization_id=project_in.organization_id,
            name=project_in.name
        )
        self.session.add(db_project)
        await self.session.commit()
        await self.session.refresh(db_project)
        return db_project

    async def update(self, project: Project, project_in) -> Project:
        if project_in.name is not None:
            project.name = project_in.name
        await self.session.commit()
        await self.session.refresh(project)
        return project
        
    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.commit()
