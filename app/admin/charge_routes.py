from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, PaymentPeriod, Resident, Address, Charge, Payment, Tariff, UtilityService
from app.admin.dependencies import get_current_user, require_admin
from app.services.billing_service import calculate_charges_for_period, get_charges_for_period

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def _ensure_period(session: AsyncSession, year: int, month: int) -> PaymentPeriod:
    result = await session.execute(
        select(PaymentPeriod).where(
            PaymentPeriod.year == year,
            PaymentPeriod.month == month,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        period = PaymentPeriod(year=year, month=month)
        session.add(period)
        await session.commit()
        await session.refresh(period)
    return period


@router.get("/", response_class=HTMLResponse)
async def charges_list(
    request: Request,
    year: int = None,
    month: int = None,
    message: str = "",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    if not year:
        year = now.year
    if not month:
        month = now.month

    period = await _ensure_period(session, year, month)
    charges = await get_charges_for_period(session, period.id)

    total_amount = sum(c["amount"] for c in charges)

    return templates.TemplateResponse("charges/list.html", {
        "request": request, "user": user, "active": "charges",
        "charges": charges, "year": year, "month": month,
        "period": period, "total_amount": total_amount,
        "message": message,
    })


@router.get("/calculate")
async def calculate_charges(
    year: int,
    month: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    period = await _ensure_period(session, year, month)
    stats = await calculate_charges_for_period(session, period.id)

    error = stats.get("error", "")
    if error:
        msg = f"Ошибка: {error}"
    else:
        msg = f"Рассчитано: {stats['created']} начислений, пропущено: {stats['skipped']}"

    return RedirectResponse(
        url=f"/admin/charges?year={year}&month={month}&message={msg}",
        status_code=302,
    )


@router.get("/close")
async def close_period(
    year: int,
    month: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    period = await _ensure_period(session, year, month)

    # Auto-calculate charges before closing
    stats = await calculate_charges_for_period(session, period.id)

    period.is_closed = True
    period.closed_at = datetime.utcnow()
    period.closed_by = user.id
    await session.commit()

    msg = f"Период закрыт. Авторасчёт: {stats.get('created', 0)} начислений создано"
    return RedirectResponse(
        url=f"/admin/charges?year={year}&month={month}&message={msg}",
        status_code=302,
    )


@router.get("/notify")
async def notify_residents(
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from app.bot.bot import bot
    from app.services.notification_service import send_period_charges_notification

    if not bot:
        msg = "Бот не запущен — уведомления не отправлены"
    else:
        sent = await send_period_charges_notification(session, bot, year, month)
        msg = f"Уведомления отправлены: {sent} жильцов"

    return RedirectResponse(
        url=f"/admin/charges?year={year}&month={month}&message={msg}",
        status_code=302,
    )


@router.get("/receipt/{resident_id}")
async def generate_receipt(
    resident_id: int,
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate PDF receipt for a resident."""
    from app.utils.pdf import generate_receipt_pdf
    from app.repositories.payment_repo import PaymentRepository

    resident = await session.get(Resident, resident_id)
    if not resident:
        return RedirectResponse(url="/admin/charges", status_code=302)

    period = await _ensure_period(session, year, month)

    # Get address
    res = await session.execute(
        select(Address).where(Address.resident_id == resident_id).limit(1)
    )
    addr = res.scalar_one_or_none()
    address_str = f"{addr.city}, ул. {addr.street}, д. {addr.building}, кв. {addr.apartment}" if addr else ""

    # Get charges for this resident in this period
    res = await session.execute(
        select(Charge, UtilityService.name, UtilityService.unit, Tariff.price_per_unit)
        .join(UtilityService, UtilityService.id == Charge.service_id)
        .join(Tariff, Tariff.id == Charge.tariff_id)
        .join(Address, Address.id == Charge.address_id)
        .where(
            Address.resident_id == resident_id,
            Charge.period_id == period.id,
        )
        .order_by(UtilityService.name)
    )

    charges = []
    total_charged = Decimal("0")
    for charge, svc_name, svc_unit, tariff_price in res.all():
        charges.append({
            "service_name": svc_name,
            "unit": svc_unit,
            "consumption": charge.consumption,
            "tariff_price": tariff_price,
            "amount": charge.amount,
        })
        total_charged += charge.amount

    # Get payments for this period
    res = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.resident_id == resident_id,
            Payment.period_id == period.id,
        )
    )
    total_paid = res.scalar_one()
    debt = max(Decimal("0"), total_charged - total_paid)

    pdf = generate_receipt_pdf(
        resident_name=resident.full_name,
        personal_account=resident.personal_account,
        address=address_str,
        period=f"{month:02d}.{year}",
        charges=charges,
        total_charged=total_charged,
        total_paid=total_paid,
        debt=debt,
    )

    filename = f"kvitanciya_{resident.personal_account}_{year}_{month:02d}.pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
