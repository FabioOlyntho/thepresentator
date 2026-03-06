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

# Persistent browser profile so Google sees a "returning" browser
_BROWSER_PROFILE_DIR = str(Path.home() / ".presentator-browser-profile")

# JavaScript to mask Playwright automation signals from Google
_STEALTH_SCRIPT = """
// Hide navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Pass Chrome App test
window.chrome = { runtime: {}, csi: function(){}, loadTimes: function(){} };

// Override navigator.permissions.query
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);

// Override navigator.plugins (real Chrome has 3+ plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        plugins.length = 3;
        return plugins;
    },
});

// Override navigator.languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en', 'es'],
});

// Fix WebGL vendor/renderer (avoid "Google SwiftShader" which screams headless)
const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {
    if (p === 37445) return 'Intel Inc.';
    if (p === 37446) return 'Intel Iris OpenGL Engine';
    return getParam.call(this, p);
};

// Fix WebGL2 too
if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParam2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(p) {
        if (p === 37445) return 'Intel Inc.';
        if (p === 37446) return 'Intel Iris OpenGL Engine';
        return getParam2.call(this, p);
    };
}

// Override connection.rtt (headless has 0, real browsers have values)
if (navigator.connection) {
    Object.defineProperty(navigator.connection, 'rtt', { get: () => 50 });
}
"""


class NlmAuthSession:
    """Manages a headless Playwright browser for Google login."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None
        self.started_at = 0.0

    async def start(self) -> str:
        """Launch browser with stealth patches and navigate to Google login."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        # Use persistent context so Google sees a "returning" browser
        # with history, local storage, etc. from previous sessions
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=_BROWSER_PROFILE_DIR,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-gpu",
                "--lang=en-US,en",
                "--disable-setuid-sandbox",
            ],
            viewport=VIEWPORT,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            },
            ignore_https_errors=True,
        )

        # Get existing page or create new one
        if self._context.pages:
            self.page = self._context.pages[0]
        else:
            self.page = await self._context.new_page()

        # Inject stealth scripts BEFORE navigating to Google
        await self.page.add_init_script(_STEALTH_SCRIPT)

        self.started_at = time.monotonic()

        logger.info("NLM Auth: navigating to Google login (stealth mode)")
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

            from datetime import datetime, timezone
            metadata = {
                "csrf_token": csrf_token,
                "session_id": session_id,
                "build_label": "",
                "updated_at": time.time(),
                "last_validated": datetime.now(timezone.utc).isoformat(),
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
        if self._context:
            try:
                await self._context.close()
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
    """Quick file-existence check (used as fallback only)."""
    try:
        from notebooklm_tools.core.auth import AuthManager
        manager = AuthManager("default")
        return manager.profile_exists()
    except Exception:
        return False


async def validate_nlm_auth() -> bool:
    """Actually validate NotebookLM cookies by making a lightweight HTTP request.

    Returns True only if the cookies produce an authenticated session.
    This prevents false positives from expired cookies sitting on disk.
    """
    import json as _json

    profile_dir = Path.home() / ".notebooklm-mcp-cli" / "profiles" / "default"
    cookies_path = profile_dir / "cookies.json"

    if not cookies_path.exists():
        logger.info("NLM Auth validate: no cookies file found")
        return False

    try:
        cookie_data = _json.loads(cookies_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("NLM Auth validate: failed to read cookies file")
        return False

    if not cookie_data:
        return False

    # Build cookie header from stored cookies
    cookie_header = "; ".join(
        f"{c['name']}={c['value']}" for c in cookie_data
        if isinstance(c, dict) and "name" in c and "value" in c
    )

    try:
        import httpx

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=8.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Cookie": cookie_header,
            },
        ) as client:
            resp = await client.get("https://notebooklm.google.com/")

        # 200 = authenticated, 302 to accounts.google.com = expired
        if resp.status_code == 200:
            logger.info("NLM Auth validate: cookies valid (200)")
            return True

        location = resp.headers.get("location", "")
        if "accounts.google.com" in location:
            logger.info("NLM Auth validate: cookies expired (redirect to login)")
            return False

        # Any other status — treat as invalid
        logger.warning("NLM Auth validate: unexpected status %d", resp.status_code)
        return False

    except Exception as e:
        logger.warning("NLM Auth validate: HTTP check failed: %s", e)
        # Network error — fall back to file check
        return check_nlm_auth()
