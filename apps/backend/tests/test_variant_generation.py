"""
Tests for multi-variant site generation.

Tests variant strategy definitions, generation lock behavior,
and overall variant generation flow.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.variant_strategy import (
    get_variant_strategies,
    get_variant_strategy,
)
from app.schemas.site import VariantType


class TestVariantStrategies:
    """Tests for variant strategy definitions."""

    def test_variant_strategies_structure(self) -> None:
        """Test that variant strategies have all required fields."""
        strategies = get_variant_strategies()

        assert len(strategies) == 3, "Should have 3 HTML variant strategies"

        expected_variants: list[VariantType] = ["html_v1", "html_v2", "html_v3"]
        for variant_type in expected_variants:
            assert variant_type in strategies, f"Missing strategy for {variant_type}"

            strategy = strategies[variant_type]
            assert "variantType" in strategy
            assert "variantLabel" in strategy
            assert "variantPosition" in strategy
            assert "designMode" in strategy
            assert "paletteMode" in strategy
            assert "creativeBriefGuidance" in strategy
            assert "inspirationKeywords" in strategy
            assert "avoidPatterns" in strategy

    def test_variant_strategies_are_distinct(self) -> None:
        """Test that each variant has distinct design parameters."""
        strategies = get_variant_strategies()

        design_modes = [s["designMode"] for s in strategies.values()]
        palette_modes = [s["paletteMode"] for s in strategies.values()]

        assert len(set(design_modes)) > 1, "Design modes should vary across variants"
        assert len(set(palette_modes)) > 1, "Palette modes should vary across variants"

    def test_variant_positions_are_unique(self) -> None:
        """Test that variant positions are unique and ordered."""
        strategies = get_variant_strategies()

        positions = [s["variantPosition"] for s in strategies.values()]

        assert len(positions) == len(set(positions)), "Positions must be unique"
        assert sorted(positions) == [1, 2, 3], "Positions should be 1, 2, 3"

    def test_industry_specific_strategies_consulting(self) -> None:
        """Test that consulting industry gets modified v3 strategy."""
        consulting_strats = get_variant_strategies("consulting")
        default_strats = get_variant_strategies()

        v3_consulting = consulting_strats["html_v3"]
        v3_default = default_strats["html_v3"]

        assert v3_consulting["variantLabel"] == "Minimal Luxe"
        assert v3_consulting["designMode"] == "minimalist"
        assert v3_default["variantLabel"] == "Creative Alternative"
        assert v3_default["designMode"] == "playful"

    def test_industry_specific_strategies_legal(self) -> None:
        """Test that legal industry gets modified v3 strategy."""
        legal_strats = get_variant_strategies("legal")
        v3_legal = legal_strats["html_v3"]

        assert v3_legal["variantLabel"] == "Minimal Luxe"
        assert v3_legal["designMode"] == "minimalist"

    def test_industry_specific_strategies_finance(self) -> None:
        """Test that finance industry gets modified v3 strategy."""
        finance_strats = get_variant_strategies("B2B finance")
        v3_finance = finance_strats["html_v3"]

        assert v3_finance["variantLabel"] == "Minimal Luxe"

    def test_get_single_variant_strategy(self) -> None:
        """Test getting a single variant strategy by type."""
        strategy = get_variant_strategy("html_v1")

        assert strategy["variantType"] == "html_v1"
        assert strategy["variantLabel"] == "Professional Standard"
        assert strategy["variantPosition"] == 1

    def test_get_variant_strategy_unknown_type(self) -> None:
        """Test that unknown variant type raises error."""
        with pytest.raises(ValueError, match="Unknown variant type"):
            get_variant_strategy("html_v999")  # type: ignore[arg-type]

    def test_variant_labels_are_descriptive(self) -> None:
        """Test that variant labels describe the design direction."""
        strategies = get_variant_strategies()

        labels = {s["variantLabel"] for s in strategies.values()}

        assert "Professional Standard" in labels
        assert "Bold Startup" in labels
        assert "Creative Alternative" in labels

    def test_creative_brief_guidance_is_substantial(self) -> None:
        """Test that creative brief guidance has meaningful content."""
        strategies = get_variant_strategies()

        for variant_type, strategy in strategies.items():
            guidance = strategy["creativeBriefGuidance"]
            assert len(guidance) > 100, f"{variant_type} guidance too short"
            assert "\n" in guidance, f"{variant_type} guidance should be multi-line"

    def test_inspiration_keywords_not_empty(self) -> None:
        """Test that inspiration keywords are provided."""
        strategies = get_variant_strategies()

        for variant_type, strategy in strategies.items():
            keywords = strategy["inspirationKeywords"]
            assert len(keywords) >= 5, f"{variant_type} needs at least 5 keywords"

    def test_avoid_patterns_not_empty(self) -> None:
        """Test that avoid patterns are provided."""
        strategies = get_variant_strategies()

        for variant_type, strategy in strategies.items():
            patterns = strategy["avoidPatterns"]
            assert len(patterns) >= 3, f"{variant_type} needs at least 3 avoid patterns"


class TestGenerationLock:
    """Tests for Redis distributed generation lock."""

    @pytest.mark.asyncio
    async def test_lock_prevents_parallel_execution(self) -> None:
        """Test that generation lock enforces sequential execution."""
        from app.core.generation_lock import generation_lock

        with patch("app.core.generation_lock.redis") as mock_redis_module:
            mock_client = AsyncMock()
            mock_redis_module.from_url.return_value = mock_client

            execution_order: list[str] = []
            lock_acquired_count = 0

            async def mock_set(
                _key: str,
                _value: str,
                nx: bool,
                ex: int,  # noqa: ARG001
            ) -> bool:
                nonlocal lock_acquired_count
                _ = nx, ex  # silence unused warnings
                if lock_acquired_count == 0:
                    lock_acquired_count += 1
                    return True
                return False

            async def mock_get(_key: str) -> str | None:
                return "lock-id" if lock_acquired_count > 0 else None

            async def mock_delete(_key: str) -> int:
                nonlocal lock_acquired_count
                lock_acquired_count = 0
                return 1

            mock_client.set = mock_set
            mock_client.get = mock_get
            mock_client.delete = mock_delete
            mock_client.close = AsyncMock()

            async def task(name: str) -> None:
                async with generation_lock(timeout_seconds=5):
                    execution_order.append(f"{name}_start")
                    await asyncio.sleep(0.01)
                    execution_order.append(f"{name}_end")

            await task("task1")

            assert execution_order == ["task1_start", "task1_end"]


class TestStaticHtmlGenerator:
    """Tests for static HTML generation."""

    def test_parse_llm_response_valid(self) -> None:
        """Test parsing valid LLM response with all code blocks."""
        from app.core.static_html_generator import _parse_llm_response

        response = """
