from __future__ import annotations

import pytest
from uuid import uuid4

from app.core.leads import lead_repository
from app.core.mongo import get_database


@pytest.mark.asyncio
async def test_permanent_delete_removes_all_lead_owned_records(monkeypatch: pytest.MonkeyPatch) -> None:
    token = uuid4().hex
    lead_id = f"permanent-delete-lead-{token}"
    other_lead_id = f"keep-this-lead-{token}"
    job_id = f"permanent-delete-job-{token}"
    database = get_database()

    revoked: list[tuple[str, bool]] = []
    from app.core.celery_app import celery_app

    monkeypatch.setattr(
        celery_app.control,
        "revoke",
        lambda task_id, terminate=False: revoked.append((task_id, terminate)),
    )

    await database["leads"].insert_many([
        {"id": lead_id, "user_id": "owner"},
        {"id": other_lead_id, "user_id": "owner"},
    ])
    await database["jobs"].insert_many([
        {"id": job_id, "leadId": lead_id, "leadIds": [lead_id]},
        {"id": f"legacy-{job_id}", "leadIds": [lead_id]},
        {"id": "other-job", "leadId": other_lead_id, "leadIds": [other_lead_id]},
    ])
    for collection in (
        "site_extractions", "site_briefs", "master_briefs", "generated_sites",
        "generation_runs", "generation_input_claims", "message_drafts",
        "analytics_events", "asset_metadata",
    ):
        documents = [
            {"id": f"deleted-{collection}-{token}", "leadId": lead_id},
            {"id": f"retained-{collection}-{token}", "leadId": other_lead_id},
        ]
        await database[collection].insert_many(documents)
    await database["task_checkpoints"].insert_many([
        {"taskId": job_id}, {"taskId": f"legacy-{job_id}"}, {"taskId": "other-job"},
    ])
    await database["audit_logs"].insert_many([
        {"entityId": lead_id}, {"metadata": {"leadId": lead_id}}, {"entityId": other_lead_id},
    ])

    assert await lead_repository.permanently_delete_lead(lead_id, user_id="owner")
    assert revoked == [(job_id, True), (f"legacy-{job_id}", True)]
    assert await database["leads"].find_one({"id": lead_id}) is None
    assert await database["jobs"].find_one({"id": job_id}) is None
    assert await database["jobs"].find_one({"id": f"legacy-{job_id}"}) is None
    assert await database["task_checkpoints"].find_one({"taskId": job_id}) is None
    assert await database["task_checkpoints"].find_one({"taskId": f"legacy-{job_id}"}) is None
    assert await database["leads"].find_one({"id": other_lead_id}) is not None
    assert await database["jobs"].find_one({"id": "other-job"}) is not None
    assert await database["task_checkpoints"].find_one({"taskId": "other-job"}) is not None
    for collection in (
        "site_extractions", "site_briefs", "master_briefs", "generated_sites",
        "generation_runs", "generation_input_claims", "message_drafts",
        "analytics_events", "asset_metadata",
    ):
        assert await database[collection].count_documents({"leadId": lead_id}) == 0
        assert await database[collection].count_documents({"leadId": other_lead_id}) == 1
    assert await database["audit_logs"].count_documents({"entityId": lead_id}) == 0
    assert await database["audit_logs"].count_documents({"metadata.leadId": lead_id}) == 0

    # Keep a configured local Mongo database free of this test's retained fixture.
    for collection in (
        "leads", "jobs", "site_extractions", "site_briefs", "master_briefs",
        "generated_sites", "generation_runs", "generation_input_claims",
        "message_drafts", "analytics_events", "asset_metadata", "task_checkpoints",
        "audit_logs",
    ):
        await database[collection].delete_many({"$or": [{"leadId": other_lead_id}, {"leadIds": other_lead_id}, {"id": other_lead_id}, {"taskId": "other-job"}, {"entityId": other_lead_id}]})
