from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.database import async_session
from app.repositories.resident_repo import ResidentRepository

# Commands that don't require registration
PUBLIC_COMMANDS = {"/start", "/help", "/cancel"}


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Skip non-message events
        if not isinstance(event, Message):
            return await handler(event, data)

        # Allow public commands
        if event.text and any(event.text.startswith(cmd) for cmd in PUBLIC_COMMANDS):
            return await handler(event, data)

        # Allow cancel button
        if event.text in ("Отмена", "Нет, отмена", "Да, всё верно", "❓ Помощь", "Помощь"):
            return await handler(event, data)

        # Allow if in FSM state (user is in the middle of a process)
        state = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state:
                return await handler(event, data)

        # Check registration for other commands
        async with async_session() as session:
            repo = ResidentRepository(session)
            resident = await repo.get_by_telegram_id(event.from_user.id)

        if not resident:
            await event.answer(
                "⚠️ Вы не зарегистрированы.\n\n"
                "Введите /start для регистрации."
            )
            return

        return await handler(event, data)
