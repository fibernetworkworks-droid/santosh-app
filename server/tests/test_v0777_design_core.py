"""v0.777 HOOLA DESIGN, the client core (docs/HOOLA_DESIGN_PLAN.md section 3): hd-math.js + hd-core.js + hd-net.js.

The real tests are JavaScript - server/tests/web/design_core_test.js, run with plain `node` (no packages): fractional
indexes, the store (create / set / remove / move, tx merging, undo / redo, world matrices, pending + rollback),
three editors against a contract server that must always converge, HD.net against a scripted socket, and speed
(50,000 nodes). This file runs them so CI covers them, and checks that the keys the BROWSER makes and the keys the
SERVER makes (app/design/fracidx.py) order the same way and accept each other."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_core_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")

# hd-core.js in a bare vm context; reads {"keys": [...], "seed": n, "inserts": n} and prints the keys after the inserts
FRAC_JS = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
const dir = process.argv[1], job = JSON.parse(fs.readFileSync(0, 'utf8'));
const ctx = {console}; ctx.window = ctx; vm.createContext(ctx);
for (const f of ['hd-math.js', 'hd-core.js']) vm.runInContext(fs.readFileSync(path.join(dir, f), 'utf8'), ctx, {filename: f});
const F = ctx.HD.frac, keys = job.keys.slice();
let s = job.seed >>> 0;
const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
for (let i = 0; i < job.inserts; i++) {
  const roll = rnd();
  const pos = roll < 0.2 ? 0 : roll < 0.4 ? keys.length : Math.floor(rnd() * (keys.length + 1));
  keys.splice(pos, 0, F.between(pos > 0 ? keys[pos - 1] : null, pos < keys.length ? keys[pos] : null));
}
process.stdout.write(JSON.stringify(keys));
"""


def _js_keys(keys: list[str], seed: int, inserts: int) -> list[str]:
    run = subprocess.run([NODE, "-e", FRAC_JS, str(DESIGN)], input=json.dumps({"keys": keys, "seed": seed, "inserts": inserts}),
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-3000:]
    return json.loads(run.stdout)


def test_the_three_files_are_there_and_are_plain_strict_scripts():
    for name in ("hd-math.js", "hd-core.js", "hd-net.js"):
        text = (DESIGN / name).read_text(encoding="utf-8")
        assert "'use strict';" in text and text.rstrip().endswith("})();"), name
        assert "eval(" not in text and "new Function" not in text, name          # strict CSP: script-src 'self'
        assert "import " not in text.split("(function () {", 1)[0], name          # no modules, no build step
    net = (DESIGN / "hd-net.js").read_text(encoding="utf-8")
    assert "'hoola-key.' + tk" in net and "'/api/design/ws?file='" in net        # the token rides as a subprotocol
    assert "token=" not in net and "key=" not in net                              # ...never in the address


@needs_node
def test_client_core_node_suite():
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=300)
    tail = (run.stdout + "\n" + run.stderr)[-6000:]
    assert run.returncode == 0, tail
    assert "# fail 0" in run.stdout, tail
    passed = [line for line in run.stdout.splitlines() if line.startswith("# pass ")]
    assert passed and int(passed[0].split()[2]) >= 24, tail
    for line in run.stdout.splitlines():                                          # the measured numbers, in the CI log
        if line.strip().startswith(("perf:", "frac:", "sync:")):
            print(line.strip())


@needs_node
def test_browser_keys_and_server_keys_order_the_same_and_accept_each_other():
    fracidx = pytest.importorskip("app.design.fracidx")
    rnd = random.Random(777)
    # the server starts a parent (a new file, a template, the AI endpoint) ...
    keys: list[str] = []
    for _ in range(40):
        pos = rnd.randint(0, len(keys))
        keys.insert(pos, fracidx.between(keys[pos - 1] if pos else None, keys[pos] if pos < len(keys) else None))
    assert keys == sorted(keys)
    # ... the browser inserts 1,500 more among them (head, tail and in between) ...
    mixed = _js_keys(keys, seed=11, inserts=1500)
    assert len(mixed) == len(keys) + 1500 and len(set(mixed)) == len(mixed)
    assert mixed == sorted(mixed), "plain string order is the order, in both languages"
    assert all(fracidx.valid(k) for k in mixed), "every key the browser makes is one the server can work with"
    # ... the server inserts between ANY two neighbours of that mix (and at both ends) ...
    again = list(mixed)
    for _ in range(600):
        pos = rnd.randint(0, len(again))
        a, b = (again[pos - 1] if pos else None), (again[pos] if pos < len(again) else None)
        k = fracidx.between(a, b)
        assert (a is None or a < k) and (b is None or k < b), (a, k, b)
        again.insert(pos, k)
    assert again == sorted(again)
    # ... and the browser carries on from there.
    final = _js_keys(again, seed=12, inserts=800)
    assert final == sorted(final) and len(set(final)) == len(final)
    assert all(fracidx.valid(k) for k in final)
    assert max(len(k) for k in final) < 64                                        # nowhere near the server's 4096 limit
    # a brand-new parent filled only by the browser: 5,000 appends stay tiny
    assert max(len(k) for k in _js_keys([], seed=1, inserts=0) + _js_keys(["V"], seed=3, inserts=300)) < 40


@needs_node
def test_the_contract_server_of_the_js_suite_is_the_real_server(tmp_path):
    """The convergence test in the node suite plays three editors against a small JavaScript server. That only proves
    something if it rules like the real one: replay everything it saw through app.design.doc.Doc and compare every
    verdict and the final document."""
    doc_mod = pytest.importorskip("app.design.doc")
    for seed in (3, 8, 21):
        out = tmp_path / f"run{seed}.json"
        run = subprocess.run([NODE, "--test-name-pattern", "sync:", str(JS_TEST)], capture_output=True, text=True, timeout=300,
                             env={"PATH": str(Path(NODE).parent), "HD_SEED": str(seed), "HD_DUMP": str(out)})
        assert run.returncode == 0, (run.stdout + run.stderr)[-3000:]
        log = json.loads(out.read_text())
        doc = doc_mod.Doc(log["start"]["nodes"])
        assert len(log["batches"]) > 100
        rejected_total = 0
        for i, batch in enumerate(log["batches"]):
            rejected = [k for k, op in enumerate(batch["ops"]) if doc.apply(op) == doc_mod.REJECTED]
            assert rejected == batch["rejected"], f"seed {seed}, batch {i}: {batch['ops']}"
            rejected_total += len(rejected)
        assert rejected_total > 0
        assert doc.nodes == log["end"]["nodes"], f"seed {seed}: final documents differ"
