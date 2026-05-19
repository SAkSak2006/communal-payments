from decimal import Decimal
from pydantic import BaseModel


class ChargeOut(BaseModel):
    id: int
    address_id: int
    service_id: int
    period_id: int
    consumption: Decimal
    amount: Decimal

    model_config = {"from_attributes": True}
