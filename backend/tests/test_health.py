"""Health endpoint tests."""


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "expense-tracker-api"


async def test_health_db(client):
    response = await client.get("/api/v1/health/db")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"healthy", "unhealthy"}


async def test_docs_available(client):
    response = await client.get("/docs")
    assert response.status_code == 200


async def test_openapi_schema(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/analytics/top-expenses" in paths
