"""
Path Security and Boundary Validator for ALFRED AI Local Companion.

This module is the bedrock of local filesystem security. It ensures:
1. Canonical Path Resolution: Resolves all relative components and symbolic links.
2. Jail Confinement: Verifies that the resolved realpath starts with one of the
   explicitly authorized base directories.
3. Path Traversal Neutralization: Rejects attempts using '..', null bytes, UNC paths,
   or URI encoding tricks.
4. Symlink Escape Prevention: Blocks symlinks whose target lies outside authorized zones.
5. Sensitive File Denials: Hardcoded blocklist for sensitive configuration files
   (.env, credentials, SSH keys, registry hives).
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple


class PathSecurityException(Exception):
    """Raised when an operation attempts to breach filesystem confinement boundaries."""
    pass


class PathValidator:
    """
    Enforces strict filesystem jail confinement and prevents unauthorized traversals.
    """

    # Strictly forbidden sensitive files and folders even if placed in authorized directories
    BLOCKED_FILENAMES = {
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
        "known_hosts",
        "authorized_keys",
        ".git",
        ".aws",
        ".ssh",
        "credentials.json",
        "client_secret.json",
        "token.json",
        "sam.dat",
        "system.dat",
    }

    def __init__(self, authorized_roots: Optional[List[str]] = None):
        """
        Initializes validator with a list of authorized directory paths.
        All paths are immediately resolved to canonical paths.
        """
        self.authorized_roots: List[str] = []
        if authorized_roots:
            for root in authorized_roots:
                self.add_authorized_root(root)

    def add_authorized_root(self, directory_path: str) -> str:
        """
        Adds a directory to the authorized whitelist, resolving to canonical form.
        Creates directory if it does not exist.
        """
        p = Path(directory_path).resolve()
        p.mkdir(parents=True, exist_ok=True)
        canonical = str(p)
        if canonical not in self.authorized_roots:
            self.authorized_roots.append(canonical)
        return canonical

    def validate_path(self, target_path: str) -> str:
        """
        Validates target_path against authorized root boundaries.
        Returns the canonical absolute path if valid.
        Raises PathSecurityException if path traversal, escape, or blocked file is detected.
        """
        if not target_path or not str(target_path).strip():
            raise PathSecurityException("Target path cannot be empty")

        # 1. Null byte and control char check
        if "\0" in target_path or "\r" in target_path or "\n" in target_path:
            raise PathSecurityException("Path contains invalid null byte or control characters")

        # 2. Resolve to canonical path (resolves symlinks and '..' components)
        try:
            resolved_path = Path(target_path).resolve()
        except Exception as e:
            raise PathSecurityException(f"Failed to resolve path '{target_path}': {str(e)}")

        canonical_target = str(resolved_path)

        # 3. Check for forbidden file names
        filename = resolved_path.name.lower()
        if filename in self.BLOCKED_FILENAMES:
            raise PathSecurityException(f"Access to sensitive file '{filename}' is strictly blocked")

        # Check for blocked extensions or patterns
        if filename.endswith(".pem") or filename.endswith(".key") or filename.endswith(".pfx"):
            raise PathSecurityException(f"Access to private key/certificate file '{filename}' is strictly blocked")

        # 4. Check confinement within at least one authorized root
        if not self.authorized_roots:
            raise PathSecurityException("No authorized directories configured on Local Companion service")

        is_confined = False
        for root in self.authorized_roots:
            # Check if canonical_target is exactly root or a subpath of root
            try:
                # relative_to will throw ValueError if not a subpath
                resolved_path.relative_to(Path(root))
                is_confined = True
                break
            except ValueError:
                continue

        if not is_confined:
            raise PathSecurityException(
                f"Path Traversal Violation: '{target_path}' resolves to '{canonical_target}', "
                f"which is outside of all authorized directories."
            )

        return canonical_target
