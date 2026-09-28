"""Apply a trained model to the ranking set's departure rows.

Reads the model artifact produced by train.py -- doesn't know or care how
those predictions were derived, only how to join them onto ranking rows.

Usage:
    python src/predict.py
"""
import duckdb
import polars as pl

from config import MODELS_DIR, PREDICTIONS_DIR, TARGET
from db import connect_clean
from train import GLOBAL_KEY


def predict_baseline(con: duckdb.DuckDBPyConnection, medians: pl.DataFrame) -> pl.DataFrame:
    """Return MVT_ID_mvt + predicted TAXITIME_SEC_mvt for every departure in `ranking`."""
    dep = con.execute("SELECT MVT_ID_mvt, monitored_airport FROM ranking WHERE PHASE_mvt = 'DEP'").pl()

    global_median = medians.filter(pl.col("monitored_airport") == GLOBAL_KEY)["prediction"][0]
    lookup = medians.filter(pl.col("monitored_airport") != GLOBAL_KEY).select("monitored_airport", "prediction")

    joined = dep.join(lookup, on="monitored_airport", how="left")
    joined = joined.with_columns(
        pl.col("prediction").fill_null(global_median).round(0).cast(pl.Int32).alias(TARGET)
    )
    return joined.select("MVT_ID_mvt", TARGET)


def main() -> None:
    con = connect_clean()
    medians = pl.read_parquet(MODELS_DIR / "baseline_medians.parquet")
    predictions = predict_baseline(con, medians)

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREDICTIONS_DIR / "baseline_v1.parquet"
    predictions.write_parquet(out_path)

    print(f"predictions: {predictions.height:,} rows")
    print(predictions.describe())
    print(f"\nOK: saved predictions to {out_path}")


if __name__ == "__main__":
    main()
