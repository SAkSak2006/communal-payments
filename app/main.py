from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.admin.router import router as admin_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run seed data
    from app.utils.seed import seed_initial_data
    await seed_initial_data()

    # Startup: start Telegram bot polling
    if settings.BOT_TOKEN:
        from app.bot.bot import start_bot
        await start_bot()

    # Startup: start scheduler (reminders)
    from app.utils.scheduler import start_scheduler
    start_scheduler()

    yield

    # Shutdown: stop scheduler
    from app.utils.scheduler import stop_scheduler
    stop_scheduler()

    # Shutdown: stop Telegram bot
    if settings.BOT_TOKEN:
        from app.bot.bot import stop_bot
        await stop_bot()


app = FastAPI(
    title="Платформа учёта коммунальных платежей",
    description="Система учёта ЖКУ с Telegram-ботом",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Admin panel routes
app.include_router(admin_router)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/")
