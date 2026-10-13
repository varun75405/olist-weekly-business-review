#!/usr/bin/env python3
"""
package_submission.py — Utility to create a clean, compliant submission ZIP file.

Excludes:
  - .env (database credentials / secrets)
  - data/*.csv (raw dataset files)
  - __pycache__ / *.pyc
  - .pytest_cache
  - logs / temporary artifacts

Includes:
  - .env.example
  - pipeline.py
  - README.md
  - requirements.txt
  - src/
  - sql/
  - tests/
  - charts/ (*.png)
  - reports/ (*.pdf)
  - dags/
  - data/.gitkeep
"""
import os
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_ZIP = BASE_DIR.parent / "olist-weekly-business-review-submission.zip"

EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "venv",
    "rendered_pages",
    "rendered_pages_final",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
}

def should_exclude(rel_path: Path) -> bool:
    # Exclude .env file (keep .env.example)
    if rel_path.name == ".env":
        return True
    
    # Exclude CSV files in data/ (keep .gitkeep)
    if rel_path.suffix.lower() == ".csv":
        return True
    
    # Exclude forbidden directories
    for part in rel_path.parts:
        if part in EXCLUDE_DIRS:
            return True

    # Exclude intermediate test / debugging files (test_*.png, test_*.pdf, etc.)
    if rel_path.name.startswith("test_") and rel_path.suffix.lower() in {".png", ".pdf"}:
        return True
        
    # Exclude compiled bytecode or logs
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True

    return False

def create_submission_zip():
    print(f"Creating submission zip: {OUTPUT_ZIP} ...")
    included_count = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zip_out:
        for root, dirs, files in os.walk(BASE_DIR):
            for file in sorted(files):
                full_path = Path(root) / file
                rel_path = full_path.relative_to(BASE_DIR)
                
                if should_exclude(rel_path):
                    continue
                
                archive_name = Path("olist-weekly-business-review") / rel_path
                zip_out.write(full_path, arcname=str(archive_name))
                included_count += 1
                
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"Submission ZIP created successfully: {OUTPUT_ZIP}")
    print(f"Total files included: {included_count} | Size: {zip_size_mb:.2f} MB")
    return OUTPUT_ZIP

if __name__ == "__main__":
    create_submission_zip()
