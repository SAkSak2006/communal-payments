from fastapi import APIRouter

from app.admin import auth_routes, dashboard_routes, resident_routes
from app.admin import tariff_routes, meter_routes, reading_routes, payment_routes
from app.admin import charge_routes, report_routes, import_routes

router = APIRouter(prefix="/admin")

# Auth (no prefix — login/logout)
router.include_router(auth_routes.router, tags=["auth"])

# Dashboard
router.include_router(dashboard_routes.router, tags=["dashboard"])

# CRUD modules
router.include_router(resident_routes.router, prefix="/residents", tags=["residents"])
router.include_router(tariff_routes.router, prefix="/tariffs", tags=["tariffs"])
router.include_router(meter_routes.router, prefix="/meters", tags=["meters"])
router.include_router(reading_routes.router, prefix="/readings", tags=["readings"])
router.include_router(payment_routes.router, prefix="/payments", tags=["payments"])
router.include_router(charge_routes.router, prefix="/charges", tags=["charges"])
router.include_router(report_routes.router, prefix="/reports", tags=["reports"])
router.include_router(import_routes.router, prefix="/import", tags=["import"])
