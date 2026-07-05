
from fastapi import APIRouter
from src.modules.auth import auth_controller
from src.modules.auth.dto.auth_dto import RegisterUserDto

auth_router = APIRouter(
    prefix="/auth"
)


@auth_router.get("/test")
def test_auth():
    return {"message": "Auth route is working!"}


@auth_router.post("/register")
def register_user_route(body: RegisterUserDto):
    return auth_controller.register_user(body)
