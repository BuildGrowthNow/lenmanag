#!/usr/bin/env python3
"""
Deployment verification script for multi-variant site generation.

Run this script after deployment to verify that all components are working correctly.

Usage:
    python scripts/verify_deployment.py [--base-url https://sites-api.lenquant.com]

Checks:
1. API health endpoint
2. Redis connectivity (generation lock)
3. Variant strategy loading
4. Static HTML generator parsing
5. Database connectivity
"""

from __future__ import annotations

import argparse
import asyncio
import sys


class DeploymentVerifier:
    """Verify multi-variant deployment is working correctly."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.results: list[tuple[str, bool, str]] = []

    def report(self, check: str, passed: bool, message: str = "") -> None:
        """Record a check result."""
        status = "[PASS]" if passed else "[FAIL]"
        self.results.append((check, passed, message))
        print(f"  {status} {check}" + (f": {message}" if message else ""))

    async def check_health_endpoint(self) -> None:
        """Check API health endpoint."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/health",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        self.report("Health endpoint", True, "API is healthy")
                    else:
                        self.report(
                            "Health endpoint",
                            False,
                            f"Status {response.status}",
                        )
        except Exception as e:
            self.report("Health endpoint", False, str(e))

    def check_variant_strategies(self) -> None:
        """Check variant strategy definitions."""
        try:
            from app.core.variant_strategy import get_variant_strategies

            strategies = get_variant_strategies()

            if len(strategies) == 3:
                self.report("Variant strategies", True, "3 HTML variants defined")
            else:
                self.report(
                    "Variant strategies",
                    False,
                    f"Expected 3 strategies, got {len(strategies)}",
                )

            # Verify each strategy has required fields
            required_fields = [
                "variantType",
                "variantLabel",
                "variantPosition",
                "designMode",
                "creativeBriefGuidance",
            ]
            for variant_type, strategy in strategies.items():
                missing = [f for f in required_fields if f not in strategy]
                if missing:
                    self.report(
                        f"Strategy {variant_type}",
                        False,
                        f"Missing fields: {missing}",
                    )
        except Exception as e:
            self.report("Variant strategies", False, str(e))

    def check_static_html_parser(self) -> None:
        """Check static HTML parser."""
        try:
            from app.core.static_html_generator import _parse_llm_response

            test_response = """
```html
<!DOCTYPE html><html><body>Test</body></html>
```

```css
body { margin: 0; }
```

```javascript
console.log('test');
```
"""
            html, css, _js = _parse_llm_response(test_response)

            if "<!DOCTYPE html>" in html and "margin" in css:
                self.report("Static HTML parser", True, "Parser working correctly")
            else:
                self.report("Static HTML parser", False, "Parsed content incorrect")
        except Exception as e:
            self.report("Static HTML parser", False, str(e))

    async def check_redis_connectivity(self) -> None:
        """Check Redis connectivity for generation lock."""
        try:
            import redis.asyncio as redis_async

            from app.core.config import get_settings

            settings = get_settings()
            client = redis_async.from_url(
                settings.celery_broker_url, decode_responses=True
            )

            # Test basic connectivity
            pong = await client.ping()
            if pong:
                self.report("Redis connectivity", True, "Redis responding")
            else:
                self.report("Redis connectivity", False, "No response from Redis")

            await client.aclose()
        except Exception as e:
            self.report("Redis connectivity", False, str(e))

    async def check_database_connectivity(self) -> None:
        """Check MongoDB connectivity."""
        try:
            from app.core.mongo import get_database

            db = get_database()
            if db is not None:
                # Try to list collections
                collections = await db.list_collection_names()
                self.report(
                    "Database connectivity",
                    True,
                    f"Connected, {len(collections)} collections",
                )
            else:
                self.report(
                    "Database connectivity",
                    False,
                    "Database not initialized",
                )
        except Exception as e:
            self.report("Database connectivity", False, str(e))

    def check_slug_generation(self) -> None:
        """Check variant slug generation."""
        try:
            from app.core.sites import SiteRepository

            repo = SiteRepository.__new__(SiteRepository)

            slugs = [
                repo._generate_variant_slug("lead1", "html_v1", "Test Company"),
                repo._generate_variant_slug("lead1", "html_v2", "Test Company"),
                repo._generate_variant_slug("lead1", "html_v3", "Test Company"),
                repo._generate_variant_slug("lead1", "nextjs", "Test Company"),
            ]

            if len(slugs) == len(set(slugs)):
                self.report("Slug generation", True, "All slugs unique")
            else:
                self.report("Slug generation", False, "Duplicate slugs generated")
        except Exception as e:
            self.report("Slug generation", False, str(e))

    def check_celery_task_registered(self) -> None:
        """Check that the multi-variant Celery task module exists."""
        try:
            # Import the tasks module to ensure the task is defined
            from app.core import tasks as tasks_module

            # Check that the task function exists
            if hasattr(tasks_module, "run_multi_variant_generation_task"):
                self.report(
                    "Celery task",
                    True,
                    "Multi-variant task function defined",
                )
            else:
                self.report(
                    "Celery task",
                    False,
                    "run_multi_variant_generation_task not found in tasks module",
                )
        except Exception as e:
            self.report("Celery task", False, str(e))

    async def run_all_checks(self) -> bool:
        """Run all verification checks."""
        print("\n" + "=" * 60)
        print("Multi-Variant Deployment Verification")
        print("=" * 60 + "\n")

        print("Checking backend components...")
        self.check_variant_strategies()
        self.check_static_html_parser()
        self.check_slug_generation()
        self.check_celery_task_registered()

        print("\nChecking connectivity...")
        await self.check_health_endpoint()
        await self.check_redis_connectivity()
        await self.check_database_connectivity()

        print("\n" + "-" * 60)

        # Summary
        passed = sum(1 for _, p, _ in self.results if p)
        total = len(self.results)
        all_passed = passed == total

        print(f"\nResults: {passed}/{total} checks passed")

        if all_passed:
            print("\n[OK] All checks passed! Deployment is ready.\n")
        else:
            print("\n[ERROR] Some checks failed. Please review the errors above.\n")
            for check, p, msg in self.results:
                if not p:
                    print(f"  - {check}: {msg}")

        return all_passed


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify multi-variant deployment")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for API health check",
    )
    args = parser.parse_args()

    verifier = DeploymentVerifier(base_url=args.base_url)
    success = await verifier.run_all_checks()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
