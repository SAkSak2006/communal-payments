from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    period_id: Mapped[int] = mapped_column(ForeignKey("payment_periods.id"))
    payment_method: Mapped[str] = mapped_column(String(50), default="cash")
    receipt_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    resident: Mapped["Resident"] = relationship(back_populates="payments")
    period: Mapped["PaymentPeriod"] = relationship()
