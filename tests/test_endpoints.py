import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DISCORD_API_SECRET", "test-secret")

from scraper_api.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-secret"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_scrape_requires_auth():
    r = client.post("/scrape", json={"url": "https://example.com"})
    assert r.status_code == 403


def test_scrape_returns_job_id():
    r = client.post("/scrape", json={"url": "https://example.com"}, headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] in ("pending", "running", "complete")


def test_job_not_found():
    r = client.get("/scrape/nonexistent-id", headers=AUTH)
    assert r.status_code == 404


def test_batch_scrape():
    r = client.post(
        "/scrape/batch",
        json={"urls": ["https://example.com", "https://example.org"]},
        headers=AUTH,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all("job_id" in j for j in data)
