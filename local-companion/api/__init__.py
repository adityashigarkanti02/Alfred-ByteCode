"""
Export companion API router.
"""

from .routes import router, set_filesystem_manager, get_manager

__all__ = ["router", "set_filesystem_manager", "get_manager"]
