from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.services.auth_service import decode_access_token


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/admin/login"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/admin/login"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/admin/login"},
        )

    user = await session.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/admin/login"},
        )

    return user
