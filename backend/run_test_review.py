import os
os.environ["DEV_AUTH_BYPASS"] = "true"
import time
from fastapi.testclient import TestClient
from src.main import app
from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.code_review_models import DBCodeReview
from sqlalchemy import create_engine
from src.core.config import settings

engine = create_engine(settings.POSTGRES_URL)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

print("Starting review...")
start_payload = {
    "repository_id": "64e085e4-1305-4bd7-85a3-80d684351329",
    "files": [
        "src/application/services/auth_service.py",
        "src/interfaces/api/dependencies.py",
        "src/main.py"
    ]
}

response = client.post("/api/v1/reviews/start", json=start_payload)
print(f"Start Response: {response.status_code}")
data = response.json()
print(f"Response Data: {data}")

if "review_id" not in data:
    print("No review_id found. Exiting.")
    exit(1)

review_id = data["review_id"]
print(f"Review ID: {review_id}")

resp = client.get(f"/api/v1/reviews/{review_id}")
status_data = resp.json()
print("Full Review Data:")
import json
print(json.dumps(status_data, indent=2))

print("\n--- Findings Stats ---")
arch = client.get(f"/api/v1/reviews/{review_id}/architecture").json()
print("Architecture findings:", len(arch.get("architecture_findings", [])))

perf = client.get(f"/api/v1/reviews/{review_id}/performance").json()
print("Performance findings:", len(perf.get("performance_findings", [])))

ref = client.get(f"/api/v1/reviews/{review_id}/refactoring").json()
print("Refactoring findings:", len(ref.get("refactoring_findings", [])))
