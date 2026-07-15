from app.core.sites import _is_client_safe_cta, _ensure_client_safe_cta


def test_allowed_verbs_pass():
    assert _is_client_safe_cta("Book a call") is True
    assert _is_client_safe_cta("Schedule a demo") is True
    assert _is_client_safe_cta("Contact us") is True


def test_blocked_phrases_fail():
    assert _is_client_safe_cta("Review the preview") is False
    assert _is_client_safe_cta("See source notes") is False


def test_case_insensitive_matching():
    assert _is_client_safe_cta("book a Call") is True
    assert _is_client_safe_cta("REview the Preview") is False


def test_ensure_replaces_blocked_phrase():
    replaced = _ensure_client_safe_cta("Review the preview")
    assert replaced != "Review the preview"
    assert replaced in ("Explore the preview", "Learn more", "Get")
