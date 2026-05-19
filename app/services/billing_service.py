from decimal import Decimal
from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Address, Meter, MeterReading, Tariff, UtilityService,
    Charge, PaymentPeriod,
)


async def get_active_tariff(
    session: AsyncSession, service_id: int
) -> Tariff | None:
    result = await session.execute(
        select(Tariff).where(
            Tariff.service_id == service_id,
            Tariff.effective_to.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def calculate_charges_for_period(
    session: AsyncSession, period_id: int
) -> Dict[str, int]:
    """Calculate charges for all addresses in a given period.
    Returns stats: {'created': N, 'skipped': N}
    """
    period = await session.get(PaymentPeriod, period_id)
    if not period:
        return {"created": 0, "skipped": 0, "error": "Period not found"}

    if period.is_closed:
        return {"created": 0, "skipped": 0, "error": "Period is closed"}

    # Get all addresses
    result = await session.execute(select(Address))
    addresses = result.scalars().all()

    # Get all services
    result = await session.execute(select(UtilityService))
    services = result.scalars().all()

    created = 0
    skipped = 0

    for address in addresses:
        for service in services:
            # Check if charge already exists
            existing = await session.execute(
                select(Charge).where(
                    Charge.address_id == address.id,
                    Charge.service_id == service.id,
                    Charge.period_id == period_id,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            # Get active tariff
            tariff = await get_active_tariff(session, service.id)
            if not tariff:
                skipped += 1
                continue

            consumption = Decimal("0")
            reading_id = None

            if service.has_meter:
                # Find meter for this address + service
                meter_result = await session.execute(
                    select(Meter).where(
                        Meter.address_id == address.id,
                        Meter.service_id == service.id,
                        Meter.is_active.is_(True),
                    )
                )
                meter = meter_result.scalar_one_or_none()

                if not meter:
                    skipped += 1
                    continue

                # Find validated reading for this period
                reading_result = await session.execute(
                    select(MeterReading).where(
                        MeterReading.meter_id == meter.id,
                        MeterReading.period_year == period.year,
                        MeterReading.period_month == period.month,
                        MeterReading.is_validated.is_(True),
                    )
                )
                reading = reading_result.scalar_one_or_none()

                if not reading:
                    skipped += 1
                    continue

                consumption = reading.consumption
                reading_id = reading.id
            else:
                # No meter (e.g. heating) — calculate by area
                consumption = address.area_sqm

            amount = (consumption * tariff.price_per_unit).quantize(Decimal("0.01"))

            charge = Charge(
                address_id=address.id,
                service_id=service.id,
                period_id=period_id,
                reading_id=reading_id,
                tariff_id=tariff.id,
                consumption=consumption,
                amount=amount,
            )
            session.add(charge)
            created += 1

    await session.commit()
    return {"created": created, "skipped": skipped}


async def get_charges_for_period(
    session: AsyncSession, period_id: int
) -> List[Dict]:
    """Get all charges for a period with details."""
    from app.models import Resident

    result = await session.execute(
        select(
            Charge,
            Address,
            UtilityService.name,
            UtilityService.unit,
            Resident.full_name,
            Resident.personal_account,
            Resident.id,
        )
        .join(Address, Address.id == Charge.address_id)
        .join(Resident, Resident.id == Address.resident_id)
        .join(UtilityService, UtilityService.id == Charge.service_id)
        .where(Charge.period_id == period_id)
        .order_by(Resident.full_name, UtilityService.name)
    )

    charges = []
    for charge, addr, svc_name, svc_unit, res_name, account, res_id in result.all():
        charges.append({
            "id": charge.id,
            "resident_id": res_id,
            "resident_name": res_name,
            "personal_account": account,
            "address": f"ул. {addr.street}, д. {addr.building}, кв. {addr.apartment}",
            "service_name": svc_name,
            "unit": svc_unit,
            "consumption": charge.consumption,
            "amount": charge.amount,
        })

    return charges
