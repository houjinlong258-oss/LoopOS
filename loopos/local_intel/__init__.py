"""Privacy-first local workspace intelligence."""

from loopos.local_intel.index import WorkspaceIndexer
from loopos.local_intel.models import WorkspaceIndex, WorkspaceSearchResult
from loopos.local_intel.privacy import is_indexable_text, is_private_path

__all__ = [
    "WorkspaceIndex",
    "WorkspaceIndexer",
    "WorkspaceSearchResult",
    "is_indexable_text",
    "is_private_path",
]
