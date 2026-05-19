from decimal import Decimal
from pydantic import BaseModel
from app.models.meter_reading import ReadingSource


class MeterReadingCreate(BaseModel):
    meter_id: int
    value: Decimal
    previous_value: Decimal
    consumption: Decimal
    period_year: int
    period_month: int
    source: ReadingSource = ReadingSource.ADMIN


class MeterReadingOut(BaseModel):
    id: int
    meter_id: int
    value: Decimal
    previous_value: Decimal
    consumption: Decimal
    period_year: int
    period_month: int
    source: ReadingSource
    is_validated: bool

    model_config = {"from_attributes": True}
