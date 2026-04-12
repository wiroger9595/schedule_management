from fastapi import APIRouter
from .endpoints.auth import router as auth_router
from .endpoints.users import router as users_router
from .endpoints.schedules import router as schedules_router
from .endpoints.contacts import router as contacts_router
from .endpoints.estimate import router as estimate_router
from .endpoints.line import router as line_router
from .endpoints.comments import router as comments_router
from .endpoints.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(schedules_router, prefix="/schedules", tags=["schedules"])
api_router.include_router(contacts_router, prefix="/contacts", tags=["contacts"])
api_router.include_router(estimate_router, prefix="/estimate", tags=["estimate"])
api_router.include_router(line_router, prefix="/line", tags=["line"])
api_router.include_router(comments_router, prefix="/comments", tags=["comments"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
