import json
import unittest

from loopos.llm.providers import MockLLMProvider, OpenAICompatibleProvider
from loopos.memory.extractor import MemoryProposalExtractor
from loopos.memory.event_log import Event


class LLMProviderTests(unittest.TestCase):
    def test_mock_provider_extracts_proposal(self) -> None:
        response = json.dumps(
            [
                {
                    "proposed_item": {
                        "type": "fact",
                        "content": "Project uses LoopOS.",
                        "confidence": 0.9,
                        "source": "llm",
                        "tags": ["project"],
                        "layer": "semantic",
                        "scope": "project",
                    },
                    "source": "llm",
                    "rationale": "Durable project fact.",
                }
            ]
        )
        provider = MockLLMProvider(response)
        proposals, errors = MemoryProposalExtractor(provider).extract(
            run_id="run",
            events=[Event(run_id="run", step_index=1, type="observation", payload={})],
            user_profile={},
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].proposed_item.layer, "semantic")

    def test_openai_provider_without_key_does_not_request(self) -> None:
        provider = OpenAICompatibleProvider(api_key="", base_url="https://example.invalid")
        response = provider.complete("hello")
        self.assertIn("LOOPOS_LLM_API_KEY", response.error or "")

    def test_extractor_rejects_invalid_json(self) -> None:
        proposals, errors = MemoryProposalExtractor(MockLLMProvider("not json")).extract(
            run_id="run",
            events=[],
            user_profile={},
        )
        self.assertEqual(proposals, [])
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