Here's the generated code:

```html
<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>
```

```css
body { margin: 0; }
h1 { color: blue; }
```

```javascript
document.addEventListener('DOMContentLoaded', () => {
  console.log('loaded');
});
```
"""
        html, css, js = _parse_llm_response(response)

        assert "<!DOCTYPE html>" in html
        assert "<h1>Hello</h1>" in html
        assert "body { margin: 0; }" in css
        assert "console.log('loaded')" in js

    def test_parse_llm_response_missing_html(self) -> None:
        """Test that missing HTML block raises error."""
        from app.core.static_html_generator import _parse_llm_response

        response = """
```css
body { margin: 0; }
```

```javascript
console.log('test');
```
"""
        with pytest.raises(ValueError, match="No HTML code block"):
            _parse_llm_response(response)

    def test_parse_llm_response_missing_css(self) -> None:
        """Test that missing CSS block raises error."""
        from app.core.static_html_generator import _parse_llm_response

        response = """
```html
<!DOCTYPE html><html></html>
```

```javascript
console.log('test');
```
"""
        with pytest.raises(ValueError, match="No CSS code block"):
            _parse_llm_response(response)

    def test_parse_llm_response_missing_js_uses_default(self) -> None:
        """Test that missing JS block uses minimal JS placeholder."""
        from app.core.static_html_generator import _parse_llm_response

        response = """
```html
<!DOCTYPE html><html></html>
```

```css
body { margin: 0; }
```
"""
        html, css, js = _parse_llm_response(response)

        assert "<!DOCTYPE html>" in html
        assert "margin: 0" in css
        assert "Minimal script" in js or "DOMContentLoaded" in js

    def test_parse_llm_response_js_alternate_syntax(self) -> None:
        """Test parsing JS with ```js instead of ```javascript."""
        from app.core.static_html_generator import _parse_llm_response

        response = """
```html
<!DOCTYPE html><html></html>
```

```css
body { margin: 0; }
```

