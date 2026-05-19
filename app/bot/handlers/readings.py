from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile

from app.bot.keyboards.inline import meters_keyboard, confirm_reading_keyboard
from app.bot.keyboards.reply import main_menu

IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "bot_images"
from app.bot.states.readings import ReadingStates
from app.database import async_session
from app.models import Meter, MeterReading, Address, ReadingSource
from app.repositories.resident_repo import ResidentRepository
from app.repositories.meter_repo import MeterRepository

router = Router()


@router.message(Command("readings"))
@router.message(F.text.in_({"Подать показания", "📊 Подать показания"}))
async def cmd_readings(message: Message, state: FSMContext):
    async with async_session() as session:
        repo = ResidentRepository(session)
        resident = await repo.get_by_telegram_id(message.from_user.id)

        if not resident:
            await message.answer("Вы не зарегистрированы. Введите /start")
            return

        # Get all meters for this resident
        resident_with_addr = await repo.get_with_addresses(resident.id)
        meter_repo = MeterRepository(session)

        meters_list = []
        for addr in resident_with_addr.addresses:
            meters = await meter_repo.get_by_address(addr.id)
            for meter in meters:
                meters_list.append({
                    "id": meter.id,
                    "service_name": meter.service.name,
                    "serial_number": meter.serial_number,
                })

    if not meters_list:
        await message.answer(
            "У вас нет зарегистрированных счётчиков.\n"
            "Обратитесь в управляющую компанию.",
            reply_markup=main_menu,
        )
        return

    await state.update_data(resident_id=resident.id)
    await message.answer(
        "Выберите счётчик для подачи показания:",
        reply_markup=meters_keyboard(meters_list),
    )
    await state.set_state(ReadingStates.waiting_for_meter)


@router.callback_query(ReadingStates.waiting_for_meter, F.data == "cancel")
async def cancel_meter_selection(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Подача показаний отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=main_menu)
    await callback.answer()


@router.callback_query(ReadingStates.waiting_for_meter, F.data.startswith("meter:"))
async def process_meter_selection(callback: CallbackQuery, state: FSMContext):
    meter_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        meter_repo = MeterRepository(session)
        meter = await session.get(Meter, meter_id)
        last_reading = await meter_repo.get_last_reading(meter_id)

        service_name = ""
        if meter:
            from app.models import UtilityService
            service = await session.get(UtilityService, meter.service_id)
            service_name = service.name if service else ""

    prev_value = last_reading.value if last_reading else Decimal("0")

    await state.update_data(
        meter_id=meter_id,
        service_name=service_name,
        previous_value=str(prev_value),
    )

    await callback.message.edit_text(
        f"<b>{service_name}</b>\n\n"
        f"Предыдущее показание: <b>{prev_value}</b>\n\n"
        f"Введите текущее показание:"
    )
    await state.set_state(ReadingStates.waiting_for_value)
    await callback.answer()


@router.message(ReadingStates.waiting_for_value)
async def process_reading_value(message: Message, state: FSMContext):
    if message.text in ("Отмена", "/cancel"):
        await state.clear()
        await message.answer("Подача показаний отменена.", reply_markup=main_menu)
        return

    # Validate input
    text = message.text.strip().replace(",", ".")
    try:
        new_value = Decimal(text)
    except (InvalidOperation, ValueError):
        await message.answer("Введите число. Например: <b>12345.67</b>")
        return

    if new_value < 0:
        await message.answer("Показание не может быть отрицательным.")
        return

    MAX_VALUE = Decimal("999999999")
    if new_value > MAX_VALUE:
        await message.answer(
            "Значение слишком большое. Максимально допустимое: <b>999 999 999</b>.\n"
            "Введите корректное показание:"
        )
        return

    data = await state.get_data()
    prev_value = Decimal(data["previous_value"])

    if new_value < prev_value:
        await message.answer(
            f"Новое показание ({new_value}) меньше предыдущего ({prev_value}).\n"
            f"Показание должно быть >= {prev_value}.\n\n"
            f"Введите корректное значение:"
        )
        return

    consumption = new_value - prev_value

    # Check for anomaly (> 3x average)
    anomaly_warning = ""
    if prev_value > 0 and consumption > prev_value * 3:
        anomaly_warning = "\n\n⚠️ <i>Внимание: потребление значительно выше обычного!</i>"

    await state.update_data(
        new_value=str(new_value),
        consumption=str(consumption),
    )

    await message.answer(
        f"<b>{data['service_name']}</b>\n\n"
        f"Предыдущее: {prev_value}\n"
        f"Текущее: <b>{new_value}</b>\n"
        f"Потребление: <b>{consumption}</b>\n"
        f"{anomaly_warning}\n"
        f"Подтвердить?",
        reply_markup=confirm_reading_keyboard(),
    )
    await state.set_state(ReadingStates.waiting_for_confirm)


@router.callback_query(ReadingStates.waiting_for_confirm, F.data == "cancel")
async def cancel_reading(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Подача показаний отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=main_menu)
    await callback.answer()


@router.callback_query(ReadingStates.waiting_for_confirm, F.data == "confirm_reading")
async def confirm_reading(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    now = datetime.utcnow()

    async with async_session() as session:
        # Check if reading already exists for this meter/period
        from sqlalchemy import select
        existing = await session.execute(
            select(MeterReading).where(
                MeterReading.meter_id == data["meter_id"],
                MeterReading.period_year == now.year,
                MeterReading.period_month == now.month,
            )
        )
        old_reading = existing.scalar_one_or_none()

        if old_reading:
            # Update existing reading
            old_reading.value = Decimal(data["new_value"])
            old_reading.previous_value = Decimal(data["previous_value"])
            old_reading.consumption = Decimal(data["consumption"])
            old_reading.source = ReadingSource.TELEGRAM
            old_reading.submitted_by_resident = data["resident_id"]
            old_reading.is_validated = False
        else:
            reading = MeterReading(
                meter_id=data["meter_id"],
                value=Decimal(data["new_value"]),
                previous_value=Decimal(data["previous_value"]),
                consumption=Decimal(data["consumption"]),
                period_year=now.year,
                period_month=now.month,
                source=ReadingSource.TELEGRAM,
                submitted_by_resident=data["resident_id"],
                is_validated=False,
            )
            session.add(reading)

        await session.commit()

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Показание принято!</b>\n\n"
        f"📊 <b>{data['service_name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"  Значение: <b>{data['new_value']}</b>\n"
        f"  Потребление: <b>{data['consumption']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Показание будет проверено оператором."
    )
    photo = FSInputFile(IMG_DIR / "success.png")
    await callback.message.answer_photo(
        photo,
        caption="Данные отправлены! Выберите действие:",
        reply_markup=main_menu,
    )
    await callback.answer()
