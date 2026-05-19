from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import async_session

scheduler = AsyncIOScheduler()


async def reading_reminder_job():
    """Runs on the 20th of each month — reminds to submit readings."""
    from app.bot.bot import bot
    if not bot:
        return

    async with async_session() as session:
        from app.services.notification_service import send_reading_reminders
        count = await send_reading_reminders(session, bot)
        print(f"Sent {count} reading reminders")


async def debt_reminder_job():
    """Runs on the 5th of each month — reminds about outstanding debt."""
    from app.bot.bot import bot
    if not bot:
        return

    async with async_session() as session:
        from app.services.notification_service import send_debt_reminders
        count = await send_debt_reminders(session, bot)
        print(f"Sent {count} debt reminders")


def start_scheduler():
    # 20th of each month at 10:00 — reading reminders
    scheduler.add_job(
        reading_reminder_job,
        "cron",
        day=20,
        hour=10,
        minute=0,
        id="reading_reminder",
    )

    # 5th of each month at 10:00 — debt reminders
    scheduler.add_job(
        debt_reminder_job,
        "cron",
        day=5,
        hour=10,
        minute=0,
        id="debt_reminder",
    )

    scheduler.start()
    print("Scheduler started: reading reminders (20th), debt reminders (5th)")


def stop_scheduler():
    scheduler.shutdown(wait=False)
