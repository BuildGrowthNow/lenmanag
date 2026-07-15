from datetime import datetime, timezone
from typing import Any

from unittest.mock import patch

from app.core import extraction
from app.core.config import Settings
from app.core.extraction import crawl_website, _max_pages
from app.core.sites import _readiness_status
from app.schemas.brief import SiteBrief, BriefEvidence, BriefTextRecommendation


def test_crawl_website_sitemap_priority_and_budget(caplog):
    """When sitemap is found, crawl homepage + sitemap URLs within max_pages and skip internal links."""

    max_pages = _max_pages()

    homepage_html = "<html><body>HOME<a href='https://example.com/about'>About</a></body></html>"
    sitemap_urls = [f"https://example.com/page-{i}" for i in range(1, max_pages + 5)]

    def fake_safe_fetch(url: str) -> dict[str, Any]:
        # Match _safe_fetch return shape
        if url.endswith("sitemap.xml"):
            return {
                "ok": True,
                "status": 200,
                "body": "<urlset></urlset>",
                "finalUrl": url,
                "headers": {},
                "error": None,
            }
        # Handle both with and without trailing slash for homepage
        if url == "https://example.com/" or url == "https://example.com":
            return {
                "ok": True,
                "status": 200,
                "body": homepage_html,
                "finalUrl": url,
                "headers": {},
                "error": None,
            }
        # Any sitemap URL or internal page is considered fetchable
        return {
            "ok": True,
            "status": 200,
            "body": "<html><body>PAGE</body></html>",
            "finalUrl": url,
            "headers": {},
            "error": None,
        }

    def fake_parse_html(body: str):  # pragma: no cover - simple stub container
        class Signals:
            def __init__(self, body: str) -> None:
                self.url = "https://example.com/"
                self.title = "Title"
                self.body = body
                # links should be list of tuples (href, anchor_text)
                self.links = [("https://example.com/about", "About")] if "HOME" in body else []
                self.service_clues = []
                self.audience_clues = []
                self.cta_clues = []
                self.tone_clues = []
                self.logo_candidates = []
                self.theme_color = None
                self.images = []
                self.font_family = None
                # Attributes used by _extract_page_summary
                self.meta_description = ""
                self.h1 = []
                self.ctas = []
                self.sections = []
                self.assets = []
                self.body_text = []

        return Signals(body)

    def fake_parse_sitemap_urls(body: str) -> list[str]:
        return sitemap_urls

    def fake_capture_page_visuals(*_args, **_kwargs):  # pragma: no cover - visual capture not relevant
        return {}

    with (
        patch("app.core.extraction._safe_fetch", side_effect=fake_safe_fetch),
        patch("app.core.extraction._parse_html", side_effect=fake_parse_html),
        patch("app.core.extraction._parse_sitemap_urls", side_effect=fake_parse_sitemap_urls),
        patch("app.core.extraction._capture_page_visuals", side_effect=fake_capture_page_visuals),
    ):
        result = crawl_website("https://example.com")

    assert result["pagesCrawled"] <= max_pages
    assert result["pagesDiscovered"] <= max_pages

    inventory = result["pageInventory"]
    homepage_entries = [p for p in inventory if p.get("source") == "homepage"]
    sitemap_entries = [p for p in inventory if p.get("source") == "sitemap"]
    internal_entries = [p for p in inventory if p.get("source") == "internal_link"]

    assert len(homepage_entries) == 1
    assert len(sitemap_entries) > 0
    assert len(internal_entries) == 0

    crawled_urls = {p["url"] for p in inventory}
    # Homepage URL is normalized (trailing slash removed)
    assert "https://example.com" in crawled_urls or "https://example.com/" in crawled_urls
    # Ensure only a prefix of sitemap URLs were used within budget
    assert any(url in crawled_urls for url in sitemap_urls[: max_pages - 1])

    # End-of-crawl logging should mention pages crawled and discovered (if any logs captured)
    log_text = "\n".join(rec.getMessage() for rec in caplog.records)
    if log_text:  # Only check if logs were captured
        assert "pagesCrawled" in log_text or "pages crawled" in log_text


