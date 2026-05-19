from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, PaymentPeriod
from app.admin.dependencies import get_current_user
from app.services.billing_service import get_charges_for_period
from app.services.report_service import report_by_period, debtors_report
from app.utils.excel import export_charges_to_excel, export_debtors_to_excel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def reports_index(
    request: Request,
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    return templates.TemplateResponse("reports/index.html", {
        "request": request, "user": user, "active": "reports",
        "year": now.year, "month": now.month,
    })


@router.get("/period", response_class=HTMLResponse)
async def period_report(
    request: Request,
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PaymentPeriod).where(
            PaymentPeriod.year == year, PaymentPeriod.month == month
        )
    )
    period = result.scalar_one_or_none()

    report = {"by_service": [], "total_charged": 0, "total_paid": 0, "debt": 0}
    if period:
        report = await report_by_period(session, period.id)

    return templates.TemplateResponse("reports/period.html", {
        "request": request, "user": user, "active": "reports",
        "report": report, "year": year, "month": month,
    })


@router.get("/debtors", response_class=HTMLResponse)
async def debtors_list(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    debtors = await debtors_report(session)

    return templates.TemplateResponse("reports/debtors.html", {
        "request": request, "user": user, "active": "reports",
        "debtors": debtors,
    })


@router.get("/debtors/excel")
async def debtors_excel(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    debtors = await debtors_report(session)
    output = export_debtors_to_excel(debtors)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=debtors.xlsx"},
    )


@router.get("/export")
async def export_charges(
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PaymentPeriod).where(
            PaymentPeriod.year == year, PaymentPeriod.month == month
        )
    )
    period = result.scalar_one_or_none()

    charges = []
    if period:
        charges = await get_charges_for_period(session, period.id)

    output = export_charges_to_excel(charges, year, month)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=charges_{year}_{month:02d}.xlsx"
        },
    )
