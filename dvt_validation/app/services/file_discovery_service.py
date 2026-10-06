"""
File Discovery Service — content-based and extension-driven identification.

Walks the extracted directory and classifies files into:
  1. Validation Contract (YAML/YML)
  2. SeaTunnel Execution Plan (.conf / HOCON)

Uses content heuristics first, and single-candidate extension fallback when appropriate.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app.models.preflight_models import Problem, Severity


# Signals for classification
_YAML_CONTRACT_SIGNALS = {
    "duckdb_jobs_version",
    "produced_by",
    "engine",
    "convention",
    "acquisition",
    "bindings",
    "job",
    "jobs",
    "summary",
    "source",
    "target",
    "version",
    "checks",
}

_SEATUNNEL_BLOCK_RE = re.compile(
    r"\b(source|sink|transform|env|job)\s*\{", re.MULTILINE
)


def _is_validation_yaml(path: Path) -> bool:
    """Return True if the YAML file looks like a validation contract."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    hits = _YAML_CONTRACT_SIGNALS & set(data.keys())
    # Accept if at least 1 strong signal key (like job, jobs, engine, source) exists
    return len(hits) >= 1


def _is_seatunnel_conf(path: Path) -> bool:
    """Return True if the file looks like a SeaTunnel HOCON config."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    blocks_found = set(_SEATUNNEL_BLOCK_RE.findall(text))
    # Standard SeaTunnel config has at least source OR sink OR env block
    return len(blocks_found.intersection({"source", "sink", "env", "transform", "job"})) >= 1


def discover_files(
    extracted_dir: Path,
) -> tuple[Path | None, Path | None, list[Problem]]:
    """
    Walk *extracted_dir* and return ``(yaml_path, conf_path, problems)``.
    """
    problems: list[Problem] = []
    yaml_candidates: list[Path] = []
    conf_candidates: list[Path] = []
    all_yamls: list[Path] = []
    all_confs: list[Path] = []

    for root, _dirs, files in extracted_dir.walk():
        for fname in files:
            fpath = root / fname
            suffix = fpath.suffix.lower()

            if suffix in {".yaml", ".yml"}:
                all_yamls.append(fpath)
                if _is_validation_yaml(fpath):
                    yaml_candidates.append(fpath)

            if suffix in {".conf", ".hocon"}:
                all_confs.append(fpath)
                if _is_seatunnel_conf(fpath):
                    conf_candidates.append(fpath)

    # Fallbacks if content signals didn't match but extension candidates exist
    if not yaml_candidates and len(all_yamls) == 1:
        yaml_candidates = all_yamls
    if not conf_candidates and len(all_confs) == 1:
        conf_candidates = all_confs

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
