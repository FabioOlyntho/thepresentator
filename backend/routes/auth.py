"""
Auth routes — NotebookLM browser-based authentication.

Provides endpoints for a remote browser login flow:
  1. GET  /auth/notebooklm/status     → check if authenticated
  2. POST /auth/notebooklm/start      → start browser session
  3. GET  /auth/notebooklm/screenshot  → get current screenshot
  4. POST /auth/notebooklm/click       → click at coordinates
  5. POST /auth/notebooklm/type        → type text
  6. POST /auth/notebooklm/key         → press keyboard key
  7. POST /auth/notebooklm/complete    → save cookies & close
  8. POST /auth/notebooklm/cancel      → close without saving
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.services.nlm_auth_service import (
    close_session,
    get_session,
    save_uploaded_cookies,
    start_session,
    validate_nlm_auth,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")


class AuthStatus(BaseModel):
    authenticated: bool


class ScreenshotResponse(BaseModel):
    screenshot: str  # base64-encoded PNG


class ClickRequest(BaseModel):
    x: int
    y: int


class TypeRequest(BaseModel):
    text: str


class KeyRequest(BaseModel):
    key: str  # "Enter", "Tab", "Backspace", etc.


class CookieUploadRequest(BaseModel):
    cookies: list[dict]
    api_key: str


class SaveResult(BaseModel):
    success: bool
    message: str


@router.get("/notebooklm/status", response_model=AuthStatus)
async def nlm_auth_status():
    """Check if NotebookLM auth cookies are actually valid (live HTTP check)."""
    authenticated = await validate_nlm_auth()
    return AuthStatus(authenticated=authenticated)


@router.post("/notebooklm/start", response_model=ScreenshotResponse)
async def nlm_auth_start():
    """Start a browser login session. Returns first screenshot."""
    try:
        session = await start_session()
        screenshot = await session.screenshot()
        return ScreenshotResponse(screenshot=screenshot)
    except Exception as e:
        logger.error("Failed to start auth session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notebooklm/screenshot", response_model=ScreenshotResponse)
async def nlm_auth_screenshot():
    """Get current browser screenshot."""
    session = await get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active auth session")
    try:
        screenshot = await session.screenshot()
        return ScreenshotResponse(screenshot=screenshot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notebooklm/click", response_model=ScreenshotResponse)
async def nlm_auth_click(req: ClickRequest):
    """Click at coordinates in the browser."""
    session = await get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active auth session")
    try:
        screenshot = await session.click(req.x, req.y)
        return ScreenshotResponse(screenshot=screenshot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notebooklm/type", response_model=ScreenshotResponse)
async def nlm_auth_type(req: TypeRequest):
    """Type text into the focused element."""
    session = await get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active auth session")
    try:
        screenshot = await session.type_text(req.text)
        return ScreenshotResponse(screenshot=screenshot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notebooklm/key", response_model=ScreenshotResponse)
async def nlm_auth_key(req: KeyRequest):
    """Press a keyboard key (Enter, Tab, Backspace, etc.)."""
    session = await get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active auth session")
    try:
        screenshot = await session.press_key(req.key)
        return ScreenshotResponse(screenshot=screenshot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notebooklm/complete", response_model=SaveResult)
async def nlm_auth_complete():
    """Save cookies from the browser session and close."""
    session = await get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active auth session")
    try:
        saved = await session.save_cookies()
        await close_session()
        if saved:
            return SaveResult(success=True, message="Authentication saved successfully")
        return SaveResult(success=False, message="No valid cookies found — login may not be complete")
    except Exception as e:
        await close_session()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notebooklm/cancel")
async def nlm_auth_cancel():
    """Cancel the auth session without saving."""
    await close_session()
    return {"status": "cancelled"}


@router.post("/notebooklm/upload-cookies", response_model=SaveResult)
async def nlm_upload_cookies(req: CookieUploadRequest):
    """Receive cookies from local auth_local.py script."""
    if not settings.GEMINI_API_KEY or req.api_key != settings.GEMINI_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    if not req.cookies:
        return SaveResult(success=False, message="No cookies provided")

    try:
        saved = save_uploaded_cookies(req.cookies)
        if saved:
            return SaveResult(success=True, message="Cookies saved — NotebookLM authenticated")
        return SaveResult(success=False, message="No Google cookies found in upload")
    except Exception as e:
        logger.error("Failed to save uploaded cookies: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
