"""Download competition datasets from the OpenSky S3 (MinIO) bucket.

Reproduces what was done manually on the command line:
    mc alias set prc https://s3.opensky-network.org/ $PRC_ACCESS_KEY $PRC_SECRET_KEY
    mc mirror prc/prc-2026-datasets/ data/prc-2026-datasets/

Requires the `mc` (MinIO Client) binary on PATH or at ~/.local/bin/mc, and
PRC_S3_ENDPOINT / PRC_ACCESS_KEY / PRC_SECRET_KEY set in .env or the environment.

Usage:
    python src/download.py
"""
import subprocess
import sys

from config import BUCKET_DATASETS, DATA_DIR, EXPECTED_FILES
from mc import ALIAS, ensure_alias

MAX_ATTEMPTS = 3


def mirror(mc: str) -> None:
    remote = f"{ALIAS}/{BUCKET_DATASETS}/"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = subprocess.run([mc, "mirror", remote, f"{DATA_DIR}/"])
        if result.returncode == 0:
            return
        print(f"mc mirror attempt {attempt}/{MAX_ATTEMPTS} failed, retrying...", file=sys.stderr)
    raise SystemExit("mc mirror failed after all retries. Check network / credentials.")


def verify() -> None:
    present = {p.name for p in DATA_DIR.glob("*.parquet")}
    missing = EXPECTED_FILES - present
    if missing:
        raise SystemExit(f"Download incomplete, missing files: {sorted(missing)}")
    print(f"OK: all {len(EXPECTED_FILES)} expected files present in {DATA_DIR}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    mc = ensure_alias()
    mirror(mc)
    verify()


if __name__ == "__main__":
    main()
