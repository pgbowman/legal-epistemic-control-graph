"""Pytest configuration: add repo root to sys.path so `import src.*` works
when pytest is run from a fresh checkout without `pip install -e .`.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
