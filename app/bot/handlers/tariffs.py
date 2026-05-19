from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from sqlalchemy import select

from app.bot.keyboards.reply import main_menu
from app.database import async_session
from app.models import Tariff, UtilityService

router = Router()

IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "bot_images"


@router.message(Command("tariffs"))
@router.message(F.text.in_({"Тарифы", "📈 Тарифы"}))
async def cmd_tariffs(message: Message):
    async with async_session() as session:
        result = await session.execute(
            select(Tariff, UtilityService.name, UtilityService.unit)
            .join(UtilityService, UtilityService.id == Tariff.service_id)
            .where(Tariff.effective_to.is_(None))
            .order_by(UtilityService.name)
        )
        tariffs = result.all()

    if not tariffs:
        await message.answer(
            "📈 <b>Тарифы</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "Тарифы не установлены.",
            reply_markup=main_menu,
        )
        return

    service_icons = {
        "Холодное водоснабжение": "💧",
        "Горячее водоснабжение": "🔥",
        "Электроснабжение": "⚡",
        "Газоснабжение": "🔵",
        "Отопление": "🌡",
    }

    text = "📈 <b>Текущие тарифы</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"

    for tariff, svc_name, svc_unit in tariffs:
        icon = service_icons.get(svc_name, "▪️")
        price = f"{tariff.price_per_unit:,.4f}".replace(",", " ")
        text += f"  {icon} <b>{svc_name}</b>\n"
        text += f"      {price} руб. / {svc_unit}\n\n"

    text += "━━━━━━━━━━━━━━━━━━━\n"
    text += f"📅 Действуют с {tariffs[0][0].effective_from.strftime('%d.%m.%Y')}"

    photo = FSInputFile(IMG_DIR / "tariffs.png")
    await message.answer_photo(photo, caption=text, reply_markup=main_menu)
