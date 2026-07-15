from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class ResponseMeta(BaseModel):
    version: str
    requestId: str
    generatedAt: datetime


class ResponseError(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ResponseEnvelope(GenericModel, Generic[T]):
    status: Literal["success", "error"]
    meta: ResponseMeta
    data: Optional[T] = None
    error: Optional[ResponseError] = None


def success_response(data: T, *, meta: ResponseMeta) -> ResponseEnvelope[T]:
    return ResponseEnvelope(status="success", meta=meta, data=data)
