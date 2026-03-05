"""
Production smoke tests for The Presentator.

Tests the deployed app at presentator.humanaie.com via SSH.

Usage:
    set VPS_PASSWORD=<password>
    python deploy/smoke_tests.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_exec import ssh_exec

results = []


def smoke(
    name: str,
    cmd: str,
    expect_code: int | None = 200,
    expect_json: list | None = None,
    expect_contains: str | None = None,
) -> bool:
    """Run a smoke test and record result."""
    code, out = ssh_exec(cmd, timeout=30)
    out = out.strip()

    passed = True
    details = ""

    if expect_code:
        if out.endswith(str(expect_code)):
            details = f"HTTP {expect_code}"
        elif str(expect_code) in out:
            details = f"HTTP {expect_code}"
        else:
            passed = False
            details = f"Expected HTTP {expect_code}, got: {out[:200]}"

    if expect_json:
        try:
            data = json.loads(out)
            for key in expect_json:
                if key not in data:
                    passed = False
                    details = f"Missing key: {key}"
                    break
            if passed and not details:
                details = f"JSON OK: {expect_json}"
        except json.JSONDecodeError:
            passed = False
            details = f"Invalid JSON: {out[:200]}"

    if expect_contains:
        if expect_contains in out:
            if not details:
                details = f"Contains '{expect_contains}'"
        else:
            passed = False
            details = f"Missing '{expect_contains}' in: {out[:200]}"

    status = "PASS" if passed else "FAIL"
    results.append((name, status, details))
    print(f"  [{status}] {name}: {details}")
    return passed


def main():
    print("=" * 60)
    print("  The Presentator — Smoke Tests")
    print("=" * 60)

    # === Health ===
    print("\n--- Health ---\n")

    smoke(
        "ST-01: Health endpoint (HTTPS)",
        "curl -sk https://presentator.humanaie.com/api/v1/health --max-time 10",
        expect_code=None,
        expect_contains='"status":"ok"',
    )

    smoke(
        "ST-02: Health endpoint (localhost)",
        "curl -sf http://localhost:8001/api/v1/health --max-time 10",
        expect_code=None,
        expect_contains='"status":"ok"',
    )

    # === Frontend ===
    print("\n--- Frontend ---\n")

    smoke(
        "ST-03: Frontend loads (HTTPS)",
        "curl -sk https://presentator.humanaie.com/ --max-time 10",
        expect_code=None,
        expect_contains="<!doctype html>",
    )

    smoke(
        "ST-04: Static assets load",
        "ASSET=$(curl -sk https://presentator.humanaie.com/ 2>/dev/null | grep -o 'assets/[^\"]*\\.js' | head -1) && "
        "curl -sk -o /dev/null -w '%{http_code}' https://presentator.humanaie.com/$ASSET --max-time 10",
        expect_code=200,
    )

    # === SSL & Redirect ===
    print("\n--- SSL & Redirect ---\n")

    smoke(
        "ST-05: HTTP -> HTTPS redirect",
        "curl -sI http://presentator.humanaie.com --max-time 10 2>&1 | head -5",
        expect_code=None,
        expect_contains="308",
    )

    smoke(
        "ST-06: SSL certificate valid",
        "curl -svk https://presentator.humanaie.com/ 2>&1 | grep 'issuer:'",
        expect_code=None,
        expect_contains="Let's Encrypt",
    )

    # === API ===
    print("\n--- API ---\n")

    smoke(
        "ST-07: Jobs endpoint",
        "curl -sk -o /dev/null -w '%{http_code}' https://presentator.humanaie.com/api/v1/jobs --max-time 10",
        expect_code=200,
    )

    # === Infrastructure ===
    print("\n--- Infrastructure ---\n")

    smoke(
        "ST-08: PM2 process running",
        "pm2 jlist 2>/dev/null",
        expect_code=None,
        expect_contains="presentator",
    )

    smoke(
        "ST-09: SQLite database exists",
        f"test -f /var/www/presentator/data/presentator.db && echo DB_EXISTS || echo NO_DB",
        expect_code=None,
        expect_contains="DB_EXISTS",
    )

    # === Summary ===
    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    total = len(results)
    print(f"  SMOKE TEST RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n  Failed tests:")
        for name, status, details in results:
            if status == "FAIL":
                print(f"    - {name}: {details}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
