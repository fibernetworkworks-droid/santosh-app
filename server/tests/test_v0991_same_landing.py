"""v0.991 SAME LANDING (owner: "CHECK HOW HOOLA APP CHAT CONVERSATION IS SAME AS CONSOLE CHAT --- FONT, TIMING, WORD
LANDING ETC" -> "GO"). Found: the console's pacer threw away the time left over each frame and released one word per
screen refresh (60 a second at 60 Hz, 120 at 120 Hz - twice the Calm pace it was written for); the phone drew streamed
words in whatever bursts the network brought, with no fade; phone headings one step smaller; the phone's working clock
counted from when the row appeared. Now both run one pacer (a true 34 ms a word, the same capped catch-up), both fade a
new word in over 460 ms, the headings match, and the clock counts from her message."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STREAM = ROOT / "server/app/static/console/stream.js"
CHAT = ROOT / "lib/ui/chat/hoola_chat.dart"

RUN = r"""
global.document = {hidden: false}; let T = 0; const cbs = [];
global.performance = {now: () => T};
global.requestAnimationFrame = f => { cbs.push(f); return cbs.length; }; global.cancelAnimationFrame = () => {};
global.window = {}; global.fetch = () => {};
eval(require('fs').readFileSync(process.argv[1], 'utf8'));
const out = {};
for (const hz of [60, 120]) {
  let shown = ''; const P = new window.HoolaStream.Pacer(t => { shown = t; }); T = 0;
  const text = Array.from({length: 60}, (_, i) => 'w' + i + ' ').join(''); P.final(text);
  while (cbs.length) { const f = cbs.shift(); T += 1000 / hz; f(T); }
  out[hz] = {ms: T, done: shown === text};
}
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_console_lands_at_a_true_34_ms_a_word_on_every_screen():
    import json
    r = subprocess.run(["node", "-e", RUN, str(STREAM)], capture_output=True, text=True, timeout=60)
    out = json.loads(r.stdout.strip())
    for hz in ("60", "120"):
        assert out[hz]["done"]
        wps = 60 / (out[hz]["ms"] / 1000)
        assert 27 <= wps <= 32, (hz, wps)          # ~29 a second (34 ms), the same on a 60 Hz and a 120 Hz screen


def test_phone_runs_the_same_numbers_as_the_console():
    js, d = STREAM.read_text(), CHAT.read_text()
    assert "Math.floor(this.acc / 34)" in js and "Math.min(2, Math.floor(this.queue.length / 80))" in js
    assert "const kLandMsPerWord = 34;" in d and "(waiting ~/ 80).clamp(0, 2)" in d
    soft = re.search(r"const SOFT_MS = (\d+);", (ROOT / "server/app/static/console/md.js").read_text()).group(1)
    assert f"const kLandSoftMs = {soft};" in d
    # streamed words go through the pacer, a whole reply too, and the final message carries on from the stream
    assert "_Paced(text: '${it.data['text'] ?? ''}', live: true, land: 'stream:$turn')" in d
    assert "_Paced(text: text, live: false, startChars: from" in d
    assert "class _Reveal" not in d


def test_headings_match_the_console():
    css = (ROOT / "server/app/static/console/v2.css").read_text()
    assert ".textmd h3.mdh{font-size:22px}" in css and ".textmd h4.mdh{font-size:20px}" in css
    assert ".textmd h5.mdh,.textmd h6.mdh{font-size:17px}" in css
    md = (ROOT / "lib/ui/chat/hoola_md.dart").read_text()
    for size in ("22", "20", "17"):
        assert f"copyWith(fontSize: reply ? {size} : null)" in md


def test_working_clock_counts_from_her_message():
    d = CHAT.read_text()
    assert "since: _sentAt(feed)" in d and "DateTime? _sentAt(List<FeedItem> feed)" in d
    assert "final DateTime? since;" in d


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.152"
    assert "0.999.152+1147" in (ROOT / "pubspec.yaml").read_text()
