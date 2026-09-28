"""Baseline model: median taxi-out time (TAXITIME_SEC_mvt) per airport.

Trains on every departure row in the clean `movements` table, unfiltered --
see docs/plan.md step 2 (decided 2026-09-21: no row exclusion by flag).

Not meant to be accurate. Meant to prove the training -> prediction ->
submission pipeline works end to end, and to give later models a floor to
beat.

Usage:
    python src/train.py
"""
import duckdb
import polars as pl

from config import MODELS_DIR, TARGET
from db import connect_clean

GLOBAL_KEY = "__global__"


def train_baseline(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Return a table of monitored_airport -> median TAXITIME_SEC_mvt, plus a
    '__global__' row (median over all departures) as a fallback for any
    airport with no training data."""
    dep = con.execute(f"SELECT monitored_airport, {TARGET} FROM movements WHERE PHASE_mvt = 'DEP'").pl()

    per_airport = dep.group_by("monitored_airport").agg(
        pl.col(TARGET).median().alias("prediction"),
        n=pl.len().cast(pl.Int64),
    )
    global_row = pl.DataFrame(
        {"monitored_airport": [GLOBAL_KEY], "prediction": [dep[TARGET].median()], "n": [dep.height]},
        schema={"monitored_airport": pl.Utf8, "prediction": pl.Float64, "n": pl.Int64},
    )
    return pl.concat([per_airport, global_row])


def main() -> None:
    con = connect_clean()
    medians = train_baseline(con)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MODELS_DIR / "baseline_medians.parquet"
    medians.write_parquet(out_path)

    print(medians.sort("monitored_airport"))
    print(f"\nOK: saved baseline model to {out_path}")


if __name__ == "__main__":
    main()
