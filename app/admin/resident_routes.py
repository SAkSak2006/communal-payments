from decimal import Decimal

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import User, Resident, Address, Payment, Charge
from app.admin.dependencies import get_current_user
from app.repositories.resident_repo import ResidentRepository
from app.repositories.payment_repo import PaymentRepository

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def residents_list(
    request: Request,
    q: str = "",
    page: int = 1,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = ResidentRepository(session)
    per_page = 20

    if q:
        residents = await repo.search(q)
        total_count = len(residents)
    else:
        total_count = await repo.count()
        offset = (page - 1) * per_page
        residents = await repo.get_all(offset=offset, limit=per_page)

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    query_params = f"q={q}" if q else ""

    return templates.TemplateResponse("residents/list.html", {
        "request": request, "user": user, "active": "residents",
        "residents": residents, "q": q,
        "page": page, "total_pages": total_pages, "total_count": total_count,
        "per_page": per_page, "offset": (page - 1) * per_page,
        "query_params": query_params,
    })


@router.get("/create", response_class=HTMLResponse)
async def resident_create_form(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse("residents/form.html", {
        "request": request, "user": user, "active": "residents",
        "resident": None, "address": None,
    })


@router.post("/create")
async def resident_create(
    request: Request,
    full_name: str = Form(...),
    personal_account: str = Form(...),
    phone: str = Form(...),
    is_verified: str = Form("false"),
    city: str = Form(...),
    street: str = Form(...),
    building: str = Form(...),
    apartment: str = Form(...),
    area_sqm: float = Form(0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    resident = Resident(
        full_name=full_name,
        personal_account=personal_account,
        phone=phone,
        is_verified=is_verified == "true",
    )
    session.add(resident)
    await session.flush()

    address = Address(
        city=city, street=street, building=building, apartment=apartment,
        area_sqm=Decimal(str(area_sqm)), resident_id=resident.id,
    )
    session.add(address)
    await session.commit()

    return RedirectResponse(url=f"/admin/residents/{resident.id}", status_code=302)


@router.get("/{resident_id}", response_class=HTMLResponse)
async def resident_detail(
    request: Request,
    resident_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = ResidentRepository(session)
    resident = await repo.get_with_addresses(resident_id)
    if not resident:
        return RedirectResponse(url="/admin/residents", status_code=302)

    payment_repo = PaymentRepository(session)
    total_paid = await payment_repo.get_total_paid(resident_id)
    total_charged = await payment_repo.get_total_charged(resident_id)
    debt = max(Decimal("0"), total_charged - total_paid)

    recent_payments = await payment_repo.get_by_resident(resident_id, limit=10)

    return templates.TemplateResponse("residents/detail.html", {
        "request": request, "user": user, "active": "residents",
        "resident": resident,
        "addresses": resident.addresses,
        "debt": debt,
        "recent_payments": recent_payments,
    })


@router.get("/{resident_id}/edit", response_class=HTMLResponse)
async def resident_edit_form(
    request: Request,
    resident_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    resident = await session.get(Resident, resident_id)
    if not resident:
        return RedirectResponse(url="/admin/residents", status_code=302)

    result = await session.execute(
        select(Address).where(Address.resident_id == resident_id).limit(1)
    )
    address = result.scalar_one_or_none()

    return templates.TemplateResponse("residents/form.html", {
        "request": request, "user": user, "active": "residents",
        "resident": resident, "address": address,
    })


@router.post("/{resident_id}/edit")
async def resident_edit(
    request: Request,
    resident_id: int,
    full_name: str = Form(...),
    personal_account: str = Form(...),
    phone: str = Form(...),
    is_verified: str = Form("false"),
    city: str = Form(...),
    street: str = Form(...),
    building: str = Form(...),
    apartment: str = Form(...),
    area_sqm: float = Form(0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    resident = await session.get(Resident, resident_id)
    if not resident:
        return RedirectResponse(url="/admin/residents", status_code=302)

    resident.full_name = full_name
    resident.personal_account = personal_account
    resident.phone = phone
    resident.is_verified = is_verified == "true"

    result = await session.execute(
        select(Address).where(Address.resident_id == resident_id).limit(1)
    )
    address = result.scalar_one_or_none()
    if address:
        address.city = city
        address.street = street
        address.building = building
        address.apartment = apartment
        address.area_sqm = Decimal(str(area_sqm))

    await session.commit()
    return RedirectResponse(url=f"/admin/residents/{resident_id}", status_code=302)
