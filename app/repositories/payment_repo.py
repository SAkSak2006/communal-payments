from decimal import Decimal
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Charge
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_by_resident(
        self, resident_id: int, limit: int = 10
    ) -> Sequence[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.resident_id == resident_id)
            .order_by(Payment.payment_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_total_paid(self, resident_id: int) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.resident_id == resident_id
            )
        )
        return result.scalar_one()

    async def get_total_charged(self, resident_id: int) -> Decimal:
        from app.models import Address

        result = await self.session.execute(
            select(func.coalesce(func.sum(Charge.amount), 0))
            .join(Address, Charge.address_id == Address.id)
            .where(Address.resident_id == resident_id)
        )
        return result.scalar_one()
