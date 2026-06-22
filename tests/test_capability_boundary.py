"""Tests for :class:`CapabilityBoundary` enforcement."""

from __future__ import annotations

import unittest

from loopos.freedom import (
    CapabilityBoundary,
    FreedomLevel,
    FreedomPolicy,
    check_authority,
)
from loopos.freedom.boundary import (
    RC_DATABASE_MUTATION_DENIED,
    RC_DATABASE_PATH_NOT_ALLOWLISTED,
    RC_FS_WRITE_TOO_LARGE,
    RC_LEVEL_TOO_LOW,
    RC_NETWORK_DENIED,
    RC_NETWORK_HOST_NOT_ALLOWLISTED,
    RC_OK,
    RC_PATH_NOT_ALLOWLISTED,
    RC_PRIVILEGE_DENIED,
    RC_RELEASE_TAG_DENIED,
)


def _f0_with_allowlist(allowlist: list[str] | None = None) -> FreedomPolicy:
    return FreedomPolicy(
        level="F0_DETERMINISTIC",
        allow_network=False,
        allow_database_mutation=False,
        allow_release_tag_changes=False,
        allow_privilege_escalation=False,
        metadata={"terminal_allowlist": allowlist or []},
    )


def _f5_open() -> FreedomPolicy:
    return FreedomPolicy(
        level="F5_AUTONOMOUS_PROJECT",
        allow_network=True,
        allow_database_mutation=True,
        allow_release_tag_changes=True,
        allow_privilege_escalation=True,
    )


class CapabilityBoundaryTerminalTests(unittest.TestCase):
    def test_f0_denies_arbitrary_terminal_command(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist())
        d = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="echo hi",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_LEVEL_TOO_LOW)

    def test_f0_allows_allowlisted_command(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist(allowlist=["echo hi"]))
        d = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="echo hi",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason_code, RC_OK)

    def test_f0_denies_network_command(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist(allowlist=["*"]))
        d = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="curl https://example.com",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_NETWORK_DENIED)

    def test_f0_denies_privilege_command(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist(allowlist=["*"]))
        d = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="sudo apt update",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_PRIVILEGE_DENIED)
        self.assertEqual(d.safety_level, "L5")

    def test_f0_denies_database_mutation(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist(allowlist=["*"]))
        d = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="psql -c 'DROP TABLE users'",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_DATABASE_MUTATION_DENIED)

    def test_f0_denies_release_tag_through_release_tag_action(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist(allowlist=["*"]))
        d = check_authority(
            boundary,
            action="release.tag",
            level="F0_DETERMINISTIC",
            command="git tag v0.2.0",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_RELEASE_TAG_DENIED)
        self.assertTrue(d.requires_human_approval)

    def test_f0_denies_release_tag_pattern_in_terminal(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist(allowlist=["*"]))
        d = check_authority(
            boundary,
            action="terminal.execute",
            level="F0_DETERMINISTIC",
            command="git tag v0.2.0",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_RELEASE_TAG_DENIED)


class CapabilityBoundaryNetworkTests(unittest.TestCase):
    def test_f0_denies_network_request(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist())
        d = check_authority(
            boundary,
            action="network.request",
            level="F0_DETERMINISTIC",
            host="example.com",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_NETWORK_DENIED)

    def test_f5_with_allowlist_host(self) -> None:
        policy = _f5_open()
        policy.allowed_network_hosts = ["api.example.com"]
        boundary = CapabilityBoundary(policy)
        d_ok = check_authority(
            boundary,
            action="network.request",
            level="F5_AUTONOMOUS_PROJECT",
            host="api.example.com",
        )
        d_bad = check_authority(
            boundary,
            action="network.request",
            level="F5_AUTONOMOUS_PROJECT",
            host="other.example.com",
        )
        self.assertTrue(d_ok.allowed)
        self.assertFalse(d_bad.allowed)
        self.assertEqual(d_bad.reason_code, RC_NETWORK_HOST_NOT_ALLOWLISTED)


class CapabilityBoundaryFileTests(unittest.TestCase):
    def test_f0_denies_file_write(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist())
        d = check_authority(
            boundary,
            action="file.write",
            level="F0_DETERMINISTIC",
            path="README.md",
            bytes_=10,
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_LEVEL_TOO_LOW)

    def test_f5_path_must_be_in_allowlist(self) -> None:
        policy = _f5_open()
        policy.allowed_filesystem_roots = ["/workspace/loopos"]
        boundary = CapabilityBoundary(policy)
        d_ok = check_authority(
            boundary,
            action="file.read",
            level="F5_AUTONOMOUS_PROJECT",
            path="/workspace/loopos/README.md",
        )
        d_bad = check_authority(
            boundary,
            action="file.read",
            level="F5_AUTONOMOUS_PROJECT",
            path="/etc/passwd",
        )
        self.assertTrue(d_ok.allowed)
        self.assertFalse(d_bad.allowed)
        self.assertEqual(d_bad.reason_code, RC_PATH_NOT_ALLOWLISTED)

    def test_f5_write_size_cap_enforced(self) -> None:
        policy = _f5_open()
        policy.max_filesystem_write_bytes = 1024
        boundary = CapabilityBoundary(policy)
        d = check_authority(
            boundary,
            action="file.write",
            level="F5_AUTONOMOUS_PROJECT",
            path="/workspace/loopos/big.bin",
            bytes_=2048,
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_FS_WRITE_TOO_LARGE)


class CapabilityBoundaryDatabaseTests(unittest.TestCase):
    def test_f0_denies_database_mutation_action(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist())
        d = check_authority(
            boundary,
            action="database.mutation",
            level="F0_DETERMINISTIC",
            database_path="/var/db/main.sqlite",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, RC_DATABASE_MUTATION_DENIED)

    def test_f5_database_path_must_be_allowlisted(self) -> None:
        policy = _f5_open()
        policy.allowed_database_paths = ["/var/db/main.sqlite"]
        boundary = CapabilityBoundary(policy)
        d_ok = check_authority(
            boundary,
            action="database.mutation",
            level="F5_AUTONOMOUS_PROJECT",
            database_path="/var/db/main.sqlite",
        )
        d_bad = check_authority(
            boundary,
            action="database.mutation",
            level="F5_AUTONOMOUS_PROJECT",
            database_path="/var/db/other.sqlite",
        )
        self.assertTrue(d_ok.allowed)
        self.assertEqual(d_ok.reason_code, RC_OK)
        self.assertTrue(d_ok.requires_human_approval)
        self.assertFalse(d_bad.allowed)
        self.assertEqual(d_bad.reason_code, RC_DATABASE_PATH_NOT_ALLOWLISTED)


class CapabilityBoundaryDefaultsTests(unittest.TestCase):
    def test_unknown_action_returns_allow_with_reason(self) -> None:
        boundary = CapabilityBoundary(_f0_with_allowlist())
        d = check_authority(
            boundary,
            action="noop",
            level="F0_DETERMINISTIC",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason_code, RC_OK)


if __name__ == "__main__":
    unittest.main()
