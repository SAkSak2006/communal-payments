from datetime import date, datetime, timezone
from decimal import Decimal
import math

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, Payment, Resident, PaymentPeriod, Charge, Address
from app.admin.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PER_PAGE = 20


@router.get("/", response_class=HTMLResponse)
async def payments_list(
    request: Request,
    page: int = 1,
    q: str = "",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(Payment, Resident.full_name, Resident.personal_account)
        .join(Resident, Resident.id == Payment.resident_id)
    )

    if q:
        query = query.where(
            Resident.full_name.ilike(f"%{q}%")
            | Resident.personal_account.ilike(f"%{q}%")
        )

    # Count total
    count_query = select(func.count()).select_from(Payment)
    if q:
        count_query = (
            select(func.count())
            .select_from(Payment)
            .join(Resident, Resident.id == Payment.resident_id)
            .where(
                Resident.full_name.ilike(f"%{q}%")
                | Resident.personal_account.ilike(f"%{q}%")
            )
        )
    res = await session.execute(count_query)
    total_count = res.scalar_one()
    total_pages = max(1, math.ceil(total_count / PER_PAGE))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PER_PAGE

    result = await session.execute(
        query.order_by(Payment.payment_date.desc())
        .offset(offset).limit(PER_PAGE)
    )

    payments = []
    for payment, res_name, account in result.all():
        payments.append({
            "id": payment.id,
            "payment_date": payment.payment_date,
            "resident_name": res_name,
            "personal_account": account,
            "amount": payment.amount,
            "payment_method": payment.payment_method,
            "receipt_number": payment.receipt_number,
        })

    return templates.TemplateResponse("payments/list.html", {
        "request": request, "user": user, "active": "payments",
        "payments": payments, "q": q,
        "page": page, "total_pages": total_pages,
        "total_count": total_count, "offset": offset, "per_page": PER_PAGE,
        "query_params": f"q={q}" if q else "",
    })


@router.get("/create", response_class=HTMLResponse)
async def payment_create_form(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Resident).order_by(Resident.full_name)
    )
    residents_raw = result.scalars().all()

    # Calculate debt for each resident
    residents = []
    for r in residents_raw:
        res_charged = await session.execute(
            select(func.coalesce(func.sum(Charge.amount), 0))
            .join(Address, Address.id == Charge.address_id)
            .where(Address.resident_id == r.id)
        )
        charged = res_charged.scalar_one()

        res_paid = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.resident_id == r.id)
        )
        paid = res_paid.scalar_one()
        debt = max(Decimal("0"), charged - paid)

        residents.append({
            "id": r.id,
            "full_name": r.full_name,
            "personal_account": r.personal_account,
            "debt": debt,
        })

    # Ensure current period exists
    now = datetime.now(timezone.utc)
    result2 = await session.execute(
        select(PaymentPeriod).where(
            PaymentPeriod.year == now.year,
            PaymentPeriod.month == now.month,
        )
    )
    if not result2.scalar_one_or_none():
        session.add(PaymentPeriod(year=now.year, month=now.month))
        await session.commit()

    result3 = await session.execute(
        select(PaymentPeriod).order_by(PaymentPeriod.year.desc(), PaymentPeriod.month.desc())
    )
    periods = result3.scalars().all()

    return templates.TemplateResponse("payments/form.html", {
        "request": request, "user": user, "active": "payments",
        "residents": residents, "periods": periods,
    })


@router.post("/create")
async def payment_create(
    request: Request,
    resident_id: int = Form(...),
    amount: float = Form(...),
    payment_date: date = Form(...),
    period_id: int = Form(...),
    payment_method: str = Form("cash"),
    receipt_number: str = Form(None),
    notes: str = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    payment = Payment(
        resident_id=resident_id,
        amount=Decimal(str(amount)),
        payment_date=datetime.combine(payment_date, datetime.min.time()),
        period_id=period_id,
        payment_method=payment_method,
        receipt_number=receipt_number or None,
        notes=notes or None,
        recorded_by=user.id,
    )
    session.add(payment)
    await session.commit()

    return RedirectResponse(url="/admin/payments", status_code=302)
