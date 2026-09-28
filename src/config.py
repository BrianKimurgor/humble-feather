"""Project-wide paths and constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "prc-2026-datasets"
SUBMISSIONS_DIR = ROOT / "submissions"
ENV_FILE = ROOT / ".env"
RAW_DB_PATH = ROOT / "data" / "prc2026.duckdb"
CLEAN_DB_PATH = ROOT / "data" / "prc2026_clean.duckdb"
MODELS_DIR = ROOT / "data" / "models"
PREDICTIONS_DIR = ROOT / "data" / "predictions"

BUCKET_DATASETS = "prc-2026-datasets"
BUCKET_TEAM = "prc-2026-humble-feather"
TEAM_NAME = "humble-feather"

AIRPORTS = ["EDDF", "EDDM", "EGLL", "EHAM", "LEBL", "LEMD", "LFPG", "LIRF", "LTFM", "LSZH"]

TARGET = "TAXITIME_SEC_mvt"

EXPECTED_FILES = {
    "ranking.parquet",
    "submitting.parquet",
    "training_2025-01-01_2025-02-01.parquet",
    "training_2025-02-01_2025-03-01.parquet",
    "training_2025-03-01_2025-04-01.parquet",
    "training_2025-04-01_2025-05-01.parquet",
    "training_2025-05-01_2025-06-01.parquet",
    "training_2025-06-01_2025-07-01.parquet",
    "training_2025-07-01_2025-08-01.parquet",
    "training_2025-08-01_2025-09-01.parquet",
    "training_2025-09-01_2025-10-01.parquet",
    "training_2025-10-01_2025-11-01.parquet",
    "training_2025-11-01_2025-12-01.parquet",
    "training_2025-12-01_2026-01-01.parquet",
}
