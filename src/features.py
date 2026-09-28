"""Feature engineering, shared between training and prediction.

Categorical encoding must be identical between train and predict time --
codes are fit once on training data (fit_encoders) and reused everywhere
else (apply_encoders), never refit on validation or ranking data. An
unseen category at predict time maps to UNKNOWN_CODE rather than crashing.

Time features are derived from SCHED_TIME_UTC_mvt (the *scheduled* time),
not actual block/takeoff time -- scheduled time is known for every
departure in `ranking` too, so this stays leakage-free
(see docs/data_dictionary.md).
"""
import polars as pl

CATEGORICAL_COLUMNS = [
    "monitored_airport",
    "counterpart_airport",
    "WK_TBL_CAT_flt",
    "AIRCRAFT_TYPE_mvt",
    "MARKET_SEGMENT_flt",
    "AIRCRAFT_OPERATOR_flt",
]

NUMERIC_COLUMNS = ["sched_hour", "sched_weekday", "sched_month", "flag_flt_unmatched"]

FEATURE_COLUMNS = CATEGORICAL_COLUMNS + NUMERIC_COLUMNS

UNKNOWN_CODE = -1
NULL_SENTINEL = "__null__"


def add_time_features(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("SCHED_TIME_UTC_mvt").dt.hour().alias("sched_hour"),
        pl.col("SCHED_TIME_UTC_mvt").dt.weekday().alias("sched_weekday"),
        pl.col("SCHED_TIME_UTC_mvt").dt.month().alias("sched_month"),
        pl.col("flag_flt_unmatched").cast(pl.Int8),
    )


def fit_encoders(train: pl.DataFrame) -> dict[str, dict[str, int]]:
    """Build a value -> integer code mapping per categorical column, from
    training data only."""
    encoders = {}
    for col in CATEGORICAL_COLUMNS:
        values = train[col].fill_null(NULL_SENTINEL).unique().sort().to_list()
        encoders[col] = {v: i for i, v in enumerate(values)}
    return encoders


def apply_encoders(df: pl.DataFrame, encoders: dict[str, dict[str, int]]) -> pl.DataFrame:
    df = df.clone()
    for col, mapping in encoders.items():
        df = df.with_columns(
            pl.col(col)
            .fill_null(NULL_SENTINEL)
            .replace_strict(mapping, default=UNKNOWN_CODE, return_dtype=pl.Int32)
            .alias(col)
        )
    return df


def build_matrix(df: pl.DataFrame, encoders: dict[str, dict[str, int]]) -> pl.DataFrame:
    df = add_time_features(df)
    df = apply_encoders(df, encoders)
    return df.select(FEATURE_COLUMNS)
