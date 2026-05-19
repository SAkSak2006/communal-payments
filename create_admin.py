import asyncio
from app.database import async_session
from app.models.user import User
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"])


async def create_admin():
    async with async_session() as session:
        user = User(
            username="admin",
            hashed_password=pwd.hash("admin123"),
            full_name="Администратор",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print("Администратор создан")


asyncio.run(create_admin())
