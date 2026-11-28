"""VIRTUALIZATION DESK: the Virtualization / Hypervisor Engineer's own section, built like the finance desks - its own chat (kind
'virt') with the desk block + the virtualization tool in view; container configs (Kubernetes, Compose, docker run, OCI config.json,
Dockerfiles) against the Pod Security Standards with the hardened lines; seccomp profiles checked and made from a strace; libvirt
VM XML checked (DOCTYPE refused); host capacity and failover worked out; CPU flags compared (x86-64 levels); the CI workflow is
valid YAML; walked in a browser."""
from __future__ import annotations

import json
import os

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

K8S = """apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  template:
    spec:
      hostNetwork: true
      volumes: [{name: sock, hostPath: {path: /var/run/docker.sock}}, {name: tmp, emptyDir: {}}]
      containers:
      - name: app
        image: nginx
        securityContext: {capabilities: {add: [SYS_ADMIN]}}
        volumeMounts: [{name: sock, mountPath: /var/run/docker.sock}]
---
apiVersion: v1
kind: Pod
metadata: {name: good}
spec:
  automountServiceAccountToken: false
  securityContext: {runAsNonRoot: true, runAsUser: 1000, seccompProfile: {type: RuntimeDefault}}
  containers:
  - name: a
    image: registry.example/app@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: [ALL], add: [NET_BIND_SERVICE]}}
    resources: {limits: {memory: 64Mi, cpu: 100m}}
"""

DOMAIN = """<domain type='kvm'><name>win11-dev</name><memory unit='GiB'>32</memory><vcpu>8</vcpu>
<os><type arch='x86_64' machine='pc-i440fx-8.2'>hvm</type></os>
<cpu mode='host-passthrough'><topology sockets='4' cores='2' threads='2'/></cpu>
<devices><disk type='file' device='disk'><driver name='qemu' type='qcow2' cache='unsafe'/><source file='/var/lib/libvirt/images/win.qcow2'/><target dev='hda' bus='ide'/></disk>
<interface type='network'><source network='default'/><model type='e1000'/></interface>
<graphics type='vnc' port='-1' listen='0.0.0.0'/></devices><seclabel type='none'/></domain>"""

GOOD_DOMAIN = """<domain type='kvm'><name>db1</name><memory unit='GiB'>8</memory><vcpu>4</vcpu>
<os firmware='efi'><type arch='x86_64' machine='q35'>hvm</type><loader secure='yes'/></os>
<cpu mode='host-model'><topology sockets='1' cores='4' threads='1'/></cpu>
<devices><disk type='file' device='disk'><driver name='qemu' type='raw' cache='none' io='native' discard='unmap'/><source file='/v/db1.raw'/><target dev='vda' bus='virtio'/></disk>
<interface type='bridge'><source bridge='br0'/><model type='virtio'/><driver name='vhost' queues='4'/></interface>
<graphics type='vnc' listen='127.0.0.1'/><rng model='virtio'><backend model='random'>/dev/urandom</backend></rng>
<channel type='unix'><target type='virtio' name='org.qemu.guest_agent.0'/></channel><watchdog model='i6300esb' action='reset'/></devices></domain>"""

PLAN = """host, h1, 16, 128, 2
host, h2, 16, 128, 2
host, h3, 16, 128
vm, db, 8, 96
vm, web1, 4, 16
vm, web2, 4, 16
vm, web3, 4, 16
vm, cache, 2, 48
vm, big, 4, 70
"""

V1 = "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx lm"
V3 = V1 + " cx16 lahf_lm popcnt sse4_1 sse4_2 ssse3 avx avx2 bmi1 bmi2 f16c fma abm movbe xsave aes vmx ept vpid"
V4 = V3 + " avx512f avx512bw avx512cd avx512dq avx512vl avx512_vnni"
CPUS = f"""## node-a
model name : Intel(R) Xeon(R) Gold 6338
vendor_id : GenuineIntel
flags : {V4}
Vulnerability Mds: Vulnerable: Clear CPU buffers attempted, no microcode
## node-b
vendor_id : GenuineIntel
flags : {V3}
"""

