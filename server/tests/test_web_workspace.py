"""Real upload and durable turn contracts; provider work is replaced to avoid credits."""
from fastapi.testclient import TestClient


def test_workspace_turn_keeps_sources_and_retries_once(env, monkeypatch):
    monkeypatch.setenv('API_KEY', 'web-workspace-test-key')
    monkeypatch.setenv('SIDE_PANEL', 'true')
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main, turn_inbox
    captured = []

    async def receive(*args, **kwargs):
        captured.append((args, kwargs))

    monkeypatch.setattr(turn_inbox, 'run_owned', receive)
    headers = {'Authorization': 'Bearer web-workspace-test-key'}
    with TestClient(main.app) as client:
        conv = client.post('/api/conversations', headers=headers).json()['id']
        uploaded = client.post(f'/api/conversations/{conv}/files', headers=headers,
                               files={'file': ('source.txt', b'Confirmed launch date: 30 October.', 'text/plain')})
        assert uploaded.status_code == 200
        fid = uploaded.json()['file_id']
        body = {'text': 'Create a real Word document from the attached source.',
                'files': [fid], 'client_id': 'workspace-stable-retry-id'}
        first = client.post(f'/api/conversations/{conv}/messages', json=body, headers=headers)
        again = client.post(f'/api/conversations/{conv}/messages', json=body, headers=headers)
        assert first.status_code == again.status_code == 202
        assert again.json()['duplicate'] is True
        assert len(captured) == 1
        assert captured[0][0][1] == conv
        assert fid in captured[0][1]['context'] and 'source.txt' in captured[0][1]['context']
        assert captured[0][1]['client_id'] == body['client_id']
        timeline = client.get(f'/api/conversations/{conv}/timeline', headers=headers).json()
        user = [x for x in timeline['events'] if x['kind'] == 'message' and x['payload'].get('role') == 'user']
        assert len(user) == 1 and user[0]['payload']['files'][0]['file_id'] == fid
        assert client.post(f'/api/conversations/{conv}/messages', json=body).status_code == 401
    get_settings.cache_clear()
