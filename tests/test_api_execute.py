import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_execute_endpoint_smoke():
    client = TestClient(app)
    resp = client.post('/api/execute', json={'goal': 'What is the weather forecast for tomorrow?'})
    assert resp.status_code == 200
    body = resp.json()
    assert 'request_id' in body
    assert body['route']
    assert 'plan' in body
    assert 'research' in body
    assert 'draft' in body
    assert 'final' in body

