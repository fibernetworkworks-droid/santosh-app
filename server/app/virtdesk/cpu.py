"""CPU flags of her hosts compared, for VMs and live migration: virtualisation support (VT-x / AMD-V, EPT / NPT), the x86-64
psABI level each host and all of them reach (v1 to v4, as defined in the x86-64 psABI), the flags only some hosts have (a guest
that uses one cannot move to a host without it), mixed vendors, and the CPU vulnerabilities lscpu reports. Pasted text is data."""
from __future__ import annotations

import re
from typing import Any


class CpuError(ValueError):
    pass


# x86-64 psABI microarchitecture levels, in /proc/cpuinfo flag names (LZCNT = abm, OSXSAVE is implied by xsave being usable)
LEVELS = [("x86-64-v1", ["cmov", "cx8", "fpu", "fxsr", "mmx", "syscall", "sse", "sse2"]),
          ("x86-64-v2", ["cx16", "lahf_lm", "popcnt", "sse4_1", "sse4_2", "ssse3"]),
          ("x86-64-v3", ["avx", "avx2", "bmi1", "bmi2", "f16c", "fma", "abm", "movbe", "xsave"]),
          ("x86-64-v4", ["avx512f", "avx512bw", "avx512cd", "avx512dq", "avx512vl"])]
NOTABLE = {"avx512f", "avx512bw", "avx512vl", "avx512_vnni", "avx512_bf16", "avx512_fp16", "amx_tile", "amx_bf16", "amx_int8", "avx_vnni",
           "sha_ni", "vaes", "vpclmulqdq", "gfni", "aes", "pku", "ospke", "umip", "la57", "x2apic", "rdseed", "rdpid", "md_clear", "ibrs",
           "ibpb", "stibp", "ssbd", "arch_capabilities", "tsc_adjust", "invpcid", "pcid", "fsrm", "erms", "clwb", "clflushopt", "movdiri",
           "movdir64b", "waitpkg", "serialize", "tsxldtrk", "rtm", "hle", "sgx", "sev", "sev_es", "sev_snp", "tdx_host_platform",
           "sve", "sve2", "sha3", "sha512", "atomics", "bf16", "i8mm"}


def _blocks(text: str) -> list[tuple[str, str]]:
    t = str(text or "")
    if len(t) > 3_000_000:
        raise CpuError("That is longer than 3 MB.")
    heads = list(re.finditer(r"^\s*(?:##+\s*|===+\s*|\[)([^\]\n=]+?)(?:\s*===+|\])?\s*$", t, re.M))
    if heads:
        out = []
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
            out.append((m.group(1).strip()[:60], t[m.end():end]))
        return out
    # one host per line: "name: fpu vme de ..." or "name flags: fpu ..."
    lines = [ln for ln in t.splitlines() if ln.strip()]
    if lines and all(len(ln.split()) > 15 for ln in lines):
        out = []
        for i, ln in enumerate(lines):
            m = re.match(r"\s*([\w.\-]+)\s*(?:flags|features)?\s*:\s*(.+)$", ln, re.I)
            if m and not m.group(1).lower() in ("flags", "features"):
                out.append((m.group(1), "flags : " + m.group(2)))
            else:
                out.append((f"host {i + 1}", ln))
        return out
    return [("host 1", t)]


def _host(name: str, txt: str) -> dict[str, Any]:
    flags: set[str] = set()
    model = vendor = ""
    vulns: list[dict[str, str]] = []
    for ln in txt.splitlines():
        m = re.match(r"\s*(flags|features|Flags|Features)\s*:\s*(.*)$", ln)
        if m and len(m.group(2).split()) > 3:
            flags |= set(m.group(2).lower().split())
            continue
        m = re.match(r"\s*(model name|Model name|cpu model|CPU part)\s*:\s*(.*)$", ln)
        if m and not model:
            model = m.group(2).strip()
        m = re.match(r"\s*(vendor_id|Vendor ID|CPU implementer)\s*:\s*(.*)$", ln)
        if m and not vendor:
            vendor = m.group(2).strip()
        m = re.match(r"\s*(?:Vulnerability\s+|/sys/devices/system/cpu/vulnerabilities/)([\w ./-]+?)\s*:\s*(.+)$", ln)
        if m:
            vulns.append({"name": m.group(1).strip(), "state": m.group(2).strip()})
    if not flags:
        bare = [w.lower() for w in re.findall(r"\b[a-zA-Z][\w]+\b", txt)]
        if len(bare) > 20:
            flags = set(bare)
    if not flags:
        raise CpuError(f"{name}: no CPU flags found - paste `grep -m1 flags /proc/cpuinfo` or `lscpu`.")
    if not vendor:
        vendor = "GenuineIntel" if "vmx" in flags or "intel" in model.lower() else "AuthenticAMD" if "svm" in flags or "amd" in model.lower() else ""
    x86 = "sse2" in flags or "lm" in flags
    level = None
    if x86:
        for lv, need in LEVELS:
            if all(f in flags for f in need):
                level = lv
            else:
                break
    virt = "vmx" if "vmx" in flags else "svm" if "svm" in flags else ""
    slat = "ept" in flags or "npt" in flags
    vbad = [v for v in vulns if v["state"].lower().startswith("vulnerable")]
    return {"name": name, "model": model, "vendor": vendor, "flags": flags, "count": len(flags), "x86": x86, "level": level, "virt": virt,
            "slat": bool(slat), "vpid": "vpid" in flags, "nested_ok": virt != "", "vulns": vulns, "vulnerable": vbad}


