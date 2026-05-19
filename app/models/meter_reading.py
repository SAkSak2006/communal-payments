import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, Integer, Boolean, Enum, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReadingSource(str, enum.Enum):
    TELEGRAM = "telegram"
    ADMIN = "admin"
    AUTO = "auto"


class MeterReading(Base):
    __tablename__ = "meter_readings"
    __table_args__ = (
        UniqueConstraint("meter_id", "period_year", "period_month", name="uq_reading_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    previous_value: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    consumption: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    reading_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    source: Mapped[ReadingSource] = mapped_column(Enum(ReadingSource), default=ReadingSource.ADMIN)
    submitted_by_resident: Mapped[Optional[int]] = mapped_column(
        ForeignKey("residents.id"), nullable=True
    )
    submitted_by_admin: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    meter: Mapped["Meter"] = relationship(back_populates="readings")
