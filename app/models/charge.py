from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Charge(Base):
    __tablename__ = "charges"
    __table_args__ = (
        UniqueConstraint("address_id", "service_id", "period_id", name="uq_charge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("utility_services.id"))
    period_id: Mapped[int] = mapped_column(ForeignKey("payment_periods.id"))
    reading_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("meter_readings.id"), nullable=True
    )
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    consumption: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    address: Mapped["Address"] = relationship(back_populates="charges")
    service: Mapped["UtilityService"] = relationship()
    period: Mapped["PaymentPeriod"] = relationship()
    tariff: Mapped["Tariff"] = relationship()
