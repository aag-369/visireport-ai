from fastapi import APIRouter

from app.api.v1 import auth, boards, inspections, defects, audit, system

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(boards.router)
api_router.include_router(inspections.router)
api_router.include_router(defects.router)
api_router.include_router(audit.router)
api_router.include_router(system.router)
