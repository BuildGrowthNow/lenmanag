import os
import sys
import json
from pathlib import Path

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "1")
# Tests must never inherit a developer's or CI runner's real MongoDB URI from
# .env. Set both switches before any application module is imported.
os.environ["MONGO_USE_MOCK"] = "true"
os.environ["MONGODB_URI"] = ""
# Do not let a developer's provider override make unit tests construct a
# network-backed client. The repository's normal local provider is Bedrock;
# individual LLM tests patch their client explicitly.
os.environ["LLM_PROVIDER"] = "bedrock"

# Ensure the backend package root is importable when tests run from IDEs or CI.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))


class _DeterministicTestLLM:
    """Keep repository tests offline and independent of provider credentials."""

    async def generate_text(self, *_args, **_kwargs) -> str:
        return "{}"

    def extract_json_from_response(self, response: str) -> dict:
        return json.loads(response)


# Master-brief tests exercise persistence and approval rules, not a live model.
# Patch the imported provider reference after the environment is isolated.
from app.core import master_brief as _master_brief  # noqa: E402

_master_brief.get_llm_client = lambda: _DeterministicTestLLM()
