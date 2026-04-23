from fastapi import HTTPException, Request

from core.config import get_settings


def assert_import_token(request: Request) -> None:
    expected = get_settings().import_api_token
    if not expected:
        return

    provided = request.headers.get("X-Import-Token", "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="invalid import token")
