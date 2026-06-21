"""Prompt distiller - segment, classify, and extract structured packs.

Safety rule: distill behavior, not source prose. Extracted rules are
canonicalized templates so long source passages cannot be copied into
active behavior, renderer, or policy packs.
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

_RENDERER_KEYWORDS = (
    "markdown",
    "format",
    "output",
    "render",
    "display",
    "cli",
    "terminal",
    "table",
    "verbose",
    "concise",
    "brevity",
    "headers",
    "bullet",
    "section",
)
_SAFETY_KEYWORDS = (
    "safe",
    "security",
    "danger",
    "risk",
    "forbidden",
    "never execute",
    "bypass",
    "malicious",
    "harmful",
    "secret",
    "credential",
)
_POLICY_KEYWORDS = (
    "policy",
    "rule",
    "constraint",
    "require",
    "must",
    "permission",
    "approval",
    "tool",
    "file",
    "delete",
    "memory",
    "check",
)
_BEHAVIOR_KEYWORDS = (
    "tone",
    "style",
    "voice",
    "concise",
    "clear",
    "kind",
    "professional",
    "warm",
    "honest",
    "explain",
    "respond",
)
_INTERACTION_KEYWORDS = ("ask", "clarif", "confirm", "user", "interaction", "reply", "question")
_UNCERTAINTY_KEYWORDS = ("uncertain", "unsure", "ambig", "unknown", "insufficient")
_PLANNING_KEYWORDS = ("plan", "step", "phase", "strategy", "break down", "decompose")


class PromptDistiller:
    """Distill structured packs from prompt/rule documents."""

    def inspect(self, text: str, *, source_type: str = "project_doc") -> PromptSource:
        """Create a PromptSource from raw text with a full source hash."""

        source_sha256 = hashlib.sha256(text.encode()).hexdigest()
        return PromptSource(
            content_hash=source_sha256[:16],
            source_sha256=source_sha256,
            source_type=source_type,  # type: ignore[arg-type]
        )

    def segment(
        self,
        text: str,
        *,
        source_id: str = "",
        source_hash: str = "",
    ) -> list[PromptSegment]:
        """Split text into classified, multi-tagged segments."""

        segments: list[PromptSegment] = []
        current_category = "unknown"
        current_lines: list[str] = []

        for line in text.splitlines():
            category = self._classify_line(line)
            if category != current_category and current_lines:
                segments.append(
                    self._make_segment(
                        current_lines,
                        source_id=source_id,
                        source_hash=source_hash,
                        category=current_category,
                    )
                )
                current_lines = []
            current_category = category
            current_lines.append(line)

        if current_lines:
            segments.append(
                self._make_segment(
                    current_lines,
                    source_id=source_id,
                    source_hash=source_hash,
                    category=current_category,
                )
            )

        return segments

    def extract_behavior(
        self,
        segments: list[PromptSegment],
        *,
        name: str = "distilled",
    ) -> BehaviorPack:
        tone: list[str] = []
        planning: list[str] = []
        interaction: list[str] = []
        uncertainty: list[str] = []

        for seg in segments:
            for rule in self._extract_rules(seg.text):
                bucket = self._classify_behavior_rule(rule)
                if bucket == "planning":
                    planning.append(rule)
                elif bucket == "interaction":
                    interaction.append(rule)
                elif bucket == "uncertainty":
                    uncertainty.append(rule)
                else:
                    tone.append(rule)

        return BehaviorPack(
            name=name,
            description=f"Distilled behavior pack from {len(segments)} segments",
            tone_rules=_dedupe(tone),
            planning_rules=_dedupe(planning),
            interaction_rules=_dedupe(interaction),
            uncertainty_rules=_dedupe(uncertainty),
            source_refs=[s.source_id for s in segments],
            status="draft",
        )

    def extract_renderer(self, segments: list[PromptSegment]) -> RendererPack:
        markdown_rules: list[str] = []
        cli_rules: list[str] = []
        verbosity_rules: list[str] = []

        for seg in segments:
            for rule in self._extract_rules(seg.text):
                if not self._is_renderer_rule(rule):
                    continue
                lower = rule.lower()
                if "terminal" in lower or "cli" in lower:
                    cli_rules.append(rule)
                elif "concise" in lower or "verbose" in lower:
                    verbosity_rules.append(rule)
                else:
                    markdown_rules.append(rule)

        return RendererPack(
            markdown_rules=_dedupe(markdown_rules),
            cli_rules=_dedupe(cli_rules),
            verbosity_rules=_dedupe(verbosity_rules),
            status="draft",
        )

    def extract_policy_draft(
        self,
        segments: list[PromptSegment],
        *,
        source_id: str = "",
    ) -> PolicyPackDraft:
        proposed: list[dict[str, Any]] = []
        conflicts: list[str] = []

        for seg in segments:
            for rule in self._extract_rules(seg.text):
                is_safety = self._is_safety_rule(rule)
                is_policy = self._is_policy_rule(rule)
                is_renderer = self._is_renderer_rule(rule)
                if self._conflicts_with_safety(rule):
                    conflicts.append("Potential safety conflict: policy bypass request")
                elif is_safety or (is_policy and not is_renderer):
                    proposed.append({"rule": rule, "from_tags": seg.tags, "source_segment": seg.segment_hash})

        return PolicyPackDraft(
            source_id=source_id,
            source_hash=segments[0].source_hash if segments else "",
            proposed_rules=_dedupe_dicts(proposed),
            conflicts=_dedupe(conflicts),
            policy_conflicts=_dedupe(conflicts),
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
        copied_rule_ids = self._copied_rule_ids(behavior, renderer, policy_draft)

        return DistillationAudit(
            source_id=source.source_id,
            source_hash=source.source_sha256 or source.content_hash,
            segments_found=len(segments),
            behavior_rules_extracted=total_behavior,
            renderer_rules_extracted=total_renderer,
            policy_rules_proposed=len(policy_draft.proposed_rules),
            safety_conflicts=policy_draft.conflicts,
            policy_conflicts=policy_draft.policy_conflicts,
            source_text_copied=bool(copied_rule_ids),
            copied_rule_ids=copied_rule_ids,
            activation_ready=not copied_rule_ids and not policy_draft.conflicts,
        )

    def _make_segment(
        self,
        lines: list[str],
        *,
        source_id: str,
        source_hash: str,
        category: str,
    ) -> PromptSegment:
        text = "\n".join(lines)
        return PromptSegment(
            source_id=source_id,
            source_hash=source_hash,
            segment_hash=hashlib.sha256(text.encode()).hexdigest(),
            category=category,  # type: ignore[arg-type]
            tags=self._classify_tags(text),
            text=text,
            confidence=0.7,
        )

    def _classify_line(self, line: str) -> str:
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

    def _classify_tags(self, text: str) -> list[str]:
        lower = text.lower()
        groups = {
            "behavior": _BEHAVIOR_KEYWORDS,
            "planning": _PLANNING_KEYWORDS,
            "interaction": _INTERACTION_KEYWORDS,
            "uncertainty": _UNCERTAINTY_KEYWORDS,
            "rendering": _RENDERER_KEYWORDS,
            "safety": _SAFETY_KEYWORDS,
            "policy": _POLICY_KEYWORDS,
        }
        tags = [tag for tag, keywords in groups.items() if any(kw in lower for kw in keywords)]
        return tags or ["unknown"]

    def _classify_behavior_rule(self, rule: str) -> str:
        lower = rule.lower()
        if any(kw in lower for kw in _UNCERTAINTY_KEYWORDS):
            return "uncertainty"
        if any(kw in lower for kw in _INTERACTION_KEYWORDS):
            return "interaction"
        if any(kw in lower for kw in _PLANNING_KEYWORDS):
            return "planning"
        return "tone"

    def _is_renderer_rule(self, rule: str) -> bool:
        return any(kw in rule.lower() for kw in _RENDERER_KEYWORDS)

    def _is_safety_rule(self, rule: str) -> bool:
        return any(kw in rule.lower() for kw in _SAFETY_KEYWORDS)

    def _is_policy_rule(self, rule: str) -> bool:
        return any(kw in rule.lower() for kw in _POLICY_KEYWORDS)

    def _is_behavior_rule(self, rule: str) -> bool:
        lower = rule.lower()
        keywords = _BEHAVIOR_KEYWORDS + _INTERACTION_KEYWORDS + _UNCERTAINTY_KEYWORDS + _PLANNING_KEYWORDS
        return any(kw in lower for kw in keywords)

    def _extract_rules(self, text: str) -> list[str]:
        rules: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^[-*•]\s+.{10,}", stripped):
                rules.append(self._distill_rule(re.sub(r"^[-*•]\s+", "", stripped)))
            elif re.match(r"^\d+\.\s+.{10,}", stripped):
                rules.append(self._distill_rule(re.sub(r"^\d+\.\s+", "", stripped)))
            elif stripped.startswith(("Do ", "Don't ", "Never ", "Always ", "Must ", "Should ")):
                rules.append(self._distill_rule(stripped))
        return _dedupe([rule for rule in rules if rule])

    def _distill_rule(self, raw: str) -> str:
        lower = raw.lower()
        if self._conflicts_with_safety(raw):
            return "Reject rules that bypass security, validation, or policy gates."
        if "dangerous shell" in lower:
            return "Block dangerous shell commands through policy gates."
        if "permissions before file" in lower or ("permission" in lower and "file" in lower):
            return "Require permissions before file operations."
        if "ask before deleting" in lower or ("ask" in lower and "delet" in lower):
            return "Ask before deleting files and require policy approval."
        if any(keyword in lower for keyword in ("approval", "permission", "policy", "must", "require")):
            return "Require explicit policy and approval gates for constrained actions."
        if self._is_safety_rule(raw):
            return "Preserve safety checks before tools, memory writes, and external actions."
        if "markdown" in lower:
            return "Use Markdown formatting for structured outputs."
        if "cli" in lower or "terminal" in lower:
            return "Render terminal output with clear status and evidence."
        if self._is_renderer_rule(raw):
            return "Render concise structured terminal output with clear status and evidence."
        if any(keyword in lower for keyword in _PLANNING_KEYWORDS):
            return "Use explicit phased plans for multi-step work."
        if any(keyword in lower for keyword in _INTERACTION_KEYWORDS):
            return "Ask for clarification when user intent is ambiguous or risky."
        if any(keyword in lower for keyword in _UNCERTAINTY_KEYWORDS):
            return "State uncertainty and missing information explicitly."
        if self._is_behavior_rule(raw):
            return "Use clear, professional, direct communication."
        return ""

    def _conflicts_with_safety(self, rule: str) -> bool:
        lower = rule.lower()
        dangerous = (
            "ignore safety",
            "bypass security",
            "bypass safety",
            "skip validation",
            "disable check",
            "override policy",
            "grant all",
            "execute arbitrary",
            "allow dangerous",
        )
        return any(item in lower for item in dangerous)

    def _copied_rule_ids(
        self,
        behavior: BehaviorPack,
        renderer: RendererPack,
        policy_draft: PolicyPackDraft,
    ) -> list[str]:
        rules = (
            behavior.tone_rules
            + behavior.planning_rules
            + behavior.interaction_rules
            + behavior.uncertainty_rules
            + renderer.markdown_rules
            + renderer.cli_rules
            + renderer.verbosity_rules
            + [str(rule.get("rule", "")) for rule in policy_draft.proposed_rules]
        )
        return [f"rule-{idx}" for idx, rule in enumerate(rules) if len(rule.split()) > 30]


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _dedupe_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = json_key(item)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def json_key(item: dict[str, Any]) -> str:
    return repr(sorted(item.items()))
