from fastapi import APIRouter

from app.api.v1 import admin, announcements, auth, billing, exports, generation, knowledge, projects, review, tenant, workflow

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(knowledge.router)
api_router.include_router(generation.router)
api_router.include_router(workflow.router)
api_router.include_router(review.router)
api_router.include_router(exports.router)
api_router.include_router(tenant.router)
api_router.include_router(admin.router)
api_router.include_router(billing.router)
api_router.include_router(announcements.router)
