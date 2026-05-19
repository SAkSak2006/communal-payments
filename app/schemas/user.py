from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}
