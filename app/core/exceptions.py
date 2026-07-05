"""Shared exception base for all modules.

Every module defines its own exceptions inheriting from `AppError` and
sets `status_code` + `code` on each. `app/core/errors.py` registers a
single handler for `AppError` — no per-exception mapping table to keep
in sync. `code` is a stable, machine-readable identifier for API
consumers — deliberately separate from the Python class name, so
renaming/refactoring an exception class is never a breaking API change.
"""


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
