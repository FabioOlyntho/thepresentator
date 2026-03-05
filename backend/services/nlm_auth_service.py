"""
NotebookLM Auth Service — Remote browser login via Playwright screenshots.

Manages a headless Chromium browser on the server. The frontend streams
screenshots and sends click/keyboard events so the user can complete
Google sign-in without needing SSH access.

Flow: start() → screenshot loop + click/type → save_cookies() → close()
"""

import asyncio
import base64
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Singleton session — only one auth session at a time
_session: "NlmAuthSession | None" = None

GOOGLE_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https://notebooklm.google.com"
SESSION_TIMEOUT = 300  # 5 minutes max
VIEWPORT = {"width": 1024, "height": 700}


class NlmAuthSession:
    """Manages a headless Playwright browser for Google login."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None
        self.started_at = 0.0

    async def start(self) -> str:
        """Launch browser and navigate to Google login. Returns base64 screenshot."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = await self._browser.new_context(
            viewport=VIEWPORT,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self._context.new_page()
        self.started_at = time.monotonic()

        logger.info("NLM Auth: navigating to Google login")
        await self.page.goto(GOOGLE_LOGIN_URL, wait_until="networkidle", timeout=30000)
        return await self.screenshot()

    async def screenshot(self) -> str:
        """Take a screenshot and return as base64-encoded PNG."""
        if not self.page:
            raise RuntimeError("No active auth session")
        png_bytes = await self.page.screenshot(type="png")
        return base64.b64encode(png_bytes).decode("ascii")

    async def click(self, x: int, y: int) -> str:
        """Click at coordinates and return screenshot."""
        if not self.page:
            raise RuntimeError("No active auth session")
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.5)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass  # Page might not navigate
        return await self.screenshot()

    async def type_text(self, text: str) -> str:
        """Type text into the focused element and return screenshot."""
        if not self.page:
            raise RuntimeError("No active auth session")
        await self.page.keyboard.type(text, delay=50)
        return await self.screenshot()

    async def press_key(self, key: str) -> str:
        """Press a keyboard key (Enter, Tab, etc.) and return screenshot."""
        if not self.page:
            raise RuntimeError("No active auth session")
        await self.page.keyboard.press(key)
        await asyncio.sleep(0.5)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        return await self.screenshot()

    async def save_cookies(self) -> bool:
        """Extract cookies and save to NotebookLM profile."""
        if not self._context:
            raise RuntimeError("No active auth session")

        cookies = await self._context.cookies()
        if not cookies:
            logger.warning("NLM Auth: no cookies found")
            return False

        # Filter for Google/NotebookLM cookies
        relevant = [c for c in cookies if "google" in c.get("domain", "")]
        logger.info("NLM Auth: extracted %d cookies (%d Google)", len(cookies), len(relevant))

        if not relevant:
            return False

        # Save to notebooklm-mcp-cli profile format
        try:
            profile_dir = Path.home() / ".notebooklm-mcp-cli" / "profiles" / "default"
            profile_dir.mkdir(parents=True, exist_ok=True)

            # Convert Playwright cookies to the format expected by notebooklm-mcp-cli
            import json

            # notebooklm-mcp-cli expects cookies as a list of dicts
            cookie_data = []
            for c in cookies:
                cookie_data.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c["domain"],
                    "path": c.get("path", "/"),
                    "expires": c.get("expires", -1),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": c.get("sameSite", "Lax"),
                })

            cookies_path = profile_dir / "cookies.json"
            cookies_path.write_text(json.dumps(cookie_data, indent=2), encoding="utf-8")

            # Also try to extract CSRF token and session ID from cookies
            csrf_token = ""
            session_id = ""
            for c in cookies:
                if c["name"] == "COMPASS":
                    csrf_token = c["value"]
                elif c["name"] == "SID":
                    session_id = c["value"]

            metadata = {
                "csrf_token": csrf_token,
                "session_id": session_id,
                "build_label": "",
                "updated_at": time.time(),
            }
            metadata_path = profile_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            logger.info("NLM Auth: cookies saved to %s", cookies_path)
            return True

        except Exception as e:
            logger.error("NLM Auth: failed to save cookies: %s", e)
            return False

    @property
    def is_expired(self) -> bool:
        """Check if session has timed out."""
        if self.started_at == 0:
            return True
        return (time.monotonic() - self.started_at) > SESSION_TIMEOUT

    async def close(self):
        """Close browser and clean up."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._browser = None
        self._context = None
        self.page = None
        self._playwright = None
        logger.info("NLM Auth: session closed")


async def get_session() -> "NlmAuthSession | None":
    """Get the active auth session (if any)."""
    global _session
    if _session and _session.is_expired:
        await _session.close()
        _session = None
    return _session


async def start_session() -> NlmAuthSession:
    """Start a new auth session (closes any existing one)."""
    global _session
    if _session:
        await _session.close()
    _session = NlmAuthSession()
    await _session.start()
    return _session


async def close_session():
    """Close the active session."""
    global _session
    if _session:
        await _session.close()
        _session = None


def check_nlm_auth() -> bool:
    """Check if NotebookLM auth credentials exist and look valid."""
    try:
        from notebooklm_tools.core.auth import AuthManager
        manager = AuthManager("default")
        return manager.profile_exists()
    except ImportError:
        return False
    except Exception:
        return False
