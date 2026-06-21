"""Deterministic ambiguity analysis and goal proposal generation."""

from __future__ import annotations

from loopos.goal.models import GoalAnalysis, GoalOption, GoalProposal, GoalSpec
from loopos.data_guard.detector import detect_data_operation

_VAGUE_PHRASES = (
    "优化这个项目",
    "改进这个项目",
    "完善这个项目",
    "帮我优化",
    "make it better",
    "improve this project",
    "fix it",
    "甯垜浼樺寲杩欎釜椤圭洰",
)
_CONCRETE_MARKERS = (
    "demo",
    ".py",
    ".md",
    "pytest",
    "内容",
    "运行",
    "确认输出",
    "修复",
    "实现",
    "创建",
    "删除",
    "重命名",
    "--dry-run",
)
_ACCEPTANCE_MARKERS = ("确认", "通过", "输出", "验收", "测试", "verify", "pass")
_RISK_MARKERS = ("database", "数据库", "production", "生产", "删除", "支付", "secret")


class GoalNegotiator:
    def analyze(self, raw_goal: str) -> GoalAnalysis:
        value = raw_goal.strip()
        if not value:
            return GoalAnalysis(
                raw_goal=raw_goal,
                ambiguous=True,
                level="high",
                score=1.0,
                missing_fields=["objective", "scope", "acceptance_criteria"],
                requires_negotiation=True,
                reason_codes=["goal.empty"],
            )
        lowered = value.lower()
        vague = any(phrase in lowered for phrase in _VAGUE_PHRASES)
        concrete = any(marker in lowered for marker in _CONCRETE_MARKERS)
        has_acceptance = any(marker in lowered for marker in _ACCEPTANCE_MARKERS)
        risk_factors = [marker for marker in _RISK_MARKERS if marker in lowered]
        data_detection = detect_data_operation(value)
        if data_detection.detected:
            risk_factors.extend(data_detection.reason_codes)
        score = 0.0
        missing: list[str] = []
        reasons: list[str] = []
        if vague:
            score += 0.55
            reasons.append("goal.vague_scope")
            missing.append("scope")
        if not concrete:
            score += 0.2
            reasons.append("goal.missing_deliverable")
            missing.append("deliverables")
        if not has_acceptance:
            score += 0.15
            reasons.append("goal.missing_acceptance_criteria")
            missing.append("acceptance_criteria")
        if len(value) < 12:
            score += 0.1
            reasons.append("goal.too_short")
        if risk_factors and not has_acceptance:
            score += 0.1
            reasons.append("goal.risk_needs_confirmation")
        if data_detection.requires_backup:
            score = max(score, 0.7)
            reasons.append("goal.data_guard_required")
            missing.extend(["backup_plan", "rollback_plan"])
        score = min(1.0, score)
        level = "high" if score >= 0.65 else "medium" if score >= 0.35 else "low"
        if level == "low":
            reasons = reasons or ["goal.concrete_enough"]
        return GoalAnalysis(
            raw_goal=value,
            ambiguous=level == "high",
            level=level,
            score=score,
            missing_fields=list(dict.fromkeys(missing)),
            risk_factors=list(dict.fromkeys(risk_factors)),
            requires_confirmation=level == "medium",
            requires_negotiation=level == "high",
            reason_codes=reasons,
        )

    def propose(self, raw_goal: str) -> GoalProposal:
        analysis = self.analyze(raw_goal)
        if detect_data_operation(raw_goal).detected:
            options = [
                GoalOption(
                    id=1,
                    title="只读数据库风险审计",
                    objective="只生成备份、迁移和回滚计划，不执行数据库写操作",
                    scope=["database metadata and migration files"],
                    non_goals=["database writes"],
                    deliverables=["risk report", "backup plan", "rollback checklist"],
                    acceptance_criteria=["no database connection opened", "rollback plan exists"],
                    risk="low",
                    estimated_steps=3,
                ),
                GoalOption(
                    id=2,
                    title="备份、Shadow Run 与验证",
                    objective="验证本地备份，在隔离 mock shadow 中生成迁移和验证报告",
                    scope=["workspace-local samples and migration plans"],
                    non_goals=["production migration execution"],
                    deliverables=["verified backup", "shadow plan", "validation report"],
                    acceptance_criteria=_data_acceptance_criteria(),
                    risk="high",
                    estimated_steps=7,
                    recommended=True,
                ),
                GoalOption(
                    id=3,
                    title="手工执行清单",
                    objective="仅生成供用户手工执行和确认的命令与检查清单",
                    scope=["manual migration guidance"],
                    non_goals=["agent-executed database writes"],
                    deliverables=["manual checklist"],
                    acceptance_criteria=["human approval recorded", "rollback plan exists"],
                    risk="medium",
                    estimated_steps=4,
                ),
            ]
            return GoalProposal(analysis=analysis, options=options, recommended_option_id=2)
        options = [
            self._option(1, "架构审计优先", "审计当前架构、依赖和风险并给出任务清单", 4),
            self._option(2, "MVP 快速落地", "完成最小可运行、可测试的用户价值增量", 5, recommended=True),
            self._option(3, "Kernel 架构升级", "加强 AIL、调度、Policy、Syscall、Trace 和 Replay", 8),
            self._option(4, "CLI UI 优先", "改进终端命令、诊断、状态展示和审批体验", 5),
            self._option(5, "自定义或合并", "补充约束或合并多个方案形成最终目标", 3),
        ]
        return GoalProposal(analysis=analysis, options=options, recommended_option_id=2)

    def finalize(
        self,
        raw_goal: str,
        *,
        option_ids: list[int] | None = None,
        confirmed: bool = False,
        manual_objective: str | None = None,
    ) -> GoalSpec:
        proposal = self.propose(raw_goal)
        selected = option_ids or []
        if proposal.analysis.requires_negotiation and not selected and not manual_objective:
            raise ValueError("ambiguous goal requires a selected option")
        if proposal.analysis.requires_confirmation and not confirmed and not selected:
            raise ValueError("medium-ambiguity goal requires confirmation")
        if selected:
            options = [option for option in proposal.options if option.id in selected]
            if len(options) != len(set(selected)):
                raise ValueError("unknown goal option")
            objective = " ".join(option.objective for option in options)
            criteria = list(dict.fromkeys(item for option in options for item in option.acceptance_criteria))
            scope = list(dict.fromkeys(item for option in options for item in option.scope))
            deliverables = list(dict.fromkeys(item for option in options for item in option.deliverables))
            origin = "merged" if len(options) > 1 else "selected"
            risk = max((option.risk for option in options), key=("low", "medium", "high", "critical").index)
            estimated_steps = sum(option.estimated_steps for option in options)
        else:
            objective = manual_objective or raw_goal.strip()
            criteria = ["requested outcome observed", "policy constraints satisfied"]
            scope = [objective]
            deliverables = ["verified goal outcome"]
            origin = "manual" if manual_objective else "confirmed" if confirmed else "direct"
            risk = "medium" if proposal.analysis.risk_factors else "low"
            estimated_steps = 3
        if detect_data_operation(raw_goal).detected:
            criteria = list(dict.fromkeys([*criteria, *_data_acceptance_criteria()]))
        return GoalSpec(
            raw_goal=raw_goal.strip(),
            objective=objective,
            origin=origin,
            selected_option_ids=selected,
            scope=scope,
            deliverables=deliverables,
            acceptance_criteria=criteria,
            constraints=["Policy OS enforced", "all external actions use syscalls"],
            risk=risk,
            estimated_steps=estimated_steps,
        )

    @staticmethod
    def _option(
        option_id: int,
        title: str,
        objective: str,
        estimated_steps: int,
        *,
        recommended: bool = False,
    ) -> GoalOption:
        return GoalOption(
            id=option_id,
            title=title,
            objective=objective,
            scope=[objective],
            non_goals=["unrelated repository rewrites"],
            deliverables=[objective],
            acceptance_criteria=["requested outcome observed", "tests pass", "policy constraints satisfied"],
            risk="medium" if option_id in {3, 5} else "low",
            estimated_steps=estimated_steps,
            recommended=recommended,
        )


def _data_acceptance_criteria() -> list[str]:
    return [
        "backup verified",
        "shadow migration passed",
        "validation passed",
        "rollback plan exists",
        "no sensitive data leaked to trace",
    ]
