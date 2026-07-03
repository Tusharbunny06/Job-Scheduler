from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, List
from uuid import UUID

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.repositories.project_repository import ProjectRepository

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    if not project_in.organization_id:
        # Auto-resolve or create an organization for the user
        stmt = select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
        result = await db.execute(stmt)
        member = result.scalars().first()
        if member:
            project_in.organization_id = member.organization_id
        else:
            org = Organization(name=f"{current_user.email}'s Org")
            db.add(org)
            await db.flush()
            new_member = OrganizationMember(user_id=current_user.id, organization_id=org.id, role="owner")
            db.add(new_member)
            await db.flush()
            project_in.organization_id = org.id

    project_repo = ProjectRepository(db)
    project = await project_repo.create(project_in=project_in)
    return project


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all projects belonging to the current user's organizations.
    Implements RBAC: users only see their own org's projects.
    Admin users see all projects.
    """
    if current_user.role == "admin":
        # Admins see all projects
        project_repo = ProjectRepository(db)
        return await project_repo.get_all(skip=skip, limit=limit)

    # Non-admin users: scope to their own organizations
    stmt = (
        select(Project)
        .join(OrganizationMember, Project.organization_id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await project_repo.update(project=project, project_in=project_in)
    return project

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await project_repo.delete(project=project)
    return None
