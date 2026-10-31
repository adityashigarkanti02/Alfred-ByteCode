"""
Deliverable Packaging Script for ALFRED AI.

Packages the complete project into a clean, standalone ZIP deliverable named:
alfred-ai-complete.zip

Excludes:
- node_modules/
- .next/ build cache
- __pycache__/ and *.pyc
- .pytest_cache/
- local sqlite database files (*.db)
- secret .env files
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP_DIR = ROOT_DIR.parent
TARGET_ZIP_NAME = "alfred-ai-complete.zip"
TARGET_ZIP_PATH = OUTPUT_ZIP_DIR / TARGET_ZIP_NAME

# Artifact directory for AI assistant platform if present
ARTIFACT_DIR = Path(r"C:\Users\Aditya\.gemini\antigravity\brain\a5164a8f-b7f3-4bed-a32e-21f2f6f00d54")

EXCLUDED_DIR_NAMES = {
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "venv",
    "env",
    ".idea",
    ".vscode",
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite3",
}

EXCLUDED_FILENAMES = {
    ".env",
    ".env.local",
    "alfred.db",
}


def should_include_path(file_path: Path) -> bool:
    """Evaluates whether file should be packaged into clean source deliverable."""
    for part in file_path.parts:
        if part in EXCLUDED_DIR_NAMES:
            return False

    if file_path.name in EXCLUDED_FILENAMES:
        return False

    if file_path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return False

    return True


def package_project():
    print(f"[*] Packaging ALFRED AI from: {ROOT_DIR}")
    print(f"[*] Destination: {TARGET_ZIP_PATH}")

    total_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(TARGET_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Modify dirs in-place to prevent os.walk from recursing into excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]

            for file in files:
                full_path = Path(root) / file
                if should_include_path(full_path):
                    # Relative archive path with top-level 'alfred-ai/' prefix
                    rel_path = full_path.relative_to(ROOT_DIR)
                    arc_name = Path("alfred-ai") / rel_path
                    zf.write(full_path, arc_name)
                    total_files += 1
                    total_uncompressed_bytes += full_path.stat().st_size

    zip_size_mb = TARGET_ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"[OK] Created {TARGET_ZIP_PATH}")
    print(f"    - Packaged Files: {total_files}")
    print(f"    - Archive Size:   {zip_size_mb:.2f} MB")

    # Also copy to conversation artifact directory if available
    if ARTIFACT_DIR.exists():
        artifact_zip_path = ARTIFACT_DIR / TARGET_ZIP_NAME
        shutil.copy2(TARGET_ZIP_PATH, artifact_zip_path)
        print(f"[OK] Copied archive to Artifacts Directory: {artifact_zip_path}")


if __name__ == "__main__":
    package_project()
