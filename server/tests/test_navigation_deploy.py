import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('nav_deploy',Path(__file__).parents[1]/'deploy/deploy_web_navigation.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_pagination_patch_is_idempotent_and_keeps_unrelated_code():
    for kind in ('main','chats'):
        current=(Path(__file__).parents[1]/'app'/f'{kind}.py').read_text()
        assert module.pagination(current,kind)==current

def test_unknown_live_shape_is_rejected_before_install():
    with pytest.raises(RuntimeError):module.pagination('unrecognized = True','main')

def test_original_source_patch_preserves_agent_guard_and_version():
    import subprocess
    root=Path(__file__).parents[2]
    for kind in ('main','chats'):
        original=subprocess.check_output(['git','show',f'c1b50f9:server/app/{kind}.py'],cwd=root,text=True)
        updated=module.pagination(original,kind)
        assert updated!=original
        assert module.pagination(updated,kind)==updated
        if kind=='main':
            assert 'APP_VERSION = "0.217.0"' in updated
            assert 'def console_conversations' in updated
