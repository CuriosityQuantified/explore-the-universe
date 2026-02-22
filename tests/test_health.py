from httpx import Client

BASE_URL = "http://localhost:8000"


def test_health_endpoint_returns_200_when_all_services_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint_reports_postgresql_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "postgresql" in data["services"]
    assert data["services"]["postgresql"]["status"] == "connected"


def test_health_endpoint_reports_redis_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "redis" in data["services"]
    assert data["services"]["redis"]["status"] == "connected"


def test_health_endpoint_reports_minio_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "minio" in data["services"]
    assert data["services"]["minio"]["status"] == "connected"
    assert "buckets" in data["services"]["minio"]


def test_health_endpoint_reports_neo4j_connected():
    with Client(base_url=BASE_URL) as client:
        response = client.get("/health")

    data = response.json()
    assert "neo4j" in data["services"]
    assert data["services"]["neo4j"]["status"] == "connected"
