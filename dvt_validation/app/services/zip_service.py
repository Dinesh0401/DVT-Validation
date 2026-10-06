"""
ZIP Service — secure extraction with run isolation.

Responsibilities
    • Create a unique run directory
    • Validate ZIP safety (traversal, size, duplicates)
    • Extract into an isolated directory
"""
from __future__ import annotations

import os
import uuid
import zipfile
from pathlib import Path

from app.config.settings import (
    ALLOWED_EXTENSIONS,
    MAX_EXTRACTED_SIZE_BYTES,
    MAX_FILE_COUNT,
    MAX_PATH_DEPTH,
    MAX_ZIP_SIZE_BYTES,
    RUNS_DIR,
)
from app.models.preflight_models import Problem, Severity


def _make_run_dir(run_id: str) -> dict[str, Path]:
    """Create ``runs/<run_id>/{uploaded,extracted,reports}`` and return paths."""
    base = RUNS_DIR / run_id
    dirs = {
        "base": base,
        "uploaded": base / "uploaded",
        "extracted": base / "extracted",
        "reports": base / "reports",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def extract_zip(zip_bytes: bytes, original_filename: str) -> tuple[str, dict[str, Path], list[Problem]]:
    """
    Accept raw ZIP bytes, validate safety, extract, and return
    ``(run_id, paths_dict, problems)``.

    If *problems* contains any ERROR-severity item the caller should abort.
    """
    run_id = uuid.uuid4().hex[:12]
    dirs = _make_run_dir(run_id)
    problems: list[Problem] = []

    # ---- save the uploaded file ----
    uploaded_path = dirs["uploaded"] / original_filename
    uploaded_path.write_bytes(zip_bytes)

    # ---- size gate ----
    if len(zip_bytes) > MAX_ZIP_SIZE_BYTES:
        problems.append(Problem(
            type="ZIP_TOO_LARGE",
            severity=Severity.ERROR,
            message=f"ZIP file is {len(zip_bytes):,} bytes, exceeds limit of {MAX_ZIP_SIZE_BYTES:,} bytes.",
            stage="zip_extraction",
        ))
        return run_id, dirs, problems

    # ---- open & validate entries ----
    try:
        zf = zipfile.ZipFile(uploaded_path, "r")
    except zipfile.BadZipFile:
        problems.append(Problem(
            type="INVALID_ZIP",
            severity=Severity.ERROR,
            message="Uploaded file is not a valid ZIP archive.",
            stage="zip_extraction",
        ))
        return run_id, dirs, problems

    with zf:
        infos = zf.infolist()

        # file count
        if len(infos) > MAX_FILE_COUNT:
            problems.append(Problem(
                type="TOO_MANY_FILES",
                severity=Severity.ERROR,
                message=f"ZIP contains {len(infos)} entries, exceeds limit of {MAX_FILE_COUNT}.",
                stage="zip_extraction",
            ))
            return run_id, dirs, problems

        total_uncompressed = 0
        seen_names: set[str] = set()

        for info in infos:
            name = info.filename

            # --- path traversal / absolute path ---
            if name.startswith("/") or name.startswith("\\"):
                problems.append(Problem(
                    type="ABSOLUTE_PATH",
                    severity=Severity.ERROR,
                    message=f"ZIP entry has an absolute path: '{name}'.",
                    stage="zip_extraction",
                ))
            if ".." in name.split("/") or ".." in name.split("\\"):
                problems.append(Problem(
                    type="PATH_TRAVERSAL",
                    severity=Severity.ERROR,
                    message=f"ZIP entry contains path traversal: '{name}'.",
                    stage="zip_extraction",
                ))

            # --- depth ---
            depth = len(Path(name).parts)
            if depth > MAX_PATH_DEPTH:
                problems.append(Problem(
                    type="PATH_TOO_DEEP",
                    severity=Severity.ERROR,
                    message=f"ZIP entry path depth {depth} exceeds limit {MAX_PATH_DEPTH}: '{name}'.",
                    stage="zip_extraction",
                ))

            # --- duplicates ---
            normalised = name.lower().replace("\\", "/")
            if normalised in seen_names:
                problems.append(Problem(
                    type="DUPLICATE_ENTRY",
                    severity=Severity.ERROR,
                    message=f"Duplicate entry in ZIP: '{name}'.",
                    stage="zip_extraction",
                ))
            seen_names.add(normalised)

            # --- accumulated size ---
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_EXTRACTED_SIZE_BYTES:
                problems.append(Problem(
                    type="EXTRACTED_SIZE_TOO_LARGE",
                    severity=Severity.ERROR,
                    message=f"Total extracted size exceeds limit of {MAX_EXTRACTED_SIZE_BYTES:,} bytes.",
                    stage="zip_extraction",
                ))
                return run_id, dirs, problems

        # abort before extracting if any errors found
        if any(p.severity == Severity.ERROR for p in problems):
            return run_id, dirs, problems

        # ---- extract ----
        zf.extractall(dirs["extracted"])

    return run_id, dirs, problems
