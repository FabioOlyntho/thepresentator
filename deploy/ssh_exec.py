"""SSH remote execution helper for The Presentator deployment."""
import os
import sys
import time

import paramiko

HOST = os.environ.get("VPS_HOST", "82.25.117.157")
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ.get("VPS_PASSWORD", "")
SSH_KEY = os.environ.get("VPS_SSH_KEY", os.path.expanduser("~/.ssh/id_rsa"))

REMOTE_APP_DIR = "/var/www/presentator"


def _connect(client: paramiko.SSHClient) -> None:
    """Connect using SSH key (preferred) or password fallback."""
    if os.path.exists(SSH_KEY):
        client.connect(HOST, username=USER, key_filename=SSH_KEY, timeout=15)
    elif PASSWORD:
        client.connect(HOST, username=USER, password=PASSWORD, timeout=15)
    else:
        raise RuntimeError("No SSH key found and VPS_PASSWORD not set")


def ssh_exec(commands: str, timeout: int = 300) -> tuple[int, str]:
    """Execute commands on remote VPS via SSH. Returns (exit_code, output)."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    for attempt in range(3):
        try:
            _connect(client)
            break
        except Exception as e:
            if attempt < 2:
                print(f"SSH attempt {attempt + 1} failed: {e}, retrying...", file=sys.stderr)
                time.sleep(5)
            else:
                print(f"SSH failed after 3 attempts: {e}", file=sys.stderr)
                return 1, str(e)

    try:
        stdin, stdout, stderr = client.exec_command(commands, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        errors = stderr.read().decode("utf-8", errors="replace")
        if errors:
            output += "\nSTDERR:\n" + errors
        return exit_code, output
    finally:
        client.close()


def scp_upload(local_path: str, remote_path: str) -> bool:
    """Upload a file to the VPS via SCP."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    try:
        _connect(client)
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print(f"  Uploaded {local_path} -> {remote_path}")
        return True
    except Exception as e:
        print(f"SCP failed: {e}", file=sys.stderr)
        return False
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ssh_exec.py <command>")
        sys.exit(1)

    cmd = " ".join(sys.argv[1:])
    code, out = ssh_exec(cmd)
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    sys.exit(code)
