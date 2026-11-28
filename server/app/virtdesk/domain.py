"""libvirt VM definitions (`virsh dumpxml`) checked for speed, safety and live migration: KVM or slow emulation, the CPU mode and
topology, pinning and NUMA, huge pages, emulated vs virtio disks and network cards, cache and I/O modes, console listeners open to
the network, sVirt off, firmware / Secure Boot / TPM, Hyper-V enlightenments for Windows guests, devices passed through. Each
finding has the XML to put in its place. The XML is data: a DOCTYPE or entity is refused."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


class DomainError(ValueError):
    pass


EMULATED_DISK = {"ide": "IDE", "sata": "SATA", "fdc": "floppy", "usb": "USB"}
EMULATED_NIC = {"e1000": "e1000", "e1000e": "e1000e", "rtl8139": "rtl8139", "ne2k_pci": "ne2k", "pcnet": "pcnet"}
UNITS = {"b": 1, "bytes": 1, "kb": 1000, "k": 1024, "kib": 1024, "mb": 1000 ** 2, "m": 1024 ** 2, "mib": 1024 ** 2, "gb": 1000 ** 3,
         "g": 1024 ** 3, "gib": 1024 ** 3, "tb": 1000 ** 4, "t": 1024 ** 4, "tib": 1024 ** 4}


def _I(sev: str, area: str, text: str, fix: str = "") -> dict[str, Any]:
    return {"sev": sev, "area": area, "text": text, "fix": fix}


def _bytes(el) -> int | None:
    if el is None or not (el.text or "").strip():
        return None
    try:
        v = float(el.text.strip())
    except ValueError:
        return None
    return int(v * UNITS.get((el.get("unit") or "KiB").lower(), 1024))


def parse(text: str) -> ET.Element:
    t = str(text or "").strip()
    if not t:
        raise DomainError("Paste the VM's XML first (virsh dumpxml <name>).")
    if re.search(r"<!(DOCTYPE|ENTITY)", t, re.I):
        raise DomainError("The XML has a DOCTYPE or entity: libvirt XML never needs one, so it is not read.")
    if len(t) > 2_000_000:
        raise DomainError("That XML is longer than 2 MB.")
    try:
        root = ET.fromstring(t)
    except ET.ParseError as e:
        raise DomainError(f"The XML does not read: {e}.")
    if root.tag != "domain":
        d = root.find(".//domain")
        if d is None:
            raise DomainError("This is not a libvirt domain: the top element must be <domain>.")
        root = d
    return root


def check(text: str) -> dict[str, Any]:
    d = parse(text)
    iss: list[dict[str, Any]] = []
    name = (d.findtext("name") or "vm").strip()
    hv = (d.get("type") or "").lower()
    desc = " ".join(filter(None, [name, d.findtext("description") or "", d.findtext("title") or "", ET.tostring(d.find("metadata"), "unicode") if d.find("metadata") is not None else ""])).lower()
    windows = bool(re.search(r"\bwin(dows)?(\d|[ -]?server|10|11|2k|xp|7|8)?\b", desc)) or d.find("features/hyperv") is not None
    os_el = d.find("os")
    ostype = os_el.find("type") if os_el is not None else None
    machine = (ostype.get("machine") if ostype is not None else "") or ""
    arch = (ostype.get("arch") if ostype is not None else "") or "x86_64"
    # hypervisor
    if hv == "qemu":
        iss.append(_I("bad", "speed", "type='qemu' runs the VM in software emulation (TCG): 10 to 50 times slower than KVM.",
                      "<domain type='kvm'>  (needs /dev/kvm: vmx / svm on the host)"))
    elif hv and hv not in ("kvm", "xen", "hyperv", "vz", "lxc"):
        iss.append(_I("info", "speed", f"Hypervisor type '{hv}'.", ""))
    if "i440fx" in machine or re.fullmatch(r"pc(-\d.*)?", machine):
        iss.append(_I("info", "speed", f"Machine type {machine}: the old i440FX chipset. q35 has PCIe, which passthrough and many virtio devices expect.",
                      "<type arch='x86_64' machine='q35'>hvm</type>  (a change of chipset: test the guest boots)"))
    # firmware
    fw = (os_el.get("firmware") if os_el is not None else "") or ""
    loader = os_el.find("loader") if os_el is not None else None
    uefi = fw == "efi" or (loader is not None and ("OVMF" in (loader.text or "") or "AAVMF" in (loader.text or "") or loader.get("type") == "pflash"))
    secure = (loader is not None and loader.get("secure") == "yes") or bool(os_el is not None and os_el.find("firmware/feature[@name='secure-boot'][@enabled='yes']") is not None)
    tpm = d.find("devices/tpm") is not None
    if arch.startswith("x86") and not uefi:
        iss.append(_I("info", "safety", "Boots with legacy BIOS (SeaBIOS): no Secure Boot.", "<os firmware='efi'> ... <loader secure='yes'/></os>"))
    elif uefi and not secure:
        iss.append(_I("info", "safety", "UEFI without Secure Boot: anything can be booted.", "<loader readonly='yes' secure='yes' type='pflash'>.../OVMF_CODE.secboot.fd</loader>"))
    if windows and not (uefi and secure and tpm):
        iss.append(_I("warn", "safety", "A Windows guest without UEFI + Secure Boot + TPM 2.0: Windows 11 and Server 2025 need all three.",
                      "<tpm model='tpm-crb'><backend type='emulator' version='2.0'/></tpm>"))
    # CPU
    cpu = d.find("cpu")
    mode = (cpu.get("mode") if cpu is not None else "") or ""
    model = (cpu.findtext("model") if cpu is not None else "") or ""
    vc_el = d.find("vcpu")
    try:
        vcpus = int((vc_el.text or "1").strip()) if vc_el is not None else 1
    except ValueError:
        vcpus = 1
    cur = vc_el.get("current") if vc_el is not None else None
    migratable = "yes"
    why_not: list[str] = []
    if cpu is None or (not mode and not model):
        iss.append(_I("warn", "speed", "No <cpu> set: the guest gets a generic CPU (qemu64) without AVX, AES-NI and other instructions it could use.",
                      "<cpu mode='host-model'/>  (or host-passthrough if it never moves to a different CPU)"))
    elif mode == "host-passthrough":
        migratable = "only to identical CPUs"
        why_not.append("host-passthrough: the target host must have exactly the same CPU and microcode")
        iss.append(_I("info", "migration", "CPU mode host-passthrough: fastest, but live migration works only between hosts with the same CPU.",
                      "<cpu mode='host-model'/> or a named model all hosts share (the Capacity tab finds it)"))
    elif mode == "custom" and model in ("qemu64", "kvm64", "qemu32", "kvm32", "pentium", "486"):
        iss.append(_I("warn", "speed", f"CPU model {model}: an old generic CPU, no AVX / AES-NI.", "<cpu mode='host-model'/>"))
    if cpu is not None:
        topo = cpu.find("topology")
        if topo is not None:
            try:
                prod = int(topo.get("sockets", 1)) * int(topo.get("dies", 1)) * int(topo.get("clusters", 1)) * int(topo.get("cores", 1)) * int(topo.get("threads", 1))
                if prod != vcpus:
                    iss.append(_I("bad", "config", f"CPU topology gives {prod} vCPUs but <vcpu> is {vcpus}: libvirt refuses this (or the guest sees the wrong count).",
                                  f"sockets x cores x threads = {vcpus}"))
                if int(topo.get("sockets", 1)) > 2 and windows:
                    iss.append(_I("warn", "config", f"{topo.get('sockets')} sockets: Windows desktop editions use only 1-2 sockets - put the vCPUs in cores.",
                                  f"<topology sockets='1' cores='{vcpus}' threads='1'/>"))
            except ValueError:
                pass
        if cpu.find("feature[@name='vmx'][@policy='require']") is not None or cpu.find("feature[@name='svm'][@policy='require']") is not None:
            iss.append(_I("info", "migration", "Nested virtualisation is on (vmx / svm required): a VM running VMs is harder to migrate and slower.", ""))
    tune = d.find("cputune")
    pinned = tune is not None and tune.find("vcpupin") is not None
    if vcpus >= 8 and not pinned:
        iss.append(_I("info", "speed", f"{vcpus} vCPUs and none are pinned: for steady latency pin them to cores on one NUMA node, and keep the emulator off them.",
                      "<cputune><vcpupin vcpu='0' cpuset='2'/> ... <emulatorpin cpuset='0-1'/></cputune>"))
    if pinned and d.find("numatune") is None:
        iss.append(_I("info", "speed", "vCPUs are pinned but memory is not tied to the same NUMA node.", "<numatune><memory mode='strict' nodeset='0'/></numatune>"))
    # memory
    mem = _bytes(d.find("memory"))
    cmem = _bytes(d.find("currentMemory"))
    gib = round(mem / 1024 ** 3, 2) if mem else None
    hp = d.find("memoryBacking/hugepages") is not None
    if gib and gib >= 16 and not hp:
        iss.append(_I("info", "speed", f"{gib:g} GiB of memory on normal 4 KiB pages: huge pages cut TLB misses for big or busy guests.",
                      "<memoryBacking><hugepages><page size='1' unit='G'/></hugepages></memoryBacking>  (reserve them on the host first)"))
    if mem and cmem and cmem < mem:
        iss.append(_I("info", "config", f"Started with {round(cmem / 1024 ** 3, 2):g} of {gib:g} GiB (ballooned down): the guest sees less than it was given.", ""))
    bal = d.find("devices/memballoon")
    if bal is not None and bal.get("model") == "virtio" and hp:
        iss.append(_I("info", "speed", "A memory balloon with huge pages: the balloon cannot give huge pages back to the host.", "<memballoon model='none'/>"))
    # disks
    disks = []
    for dk in d.findall("devices/disk"):
        dev = dk.get("device") or "disk"
        tgt = dk.find("target")
        drv = dk.find("driver")
        bus = (tgt.get("bus") if tgt is not None else "") or ""
        dname = (tgt.get("dev") if tgt is not None else "") or "?"
        cache = (drv.get("cache") if drv is not None else "") or "default"
        io = (drv.get("io") if drv is not None else "") or ""
        fmt = (drv.get("type") if drv is not None else "") or ""
        src = dk.find("source")
        path = (src.get("file") or src.get("dev") or src.get("name") or src.get("volume") or "") if src is not None else ""
        disks.append({"dev": dname, "bus": bus, "cache": cache, "io": io, "format": fmt, "device": dev, "source": path,
                      "shareable": dk.find("shareable") is not None})
        if dev == "cdrom":
            continue
        if bus in EMULATED_DISK:
            iss.append(_I("warn", "speed", f"Disk {dname} is on an emulated {EMULATED_DISK[bus]} controller: much slower than virtio.",
                          f"<target dev='vd{dname[-1:] or 'a'}' bus='virtio'/>  (Windows needs the virtio-win drivers first)"))
        if cache == "unsafe":
            iss.append(_I("bad", "safety", f"Disk {dname} has cache='unsafe': the guest's flushes are ignored, a host crash loses data.", "cache='none'"))
        elif cache in ("writeback", "default") and dk.find("shareable") is not None:
            iss.append(_I("bad", "safety", f"Disk {dname} is shared between VMs with host caching on: the VMs can see different data.", "cache='none' on shared disks"))
        if io == "native" and cache not in ("none", "directsync"):
            iss.append(_I("warn", "config", f"Disk {dname} has io='native' with cache='{cache}': native AIO needs O_DIRECT (cache none or directsync).", "cache='none' io='native'"))
        if cache == "default" and fmt in ("raw", "qcow2"):
            iss.append(_I("info", "speed", f"Disk {dname} uses the default cache (writeback): cache='none' gives steadier latency and is needed for safe live migration with shared storage.",
                          "<driver name='qemu' type='%s' cache='none' io='native' discard='unmap'/>" % fmt))
        if drv is not None and fmt in ("qcow2", "raw") and drv.get("discard") != "unmap" and dev == "disk":
            iss.append(_I("info", "space", f"Disk {dname}: discard is not passed through, deleted guest files stay allocated on the host.", "discard='unmap'"))
    if any(x["bus"] == "scsi" for x in disks):
        ctl = [c for c in d.findall("devices/controller") if c.get("type") == "scsi"]
        if ctl and all((c.get("model") or "") not in ("virtio-scsi",) for c in ctl):
            iss.append(_I("warn", "speed", "SCSI disks on an emulated SCSI controller.", "<controller type='scsi' model='virtio-scsi'/>"))
    if len([x for x in disks if x["device"] == "disk"]) >= 2 and d.find("iothreads") is None:
        iss.append(_I("info", "speed", "Several disks share the main QEMU thread: an iothread per busy disk spreads the work.", "<iothreads>2</iothreads> + <driver ... iothread='1'/>"))
    # network
    nics = []
    for ni in d.findall("devices/interface"):
        mdl = ni.find("model")
        m = (mdl.get("type") if mdl is not None else "") or "default"
        drv = ni.find("driver")
        q = int(drv.get("queues")) if drv is not None and (drv.get("queues") or "").isdigit() else 1
        nics.append({"type": ni.get("type") or "", "model": m, "queues": q, "mac": (ni.find("mac").get("address") if ni.find("mac") is not None else "")})
        if m in EMULATED_NIC:
            iss.append(_I("warn", "speed", f"Network card model {m}: emulated, slower and more CPU than virtio-net.", "<model type='virtio'/>"))
        elif m == "default":
            iss.append(_I("info", "speed", "Network card with no model: libvirt picks one (often rtl8139 or e1000).", "<model type='virtio'/>"))
        if m == "virtio" and vcpus >= 4 and q < 2:
            iss.append(_I("info", "speed", f"virtio-net with one queue on {vcpus} vCPUs: one core handles all the network interrupts.",
                          f"<driver name='vhost' queues='{min(vcpus, 8)}'/>"))
    # consoles
    for g in d.findall("devices/graphics"):
        t = g.get("type") or "?"
        listen = g.get("listen") or ""
        for li in g.findall("listen"):
            listen = li.get("address") or listen or (li.get("type") == "network" and "network") or ""
        open_ = listen in ("0.0.0.0", "::", "[::]") or (listen and not listen.startswith(("127.", "::1", "localhost", "/")) and listen != "network")
        if t in ("vnc", "spice") and open_ and not g.get("passwd"):
            iss.append(_I("bad", "safety", f"The {t.upper()} console listens on {listen} with no password: anyone who can reach the host sees and types into the VM's screen.",
                          f"<graphics type='{t}' listen='127.0.0.1'/>  (reach it over SSH or a VPN)"))
        elif t in ("vnc", "spice") and open_:
            iss.append(_I("warn", "safety", f"The {t.upper()} console listens on {listen}: a password alone (VNC: 8 characters max) is weak.",
                          f"listen='127.0.0.1' + an SSH tunnel, or TLS"))
    # security
    for sl in d.findall("seclabel"):
        if sl.get("type") == "none" or sl.get("relabel") == "no" and sl.get("type") != "dynamic":
            iss.append(_I("bad", "safety", "sVirt is off (seclabel type='none' / relabel='no'): a QEMU escape can touch every other VM's disks.",
                          "remove the <seclabel> to get the dynamic label"))
    hostdev = d.findall("devices/hostdev")
    if hostdev:
        migratable = "no"
        why_not.append(f"{len(hostdev)} device(s) passed through from the host")
        iss.append(_I("info", "migration", f"{len(hostdev)} host device(s) passed through: the VM cannot live-migrate while they are attached, and the host needs the IOMMU on.", ""))
    if windows:
        hv = d.find("features/hyperv")
        if hv is None:
            iss.append(_I("warn", "speed", "A Windows guest without Hyper-V enlightenments: noticeably slower timers, spinlocks and interrupts.",
                          "<features><hyperv mode='custom'><relaxed state='on'/><vapic state='on'/><spinlocks state='on' retries='8191'/>"
                          "<vpindex state='on'/><synic state='on'/><stimer state='on'/></hyperv></features>"))
        clock = d.find("clock")
        if clock is not None and clock.get("offset") == "utc":
            iss.append(_I("info", "config", "A Windows guest with the clock on UTC: Windows expects local time unless it is told otherwise.", "<clock offset='localtime'>"))
        if clock is None or clock.find("timer[@name='hypervclock']") is None:
            iss.append(_I("info", "speed", "No Hyper-V clock for the Windows guest.", "<timer name='hypervclock' present='yes'/>"))
    if d.find("devices/rng") is None:
        iss.append(_I("info", "config", "No virtio RNG: guests can stall at boot waiting for entropy.", "<rng model='virtio'><backend model='random'>/dev/urandom</backend></rng>"))
    if d.find("devices/channel/target[@name='org.qemu.guest_agent.0']") is None:
        iss.append(_I("info", "config", "No guest agent channel: no clean shutdown, freeze for snapshots or IP reporting.",
                      "<channel type='unix'><target type='virtio' name='org.qemu.guest_agent.0'/></channel>"))
    if d.find("devices/watchdog") is None and not windows:
        iss.append(_I("info", "config", "No watchdog: a hung guest stays hung.", "<watchdog model='i6300esb' action='reset'/>"))
    order = {"bad": 0, "warn": 1, "info": 2}
    iss.sort(key=lambda i: order[i["sev"]])
    counts = {s: sum(1 for i in iss if i["sev"] == s) for s in order}
    return {"name": name, "hypervisor": hv or "?", "machine": machine, "arch": arch, "vcpus": vcpus, "vcpus_current": int(cur) if (cur or "").isdigit() else vcpus,
            "memory_gib": gib, "cpu_mode": mode or (model and "custom") or "none", "cpu_model": model, "firmware": "UEFI" if uefi else "BIOS",
            "secure_boot": secure, "tpm": tpm, "hugepages": hp, "pinned": pinned, "windows": windows, "disks": disks, "nics": nics,
            "hostdev": len(hostdev), "migratable": migratable, "why_not": why_not, "issues": iss, "counts": counts,
            "verdict": (f"{name}: {vcpus} vCPUs, {gib:g} GiB" if gib else f"{name}: {vcpus} vCPUs") +
                       (f" - {counts['bad']} serious, {counts['warn']} to fix." if counts["bad"] or counts["warn"] else " - nothing serious found."),
            "note": "Read from the XML only: it does not see the host, its storage or the guest. Test a changed VM before you rely on it."}
