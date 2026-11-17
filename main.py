"""
Deployment entry point for SurakshaEdge.
Ensures the 'surakshaedge' package is registered in sys.modules
regardless of the directory name (e.g. on Render, Railway, Docker, or local).

Usage: uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import importlib.util
import os
import sys

_app_root = os.path.dirname(os.path.abspath(__file__))

# Ensure app root is at the head of sys.path
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

# If 'surakshaedge' is not already in sys.modules, register this directory as 'surakshaedge'
if "surakshaedge" not in sys.modules:
    try:
        import surakshaedge  # noqa: F401
    except ModuleNotFoundError:
        _init_file = os.path.join(_app_root, "__init__.py")
        if os.path.exists(_init_file):
            _spec = importlib.util.spec_from_file_location(
                "surakshaedge",
                _init_file,
                submodule_search_locations=[_app_root],
            )
            if _spec and _spec.loader:
                _mod = importlib.util.module_from_spec(_spec)
                sys.modules["surakshaedge"] = _mod
                _spec.loader.exec_module(_mod)

# Now both `from api.main import app` and `from surakshaedge.api.main import app` work
try:
    from api.main import app  # noqa: E402, F401
except ModuleNotFoundError:
    from surakshaedge.api.main import app  # noqa: E402, F401
