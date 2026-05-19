from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.admin.dependencies import get_current_user, require_admin
from app.services.import_service import (
    import_residents_from_excel,
    import_readings_from_excel,
    generate_residents_template,
    generate_readings_template,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class UserInfo:
    """Snapshot of user data that survives session.commit() expiry."""
    def __init__(self, user: User):
        self.id = user.id
        self.full_name = user.full_name
        self.role = user.role


@router.get("/", response_class=HTMLResponse)
async def import_page(
    request: Request,
    user: User = Depends(require_admin),
):
    return templates.TemplateResponse("import.html", {
        "request": request, "user": user, "active": "import",
        "result": None,
    })


@router.post("/residents", response_class=HTMLResponse)
async def import_residents(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    # Snapshot user BEFORE commit expires it
    user_info = UserInfo(user)
    content = await file.read()
    try:
        result = await import_residents_from_excel(session, content)
    except Exception as e:
        try:
            await session.rollback()
        except Exception:
            pass
        result = {"created": 0, "skipped": 0, "errors": [f"Критическая ошибка: {str(e)}"]}

    return templates.TemplateResponse("import.html", {
        "request": request, "user": user_info, "active": "import",
        "result": result,
    })


@router.post("/readings", response_class=HTMLResponse)
async def import_readings(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user_info = UserInfo(user)
    content = await file.read()
    try:
        result = await import_readings_from_excel(session, content)
    except Exception as e:
        try:
            await session.rollback()
        except Exception:
            pass
        result = {"created": 0, "skipped": 0, "errors": [f"Критическая ошибка: {str(e)}"]}

    return templates.TemplateResponse("import.html", {
        "request": request, "user": user_info, "active": "import",
        "result": result,
    })


@router.get("/template/residents")
async def download_residents_template(user: User = Depends(get_current_user)):
    output = generate_residents_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=shablon_zhiteli.xlsx"},
    )


@router.get("/template/readings")
async def download_readings_template(user: User = Depends(get_current_user)):
    output = generate_readings_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=shablon_pokazaniya.xlsx"},
    )
