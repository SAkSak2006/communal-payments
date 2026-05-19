from typing import TypeVar, Generic, Type, Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        return await self.session.get(self.model, id)

    async def get_all(self, offset: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await self.session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs) -> ModelType:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.commit()
