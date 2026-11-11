"""v0.478.0 HOOLA FRAMES on the web console (owner: "DEPLOYE IT TO WEB CONSOLE ALSO").

The console could already RECEIVE a frames MP4 - the pc_file card renders as an inline
<video> (results.js) and opens as a video tab (panel.js). What was missing was OFFERING
the free engine: the Creative workspace "Video & motion" form only knew the paid
video_studio storyboard path, and the Kaam catalog had no frames row. These pins hold
the three touch-ups (workspace engine choice, kaam catalog entry, version layer) so a
later merge cannot silently drop the console's only free video path."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
WS = ROOT / 'app/static/console/workspace.js'
KAAM = ROOT / 'app/static/console/kaam.js'
V2 = ROOT / 'app/static/console/v2.html'
RESULTS = ROOT / 'app/static/console/results.js'
PANEL = ROOT / 'app/static/console/panel.js'


def src(path: Path) -> str:
    return path.read_text(encoding='utf-8')


# ---------- Creative workspace: the engine choice ----------

def test_workspace_video_has_engine_choice_frames_default():
    s = src(WS)
    assert "chips('vengine'" in s, 'engine chip row missing'
    assert "['frames','HOOLA FRAMES" in s and "['film','AI film" in s
    sel = re.search(r'<select id="cw-vengine".*?</select>', s, re.S)
    assert sel and 'value="frames"' in sel.group(0) and 'value="film"' in sel.group(0)
    # frames is the default: selected unless the draft says film
    assert "d.vengine!=='film'?' selected':''}>frames" in s


def test_workspace_voiceover_only_for_film():
    s = src(WS)
    # the voiceover select is wrapped in the film-only conditional
    assert "${d.vengine==='film'?`<label>Voiceover" in s


def test_workspace_frames_request_pillow_texts():
    s = src(WS)
    assert 'Use hoola_frames to render a real MP4 with the free in-house engine' in s
    assert 'app/studio/frames_contract.md' in s, 'the model must be pointed at the contract'
    assert 'window.__timelines' in s and 'no network fetch' in s
    assert 'action=check first and fix every error it reports, then action=render' in s
    assert 'Do not claim the video is ready before action=render succeeds' in s


def test_workspace_film_branch_still_intact_and_gated():
    s = src(WS)
    assert "if(mode==='video' && d.vengine==='film')return `Use video_studio" in s
    assert 'Do not start paid generation until I approve its cost' in s


def test_workspace_labels_and_note_speak_per_engine():
    s = src(WS)
    assert "d.vengine === 'film' ? 'Prepare storyboard · free' : 'Render video · free · ~2 min'" in s
    assert "'Free in-house render: animated MP4 in chat in about 2 minutes'" in s
    assert 'It cannot film real people, and voiceover needs the AI film engine' in s


def test_workspace_take_reads_vengine_and_chip_handler_redraws():
    s = src(WS)
    assert "vengine:$('#cw-vengine')?.value" in s
    assert 'if(b.dataset.vengine){take();drafts[mode].vengine=b.dataset.vengine;render();return;}' in s


def test_workspace_old_honest_hint_gone():
    s = src(WS)
    assert 'Hoola prepares the storyboard first.' not in s
    assert 'storyboard first · paid' in s


# ---------- Kaam catalog: the tools page offers it ----------

def test_kaam_media_group_has_frames_row():
    s = src(KAAM)
    assert '["frames","HOOLA FRAMES video","Free animated MP4, ~2 min",' in s
    # sits inside the Photos & video group, next to studio (paid) and brand
    i_studio, i_frames = s.index('"studio","AI video (Studio)"'), s.index('"frames","HOOLA FRAMES video"')
    i_media = s.index('Photos & video')
    assert i_media < i_frames < i_studio + 200, 'frames row should sit beside the studio row in the media group'


def test_kaam_frames_icon():
    assert '"frames":"📼"' in src(KAAM)


# ---------- The receive side was already there - pin it anyway ----------

def test_results_renders_pc_file_with_inline_video():
    s = src(RESULTS)
    assert "'photo_made', 'pc_file', 'motion', 'video_job', 'artifact'" in s
    assert "['image', 'video', 'audio', 'pdf'].includes(info.media)" in s
    assert "document.createElement(info.media === 'image' ? 'img' : info.media)" in s


def test_panel_knows_mp4_is_video():
    assert r'/\.(mp4|webm|mov|m4v|mkv|3gp)$/' in src(PANEL)


# ---------- Version layer ----------

def test_console_stamps_0_4_8_5():
    # 21 stamps = the 20 originals + the skills.js tag added by v0.485 SKILL DESK.
    # The COUNT is the guard; the version they carry follows APP_VERSION (see below).
    s = src(V2)
    from app.main import APP_VERSION
    # v0.537: this pinned the literal v=0.487.0 and had gone red on main, which ships the stamps at
    # APP_VERSION. Two sessions' conventions disagreed; CLAUDE.md's version ritual lists the console
    # stamps as part of the bump, so the typed number goes and the COUNT - the real guard - stays.
    # v0.768: 28 -> 27. code.js left the console page - Hoola Code is its own page (/console/code, hoolacode.html).
    # v0.781: 27 -> 28. connectors.js joined the console page (the Connectors page).
    # v0.772 AI APPS: 28 -> 29. aiapps.js joined the console page (its stylesheet is loaded by the script, not v2.html).
    # v0.799 DESK ROOM: 29 -> 30. deptdesk.js joined the console page (the department desks).
    assert s.count(f'v={APP_VERSION}') == 31, f"expected 31 stamps at {APP_VERSION}, got {s.count(f'v={APP_VERSION}')}"
    assert 'v=0.482.0' not in s and 'v=0.473.0' not in s
    assert f'console/skills.js?v={APP_VERSION}' in s and 'id="v-skills"' in s


def test_app_version_story():
    main = (ROOT / 'app/main.py').read_text(encoding='utf-8')
    from app.main import APP_VERSION
    assert f'APP_VERSION = "{APP_VERSION}"' in main    # v0.537: was a typed 0.535.0, two releases behind
    # story pin moved to the v0.555 story (the v0.476 precedent: the newest release's story carries the
    # marker; the older stories live in git history)
    assert 'GALTI PAKDO' in main and 'galti' in main  # the newest-story precedent (v0.802.0 carries the marker; older stories live in git history)


def test_pubspec_pin():
    pub = (ROOT.parents[0] / 'pubspec.yaml').read_text(encoding='utf-8') if (ROOT.parents[0] / 'pubspec.yaml').exists() else None
    if pub is None:  # tests dir is server/tests; pubspec is at repo root
        pub = (ROOT / 'pubspec.yaml').read_text(encoding='utf-8')
    assert 'version: 0.802.0+801' in pub
