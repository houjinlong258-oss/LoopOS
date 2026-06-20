import unittest
import tempfile
from pathlib import Path

from loopos.gateway import ChatOpsGateway, GatewayStore
from loopos.model_kernel import MultiModelScheduler, ProviderRegistry


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
            self.assertEqual(decision.run_id, "run-1")
            self.assertEqual(store.load_approval(card.id).status, "approved")


if __name__ == "__main__":
    unittest.main()
