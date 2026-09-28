"""Build the clean database from raw Parquet.

Non-destructive by design: nothing is dropped or overwritten in the raw data.
This script only ADDS derived columns (monitored_airport, counterpart_airport)
and flag columns for issues found during the data audit (docs/data_dictionary.md).
Rows are never deleted and no value is ever modified -- suspicious rows are
flagged, not removed, so downstream modeling decides how to handle them.

Output: a separate DuckDB file (config.CLEAN_DB_PATH), so the raw database
(config.RAW_DB_PATH) and the original Parquet files are never touched.

Usage:
    python src/clean.py
"""
import duckdb

from config import CLEAN_DB_PATH, DATA_DIR

# Columns added on top of every raw column, for both `movements` and `ranking`
# (both share the same 30-column schema -- confirmed during the data audit).
DERIVED_COLUMNS = """
    CASE WHEN PHASE_mvt = 'DEP' THEN ADEP_mvt ELSE ADES_mvt END AS monitored_airport,
    CASE WHEN PHASE_mvt = 'DEP' THEN ADES_mvt ELSE ADEP_mvt END AS counterpart_airport,
    (TAXITIME_SEC_mvt <= 0) AS flag_taxitime_nonpositive,
    (TAXITIME_SEC_mvt > 10800) AS flag_taxitime_gt_3h,
    (TAXITIME_SEC_mvt > 86400) AS flag_taxitime_gt_24h,
    (LOBT_flt IS NULL) AS flag_flt_unmatched
"""


def build(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("SET TimeZone='UTC'")

    training_glob = str(DATA_DIR / "training_*.parquet")
    con.execute(f"""
        CREATE OR REPLACE TABLE movements AS
        SELECT *, {DERIVED_COLUMNS}
        FROM read_parquet('{training_glob}', union_by_name=true)
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE ranking AS
        SELECT *, {DERIVED_COLUMNS}
        FROM read_parquet('{DATA_DIR / "ranking.parquet"}')
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE submitting AS
        SELECT * FROM read_parquet('{DATA_DIR / "submitting.parquet"}')
    """)


def summarize(con: duckdb.DuckDBPyConnection) -> None:
    for table in ("movements", "ranking", "submitting"):
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count:,} rows")

    print()
    print("Flag counts (movements, DEP rows only):")
    row = con.execute("""
        SELECT
            SUM(flag_taxitime_nonpositive::INT) AS nonpositive,
            SUM(flag_taxitime_gt_3h::INT) AS gt_3h,
            SUM(flag_taxitime_gt_24h::INT) AS gt_24h,
            SUM(flag_flt_unmatched::INT) AS flt_unmatched
        FROM movements WHERE PHASE_mvt = 'DEP'
    """).fetchone()
    print(f"  taxitime <= 0:     {row[0]:,}")
    print(f"  taxitime > 3h:     {row[1]:,}")
    print(f"  taxitime > 24h:    {row[2]:,}")
    print(f"  flt unmatched:     {row[3]:,}")


def main() -> None:
    con = duckdb.connect(str(CLEAN_DB_PATH))
    build(con)
    summarize(con)
    con.close()
    print(f"\nOK: clean database written to {CLEAN_DB_PATH}")


if __name__ == "__main__":
    main()
