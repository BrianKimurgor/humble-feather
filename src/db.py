"""DuckDB connections.

Two sources, kept distinct:
- connect_raw()   -- live views straight over the raw Parquet files, nothing
                      derived, nothing flagged. For auditing the source data.
- connect_clean() -- the materialized tables built by clean.py: same rows
                      as raw (nothing dropped) plus monitored_airport /
                      counterpart_airport / flag_* columns. Everything past
                      the data-audit stage (validation, features, training)
                      should read from here, not from raw.
"""
import duckdb

from config import CLEAN_DB_PATH, DATA_DIR


def connect_raw() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")

    training_glob = str(DATA_DIR / "training_*.parquet")
    con.execute(f"CREATE VIEW movements AS SELECT * FROM read_parquet('{training_glob}', union_by_name=true)")
    con.execute(f"CREATE VIEW ranking AS SELECT * FROM read_parquet('{DATA_DIR / 'ranking.parquet'}')")
    con.execute(f"CREATE VIEW submitting AS SELECT * FROM read_parquet('{DATA_DIR / 'submitting.parquet'}')")

    return con


def connect_clean(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(CLEAN_DB_PATH), read_only=read_only)
    con.execute("SET TimeZone='UTC'")
    return con


# Backwards-compatible alias -- earlier exploration used connect() for the raw views.
connect = connect_raw


if __name__ == "__main__":
    con = connect_clean()
    for table in ("movements", "ranking", "submitting"):
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count:,} rows")