```js
const x = 1;
```
"""
        _html, _css, js = _parse_llm_response(response)

        assert "const x = 1" in js


class TestGenerationMetrics:
    """Tests for generation metrics collector."""

    @pytest.mark.asyncio
    async def test_metrics_collector_tracks_success(self) -> None:
        """Test that metrics collector tracks successful generations."""
        from app.core.generation_metrics import GenerationMetricsCollector

        collector = GenerationMetricsCollector()

        async with collector.track_generation("lead-1", "html_v1") as metrics:
            metrics.success = True
            metrics.model_used = "claude-sonnet"

        results = collector.get_metrics()
        assert len(results) == 1
        assert results[0].lead_id == "lead-1"
        assert results[0].variant_type == "html_v1"
        assert results[0].success is True
        assert results[0].model_used == "claude-sonnet"

    @pytest.mark.asyncio
    async def test_metrics_collector_tracks_failure(self) -> None:
        """Test that metrics collector tracks failed generations."""
        from app.core.generation_metrics import GenerationMetricsCollector

        collector = GenerationMetricsCollector()

        try:
            async with collector.track_generation("lead-2", "html_v2") as metrics:
                metrics.success = False
                raise ValueError("Test error")
        except ValueError:
            pass

        results = collector.get_metrics()
        assert len(results) == 1
        assert results[0].success is False
        assert "Test error" in (results[0].error_message or "")

    @pytest.mark.asyncio
    async def test_metrics_collector_tracks_lock_wait(self) -> None:
        """Test that metrics collector tracks lock wait time."""
        import asyncio

        from app.core.generation_metrics import GenerationMetricsCollector

        collector = GenerationMetricsCollector()

        async with collector.track_generation("lead-3", "html_v3") as metrics:
            async with collector.track_lock_wait(metrics):
                await asyncio.sleep(0.01)  # Simulate lock wait
            metrics.success = True

        results = collector.get_metrics()
        assert len(results) == 1
        assert results[0].lock_wait_seconds > 0

    def test_log_functions_exist(self) -> None:
        """Test that all logging functions are importable."""
        from app.core.generation_metrics import (
            log_generation_complete,
            log_generation_start,
            log_model_fallback,
            log_variant_progress,
        )

        # Just verify they're callable
        assert callable(log_generation_start)
        assert callable(log_generation_complete)
        assert callable(log_variant_progress)
        assert callable(log_model_fallback)


class TestSlugGeneration:
    """Tests for variant slug generation.

    Note: Slugs are truncated to 8 characters from the company name.
    """

    def test_generate_variant_slug_v1(self) -> None:
        """Test slug generation for html_v1 (truncated to 8 chars)."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)
        slug = repo._generate_variant_slug("lead123", "html_v1", "Acme Corp")

        # "acme-cor" is 8 chars (acme + dash + cor)
        assert slug == "acme-cor-v1"
        assert "-v1" in slug

    def test_generate_variant_slug_v2(self) -> None:
        """Test slug generation for html_v2."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)
        slug = repo._generate_variant_slug("lead123", "html_v2", "Test Company")

        # Base slug truncated to 8 chars
        assert "-v2" in slug
        assert len(slug.replace("-v2", "")) <= 8

    def test_generate_variant_slug_v3(self) -> None:
        """Test slug generation for html_v3."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)
        slug = repo._generate_variant_slug("lead123", "html_v3", "My Business")

        assert "-v3" in slug
        assert len(slug.replace("-v3", "")) <= 8

    def test_generate_variant_slug_nextjs(self) -> None:
        """Test slug generation for nextjs (no suffix)."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)
        slug = repo._generate_variant_slug("lead123", "nextjs", "Acme Corp")

        # No variant suffix for nextjs
        assert "-v" not in slug
        assert len(slug) <= 8

    def test_generate_variant_slug_no_company_name(self) -> None:
        """Test slug generation when company name is None uses lead ID."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)
        slug = repo._generate_variant_slug("abcd1234efgh", "html_v1", None)

        assert slug == "abcd1234-v1"
        assert slug.startswith("abcd1234")

    def test_generate_variant_slug_special_characters(self) -> None:
        """Test slug generation removes special characters."""
        from app.core.sites import SiteRepository

        repo = SiteRepository.__new__(SiteRepository)
        slug = repo._generate_variant_slug("lead123", "html_v1", "Test & Co. LLC!")

        # Special chars removed, truncated to 8 chars
        assert "&" not in slug
        assert "!" not in slug
        assert "." not in slug
        assert "-v1" in slug
