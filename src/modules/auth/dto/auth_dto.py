from pydantic import BaseModel


class RegisterUserDto(BaseModel):
    name: str
    email: str
    password: str


class RegisterUserResponseDto(BaseModel):
    message: str
