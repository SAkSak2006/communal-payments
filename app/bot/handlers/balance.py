from decimal import Decimal
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from app.bot.keyboards.reply import main_menu
from app.database import async_session
from app.models import Charge, Address, UtilityService
from app.repositories.resident_repo import ResidentRepository
from app.repositories.payment_repo import PaymentRepository

from sqlalchemy import select, func

router = Router()

IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "bot_images"


@router.message(Command("balance"))
@router.message(F.text.in_({"Баланс", "💰 Баланс"}))
async def cmd_balance(message: Message):
    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_telegram_id(message.from_user.id)

        if not resident:
            await message.answer("⚠️ Вы не зарегистрированы. Введите /start")
            return

        payment_repo = PaymentRepository(session)
        total_paid = await payment_repo.get_total_paid(resident.id)
        total_charged = await payment_repo.get_total_charged(resident.id)
        debt = total_charged - total_paid

        result = await session.execute(
            select(
                UtilityService.name,
                func.coalesce(func.sum(Charge.amount), 0),
            )
            .join(Address, Address.id == Charge.address_id)
            .join(UtilityService, UtilityService.id == Charge.service_id)
            .where(Address.resident_id == resident.id)
            .group_by(UtilityService.name)
            .order_by(UtilityService.name)
        )
        breakdown = result.all()

    fmt = lambda x: f"{x:,.2f}".replace(",", " ")

    service_icons = {
        "Холодное водоснабжение": "💧",
        "Горячее водоснабжение": "🔥",
        "Электроснабжение": "⚡",
        "Газоснабжение": "🔵",
        "Отопление": "🌡",
    }

    text = f"💰 <b>Баланс — {resident.full_name}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"

    if breakdown:
        text += "<b>Начисления по услугам:</b>\n\n"
        for svc_name, amount in breakdown:
            icon = service_icons.get(svc_name, "▪️")
            text += f"  {icon} {svc_name}\n"
            text += f"      <b>{fmt(amount)}</b> руб.\n\n"

        text += "━━━━━━━━━━━━━━━━━━━\n"
        text += f"📊 Начислено: <b>{fmt(total_charged)}</b> руб.\n"
        text += f"✅ Оплачено: <b>{fmt(total_paid)}</b> руб.\n"
        text += "━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        text += "📭 Начислений пока нет.\n\n"

    if debt > 0:
        text += f"🔴 <b>Задолженность: {fmt(debt)} руб.</b>"
    elif debt < 0:
        text += f"🟢 <b>Переплата: {fmt(abs(debt))} руб.</b>"
    else:
        text += "🟢 <b>Задолженность отсутствует</b>"

    photo = FSInputFile(IMG_DIR / "balance.png")
    await message.answer_photo(photo, caption=text, reply_markup=main_menu)
