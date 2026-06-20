"""Memory, profile, and skill CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.memory.repository import MemoryRepository


def skills_command(
    action: str = "list",
    arg: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    repo = MemoryRepository(data_paths(data_dir)["base"])
    skills = repo.skills.list()
    if action == "review":
        proposals = repo.list_skill_proposals(status="pending")
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in proposals],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "accept":
        if not arg:
            print("skills accept requires PROPOSAL_ID.", file=sys.stderr)
            return 1
        try:
            proposal = repo.commit_skill_proposal(arg)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{proposal.status}: {proposal.id}")
        return 0 if proposal.status in {"accepted", "merged"} else 1
    if action == "disable":
        if not arg:
            print("skills disable requires SKILL_ID.", file=sys.stderr)
            return 1
        for skill in skills:
            if skill.id == arg:
                skill.status = "disabled"
                repo.skills.upsert(skill)
                repo.index.upsert_skill(skill)
                print(f"disabled: {skill.id}")
                return 0
        print(f"Skill not found: {arg}", file=sys.stderr)
        return 1
    if action != "list":
        print(f"Unknown skills action: {action}", file=sys.stderr)
        return 1
    skills = [skill for skill in skills if skill.status == "active"]
    if not skills:
        print("No skills stored.")
        return 0
    print(
        json.dumps(
            [skill.model_dump(mode="json") for skill in skills],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def memory_command(
    action: str = "list",
    arg: str | None = None,
    *,
    from_run: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
) -> int:
    repo = MemoryRepository(data_paths(data_dir)["base"])
    if action == "list":
        items = repo.list_memory(status="active")
        if not items:
            print("No active memory.")
            return 0
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in items],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "search":
        if not arg:
            print("Search query is required.", file=sys.stderr)
            return 1
        items = repo.retrieve(query_text=arg, tags=arg.split(), limit=10)
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in items],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "propose":
        if not from_run:
            print("--from-run RUN_ID is required.", file=sys.stderr)
            return 1
        proposal = repo.proposal_for_run(from_run)
        repo.propose(proposal)
        print(f"Created proposal {proposal.id}")
        if verbose:
            print(proposal.model_dump_json(indent=2))
        return 0
    if action == "review":
        proposals = repo.list_proposals(status="pending")
        if not proposals:
            print("No pending memory proposals.")
            return 0
        print(
            json.dumps(
                [proposal.model_dump(mode="json") for proposal in proposals],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action in {"accept", "reject"}:
        if not arg:
            print(f"Proposal id is required for memory {action}.", file=sys.stderr)
            return 1
        try:
            proposal = repo.decide_proposal(
                arg,
                "accepted" if action == "accept" else "rejected",
                reasons=[f"CLI {action}"],
            )
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{proposal.status}: {proposal.id}")
        return 0
    if action == "reindex":
        counts = repo.reindex()
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    print(f"Unknown memory action: {action}", file=sys.stderr)
    return 1


def profile_command(
    action: str = "show",
    key: str | None = None,
    value: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    repo = MemoryRepository(data_paths(data_dir)["base"])
    if action == "show":
        profile = repo.get_profile()
        if not profile:
            print("No user profile.")
        else:
            print(json.dumps(profile, ensure_ascii=False, indent=2))
        return 0
    if action == "set":
        if not key or value is None:
            print("profile set requires KEY and VALUE.", file=sys.stderr)
            return 1
        repo.set_profile(key, value)
        print(f"Set profile {key}")
        return 0
    print(f"Unknown profile action: {action}", file=sys.stderr)
    return 1
