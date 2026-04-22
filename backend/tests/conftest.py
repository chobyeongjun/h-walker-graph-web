"""Configure sys.path so tests can import from backend/ directly."""
import sys
import os

# Add backend root (so `from services.x import y` works)
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

# Add graph_app root (so `from backend.x import y` works in routers)
_graph_app_root = os.path.abspath(os.path.join(_backend_root, ".."))
if _graph_app_root not in sys.path:
    sys.path.insert(0, _graph_app_root)
