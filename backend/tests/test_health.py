from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check_returns_service_unavailable_without_db():
    # Mock psycopg2.connect to simulate database being offline
    with patch("psycopg2.connect") as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")
        response = client.get("/api/v1/health/")
        assert response.status_code == 503
        assert response.json()["detail"]["status"] == "error"
        assert response.json()["detail"]["db"] == "disconnected"

