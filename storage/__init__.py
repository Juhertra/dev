"""Storage facade (Phase 1).
Thin wrappers re-export existing file-backed functions to provide a stable
import path for future refactors without changing behavior now.
"""

from .projects import *  # noqa
from .state import *  # noqa
from .findings import *  # noqa
from .runs import *  # noqa
from .profiles import *  # noqa

__all__ = []


