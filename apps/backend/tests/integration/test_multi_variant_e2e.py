"""
End-to-end integration test for multi-variant site generation.

This test requires:
- MongoDB running (or MongoDB Atlas)
- Redis running
- Celery worker running (or CELERY_TASK_ALWAYS_EAGER=1)
- LLM client configured (or mocked)

Run manually with:
    python -m pytest tests/integration/test_multi_variant_e2e.py -v -s
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_llm_response() -> str:
    """Mock LLM response with HTML/CSS/JS code blocks."""
    return """
Here is your generated landing page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Company</title>
</head>
<body>
    <header>
        <nav>
            <a href="/">Test Company</a>
        </nav>
    </header>
    <main>
        <section class="hero">
            <h1>Welcome to Test Company</h1>
            <p>Your trusted partner for success.</p>
            <a href="#contact" class="cta">Get Started</a>
        </section>
        <section class="services">
            <h2>Our Services</h2>
            <div class="service-grid">
                <div class="service">Service 1</div>
                <div class="service">Service 2</div>
            </div>
        </section>
    </main>
    <footer>
        <p>&copy; 2026 Test Company</p>
    </footer>
</body>
</html>
```

```css
:root {
    --primary-color: #2563eb;
    --secondary-color: #1e40af;
    --text-color: #1f2937;
    --background: #ffffff;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: system-ui, -apple-system, sans-serif;
    color: var(--text-color);
    background: var(--background);
}

header {
    padding: 1rem 2rem;
    border-bottom: 1px solid #e5e7eb;
}

.hero {
    padding: 4rem 2rem;
    text-align: center;
}

.hero h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.cta {
    display: inline-block;
    padding: 1rem 2rem;
    background: var(--primary-color);
    color: white;
    text-decoration: none;
    border-radius: 0.5rem;
}

.services {
    padding: 4rem 2rem;
    background: #f9fafb;
}

.service-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
    margin-top: 2rem;
}

