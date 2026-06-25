"""LAIL agent roles."""

from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    LOOP_CONTROLLER = "loop_controller"
    PLANNER = "planner"
    BUILDER = "builder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    REPAIRER = "repairer"
    OPTIMIZER = "optimizer"
    MAD_DOG = "mad_dog"
    DELIVERY_EVALUATOR = "delivery_evaluator"
    MEMORY_COMPILER = "memory_compiler"
    COMPUTER_OPERATOR = "computer_operator"
    VISUAL_TESTER = "visual_tester"
    UI_REVIEWER = "ui_reviewer"


ALL_AGENT_ROLES: tuple[AgentRole, ...] = tuple(AgentRole)


__all__ = ["ALL_AGENT_ROLES", "AgentRole"]
