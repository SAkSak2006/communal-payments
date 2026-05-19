from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Meter(Base):
    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(primary_key=True)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("utility_services.id"))
    serial_number: Mapped[str] = mapped_column(String(50))
    installation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    verification_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    address: Mapped["Address"] = relationship(back_populates="meters")
    service: Mapped["UtilityService"] = relationship(back_populates="meters")
    readings: Mapped[List["MeterReading"]] = relationship(back_populates="meter")
