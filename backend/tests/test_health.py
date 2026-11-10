"""Tests for `GET /health`."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from statement_qa.api.health import HealthResponse
from statement_qa.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client over a fresh app instance."""
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_body_matches_schema(client: TestClient) -> None:
    response = client.get("/health")

    assert HealthResponse.model_validate(response.json()).status == "ok"


def test_health_rejects_post(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405


def test_openapi_documents_health_response_model(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    ok_response = schema["paths"]["/health"]["get"]["responses"]["200"]
    ref = ok_response["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/HealthResponse"
