import asyncio
import bcrypt
from app.database import async_session
from app.models.user import User, UserRole


async def create_admin():
    hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    async with async_session() as session:
        user = User(
            username="admin",
            email="admin@communal.local",
            hashed_password=hashed,
            full_name="Администратор",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print("Администратор создан")


asyncio.run(create_admin())
