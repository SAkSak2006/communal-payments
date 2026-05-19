from typing import List

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UtilityService(Base):
    __tablename__ = "utility_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    unit: Mapped[str] = mapped_column(String(20))
    has_meter: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String(255), default="")

    tariffs: Mapped[List["Tariff"]] = relationship(back_populates="service")
    meters: Mapped[List["Meter"]] = relationship(back_populates="service")
