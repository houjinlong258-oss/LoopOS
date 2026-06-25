from __future__ import annotations

import pytest
from pydantic import ValidationError

from loopos.adapters.memory_os import MemoryOSAdapter


def test_memory_os_adapter_is_available_metadata() -> None:
    adapter = MemoryOSAdapter()

    assert adapter.adapter_id == "memory_os"
    assert adapter.available is True


def test_memory_os_adapter_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MemoryOSAdapter.model_validate({"available": True, "extra": "no"})
