"""
Application settings — configuration-driven, zero hardcoding.
"""
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent        # dvt_validation/
RUNS_DIR = BASE_DIR / "runs"
INPUT_DIR = BASE_DIR / "input"

# Ensure the runs directory exists at import time
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# ZIP Security Limits
# ---------------------------------------------------------------------------
MAX_ZIP_SIZE_BYTES: int = int(os.getenv("MAX_ZIP_SIZE_BYTES", 50 * 1024 * 1024))  # 50 MB
MAX_EXTRACTED_SIZE_BYTES: int = int(os.getenv("MAX_EXTRACTED_SIZE_BYTES", 200 * 1024 * 1024))  # 200 MB
MAX_FILE_COUNT: int = int(os.getenv("MAX_FILE_COUNT", 500))
MAX_PATH_DEPTH: int = int(os.getenv("MAX_PATH_DEPTH", 10))
ALLOWED_EXTENSIONS: set[str] = {".yaml", ".yml", ".conf", ".json", ".md", ".txt", ".sql", ".csv"}

# ---------------------------------------------------------------------------
# Validation Thresholds
# ---------------------------------------------------------------------------
# Column order comparison is only a WARNING, not an ERROR
COLUMN_ORDER_SEVERITY: str = os.getenv("COLUMN_ORDER_SEVERITY", "WARNING")
