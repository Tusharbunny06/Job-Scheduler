from fastapi import APIRouter
from app.api.v1 import auth, projects, queues, jobs, metrics, scheduled_jobs, workers

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(queues.router, prefix="/queues", tags=["queues"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scheduled_jobs.router, prefix="/scheduled-jobs", tags=["scheduled-jobs"])
api_router.include_router(workers.router, prefix="/workers", tags=["workers"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
