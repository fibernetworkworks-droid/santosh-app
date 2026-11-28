"""Container configs checked against the Kubernetes Pod Security Standards (baseline + restricted, as written in the Kubernetes
docs) and the usual hardening points: Kubernetes YAML (Pod, Deployment, StatefulSet, DaemonSet, ReplicaSet, Job, CronJob), Docker
Compose files, `docker run` / `podman run` command lines, OCI runtime config.json files and Dockerfiles. Every container gets the
level it meets, each finding, and the hardened lines to put in its place. Pasted text is data."""
from __future__ import annotations

import json
import re
import shlex
from typing import Any


class ContainerError(ValueError):
    pass


# Kubernetes Pod Security Standards, baseline: capabilities that may be added; restricted: only NET_BIND_SERVICE after drop ALL.
BASE_CAPS = {"AUDIT_WRITE", "CHOWN", "DAC_OVERRIDE", "FOWNER", "FSETID", "KILL", "MKNOD", "NET_BIND_SERVICE", "SETFCAP", "SETGID",
             "SETPCAP", "SETUID", "SYS_CHROOT"}
DOCKER_DEFAULT = BASE_CAPS | {"NET_RAW"}
DANGER = {"SYS_ADMIN": "nearly root on the host: mount, namespaces, many escapes", "SYS_PTRACE": "can read and change other processes",
          "SYS_MODULE": "can load kernel modules", "NET_ADMIN": "can change the host's network if it shares it",
          "SYS_RAWIO": "raw access to devices and memory", "DAC_READ_SEARCH": "can read any file by handle (the old shocker escape)",
          "SYS_BOOT": "can reboot", "SYS_TIME": "can set the host clock", "BPF": "can load eBPF programs", "PERFMON": "can read kernel events",
          "SYS_RESOURCE": "can lift resource limits", "MAC_ADMIN": "can change security policy", "MAC_OVERRIDE": "can ignore security policy",
          "SYSLOG": "can read the kernel log", "NET_RAW": "raw sockets: spoofing and ARP tricks on the network", "ALL": "every capability"}
SAFE_SYSCTLS = {"kernel.shm_rmid_forced", "net.ipv4.ip_local_port_range", "net.ipv4.ip_unprivileged_port_start", "net.ipv4.tcp_syncookies",
                "net.ipv4.ping_group_range", "net.ipv4.ip_local_reserved_ports", "net.ipv4.tcp_keepalive_time", "net.ipv4.tcp_fin_timeout",
                "net.ipv4.tcp_keepalive_intvl", "net.ipv4.tcp_keepalive_probes"}
RESTRICTED_VOLUMES = {"configMap", "csi", "downwardAPI", "emptyDir", "ephemeral", "persistentVolumeClaim", "projected", "secret"}
SOCKETS = ("/var/run/docker.sock", "/run/docker.sock", "/run/containerd/containerd.sock", "/var/run/containerd/containerd.sock",
           "/var/run/crio/crio.sock", "/run/crio/crio.sock", "/run/podman/podman.sock", "/var/run/podman/podman.sock")
HOST_DIRS = {"/": "the whole host disk", "/etc": "the host's config and passwords", "/proc": "the host's processes", "/sys": "the host's kernel settings",
             "/dev": "the host's devices", "/boot": "the host's kernel", "/root": "root's home", "/home": "every user's home",
             "/var/lib/kubelet": "the kubelet's secrets", "/var/lib/docker": "every container's files", "/var/log": "the host's logs"}
WORKLOADS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "ReplicationController", "Job", "CronJob"}


def _cap(c: Any) -> str:
    s = str(c or "").strip().upper()
    return s[4:] if s.startswith("CAP_") else s


def _new(name: str, source: str) -> dict[str, Any]:
    return {"name": name, "source": source, "image": "", "privileged": False, "cap_add": [], "cap_drop": [], "caps_set": None,
            "user": None, "non_root": None, "read_only": None, "no_new_privs": None, "seccomp": None, "apparmor": None, "selinux": None,
            "host_network": False, "host_pid": False, "host_ipc": False, "host_userns": False, "host_paths": [], "host_ports": [],
            "devices": [], "limits": {}, "proc_mount": None, "sysctls": [], "volumes": [], "sa_token": None, "init": False}


