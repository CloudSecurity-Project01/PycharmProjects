from pydantic import BaseModel, ConfigDict
from typing import Optional


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    name: str
    email: str


class UserIn(User):
    password: str


class AuthenticationIn(BaseModel):
    email: str
    password: str


class Authentication(AuthenticationIn):
    model_config = ConfigDict(from_attributes=True)
    username: str
    id: int





