from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class TariffCreate(BaseModel):
    service_id: int
    price_per_unit: Decimal
    effective_from: date


class TariffOut(BaseModel):
    id: int
    service_id: int
    price_per_unit: Decimal
    effective_from: date
    effective_to: Optional[date] = None

    model_config = {"from_attributes": True}
