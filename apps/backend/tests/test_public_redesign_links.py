from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import Request

from app.api import public


class _FakeLeadsCollection:
    def __init__(self, document: dict):
        self.document = document
        self.query: dict | None = None

    async def find_one(self, query: dict) -> dict:
        self.query = query
        return self.document


class _FakeDatabase:
    def __init__(self, document: dict):
        self.leads = _FakeLeadsCollection(document)

    def __getitem__(self, name: str) -> _FakeLeadsCollection:
        assert name == "leads"
        return self.leads


@pytest.mark.asyncio
async def test_redesign_page_resolves_legacy_client_share_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _FakeDatabase(
        {
            "id": "lead-1",
            "companyName": "Kordzadze Law Office",
            "contactName": None,
            "redesignSlug": None,
            "clientShare": {
                "slug": "kordzadz-af07",
                "selectedSiteIds": ["site-1"],
            },
        }
    )
    site = SimpleNamespace(
        id="site-1",
        variantPosition=1,
        createdAt=datetime.now(timezone.utc),
        variantType="html_v1",
        variantTitle=None,
        variantDescription=None,
        variantLabel="Website option",
        readinessStatus="ready_for_review",
        qaStatus="warn",
        screenshotRefs=[],
        previewUrl="https://sites.lenquant.com/st/site-1",
        previewSlug="site-1",
        staticHtml="<html></html>",
        compilationStatus="success",
    )

    monkeypatch.setattr(public, "get_database", lambda: database)
    monkeypatch.setattr(public.site_repository, "list_sites_by_lead", lambda *args, **kwargs: _one(site))
    monkeypatch.setattr(public.lead_repository, "get_master_brief", lambda *args, **kwargs: _none())
    monkeypatch.setattr(public, "_publicly_eligible", lambda _site: True)

    request = Request(
        scope={"type": "http", "method": "GET", "path": "/public/redesign/kordzadz-af07"}
    )
    response = await public.get_redesign_page("kordzadz-af07` ", request)

    assert response.data is not None
    assert response.data.leadId == "lead-1"
    assert [variant.siteId for variant in response.data.variants] == ["site-1"]
    assert database.leads.query == {
        "$or": [
            {"redesignSlug": "kordzadz-af07"},
            {"clientShare.slug": "kordzadz-af07"},
        ]
    }


async def _one(site: SimpleNamespace) -> list[SimpleNamespace]:
    return [site]


async def _none() -> None:
    return None