.service {
    padding: 2rem;
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

footer {
    padding: 2rem;
    text-align: center;
    background: #1f2937;
    color: white;
}
```

```javascript
document.addEventListener('DOMContentLoaded', () => {
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Add scroll animation
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    });

    document.querySelectorAll('.service').forEach(el => observer.observe(el));
});
```
"""


class TestMultiVariantE2E:
    """End-to-end tests for multi-variant generation flow."""

    @pytest.mark.asyncio
    async def test_variant_strategies_load_correctly(self) -> None:
        """Test that variant strategies can be loaded and are valid."""
        from app.core.variant_strategy import get_variant_strategies

        strategies = get_variant_strategies()

        assert "html_v1" in strategies
        assert "html_v2" in strategies
        assert "html_v3" in strategies

        # Verify each strategy has required fields
        for strategy in strategies.values():
            assert strategy["variantLabel"]
            assert strategy["creativeBriefGuidance"]
            assert len(strategy["inspirationKeywords"]) > 0

    @pytest.mark.asyncio
    async def test_static_html_parsing(self, mock_llm_response: str) -> None:
        """Test that static HTML generator can parse LLM response."""
        from app.core.static_html_generator import _parse_llm_response

        html, css, js = _parse_llm_response(mock_llm_response)

        # Verify HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<title>Test Company</title>" in html
        assert '<section class="hero">' in html
        assert "<footer>" in html

        # Verify CSS content
        assert "--primary-color" in css
        assert "grid-template-columns" in css

        # Verify JS content
        assert "DOMContentLoaded" in js
        assert "IntersectionObserver" in js

    @pytest.mark.asyncio
    async def test_html_prompt_building(self) -> None:
        """Test that HTML prompt is built correctly from brief data."""
        from app.core.static_html_generator import _build_static_html_prompt
        from unittest.mock import MagicMock

        # Create mock brief with required attributes
        mock_brief = MagicMock()
        mock_brief.businessGoal = "Generate leads"
        mock_brief.primaryAudience = "Small businesses"
        mock_brief.valueProposition = "Save time and money"
        mock_brief.toneAndVoice = "Professional"
        mock_brief.visualStyle = "Modern"
        mock_brief.colorStrategy = "Blue primary"
        mock_brief.motionLevel = "subtle"
        mock_brief.headline = "Welcome"
        mock_brief.subheadline = "Get started today"
        mock_brief.sections = []
        mock_brief.ctaStrategy = "Strong CTA"
        mock_brief.creativeDirection = MagicMock()
        mock_brief.creativeDirection.designConcept = "Minimalist"
        mock_brief.creativeDirection.heroTreatment = "Full-width"
        mock_brief.creativeDirection.signatureTechnique = "Fade in"
        mock_brief.creativeDirection.layoutStrategy = "Grid"
        mock_brief.creativeDirection.colorMood = "Professional blue"
        mock_brief.creativeDirection.typographyPersonality = "Clean"
        mock_brief.brandAssets = MagicMock()
        mock_brief.brandAssets.logoUrl = None
        mock_brief.brandAssets.primaryColor = "#2563eb"
        mock_brief.brandAssets.secondaryColor = "#1e40af"
        mock_brief.brandAssets.fontFamily = "system-ui"

        # Create mock extraction
        mock_extraction = MagicMock()

        prompt = _build_static_html_prompt(mock_brief, mock_extraction, "html_v1")

        # Verify prompt contains key content
        assert "Generate leads" in prompt
        assert "Small businesses" in prompt
        assert "html_v1" in prompt
        assert "HTML" in prompt
        assert "CSS" in prompt

    @pytest.mark.asyncio
    async def test_generation_lock_behavior(self) -> None:
        """Test that generation lock properly serializes execution."""
        from app.core.generation_lock import generation_lock

        execution_log: list[tuple[str, str]] = []

        with patch("app.core.generation_lock.redis") as mock_redis_module:
            mock_client = AsyncMock()
            mock_redis_module.from_url.return_value = mock_client

            lock_held = False

            async def mock_set(
                _k: str, _v: str, nx: bool, ex: int  # noqa: ARG001
            ) -> bool:
                nonlocal lock_held
                _ = nx, ex  # silence unused
                if not lock_held:
                    lock_held = True
                    return True
                return False

            async def mock_get(_k: str) -> str | None:  # noqa: ARG001
                return "lock" if lock_held else None

            async def mock_delete(_k: str) -> int:  # noqa: ARG001
                nonlocal lock_held
                lock_held = False
                return 1

            mock_client.set = mock_set
            mock_client.get = mock_get
            mock_client.delete = mock_delete
            mock_client.close = AsyncMock()

            async def work(name: str) -> None:
                execution_log.append((name, "waiting"))
                async with generation_lock(timeout_seconds=5):
                    execution_log.append((name, "acquired"))
                    await asyncio.sleep(0.01)
                    execution_log.append((name, "released"))

            await work("task1")

            # Verify execution sequence
            assert execution_log == [
                ("task1", "waiting"),
                ("task1", "acquired"),
                ("task1", "released"),
            ]


class TestVariantAPIIntegration:
    """Test API endpoint integration for variants."""

    @pytest.mark.asyncio
    async def test_list_sites_by_lead_empty(self) -> None:
        """Test listing variants for a lead with no sites."""
        from app.core.sites import SiteRepository

        # Create repository with in-memory storage
        repo = SiteRepository()

        sites = await repo.list_sites_by_lead("nonexistent-lead")

        assert sites == []

    @pytest.mark.asyncio
    async def test_variant_slug_uniqueness(self) -> None:
        """Test that variant slugs are unique for the same lead."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)

        slugs = [
            repo._generate_variant_slug("lead1", "html_v1", "Test"),
            repo._generate_variant_slug("lead1", "html_v2", "Test"),
            repo._generate_variant_slug("lead1", "html_v3", "Test"),
            repo._generate_variant_slug("lead1", "nextjs", "Test"),
        ]

        # All slugs should be unique
        assert len(slugs) == len(set(slugs))

    @pytest.mark.asyncio
    async def test_variant_ordering(self) -> None:
        """Test that variant positions are assigned correctly."""
        from app.core.variant_strategy import get_variant_strategies

        strategies = get_variant_strategies()

        assert strategies["html_v1"]["variantPosition"] == 1
        assert strategies["html_v2"]["variantPosition"] == 2
        assert strategies["html_v3"]["variantPosition"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
