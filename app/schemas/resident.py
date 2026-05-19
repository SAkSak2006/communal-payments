from typing import Optional
from pydantic import BaseModel


class ResidentCreate(BaseModel):
    full_name: str
    phone: str
    personal_account: str


class ResidentOut(BaseModel):
    id: int
    full_name: str
    phone: str
    personal_account: str
    telegram_id: Optional[int] = None
    is_verified: bool

    model_config = {"from_attributes": True}