TRACE = """12345 execve("/bin/app", ["app"], 0x7ffd) = 0
12345 brk(NULL) = 0x55
[pid 12346] openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
[pid 12346] <... read resumed>"abc", 3) = 3
12345 clone3({flags=CLONE_VM}, 88) = 12346
12345 epoll_wait(4, [], 64, 1000) = 0
12345 ptrace(PTRACE_TRACEME) = 0
12345 not_a_call(1) = -1
+++ exited with 0 +++
"""


@pytest.fixture
def vtc(env):
    from app import virtchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "hypervisor_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_containers_against_pod_security():
    from app.virtdesk import container as C
    r = C.check(K8S)
    assert r["format"] == "kubernetes" and len(r["containers"]) == 2 and r["meets"] == 1 and r["level"] == "privileged"
    app, good = r["containers"]
    texts = " ".join(i["text"] for i in app["issues"])
    assert app["level"] == "privileged" and "runtime's socket" in texts and "SYS_ADMIN" in texts and "host's network" in texts
    assert good["level"] == "restricted" and not [i for i in good["issues"] if i["sev"] in ("bad", "warn")]
    assert "allowPrivilegeEscalation: false" in app["fix"] and "drop: [\"ALL\"]" in app["fix"] and yaml.safe_load(app["fix"])["securityContext"]["runAsUser"] == 10001
    assert "SYS_ADMIN" in app["caps_effective"]
    # baseline met, restricted not: no seccomp, not non-root
    mid = C.check("apiVersion: v1\nkind: Pod\nmetadata: {name: m}\nspec:\n  containers:\n  - {name: c, image: 'x:1'}\n")
    assert mid["containers"][0]["level"] == "baseline" and mid["meets"] == 0
    assert C.check("apiVersion: v1\nkind: Pod\nmetadata: {name: m}\nspec:\n  containers:\n  - {name: c, image: 'x:1'}\n", target="baseline")["meets"] == 1
    d = C.check("docker run -d --name x --privileged -v /:/host -p 8080:80 nginx:1.25")
    c = d["containers"][0]
    assert d["format"] == "docker" and c["name"] == "docker run --name x" and c["level"] == "privileged" and c["caps_effective"] == ["ALL"]
    assert any("whole host disk" in i["text"] for i in c["issues"]) and "--cap-drop ALL" in c["fix"] and "-p 8080" in c["fix"]
    ok = C.check("docker run --rm --user 10001 --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 100 -m 100m "
                 "--cpus 1 alpine:3.20@sha256:" + "a" * 64 + " sh")
    assert ok["containers"][0]["level"] == "restricted" and ok["counts"]["bad"] == 0 and ok["containers"][0]["caps_effective"] == []
    cp = C.check('services:\n  db:\n    image: postgres\n    security_opt: ["seccomp:unconfined"]\n    volumes: ["/var/run/docker.sock:/var/run/docker.sock"]\n')
    assert cp["format"] == "compose" and cp["containers"][0]["level"] == "privileged" and cp["counts"]["bad"] >= 2
    oci = C.check(json.dumps({"ociVersion": "1.0.2", "process": {"user": {"uid": 0}, "capabilities": {"bounding": ["CAP_CHOWN", "CAP_SYS_ADMIN"]}},
                              "root": {"readonly": True}, "linux": {"namespaces": [{"type": "pid"}, {"type": "mount"}, {"type": "network"}, {"type": "ipc"}]}}))
    t = " ".join(i["text"] for i in oci["containers"][0]["issues"])
    assert oci["format"] == "oci" and "SYS_ADMIN" in t and "No linux.seccomp" in t and "user 0" in t
    df = C.check("FROM python:latest\nENV API_KEY=abc\nRUN curl -s https://x | sh\nCOPY . .\nCMD python app.py\n")
    t = " ".join(i["text"] for i in df["issues"])
    assert df["format"] == "dockerfile" and "No USER" in t and "API_KEY" in t and "runs it in one step" in t and df["counts"]["bad"] == 2
    good_df = C.check("FROM python:3.13-slim@sha256:" + "b" * 64 + "\nRUN useradd -u 10001 app\nUSER 10001\nHEALTHCHECK CMD [\"true\"]\nCMD [\"python\", \"a.py\"]\n")
    assert good_df["issues"] == []
    for bad in ("", "hello world", "{not json", "apiVersion: v1\nkind: ConfigMap\nmetadata: {name: x}\n"):
        with pytest.raises(C.ContainerError):
            C.check(bad)


