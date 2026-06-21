"""Tests for diff summary parser."""

from loopos.maintainability.diff_summary import parse_diff


_SAMPLE_DIFF = """\
--- a/loopos/kernel/loop_engine.py
+++ b/loopos/kernel/loop_engine.py
@@ -1,5 +1,10 @@
 existing line
+new line one
+new line two
+new line three
+new line four
+new line five
-removed line
--- a/tests/test_kernel.py
+++ b/tests/test_kernel.py
@@ -1,3 +1,5 @@
 test line
+def test_new_thing() -> None:
+    pass
"""


def test_parse_diff_changed_files() -> None:
    summary = parse_diff(_SAMPLE_DIFF)
    assert "loopos/kernel/loop_engine.py" in summary.changed_files
    assert "tests/test_kernel.py" in summary.changed_files


def test_parse_diff_line_counts() -> None:
    summary = parse_diff(_SAMPLE_DIFF)
    assert summary.added_lines == 7
    assert summary.removed_lines == 1


def test_parse_diff_test_files_detected() -> None:
    summary = parse_diff(_SAMPLE_DIFF)
    assert "tests/test_kernel.py" in summary.test_files_changed


def test_parse_diff_risk_detection() -> None:
    risky = """\
--- a/loopos/core/runner.py
+++ b/loopos/core/runner.py
@@ -1,2 +1,3 @@
 import os
+os.system("rm -rf /tmp/data")
"""
    summary = parse_diff(risky)
    assert "os.system_call" in summary.risk_flags or "rm_rf" in summary.risk_flags


def test_parse_diff_empty() -> None:
    summary = parse_diff("")
    assert summary.changed_files == []
    assert summary.added_lines == 0


def test_parse_diff_new_public_api() -> None:
    diff = """\
--- a/loopos/core/models.py
+++ b/loopos/core/models.py
@@ -1,2 +1,5 @@
 existing
+def new_function():
+    pass
+class NewModel:
+    pass
"""
    summary = parse_diff(diff)
    assert "new_function" in summary.new_public_apis
    assert "NewModel" in summary.new_public_apis
