from datetime import date

from sqlalchemy import select

from app.database import async_session
from app.models import UtilityService, Tariff, User, UserRole
from app.services.auth_service import get_password_hash


async def seed_initial_data():
    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(UtilityService).limit(1))
        if result.scalar_one_or_none():
            return

        # Seed utility services
        services = [
            UtilityService(
                name="Холодное водоснабжение",
                code="cold_water",
                unit="куб.м",
                has_meter=True,
                description="Подача холодной воды",
            ),
            UtilityService(
                name="Горячее водоснабжение",
                code="hot_water",
                unit="куб.м",
                has_meter=True,
                description="Подача горячей воды",
            ),
            UtilityService(
                name="Электроснабжение",
                code="electricity",
                unit="кВт·ч",
                has_meter=True,
                description="Подача электроэнергии",
            ),
            UtilityService(
                name="Газоснабжение",
                code="gas",
                unit="куб.м",
                has_meter=True,
                description="Подача газа",
            ),
            UtilityService(
                name="Отопление",
                code="heating",
                unit="Гкал",
                has_meter=False,
                description="Теплоснабжение (расчёт по площади)",
            ),
        ]
        session.add_all(services)
        await session.flush()

        # Seed tariffs (example rates)
        tariffs = [
            Tariff(service_id=services[0].id, price_per_unit=42.30, effective_from=date(2025, 1, 1)),
            Tariff(service_id=services[1].id, price_per_unit=215.54, effective_from=date(2025, 1, 1)),
            Tariff(service_id=services[2].id, price_per_unit=6.73, effective_from=date(2025, 1, 1)),
            Tariff(service_id=services[3].id, price_per_unit=7.19, effective_from=date(2025, 1, 1)),
            Tariff(service_id=services[4].id, price_per_unit=2546.83, effective_from=date(2025, 1, 1)),
        ]
        session.add_all(tariffs)

        # Seed admin user (password: admin123)
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Администратор",
            role=UserRole.ADMIN,
        )
        session.add(admin)

        await session.commit()
        print("Seed data created successfully.")
