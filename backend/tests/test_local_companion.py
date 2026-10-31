"""
Tests for Local Companion Service Filesystem Security.

Verifies:
1. Canonical path validation and authorized jail confinement.
2. Traversal neutralization (../, ..\\, null bytes).
3. Blocking of sensitive files (.env, id_rsa, credentials).
4. Safe file read, write, and search operations.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Add local-companion directory to sys.path
companion_dir = str(Path(__file__).resolve().parent.parent.parent / "local-companion")
if companion_dir not in sys.path:
    sys.path.insert(0, companion_dir)

from security.path_validator import PathValidator, PathSecurityException
from filesystem.operations import CompanionFilesystemManager


@pytest.fixture
def sandbox_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        sub = Path(tmpdir) / "subfolder"
        sub.mkdir()
        (sub / "doc.txt").write_text("Hello World", encoding="utf-8")
        yield tmpdir


@pytest.fixture
def validator(sandbox_dir):
    return PathValidator(authorized_roots=[sandbox_dir])


@pytest.fixture
def fs_manager(validator):
    return CompanionFilesystemManager(validator=validator)


def test_path_confinement_within_jail(validator, sandbox_dir):
    """Verifies that paths within the authorized root are accepted."""
    target = os.path.join(sandbox_dir, "subfolder", "doc.txt")
    canonical = validator.validate_path(target)
    assert canonical == str(Path(target).resolve())


def test_path_traversal_neutralization(validator, sandbox_dir):
    """Verifies that path traversal attacks (../) outside authorized root are blocked."""
    outside_target = os.path.join(sandbox_dir, "..", "outside_secret.txt")
    with pytest.raises(PathSecurityException) as exc:
        validator.validate_path(outside_target)
    assert "traversal" in str(exc.value).lower() or "outside" in str(exc.value).lower()


def test_sensitive_file_denial(validator, sandbox_dir):
    """Verifies that sensitive filenames are blocked even if created inside jail."""
    env_file = os.path.join(sandbox_dir, ".env")
    with pytest.raises(PathSecurityException) as exc:
        validator.validate_path(env_file)
    assert "sensitive file" in str(exc.value).lower()


def test_null_byte_injection(validator, sandbox_dir):
    """Verifies that null byte injection is rejected."""
    null_path = os.path.join(sandbox_dir, "doc.txt\0.jpg")
    with pytest.raises(PathSecurityException) as exc:
        validator.validate_path(null_path)
    assert "null byte" in str(exc.value).lower()


def test_fs_read_and_write(fs_manager, sandbox_dir):
    """Verifies atomic writing and reading of files."""
    new_file = os.path.join(sandbox_dir, "new_note.txt")
    write_res = fs_manager.write_file(new_file, "Important meeting notes", overwrite=True)
    assert write_res["status"] == "WRITTEN"

    read_res = fs_manager.read_file(new_file)
    assert read_res["content"] == "Important meeting notes"


def test_fs_search(fs_manager, sandbox_dir):
    """Verifies recursive search within jail."""
    matches = fs_manager.search_files(sandbox_dir, "doc")
    assert len(matches) >= 1
    assert any("doc.txt" in m["name"] for m in matches)
