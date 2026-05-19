from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, Boolean, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentPeriod(Base):
    __tablename__ = "payment_periods"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
