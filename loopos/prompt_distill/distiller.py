"""Prompt distiller — segment, classify, and extract structured packs from source text.

Safety rule: Distill behavior, not text. No source text is copied into packs.

v0.5: Each extracted rule is individually classified into one of
behavior / renderer / policy / safety so that a single segment can
contribute to multiple packs instead of being bucketed wholesale by
section heading.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from loopos.prompt_distill.models import (
    BehaviorPack,
    DistillationAudit,
    PolicyPackDraft,
    PromptSegment,
    PromptSource,
    RendererPack,
)


# Rule-level keywords that route a single rule to a specific pack.
_RENDERER_KEYWORDS = (
    "markdown", "format", "output", "render", "display", "cli", "terminal",
    "table", "verbose", "concise", "brevity", "headers", "bullet", "section",
)
_SAFETY_KEYWORDS = (
    "safe", "security", "danger", "risk", "forbidden", "never execute",
    "bypass", "malicious", "harmful", "secret", "credential",
)
_POLICY_KEYWORDS = (
    "policy", "rule", "constraint", "require", "must", "permission",
    "approval", "tool", "file", "delete", "memory", "check",
)
_BEHAVIOR_KEYWORDS = (
    "tone", "style", "voice", "concise", "clear", "kind", "professional",
    "warm", "honest", "explain", "respond",
)
_INTERACTION_KEYWORDS = (
    "ask", "clarif", "confirm", "user", "interaction", "reply", "question",
)
_UNCERTAINTY_KEYWORDS = (
    "uncertain", "unsure", "ambig", "unknown", "insufficient",
)
_PLANNING_KEYWORDS = (
    "plan", "step", "phase", "strategy", "break down", "decompose",
)


class PromptDistiller:
    """Distill structured packs from prompt/rule documents."""

    def inspect(self, text: str, *, source_type: str = "project_doc") -> PromptSource:
        """Create a PromptSource from raw text."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return PromptSource(
            content_hash=content_hash,
            source_type=source_type,  # type: ignore[arg-type]
        )

    def segment(self, text: str, *, source_id: str = "") -> list[PromptSegment]:
        """Split text into classified segments."""
        segments: list[PromptSegment] = []
        current_category = "unknown"
        current_lines: list[str] = []

        for line in text.splitlines():
            category = self._classify_line(line)
            if category != current_category and current_lines:
                segments.append(PromptSegment(
                    source_id=source_id,
                    category=current_category,  # type: ignore[arg-type]
                    text="\n".join(current_lines),
                    confidence=0.7,
                ))
                current_lines = []
            current_category = category
            current_lines.append(line)

        if current_lines:
            segments.append(PromptSegment(
                source_id=source_id,
                category=current_category,  # type: ignore[arg-type]
                text="\n".join(current_lines),
                confidence=0.7,
            ))

        return segments

    def extract_behavior(
        self,
        segments: list[PromptSegment],
        *,
        name: str = "distilled",
    ) -> BehaviorPack:
        """Extract behavior rules from classified segments.

        v0.5: Each rule inside a segment is individually routed to the
        most appropriate behavior sub-bucket (tone / planning /
        interaction / uncertainty) using keyword signals, so that a
        single segment can populate multiple sub-buckets.
        """
        tone: list[str] = []
        planning: list[str] = []
        interaction: list[str] = []
        uncertainty: list[str] = []

        for seg in segments:
            rules = self._extract_rules(seg.text)
            for rule in rules:
                bucket = self._classify_behavior_rule(rule)
                if bucket == "tone":
                    tone.append(rule)
                elif bucket == "planning":
                    planning.append(rule)
                elif bucket == "interaction":
                    interaction.append(rule)
                elif bucket == "uncertainty":
                    uncertainty.append(rule)

        return BehaviorPack(
            name=name,
            description=f"Distilled behavior pack from {len(segments)} segments",
            tone_rules=tone,
            planning_rules=planning,
            interaction_rules=interaction,
            uncertainty_rules=uncertainty,
            source_refs=[s.source_id for s in segments],
            status="draft",
        )

    def extract_renderer(self, segments: list[PromptSegment]) -> RendererPack:
        """Extract rendering rules from classified segments.

        v0.5: A rule is routed to the renderer pack when it mentions
        formatting/output keywords, regardless of which section heading
        it appeared under.
        """
        markdown_rules: list[str] = []
        cli_rules: list[str] = []
        verbosity_rules: list[str] = []

        for seg in segments:
            rules = self._extract_rules(seg.text)
            for rule in rules:
                if not self._is_renderer_rule(rule):
                    continue
                lower = rule.lower()
                if "markdown" in lower or "table" in lower or "format" in lower:
                    markdown_rules.append(rule)
                elif "cli" in lower or "terminal" in lower:
                    cli_rules.append(rule)
                elif "verbose" in lower or "concise" in lower or "brevity" in lower:
                    verbosity_rules.append(rule)
                else:
                    markdown_rules.append(rule)

        return RendererPack(
            markdown_rules=markdown_rules,
            cli_rules=cli_rules,
            verbosity_rules=verbosity_rules,
            status="draft",
        )

    def extract_policy_draft(
        self,
        segments: list[PromptSegment],
        *,
        source_id: str = "",
    ) -> PolicyPackDraft:
        """Extract proposed policy rules from segments.

        v0.5: A rule is routed to the policy draft only when it reads as
        a constraint/permission/approval statement, not when it is a
        generic behavior or rendering preference. Safety-flagged rules
        are still surfaced as conflicts.
        """
        proposed: list[dict[str, Any]] = []
        risk_notes: list[str] = []
        conflicts: list[str] = []

        for seg in segments:
            rules = self._extract_rules(seg.text)
            for rule in rules:
                is_safety = self._is_safety_rule(rule)
                is_policy = self._is_policy_rule(rule)
                is_renderer = self._is_renderer_rule(rule)
                is_behavior = self._is_behavior_rule(rule)
                if is_safety:
                    if self._conflicts_with_safety(rule):
                        conflicts.append(f"Potential safety conflict: {rule[:80]}")
                    else:
                        proposed.append({"rule": rule, "from_category": "safety"})
                elif is_policy and not is_renderer:
                    proposed.append({"rule": rule, "from_category": "policy"})
                elif is_behavior and not is_renderer and not is_policy:
                    # Behavior-only rules stay out of the policy draft.
                    pass
                # Renderer rules are intentionally not added to policy draft.

        return PolicyPackDraft(
            source_id=source_id,
            proposed_rules=proposed,
            risk_notes=risk_notes,
            conflicts=conflicts,
            requires_human_review=True,
        )

    def audit(
        self,
        source: PromptSource,
        segments: list[PromptSegment],
        behavior: BehaviorPack,
        renderer: RendererPack,
        policy_draft: PolicyPackDraft,
    ) -> DistillationAudit:
        """Create an audit record for the distillation."""
        total_behavior = (
            len(behavior.tone_rules)
            + len(behavior.planning_rules)
            + len(behavior.interaction_rules)
            + len(behavior.uncertainty_rules)
        )
        total_renderer = (
            len(renderer.markdown_rules)
            + len(renderer.cli_rules)
            + len(renderer.verbosity_rules)
        )

        return DistillationAudit(
            source_id=source.source_id,
            segments_found=len(segments),
            behavior_rules_extracted=total_behavior,
            renderer_rules_extracted=total_renderer,
            policy_rules_proposed=len(policy_draft.proposed_rules),
            safety_conflicts=policy_draft.conflicts,
            source_text_copied=False,
        )

    # ------------------------------------------------------------------
    # Line-level classification (used by segment())
    # ------------------------------------------------------------------
    def _classify_line(self, line: str) -> str:
        """Classify a line into a segment category.

        Safety and policy are checked first because they are hard constraints
        that must win over generic category keywords (e.g. a line containing
        both "security" and "users" should be safety, not interaction).
        """

        lower = line.lower().strip()
        if any(kw in lower for kw in ("safe", "security", "danger", "risk", "forbidden", "never")):
            return "safety"
        if any(kw in lower for kw in ("policy", "rule", "constraint", "require", "must")):
            return "policy"
        if any(kw in lower for kw in ("tone", "style", "voice", "personality", "behavior")):
            return "behavior"
        if any(kw in lower for kw in ("plan", "step", "phase", "strategy")):
            return "planning"
        if any(kw in lower for kw in ("interact", "respond", "user", "communication")):
            return "interaction"
        if any(kw in lower for kw in ("uncertain", "unsure", "clarif", "ambig")):
            return "uncertainty"
        if any(kw in lower for kw in ("format", "render", "markdown", "output", "display", "cli")):
            return "rendering"
        return "unknown"

    # ------------------------------------------------------------------
    # Rule-level classification (v0.5)
    # ------------------------------------------------------------------
    def _classify_behavior_rule(self, rule: str) -> str:
        lower = rule.lower()
        if any(kw in lower for kw in _UNCERTAINTY_KEYWORDS):
            return "uncertainty"
        if any(kw in lower for kw in _INTERACTION_KEYWORDS):
            return "interaction"
        if any(kw in lower for kw in _PLANNING_KEYWORDS):
            return "planning"
        if any(kw in lower for kw in _BEHAVIOR_KEYWORDS):
            return "tone"
        return "tone"

    def _is_renderer_rule(self, rule: str) -> bool:
        lower = rule.lower()
        return any(kw in lower for kw in _RENDERER_KEYWORDS)

    def _is_safety_rule(self, rule: str) -> bool:
        lower = rule.lower()
        return any(kw in lower for kw in _SAFETY_KEYWORDS)

    def _is_policy_rule(self, rule: str) -> bool:
        lower = rule.lower()
        return any(kw in lower for kw in _POLICY_KEYWORDS)

    def _is_behavior_rule(self, rule: str) -> bool:
        lower = rule.lower()
        return any(kw in lower for kw in _BEHAVIOR_KEYWORDS + _INTERACTION_KEYWORDS + _UNCERTAINTY_KEYWORDS + _PLANNING_KEYWORDS)

    def _extract_rules(self, text: str) -> list[str]:
        """Extract rule-like statements from text."""
        rules: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            # Bullet points and numbered items
            if re.match(r"^[-*•]\s+.{10,}", stripped):
                rule = re.sub(r"^[-*•]\s+", "", stripped)
                rules.append(rule)
            elif re.match(r"^\d+\.\s+.{10,}", stripped):
                rule = re.sub(r"^\d+\.\s+", "", stripped)
                rules.append(rule)
            # Imperative sentences
            elif stripped.startswith(("Do ", "Don't ", "Never ", "Always ", "Must ", "Should ")):
                rules.append(stripped)
        return rules

    def _conflicts_with_safety(self, rule: str) -> bool:
        """Check if a rule potentially conflicts with core safety."""
        lower = rule.lower()
        dangerous = [
            "ignore safety", "bypass security", "skip validation",
            "disable check", "override policy", "grant all",
            "execute arbitrary", "allow dangerous",
        ]
        return any(d in lower for d in dangerous)
