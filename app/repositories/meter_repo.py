from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Meter, MeterReading
from app.repositories.base import BaseRepository


class MeterRepository(BaseRepository[Meter]):
    def __init__(self, session: AsyncSession):
        super().__init__(Meter, session)

    async def get_by_address(self, address_id: int) -> Sequence[Meter]:
        result = await self.session.execute(
            select(Meter)
            .options(selectinload(Meter.service))
            .where(Meter.address_id == address_id, Meter.is_active.is_(True))
        )
        return result.scalars().all()

    async def get_last_reading(self, meter_id: int) -> Optional[MeterReading]:
        result = await self.session.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter_id)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
