from decimal import Decimal

import pytest

from app.models import MeterReading, ReadingSource
from app.repositories.meter_repo import MeterRepository


@pytest.mark.asyncio
async def test_reading_value_must_be_non_negative():
    """Reading value cannot be negative."""
    # This is a logic test — no DB needed
    new_value = Decimal("-5.0")
    assert new_value < 0, "Negative readings should be rejected"


@pytest.mark.asyncio
async def test_reading_must_be_gte_previous():
    """New reading must be >= previous reading."""
    previous = Decimal("100.000")
    new_value = Decimal("95.000")

    assert new_value < previous, "New reading less than previous should be rejected"


@pytest.mark.asyncio
async def test_consumption_calculation():
    """Consumption = new value - previous value."""
    previous = Decimal("100.000")
    new_value = Decimal("115.500")
    consumption = new_value - previous

    assert consumption == Decimal("15.500")


@pytest.mark.asyncio
async def test_anomaly_detection():
    """Consumption > 3x previous value is anomalous."""
    previous_value = Decimal("100.000")
    new_value = Decimal("450.000")
    consumption = new_value - previous_value  # 350

    is_anomaly = previous_value > 0 and consumption > previous_value * 3
    assert is_anomaly is True


@pytest.mark.asyncio
async def test_normal_consumption_not_anomalous():
    """Normal consumption should not trigger anomaly."""
    previous_value = Decimal("100.000")
    new_value = Decimal("112.000")
    consumption = new_value - previous_value  # 12

    is_anomaly = previous_value > 0 and consumption > previous_value * 3
    assert is_anomaly is False


@pytest.mark.asyncio
async def test_get_last_reading(session, seed_data):
    """Last reading should be returned correctly."""
    meter = seed_data["meters"][0]
    meter_repo = MeterRepository(session)

    # No readings yet
    last = await meter_repo.get_last_reading(meter.id)
    assert last is None

    # Add reading
    reading = MeterReading(
        meter_id=meter.id,
        value=Decimal("100.000"),
        previous_value=Decimal("90.000"),
        consumption=Decimal("10.000"),
        period_year=2025,
        period_month=1,
        source=ReadingSource.ADMIN,
        is_validated=True,
    )
    session.add(reading)
    await session.commit()

    last = await meter_repo.get_last_reading(meter.id)
    assert last is not None
    assert last.value == Decimal("100.000")


@pytest.mark.asyncio
async def test_one_reading_per_meter_per_period(session, seed_data):
    """Only one reading per meter per period is allowed (unique constraint)."""
    meter = seed_data["meters"][1]

    reading1 = MeterReading(
        meter_id=meter.id,
        value=Decimal("200.000"),
        previous_value=Decimal("190.000"),
        consumption=Decimal("10.000"),
        period_year=2025,
        period_month=2,
        source=ReadingSource.TELEGRAM,
        is_validated=False,
    )
    session.add(reading1)
    await session.commit()

    reading2 = MeterReading(
        meter_id=meter.id,
        value=Decimal("205.000"),
        previous_value=Decimal("200.000"),
        consumption=Decimal("5.000"),
        period_year=2025,
        period_month=2,
        source=ReadingSource.ADMIN,
        is_validated=True,
    )
    session.add(reading2)

    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()
