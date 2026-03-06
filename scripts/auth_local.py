#!/usr/bin/env python3
"""
NotebookLM Local Authentication — Run on YOUR machine (not the server).

Opens a real Chrome browser window so you can log in to Google normally.
After login, the cookies are uploaded to the production server automatically.

Usage (from presentation-factory directory):
    ./venv/Scripts/python.exe scripts/auth_local.py

Prerequisites:
    pip install playwright
    playwright install chromium
"""

import asyncio
import json
import ssl
import sys
import urllib.request
from pathlib import Path

VPS_URL = "https://presentator.humanaie.com/api/v1/auth/notebooklm/upload-cookies"
GOOGLE_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https://notebooklm.google.com"


def load_api_key() -> str:
    """Read GEMINI_API_KEY from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def upload_cookies(cookies: list[dict], api_key: str) -> dict:
    """Upload cookies to the production server."""
    data = json.dumps({"cookies": cookies, "api_key": api_key}).encode("utf-8")
    req = urllib.request.Request(
        VPS_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


async def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file")
        sys.exit(1)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright not installed. Run:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    print()
    print("=" * 50)
    print("  NotebookLM Authentication")
    print("=" * 50)
    print()
    print("A Chrome window will open.")
    print("Sign in to your Google account (fabio.olyntho@gmail.com).")
    print("Wait until you see NotebookLM load.")
    print("The window will close automatically.")
    print()

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(GOOGLE_LOGIN_URL)

    # Wait for the user to complete login — detect NotebookLM URL
    print("Waiting for login... (watching for notebooklm.google.com)")
    print()
    try:
        await page.wait_for_url("**/notebooklm.google.com/**", timeout=300_000)
        print("Login detected! Extracting cookies...")
    except Exception:
        print("Timeout waiting for login. Extracting cookies anyway...")

    # Give cookies a moment to settle
    await asyncio.sleep(3)

    cookies = await context.cookies()
    google_count = sum(1 for c in cookies if "google" in c.get("domain", ""))
    print(f"Extracted {len(cookies)} cookies ({google_count} Google)")

    await browser.close()
    await pw.stop()

    if google_count == 0:
        print("\nWARNING: No Google cookies found. Login may not have completed.")
        sys.exit(1)

    # Upload to production server
    print(f"\nUploading to {VPS_URL}...")
    try:
        result = upload_cookies(cookies, api_key)
        if result.get("success"):
            print("\nSUCCESS! Authentication saved to server.")
            print("You can now use NotebookLM mode at https://presentator.humanaie.com")
        else:
            print(f"\nFAILED: {result.get('message', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        print(f"\nERROR uploading cookies: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
