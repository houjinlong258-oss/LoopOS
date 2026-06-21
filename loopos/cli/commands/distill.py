"""CLI commands for Prompt / Policy Distillation.

Subcommands:
    loopos distill inspect <file>
    loopos distill draft <file>
    loopos distill audit <draft_id>  (re-derives audit from file)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.prompt_distill.distiller import PromptDistiller


def distill_command(
    action: str = "inspect",
    target: str | None = None,
    *,
    json_output: bool = False,
) -> int:
    """Entry point for ``loopos distill <action>``."""

    if not target:
        print("distill requires a file path.", file=sys.stderr)
        return 1
    path = Path(target)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")

    distiller = PromptDistiller()

    if action == "inspect":
        source = distiller.inspect(text)
        if json_output:
            print(source.model_dump_json(indent=2))
        else:
            print(f"Source ID:    {source.source_id}")
            print(f"Content hash: {source.content_hash}")
            print(f"Source type:  {source.source_type}")
        return 0

    if action == "draft":
        source = distiller.inspect(text)
        segments = distiller.segment(text, source_id=source.source_id)
        behavior = distiller.extract_behavior(segments, name=path.stem)
        renderer = distiller.extract_renderer(segments)
        policy_draft = distiller.extract_policy_draft(segments, source_id=source.source_id)
        if json_output:
            payload = {
                "source": source.model_dump(mode="json"),
                "behavior": behavior.model_dump(mode="json"),
                "renderer": renderer.model_dump(mode="json"),
                "policy_draft": policy_draft.model_dump(mode="json"),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Distilled packs from {path.name}")
            print(
                f"  behavior:   {len(behavior.tone_rules)} tone, "
                f"{len(behavior.planning_rules)} planning, "
                f"{len(behavior.interaction_rules)} interaction, "
                f"{len(behavior.uncertainty_rules)} uncertainty"
            )
            print(
                f"  renderer:   {len(renderer.markdown_rules)} markdown, "
                f"{len(renderer.cli_rules)} cli, "
                f"{len(renderer.verbosity_rules)} verbosity"
            )
            print(f"  policy:     {len(policy_draft.proposed_rules)} proposed rules")
            print(f"  conflicts:  {len(policy_draft.conflicts)}")
            print(f"  review:     {policy_draft.requires_human_review}")
        return 0

    if action == "audit":
        source = distiller.inspect(text)
        segments = distiller.segment(text, source_id=source.source_id)
        behavior = distiller.extract_behavior(segments)
        renderer = distiller.extract_renderer(segments)
        policy_draft = distiller.extract_policy_draft(segments, source_id=source.source_id)
        audit = distiller.audit(source, segments, behavior, renderer, policy_draft)
        if json_output:
            print(audit.model_dump_json(indent=2))
        else:
            print(f"Segments found:           {audit.segments_found}")
            print(f"Behavior rules extracted: {audit.behavior_rules_extracted}")
            print(f"Renderer rules extracted: {audit.renderer_rules_extracted}")
            print(f"Policy rules proposed:    {audit.policy_rules_proposed}")
            print(f"Safety conflicts:         {len(audit.safety_conflicts)}")
            print(f"Source text copied:        {audit.source_text_copied}")
        return 0

    print(f"Unknown distill action: {action}", file=sys.stderr)
    return 1
