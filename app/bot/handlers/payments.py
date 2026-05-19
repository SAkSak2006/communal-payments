from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.reply import main_menu
from app.database import async_session
from app.repositories.resident_repo import ResidentRepository
from app.repositories.payment_repo import PaymentRepository

router = Router()


@router.message(Command("payments"))
@router.message(F.text.in_({"История оплат", "📋 История оплат"}))
async def cmd_payments(message: Message):
    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_telegram_id(message.from_user.id)

        if not resident:
            await message.answer("⚠️ Вы не зарегистрированы. Введите /start")
            return

        payment_repo = PaymentRepository(session)
        payments = await payment_repo.get_by_resident(resident.id, limit=10)

    if not payments:
        await message.answer(
            "📋 <b>История оплат</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 Оплат пока нет.",
            reply_markup=main_menu,
        )
        return

    fmt = lambda x: f"{x:,.2f}".replace(",", " ")

    method_names = {
        "cash": "💵 наличные",
        "card": "💳 карта",
        "bank_transfer": "🏦 перевод",
        "online": "📱 онлайн",
    }

    text = "📋 <b>Последние оплаты</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"

    total = sum(p.amount for p in payments)

    for i, p in enumerate(payments, 1):
        date_str = p.payment_date.strftime("%d.%m.%Y")
        method = method_names.get(p.payment_method, p.payment_method)
        text += f"  {i}. {date_str}\n"
        text += f"      <b>{fmt(p.amount)}</b> руб. ({method})\n\n"

    text += "━━━━━━━━━━━━━━━━━━━\n"
    text += f"Итого за последние {len(payments)} платежей: <b>{fmt(total)}</b> руб."

    await message.answer(text, reply_markup=main_menu)
