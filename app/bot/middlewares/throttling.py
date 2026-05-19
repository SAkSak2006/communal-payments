from typing import Any, Awaitable, Callable, Dict
from datetime import datetime, timezone

from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self._last_message: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        now = datetime.now(timezone.utc).timestamp()

        last_time = self._last_message.get(user_id, 0)
        if now - last_time < self.rate_limit:
            return  # Skip message (throttled)

        self._last_message[user_id] = now
        return await handler(event, data)
