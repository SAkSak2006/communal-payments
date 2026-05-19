import asyncio
import bcrypt
from app.database import async_session
from app.models.user import User


async def create_admin():
    hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    async with async_session() as session:
        user = User(
            username="admin",
            hashed_password=hashed,
            full_name="Администратор",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print("Администратор создан")


asyncio.run(create_admin())
