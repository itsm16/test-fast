from src.modules.auth import auth_service
from src.modules.auth.dto.auth_dto import RegisterUserDto


def register_user(body: RegisterUserDto):
    user = auth_service.register_user(body)
    return {"message": "User registered successfully!", **user}


