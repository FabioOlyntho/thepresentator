"""
Deployment script for The Presentator.

Deploys to VPS 82.25.117.157 using tarball+SCP+SSH pattern.
Existing infrastructure: PM2 + Traefik (shared VPS).
No PostgreSQL — uses SQLite.

Usage:
    set VPS_PASSWORD=<password>
    python deploy/deploy.py [--skip-backup] [--first-deploy]

Steps:
    1. Build tarball (backend/, scripts/, frontend/dist/, config/, prompts/, requirements*.txt)
    2. SCP upload to /tmp/presentator-deploy.tar.gz
    3. Pre-deploy backup (current code)
    4. Extract + install Python dependencies
    5. Restart PM2 process
    6. Health check validation
    7. Auto-rollback on failure
"""
import os
import sys
import tarfile
import tempfile
import time

sys.path.insert(0, os.path.dirname(__file__))
from ssh_exec import ssh_exec, scp_upload, REMOTE_APP_DIR

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

REMOTE_TARBALL = "/tmp/presentator-deploy.tar.gz"
PM2_PROCESS = "presentator"
BACKUP_DIR = "/var/backups/presentator"
HEALTH_URL = "http://localhost:8001/api/v1/health"


def safe_print(text: str):
    """Print text safely on Windows (cp1252 can't encode some UTF-8 chars)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def step(num: int, label: str):
    print(f"\n{'=' * 60}")
    print(f"  Step {num}: {label}")
    print(f"{'=' * 60}\n")


def build_tarball() -> str:
    """Create deployment tarball."""
    step(1, "Building deployment tarball")

    tarball_path = os.path.join(tempfile.gettempdir(), "presentator-deploy.tar.gz")

    include_dirs = [
        ("backend", "backend"),
        ("scripts", "scripts"),
        ("frontend/dist", "frontend/dist"),
        ("config", "config"),
        ("prompts", "prompts"),
    ]
    include_files = [
        ("requirements.txt", "requirements.txt"),
        ("requirements-web.txt", "requirements-web.txt"),
    ]

    # Exclude patterns
    exclude_suffixes = (".pyc", "__pycache__", ".pytest_cache")

    def tar_filter(tarinfo):
        for suffix in exclude_suffixes:
            if suffix in tarinfo.name:
                return None
        return tarinfo

    # Validate required paths
    for local_dir, _arc_dir in include_dirs:
        full_path = os.path.join(PROJECT_ROOT, local_dir)
        if not os.path.exists(full_path):
            print(f"  FATAL: Required directory missing: {full_path}")
            sys.exit(1)

    for local_file, _arc_name in include_files:
        full_path = os.path.join(PROJECT_ROOT, local_file)
        if not os.path.exists(full_path):
            print(f"  FATAL: Required file missing: {full_path}")
            sys.exit(1)

    with tarfile.open(tarball_path, "w:gz") as tar:
        for local_dir, arc_dir in include_dirs:
            full_path = os.path.join(PROJECT_ROOT, local_dir)
            tar.add(full_path, arcname=arc_dir, filter=tar_filter)
            print(f"  Added {local_dir}/ -> {arc_dir}/")

        for local_file, arc_name in include_files:
            full_path = os.path.join(PROJECT_ROOT, local_file)
            tar.add(full_path, arcname=arc_name)
            print(f"  Added {local_file} -> {arc_name}")

    size_mb = os.path.getsize(tarball_path) / (1024 * 1024)
    print(f"\n  Tarball: {tarball_path} ({size_mb:.2f} MB)")
    return tarball_path


def upload_tarball(tarball_path: str) -> bool:
    """Upload tarball to VPS."""
    step(2, "Uploading tarball to VPS")
    return scp_upload(tarball_path, REMOTE_TARBALL)


def pre_deploy_backup(skip: bool = False) -> bool:
    """Backup current deployment."""
    step(3, "Pre-deploy backup")

    if skip:
        print("  Skipped (--skip-backup)")
        return True

    cmds = f"""
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p {BACKUP_DIR}

# Backup current code (if exists)
if [ -d {REMOTE_APP_DIR}/backend ]; then
    tar czf {BACKUP_DIR}/code_$TIMESTAMP.tar.gz -C {REMOTE_APP_DIR} backend scripts frontend/dist config prompts requirements.txt requirements-web.txt 2>/dev/null || true
    echo "Code backup: {BACKUP_DIR}/code_$TIMESTAMP.tar.gz"
