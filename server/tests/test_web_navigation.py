"""Web history pagination preserves mobile list defaults and tenant boundaries."""
from datetime import timedelta
from fastapi.testclient import TestClient
from tests.test_v162_chats import cs, H

def test_console_history_paginates_without_duplicates_or_tenant_leaks(cs):
    from app.db import Conversation, session, now
    from app import chats
    with session() as s:
        for i in range(205):
            s.add(Conversation(id=f"nav-{i}", tenant_id="default", title=f"History {i}", created_at=now()-timedelta(minutes=i)))
        s.add(Conversation(id="nav-private",tenant_id="other",title="Private"))
        s.add(Conversation(id="nav-archive",tenant_id="default",title="Archived",archived=True))
    first=cs.get('/api/console/conversations?limit=200&offset=0',headers=H)
    second=cs.get('/api/console/conversations?limit=200&offset=200',headers=H)
    assert first.status_code==second.status_code==200
    a=first.json()['conversations'];b=second.json()['conversations']
    ids=[c['id'] for c in a+b]
    assert len(a)==200 and len(b)==5 and len(set(ids))==205
    assert 'nav-private' not in ids and 'nav-archive' not in ids
    assert len(chats.chat_list('default',False,40))==40
    archived=cs.get('/api/console/conversations?archived=true&offset=0',headers=H).json()['conversations']
    assert [c['id'] for c in archived]==['nav-archive']
