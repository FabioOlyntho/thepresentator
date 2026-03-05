"""
Write Traefik routing config for The Presentator.

One-time setup: creates /etc/traefik/dynamic/presentator.yml on the VPS.
Traefik auto-detects file changes — no restart needed.

Usage:
    set VPS_PASSWORD=<password>
    python deploy/traefik_config.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from ssh_exec import ssh_exec, scp_upload

TRAEFIK_CONFIG = """\
http:
  routers:
    presentator:
      rule: "Host(`presentator.humanaie.com`)"
      entryPoints:
        - websecure
      service: presentator
      tls:
        certResolver: letsencryptresolver
    presentator-http:
      rule: "Host(`presentator.humanaie.com`)"
      entryPoints:
        - web
      middlewares:
        - redirect-to-https
      service: presentator
  services:
    presentator:
      loadBalancer:
        servers:
          - url: "http://host.docker.internal:8001"
"""

REMOTE_PATH = "/etc/traefik/dynamic/presentator.yml"


def main():
    print("=" * 60)
    print("  The Presentator — Traefik Configuration")
    print("=" * 60)

    # Verify SSH connectivity
    code, out = ssh_exec("echo CONNECTED", timeout=15)
    if "CONNECTED" not in out:
        print(f"ERROR: Cannot connect to VPS. Output: {out}")
        sys.exit(1)
    print("  Connected to VPS")

    # Check Traefik dynamic dir exists
    code, out = ssh_exec("ls /etc/traefik/dynamic/ 2>/dev/null && echo DIR_OK", timeout=15)
    if "DIR_OK" not in out:
        print("ERROR: /etc/traefik/dynamic/ does not exist. Is Traefik installed?")
        sys.exit(1)

    # Check if config already exists
    code, out = ssh_exec(f"test -f {REMOTE_PATH} && echo EXISTS || echo NEW", timeout=15)
    if "EXISTS" in out:
        print(f"  Config already exists at {REMOTE_PATH} — will overwrite")
    else:
        print(f"  Creating new config at {REMOTE_PATH}")

    # Write config via temp file + SCP
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(TRAEFIK_CONFIG)
        tmp_path = f.name

    try:
        if not scp_upload(tmp_path, REMOTE_PATH):
            print("FATAL: Failed to upload Traefik config")
            sys.exit(1)
    finally:
        os.unlink(tmp_path)

    # Verify config was written
    code, out = ssh_exec(f"cat {REMOTE_PATH}", timeout=15)
    if "presentator.humanaie.com" in out:
        print(f"\n  Traefik config written to {REMOTE_PATH}")
        print("  Traefik will auto-detect the new config (file provider)")
        print("\n  NOTE: Ensure DNS A record exists:")
        print("    presentator -> 82.25.117.157")
    else:
        print(f"ERROR: Config verification failed. Content:\n{out[:500]}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  TRAEFIK CONFIGURATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
