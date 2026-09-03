from app.core.semantic_validation import sanitize_unsupported_proof, validate_semantics
from app.core.generation_contracts import generation_preflight
from app.core.interaction_qa import normalize_interaction_manifest, state_changed
from app.api.internal import CompileRequest


def test_unsupported_proof_is_removed_as_a_complete_section() -> None:
    html = """
    <nav><a href="#testimonials">Reviews</a></nav>
    <main><section id="testimonials" class="testimonial-grid"><h2>What clients say</h2><p>Ridgewood homeowner</p></section></main>
    """
    cleaned = sanitize_unsupported_proof(html)
    assert "Ridgewood" not in cleaned
    assert "testimonials" not in cleaned
    assert "Reviews" not in cleaned


def test_semantic_gate_reports_exact_rule_and_selector() -> None:
    result = validate_semantics(
        "<main><section class='hero'></section></main>",
        require_footer=True,
        require_media=True,
    )
    assert not result.valid
    assert result.issues[0].rule_id == "footer.required"
    assert result.issues[0].selector == "footer"


def test_semantic_gate_accepts_evidence_backed_media_and_proof() -> None:
    html = """
    <main><section><img src="https://assets.test/project.jpg" alt="Kitchen project"></section></main>
    <footer><p>© Company 2026</p></footer>
    <section class="proof" data-evidence-id="proof-1"><blockquote>Reliable local service</blockquote></section>
    """
    result = validate_semantics(
        html,
        require_footer=True,
        require_media=True,
        approved_images={"https://assets.test/project.jpg"},
        approved_proof=["Reliable local service"],
        approved_evidence_ids={"proof-1"},
    )
    assert result.valid


def test_interaction_manifest_is_strict_and_observable() -> None:
    manifest = normalize_interaction_manifest(
        [
            {"id": "menu", "selector": "#menu", "action": "click"},
            {
                "selector": "#search",
                "action": "press",
                "key": "Enter",
                "required": False,
            },
            {"selector": "#bad", "action": "hover"},
            "ignored",
        ]
    )
    assert [item["action"] for item in manifest] == ["click", "press"]
    assert state_changed({"expanded": "false"}, {"expanded": "true"})
    assert not state_changed({"text": "same"}, {"text": "same"})


def test_internal_compiler_contract_accepts_js_only_entries() -> None:
    request = CompileRequest(
        componentName="RuntimeEntry",
        siteId="site-1",
        jsEntry="console.log('runtime');",
        capabilityManifest={"dependencies": []},
    )
    assert request.sourceCode == ""
    assert request.jsEntry == "console.log('runtime');"


def test_image_led_preflight_blocks_before_provider_when_cached_media_is_missing() -> None:
    brief = type("Brief", (), {"heroMode": "image_led", "missingRequirements": [], "brandAssets": type("Assets", (), {"imageInventory": [{"sourceUrl": "http://source.test/work.jpg"}], "imageUrls": []})()})()
    result = generation_preflight(brief, asset_download_enabled=False)
    assert not result.allowed
    assert {block.rule_id for block in result.blocks} == {"assets.downloader_disabled", "hero.approved_media_required"}


def test_enabled_downloader_uses_only_cached_approved_https_media() -> None:
    brief = type("Brief", (), {"heroMode": "image_led", "missingRequirements": [], "brandAssets": type("Assets", (), {"imageInventory": [{"sourceUrl": "http://source.test/logo.svg", "url": "https://cache.test/logo.svg", "approved": True}], "imageUrls": ["https://cache.test/project.jpg"]})()})()
    result = generation_preflight(brief, asset_download_enabled=True)
    assert result.allowed
    assert result.approved_assets == ["https://cache.test/logo.svg", "https://cache.test/project.jpg"]


def test_typography_only_contract_rejects_fake_media_shell() -> None:
    result = validate_semantics("<main><section class='hero-media' data-media-required></section></main><footer>Footer</footer>", require_footer=True, hero_mode="typography_only")
    assert any(issue.rule_id == "hero.typography_only_no_media_shell" for issue in result.issues)


def test_proof_bearing_markup_requires_exact_evidence_id() -> None:
    result = validate_semantics("<main><section class='review' data-evidence-id='wrong'>5 stars</section></main>", approved_evidence_ids={"right"})
    assert any(issue.rule_id == "proof.evidence_required" for issue in result.issues)
