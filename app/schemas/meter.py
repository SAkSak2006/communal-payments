from datetime import date
from typing import Optional
from pydantic import BaseModel


class MeterCreate(BaseModel):
    address_id: int
    service_id: int
    serial_number: str
    installation_date: Optional[date] = None
    verification_date: Optional[date] = None


class MeterOut(BaseModel):
    id: int
    address_id: int
    service_id: int
    serial_number: str
    is_active: bool

    model_config = {"from_attributes": True}
