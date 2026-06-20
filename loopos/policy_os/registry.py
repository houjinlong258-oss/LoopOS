"""Policy registry."""

from __future__ import annotations

from loopos.policy_os.models import PolicyPack, PolicyRule


class PolicyRegistry:
    """In-memory registry for policy packs and rules."""

    def __init__(self, packs: list[PolicyPack] | None = None) -> None:
        self.packs: list[PolicyPack] = []
        self.rules: list[PolicyRule] = []
        for pack in packs or []:
            self.add_pack(pack)

    def add_pack(self, pack: PolicyPack) -> None:
        self.packs.append(pack)
        self.rules.extend(rule for rule in pack.rules if rule.enabled)

    def list_rules(self, *, scope: str | None = None, tag: str | None = None) -> list[PolicyRule]:
        rules = self.rules
        if scope is not None:
            rules = [rule for rule in rules if rule.scope == scope]
        if tag is not None:
            rules = [rule for rule in rules if tag in rule.tags]
        return sorted(rules, key=lambda rule: rule.priority, reverse=True)

    def get_rule(self, rule_id: str) -> PolicyRule:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        raise KeyError(f"unknown policy rule: {rule_id}")

    def get_pack(self, pack_id: str) -> PolicyPack:
        for pack in self.packs:
            if pack.id == pack_id:
                return pack
        raise KeyError(f"unknown policy pack: {pack_id}")