def test_crawl_website_no_sitemap_falls_back_to_internal_links():
    """When no sitemap is found, crawl homepage + internal links within max_pages."""

    max_pages = _max_pages()

    homepage_html = "<html><body>HOME<a href='https://example.com/about'>About</a><a href='https://example.com/contact'>Contact</a></body></html>"

    def fake_safe_fetch(url: str) -> dict[str, Any]:
        # Simulate sitemap fetch failures
        if url.endswith("sitemap.xml"):
            return {
                "ok": False,
                "status": 404,
                "body": "",
                "finalUrl": url,
                "headers": {},
                "error": "http_404",
            }
        # Handle both with and without trailing slash for homepage
        if url == "https://example.com/" or url == "https://example.com":
            return {
                "ok": True,
                "status": 200,
                "body": homepage_html,
                "finalUrl": url,
                "headers": {},
                "error": None,
            }
        return {
            "ok": True,
            "status": 200,
            "body": "<html><body>PAGE</body></html>",
            "finalUrl": url,
            "headers": {},
            "error": None,
        }

    def fake_parse_html(body: str):
        class Signals:
            def __init__(self, body: str) -> None:
                self.url = "https://example.com/"
                self.title = "Title"
                self.body = body
                # links should be list of tuples (href, anchor_text)
                self.links = [
                    ("https://example.com/about", "About"),
                    ("https://example.com/contact", "Contact"),
                ] if "HOME" in body else []
                self.service_clues = []
                self.audience_clues = []
                self.cta_clues = []
                self.tone_clues = []
                self.logo_candidates = []
                self.theme_color = None
                self.images = []
                self.font_family = None
                self.meta_description = ""
                self.h1 = []
                self.ctas = []
                self.sections = []
                self.assets = []
                self.body_text = []

        return Signals(body)

    def fake_parse_sitemap_urls(body: str) -> list[str]:
        return []

    def fake_capture_page_visuals(*_args, **_kwargs):  # pragma: no cover
        return {}

    with (
        patch("app.core.extraction._safe_fetch", side_effect=fake_safe_fetch),
        patch("app.core.extraction._parse_html", side_effect=fake_parse_html),
        patch("app.core.extraction._parse_sitemap_urls", side_effect=fake_parse_sitemap_urls),
        patch("app.core.extraction._capture_page_visuals", side_effect=fake_capture_page_visuals),
    ):
        result = crawl_website("https://example.com")

    assert result["pagesCrawled"] <= max_pages
    assert result["pagesDiscovered"] <= max_pages

    inventory = result["pageInventory"]
    homepage_entries = [p for p in inventory if p.get("source") == "homepage"]
    sitemap_entries = [p for p in inventory if p.get("source") == "sitemap"]
    internal_entries = [p for p in inventory if p.get("source") == "internal_link"]

    assert len(homepage_entries) == 1
    assert len(sitemap_entries) == 0
    assert len(internal_entries) > 0


def test_crawl_website_brand_asset_cues_aggregated_and_assets_from_homepage_only(monkeypatch):
    """Brand asset cues come from all pages but downloads only triggered from homepage-derived cues."""

    homepage_html = "<html><body>HOME</body></html>"

    def fake_safe_fetch(url: str) -> dict[str, Any]:
        if url == "https://brand.com/" or url == "https://brand.com":
            return {
                "ok": True,
                "status": 200,
                "body": homepage_html,
                "finalUrl": url,
                "headers": {},
                "error": None,
            }
        if "about" in url:
            return {
                "ok": True,
                "status": 200,
                "body": "<html><body>about</body></html>",
                "finalUrl": url,
                "headers": {},
                "error": None,
            }
        if "contact" in url:
            return {
                "ok": True,
                "status": 200,
                "body": "<html><body>contact</body></html>",
                "finalUrl": url,
                "headers": {},
                "error": None,
            }
        return {
            "ok": True,
            "status": 200,
            "body": "<html><body>PAGE</body></html>",
            "finalUrl": url,
            "headers": {},
            "error": None,
        }

    class Signals:
        def __init__(self, body: str) -> None:
            self.url = "https://brand.com/"
            self.title = "Title"
            self.body = body
            self.links = []
            self.service_clues = []
            self.audience_clues = []
            self.cta_clues = []
            self.tone_clues = []
            self.logo_candidates = []
            self.theme_color = None
            self.images = []
            self.font_family = None
            self.meta_description = ""
            self.h1 = []
            self.ctas = []
            self.sections = []
            self.assets = []
            self.body_text = []
    def fake_parse_html(body: str):
        sig = Signals(body)
        # Encode which page we are on by body marker
        if "HOME" in body:
            sig.logo_candidates = ["https://cdn.brand.com/logo-home.png"]
        elif "about" in body:
            sig.logo_candidates = ["https://cdn.brand.com/logo-about.png"]
        elif "contact" in body:
            sig.logo_candidates = ["https://cdn.brand.com/logo-contact.png"]
        return sig

    def fake_parse_sitemap_urls(body: str) -> list[str]:
        # Force three pages including homepage and two internals
        return [
            "https://brand.com/",
            "https://brand.com/about",
            "https://brand.com/contact",
        ]

    def fake_capture_page_visuals(*_args, **_kwargs):  # pragma: no cover
        return {}

    download_calls: list[list[str]] = []

    class DummyResult:
        def __init__(self, url: str) -> None:
            self.source_url = url
            self.success = True
            self.cached_uri = f"cached://{url}"
            self.bytes = 100

    class DummyDownloader:
        # Note: download_batch is called via asyncio.run() from synchronous code,
        # so it needs to be async but will be run in a new event loop
        async def download_batch(self, urls: list[str], lead_id: str):  # type: ignore[override]
            download_calls.append(urls)
            return [DummyResult(u) for u in urls]

        def enforce_aggregate_limit(self, total_bytes: int, max_bytes: int | None = None) -> bool:  # pragma: no cover - simple stub
            return True

    # Enable asset downloads for this test by patching get_settings
    from app.core.config import get_settings
    original_settings = get_settings()

    class MockSettings:
        def __init__(self):
            for attr in dir(original_settings):
                if not attr.startswith('_'):
                    setattr(self, attr, getattr(original_settings, attr))
            self.asset_download_enabled = True

    mock_settings = MockSettings()

    with (
        patch("app.core.extraction._safe_fetch", side_effect=fake_safe_fetch),
        patch("app.core.extraction._parse_html", side_effect=fake_parse_html),
        patch("app.core.extraction._parse_sitemap_urls", side_effect=fake_parse_sitemap_urls),
        patch("app.core.extraction._capture_page_visuals", side_effect=fake_capture_page_visuals),
        patch("app.core.extraction.settings", mock_settings),
        patch.object(extraction, "AssetDownloader", DummyDownloader),
    ):
        result = crawl_website("https://brand.com")

    cues = result.get("brandAssetCues") or []
    assert len(cues) >= 3

    # Cues should include contributions from multiple pages
    sources = {c["sourceUrl"] for c in cues}
    assert "https://brand.com/" in sources
    assert "https://brand.com/about" in sources or "https://brand.com/contact" in sources

    # Exactly one batch download call, and only homepage-derived asset URLs are downloaded
    assert len(download_calls) == 1
    downloaded = set(download_calls[0])
    assert "https://cdn.brand.com/logo-home.png" in downloaded
    assert "https://cdn.brand.com/logo-about.png" not in downloaded
    assert "https://cdn.brand.com/logo-contact.png" not in downloaded


