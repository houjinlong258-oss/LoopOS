from __future__ import annotations

import pytest
from pydantic import ValidationError

from loopos.adapters.a2a import A2AAdapter


def test_a2a_adapter_is_unavailable_by_default() -> None:
    adapter = A2AAdapter()

    assert adapter.adapter_id == "a2a"
    assert adapter.available is False


def test_a2a_adapter_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        A2AAdapter.model_validate({"unexpected": True})
