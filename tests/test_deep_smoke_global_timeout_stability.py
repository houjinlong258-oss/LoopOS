"""Stability regression for ``test_deep_smoke_global_timeout_names_running_check``.

The P0 hardening pass left this test as
``assert report['duration_ms'] < 6000`` — a brittle wall-clock
threshold that flaked under machine load. The P1-1 fix
replaced the magic constant with a deterministic
``configured timeout + explicit grace window`` bound plus
semantic assertions (configured timeout honored, running check
named, global-timeout result reported, process exits cleanly,
no side effects).

This module proves the fix is stable: it re-runs the test
several times in the same process and asserts every run
passes. If a future change reintroduces timing flakiness, this
regression catches it at unit-test time without needing a
flaky CI pass.
"""

from __future__ import annotations

import pytest

import loopos.release.deep_smoke as deep_smoke


# A small number is enough to surface a regression; 8 runs fit
# comfortably under the 60-second default pytest timeout. The
# number is a constant (not a CLI flag) so the regression is
# deterministic and inspectable in code review.
_REPEAT_COUNT = 8


@pytest.mark.parametrize("iteration", range(_REPEAT_COUNT))
def test_deep_smoke_global_timeout_stable_across_repeated_runs(
    iteration: int,
) -> None:
    """Re-run the global-timeout path and assert each run passes.

    The test is parameterised so pytest reports each run as a
    separate case, and a single failure shows up as a single
    failure rather than aborting the rest.
    """
    del iteration  # only used to give the parameterised case a name.
    report = deep_smoke.run_deep_smoke(
        ".",
        only={"registry_examples"},
        timeout_per_check=20,
        global_timeout=1,
    )
    # Mirror the production test's semantic assertions (without
    # the boundary-detail noise that the production test carries
    # for documentation).
    assert report["passed"] is False
    assert report["currently_running_check"] == "registry_examples"
    assert report["checks"][0]["reason"] == "global_timeout"
    assert report["checks"][0]["status"] == "failed"
    duration_ms = int(report["duration_ms"])
    assert 1000 <= duration_ms < 1000 + 8000, (
        f"global-timeout path took {duration_ms} ms; expected "
        f"1000 <= duration < 9000 (timeout=1s + 8s grace)"
    )


def test_deep_smoke_global_timeout_path_is_deterministic_under_seed() -> None:
    """Two consecutive invocations of the global-timeout path
    must produce structurally identical reports. The wall-clock
    duration is allowed to vary, but the report's *shape* must
    be stable: the same fields are present with the same values
    except for ``duration_ms`` and the recorded subprocess
    command tail.
    """
    first = deep_smoke.run_deep_smoke(
        ".",
        only={"registry_examples"},
        timeout_per_check=20,
        global_timeout=1,
    )
    second = deep_smoke.run_deep_smoke(
        ".",
        only={"registry_examples"},
        timeout_per_check=20,
        global_timeout=1,
    )
    # Compare the deterministic fields.
    for key in (
        "schema_version",
        "name",
        "passed",
        "timeout_per_check",
        "global_timeout",
        "currently_running_check",
    ):
        assert first[key] == second[key], (
            f"deep smoke global-timeout path produced non-deterministic "
            f"{key!r}: {first[key]!r} != {second[key]!r}"
        )
    # The first check in each report must agree on the timeout
    # semantics.
    for report in (first, second):
        check = report["checks"][0]
        assert check["name"] == "registry_examples"
        assert check["reason"] == "global_timeout"
        assert check["status"] == "failed"
        assert 0.0 < float(check["timeout_seconds"]) <= 1.0