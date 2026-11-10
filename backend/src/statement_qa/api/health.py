"""Liveness endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Body returned by `GET /health`."""

    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the process is up and serving requests.

    This is a liveness check only; it does not touch the database.
    """
    return HealthResponse(status="ok")
