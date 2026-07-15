import os
import sys
from pathlib import Path

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "1")

# Ensure the backend package root is importable when tests run from IDEs or CI.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
