from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("utility_services.id"))
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    service: Mapped["UtilityService"] = relationship(back_populates="tariffs")