def test_seccomp_check_and_make():
    from app.virtdesk import seccomp as S
    g = S.generate(TRACE)
    p = json.loads(g["profile"])
    allow = p["syscalls"][0]["names"]
    assert g["kind"] == "strace" and g["unknown"] == ["not_a_call"] and p["defaultAction"] == "SCMP_ACT_ERRNO"
    assert {"execve", "brk", "openat", "read", "epoll_wait", "ptrace"} <= set(allow) and "clone3" not in allow
    clone = next(r for r in p["syscalls"] if r["names"] == ["clone"])
    assert clone["args"][0]["value"] == 0x7E020000 and clone["args"][0]["op"] == "SCMP_CMP_MASKED_EQ"
    assert next(r for r in p["syscalls"] if r["names"] == ["clone3"])["errnoRet"] == 38
    assert any("ptrace" in i["text"] for i in g["issues"])
    c = S.check(g["profile"])
    assert c["mode"] == "allow-list" and c["allowed"] == g["allowed"] and any(r["name"] == "ptrace" for r in c["risky"])
    deny = S.check(json.dumps({"defaultAction": "SCMP_ACT_ALLOW", "syscalls": [{"names": ["mount", "ptrace"], "action": "SCMP_ACT_ERRNO"}]}))
    assert deny["mode"] == "deny-list" and deny["allowed"] == deny["of"] - 2 and deny["counts"]["bad"] >= 10
    assert any(r["name"] == "bpf" for r in deny["risky"]) and not any(r["name"] == "mount" for r in deny["risky"])
    cond = S.check(json.dumps({"defaultAction": "SCMP_ACT_ERRNO", "syscalls": [
        {"names": ["read", "write"], "action": "SCMP_ACT_ALLOW"}, {"names": ["mount"], "action": "SCMP_ACT_ALLOW", "includes": {"caps": ["CAP_SYS_ADMIN"]}}]}))
    assert cond["conditional"] == [{"name": "mount", "when": "only with CAP_SYS_ADMIN"}] and cond["counts"]["bad"] == 0
    tab = "% time seconds usecs/call calls errors syscall\n 45.00 0.000045 3 15 read\n 20.00 0.000020 2 10 2 openat\n100.00 0.000100 25 2 total"
    assert S.read_trace(tab, "x86_64")[0] == {"read": 15, "openat": 10}
    assert S.read_trace("type=SECCOMP msg=audit(1.1:2): syscall=165 compat=0", "x86_64")[0] == {"mount": 1}
    assert S.read_trace("type=SECCOMP msg=audit(1.1:2): syscall=40", "aarch64")[0] == {"mount": 1}
    a = json.loads(S.generate("openat read write", "aarch64")["profile"])
    assert a["architectures"] == ["SCMP_ARCH_AARCH64"] and "arch_prctl" not in a["syscalls"][0]["names"]
    with pytest.raises(S.SeccompError):
        S.check('{"syscalls": []}')
    with pytest.raises(S.SeccompError):
        S.generate("", "x86_64")


