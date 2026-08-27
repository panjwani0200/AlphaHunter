from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    from app.core.config import settings
    assert body["market_data_provider"] == settings.market_data_provider


def test_readiness_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/ready")

    assert response.status_code == 200
    assert "database" in response.json()


def test_scanner_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/scanner/latest?limit=3")

    assert response.status_code == 200
    assert len(response.json()) <= 3


def test_dashboard_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "AlphaHunter" in response.text


def test_dashboard_has_stock_lookup_ui() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Stock Lookup" in response.text
    assert "Search" in response.text


def test_scanner_run_creates_csv_export() -> None:
    client = TestClient(create_app())

    run_response = client.post("/api/scanner/run?limit=3")
    assert run_response.status_code == 200

    export_response = client.get("/api/exports/latest")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
