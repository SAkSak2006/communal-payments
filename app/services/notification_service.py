from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resident, Notification, Address, Charge, Payment, UtilityService, PaymentPeriod
from app.repositories.payment_repo import PaymentRepository


async def send_reading_reminders(session: AsyncSession, bot) -> int:
    """Send reminders to submit meter readings (20th of month)."""
    result = await session.execute(
        select(Resident).where(
            Resident.telegram_id.isnot(None),
            Resident.is_verified.is_(True),
        )
    )
    residents = result.scalars().all()

    sent = 0
    for resident in residents:
        try:
            await bot.send_message(
                resident.telegram_id,
                "Напоминание: пожалуйста, подайте показания счётчиков.\n"
                "Нажмите /readings для подачи показаний.",
            )

            notification = Notification(
                resident_id=resident.id,
                type="reading_reminder",
                message_text="Напоминание о подаче показаний",
                sent_at=datetime.utcnow(),
                is_delivered=True,
            )
            session.add(notification)
            sent += 1
        except Exception:
            notification = Notification(
                resident_id=resident.id,
                type="reading_reminder",
                message_text="Напоминание о подаче показаний",
                is_delivered=False,
            )
            session.add(notification)

    await session.commit()
    return sent


async def send_debt_reminders(session: AsyncSession, bot) -> int:
    """Send reminders about outstanding debt (5th of month)."""
    result = await session.execute(
        select(Resident).where(
            Resident.telegram_id.isnot(None),
            Resident.is_verified.is_(True),
        )
    )
    residents = result.scalars().all()

    sent = 0
    for resident in residents:
        pay_repo = PaymentRepository(session)
        total_paid = await pay_repo.get_total_paid(resident.id)
        total_charged = await pay_repo.get_total_charged(resident.id)
        debt = total_charged - total_paid

        if debt <= 0:
            continue

        try:
            await bot.send_message(
                resident.telegram_id,
                f"Напоминание: у вас имеется задолженность <b>{debt:,.2f} руб.</b>\n"
                f"Проверьте баланс: /balance".replace(",", " "),
            )

            notification = Notification(
                resident_id=resident.id,
                type="payment_reminder",
                message_text=f"Напоминание о задолженности: {debt} руб.",
                sent_at=datetime.utcnow(),
                is_delivered=True,
            )
            session.add(notification)
            sent += 1
        except Exception:
            notification = Notification(
                resident_id=resident.id,
                type="payment_reminder",
                message_text=f"Напоминание о задолженности: {debt} руб.",
                is_delivered=False,
            )
            session.add(notification)

    await session.commit()
    return sent


MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


async def send_period_charges_notification(session: AsyncSession, bot, year: int, month: int) -> int:
    """Отправить жильцам уведомление о начислениях за расчётный период."""
    period_result = await session.execute(
        select(PaymentPeriod).where(
            PaymentPeriod.year == year,
            PaymentPeriod.month == month,
        )
    )
    period = period_result.scalar_one_or_none()
    if not period:
        return 0

    residents_result = await session.execute(
        select(Resident).where(
            Resident.telegram_id.isnot(None),
            Resident.is_verified.is_(True),
        )
    )
    residents = residents_result.scalars().all()

    period_label = f"{MONTH_NAMES.get(month, month)} {year}"
    sent = 0

    for resident in residents:
        addr_result = await session.execute(
            select(Address).where(Address.resident_id == resident.id)
        )
        addresses = addr_result.scalars().all()
        if not addresses:
            continue

        address_ids = [a.id for a in addresses]

        charges_result = await session.execute(
            select(Charge, UtilityService)
            .join(UtilityService, UtilityService.id == Charge.service_id)
            .where(
                Charge.address_id.in_(address_ids),
                Charge.period_id == period.id,
            )
            .order_by(UtilityService.name)
        )
        charges = charges_result.all()

        if not charges:
            continue

        total = sum(c.amount for c, _ in charges)

        lines = []
        for charge, service in charges:
            lines.append(
                f"  • {service.name}: <b>{charge.amount:,.2f} руб.</b>".replace(",", " ")
            )

        text = (
            f"🔔 <b>Начисления за {period_label}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(lines) +
            f"\n━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Итого: {total:,.2f} руб.</b>\n\n".replace(",", " ") +
            f"Оплатите до 15-го числа следующего месяца.\n"
            f"Проверить задолженность: /balance"
        )

        try:
            await bot.send_message(resident.telegram_id, text)
            notification = Notification(
                resident_id=resident.id,
                type="period_charges",
                message_text=f"Начисления за {period_label}: {total:.2f} руб.",
                sent_at=datetime.utcnow(),
                is_delivered=True,
            )
            session.add(notification)
            sent += 1
        except Exception:
            notification = Notification(
                resident_id=resident.id,
                type="period_charges",
                message_text=f"Начисления за {period_label}: {total:.2f} руб.",
                is_delivered=False,
            )
            session.add(notification)

    await session.commit()
    return sent
