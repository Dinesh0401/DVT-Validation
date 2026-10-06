"""
File Discovery Service — content-based identification.

Walks the extracted directory and classifies files by their **content
structure**, not by hardcoded filenames.

Classification heuristics
    YAML validation contract — has ``duckdb_jobs_version`` or ``job:`` at the
        top level *and* looks like a transpiler-generated validation file
        (``engine``, ``convention``, ``acquisition``, etc.).
    SeaTunnel .conf — contains top-level ``job {`` block with nested
        ``source {``, ``sink {`` blocks (HOCON structure).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app.models.preflight_models import Problem, Severity


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_YAML_CONTRACT_SIGNALS = {
    # At least TWO of these top-level keys must be present for us to classify
    # a YAML file as a validation contract.
    "duckdb_jobs_version",
    "produced_by",
    "engine",
    "convention",
    "acquisition",
    "bindings",
    "job",
    "summary",
}

_SEATUNNEL_RE = re.compile(
    r"^\s*job\s*\{", re.MULTILINE
)
_SEATUNNEL_BLOCK_RE = re.compile(
    r"\b(source|sink|transform|ddl|dml|env)\s*\{", re.MULTILINE
)


def _is_validation_yaml(path: Path) -> bool:
    """Return True if the YAML file looks like a transpiler validation contract."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    hits = _YAML_CONTRACT_SIGNALS & set(data.keys())
    return len(hits) >= 3  # need at least 3 matching keys


def _is_seatunnel_conf(path: Path) -> bool:
    """Return True if the file looks like a SeaTunnel HOCON config."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    if not _SEATUNNEL_RE.search(text):
        return False
    # Must also contain at least source+sink
    blocks_found = set(_SEATUNNEL_BLOCK_RE.findall(text))
    return {"source", "sink"}.issubset(blocks_found)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_files(
    extracted_dir: Path,
) -> tuple[Path | None, Path | None, list[Problem]]:
    """
    Walk *extracted_dir* and return ``(yaml_path, conf_path, problems)``.

    Raises problems if files cannot be uniquely identified.
    """
    problems: list[Problem] = []
    yaml_candidates: list[Path] = []
    conf_candidates: list[Path] = []

    for root, _dirs, files in extracted_dir.walk():
        for fname in files:
            fpath = root / fname
            suffix = fpath.suffix.lower()

            if suffix in {".yaml", ".yml"}:
                if _is_validation_yaml(fpath):
                    yaml_candidates.append(fpath)

            if suffix == ".conf":
                if _is_seatunnel_conf(fpath):
                    conf_candidates.append(fpath)

    # ---- YAML resolution ----
    yaml_path: Path | None = None
    if len(yaml_candidates) == 0:
        problems.append(Problem(
            type="MISSING_INPUT",
            severity=Severity.ERROR,
            message="Could not identify validation YAML in the extracted ZIP.",
            stage="file_discovery",
        ))
    elif len(yaml_candidates) > 1:
        names = [str(c.relative_to(extracted_dir)) for c in yaml_candidates]
        problems.append(Problem(
            type="AMBIGUOUS_INPUT",
            severity=Severity.ERROR,
            message=f"Multiple possible validation YAML files found: {names}",
            stage="file_discovery",
        ))
    else:
        yaml_path = yaml_candidates[0]

    # ---- .conf resolution ----
    conf_path: Path | None = None
    if len(conf_candidates) == 0:
        problems.append(Problem(
            type="MISSING_INPUT",
            severity=Severity.ERROR,
            message="Could not identify SeaTunnel .conf file in the extracted ZIP.",
            stage="file_discovery",
        ))
    elif len(conf_candidates) > 1:
        names = [str(c.relative_to(extracted_dir)) for c in conf_candidates]
        problems.append(Problem(
            type="AMBIGUOUS_INPUT",
            severity=Severity.ERROR,
            message=f"Multiple possible SeaTunnel .conf files found: {names}",
            stage="file_discovery",
        ))
    else:
        conf_path = conf_candidates[0]

    return yaml_path, conf_path, problems
