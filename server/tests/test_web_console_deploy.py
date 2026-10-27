"""Static-only deployment verifies HTTP bytes and restores previous assets on failure."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import pytest

spec = importlib.util.spec_from_file_location('web_deploy', Path(__file__).parents[1] / 'deploy/deploy_console_static.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


@pytest.fixture
def install(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    target = tmp_path / 'apps/santosh-core/app/static/console'
    target.mkdir(parents=True)
    for name in d.FILES[:4]:
        (target / name).write_bytes(b'original:' + name.encode())
    bundle = tmp_path / 'bundle.tar.gz'
    with tarfile.open(bundle, 'w:gz') as archive:
        for name in d.FILES:
            data = b'new:' + name.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return target, bundle


def responses(target, fail=False):
    def get(url, timeout):
        if '/api/console/config' in url:
            return io.BytesIO(json.dumps({'v2': True}).encode())
        if fail:
            return io.BytesIO(b'mismatch')
        name = 'v2.html' if '/console/?' in url else url.split('/console/')[1].split('?')[0]
        return io.BytesIO((target / name).read_bytes())
    return get


def test_deploy_verifies_only_static_assets(install, monkeypatch):
    target, bundle = install
    monkeypatch.setattr(d, 'urlopen', responses(target))
    d.deploy(bundle, 'a' * 40)
    assert all((target / n).read_bytes() == b'new:' + n.encode() for n in d.FILES)
    assert (target.parents[2] / 'web-console-backups' / ('a' * 40) / 'console-before.tar').exists()


def test_failed_verification_restores_and_removes_new_assets(install, monkeypatch):
    target, bundle = install
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    monkeypatch.setattr(d, 'urlopen', responses(target, fail=True))
    with pytest.raises(RuntimeError, match='Served asset mismatch'):
        d.deploy(bundle, 'b' * 40)
    assert {p.name: p.read_bytes() for p in target.iterdir()} == before


def test_rejects_unreviewed_bundle(install):
    target, bundle = install
    with tarfile.open(bundle, 'w:gz') as archive:
        archive.addfile(tarfile.TarInfo('../main.py'))
    with pytest.raises(ValueError, match='Unexpected deployment contents'):
        d.deploy(bundle, 'c' * 40)
    assert (target / 'v2.html').read_bytes() == b'original:v2.html'
