"""
Internal API endpoints for system services.
These endpoints are not exposed publicly.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.compiler_client import CompilerError, get_compiler_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


class CompileRequest(BaseModel):
    sourceCode: str = ""
    componentName: str = Field(..., min_length=1)
    siteId: str = Field(..., min_length=1)
    jsEntry: str | None = None
    capabilityManifest: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_an_entry(self) -> "CompileRequest":
        if not self.sourceCode.strip() and not (self.jsEntry or "").strip():
            raise ValueError("sourceCode or jsEntry is required")
        return self


class CompileResponse(BaseModel):
    success: bool
    bundleCode: str | None = None
    cssCode: str | None = None
    error: str | None = None
    validationErrors: list[str] = Field(default_factory=list)
    dependencyInventory: list[str] = Field(default_factory=list)
    bundleMetrics: dict[str, int] | None = None
    capabilityManifest: dict[str, Any] | None = None


@router.post("/compile", response_model=CompileResponse)
async def compile_tsx(request: CompileRequest) -> CompileResponse:
    """
    Compile TSX source code to JavaScript bundle.

    This endpoint is used by the generation pipeline to compile
    AI-generated components into executable bundles.
    """
    compiler = get_compiler_client()

    try:
        result = await compiler.compile_tsx(
            source_code=request.sourceCode,
            component_name=request.componentName,
            site_id=request.siteId,
            js_entry=request.jsEntry,
            capability_manifest=request.capabilityManifest,
        )

        return CompileResponse(**result)

    except CompilerError as e:
        logger.error("Compilation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compile/health")
async def compiler_health() -> dict[str, Any]:
    """
    Check if the compiler service is available.
    """
    compiler = get_compiler_client()
    health = await compiler.health_check()
    return health
