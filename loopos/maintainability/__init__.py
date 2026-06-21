"""Maintainability Kernel — code quality governance for LoopOS.

Prevents AI-generated code from becoming unmaintainable.
Passing tests is necessary but not sufficient.
"""

from loopos.maintainability.architecture import ArchitectureBoundaryRules, ArchitectureConfig
from loopos.maintainability.debt import TechnicalDebtItem, TechnicalDebtRegistry
from loopos.maintainability.models import (
    CodeChangeSummary,
    MaintainabilityFinding,
    MaintainabilityGateDecision,
    MaintainabilityReport,
)
from loopos.maintainability.test_quality import TestQualityRules

__all__ = [
    "ArchitectureBoundaryRules",
    "ArchitectureConfig",
    "CodeChangeSummary",
    "MaintainabilityFinding",
    "MaintainabilityGateDecision",
    "MaintainabilityReport",
    "TechnicalDebtItem",
    "TechnicalDebtRegistry",
    "TestQualityRules",
]
