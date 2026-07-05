
from fastapi import APIRouter
from src.modules.auth.auth_route import auth_router

api_router=APIRouter(prefix="/api")

api_router.include_router(auth_router)
