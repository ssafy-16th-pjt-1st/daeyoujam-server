from fastapi import HTTPException

from app.core.config import get_settings


def require_openai_key() -> str:
    key = get_settings().openai_api_key
    if not key or key == "replace_with_new_openai_api_key":
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured. Set backend/.env for AI APIs.")
    return key

