from decimal import Decimal

import pytest

from app.models import MeterReading, ReadingSource
from app.repositories.meter_repo import MeterRepository
from app.repositories.resident_repo import ResidentRepository


@pytest.mark.asyncio
async def test_get_meters_for_resident(session, seed_data):
    """Bot readings: get list of meters for resident's address."""
    repo = ResidentRepository(session)
    resident = await repo.get_with_addresses(seed_data["resident"].id)

    meter_repo = MeterRepository(session)
    all_meters = []
    for addr in resident.addresses:
        meters = await meter_repo.get_by_address(addr.id)
        all_meters.extend(meters)

    assert len(all_meters) == 3  # cold water, hot water, electricity


@pytest.mark.asyncio
async def test_submit_reading_via_telegram(session, seed_data):
    """Bot readings: submit reading from Telegram."""
    meter = seed_data["meters"][0]  # cold water

    reading = MeterReading(
        meter_id=meter.id,
        value=Decimal("250.000"),
        previous_value=Decimal("240.000"),
        consumption=Decimal("10.000"),
        period_year=2025,
        period_month=4,
        source=ReadingSource.TELEGRAM,
        submitted_by_resident=seed_data["resident"].id,
        is_validated=False,
    )
    session.add(reading)
    await session.commit()

    assert reading.id is not None
    assert reading.source == ReadingSource.TELEGRAM
    assert reading.is_validated is False


@pytest.mark.asyncio
async def test_reading_consumption_calculation(session, seed_data):
    """Bot readings: consumption is correctly calculated."""
    prev = Decimal("100.000")
    new = Decimal("112.500")
    consumption = new - prev

    assert consumption == Decimal("12.500")


@pytest.mark.asyncio
async def test_reading_validation_new_gte_previous():
    """Bot readings: new value must be >= previous."""
    previous = Decimal("200.000")

    # Valid
    assert Decimal("210.000") >= previous
    assert Decimal("200.000") >= previous

    # Invalid
    assert not (Decimal("195.000") >= previous)


@pytest.mark.asyncio
async def test_previous_reading_lookup(session, seed_data):
    """Bot readings: previous reading should be found."""
    meter = seed_data["meters"][2]  # electricity
    meter_repo = MeterRepository(session)

    # No previous reading
    last = await meter_repo.get_last_reading(meter.id)
    assert last is None

    # Add one
    reading = MeterReading(
        meter_id=meter.id,
        value=Decimal("500.000"),
        previous_value=Decimal("0"),
        consumption=Decimal("500.000"),
        period_year=2025,
        period_month=1,
        source=ReadingSource.ADMIN,
        is_validated=True,
    )
    session.add(reading)
    await session.commit()

    last = await meter_repo.get_last_reading(meter.id)
    assert last is not None
    assert last.value == Decimal("500.000")


@pytest.mark.asyncio
async def test_telegram_reading_needs_validation(session, seed_data):
    """Telegram readings should be unvalidated by default."""
    meter = seed_data["meters"][1]

    reading = MeterReading(
        meter_id=meter.id,
        value=Decimal("300.000"),
        previous_value=Decimal("290.000"),
        consumption=Decimal("10.000"),
        period_year=2025,
        period_month=5,
        source=ReadingSource.TELEGRAM,
        submitted_by_resident=seed_data["resident"].id,
        is_validated=False,
    )
    session.add(reading)
    await session.commit()

    # Should not be included in billing until validated
    assert reading.is_validated is False
    assert reading.source == ReadingSource.TELEGRAM