fi

# Backup SQLite database (if exists)
if [ -f {REMOTE_APP_DIR}/data/presentator.db ]; then
    cp {REMOTE_APP_DIR}/data/presentator.db {BACKUP_DIR}/presentator_$TIMESTAMP.db
    echo "DB backup: {BACKUP_DIR}/presentator_$TIMESTAMP.db"
fi

# Clean old backups (keep 7 days)
find {BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
find {BACKUP_DIR} -name "*.db" -mtime +7 -delete 2>/dev/null || true

echo "BACKUP_OK"
"""
    code, out = ssh_exec(cmds, timeout=120)
    safe_print(out)
    return "BACKUP_OK" in out


def first_deploy_setup() -> bool:
    """One-time VPS setup for first deployment."""
    step(0, "First deployment setup")

    cmds = f"""
set -e

# Create app directory
mkdir -p {REMOTE_APP_DIR}/data

# Create Python venv
if [ ! -d {REMOTE_APP_DIR}/venv ]; then
    python3.12 -m venv {REMOTE_APP_DIR}/venv
    echo "Created venv"
else
    echo "Venv already exists"
fi

# Verify Python version
{REMOTE_APP_DIR}/venv/bin/python --version

# Create .env if it doesn't exist
if [ ! -f {REMOTE_APP_DIR}/.env ]; then
    cat > {REMOTE_APP_DIR}/.env << 'ENVEOF'
GEMINI_API_KEY=
HOST=0.0.0.0
PORT=8001
ENVEOF
    chmod 600 {REMOTE_APP_DIR}/.env
    echo "Created .env — IMPORTANT: Set GEMINI_API_KEY manually!"
else
    echo ".env already exists"
fi

echo "SETUP_OK"
"""
    code, out = ssh_exec(cmds, timeout=120)
    safe_print(out)
    return "SETUP_OK" in out


def extract_and_install() -> bool:
    """Extract tarball and install dependencies."""
    step(4, "Extracting and installing")

    cmds = f"""
set -e

# Stop PM2 to avoid serving mixed old/new code
echo "Stopping PM2 process..."
pm2 stop {PM2_PROCESS} 2>/dev/null || true

# Extract tarball
echo "Extracting tarball..."
cd {REMOTE_APP_DIR}
tar xzf {REMOTE_TARBALL} --overwrite

# Set permissions
chown -R root:root {REMOTE_APP_DIR}/backend {REMOTE_APP_DIR}/scripts 2>/dev/null || true
chmod 600 {REMOTE_APP_DIR}/.env 2>/dev/null || true
echo "EXTRACT_OK"

# Install/update dependencies
echo "Installing dependencies..."
{REMOTE_APP_DIR}/venv/bin/pip install -q -r {REMOTE_APP_DIR}/requirements.txt -r {REMOTE_APP_DIR}/requirements-web.txt
echo "DEPS_OK"

# Cleanup tarball
rm -f {REMOTE_TARBALL}

echo "INSTALL_OK"
"""
    code, out = ssh_exec(cmds, timeout=600)
    safe_print(out)
    return "INSTALL_OK" in out


def restart_pm2() -> bool:
    """Restart PM2 process."""
    step(5, "Restarting PM2 process")

    cmds = f"""
set -e

# Check if process exists
if pm2 describe {PM2_PROCESS} > /dev/null 2>&1; then
    pm2 restart {PM2_PROCESS}
    echo "Restarted existing PM2 process"
else
    cd {REMOTE_APP_DIR}
    pm2 start {REMOTE_APP_DIR}/venv/bin/uvicorn \\
        --name {PM2_PROCESS} \\
        --interpreter none \\
        --cwd {REMOTE_APP_DIR} \\
        -- backend.main:app --host 0.0.0.0 --port 8001 --workers 2
    echo "Started new PM2 process"
fi

pm2 save
sleep 3

# Show status
pm2 show {PM2_PROCESS} --no-color 2>&1 | head -20
echo "PM2_OK"
"""
    code, out = ssh_exec(cmds, timeout=60)
    safe_print(out)
    return "PM2_OK" in out


def health_check() -> bool:
    """Validate deployment via health endpoint."""
    step(6, "Health check validation")

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        print(f"  Attempt {attempt}/{max_retries}...")
        code, out = ssh_exec(
            f"curl -sf {HEALTH_URL} --max-time 10 2>&1",
            timeout=30,
        )
        out = out.strip()
        if '"status":"ok"' in out or '"status": "ok"' in out:
            print(f"  Health check PASSED: {out}")
            return True
        print(f"  Not ready: {out[:200]}")
        if attempt < max_retries:
            time.sleep(5)

    print("  Health check FAILED after all retries")
    return False


def auto_rollback():
    """Restore from latest backup on failure."""
    print("\nWARNING: Health check failed — auto-restoring code backup")
    rc, out = ssh_exec(
        f"""
LATEST_CODE=$(ls -t {BACKUP_DIR}/code_*.tar.gz 2>/dev/null | head -1)
if [ -n "$LATEST_CODE" ]; then
    cd {REMOTE_APP_DIR} && tar xzf "$LATEST_CODE" && echo CODE_ROLLBACK_OK
else
    echo NO_BACKUP_FOUND
fi
""",
        timeout=60,
    )
    if "CODE_ROLLBACK_OK" in out:
        print("  Code restored from backup. Restarting PM2...")
        ssh_exec(f"pm2 restart {PM2_PROCESS} && pm2 save", timeout=30)
    else:
        safe_print(f"  Auto-rollback failed: {out[:300]}")


def main():
    skip_backup = "--skip-backup" in sys.argv
    first_deploy = "--first-deploy" in sys.argv

    print("=" * 60)
    print("  The Presentator — Deployment")
    print(f"  Target: {REMOTE_APP_DIR} on 82.25.117.157")
    print("=" * 60)

    # Verify SSH connectivity
    code, out = ssh_exec("echo CONNECTED && hostname", timeout=15)
    if "CONNECTED" not in out:
        print(f"ERROR: Cannot connect to VPS. Output: {out}")
        sys.exit(1)
    print(f"  Connected to VPS: {out.strip()}")

    # Acquire deploy lock
    code, out = ssh_exec(
        'LOCKFILE=/tmp/presentator-deploy.lock; '
        'if [ -f "$LOCKFILE" ]; then echo DEPLOY_LOCKED; '
        'else echo $$ > "$LOCKFILE" && echo LOCK_OK; fi',
        timeout=15,
    )
    if "DEPLOY_LOCKED" in out:
        print("FATAL: Another deployment is in progress (lock file exists)")
        print("  If stale, remove: python deploy/ssh_exec.py 'rm /tmp/presentator-deploy.lock'")
        sys.exit(1)

    try:
        _deploy_pipeline(skip_backup, first_deploy)
    finally:
        # Always release deploy lock
        ssh_exec("rm -f /tmp/presentator-deploy.lock", timeout=15)


def _deploy_pipeline(skip_backup: bool, first_deploy: bool):
    """Run the deployment pipeline (called within lock)."""
    # First-deploy setup (venv, .env, data dir)
    if first_deploy:
        if not first_deploy_setup():
            print("FATAL: First deploy setup failed")
            sys.exit(1)

    # Build and upload tarball
    tarball_path = build_tarball()

    if not upload_tarball(tarball_path):
        print("FATAL: Upload failed")
        sys.exit(1)

    # Backup (skip on first deploy)
    if not pre_deploy_backup(skip=skip_backup or first_deploy):
        print("FATAL: Backup failed — aborting deployment")
        sys.exit(1)

    if not extract_and_install():
        print("FATAL: Install failed")
        sys.exit(1)

    if not restart_pm2():
        print("FATAL: PM2 restart failed")
        sys.exit(1)

    if not health_check():
        auto_rollback()
        sys.exit(1)

    # Save PM2 config for persistence across reboots
    ssh_exec("pm2 save", timeout=15)

    print("\n" + "=" * 60)
    print("  DEPLOYMENT SUCCESSFUL")
    print(f"  URL: https://presentator.humanaie.com")
    print(f"  API: https://presentator.humanaie.com/api/v1/health")
    print("=" * 60)

    # Cleanup local tarball
    os.remove(tarball_path)


if __name__ == "__main__":
    main()
