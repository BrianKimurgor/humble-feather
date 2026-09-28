"""Time-based validation strategy. See docs/plan.md and docs/validation_strategy.md.

Ranking data is Jan + Jul 2026; training data is all of 2025. A random row
split would hide how badly a model generalizes across time, so validation
holds out whole months instead of rows.

Deliberately out of scope: whether flagged rows are included or excluded
from training. That is a row-filtering policy decision (docs/plan.md step 2),
kept separate from the time-based split mechanism here. Every function in
this module operates on whatever rows it's given.
"""
from dataclasses import dataclass

import duckdb
import polars as pl

FOLDS = {
    "jan": {
        "val_months": (1,),
        "description": "train on Feb-Dec 2025, validate on Jan 2025 (mimics ranking Jan 2026)",
    },
    "jul": {
        "val_months": (7,),
        "description": "train on all months except Jul 2025, validate on Jul 2025 (mimics ranking Jul 2026)",
    },
}


@dataclass
class Fold:
    name: str
    train: pl.DataFrame
    val: pl.DataFrame


def _month_filter(months: tuple[int, ...], negate: bool) -> str:
    months_sql = ",".join(str(m) for m in months)
    op = "NOT IN" if negate else "IN"
    return f"EXTRACT(MONTH FROM BLOCK_TIME_UTC_mvt) {op} ({months_sql})"


def load_fold(con: duckdb.DuckDBPyConnection, fold: str) -> Fold:
    """Fetch the train/val DEP rows for a named fold from the clean `movements` table."""
    if fold not in FOLDS:
        raise ValueError(f"Unknown fold {fold!r}, expected one of {list(FOLDS)}")

    val_months = FOLDS[fold]["val_months"]
    base = "SELECT * FROM movements WHERE PHASE_mvt = 'DEP'"

    train = con.execute(f"{base} AND {_month_filter(val_months, negate=True)}").pl()
    val = con.execute(f"{base} AND {_month_filter(val_months, negate=False)}").pl()

    return Fold(name=fold, train=train, val=val)


def rmse(y_true: pl.Series, y_pred: pl.Series) -> float:
    diff = y_true - y_pred
    return float((diff.pow(2).mean()) ** 0.5)


def rmse_by_airport(val: pl.DataFrame, y_pred: pl.Series, target_col: str = "TAXITIME_SEC_mvt") -> pl.DataFrame:
    """RMSE per monitored_airport, for error analysis."""
    df = val.select("monitored_airport", target_col).with_columns(pred=y_pred)
    return (
        df.group_by("monitored_airport")
        .agg(
            n=pl.len(),
            rmse=((pl.col(target_col) - pl.col("pred")) ** 2).mean().sqrt(),
        )
        .sort("monitored_airport")
    )
