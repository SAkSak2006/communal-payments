from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id"))
    type: Mapped[str] = mapped_column(String(50))
    message_text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    resident: Mapped["Resident"] = relationship(back_populates="notifications")
