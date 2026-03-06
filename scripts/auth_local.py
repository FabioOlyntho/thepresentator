#!/usr/bin/env python3
"""
NotebookLM Local Authentication — Run on YOUR machine (not the server).

Launches your REAL installed Chrome browser for Google login. Google sees
your normal browser (with history, extensions, etc.) so it won't block you.
After login, cookies are extracted and uploaded to the production server.

Usage (from presentation-factory directory):
    ./venv/Scripts/python.exe scripts/auth_local.py
"""

import asyncio
import json
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

VPS_URL = "https://presentator.humanaie.com/api/v1/auth/notebooklm/upload-cookies"
GOOGLE_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https://notebooklm.google.com"
DEBUG_PORT = 9234  # Avoid 9222 which other tools might use


def load_api_key() -> str:
    """Read GEMINI_API_KEY from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def find_chrome() -> str:
    """Find the real Chrome installation on the system."""
    # Check common Windows paths
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    # Try 'where' command
    result = shutil.which("chrome")
    if result:
        return result

    # Try 'where' on Windows
    try:
        out = subprocess.check_output(["where", "chrome"], text=True, stderr=subprocess.DEVNULL)
        for line in out.strip().splitlines():
            if os.path.isfile(line.strip()):
                return line.strip()
    except Exception:
        pass

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


def wait_for_chrome_debug(timeout: int = 15) -> bool:
    """Wait until Chrome's debug port is accepting connections."""
    for _ in range(timeout * 2):
        try:
            req = urllib.request.Request(f"http://localhost:{DEBUG_PORT}/json/version")
            urllib.request.urlopen(req, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


async def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file")
        sys.exit(1)

    chrome_path = find_chrome()
    if not chrome_path:
        print("ERROR: Chrome not found. Install Google Chrome first.")
        sys.exit(1)

    print()
    print("=" * 50)
    print("  NotebookLM Authentication")
    print("=" * 50)
    print()
    print(f"Using Chrome: {chrome_path}")
    print()
    print("A Chrome window will open.")
    print("Sign in to your Google account.")
    print("Wait until you see NotebookLM load.")
    print("Then come back here and press Enter.")
    print()

    # Use a temporary profile so we don't interfere with running Chrome
    temp_profile = Path.home() / ".presentator-chrome-auth"
    temp_profile.mkdir(parents=True, exist_ok=True)

    # Launch real Chrome with remote debugging enabled
    proc = subprocess.Popen([
        chrome_path,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={temp_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        GOOGLE_LOGIN_URL,
    ])

    print("Waiting for Chrome to start...")
    if not wait_for_chrome_debug():
        print("ERROR: Chrome debug port not responding. Is Chrome already running?")
        print("Close all Chrome windows and try again.")
        proc.terminate()
        sys.exit(1)

    print("Chrome is running. Log in to Google now.\n")
    input(">>> After you see NotebookLM loaded, press Enter here... ")

    # Connect to Chrome via CDP and extract cookies
    print("\nExtracting cookies...")
    try:
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")

        # Get cookies from all contexts
        cookies = []
        for context in browser.contexts:
            ctx_cookies = await context.cookies()
            cookies.extend(ctx_cookies)

        google_count = sum(1 for c in cookies if "google" in c.get("domain", ""))
        print(f"Extracted {len(cookies)} cookies ({google_count} Google)")

        # Disconnect (does NOT close Chrome)
        await browser.close()
        await pw.stop()

    except Exception as e:
        print(f"ERROR extracting cookies: {e}")
        proc.terminate()
        sys.exit(1)

    # Close Chrome
    proc.terminate()

    if google_count == 0:
        print("\nWARNING: No Google cookies found. Login may not have completed.")
        sys.exit(1)

    # Upload to production server
    print(f"\nUploading to server...")
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