def test_vm_capacity_cpu_and_ci():
    from app.virtdesk import ci, cpu, domain, plan
    r = domain.check(DOMAIN)
    t = {i["text"][:40]: i["sev"] for i in r["issues"]}
    bad = [i["text"] for i in r["issues"] if i["sev"] == "bad"]
    assert r["vcpus"] == 8 and r["memory_gib"] == 32 and r["windows"] and r["migratable"] == "only to identical CPUs"
    assert any("topology gives 16" in x for x in bad) and any("unsafe" in x for x in bad) and any("0.0.0.0" in x for x in bad) and any("sVirt" in x for x in bad)
    assert any("IDE" in x for x in t) and any("e1000" in x for x in t)
    g = domain.check(GOOD_DOMAIN)
    assert g["counts"]["bad"] == 0 and g["counts"]["warn"] == 0 and g["secure_boot"] and g["firmware"] == "UEFI" and g["migratable"] == "yes"
    with pytest.raises(domain.DomainError):
        domain.check('<!DOCTYPE d [<!ENTITY x "y">]><domain><name>&x;</name></domain>')
    with pytest.raises(domain.DomainError):
        domain.check("<network/>")
    p = plan.plan(PLAN)
    assert p["mode"] == "worked out" and not p["unplaced"] and p["survives"] is False
    assert {h["name"]: h["vms"] for h in p["hosts"]}["h1"] == ["db"] and sorted(p["numa_span"]) == ["big", "db"]
    assert p["totals"]["vm_ram"] == 262 and all(h["ram_cap"] == 124 for h in p["hosts"])
    small = plan.plan("".join(f"host, h{i}, 16, 128\n" for i in range(4)) + "".join(f"vm, v{i}, 2, 16\n" for i in range(12)))
    assert small["survives"] is True and len(small["fail"]) == 4 and all(not f["stranded"] for f in small["fail"])
    assert plan.plan("".join(f"host, h{i}, 16, 128\n" for i in range(4)) + "".join(f"vm, v{i}, 2, 16\n" for i in range(12)), failures=2)["survives"] is True
    mine = plan.plan("host, a, 8, 64\nhost, b, 8, 64\nvm, x, 40, 32, a\nvm, y, 2, 8, b\n", failures=0)
    assert mine["mode"] == "yours" and any("40 vCPUs on 8 cores" in i["text"] and i["sev"] == "bad" for i in mine["issues"]) and mine["survives"] is None
    with pytest.raises(plan.PlanError):
        plan.plan("vm, x, 1, 1\n")
    with pytest.raises(plan.PlanError):
        plan.plan("host, a, 8, 64\nvm, x, 1, 1, nowhere\n")
    c = cpu.compare(CPUS)
    assert c["common_level"] == "x86-64-v3" and [h["level"] for h in c["hosts"]] == ["x86-64-v4", "x86-64-v3"] and not c["same"]
    assert "avx512f" in c["differ"] and any("Mds" in i["text"] and i["sev"] == "bad" for i in c["issues"])
    assert "policy='disable' name='avx512f'" in c["xml"]
    assert cpu.compare(f"a: {V3}\nb: {V3}")["same"] is True
    one = cpu.compare(f"flags : {V1} cx16 lahf_lm popcnt sse4_1 sse4_2 ssse3")
    assert one["hosts"][0]["level"] == "x86-64-v2" and any("no vmx / svm" in i["text"] for i in one["issues"])
    mixed = cpu.compare(f"## a\nvendor_id : GenuineIntel\nflags : {V3}\n## b\nvendor_id : AuthenticAMD\nflags : {V3.replace('vmx ept', 'svm npt')}\n")
    assert any("different CPU vendors" in i["text"] for i in mixed["issues"])
    w = ci.workflow(image="ghcr.io/me/app:1.4", port=8080, health="http://127.0.0.1:8080/health", seccomp_file="security/seccomp.json")
    y = yaml.safe_load(w["yaml"])
    assert set(y["jobs"]) == {"hardened-run", "seccomp-log"} and y["permissions"] == {"contents": "read"}
    run = y["jobs"]["hardened-run"]["steps"][2]["run"]
    assert "--cap-drop ALL" in run and "--security-opt no-new-privileges" in run and "seccomp=security/seccomp.json" in run and "--user 10001:10001" in run
    assert "SCMP_ACT_LOG" in w["yaml"] and "127.0.0.1:8080:8080" in run
    assert set(yaml.safe_load(ci.workflow()["yaml"])["jobs"]) == {"hardened-run"}
    for bad in (dict(image="Bad Image!"), dict(seccomp_file="../../etc/passwd"), dict(health="rm -rf / ; curl evil"), dict(uid=0),
                dict(health="http://127.0.0.1/h"), dict(memory="lots")):
        with pytest.raises(ci.CiError):
            ci.workflow(**bad)


