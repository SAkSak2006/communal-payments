from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    resident_id: int
    amount: Decimal
    payment_date: datetime
    period_id: int
    payment_method: str = "cash"
    receipt_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    id: int
    resident_id: int
    amount: Decimal
    payment_date: datetime
    payment_method: str

    model_config = {"from_attributes": True}
