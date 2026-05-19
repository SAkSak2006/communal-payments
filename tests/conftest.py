import asyncio
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models import (
    User, UserRole, Resident, Address, UtilityService, Tariff,
    Meter, PaymentPeriod,
)
from app.services.auth_service import get_password_hash

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async_sess = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as sess:
        yield sess


@pytest_asyncio.fixture
async def seed_data(session):
    """Create basic test data."""
    # Services
    services = [
        UtilityService(name="Холодное водоснабжение", code="cold_water", unit="куб.м", has_meter=True),
        UtilityService(name="Горячее водоснабжение", code="hot_water", unit="куб.м", has_meter=True),
        UtilityService(name="Электроснабжение", code="electricity", unit="кВт·ч", has_meter=True),
        UtilityService(name="Отопление", code="heating", unit="Гкал", has_meter=False),
    ]
    session.add_all(services)
    await session.flush()

    # Tariffs
    tariffs = [
        Tariff(service_id=services[0].id, price_per_unit=Decimal("42.30"), effective_from=date(2025, 1, 1)),
        Tariff(service_id=services[1].id, price_per_unit=Decimal("215.54"), effective_from=date(2025, 1, 1)),
        Tariff(service_id=services[2].id, price_per_unit=Decimal("6.73"), effective_from=date(2025, 1, 1)),
        Tariff(service_id=services[3].id, price_per_unit=Decimal("2546.83"), effective_from=date(2025, 1, 1)),
    ]
    session.add_all(tariffs)

    # Admin user
    admin = User(
        username="admin", email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Тест Админ", role=UserRole.ADMIN,
    )
    session.add(admin)

    # Resident
    resident = Resident(
        full_name="Иванов Иван Иванович",
        phone="+79001234567",
        personal_account="1001-0001",
        telegram_id=123456789,
        is_verified=True,
    )
    session.add(resident)
    await session.flush()

    # Address
    address = Address(
        city="Москва", street="Ленина", building="10", apartment="42",
        area_sqm=Decimal("54.5"), resident_id=resident.id,
    )
    session.add(address)
    await session.flush()

    # Meters
    meters = [
        Meter(address_id=address.id, service_id=services[0].id, serial_number="CW-001"),
        Meter(address_id=address.id, service_id=services[1].id, serial_number="HW-001"),
        Meter(address_id=address.id, service_id=services[2].id, serial_number="EL-001"),
    ]
    session.add_all(meters)

    # Payment period
    period = PaymentPeriod(year=2025, month=3)
    session.add(period)

    await session.commit()

    return {
        "services": services,
        "tariffs": tariffs,
        "admin": admin,
        "resident": resident,
        "address": address,
        "meters": meters,
        "period": period,
    }