def _lvl(flags: set[str]) -> str | None:
    out = None
    for lv, need in LEVELS:
        if all(f in flags for f in need):
            out = lv
        else:
            break
    return out


def compare(text: str) -> dict[str, Any]:
    hs = [_host(n, t) for n, t in _blocks(text)]
    if len(hs) > 100:
        raise CpuError("Up to 100 hosts.")
    names = [h["name"] for h in hs]
    if len(set(names)) != len(names):
        raise CpuError("Two hosts have the same name.")
    common = set.intersection(*[h["flags"] for h in hs])
    union = set.union(*[h["flags"] for h in hs])
    issues: list[dict[str, Any]] = []
    rows = []
    for h in hs:
        only_missing = sorted(union - h["flags"])
        extra = sorted(h["flags"] - common)
        rows.append({"name": h["name"], "model": h["model"], "vendor": h["vendor"], "count": h["count"], "level": h["level"], "virt": h["virt"],
                     "slat": h["slat"], "vpid": h["vpid"], "missing": only_missing[:200], "missing_n": len(only_missing),
                     "extra_notable": [f for f in extra if f in NOTABLE][:40], "extra_n": len(extra), "vulns": h["vulns"][:40],
                     "vulnerable": h["vulnerable"]})
        if not h["virt"] and h["x86"]:
            issues.append({"sev": "bad", "text": f"{h['name']}: no vmx / svm flag - VT-x / AMD-V is off in the firmware (or this is a VM without nested virtualisation): KVM cannot run."})
        elif h["x86"] and not h["slat"]:
            issues.append({"sev": "warn", "text": f"{h['name']}: no EPT / NPT flag - guest memory is shadowed in software, much slower."})
        for v in h["vulnerable"]:
            issues.append({"sev": "bad", "text": f"{h['name']}: {v['name']} - {v['state']} (from lscpu): update the microcode / kernel."})
    vendors = sorted({h["vendor"] for h in hs if h["vendor"]})
    if len(vendors) > 1:
        issues.append({"sev": "bad", "text": "Hosts from different CPU vendors (" + ", ".join(vendors) + "): live migration between them is not supported by KVM - keep them in separate pools."})
    lv = _lvl(common) if all(h["x86"] for h in hs) else None
    same = all(h["flags"] == hs[0]["flags"] for h in hs)
    differ = sorted(f for f in union - common if f in NOTABLE)
    if len(hs) > 1 and not same:
        issues.append({"sev": "warn", "text": f"{len(union - common)} flag(s) are on some hosts and not others" + (": " + ", ".join(differ[:14]) if differ else "") +
                       ". A VM started with host-passthrough on a host that has them cannot move to one that does not."})
    feats = sorted(union - common)
    xml = ("<cpu mode='host-model' check='partial'/>" if same else
           "<!-- the CPU all hosts share: run `virsh domcapabilities` on each host, then `virsh hypervisor-cpu-baseline --migratable` over those files -->\n"
           "<cpu mode='custom' match='exact' check='partial'>\n  <model fallback='forbid'><!-- the model virsh gives --></model>\n"
           + "".join(f"  <feature policy='disable' name='{f}'/>\n" for f in feats[:40]) + "</cpu>")
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    counts = {s: sum(1 for i in issues if i["sev"] == s) for s in order}
    if len(hs) == 1:
        verdict = f"{hs[0]['name']}: {hs[0]['count']} flags" + (f", {lv}" if lv else "") + (", virtualisation " + ("on" if hs[0]["virt"] else "OFF") if hs[0]["x86"] else "") + "."
    else:
        verdict = (f"{len(hs)} hosts: " + ("identical flags - live migration with host-passthrough works." if same else
                   f"they share {len(common)} flags" + (f", all reach {lv}" if lv else "") + f"; {len(union - common)} differ, so give VMs the shared CPU, not host-passthrough."))
    return {"hosts": rows, "common_n": len(common), "union_n": len(union), "common_level": lv, "same": same, "differ": differ,
            "vendors": vendors, "xml": xml, "issues": issues, "counts": counts, "verdict": verdict,
            "note": ("The x86-64 levels are the psABI's; a CPU model name for libvirt comes from virsh on your hosts (it knows each model's flags). "
                     "Flags show what the CPU and kernel report, not what the firmware may still hide.")}
