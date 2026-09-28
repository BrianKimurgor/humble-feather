"""Shared helpers for talking to the OpenSky S3 (MinIO) bucket via the mc CLI.

Used by download.py (pull the dataset bucket) and submit.py (upload a
submission) -- both need the same mc binary, the same .env credentials,
and the same alias.
"""
import os
import shutil
import subprocess
from pathlib import Path

from config import ENV_FILE

ALIAS = "prc"


def load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def find_mc() -> str:
    for candidate in (shutil.which("mc"), str(Path.home() / ".local/bin/mc")):
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit(
        "mc (MinIO Client) not found on PATH or in ~/.local/bin. "
        "Install it from https://github.com/minio/mc/releases before running this script."
    )


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}. Set it in .env or the environment.")
    return value


def ensure_alias() -> str:
    """Load credentials, find mc, and set the 'prc' alias. Returns the mc binary path."""
    load_env_file()
    mc = find_mc()
    endpoint = require_env("PRC_S3_ENDPOINT")
    access_key = require_env("PRC_ACCESS_KEY")
    secret_key = require_env("PRC_SECRET_KEY")
    subprocess.run([mc, "alias", "set", ALIAS, endpoint, access_key, secret_key], check=True)
    return mc
