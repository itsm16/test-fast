from src.modules.auth.dto.auth_dto import RegisterUserDto


def register_user(body: RegisterUserDto):
    # print(body.email)
    del body.password
    return {"data": body}

