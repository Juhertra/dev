"""
Workflow Engine Package

This package contains the workflow execution engine for SecFlow.
Implementation will be added in M3.

Import Rules:
- May import from runtime_core
- May import from findings
- May be imported by other packages
- May NOT import from wrappers or parsers
"""

from .executor import WorkflowExecutor, Workflow, WorkflowNode
from .validator import RecipeValidator

__version__ = "0.1.0"
__all__ = ["WorkflowExecutor", "Workflow", "WorkflowNode", "RecipeValidator"]
