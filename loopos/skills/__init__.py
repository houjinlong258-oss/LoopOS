"""LoopOS v0.3 skills — memory-backed compatibility shim.

.. important::

    **Skills on v0.3 are memory-backed.** The canonical
    implementation lives in
    :mod:`loopos.memory.skill_store` (the ``Skill`` /
    ``SkillStore`` / ``extract_skill_from_events`` family) and
    :mod:`loopos.memory.skill_proposals` (the ``SkillProposal``
    contract). This package is a 4-line re-export shim that
    keeps the public ``loopos.skills`` namespace visible while
    the actual code lives in :mod:`loopos.memory` for historical
    reasons (skills are part of the memory governance surface;
    the AGENTS.md blueprint in the v0.2 era placed them in
    ``loopos/memory/``).

    **Full Skill Governance is deferred to v0.4.** On v0.3 the
    surface is:

    * read existing skills (``SkillStore.list()``);
    * extract a skill from a finished run
      (``extract_skill_from_events``);
    * propose a new skill (``SkillProposal``);
    * accept / reject / merge a proposal.

    What the v0.3 surface does **not** do:

    * auto-merge proposals without a human or governance step;
    * score proposals against an external model;
    * persist skill lineage beyond ``source_run_id``;
    * expose a kernel-loop / AIL hook for skill dispatch;
    * enforce a skill-versioning policy.

    These are the v0.4 work items. They are explicitly out of
    scope for the v0.3-alpha → v0.3-RC hardening pass.

    See :doc:`v0-3-skills-boundary` for the full decision
    record and the v0.4 plan.
"""

from __future__ import annotations

from loopos.memory.skill_proposals import SkillProposal
from loopos.memory.skill_store import Skill, SkillStore, extract_skill_from_events

__all__ = ["Skill", "SkillProposal", "SkillStore", "extract_skill_from_events"]