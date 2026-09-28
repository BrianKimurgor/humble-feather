"""Build, validate, and upload a submission file.

Submission naming per the OpenSky approval email: humble-feather_vN.parquet.

Deliberately split in two: `main()` builds and validates the file locally
and stops there. Uploading to the team's bucket is a separate, explicit
step (upload_submission) -- that's a real submission to the competition,
not something to do silently as a side effect of running this script.

Usage:
    python src/submit.py            # build + validate + write locally
    python src/submit.py --upload   # also upload the result
"""
import subprocess
import sys
from pathlib import Path

import duckdb
import polars as pl

from config import BUCKET_TEAM, PREDICTIONS_DIR, SUBMISSIONS_DIR, TARGET, TEAM_NAME
from db import connect_clean
from mc import ALIAS, ensure_alias


def build_submission(con: duckdb.DuckDBPyConnection, predictions: pl.DataFrame) -> pl.DataFrame:
    """Join predictions onto the official template and validate before returning."""
    template = con.execute("SELECT MVT_ID_mvt FROM submitting").pl()

    submission = template.join(predictions, on="MVT_ID_mvt", how="left")

    if submission.height != template.height:
        raise ValueError(f"row count mismatch: template has {template.height}, got {submission.height}")

    missing = submission.filter(pl.col(TARGET).is_null()).height
    if missing:
        raise ValueError(f"{missing} rows have no prediction -- refusing to write an incomplete submission")

    return submission.select("MVT_ID_mvt", TARGET).with_columns(pl.col(TARGET).cast(pl.Int32))


def write_submission(submission: pl.DataFrame, version: int) -> Path:
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SUBMISSIONS_DIR / f"{TEAM_NAME}_v{version}.parquet"
    submission.write_parquet(path)
    return path


def upload_submission(path: Path) -> None:
    mc = ensure_alias()
    remote = f"{ALIAS}/{BUCKET_TEAM}/{path.name}"
    subprocess.run([mc, "cp", str(path), remote], check=True)


def main(version: int = 1, upload: bool = False) -> None:
    con = connect_clean()
    predictions = pl.read_parquet(PREDICTIONS_DIR / "baseline_v1.parquet")

    submission = build_submission(con, predictions)
    path = write_submission(submission, version)
    print(f"OK: wrote {path} ({submission.height:,} rows, validated: no nulls, row count matches template)")

    if upload:
        upload_submission(path)
        print(f"OK: uploaded to {ALIAS}/{BUCKET_TEAM}/{path.name}")
    else:
        print(f"Not uploaded. Re-run with --upload to upload to {ALIAS}/{BUCKET_TEAM}/")


if __name__ == "__main__":
    main(upload="--upload" in sys.argv)
