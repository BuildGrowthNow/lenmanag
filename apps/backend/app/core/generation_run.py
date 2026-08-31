from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def generation_input_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def brand_snapshot_hash(brand_assets: dict[str, Any]) -> str:
    return generation_input_hash(brand_assets)


def supersede_reason(old: dict[str, Any], new: dict[str, Any]) -> str:
    old_snapshot = old.get("snapshot") or {}
    new_snapshot = new.get("snapshot") or {}
    checks = (
        ("briefVersion", "brief_version_changed"),
        ("extractionVersion", "extraction_version_changed"),
        ("brandSnapshotHash", "brand_assets_changed"),
        ("generationTypes", "variant_selection_changed"),
        ("operatorInstructions", "operator_instructions_changed"),
    )
    for key, reason in checks:
        if old_snapshot.get(key) != new_snapshot.get(key):
            return reason
    return "generation_inputs_changed"
