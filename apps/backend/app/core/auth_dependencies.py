from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header

from app.core.config import get_settings
from app.core.jwt_handler import decode_access_token
from app.core.users import UserRepository


async def get_current_user_id_optional(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)

    if not payload:
        return None

    return payload.get("sub")


async def get_current_user_id(
    user_id: Annotated[Optional[str], Depends(get_current_user_id_optional)],
) -> str:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    repo = UserRepository()
    user = await repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_verified_user(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    settings = get_settings()
    require_verified = getattr(settings, "require_email_verification", True)

    if require_verified and not user.get("is_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Email verification required. Please check your inbox.",
        )

    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
OptionalUserId = Annotated[Optional[str], Depends(get_current_user_id_optional)]
VerifiedUser = Annotated[dict, Depends(get_verified_user)]
