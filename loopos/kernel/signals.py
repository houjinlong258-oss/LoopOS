"""Signals consumed by the deterministic kernel scheduler."""

from enum import Enum


class KernelSignal(str, Enum):
    CONTINUE = "continue"
    APPROVE = "approve"
    DENY = "deny"
    CANCEL = "cancel"
    REPAIR = "repair"
    REPLAN = "replan"
    HALT = "halt"

