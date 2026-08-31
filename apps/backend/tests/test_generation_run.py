from app.core.generation_run import generation_input_hash, supersede_reason


def test_generation_input_hash_is_canonical_and_order_independent():
    left = {"generationTypes": ["html_v1", "nextjs"], "brand": {"primary": "#123"}}
    right = {"brand": {"primary": "#123"}, "generationTypes": ["html_v1", "nextjs"]}
    assert generation_input_hash(left) == generation_input_hash(right)
    assert generation_input_hash(left) != generation_input_hash({**left, "brand": {"primary": "#456"}})


def test_supersede_reason_identifies_pinned_input_change():
    old = {"snapshot": {"briefVersion": 3, "extractionVersion": 2, "brandSnapshotHash": "a", "generationTypes": ["nextjs"]}}
    new = {"snapshot": {"briefVersion": 4, "extractionVersion": 2, "brandSnapshotHash": "a", "generationTypes": ["nextjs"]}}
    assert supersede_reason(old, new) == "brief_version_changed"
