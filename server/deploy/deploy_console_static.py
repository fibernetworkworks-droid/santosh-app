"""Install only the reviewed console assets; restore them if local HTTP verification fails."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
from urllib.request import urlopen

FILES = ('v2.html', 'v2.css', 'v2.js', 'panel.js', 'results.js', 'workspace.js', 'workspace.css', 'build.js', 'chatlist.js', 'projects.js')


def deploy(bundle, release):
    if len(release) != 40 or any(c not in '0123456789abcdef' for c in release):
        raise ValueError('Expected an exact commit SHA')
    core = Path.home() / 'apps/santosh-core'
    target = core / 'app/static/console'
    if not (target / 'v2.html').is_file():
        raise RuntimeError('Existing console installation not found')
    with tarfile.open(bundle) as archive:
        members = archive.getmembers()
        if {m.name for m in members} != set(FILES) or len(members) != len(FILES):
            raise ValueError('Unexpected deployment contents')
        if any(not m.isfile() for m in members):
            raise ValueError('Only regular console assets may be deployed')
        content = {name: archive.extractfile(name).read() for name in FILES}
    bases = ('http://172.18.0.1:8077', 'http://127.0.0.1:8077')
    base = None
    for candidate in bases:
        try:
            with urlopen(candidate + '/api/console/config', timeout=10) as response:
                config = json.load(response)
            if not config.get('v2'):
                raise RuntimeError('CONSOLE_V2 is disabled; no running settings were changed')
            base = candidate
            break
        except OSError:
            continue
    if not base:
        raise RuntimeError('Running console is not reachable locally')
    backup_dir = core / 'web-console-backups' / release
    backup_dir.mkdir(parents=True, exist_ok=True)
    originals = {name: (target / name).read_bytes() if (target / name).exists() else None for name in FILES}
    # Preserve the first backup on reruns of the same release.
    with tarfile.open(backup_dir / 'console-before.tar', 'x') as archive:
        for name, data in originals.items():
            if data is not None:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    (backup_dir / 'absent-before.json').write_text(json.dumps([n for n, d in originals.items() if d is None]))

    def replace(name, data):
        dest = target / name
        stage = target / ('.' + name + '.deploy')
        stage.write_bytes(data)
        stage.chmod(0o644)
        stage.replace(dest)

    try:
        # Entry HTML last: visitors continue requesting the old assets until installation is complete.
        for name in (*FILES[1:], FILES[0]):
            replace(name, content[name])
        for name in FILES:
            endpoint = '/console/' if name == 'v2.html' else '/static/console/' + name
            with urlopen(base + endpoint + '?release=' + release, timeout=20) as response:
                actual = response.read()
            if hashlib.sha256(actual).digest() != hashlib.sha256(content[name]).digest():
                raise RuntimeError('Served asset mismatch: ' + name)
        print('DEPLOYED console assets verified over HTTP at commit ' + release)
        print('Backup: ' + str(backup_dir))
        print('Backend process, database, mobile, desktop and PC services were not changed or restarted.')
    except BaseException:
        for name, data in originals.items():
            if data is None:
                (target / name).unlink(missing_ok=True)
            else:
                replace(name, data)
        print('Verification failed: previous console assets restored.', file=sys.stderr)
        raise


if __name__ == '__main__':
    deploy(*sys.argv[1:])
