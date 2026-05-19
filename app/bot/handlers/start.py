from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from app.bot.keyboards.reply import main_menu, confirm_keyboard, cancel_keyboard, remove_keyboard, phone_keyboard
from app.bot.states.registration import RegistrationStates
from app.database import async_session
from app.repositories.resident_repo import ResidentRepository

router = Router()

IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "bot_images"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_telegram_id(message.from_user.id)

    if resident:
        photo = FSInputFile(IMG_DIR / "welcome.png")
        await message.answer_photo(
            photo,
            caption=(
                f"С возвращением, <b>{resident.full_name}</b>! 👋\n\n"
                f"🏠 Лицевой счёт: <code>{resident.personal_account}</code>\n\n"
                "Выберите действие в меню ниже:"
            ),
            reply_markup=main_menu,
        )
        return

    photo = FSInputFile(IMG_DIR / "welcome.png")
    await message.answer_photo(
        photo,
        caption=(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Это система учёта коммунальных платежей.\n"
            "Здесь вы можете:\n\n"
            "📊 Подавать показания счётчиков\n"
            "💰 Проверять задолженность\n"
            "📋 Смотреть историю оплат\n"
            "📈 Узнавать актуальные тарифы\n\n"
            "Для начала введите ваш <b>лицевой счёт</b>:"
        ),
        reply_markup=cancel_keyboard,
    )
    await state.set_state(RegistrationStates.waiting_for_account)


@router.message(RegistrationStates.waiting_for_account)
async def process_account(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("❌ Регистрация отменена.", reply_markup=remove_keyboard)
        return

    account = message.text.strip()

    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_personal_account(account)

    if not resident:
        await message.answer(
            "⚠️ Лицевой счёт <b>не найден</b>.\n\n"
            "Проверьте номер и попробуйте ещё раз,\n"
            "или нажмите <b>Отмена</b>.",
            reply_markup=cancel_keyboard,
        )
        return

    if resident.telegram_id:
        await message.answer(
            "⚠️ Этот лицевой счёт уже привязан к другому аккаунту Telegram.\n\n"
            "Обратитесь в управляющую компанию.",
            reply_markup=remove_keyboard,
        )
        await state.clear()
        return

    await state.update_data(
        resident_id=resident.id,
        full_name=resident.full_name,
        personal_account=resident.personal_account,
    )

    await message.answer(
        f"✅ Лицевой счёт найден: <b>{resident.full_name}</b>\n\n"
        "📱 Теперь укажите ваш номер телефона.\n\n"
        "Нажмите кнопку <b>«Поделиться номером»</b> или введите вручную в формате <code>+7XXXXXXXXXX</code>:",
        reply_markup=phone_keyboard,
    )
    await state.set_state(RegistrationStates.waiting_for_phone)


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("❌ Регистрация отменена.", reply_markup=remove_keyboard)
        return

    # Получить номер — либо из контакта, либо из текста
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    elif message.text:
        phone = message.text.strip()
        # Базовая валидация
        digits = phone.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit() or len(digits) < 10 or len(digits) > 12:
            await message.answer(
                "⚠️ Неверный формат номера.\n"
                "Введите в формате <code>+7XXXXXXXXXX</code> или нажмите кнопку:",
                reply_markup=phone_keyboard,
            )
            return
    else:
        await message.answer("Нажмите кнопку или введите номер:", reply_markup=phone_keyboard)
        return

    await state.update_data(phone=phone)

    data = await state.get_data()
    async with async_session() as session:
        repo = ResidentRepository(session)
        resident_with_addr = await repo.get_with_addresses(data["resident_id"])
        addresses = []
        if resident_with_addr and resident_with_addr.addresses:
            for addr in resident_with_addr.addresses:
                addresses.append(
                    f"  📍 {addr.city}, ул. {addr.street}, д. {addr.building}, кв. {addr.apartment}"
                )

    addr_text = "\n".join(addresses) if addresses else "  Не указан"

    await message.answer(
        f"🔍 <b>Проверьте данные:</b>\n\n"
        f"👤 <b>ФИО:</b> {data['full_name']}\n"
        f"🏠 <b>Лицевой счёт:</b> <code>{data['personal_account']}</code>\n"
        f"📱 <b>Телефон:</b> {phone}\n"
        f"📍 <b>Адрес:</b>\n{addr_text}\n\n"
        f"Всё верно?",
        reply_markup=confirm_keyboard,
    )
    await state.set_state(RegistrationStates.waiting_for_confirm)


@router.message(RegistrationStates.waiting_for_confirm)
async def process_confirm(message: Message, state: FSMContext):
    if message.text == "Нет, отмена":
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.\n\nВведите /start для повторной попытки.",
            reply_markup=remove_keyboard,
        )
        return

    if message.text != "Да, всё верно":
        await message.answer("Нажмите одну из кнопок:", reply_markup=confirm_keyboard)
        return

    data = await state.get_data()
    resident_id = data["resident_id"]

    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_id(resident_id)
        if resident:
            resident.telegram_id = message.from_user.id
            resident.telegram_username = message.from_user.username
            resident.is_verified = True
            if data.get("phone"):
                resident.phone = data["phone"]
            await session.commit()

    await state.clear()

    photo = FSInputFile(IMG_DIR / "success.png")
    await message.answer_photo(
        photo,
        caption=(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"Добро пожаловать, <b>{data['full_name']}</b>!\n\n"
            "Теперь вам доступны все функции бота.\n"
            "Используйте меню ниже для навигации."
        ),
        reply_markup=main_menu,
    )


@router.message(Command("cancel"))
@router.message(F.text == "Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Операция отменена.", reply_markup=main_menu)
    else:
        await message.answer("Нет активной операции.", reply_markup=main_menu)
