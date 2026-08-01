from fastapi import FastAPI
from fastapi.testclient import TestClient

from receptenapp.core.errors import (
    ConflictError,
    NotFoundError,
    RateLimitedError,
    SemanticError,
    register_exception_handlers,
)


def _test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/not-found")
    def _not_found() -> None:
        raise NotFoundError("Recept niet gevonden.")

    @app.get("/boom/conflict")
    def _conflict() -> None:
        raise ConflictError("Je hebt dit recept al.", details={"recipe_id": "abc"})

    @app.get("/boom/rate-limited")
    def _rate_limited() -> None:
        raise RateLimitedError("Te veel imports.", retry_after=30)

    @app.get("/boom/semantic")
    def _semantic() -> None:
        raise SemanticError("Einddatum ligt voor de startdatum.")

    @app.get("/boom/validation")
    def _validation(servings: int) -> dict[str, int]:
        return {"servings": servings}

    @app.get("/boom/unhandled")
    def _unhandled() -> None:
        raise RuntimeError("something exploded")

    return app


client = TestClient(_test_app(), raise_server_exceptions=False)


def test_app_error_shape() -> None:
    response = client.get("/boom/not-found")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "Recept niet gevonden."
    assert "details" not in body["error"]


def test_app_error_with_details() -> None:
    response = client.get("/boom/conflict")
    assert response.status_code == 409
    assert response.json()["error"]["details"] == {"recipe_id": "abc"}


def test_rate_limited_sets_retry_after_header() -> None:
    response = client.get("/boom/rate-limited")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert response.json()["error"]["code"] == "rate_limited"


def test_semantic_error_is_422() -> None:
    response = client.get("/boom/semantic")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "semantic_error"


def test_request_validation_error_is_400() -> None:
    response = client.get("/boom/validation")  # missing required query param
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "errors" in body["error"]["details"]


def test_unhandled_exception_is_500_and_does_not_leak() -> None:
    response = client.get("/boom/unhandled")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "RuntimeError" not in body["error"]["message"]
