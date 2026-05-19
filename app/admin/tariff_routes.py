from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, Tariff, UtilityService
from app.admin.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def tariffs_list(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Tariff, UtilityService.name, UtilityService.unit)
        .join(UtilityService, UtilityService.id == Tariff.service_id)
        .order_by(UtilityService.name, Tariff.effective_from.desc())
    )

    tariffs_by_service = defaultdict(list)
    for tariff, svc_name, svc_unit in result.all():
        tariffs_by_service[svc_name].append({
            "id": tariff.id,
            "price_per_unit": tariff.price_per_unit,
            "unit": svc_unit,
            "effective_from": tariff.effective_from,
            "effective_to": tariff.effective_to,
        })

    return templates.TemplateResponse("tariffs/list.html", {
        "request": request, "user": user, "active": "tariffs",
        "tariffs_by_service": dict(tariffs_by_service),
    })


@router.get("/create", response_class=HTMLResponse)
async def tariff_create_form(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(UtilityService).order_by(UtilityService.name))
    services = result.scalars().all()

    return templates.TemplateResponse("tariffs/form.html", {
        "request": request, "user": user, "active": "tariffs",
        "services": services,
    })


@router.post("/create")
async def tariff_create(
    request: Request,
    service_id: int = Form(...),
    price_per_unit: float = Form(...),
    effective_from: date = Form(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Auto-close previous active tariff for this service
    result = await session.execute(
        select(Tariff).where(
            Tariff.service_id == service_id,
            Tariff.effective_to.is_(None),
        )
    )
    old_tariff = result.scalar_one_or_none()
    if old_tariff:
        old_tariff.effective_to = effective_from - timedelta(days=1)

    new_tariff = Tariff(
        service_id=service_id,
        price_per_unit=Decimal(str(price_per_unit)),
        effective_from=effective_from,
        created_by=user.id,
    )
    session.add(new_tariff)
    await session.commit()

    return RedirectResponse(url="/admin/tariffs", status_code=302)
