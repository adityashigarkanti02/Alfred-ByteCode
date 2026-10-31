"""
Filesystem and Document Operations for ALFRED AI Local Companion.

All operations execute strictly after path validation against authorized directory roots.
Supports:
- Safe directory listing with file metadata
- Text, PDF, and DOCX document reading
- Safe atomic file creation and editing
- Recursive in-jail file search
- Move / Rename within jail
- Controlled file deletion
"""

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
try:
    from security.path_validator import PathValidator, PathSecurityException
except (ImportError, ValueError):
    from ..security.path_validator import PathValidator, PathSecurityException

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None


class FileItem(BaseModel):
    """Metadata summary of a single file or directory."""
    name: str
    path: str
    is_directory: bool
    size_bytes: int
    modified_at: str
    extension: str


class CompanionFilesystemManager:
    """
    Executes validated filesystem tasks within authorized directory trees.
    """

    def __init__(self, validator: PathValidator):
        self.validator = validator

    def list_directory(self, target_dir: str) -> List[Dict[str, Any]]:
        """
        Lists files and subdirectories within a validated directory path.
        """
        canonical_dir = self.validator.validate_path(target_dir)
        p = Path(canonical_dir)
        
        if not p.is_dir():
            raise ValueError(f"Path '{target_dir}' is not a directory")

        results = []
        for entry in p.iterdir():
            # Skip hidden system entries
            if entry.name.startswith(".") and entry.name != ".":
                continue

            try:
                stat = entry.stat()
                results.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "is_directory": entry.is_dir(),
                    "size_bytes": stat.st_size if entry.is_file() else 0,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": entry.suffix.lower()
                })
            except Exception:
                continue

        return sorted(results, key=lambda x: (not x["is_directory"], x["name"].lower()))

    def read_file(self, target_path: str, max_bytes: int = 5_000_000) -> Dict[str, Any]:
        """
        Reads text, PDF, or DOCX document content from a validated file path.
        """
        canonical_file = self.validator.validate_path(target_path)
        p = Path(canonical_file)

        if not p.is_file():
            raise ValueError(f"Path '{target_path}' is not a regular file")

        ext = p.suffix.lower()

        # Handle PDF documents
        if ext == ".pdf":
            return self._read_pdf(p)

        # Handle DOCX documents
        if ext == ".docx":
            return self._read_docx(p)

        # Standard plain text files
        stat = p.stat()
        if stat.st_size > max_bytes:
            raise ValueError(f"File size ({stat.st_size} bytes) exceeds safety read limit of {max_bytes} bytes")

        try:
            with open(canonical_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "path": canonical_file,
                "mime_type": "text/plain",
                "size_bytes": stat.st_size,
                "content": content
            }
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {str(e)}")

    def _read_pdf(self, path: Path) -> Dict[str, Any]:
        """Extracts text and metadata from PDF files using pypdf."""
        if not pypdf:
            return {
                "path": str(path),
                "mime_type": "application/pdf",
                "error": "pypdf library not available on companion",
                "content": ""
            }

        try:
            reader = pypdf.PdfReader(str(path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_text.append(f"--- PAGE {i+1} ---\n{text}")

            metadata = {}
            if reader.metadata:
                for k, v in reader.metadata.items():
                    metadata[str(k)] = str(v)

            return {
                "path": str(path),
                "mime_type": "application/pdf",
                "page_count": len(reader.pages),
                "metadata": metadata,
                "content": "\n\n".join(pages_text)
            }
        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF document: {str(e)}")

    def _read_docx(self, path: Path) -> Dict[str, Any]:
        """Extracts text from DOCX files using python-docx."""
        if not docx:
            return {
                "path": str(path),
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "error": "docx library not available on companion",
                "content": ""
            }

        try:
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return {
                "path": str(path),
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "paragraph_count": len(paragraphs),
                "content": "\n\n".join(paragraphs)
            }
        except Exception as e:
            raise RuntimeError(f"Failed to parse DOCX document: {str(e)}")

    def write_file(self, target_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """
        Safely writes text to target path using an atomic temporary write pattern.
        """
        canonical_file = self.validator.validate_path(target_path)
        p = Path(canonical_file)

        if p.exists() and not overwrite:
            raise ValueError(f"File '{target_path}' already exists and overwrite=False")

        # Atomic write: write to temp file in same directory, then rename
        target_dir = p.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", dir=str(target_dir), delete=False, encoding="utf-8") as tf:
            tf.write(content)
            temp_path = tf.name

        try:
            shutil.move(temp_path, canonical_file)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return {
            "path": canonical_file,
            "bytes_written": len(content.encode("utf-8")),
            "status": "WRITTEN"
        }

    def edit_file(self, target_path: str, find_text: str, replace_text: str) -> Dict[str, Any]:
        """
        Applies a precise search-and-replace modification to a text file.
        """
        file_info = self.read_file(target_path)
        content = file_info["content"]

        if find_text not in content:
            raise ValueError(f"Target text string to replace was not found in '{target_path}'")

        modified_content = content.replace(find_text, replace_text, 1)
        return self.write_file(target_path, modified_content, overwrite=True)

    def search_files(self, base_dir: str, pattern: str) -> List[Dict[str, Any]]:
        """
        Recursively searches for filenames matching pattern within authorized base_dir.
        """
        canonical_base = self.validator.validate_path(base_dir)
        p = Path(canonical_base)

        matches = []
        pattern_lower = pattern.lower()

        for entry in p.rglob("*"):
            if entry.is_file():
                # Enforce path validation for every visited file
                try:
                    self.validator.validate_path(str(entry))
                except PathSecurityException:
                    continue

                if pattern_lower in entry.name.lower():
                    matches.append({
                        "name": entry.name,
                        "path": str(entry.resolve()),
                        "size_bytes": entry.stat().st_size,
                        "modified_at": datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
                    })

        return matches

    def move_file(self, source_path: str, dest_path: str) -> Dict[str, Any]:
        """
        Moves or renames a file, ensuring BOTH source and destination are in authorized roots.
        """
        canonical_src = self.validator.validate_path(source_path)
        canonical_dest = self.validator.validate_path(dest_path)

        src_p = Path(canonical_src)
        if not src_p.exists():
            raise FileNotFoundError(f"Source file '{source_path}' does not exist")

        shutil.move(canonical_src, canonical_dest)
        return {
            "source": canonical_src,
            "destination": canonical_dest,
            "status": "MOVED"
        }

    def delete_file(self, target_path: str, confirmed: bool = False) -> Dict[str, Any]:
        """
        Deletes a validated file. Requires confirmed=True flag.
        """
        if not confirmed:
            raise ValueError("File deletion requires explicit confirmed=True flag")

        canonical_path = self.validator.validate_path(target_path)
        p = Path(canonical_path)

        if not p.exists():
            raise FileNotFoundError(f"File '{target_path}' does not exist")

        if p.is_dir():
            shutil.rmtree(canonical_path)
        else:
            p.unlink()

        return {
            "path": canonical_path,
            "status": "DELETED"
        }