# ---------------------------------------------------------------- reading each format
def _k8s(docs: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in docs:
        if not isinstance(d, dict):
            continue
        if d.get("kind") == "List":
            out += _k8s(d.get("items") or [])
            continue
        kind = d.get("kind")
        if kind not in WORKLOADS:
            continue
        meta = d.get("metadata") or {}
        spec = d.get("spec") or {}
        ann = dict(meta.get("annotations") or {})
        if kind == "CronJob":
            spec = ((spec.get("jobTemplate") or {}).get("spec") or {})
        if kind != "Pod":
            tmpl = spec.get("template") or {}
            ann.update(((tmpl.get("metadata") or {}).get("annotations")) or {})
            spec = tmpl.get("spec") or {}
        psc = spec.get("securityContext") or {}
        vols = spec.get("volumes") or []
        vtypes: list[tuple[str, str]] = []
        hostp: dict[str, str] = {}
        for v in vols:
            if not isinstance(v, dict):
                continue
            t = next((k for k in v if k != "name"), "")
            vtypes.append((str(v.get("name") or ""), t))
            if t == "hostPath":
                hostp[str(v.get("name") or "")] = str((v.get("hostPath") or {}).get("path") or "")
        for group in ("initContainers", "containers", "ephemeralContainers"):
            for c in spec.get(group) or []:
                if not isinstance(c, dict):
                    continue
                n = str(c.get("name") or "container")
                x = _new(f"{kind}/{meta.get('name') or '?'} {n}" + (" (init)" if group == "initContainers" else ""), "kubernetes")
                csc = c.get("securityContext") or {}
                x["image"] = str(c.get("image") or "")
                x["privileged"] = bool(csc.get("privileged"))
                caps = csc.get("capabilities") or {}
                x["cap_add"] = [_cap(a) for a in caps.get("add") or []]
                x["cap_drop"] = [_cap(a) for a in caps.get("drop") or []]
                uid = csc.get("runAsUser", psc.get("runAsUser"))
                x["user"] = None if uid is None else str(uid)
                nr = csc.get("runAsNonRoot", psc.get("runAsNonRoot"))
                x["non_root"] = None if nr is None else bool(nr)
                x["read_only"] = csc.get("readOnlyRootFilesystem")
                ape = csc.get("allowPrivilegeEscalation")
                x["no_new_privs"] = None if ape is None else not bool(ape)
                sp = csc.get("seccompProfile") or psc.get("seccompProfile") or {}
                t = str(sp.get("type") or "")
                x["seccomp"] = {"RuntimeDefault": "runtime", "Localhost": "localhost", "Unconfined": "unconfined"}.get(t)
                ap = csc.get("appArmorProfile") or psc.get("appArmorProfile") or {}
                at = str(ap.get("type") or "")
                old = str(ann.get(f"container.apparmor.security.beta.kubernetes.io/{n}") or "")
                x["apparmor"] = ("unconfined" if at == "Unconfined" or old == "unconfined" else
                                 "runtime" if at == "RuntimeDefault" or old == "runtime/default" else
                                 "localhost" if at == "Localhost" or old.startswith("localhost/") else None)
                se = csc.get("seLinuxOptions") or psc.get("seLinuxOptions") or {}
                x["selinux"] = str(se.get("type") or "") or None
                x["host_network"] = bool(spec.get("hostNetwork"))
                x["host_pid"] = bool(spec.get("hostPID"))
                x["host_ipc"] = bool(spec.get("hostIPC"))
                x["host_userns"] = False
                for vm in c.get("volumeMounts") or []:
                    if isinstance(vm, dict) and vm.get("name") in hostp:
                        x["host_paths"].append({"host": hostp[vm["name"]], "path": str(vm.get("mountPath") or ""), "ro": bool(vm.get("readOnly"))})
                x["host_ports"] = [int(p["hostPort"]) for p in c.get("ports") or [] if isinstance(p, dict) and p.get("hostPort")]
                lim = ((c.get("resources") or {}).get("limits")) or {}
                x["limits"] = {k: str(lim[k]) for k in ("cpu", "memory") if k in lim}
                x["proc_mount"] = csc.get("procMount")
                x["sysctls"] = [str(s.get("name")) for s in psc.get("sysctls") or [] if isinstance(s, dict)]
                x["volumes"] = [t for _, t in vtypes]
                x["sa_token"] = spec.get("automountServiceAccountToken")
                out.append(x)
    return out


def _bindspec(v: Any) -> dict[str, Any] | None:
    if isinstance(v, dict):
        if str(v.get("type") or "bind") != "bind" and not str(v.get("source") or "").startswith("/"):
            return None
        src = str(v.get("source") or "")
        return {"host": src, "path": str(v.get("target") or ""), "ro": bool(v.get("read_only"))} if src.startswith("/") else None
    s = str(v)
    parts = s.split(":")
    if len(parts) >= 2 and (parts[0].startswith("/") or parts[0].startswith("~") or parts[0].startswith(".")):
        return {"host": parts[0], "path": parts[1], "ro": len(parts) > 2 and "ro" in parts[2].split(",")}
    return None


def _secopts(x: dict[str, Any], opts: list[str]) -> None:
    for o in opts:
        o = str(o).strip()
        k, _, v = o.replace("=", ":", 1).partition(":")
        k = k.strip()
        if k == "no-new-privileges":
            x["no_new_privs"] = v.strip().lower() not in ("false", "0")
        elif k == "seccomp":
            x["seccomp"] = "unconfined" if v.strip() == "unconfined" else "localhost"
        elif k == "apparmor":
            x["apparmor"] = "unconfined" if v.strip() == "unconfined" else "localhost"
        elif k == "label":
            x["selinux"] = "disabled" if v.strip() == "disable" else (v.split(":", 1)[1] if v.startswith("type:") else x["selinux"])


def _compose(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for name, s in (doc.get("services") or {}).items():
        if not isinstance(s, dict):
            continue
        x = _new(f"service {name}", "compose")
        x["image"] = str(s.get("image") or ("(built from " + str((s.get("build") or {}).get("context", s.get("build")) if isinstance(s.get("build"), dict) else s.get("build")) + ")" if s.get("build") else ""))
        x["privileged"] = bool(s.get("privileged"))
        x["cap_add"] = [_cap(a) for a in s.get("cap_add") or []]
        x["cap_drop"] = [_cap(a) for a in s.get("cap_drop") or []]
        x["user"] = None if s.get("user") is None else str(s.get("user"))
        x["read_only"] = s.get("read_only")
        x["seccomp"] = "runtime"
        _secopts(x, s.get("security_opt") or [])
        x["host_network"] = str(s.get("network_mode") or "") == "host"
        x["host_pid"] = str(s.get("pid") or "") == "host"
        x["host_ipc"] = str(s.get("ipc") or "") == "host"
        x["host_userns"] = str(s.get("userns_mode") or "") == "host"
        x["host_paths"] = [b for b in (_bindspec(v) for v in s.get("volumes") or []) if b]
        for p in s.get("ports") or []:
            if isinstance(p, dict):
                if p.get("published"):
                    x["host_ports"].append(str(p["published"]))
            else:
                ps = str(p).split("/")[0].split(":")
                if len(ps) >= 2:
                    x["host_ports"].append(ps[-2])
        x["devices"] = [str(d) for d in s.get("devices") or []]
        lim = (((s.get("deploy") or {}).get("resources") or {}).get("limits")) or {}
        if s.get("mem_limit"):
            lim = {**lim, "memory": s["mem_limit"]}
        if s.get("cpus"):
            lim = {**lim, "cpus": s["cpus"]}
        if s.get("pids_limit"):
            lim = {**lim, "pids": s["pids_limit"]}
        x["limits"] = {k: str(v) for k, v in lim.items() if k in ("memory", "cpus", "pids")}
        sy = s.get("sysctls") or []
        x["sysctls"] = list(sy.keys()) if isinstance(sy, dict) else [str(v).split("=")[0] for v in sy]
        x["init"] = bool(s.get("init"))
        out.append(x)
    return out


_VAL = {"-e", "--env", "--env-file", "-v", "--volume", "--mount", "-p", "--publish", "--name", "--network", "--net", "-u", "--user", "-w",
        "--workdir", "--cap-add", "--cap-drop", "--security-opt", "-m", "--memory", "--cpus", "--pids-limit", "--device", "--sysctl",
        "--label", "-l", "--entrypoint", "--restart", "--pid", "--ipc", "--userns", "--hostname", "-h", "--add-host", "--dns", "--tmpfs",
        "--ulimit", "--log-driver", "--log-opt", "--gpus", "--platform", "--shm-size", "--cpuset-cpus", "--memory-swap", "--cgroupns",
        "--uts", "--runtime", "--stop-signal", "--health-cmd", "--health-interval", "--ip", "--mac-address", "--expose", "--group-add",
        "--link", "--volumes-from", "--cidfile", "--storage-opt", "--oom-score-adj", "--cpu-shares", "-c", "--pull", "--network-alias",
        "--cpu-quota", "--cpu-period", "--blkio-weight", "--attach", "-a", "--detach-keys", "--isolation", "--kernel-memory"}


def _docker(text: str) -> list[dict[str, Any]]:
    out = []
    for cmd in re.split(r"\n(?=\s*(?:sudo\s+)?(?:docker|podman|nerdctl)\s+(?:container\s+)?(?:run|create)\b)", text.replace("\\\n", " ")):
        cmd = cmd.strip()
        if not cmd:
            continue
        try:
            a = shlex.split(cmd, comments=True)
        except ValueError as e:
            raise ContainerError(f"Could not read the command line: {e}.")
        while a and a[0] in ("sudo",):
            a.pop(0)
        if len(a) < 2 or a[0] not in ("docker", "podman", "nerdctl"):
            continue
        tool = a[0]
        i = 1
        if a[i] == "container":
            i += 1
        if i >= len(a) or a[i] not in ("run", "create"):
            continue
        i += 1
        x = _new(f"{tool} run", tool)
        x["seccomp"] = "runtime"
        nm = ""
        while i < len(a):
            t = a[i]
            if not t.startswith("-") or t == "-":
                x["image"] = t
                break
            k, eq, v = t.partition("=")
            if not eq and k in _VAL:
                i += 1
                v = a[i] if i < len(a) else ""
            if k == "--privileged":
                x["privileged"] = v.lower() != "false" if eq else True
            elif k == "--cap-add":
                x["cap_add"] += [_cap(c) for c in v.split(",") if c]
            elif k == "--cap-drop":
                x["cap_drop"] += [_cap(c) for c in v.split(",") if c]
            elif k in ("-u", "--user"):
                x["user"] = v
            elif k == "--read-only":
                x["read_only"] = v.lower() != "false" if eq else True
            elif k == "--security-opt":
                _secopts(x, [v])
            elif k in ("--network", "--net"):
                x["host_network"] = v == "host"
            elif k == "--pid":
                x["host_pid"] = v == "host"
            elif k == "--ipc":
                x["host_ipc"] = v == "host"
            elif k == "--userns":
                x["host_userns"] = v == "host"
            elif k in ("-v", "--volume"):
                b = _bindspec(v)
                if b:
                    x["host_paths"].append(b)
            elif k == "--mount":
                kv = dict(p.partition("=")[::2] for p in v.split(","))
                src = kv.get("source") or kv.get("src") or ""
                if (kv.get("type") or "volume") == "bind" and src:
                    x["host_paths"].append({"host": src, "path": kv.get("target") or kv.get("dst") or kv.get("destination") or "",
                                            "ro": "readonly" in kv or "ro" in kv or kv.get("readonly") == "true"})
            elif k in ("-p", "--publish"):
                ps = v.split("/")[0].split(":")
                if len(ps) >= 2:
                    x["host_ports"].append(ps[-2])
            elif k == "--device":
                x["devices"].append(v)
            elif k in ("-m", "--memory"):
                x["limits"]["memory"] = v
            elif k == "--cpus":
                x["limits"]["cpus"] = v
            elif k == "--pids-limit":
                x["limits"]["pids"] = v
            elif k == "--sysctl":
                x["sysctls"].append(v.split("=")[0])
            elif k == "--name":
                nm = v
            elif k == "--init":
                x["init"] = True
            i += 1
        if nm:
            x["name"] = f"{tool} run --name {nm}"
        out.append(x)
    return out


def _oci(d: dict[str, Any]) -> list[dict[str, Any]]:
    x = _new("config.json", "oci")
    p = d.get("process") or {}
    u = p.get("user") or {}
    x["user"] = str(u.get("uid", 0))
    caps = p.get("capabilities") or {}
    x["caps_set"] = sorted({_cap(c) for c in (caps.get("bounding") or []) + (caps.get("effective") or []) + (caps.get("permitted") or [])})
    x["no_new_privs"] = bool(p.get("noNewPrivileges"))
    x["read_only"] = bool((d.get("root") or {}).get("readonly"))
    lin = d.get("linux") or {}
    sc = lin.get("seccomp")
    x["seccomp"] = None if not sc else ("unconfined" if str(sc.get("defaultAction")) == "SCMP_ACT_ALLOW" and not sc.get("syscalls") else "localhost")
    x["apparmor"] = "localhost" if p.get("apparmorProfile") else None
    x["selinux"] = p.get("selinuxLabel") or None
    ns = {str(n.get("type")) for n in lin.get("namespaces") or [] if isinstance(n, dict)}
    x["host_network"] = "network" not in ns
    x["host_pid"] = "pid" not in ns
    x["host_ipc"] = "ipc" not in ns
    x["oci_userns"] = "user" in ns
    x["oci_masked"] = bool(lin.get("maskedPaths"))
    x["oci_cgroupns"] = "cgroup" in ns
    for m in d.get("mounts") or []:
        if isinstance(m, dict) and (m.get("type") == "bind" or "bind" in (m.get("options") or []) or "rbind" in (m.get("options") or [])):
            x["host_paths"].append({"host": str(m.get("source") or ""), "path": str(m.get("destination") or ""), "ro": "ro" in (m.get("options") or [])})
    r = lin.get("resources") or {}
    if (r.get("memory") or {}).get("limit"):
        x["limits"]["memory"] = str(r["memory"]["limit"])
    if (r.get("cpu") or {}).get("quota"):
        x["limits"]["cpus"] = str(r["cpu"]["quota"])
    if (r.get("pids") or {}).get("limit"):
        x["limits"]["pids"] = str(r["pids"]["limit"])
    x["devices"] = [str(dv.get("path")) for dv in lin.get("devices") or [] if isinstance(dv, dict)]
    return [x]


# ---------------------------------------------------------------- the checks
def _I(sev: str, level: str, text: str, fix: str = "") -> dict[str, Any]:
    return {"sev": sev, "level": level, "text": text, "fix": fix}


def _root(x: dict[str, Any]) -> bool | None:
    """True = runs as root, False = not, None = cannot tell from the config."""
    u = x["user"]
    if u is not None:
        first = str(u).split(":")[0].strip()
        if first in ("0", "root"):
            return True
        if first:
            return False
    if x["non_root"] is True:
        return False
    return None


def _check(x: dict[str, Any]) -> list[dict[str, Any]]:
    src = x["source"]
    k8s, oci = src == "kubernetes", src == "oci"
    iss: list[dict[str, Any]] = []
    # baseline
    if x["privileged"]:
        iss.append(_I("bad", "baseline", "Runs privileged: every capability, every device, no seccomp or AppArmor - a container escape is one step.",
                      "privileged: false" if k8s else "remove --privileged / privileged: true"))
    if x["host_network"]:
        iss.append(_I("bad", "baseline", "Shares the host's network: it sees every host interface and can reach services bound to localhost.",
                      "hostNetwork: false" if k8s else "remove --network host / network_mode: host"))
    if x["host_pid"]:
        iss.append(_I("bad", "baseline", "Shares the host's process list: it can see (and with ptrace, read) every process on the host.",
                      "hostPID: false" if k8s else "remove --pid host"))
    if x["host_ipc"]:
        iss.append(_I("bad", "baseline", "Shares the host's IPC: it can read shared memory of host processes.", "hostIPC: false" if k8s else "remove --ipc host"))
    if x.get("host_userns"):
        iss.append(_I("warn", "extra", "Turns off the user namespace the daemon set up (--userns host).", "remove --userns host"))
    for hp in x["host_paths"]:
        h = hp["host"].rstrip("/") or "/"
        if h in SOCKETS or h.endswith(".sock") and "docker" in h or h.endswith("containerd.sock"):
            iss.append(_I("bad", "baseline", f"Mounts the container runtime's socket {h}: whoever is in this container controls the whole host.",
                          "do not mount the runtime socket; if a build needs it, use a rootless builder (BuildKit rootless, kaniko, buildah)"))
        elif h in HOST_DIRS:
            iss.append(_I("bad", "baseline", f"Mounts {h} from the host ({HOST_DIRS[h]}) at {hp['path']}" + (" read-only" if hp["ro"] else " read-write") + ".",
                          "mount only the files it needs, read-only"))
        elif k8s:
            iss.append(_I("warn", "baseline", f"Mounts a host path {h} at {hp['path']}: Pod Security baseline forbids hostPath volumes.",
                          "use a PersistentVolumeClaim, configMap or emptyDir"))
        elif not hp["ro"] and not h.startswith(".") and not h.startswith("~"):
            iss.append(_I("info", "extra", f"Mounts {h} from the host read-write at {hp['path']}.", f"{h}:{hp['path']}:ro if it only reads it"))
    if x["host_ports"] and k8s:
        iss.append(_I("warn", "baseline", f"Uses hostPort {', '.join(map(str, x['host_ports']))}: Pod Security baseline forbids host ports; a Service does this.",
                      "remove hostPort and expose it with a Service"))
    if x["caps_set"] is not None:
        extra = [c for c in x["caps_set"] if c not in BASE_CAPS]
        for c in extra:
            iss.append(_I("bad" if c in DANGER and c != "NET_RAW" else "warn", "baseline", f"Keeps the {c} capability" + (f": {DANGER[c]}." if c in DANGER else "."),
                          f"drop CAP_{c} from process.capabilities"))
        if set(x["caps_set"]) - {"NET_BIND_SERVICE"}:
            iss.append(_I("warn", "restricted", f"Keeps {len(x['caps_set'])} capabilities; restricted keeps at most NET_BIND_SERVICE.",
                          "process.capabilities: only CAP_NET_BIND_SERVICE, or none"))
    else:
        for c in x["cap_add"]:
            if c == "ALL" or c not in BASE_CAPS:
                iss.append(_I("bad" if c != "NET_RAW" else "warn", "baseline", f"Adds the {c} capability" + (f": {DANGER[c]}." if c in DANGER else "."),
                              f"remove {c} from capabilities.add" if k8s else f"remove --cap-add {c}"))
        if not ("ALL" in x["cap_drop"]):
            iss.append(_I("warn", "restricted", "Does not drop all capabilities: it keeps the runtime's default set (14 in Docker, NET_RAW among them).",
                          "capabilities: {drop: [ALL]}" if k8s else "--cap-drop ALL (add back only what it needs, like NET_BIND_SERVICE)"))
        if any(c not in ("NET_BIND_SERVICE",) for c in x["cap_add"] if c != "ALL" and c in BASE_CAPS):
            iss.append(_I("warn", "restricted", "Adds back capabilities other than NET_BIND_SERVICE: restricted allows only that one.",
                          "capabilities.add: [NET_BIND_SERVICE] at most"))
    if x["seccomp"] == "unconfined":
        iss.append(_I("bad", "baseline", "Runs with seccomp off: every system call the kernel has is open to it.",
                      "seccompProfile: {type: RuntimeDefault}" if k8s else "remove seccomp=unconfined (the runtime's default profile applies)"))
    elif x["seccomp"] is None and k8s:
        iss.append(_I("warn", "restricted", "No seccomp profile is set: unless the kubelet runs with --seccomp-default it runs unconfined.",
                      "seccompProfile: {type: RuntimeDefault}"))
    elif x["seccomp"] is None and oci:
        iss.append(_I("bad", "baseline", "No linux.seccomp in the config: every system call is open.", "add a seccomp profile (the Seccomp tab can make one)"))
    if x["apparmor"] == "unconfined":
        iss.append(_I("bad", "baseline", "Runs with AppArmor off.", "remove apparmor=unconfined / the unconfined annotation"))
    if x["selinux"] == "disabled":
        iss.append(_I("bad", "baseline", "Turns SELinux labels off for this container (label=disable).", "remove label=disable"))
    elif k8s and x["selinux"] and x["selinux"] not in ("container_t", "container_init_t", "container_kvm_t", "container_engine_t"):
        iss.append(_I("warn", "baseline", f"Sets a custom SELinux type {x['selinux']}: baseline allows only the container types.", "remove seLinuxOptions.type"))
    if x["proc_mount"] and str(x["proc_mount"]) != "Default":
        iss.append(_I("bad", "baseline", "procMount Unmasked: the host's /proc paths that are normally hidden are visible.", "remove procMount"))
    bad_sys = [s for s in x["sysctls"] if s not in SAFE_SYSCTLS]
    if bad_sys:
        iss.append(_I("warn", "baseline", "Sets sysctls outside the safe list: " + ", ".join(bad_sys[:6]) + ".", "only the namespaced safe sysctls"))
    if x["devices"]:
        iss.append(_I("warn", "extra", "Gets host devices: " + ", ".join(x["devices"][:5]) + ". Each is a way to the host's kernel drivers.",
                      "only the device it needs, with r / w / m limited"))
    # restricted
    if x["no_new_privs"] is not True:
        iss.append(_I("warn", "restricted", "Can gain privileges through setuid programs (no-new-privileges is not set).",
                      "allowPrivilegeEscalation: false" if k8s else "process.noNewPrivileges: true" if oci else "--security-opt no-new-privileges"))
    r = _root(x)
    if r is True:
        iss.append(_I("bad" if not k8s else "warn", "restricted", "Runs as root (user 0) inside the container: an escape lands as root on the host unless user namespaces map it.",
                      "runAsNonRoot: true and runAsUser: 10001" if k8s else "process.user.uid: 10001" if oci else "--user 10001:10001 (and USER 10001 in the Dockerfile)"))
    elif r is None:
        iss.append(_I("warn", "restricted", "The config does not say who it runs as: it is root unless the image sets USER.",
                      "runAsNonRoot: true and runAsUser: 10001" if k8s else "--user 10001:10001"))
    if k8s:
        bad_v = sorted({t for t in x["volumes"] if t and t not in RESTRICTED_VOLUMES and t != "hostPath"})
        if bad_v:
            iss.append(_I("warn", "restricted", "Uses volume types restricted does not allow: " + ", ".join(bad_v) + ".", "use a PersistentVolumeClaim"))
    if oci and not x.get("oci_userns"):
        iss.append(_I("info", "extra", "No user namespace: root inside is root outside.", "add a user namespace with uid / gid mappings"))
    if oci and not x.get("oci_masked"):
        iss.append(_I("warn", "extra", "No linux.maskedPaths: /proc/kcore, /proc/keys and other host paths are not hidden.", "copy maskedPaths from runc spec's default"))
    # extra hardening
    if x["read_only"] is not True:
        iss.append(_I("info", "extra", "The root filesystem is writable: an attacker can drop tools into it.",
                      "readOnlyRootFilesystem: true (+ an emptyDir for /tmp)" if k8s else "root.readonly: true" if oci else "--read-only --tmpfs /tmp"))
    if not x["limits"].get("memory"):
        iss.append(_I("warn", "extra", "No memory limit: one leak can take the node's memory.", "resources.limits.memory" if k8s else "--memory 512m"))
    if not (x["limits"].get("cpu") or x["limits"].get("cpus")):
        iss.append(_I("info", "extra", "No CPU limit.", "resources.limits.cpu" if k8s else "--cpus 1"))
    if not k8s and not x["limits"].get("pids"):
        iss.append(_I("info", "extra", "No process limit: a fork bomb takes the host.", "--pids-limit 256"))
    img = x["image"]
    if img and not img.startswith("(built"):
        last = img.rsplit("/", 1)[-1]
        if "@sha256:" in img:
            pass
        elif ":" not in last or last.endswith(":latest"):
            iss.append(_I("warn", "extra", f"Image {img} has no fixed version (latest): a different image can run tomorrow.", "pin a version tag, best a digest @sha256:..."))
        else:
            iss.append(_I("info", "extra", f"Image {img} is pinned by tag, not by digest: a tag can be moved.", "pin @sha256:<digest>"))
    if k8s and x["sa_token"] is not False:
        iss.append(_I("info", "extra", "The service account token is mounted: if it does not call the Kubernetes API it does not need it.",
                      "automountServiceAccountToken: false"))
    return iss


def _level(iss: list[dict[str, Any]]) -> str:
    if any(i["level"] == "baseline" and i["sev"] in ("bad", "warn") for i in iss):
        return "privileged"
    if any(i["level"] == "restricted" for i in iss):
        return "baseline"
    return "restricted"


def _fix(x: dict[str, Any], uid: int) -> str:
    keep = [c for c in (x["cap_add"] or []) if c == "NET_BIND_SERVICE"]
    if x["source"] == "kubernetes":
        lines = ["securityContext:", "  runAsNonRoot: true", f"  runAsUser: {uid}", f"  runAsGroup: {uid}", "  allowPrivilegeEscalation: false",
                 "  readOnlyRootFilesystem: true", "  capabilities:", "    drop: [\"ALL\"]"]
        if keep:
            lines.append("    add: [\"NET_BIND_SERVICE\"]")
        lines += ["  seccompProfile:", "    type: RuntimeDefault"]
        if not x["limits"].get("memory"):
            lines += ["resources:", "  limits:", "    memory: 512Mi   # set to what it really needs", "    cpu: \"1\""]
        return "\n".join(lines)
    if x["source"] == "compose":
        lines = [f"user: \"{uid}:{uid}\"", "read_only: true", "tmpfs: [/tmp]", "cap_drop: [ALL]"]
        if keep:
            lines.append("cap_add: [NET_BIND_SERVICE]")
        lines += ["security_opt:", "  - no-new-privileges:true", "pids_limit: 256", "mem_limit: 512m   # set to what it really needs", "cpus: 1"]
        return "\n".join(lines)
    if x["source"] == "oci":
        return json.dumps({"process": {"user": {"uid": uid, "gid": uid}, "noNewPrivileges": True,
                                       "capabilities": {k: (["CAP_NET_BIND_SERVICE"] if keep else []) for k in ("bounding", "effective", "permitted")}},
                           "root": {"readonly": True}}, indent=2)
    tool = x["source"] if x["source"] in ("docker", "podman", "nerdctl") else "docker"
    flags = [f"{tool} run", f"--user {uid}:{uid}", "--read-only", "--tmpfs /tmp", "--cap-drop ALL"] + (["--cap-add NET_BIND_SERVICE"] if keep else []) + [
        "--security-opt no-new-privileges", "--pids-limit 256", "--memory 512m", "--cpus 1"]
    flags += [f"-p {p}" for p in x["host_ports"]][:4]
    return " \\\n  ".join(flags) + f" \\\n  {x['image'] or '<image>'}"


def dockerfile(text: str) -> list[dict[str, Any]]:
    iss: list[dict[str, Any]] = []
    lines = [ln.strip() for ln in text.replace("\\\n", " ").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    users = [ln.split(None, 1)[1].strip() if len(ln.split(None, 1)) > 1 else "" for ln in lines if ln.upper().startswith("USER ")]
    stages = [ln for ln in lines if ln.upper().startswith("FROM ")]
    if not stages:
        raise ContainerError("No FROM line: this does not look like a Dockerfile.")
    last_from = max(i for i, ln in enumerate(lines) if ln.upper().startswith("FROM "))
    last_user = [ln for ln in lines[last_from:] if ln.upper().startswith("USER ")]
    if not last_user:
        iss.append(_I("bad", "restricted", "No USER in the final stage: the container runs as root.", "RUN useradd -u 10001 -r app && ... \nUSER 10001"))
    elif last_user[-1].split(None, 1)[-1].split(":")[0].strip() in ("root", "0"):
        iss.append(_I("bad", "restricted", "The final USER is root.", "USER 10001"))
    for ln in stages:
        img = ln.split()[1] if len(ln.split()) > 1 else ""
        if img.lower() == "scratch" or img.startswith("$"):
            continue
        last = img.rsplit("/", 1)[-1]
        if "@sha256:" not in img and (":" not in last or last.endswith(":latest")):
            iss.append(_I("warn", "extra", f"FROM {img}: no fixed version, the build changes when the image does.", f"FROM {img.split(':')[0]}:<version>@sha256:<digest>"))
    for ln in lines:
        u = ln.upper()
        if u.startswith("ADD ") and re.search(r"\bhttps?://", ln):
            iss.append(_I("warn", "extra", "ADD from a URL: no checksum is checked.", "RUN curl -fsSLo file URL && echo '<sha256>  file' | sha256sum -c"))
        if re.search(r"(curl|wget)[^|;&]*\|\s*(ba|z)?sh\b", ln):
            iss.append(_I("warn", "extra", "Downloads a script and runs it in one step: whatever the server sends runs in the build.", "download, check the checksum, then run"))
        m = re.match(r"(ENV|ARG)\s+(\w+)", ln, re.I)
        if m and re.search(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_KEY|ACCESS_KEY)", m.group(2), re.I) and ("=" in ln or len(ln.split()) > 2 or m.group(1).upper() == "ENV"):
            iss.append(_I("bad", "extra", f"{m.group(1).upper()} {m.group(2)}: a secret in the image is readable by anyone who can pull it (docker history).",
                          "RUN --mount=type=secret,id=... (BuildKit secrets) or pass it at run time"))
        if re.search(r"chmod\s+(-R\s+)?777", ln):
            iss.append(_I("warn", "extra", "chmod 777: every user in the container can change those files.", "give the files to the app user, mode 755 / 644"))
        if re.search(r"\b(apt-get|apk|yum|dnf)\b.*\binstall\b.*\bsudo\b", ln):
            iss.append(_I("warn", "extra", "Installs sudo: the user can become root again.", "do not install sudo"))
        if u.startswith("EXPOSE") and re.search(r"\b22\b", ln):
            iss.append(_I("warn", "extra", "Exposes port 22: an SSH server in a container is one more way in.", "use docker exec / kubectl exec"))
        if re.search(r"apt-get\s+install(?!.*--no-install-recommends)", ln):
            iss.append(_I("info", "extra", "apt-get install without --no-install-recommends: a bigger image, more to patch.", "apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*"))
    if not any(ln.upper().startswith("HEALTHCHECK") for ln in lines):
        iss.append(_I("info", "extra", "No HEALTHCHECK (Kubernetes ignores it; Docker and Compose use it).", "HEALTHCHECK CMD [\"/app/health\"]"))
    seen, out = set(), []
    for i in iss:
        if i["text"] not in seen:
            seen.add(i["text"])
            out.append(i)
    return out


def detect(text: str) -> str:
    t = text.lstrip()
    if t.startswith("{"):
        return "oci"
    if re.search(r"^\s*(sudo\s+)?(docker|podman|nerdctl)\s+(container\s+)?(run|create)\b", text, re.M):
        return "docker"
    if re.search(r"^\s*FROM\s+\S+", text, re.M | re.I) and re.search(r"^\s*(RUN|CMD|ENTRYPOINT|COPY|USER|WORKDIR)\b", text, re.M | re.I):
        return "dockerfile"
    if re.search(r"^services\s*:", text, re.M):
        return "compose"
    if re.search(r"^\s*kind\s*:", text, re.M):
        return "kubernetes"
    raise ContainerError("Could not tell what this is: paste Kubernetes YAML, a Compose file, a docker run line, an OCI config.json or a Dockerfile.")


def check(text: str, uid: int = 10001, target: str = "restricted") -> dict[str, Any]:
    text = str(text or "")
    if not text.strip():
        raise ContainerError("Paste the config first.")
    fmt = detect(text)
    if fmt == "dockerfile":
        iss = dockerfile(text)
        return {"format": fmt, "containers": [], "issues": iss, "level": None,
                "counts": {s: sum(1 for i in iss if i["sev"] == s) for s in ("bad", "warn", "info")},
                "verdict": (f"{sum(1 for i in iss if i['sev'] == 'bad')} serious finding(s) in the Dockerfile." if any(i["sev"] == "bad" for i in iss)
                            else "The Dockerfile passed the serious checks." + (f" {len(iss)} thing(s) to look at." if iss else "")),
                "note": "Checks the Dockerfile's text; it does not build the image or scan its packages for CVEs."}
    if fmt == "oci":
        try:
            d = json.loads(text)
        except ValueError as e:
            raise ContainerError(f"The JSON does not read: {e}.")
        if not isinstance(d, dict) or not (d.get("process") or d.get("ociVersion")):
            raise ContainerError("This JSON is not an OCI runtime config (no process / ociVersion).")
        cs = _oci(d)
    elif fmt == "docker":
        cs = _docker(text)
    else:
        import yaml
        try:
            docs = [x for x in yaml.safe_load_all(text) if x is not None]
        except yaml.YAMLError as e:
            raise ContainerError(f"The YAML does not read: {str(e)[:200]}.")
        cs = _compose(docs[0]) if fmt == "compose" and docs and isinstance(docs[0], dict) else _k8s(docs)
    if not cs:
        raise ContainerError("No containers found in it.")
    if len(cs) > 300:
        cs = cs[:300]
    rows = []
    for x in cs:
        iss = _check(x)
        lvl = _level(iss)
        rows.append({"name": x["name"], "image": x["image"], "source": x["source"], "level": lvl, "issues": iss,
                     "root": _root(x), "fix": _fix(x, uid), "caps_effective": sorted(_effective(x))})
    order = {"privileged": 0, "baseline": 1, "restricted": 2}
    worst = min((r["level"] for r in rows), key=lambda v: order[v])
    allis = [{**i, "container": r["name"]} for r in rows for i in r["issues"]]
    counts = {s: sum(1 for i in allis if i["sev"] == s) for s in ("bad", "warn", "info")}
    tgt = target if target in order else "restricted"
    meets = sum(1 for r in rows if order[r["level"]] >= order[tgt])
    return {"format": fmt, "containers": rows, "level": worst, "counts": counts, "target": tgt, "meets": meets,
            "issues": [i for i in allis if i["sev"] == "bad"][:40],
            "verdict": (f"{meets} of {len(rows)} container(s) meet Pod Security {tgt}; the weakest is at {worst}."
                        + (f" {counts['bad']} serious finding(s)." if counts["bad"] else "")),
            "note": ("Levels follow the Kubernetes Pod Security Standards (baseline, restricted); for Docker / Compose the same rules are read in Docker's "
                     "terms. Checks the config, not the image: run it hardened in CI (the CI tab) to see it really starts.")}


def _effective(x: dict[str, Any]) -> set[str]:
    if x["privileged"]:
        return {"ALL"}
    if x["caps_set"] is not None:
        return set(x["caps_set"])
    base = set() if "ALL" in x["cap_drop"] else (DOCKER_DEFAULT - set(x["cap_drop"]))
    add = set(x["cap_add"])
    return {"ALL"} if "ALL" in add else base | add
