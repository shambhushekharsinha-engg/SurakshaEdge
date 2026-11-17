"""
Deployment entry point for SurakshaEdge.
When the repo root IS the surakshaedge package directory,
we add the parent directory to sys.path so the package
can be imported as `surakshaedge.*`.

Usage: uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import sys
import os

# The parent of the app root IS the package parent
# /app/ contains surakshaedge/__init__.py  -> parent is /
_app_root = os.path.dirname(os.path.abspath(__file__))
_pkg_parent = os.path.dirname(_app_root)
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)
# Also add current dir (app root) for configs, models, dashboard
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from surakshaedge.api.main import app  # noqa: E402, F401
