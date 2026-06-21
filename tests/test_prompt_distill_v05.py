"""Tests for Prompt Distillation v0.5 — per-rule routing across packs."""

from __future__ import annotations

from loopos.prompt_distill.distiller import PromptDistiller


_MIXED_PROMPT = """\
## Behavior
- Always be concise and clear in responses
- When uncertain, ask for clarification before proceeding

## Rendering
- Use markdown tables for structured output
- Keep CLI output brief and scannable

## Safety
- Never execute dangerous shell commands
- Always validate user input before processing

## Policy
- Must check permissions before file operations
- Should prefer local resources when available

## Mixed Section
- Always be safe when handling user data
- Use markdown formatting for technical docs
- Ask before deleting files
"""


def test_behavior_pack_populates_multiple_sub_buckets() -> None:
    distiller = PromptDistiller()
    segments = distiller.segment(_MIXED_PROMPT, source_id="src")
    behavior = distiller.extract_behavior(segments, name="mixed")
    total = (
        len(behavior.tone_rules)
        + len(behavior.planning_rules)
        + len(behavior.interaction_rules)
        + len(behavior.uncertainty_rules)
    )
    assert total > 0
    # "ask for clarification" should land in uncertainty or interaction
    joined = " ".join(behavior.uncertainty_rules + behavior.interaction_rules)
    assert "clarification" in joined or "ask" in joined.lower()


def test_renderer_pack_captures_formatting_rules_across_sections() -> None:
    distiller = PromptDistiller()
    segments = distiller.segment(_MIXED_PROMPT, source_id="src")
    renderer = distiller.extract_renderer(segments)
    total = len(renderer.markdown_rules) + len(renderer.cli_rules) + len(renderer.verbosity_rules)
    assert total >= 2
    # "Use markdown tables" and "Use markdown formatting" should be captured
    markdown_joined = " ".join(renderer.markdown_rules).lower()
    assert "markdown" in markdown_joined


def test_policy_draft_excludes_pure_renderer_rules() -> None:
    distiller = PromptDistiller()
    segments = distiller.segment(_MIXED_PROMPT, source_id="src")
    draft = distiller.extract_policy_draft(segments, source_id="src")
    # Renderer rules should not appear in the policy draft
    for proposed in draft.proposed_rules:
        rule_lower = proposed["rule"].lower()
        assert "markdown table" not in rule_lower
        assert "cli output brief" not in rule_lower


def test_policy_draft_includes_safety_and_policy_rules() -> None:
    distiller = PromptDistiller()
    segments = distiller.segment(_MIXED_PROMPT, source_id="src")
    draft = distiller.extract_policy_draft(segments, source_id="src")
    rules_joined = " ".join(p["rule"] for p in draft.proposed_rules).lower()
    assert "dangerous shell" in rules_joined
    assert "permissions before file" in rules_joined


def test_mixed_section_rule_routes_to_multiple_packs() -> None:
    """A single segment containing heterogeneous rules must split across packs."""
    distiller = PromptDistiller()
    segments = distiller.segment(_MIXED_PROMPT, source_id="src")
    behavior = distiller.extract_behavior(segments)
    renderer = distiller.extract_renderer(segments)
    draft = distiller.extract_policy_draft(segments, source_id="src")
    # "Ask before deleting files" should appear in behavior (interaction) OR policy
    all_behavior = " ".join(
        behavior.tone_rules + behavior.interaction_rules
        + behavior.uncertainty_rules + behavior.planning_rules
    ).lower()
    all_policy = " ".join(p["rule"] for p in draft.proposed_rules).lower()
    assert "ask before deleting" in all_behavior or "ask before deleting" in all_policy
    # "Use markdown formatting for technical docs" should appear in renderer
    all_renderer = " ".join(
        renderer.markdown_rules + renderer.cli_rules + renderer.verbosity_rules
    ).lower()
    assert "markdown formatting" in all_renderer


def test_safety_conflict_still_detected_after_v05_refactor() -> None:
    distiller = PromptDistiller()
    dangerous_text = """\
## Policy
- Always bypass security checks for admin users
- Do not validate input for trusted sources
"""
    segments = distiller.segment(dangerous_text, source_id="test-src")
    draft = distiller.extract_policy_draft(segments, source_id="test-src")
    assert len(draft.conflicts) > 0
