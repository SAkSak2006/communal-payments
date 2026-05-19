from datetime import date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, Meter, Address, Resident, UtilityService
from app.admin.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def meters_list(
    request: Request,
    page: int = 1,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import func
    per_page = 20

    total_count = (await session.execute(
        select(func.count(Meter.id))
        .join(Address, Address.id == Meter.address_id)
        .join(Resident, Resident.id == Address.resident_id)
    )).scalar_one()

    offset = (page - 1) * per_page
    result = await session.execute(
        select(Meter, UtilityService.name, Address, Resident.full_name)
        .join(UtilityService, UtilityService.id == Meter.service_id)
        .join(Address, Address.id == Meter.address_id)
        .join(Resident, Resident.id == Address.resident_id)
        .order_by(Meter.id.desc())
        .offset(offset).limit(per_page)
    )

    meters = []
    for meter, svc_name, addr, res_name in result.all():
        meters.append({
            "id": meter.id,
            "serial_number": meter.serial_number,
            "service_name": svc_name,
            "address_str": f"{addr.city}, {addr.street}, д. {addr.building}, кв. {addr.apartment}",
            "installation_date": meter.installation_date,
            "verification_date": meter.verification_date,
            "is_active": meter.is_active,
        })

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    return templates.TemplateResponse("meters/list.html", {
        "request": request, "user": user, "active": "meters",
        "meters": meters,
        "page": page, "total_pages": total_pages, "total_count": total_count,
        "per_page": per_page, "offset": offset, "query_params": "",
    })


@router.get("/create", response_class=HTMLResponse)
async def meter_create_form(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Address, Resident.full_name)
        .join(Resident, Resident.id == Address.resident_id)
        .order_by(Address.city, Address.street)
    )
    addresses = []
    for addr, res_name in result.all():
        addresses.append({
            "id": addr.id,
            "city": addr.city, "street": addr.street,
            "building": addr.building, "apartment": addr.apartment,
            "resident_name": res_name,
        })

    result2 = await session.execute(select(UtilityService).order_by(UtilityService.name))
    services = result2.scalars().all()

    return templates.TemplateResponse("meters/form.html", {
        "request": request, "user": user, "active": "meters",
        "addresses": addresses, "services": services,
    })


@router.post("/create")
async def meter_create(
    request: Request,
    address_id: int = Form(...),
    service_id: int = Form(...),
    serial_number: str = Form(...),
    installation_date: date = Form(None),
    verification_date: date = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    meter = Meter(
        address_id=address_id,
        service_id=service_id,
        serial_number=serial_number,
        installation_date=installation_date,
        verification_date=verification_date,
    )
    session.add(meter)
    await session.commit()

    return RedirectResponse(url="/admin/meters", status_code=302)


@router.get("/{meter_id}/deactivate")
async def meter_deactivate(
    meter_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    meter = await session.get(Meter, meter_id)
    if meter:
        meter.is_active = False
        await session.commit()

    return RedirectResponse(url="/admin/meters", status_code=302)
