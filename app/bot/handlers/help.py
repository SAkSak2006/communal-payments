from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from app.bot.keyboards.reply import main_menu

router = Router()

IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "bot_images"


@router.message(Command("help"))
@router.message(F.text.in_({"Помощь", "❓ Помощь"}))
async def cmd_help(message: Message):
    photo = FSInputFile(IMG_DIR / "help.png")
    await message.answer_photo(
        photo,
        caption=(
            "📖 <b>Справка по системе ЖКУ</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📊 /readings — Подать показания\n"
            "💰 /balance — Проверить задолженность\n"
            "📋 /payments — История оплат\n"
            "📈 /tariffs — Текущие тарифы\n"
            "👤 /profile — Ваш профиль\n"
            "❌ /cancel — Отменить операцию\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Как подать показания:</b>\n"
            "1️⃣ Нажмите «Подать показания»\n"
            "2️⃣ Выберите счётчик из списка\n"
            "3️⃣ Введите текущее показание\n"
            "4️⃣ Подтвердите отправку\n\n"
            "📞 По вопросам обращайтесь\n"
            "в управляющую компанию."
        ),
        reply_markup=main_menu,
    )
