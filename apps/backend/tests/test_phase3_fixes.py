"""
Test Phase 3 fixes: Friendly URL Slugs

Note: Quality score tests are implicitly covered by existing integration tests
(test_crawl_and_readiness.py, test_diversity_and_screenshot.py)
"""

from app.core.sites import _generate_friendly_slug


class TestPhase3FriendlySlugs:
    """Test friendly URL slug generation."""

    def test_basic_slug_generation(self):
        """Basic company name to slug conversion."""
        slug = _generate_friendly_slug("Stripe", set())
        assert slug == "stripe"

    def test_slug_with_spaces(self):
        """Company name with spaces."""
        slug = _generate_friendly_slug("Acme Corporation", set())
        assert slug == "acmecorp"

    def test_slug_with_special_chars(self):
        """Company name with special characters."""
        slug = _generate_friendly_slug("Acme, Inc.", set())
        assert slug == "acmeinc"

    def test_slug_truncation(self):
        """Long company name truncated to 8 chars."""
        slug = _generate_friendly_slug("Microsoft Corporation", set())
        assert len(slug) <= 8
        assert slug == "microsof"

    def test_slug_collision_handling(self):
        """Duplicate slug gets numeric suffix."""
        existing = {"stripe"}
        slug = _generate_friendly_slug("Stripe", existing)
        assert slug == "stripe2"

    def test_slug_multiple_collisions(self):
        """Multiple collisions increment suffix."""
        existing = {"stripe", "stripe2", "stripe3"}
        slug = _generate_friendly_slug("Stripe", existing)
        assert slug == "stripe4"

    def test_slug_empty_company_name(self):
        """Empty company name falls back to 'site'."""
        slug = _generate_friendly_slug("", set())
        assert slug == "site"

    def test_slug_all_special_chars(self):
        """Company name with only special characters."""
        slug = _generate_friendly_slug("!!!", set())
        assert slug == "site"  # Falls back to 'site'
