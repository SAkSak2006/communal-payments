from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Resident
from app.repositories.base import BaseRepository


class ResidentRepository(BaseRepository[Resident]):
    def __init__(self, session: AsyncSession):
        super().__init__(Resident, session)

    async def get_by_personal_account(self, account: str) -> Optional[Resident]:
        result = await self.session.execute(
            select(Resident).where(Resident.personal_account == account)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Resident]:
        result = await self.session.execute(
            select(Resident).where(Resident.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_with_addresses(self, resident_id: int) -> Optional[Resident]:
        result = await self.session.execute(
            select(Resident)
            .options(selectinload(Resident.addresses))
            .where(Resident.id == resident_id)
        )
        return result.scalar_one_or_none()

    async def search(self, query: str):
        result = await self.session.execute(
            select(Resident).where(
                Resident.full_name.ilike(f"%{query}%")
                | Resident.personal_account.ilike(f"%{query}%")
                | Resident.phone.ilike(f"%{query}%")
            )
        )
        return result.scalars().all()
