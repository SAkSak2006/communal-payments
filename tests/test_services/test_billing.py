from decimal import Decimal

import pytest
import pytest_asyncio

from app.models import MeterReading, ReadingSource, Charge
from app.services.billing_service import calculate_charges_for_period, get_active_tariff


@pytest.mark.asyncio
async def test_get_active_tariff(session, seed_data):
    """Active tariff should be returned for each service."""
    tariff = await get_active_tariff(session, seed_data["services"][0].id)
    assert tariff is not None
    assert tariff.price_per_unit == Decimal("42.30")
    assert tariff.effective_to is None


@pytest.mark.asyncio
async def test_calculate_charges_with_readings(session, seed_data):
    """Charges should be calculated when validated readings exist."""
    meter = seed_data["meters"][0]  # cold water
    period = seed_data["period"]

    # Add validated reading
    reading = MeterReading(
        meter_id=meter.id,
        value=Decimal("150.000"),
        previous_value=Decimal("140.000"),
        consumption=Decimal("10.000"),
        period_year=period.year,
        period_month=period.month,
        source=ReadingSource.ADMIN,
        is_validated=True,
    )
    session.add(reading)
    await session.commit()

    stats = await calculate_charges_for_period(session, period.id)

    assert stats["created"] >= 1
    assert "error" not in stats

    # Check charge was created correctly
    from sqlalchemy import select
    result = await session.execute(
        select(Charge).where(
            Charge.address_id == seed_data["address"].id,
            Charge.service_id == seed_data["services"][0].id,
            Charge.period_id == period.id,
        )
    )
    charge = result.scalar_one_or_none()
    assert charge is not None
    assert charge.consumption == Decimal("10.000")
    # 10 * 42.30 = 423.00
    assert charge.amount == Decimal("423.00")


@pytest.mark.asyncio
async def test_calculate_charges_heating_by_area(session, seed_data):
    """Heating charges should be calculated by area (no meter)."""
    period = seed_data["period"]
    heating_service = seed_data["services"][3]  # heating

    stats = await calculate_charges_for_period(session, period.id)

    from sqlalchemy import select
    result = await session.execute(
        select(Charge).where(
            Charge.address_id == seed_data["address"].id,
            Charge.service_id == heating_service.id,
            Charge.period_id == period.id,
        )
    )
    charge = result.scalar_one_or_none()
    assert charge is not None
    # area 54.5 * 2546.83 = 138,802.24
    expected = (Decimal("54.5") * Decimal("2546.83")).quantize(Decimal("0.01"))
    assert charge.amount == expected
    assert charge.consumption == Decimal("54.5")


@pytest.mark.asyncio
async def test_calculate_charges_skips_without_reading(session, seed_data):
    """Charges with meters should be skipped if no validated reading."""
    period = seed_data["period"]

    # No readings added — metered services should be skipped
    stats = await calculate_charges_for_period(session, period.id)

    # Only heating (no meter) should be created
    # Metered services without readings are skipped
    assert stats["skipped"] >= 3


@pytest.mark.asyncio
async def test_calculate_charges_no_duplicates(session, seed_data):
    """Running calculation twice should not create duplicate charges."""
    period = seed_data["period"]

    stats1 = await calculate_charges_for_period(session, period.id)
    stats2 = await calculate_charges_for_period(session, period.id)

    # Second run should skip everything
    assert stats2["created"] == 0
    assert stats2["skipped"] >= stats1["created"]


@pytest.mark.asyncio
async def test_closed_period_not_calculated(session, seed_data):
    """Closed periods should not be recalculated."""
    period = seed_data["period"]
    period.is_closed = True
    await session.commit()

    stats = await calculate_charges_for_period(session, period.id)

    assert stats["created"] == 0
    assert stats.get("error") == "Period is closed"
