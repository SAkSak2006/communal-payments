from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    User, Resident, MeterReading, Charge, Payment, Address,
    Tariff, UtilityService,
)
from app.admin.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)

    # Residents count
    res = await session.execute(select(func.count()).select_from(Resident))
    residents_count = res.scalar_one()

    # Readings this month
    res = await session.execute(
        select(func.count()).select_from(MeterReading).where(
            MeterReading.period_year == now.year,
            MeterReading.period_month == now.month,
        )
    )
    readings_count = res.scalar_one()

    # Total debt = sum(charges) - sum(payments)
    res = await session.execute(
        select(func.coalesce(func.sum(Charge.amount), 0))
    )
    total_charged = res.scalar_one()

    res = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
    )
    total_paid = res.scalar_one()
    total_debt = max(Decimal("0"), total_charged - total_paid)

    # Payments this month
    res = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            func.extract("year", Payment.payment_date) == now.year,
            func.extract("month", Payment.payment_date) == now.month,
        )
    )
    payments_month = res.scalar_one()

    stats = {
        "residents_count": residents_count,
        "readings_count": readings_count,
        "total_debt": total_debt,
        "payments_month": payments_month,
    }

    # Unvalidated readings
    res = await session.execute(
        select(
            MeterReading,
            Resident.full_name.label("resident_name"),
            UtilityService.name.label("service_name"),
        )
        .join(MeterReading.meter)
        .join(Address, Address.id == MeterReading.meter.property.mapper.class_.address_id)
        .join(Resident, Resident.id == Address.resident_id)
        .join(UtilityService, UtilityService.id == MeterReading.meter.property.mapper.class_.service_id)
        .where(MeterReading.is_validated.is_(False))
        .order_by(MeterReading.reading_date.desc())
        .limit(10)
    )
    # Simplified query - join through Meter table
    unvalidated_readings = []
    try:
        from app.models import Meter
        res2 = await session.execute(
            select(MeterReading)
            .where(MeterReading.is_validated.is_(False))
            .order_by(MeterReading.reading_date.desc())
            .limit(10)
        )
        for reading in res2.scalars().all():
            meter = await session.get(Meter, reading.meter_id)
            if meter:
                address = await session.get(Address, meter.address_id)
                service = await session.get(UtilityService, meter.service_id)
                resident = await session.get(Resident, address.resident_id) if address else None
                unvalidated_readings.append({
                    "id": reading.id,
                    "reading_date": reading.reading_date,
                    "resident_name": resident.full_name if resident else "—",
                    "service_name": service.name if service else "—",
                    "value": reading.value,
                    "consumption": reading.consumption,
                    "source": reading.source.value,
                })
    except Exception:
        pass

    # Current tariffs
    current_tariffs = []
    res3 = await session.execute(
        select(Tariff, UtilityService.name, UtilityService.unit)
        .join(UtilityService, UtilityService.id == Tariff.service_id)
        .where(Tariff.effective_to.is_(None))
        .order_by(UtilityService.name)
    )
    for tariff, svc_name, svc_unit in res3.all():
        current_tariffs.append({
            "service_name": svc_name,
            "price_per_unit": tariff.price_per_unit,
            "unit": svc_unit,
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "active": "dashboard",
        "stats": stats,
        "unvalidated_readings": unvalidated_readings,
        "current_tariffs": current_tariffs,
    })
