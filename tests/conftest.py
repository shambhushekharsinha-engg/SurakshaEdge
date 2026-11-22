"""
Pytest configuration and test environment bootstrapping for SurakshaEdge.
Ensures seamless import resolution for 'surakshaedge' across all operating systems
(Windows, Linux case-sensitive CI, Docker) regardless of directory capitalization.
"""
import os
import sys
import types
from pathlib import Path

# Identify repository root
_repo_root = Path(__file__).parent.parent.resolve()

# Bootstrap 'surakshaedge' as a virtual package pointing to the repo root
# so 'from surakshaedge.edge...' and 'from surakshaedge.api...' always resolve.
if "surakshaedge" not in sys.modules:
    _pkg = types.ModuleType("surakshaedge")
    _pkg.__path__ = [str(_repo_root)]
    _pkg.__file__ = str(_repo_root / "__init__.py")
    sys.modules["surakshaedge"] = _pkg

# Ensure repository root and its parent are on sys.path
for _p in [str(_repo_root), str(_repo_root.parent)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Default test environment variables
os.environ.setdefault("SURAKSHA_TEST_MODE", "1")
os.environ.setdefault("SURAKSHA_API_TOKEN", "demo-token")
os.environ.setdefault("SURAKSHA_DB", ":memory:")
