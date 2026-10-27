"""Deploy console navigation plus surgical pagination edits; preserve all other live code."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from urllib.request import urlopen

FILES = ('v2.html','v2.css','v2.js','panel.js','results.js','workspace.js','workspace.css','build.js','chatlist.js','projects.js')


def pagination(source, kind):
    pairs = {
        'main': [
            ('def console_conversations(limit: int = 40, archived: bool = False, project: str = "", tenant: str = Depends(current_tenant)):',
             'def console_conversations(limit: int = 40, archived: bool = False, project: str = "", offset: int = 0, tenant: str = Depends(current_tenant)):'),
            ('chats.chat_list(tenant, archived, max(limit, 200), project[:40])',
             'chats.chat_list(tenant, archived, max(limit, 200), project[:40], max(0, offset))'),
        ],
        'chats': [
            ('def chat_list(tenant: str, archived: bool = False, limit: int = 200, project: str = "")',
             'def chat_list(tenant: str, archived: bool = False, limit: int = 200, project: str = "", offset: int = 0)'),
            ('.order_by(func.coalesce(Conversation.pinned, False).desc(), at.desc()).limit(max(1, min(limit, 500))))',
             '.order_by(func.coalesce(Conversation.pinned, False).desc(), at.desc(), Conversation.id.desc()).limit(max(1, min(limit, 500))).offset(max(0, offset)))'),
        ],
    }
    for old, new in pairs[kind]:
        if new in source:
            if source.count(new) != 1:
                raise RuntimeError('Ambiguous already-patched source: '+kind)
            continue
        if source.count(old) != 1:
            raise RuntimeError('Live pagination source changed; refusing to overwrite: '+kind)
        source = source.replace(old, new, 1)
    ast.parse(source)
    return source


def restart():
    subprocess.run(['pm2','restart','santosh','--kill-timeout','12000','--update-env'],check=True,stdout=subprocess.DEVNULL)


def health():
    for _ in range(24):
        for base in ('http://127.0.0.1:8077','http://172.18.0.1:8077'):
            try:
                with urlopen(base+'/healthz',timeout=3) as r:
                    if json.load(r).get('ok') is True:
                        return base
            except (OSError,ValueError):
                pass
        time.sleep(3)
    raise RuntimeError('Backend did not become healthy')


def deploy(bundle, release):
    if len(release)!=40 or any(c not in '0123456789abcdef' for c in release):
        raise ValueError('Expected release SHA')
    bins=[str(Path.home()/'.local/bin'),'/usr/local/bin']+[str(p) for p in (Path.home()/'.nvm/versions/node').glob('*/bin')]
    os.environ['PATH']=':'.join(bins+[os.environ.get('PATH','')])
    core=Path.home()/'apps/santosh-core'
    with tarfile.open(bundle) as archive:
        members=archive.getmembers()
        if len(members)!=len(FILES) or {m.name for m in members}!=set(FILES) or any(not m.isfile() for m in members):
            raise ValueError('Unexpected console archive contents')
        changes={core/'app/static/console'/n:archive.extractfile(n).read() for n in FILES}
    for name in ('main','chats'):
        p=core/'app'/f'{name}.py'
        changes[p]=pagination(p.read_text(),name).encode()
    agent=core/'app/agent/santosh.py'
    agent_before=hashlib.sha256(agent.read_bytes()).hexdigest()
    originals={p:p.read_bytes() if p.exists() else None for p in changes}
    backup=core/'web-navigation-backups'/release
    backup.mkdir(parents=True,exist_ok=False)
    for p,data in originals.items():
        if data is not None:
            target=backup/p.relative_to(core);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    def replace(p,data):
        stage=p.with_name('.'+p.name+'.navigation')
        stage.write_bytes(data)
        stage.chmod(p.stat().st_mode & 0o777 if p.exists() else 0o644)
        os.replace(stage,p)
    try:
        # Backend first; entry HTML last. Never replace the working agent or voice code.
        for name in ('chats','main'):
            p=core/'app'/f'{name}.py';replace(p,changes[p])
        restart();base=health()
        for name in (*FILES[1:],FILES[0]):
            p=core/'app/static/console'/name;replace(p,changes[p])
        for name in FILES:
            endpoint='/console/' if name=='v2.html' else '/static/console/'+name
            with urlopen(base+endpoint+'?release='+release,timeout=15) as r:
                actual=r.read()
            if actual!=changes[core/'app/static/console'/name]:
                raise RuntimeError('Served asset differs: '+name)
        if hashlib.sha256(agent.read_bytes()).hexdigest()!=agent_before:
            raise RuntimeError('Agent unexpectedly changed during release')
        for name in ('chats','main'):
            p=core/'app'/f'{name}.py'
            if p.read_bytes()!=changes[p]:
                raise RuntimeError('Backend file unexpectedly changed during release')
        print('NAVIGATION_DEPLOYED: served console assets verified; backend healthy; working agent unchanged')
        print('BACKUP: '+str(backup))
    except BaseException:
        for p,data in originals.items():
            if data is None:
                p.unlink(missing_ok=True)
            else:
                replace(p,data)
        restart();health()
        print('Release failed; original console and pagination files restored.',file=sys.stderr)
        raise

if __name__=='__main__':
    deploy(*sys.argv[1:])
