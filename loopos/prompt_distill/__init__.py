"""Prompt / Policy Distillation — turn project prompts into structured packs.

Safety rule: Distill behavior, not text. Do not copy proprietary prompts.
"""

from loopos.prompt_distill.models import (
    BehaviorPack,
    PolicyPackDraft,
    PromptSource,
    RendererPack,
)

__all__ = [
    "BehaviorPack",
    "PolicyPackDraft",
    "PromptSource",
    "RendererPack",
]
