from src.app import app


def test_home_returns_application_message():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.json["message"] == "DevOps Lab API is running"
    assert response.json["version"] == "1.0.0"


def test_health_returns_healthy():
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_info_returns_application_details():
    client = app.test_client()

    response = client.get("/info")

    assert response.status_code == 200
    assert response.json["application"] == "devops-lab-api"

def test_version_returns_application_version_and_environment():
    client = app.test_client()

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json["application"] == "devops-lab-api"
    assert response.json["version"] == "1.0.0"
    assert response.json["environment"] == "local"
    assert response.json["build"] == "unknown"
