from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    personal_account: Mapped[str] = mapped_column(String(20), unique=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    addresses: Mapped[List["Address"]] = relationship(back_populates="resident")
    payments: Mapped[List["Payment"]] = relationship(back_populates="resident")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="resident")
