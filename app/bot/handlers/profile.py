from decimal import Decimal
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from sqlalchemy import select, func

from app.bot.keyboards.reply import main_menu
from app.database import async_session
from app.models import Address, Meter, Charge, Payment, MeterReading
from app.repositories.resident_repo import ResidentRepository
from app.repositories.payment_repo import PaymentRepository

router = Router()

IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "bot_images"


@router.message(Command("profile"))
@router.message(F.text.in_({"Профиль", "👤 Профиль"}))
async def cmd_profile(message: Message):
    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_telegram_id(message.from_user.id)

        if not resident:
            await message.answer("⚠️ Вы не зарегистрированы. Введите /start")
            return

        # Addresses
        resident_full = await repo.get_with_addresses(resident.id)
        addresses = []
        meter_count = 0
        for addr in resident_full.addresses:
            addresses.append(
                f"  📍 {addr.city}, ул. {addr.street},\n"
                f"      д. {addr.building}, кв. {addr.apartment} ({addr.area_sqm} м²)"
            )
            res = await session.execute(
                select(func.count()).select_from(Meter).where(
                    Meter.address_id == addr.id, Meter.is_active.is_(True)
                )
            )
            meter_count += res.scalar_one()

        # Readings count
        res = await session.execute(
            select(func.count()).select_from(MeterReading).where(
                MeterReading.submitted_by_resident == resident.id
            )
        )
        readings_count = res.scalar_one()

        # Debt
        payment_repo = PaymentRepository(session)
        total_paid = await payment_repo.get_total_paid(resident.id)
        total_charged = await payment_repo.get_total_charged(resident.id)
        debt = max(Decimal("0"), total_charged - total_paid)

    fmt = lambda x: f"{x:,.2f}".replace(",", " ")
    addr_text = "\n".join(addresses) if addresses else "  Не указан"

    text = "👤 <b>Ваш профиль</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📛 <b>ФИО:</b> {resident.full_name}\n"
    text += f"🏠 <b>Лицевой счёт:</b> <code>{resident.personal_account}</code>\n"
    text += f"📱 <b>Телефон:</b> {resident.phone}\n\n"
    text += f"<b>Адреса:</b>\n{addr_text}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 Счётчиков: <b>{meter_count}</b>\n"
    text += f"📋 Показаний подано: <b>{readings_count}</b>\n"

    if debt > 0:
        text += f"🔴 Задолженность: <b>{fmt(debt)}</b> руб.\n"
    else:
        text += "🟢 Задолженность: <b>нет</b>\n"

    text += f"✅ Статус: {'Верифицирован' if resident.is_verified else 'Не верифицирован'}"

    photo = FSInputFile(IMG_DIR / "profile.png")
    await message.answer_photo(photo, caption=text, reply_markup=main_menu)
