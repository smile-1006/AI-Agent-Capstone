import tempfile
import os
from fastapi.testclient import TestClient
from app.main import app

from PIL import Image


client = TestClient(app)


def test_web_search_endpoint():
    resp = client.post('/api/tools/web_search', json={'query': 'unit test', 'max_results': 2})
    assert resp.status_code == 200
    body = resp.json()
    assert 'query' in body
    assert 'results' in body


def test_image_process_info_endpoint():
    # create a small temporary image
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    try:
        img = Image.new('RGB', (16, 16), color='white')
        img.save(path)

        resp = client.post('/api/tools/image_process', json={'path': path, 'action': 'info'})
        assert resp.status_code == 200
        body = resp.json()
        assert body.get('path') == path
        assert 'format' in body or 'width' in body
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def test_execute_with_tool_context():
    # perform a web search and then run the agent with that result as context
    s = client.post('/api/tools/web_search', json={'query': 'test execute', 'max_results': 1})
    assert s.status_code == 200
    sr = s.json()

    resp = client.post('/api/execute', json={'goal': 'Summarize the search result', 'context': {'tool': 'web_search', 'result': sr}})
    assert resp.status_code == 200
    body = resp.json()
    assert 'plan' in body
    assert 'research' in body
