from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    User, MeterReading, Meter, Address, Resident, UtilityService,
    PaymentPeriod, ReadingSource,
)
from app.admin.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def readings_list(
    request: Request,
    year: int = 0,
    month: int = 0,
    validated: str = "",
    q: str = "",
    page: int = 1,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import func, distinct

    per_page = 20

    # Get available years for dropdown
    years_result = await session.execute(
        select(distinct(MeterReading.period_year)).order_by(MeterReading.period_year.desc())
    )
    available_years = [r[0] for r in years_result.all()]

    # If no year selected and we have data, default to 0 (all)
    # But on first visit default to current year
    if year is None:
        year = 0

    # Build base filters
    filters = []
    if year and year != 0:
        filters.append(MeterReading.period_year == year)
    if month and month != 0:
        filters.append(MeterReading.period_month == month)
    if validated == "true":
        filters.append(MeterReading.is_validated.is_(True))
    elif validated == "false":
        filters.append(MeterReading.is_validated.is_(False))
    if q:
        filters.append(
            Resident.full_name.ilike(f"%{q}%")
            | Resident.personal_account.ilike(f"%{q}%")
        )

    # Count
    count_q = (
        select(func.count(MeterReading.id))
        .join(Meter, Meter.id == MeterReading.meter_id)
        .join(Address, Address.id == Meter.address_id)
        .join(Resident, Resident.id == Address.resident_id)
        .where(*filters)
    )
    total_count = (await session.execute(count_q)).scalar_one()

    # Data query
    offset = (page - 1) * per_page
    data_q = (
        select(MeterReading, Meter, Address, Resident.full_name, UtilityService.name)
        .join(Meter, Meter.id == MeterReading.meter_id)
        .join(Address, Address.id == Meter.address_id)
        .join(Resident, Resident.id == Address.resident_id)
        .join(UtilityService, UtilityService.id == Meter.service_id)
        .where(*filters)
        .order_by(MeterReading.reading_date.desc())
        .offset(offset).limit(per_page)
    )
    result = await session.execute(data_q)

    readings = []
    for reading, meter, addr, res_name, svc_name in result.all():
        readings.append({
            "id": reading.id,
            "reading_date": reading.reading_date,
            "resident_name": res_name,
            "address_str": f"ул. {addr.street}, д. {addr.building}, кв. {addr.apartment}",
            "service_name": svc_name,
            "previous_value": reading.previous_value,
            "value": reading.value,
            "consumption": reading.consumption,
            "source": reading.source.value,
            "is_validated": reading.is_validated,
        })

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    query_params = f"year={year}&month={month}&validated={validated}&q={q}"

    return templates.TemplateResponse("readings/list.html", {
        "request": request, "user": user, "active": "readings",
        "readings": readings, "year": year, "month": month,
        "validated": validated, "q": q,
        "available_years": available_years,
        "page": page, "total_pages": total_pages, "total_count": total_count,
        "per_page": per_page, "offset": offset, "query_params": query_params,
    })


@router.get("/{reading_id}/validate")
async def validate_reading(
    reading_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    reading = await session.get(MeterReading, reading_id)
    if reading:
        reading.is_validated = True
        await session.commit()

    return RedirectResponse(url="/admin/readings", status_code=302)


@router.get("/{reading_id}/reject")
async def reject_reading(
    reading_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    reading = await session.get(MeterReading, reading_id)
    if reading:
        await session.delete(reading)
        await session.commit()

    return RedirectResponse(url="/admin/readings", status_code=302)


@router.get("/create", response_class=HTMLResponse)
async def create_reading_form(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Получаем все счётчики с JOIN-ами
    meters_q = (
        select(Meter, Address, UtilityService, Resident)
        .join(Address, Address.id == Meter.address_id)
        .join(UtilityService, UtilityService.id == Meter.service_id)
        .outerjoin(Resident, Resident.id == Address.resident_id)
        .order_by(Resident.full_name)
    )
    meters_result = await session.execute(meters_q)

    meters = []
    for meter, addr, svc, resident in meters_result.all():
        # Последнее показание для счётчика
        last_reading_q = (
            select(MeterReading.value)
            .where(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        last_val_row = (await session.execute(last_reading_q)).scalar_one_or_none()
        last_value = last_val_row if last_val_row is not None else Decimal("0")

        res_name = resident.full_name if resident else "—"
        display = f"{res_name} — ул. {addr.street}, д. {addr.building}, кв. {addr.apartment} — {svc.name}"
        meters.append({
            "id": meter.id,
            "display": display,
            "last_value": last_value,
        })

    # Получаем периоды
    periods_q = (
        select(PaymentPeriod)
        .order_by(PaymentPeriod.year.desc(), PaymentPeriod.month.desc())
    )
    periods_result = await session.execute(periods_q)
    periods = periods_result.scalars().all()

    return templates.TemplateResponse("readings/form.html", {
        "request": request,
        "user": user,
        "active": "readings",
        "meters": meters,
        "periods": periods,
    })


@router.post("/create")
async def create_reading_save(
    request: Request,
    meter_id: int = Form(...),
    value: str = Form(...),
    period_year: int = Form(...),
    period_month: int = Form(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Парсим значение (допускаем запятую как разделитель)
    value_decimal = Decimal(value.replace(",", "."))

    # Валидация диапазона
    if value_decimal <= 0 or value_decimal > Decimal("999999999"):
        return RedirectResponse(url="/admin/readings/create", status_code=302)

    # Ищем существующее показание за этот период
    existing_q = (
        select(MeterReading)
        .where(
            MeterReading.meter_id == meter_id,
            MeterReading.period_year == period_year,
            MeterReading.period_month == period_month,
        )
    )
    existing = (await session.execute(existing_q)).scalar_one_or_none()

    # Последнее показание для расчёта consumption
    last_reading_q = (
        select(MeterReading.value)
        .where(MeterReading.meter_id == meter_id)
        .order_by(MeterReading.reading_date.desc())
        .limit(1)
    )
    if existing:
        # Для обновления берём previous_value существующей записи
        previous_value = existing.previous_value
    else:
        prev_val_row = (await session.execute(last_reading_q)).scalar_one_or_none()
        previous_value = prev_val_row if prev_val_row is not None else Decimal("0")

    consumption = value_decimal - previous_value

    if existing:
        existing.value = value_decimal
        existing.consumption = consumption
        existing.source = ReadingSource.ADMIN
        existing.submitted_by_admin = user.id
        existing.is_validated = True
    else:
        new_reading = MeterReading(
            meter_id=meter_id,
            value=value_decimal,
            previous_value=previous_value,
            consumption=consumption,
            period_year=period_year,
            period_month=period_month,
            source=ReadingSource.ADMIN,
            submitted_by_admin=user.id,
            is_validated=True,
        )
        session.add(new_reading)

    await session.commit()
    return RedirectResponse(url="/admin/readings", status_code=302)