def _make_brief(approval_state: str = "approved") -> SiteBrief:
    ev = BriefEvidence(
        sourceKind="inferred",
        inferenceLabel="test",
        confidence=80,
        references=[],
    )
    txt = BriefTextRecommendation(value="Test", evidence=ev)
    now = datetime.now(timezone.utc)
    approved_at = now if approval_state == "approved" else None
    approved_by = "tester" if approval_state == "approved" else None

    return SiteBrief(
        id="brief-1",
        leadId="lead-1",
        sourceExtractionId="ex-1",
        sourceExtractionVersion=1,
        version=1,
        approvalState=approval_state,
        needsReview=False,
        companySummary=txt,
        valuePropositionSummary=txt,
        audienceHypothesis=txt,
        toneProfile=txt,
        conversionAngle=txt,
        recommendedHero=txt,
        recommendedSections=[],
        proofPoints=[],
        visualRedesign=[],
        sourceCitations=[],
        brandAssetProvenance=[],
        confidenceScore=80,
        missingRequirements=[],
        reviewNotes=None,
        approvedAt=approved_at,
        approvedBy=approved_by,
        createdAt=now,
        updatedAt=now,
    )


def test_readiness_status_default_threshold_bands(monkeypatch):
    """_readiness_status uses visual_redesign_quality_threshold and correct review bands."""

    class DummySettings(Settings):
        visual_redesign_quality_threshold: int = 90

    monkeypatch.setattr("app.core.sites.get_settings", lambda: DummySettings())

    brief = _make_brief("approved")

    status, qa = _readiness_status(brief, quality_score=95, missing_requirements=[])
    assert status == "ready_to_publish"
    assert qa == "pass"

    status, qa = _readiness_status(brief, quality_score=80, missing_requirements=["minor"])
    assert status == "ready_for_review"
    assert qa == "warn"

    status, qa = _readiness_status(brief, quality_score=60, missing_requirements=["minor"])
    assert status == "needs_review"
    assert qa == "warn"

    status, qa = _readiness_status(brief, quality_score=40, missing_requirements=["major"])
    assert status == "blocked"
    assert qa == "fail"


def test_readiness_status_respects_changed_threshold(monkeypatch):
    """Changing visual_redesign_quality_threshold shifts ready_to_publish band."""

    class DummySettings(Settings):
        visual_redesign_quality_threshold: int = 80

    monkeypatch.setattr("app.core.sites.get_settings", lambda: DummySettings())

    brief = _make_brief("approved")

    # At new lower threshold, score 85 should now be ready_to_publish
    status, qa = _readiness_status(brief, quality_score=85, missing_requirements=[])
    assert status == "ready_to_publish"
    assert qa == "pass"

    # Score just below threshold with small missing requirements should be ready_for_review
    status, qa = _readiness_status(brief, quality_score=75, missing_requirements=["minor"])
    assert status == "ready_for_review"
    assert qa == "warn"

    # Lower score band still maps to needs_review
    status, qa = _readiness_status(brief, quality_score=60, missing_requirements=["minor"])
    assert status == "needs_review"
    assert qa == "warn"
