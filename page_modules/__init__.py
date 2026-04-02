import sys
from pathlib import Path

# Ensure the project root (parent of this package) is on sys.path so that
# ui_helpers, persistence, analytics, credentials, etc. are importable from
# every page module without needing relative imports.
_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
