"""LoopOS release hygiene and packaging helpers.

This package is the canonical home for the release-cleanliness checker
and the release-artifact packager.  The standalone scripts in
``scripts/`` and the ``loopos release`` CLI command group are thin
wrappers around the functions exposed here.

Public API:

    check_release_clean(source)   -> ReleaseReport
    package_release(...)          -> PackageReport
"""

from __future__ import annotations

from loopos.release.hygiene import (
    BLOCKED_DIR_GLOBS,
    BLOCKED_DIRS,
    BLOCKED_FILE_GLOBS,
    BLOCKED_FILES,
    LEAKED_PATH_RE,
    REQUIRED_TOP_LEVEL_FILES,
    ReleaseFinding,
    ReleaseReport,
    check_release_clean,
)
from loopos.release.packaging import (
    PackageReport,
    package_release,
)

__all__ = [
    "BLOCKED_DIR_GLOBS",
    "BLOCKED_DIRS",
    "BLOCKED_FILE_GLOBS",
    "BLOCKED_FILES",
    "LEAKED_PATH_RE",
    "REQUIRED_TOP_LEVEL_FILES",
    "ReleaseFinding",
    "ReleaseReport",
    "check_release_clean",
    "PackageReport",
    "package_release",
]
