"""Deterministic ambiguity analysis and goal proposal generation."""

from __future__ import annotations

from loopos.goal.models import GoalAnalysis, GoalOption, GoalProposal, GoalSpec

_VAGUE_PHRASES = (
    "优化这个项目",
    "改进这个项目",
    "完善这个项目",
    "帮我优化",
    "make it better",
    "improve this project",
)
_CONCRETE_MARKERS = (
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
)


class GoalNegotiator:
    def analyze(self, raw_goal: str) -> GoalAnalysis:
        value = raw_goal.strip()
        if not value:
            return GoalAnalysis(
                raw_goal=raw_goal,
                ambiguous=True,
                reasons=["goal.empty"],
                missing_information=["objective", "success_criteria"],
            )
        lowered = value.lower()
        vague = any(phrase in lowered for phrase in _VAGUE_PHRASES)
        concrete = any(marker in lowered for marker in _CONCRETE_MARKERS)
        ambiguous = vague and not concrete
        return GoalAnalysis(
            raw_goal=value,
            ambiguous=ambiguous,
            reasons=["goal.vague_scope"] if ambiguous else ["goal.concrete_enough"],
            missing_information=["priority", "success_criteria"] if ambiguous else [],
        )

    def propose(self, raw_goal: str) -> GoalProposal:
        analysis = self.analyze(raw_goal)
        options = [
            GoalOption(
                id=1,
                title="架构审计优先",
                objective="审计当前架构、依赖和风险，输出按优先级排序的改进清单。",
                success_criteria=["完成仓库审计", "列出风险", "给出可执行任务"],
            ),
            GoalOption(
                id=2,
                title="MVP 快速落地",
                objective="选择最小用户价值路径并完成一个可运行、可测试的 MVP 增量。",
                success_criteria=["核心流程可运行", "测试通过", "限制已记录"],
            ),
            GoalOption(
                id=3,
                title="Kernel 架构升级",
                objective="优先加强 AIL、调度、Policy、Syscall、Trace 和 Replay 内核闭环。",
                success_criteria=["内核路径结构化", "策略不可绕过", "运行可回放"],
            ),
            GoalOption(
                id=4,
                title="CLI UI 优先",
                objective="优先改善终端命令、状态展示、诊断和交互审批体验。",
                success_criteria=["核心命令完整", "输出一致", "JSON 模式稳定"],
            ),
            GoalOption(
                id=5,
                title="自定义 / 合并",
                objective="由用户补充约束，或合并多个方案后形成最终目标。",
                success_criteria=["约束已确认", "范围已确认", "验收标准已确认"],
            ),
        ]
        return GoalProposal(analysis=analysis, options=options)

    def finalize(self, raw_goal: str, *, option_ids: list[int] | None = None) -> GoalSpec:
        proposal = self.propose(raw_goal)
        selected = option_ids or []
        if proposal.analysis.ambiguous and not selected:
            raise ValueError("ambiguous goal requires a selected option")
        if selected:
            options = [option for option in proposal.options if option.id in selected]
            if len(options) != len(set(selected)):
                raise ValueError("unknown goal option")
            objective = " ".join(option.objective for option in options)
            criteria = list(
                dict.fromkeys(item for option in options for item in option.success_criteria)
            )
        else:
            objective = raw_goal.strip()
            criteria = ["requested outcome observed", "policy constraints satisfied"]
        return GoalSpec(
            raw_goal=raw_goal.strip(),
            objective=objective,
            selected_option_ids=selected,
            success_criteria=criteria,
            constraints=["Policy OS enforced", "all external actions use syscalls"],
        )

