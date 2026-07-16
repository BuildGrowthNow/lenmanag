"""
Client for communicating with the TSX compiler service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CompilerError(Exception):
    """Exception raised when compilation fails."""

    pass


class CompilerClient:
    """Client for the TSX compiler service."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.compiler_service_url or "http://localhost:3001"
        self.timeout = 30.0

    async def compile_tsx(
        self, *, source_code: str, component_name: str, site_id: str
    ) -> dict[str, Any]:
        """
        Compile TSX source code to JavaScript bundle.

        Args:
            source_code: TSX source code to compile
            component_name: Name of the component (for error messages)
            site_id: Site ID (for tracking)

        Returns:
            Dict with keys: success, bundleCode, cssCode, error, validationErrors

        Raises:
            CompilerError: If compilation fails due to server error
        """
        payload = {
            "sourceCode": source_code,
            "componentName": component_name,
            "siteId": site_id,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/compile",
                    json=payload,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 422:
                    # Validation error (bad source code)
                    result = response.json()
                    return result
                elif response.status_code == 400:
                    # Bad request
                    result = response.json()
                    raise CompilerError(
                        f"Bad request: {result.get('error', 'Unknown')}"
                    )
                else:
                    # Server error
                    raise CompilerError(
                        f"Compiler service error: HTTP {response.status_code}"
                    )

        except httpx.TimeoutException:
            raise CompilerError("Compiler service timeout")
        except httpx.ConnectError:
            raise CompilerError("Cannot connect to compiler service")
        except httpx.HTTPError as e:
            raise CompilerError(f"HTTP error: {e}")

    async def health_check(self) -> dict[str, Any]:
        """
        Check if the compiler service is healthy.

        Returns:
            Dict with status, compiler availability, timestamp
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return response.json()
                return {
                    "status": "error",
                    "compiler": "unavailable",
                    "error": f"HTTP {response.status_code}",
                }
        except Exception as e:
            return {
                "status": "error",
                "compiler": "unavailable",
                "error": str(e),
            }


# Singleton instance
_compiler_client: CompilerClient | None = None


def get_compiler_client() -> CompilerClient:
    """Get the singleton compiler client instance."""
    global _compiler_client
    if _compiler_client is None:
        _compiler_client = CompilerClient()
    return _compiler_client
