from fastapi import HTTPException

from app.config import Settings

WRITE_API_DISABLED_DETAIL = (
    "Write API is disabled in production until authentication and operator controls are "
    "configured."
)


def require_write_api_enabled(settings: Settings) -> None:
    if settings.production_writes_allowed:
        return
    raise HTTPException(
        status_code=403,
        detail=WRITE_API_DISABLED_DETAIL,
    )
