from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import String, Numeric, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Address(Base):
    __tablename__ = "addresses"
    __table_args__ = (
        UniqueConstraint("city", "street", "building", "apartment", name="uq_address"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str] = mapped_column(String(100))
    street: Mapped[str] = mapped_column(String(150))
    building: Mapped[str] = mapped_column(String(20))
    apartment: Mapped[str] = mapped_column(String(20))
    area_sqm: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    resident: Mapped["Resident"] = relationship(back_populates="addresses")
    meters: Mapped[List["Meter"]] = relationship(back_populates="address")
    charges: Mapped[List["Charge"]] = relationship(back_populates="address")
