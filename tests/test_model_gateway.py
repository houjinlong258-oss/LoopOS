import unittest
import tempfile
from pathlib import Path

from loopos.gateway import (
    AttachmentMetadata,
    ChatOpsGateway,
    GatewayAuthPolicy,
    GatewaySession,
    GatewayStore,
)
from loopos.model_kernel import MultiModelScheduler, ProviderRegistry, load_provider_profiles


class ModelGatewayTests(unittest.TestCase):
    def test_provider_registry_covers_requested_ids_and_routes_capability(self) -> None:
        registry = ProviderRegistry()
        provider_ids = {profile.id for profile in registry.list()}

        self.assertIn("openai-codex", provider_ids)
        self.assertIn("anthropic", provider_ids)
        self.assertIn("gemini", provider_ids)
        self.assertEqual(registry.route(["coding"]).id, "openai-codex")

    def test_multi_model_scheduler_selects_vision_companion(self) -> None:
        scheduler = MultiModelScheduler()
        primary = scheduler.assign("coder")
        companion = scheduler.companion_for(primary, required_capability="vision")
        summary = scheduler.summarize_vision("screenshot.png", "A failing UI screenshot")

        self.assertIsNotNone(companion)
        assert companion is not None
        self.assertEqual(companion.role, "vision_companion")
        self.assertEqual(summary.source, "screenshot.png")

    def test_provider_profiles_load_from_yaml_and_alias_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.yaml"
            path.write_text(
                """
providers:
  - id: local-coder
    aliases: [lc]
    capabilities: [text, code, local_only, reasoning]
    default_models: [local-code]
    local_only: true
""",
                encoding="utf-8",
            )
            profiles = load_provider_profiles([path])
            registry = ProviderRegistry.from_paths([path], include_defaults=False)

            self.assertEqual(profiles[0].capabilities, ["text", "coding", "local", "reasoning"])
            self.assertEqual(registry.get("lc").id, "local-coder")
            self.assertEqual(registry.route(["coding"], local_only=True).id, "local-coder")

    def test_secret_task_routes_to_local_provider(self) -> None:
        assignments = MultiModelScheduler().route_task(task="coding", secret=True)

        self.assertIn("local", assignments[0].capabilities)
        self.assertEqual(assignments[0].reason_code, "privacy_local")

    def test_chatops_gateway_converts_message_to_run_spec_and_approval(self) -> None:
        gateway = ChatOpsGateway()
        event = gateway.receive("telegram", "u1", "run tests")
        spec = gateway.to_run_spec(event, workspace=".")
        card = gateway.approval_card(
            "telegram",
            run_id="run-1",
            action_summary="git reset --hard",
            risk="high",
            reason_codes=["git_reset_hard_requires_approval"],
        )
        gateway.decide(card, approve=False)

        self.assertEqual(spec.goal, "run tests")
        self.assertEqual(spec.metadata["gateway_event_id"], event.id)
        self.assertEqual(card.status, "denied")

    def test_gateway_store_persists_approval_decisions_for_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = GatewayStore(
                messages_path=Path(tmp) / "messages.json",
                approvals_path=Path(tmp) / "approvals.json",
            )
            gateway = ChatOpsGateway()
            event = store.append_message(gateway.receive("slack", "u1", "run tests"))
            card = store.save_approval(
                gateway.approval_card(
                    "slack",
                    run_id="run-1",
                    action_summary="write file",
                    risk="medium",
                    reason_codes=["file_write_requires_approval"],
                )
            )
            decision = store.decide(card.id, approve=True)

            self.assertEqual(store.list_messages()[0].id, event.id)
            self.assertTrue(decision.approve)
            self.assertEqual(decision.signal, "approve")
            self.assertEqual(decision.run_id, "run-1")
            self.assertEqual(store.load_approval(card.id).status, "approved")

    def test_gateway_auth_attachment_delivery_and_session_flow(self) -> None:
        policy = GatewayAuthPolicy(
            allowlists={"slack": {"u1"}},  # type: ignore[dict-item]
            tokens={"slack": "token"},  # type: ignore[dict-item]
        )
        gateway = ChatOpsGateway(auth_policy=policy)
        with self.assertRaises(ValueError):
            gateway.receive("slack", "u2", "run tests", token="token")
        event = gateway.receive(
            "slack",
            "u1",
            "inspect screenshot",
            token="token",
            attachments=[AttachmentMetadata(filename="failure.png", media_type="image/png")],
        )
        delivery = gateway.deliver("slack", "u1", "run accepted", message_id=event.id)
        self.assertTrue(event.authenticated)
        self.assertEqual(event.attachments[0].filename, "failure.png")
        self.assertEqual(delivery.status, "delivered")

        with tempfile.TemporaryDirectory() as tmp:
            store = GatewayStore(
                messages_path=Path(tmp) / "messages.json",
                approvals_path=Path(tmp) / "approvals.json",
            )
            store.save_delivery(delivery)
            session = store.save_session(
                GatewaySession(channel="slack", user_id="u1", run_id="run-1")
            )
            self.assertEqual(store.list_deliveries()[0].id, delivery.id)
            self.assertEqual(store.list_sessions()[0].id, session.id)


if __name__ == "__main__":
    unittest.main()