def test_hire_chat_wiring_store_and_guards(vtc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert vtc.summary(T)["hired"] is False and "Hire me from AI Employees" in vtc.greeting(T)
    with pytest.raises(PermissionError):
        vtc.do(T, "add", {"kind": "container", "text": K8S})
    _hire()
    d = vtc.summary(T)
    assert d["hired"] and "never changes anything on your hosts" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"containers", "settings"}
    chat = vtc.current(T)
    assert vtc.is_virt(chat["id"]) and vtc.owns(T, chat["id"]) and "<virt_desk>" in vtc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_vtc.is_virt(conversation_id)" in s_ and "adm.admit_families(_vtc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"virt"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/virtualization")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "hvdesk.js" in r.text
    html = (root / "server/app/static/console/hvdesk.html").read_text()
    for x in ("chatkit.js", "hvdesk.css", "hvdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/virtualization')" in (root / "server/app/static/console/v2.js").read_text()
    assert "hypervisor_eng: 'hvdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["hypervisor_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["virt_desk"] in vtc.FAMILIES and "virt_desk" in HANDLERS
    c = vtc.do(T, "add", {"kind": "container", "text": K8S})
    assert c["number"] == "C-0001" and c["brief"]["bad"] and c["brief"]["level"] == "privileged"
    assert any(n["go"] == "containers/" + c["id"] for n in vtc.summary(T)["desk"]["needs"])
    assert vtc.summary(T)["desk"]["containers"]["level"] == "privileged"
    tr = vtc.do(T, "add", {"kind": "trace", "text": TRACE})
    assert tr["number"] == "T-0001" and json.loads(tr["result"]["profile"])["defaultAction"] == "SCMP_ACT_ERRNO" and not tr["brief"]["bad"]
    sc = vtc.do(T, "add", {"kind": "seccomp", "text": tr["result"]["profile"]})
    assert sc["number"] == "S-0001" and sc["brief"]["mode"] == "allow-list"
    dm = vtc.do(T, "add", {"kind": "domain", "text": DOMAIN})
    assert dm["number"] == "V-0001" and dm["title"] == "VM win11-dev" and dm["brief"]["bad"]
    pl = vtc.do(T, "add", {"kind": "plan", "text": PLAN})
    assert pl["brief"]["survives"] is False and vtc.summary(T)["desk"]["capacity"]["survives"] is False
    cu = vtc.do(T, "add", {"kind": "cpu", "text": CPUS})
    assert cu["brief"]["level"] == "x86-64-v3"
    st = vtc.do(T, "settings", {"vcpu_ratio": "2", "failures": "2", "image": "ghcr.io/me/app:1.4", "port": "8080",
                                "health": "http://127.0.0.1:8080/health", "seccomp_file": "security/seccomp.json", "net_bind": "1"})
    assert st["vcpu_ratio"] == 2 and st["failures"] == 2 and st["net_bind"] is True
    w = vtc.do(T, "ci", {})
    assert "ghcr.io/me/app:1.4" in w["yaml"] and "--cap-add NET_BIND_SERVICE" in w["yaml"] and yaml.safe_load(w["yaml"])
    pl2 = vtc.do(T, "add", {"kind": "plan", "text": PLAN})
    assert pl2["result"]["ratio"] == 2 and pl2["result"]["failures"] == 2
    vtc.forget(T)
    assert "ghcr.io/me/app:1.4" in vtc.block(T) and "2.0 vCPUs per core" in vtc.block(T)
    mk = vtc.do(T, "mark", {"id": c["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "containers/" + c["id"] for n in vtc.summary(T)["desk"]["needs"])
    # the tool
    import asyncio
    from app.agent import virt_tools as VT
    from app.agent.tools import Ctx
    out = asyncio.run(VT.virt_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="container", text=K8S))
    assert out["level"] == "privileged" and out["containers"][0]["fix"].startswith("securityContext:")
    out = asyncio.run(VT.virt_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/hardened-container.yml"
    # guards
    with pytest.raises(PermissionError):
        vtc.do(T, "settings", {"image": "my password is hunter2"})
    assert vtc.do(T, "add", {"kind": "container", "text": "docker run -e PASSWORD=hunter2 nginx:1.27"})["kind"] == "container"
    for bad in ({"port": "70000"}, {"arch": "sparc"}, {"seccomp_file": "/etc/shadow"}, {"vcpu_ratio": "100"}):
        with pytest.raises(vtc.HvDeskError):
            vtc.do(T, "settings", bad)
    with pytest.raises(vtc.HvDeskError):
        vtc.do(T, "add", {"kind": "domain", "text": "<!DOCTYPE x><domain/>"})
    with pytest.raises(vtc.HvDeskError):
        vtc.do(T, "add", {"kind": "plan", "text": ""})
    with pytest.raises(vtc.HvDeskError):
        vtc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "hypervisor_eng")
    assert vtc.do(T, "get", {"id": c["id"]})["id"] == c["id"] and vtc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        vtc.do(T, "add", {"kind": "container", "text": K8S})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def hv_server(vtc, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(vtc, hv_server):
    base, browser, key = hv_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def submit(pg, form, text, sel):
        pg.fill(f"form[data-form={form}] [name=text]", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/virtualization")
    pg.wait_for_selector(".hvk-starts", timeout=20000)
    snap(pg, "hv-today-empty-1440")
    go(pg, "#/containers", "form[data-form=container]")
    assert pg.locator(".hvk-ladder > div").count() == 3
    submit(pg, "container", K8S, ".hvk-ct")
    assert pg.locator(".hvk-ct").count() == 2 and "Deployment/web app" in pg.inner_text("#hvPage")
    pg.click(".hvk-ct summary")
    pg.wait_for_selector(".hvk-ct[open] .hvk-fix", timeout=10000)
    assert "runAsNonRoot: true" in pg.inner_text(".hvk-ct[open] .hvk-fix")
    snap(pg, "hv-container-1440")
    go(pg, "#/seccomp", "form[data-form=trace]")
    submit(pg, "trace", TRACE, "[data-dlprof]")
    assert "SCMP_ACT_ERRNO" in pg.inner_text("#hvPage") and "ptrace" in pg.inner_text("#hvPage")
    snap(pg, "hv-trace-1440")
    go(pg, "#/seccomp", "form[data-form=seccomp]")
    submit(pg, "seccomp", json.dumps({"defaultAction": "SCMP_ACT_ALLOW", "syscalls": [{"names": ["mount"], "action": "SCMP_ACT_ERRNO"}]}), ".hvk-big2")
    assert "deny-list" in pg.inner_text(".hvk-big2")
    snap(pg, "hv-seccomp-1440")
    go(pg, "#/vms", "form[data-form=domain]")
    submit(pg, "domain", DOMAIN, ".ar-facts")
    assert "only to identical CPUs" in pg.inner_text(".ar-facts") and "0.0.0.0" in pg.inner_text("#hvPage")
    snap(pg, "hv-vm-1440")
    go(pg, "#/capacity", ".hvk-seg")
    submit(pg, "plan", PLAN, ".hvk-hosts")
    assert pg.locator(".hvk-host").count() == 3 and "At risk" in pg.inner_text(".cs-hero") and pg.locator(".hvk-vms span.numa").count() == 2
    snap(pg, "hv-plan-1440")
    go(pg, "#/capacity", ".hvk-seg")
    pg.click("[data-cap=cpu]")
    pg.wait_for_selector("form[data-form=cpu]", timeout=10000)
    submit(pg, "cpu", CPUS, ".hvk-vul")
    assert "x86-64-v3" in pg.inner_text("#hvPage") and "avx512f" in pg.inner_text("#hvPage")
    snap(pg, "hv-cpu-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=image]", "ghcr.io/me/app:1.4")
    pg.fill("form[data-form=settings] [name=port]", "8080")
    pg.fill("form[data-form=settings] [name=health]", "http://127.0.0.1:8080/health")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=hardened-container.yml")
    assert "ghcr.io/me/app:1.4" in pg.inner_text("#hvPage") and "--cap-drop ALL" in pg.inner_text("#hvPage")
    snap(pg, "hv-ci-1440")
    go(pg, "#/today", ".hvk-list")
    assert "Privileged" in pg.inner_text(".cs-hero") and "At risk" in pg.inner_text(".cs-hero")
    snap(pg, "hv-today-1440")
    for route, sel in (("#/today", ".hvk-list"), ("#/containers", ".hvk-item"), ("#/seccomp", ".hvk-item"), ("#/vms", ".hvk-item"),
                       ("#/capacity", ".hvk-item"), ("#/ci", "text=hardened-container.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#hvPage *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    go(pg, "#/capacity", ".hvk-item")
    pg.locator(".hvk-item").last.click()
    pg.wait_for_selector(".hvk-hosts", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "hv-plan-390")
    assert not errs, errs
