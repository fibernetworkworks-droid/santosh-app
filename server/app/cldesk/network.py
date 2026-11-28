"""Cloud networks checked before they are built or joined: address ranges for networks (VPC / VNet) and subnets, checked for
subnets outside their network, subnets that overlap, networks that overlap each other (they cannot be peered or joined through a
transit hub), public address space used privately, subnets below the provider's smallest size, the addresses each subnet really
gives (the provider keeps some), and the space left free; firewall and security group rules that let the internet reach admin and
database ports; and a plan that splits a range across zones and tiers. Lines, or AWS `describe-security-groups` / Google Cloud
`firewall-rules list` JSON."""
from __future__ import annotations

import ipaddress as ip
import json
import math
import re
from typing import Any

from .common import ClInputError, finder, finish


class NetError(ClInputError):
    pass


RESERVED = {"aws": 5, "azure": 5, "gcp": 4, "other": 2}
SMALLEST = {"aws": 28, "azure": 29, "gcp": 29, "other": 30}
ADMIN = {22: "SSH", 3389: "RDP", 23: "Telnet", 5985: "WinRM", 5986: "WinRM", 3306: "MySQL", 5432: "PostgreSQL", 1433: "SQL Server", 1521: "Oracle",
         6379: "Redis", 27017: "MongoDB", 9200: "Elasticsearch", 5601: "Kibana", 11211: "Memcached", 2375: "Docker API", 2379: "etcd",
         6443: "Kubernetes API", 10250: "kubelet", 9092: "Kafka", 5672: "RabbitMQ", 8080: "HTTP admin", 445: "SMB", 135: "RPC", 161: "SNMP"}
WEB = {80, 443}
PRIVATE = [ip.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "fd00::/8")]


def _net(v: str, where: str) -> ip._BaseNetwork:
    try:
        return ip.ip_network(v.strip(), strict=True)
    except ValueError:
        try:
            n = ip.ip_network(v.strip(), strict=False)
        except ValueError:
            raise NetError(f"{where}: '{v}' is not an address range (10.0.0.0/16).")
        raise NetError(f"{where}: '{v}' has host bits set - the range starts at {n.network_address} ({n}).")


def _ports(v: str) -> list[tuple[int, int]]:
    s = str(v or "").strip().lower()
    if s in ("", "all", "any", "*", "-1", "0-65535", "1-65535"):
        return [(0, 65535)]
    out = []
    for p in re.split(r"[,; ]+", s):
        if not p:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", p)
        if not m:
            raise NetError(f"'{v}' is not a port list (22, 80,443, 8000-8100, all).")
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        out.append((min(a, b), max(a, b)))
    return out


def _json_rules(data: Any) -> list[dict[str, Any]]:
    out = []
    if isinstance(data, dict) and "SecurityGroups" in data:
        for g in data["SecurityGroups"]:
            nm = g.get("GroupName") or g.get("GroupId")
            for d, k in (("in", "IpPermissions"), ("out", "IpPermissionsEgress")):
                for p in g.get(k) or []:
                    proto = str(p.get("IpProtocol", "-1"))
                    ports = [(0, 65535)] if proto == "-1" or p.get("FromPort") in (None, -1) else [(int(p["FromPort"]), int(p["ToPort"]))]
                    srcs = [x.get("CidrIp") for x in p.get("IpRanges") or []] + [x.get("CidrIpv6") for x in p.get("Ipv6Ranges") or []]
                    for sr in srcs:
                        if sr:
                            out.append({"name": nm, "dir": d, "proto": "all" if proto == "-1" else proto, "ports": ports, "src": sr})
    elif isinstance(data, list) and data and isinstance(data[0], dict) and ("sourceRanges" in data[0] or "allowed" in data[0]):
        for r in data:
            if r.get("disabled"):
                continue
            d = "in" if str(r.get("direction", "INGRESS")).upper() == "INGRESS" else "out"
            for a in r.get("allowed") or []:
                proto = str(a.get("IPProtocol", "all"))
                ports = [] if a.get("ports") else [(0, 65535)]
                for p in a.get("ports") or []:
                    ports += _ports(p)
                for sr in r.get("sourceRanges") or (r.get("destinationRanges") or []):
                    out.append({"name": r.get("name"), "dir": d, "proto": proto, "ports": ports, "src": sr})
    else:
        raise NetError("This JSON is not `aws ec2 describe-security-groups` or `gcloud compute firewall-rules list --format=json` output.")
    return out


def analyse(text: str, provider: str = "aws") -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise NetError("Describe the network: 'vpc prod 10.0.0.0/16', 'subnet app-a 10.0.1.0/24 vpc=prod zone=a', 'rule web in tcp 22 0.0.0.0/0', 'plan 10.20.0.0/16 zones=3 tiers=public,private,data'.")
    prov = (provider or "aws").lower()
    if prov not in RESERVED:
        prov = "other"
    vpcs: list[dict[str, Any]] = []
    subs: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    if t[:1] in "[{":
        try:
            rules = _json_rules(json.loads(t))
        except ValueError as e:
            raise NetError(f"The JSON could not be read: {e}")
    else:
        for n, line in enumerate(t.splitlines(), 1):
            s = line.split("#", 1)[0].strip()
            if not s:
                continue
            parts = s.split()
            word = parts[0].lower()
            kv = {k.lower(): v for k, v in (p.split("=", 1) for p in parts[1:] if "=" in p)}
            pos = [p for p in parts[1:] if "=" not in p]
            where = f"line {n}"
            if word in ("vpc", "vnet", "network"):
                if not pos:
                    raise NetError(f"{where}: vpc <name> <range>.")
                name, rng = (pos[0], pos[1]) if len(pos) > 1 else (f"network {len(vpcs) + 1}", pos[0])
                extra = [_net(x, where) for x in pos[2:]]
                vpcs.append({"name": name, "cidr": [_net(rng, where)] + extra, "provider": kv.get("provider", prov).lower()})
            elif word == "subnet":
                if not pos:
                    raise NetError(f"{where}: subnet <name> <range> vpc=<network> zone=<zone>.")
                name, rng = (pos[0], pos[1]) if len(pos) > 1 else (f"subnet {len(subs) + 1}", pos[0])
                subs.append({"name": name, "cidr": _net(rng, where), "vpc": kv.get("vpc") or kv.get("network") or "", "zone": kv.get("zone", ""), "line": n})
            elif word == "rule":
                if len(pos) < 5:
                    raise NetError(f"{where}: rule <name> in|out <protocol> <ports> <source range>.")
                d = "in" if pos[1].lower() in ("in", "ingress", "inbound") else "out"
                rules.append({"name": pos[0], "dir": d, "proto": pos[2].lower(), "ports": _ports(pos[3]), "src": pos[4]})
            elif word == "plan":
                if not pos:
                    raise NetError(f"{where}: plan <range> zones=3 tiers=public,private,data spare=1.")
                plans.append({"cidr": _net(pos[0], where), "zones": int(kv.get("zones", 3)), "tiers": [x for x in kv.get("tiers", "public,private").split(",") if x],
                              "spare": int(kv.get("spare", 1))})
            else:
                raise NetError(f"{where}: start with vpc, subnet, rule or plan.")
    issues, add = finder()
    # networks
    for v in vpcs:
        p = v["provider"] if v["provider"] in RESERVED else "other"
        for c in v["cidr"]:
            if not any(c.subnet_of(x) for x in PRIVATE if x.version == c.version):
                add("warn", "Public range", f"{v['name']} uses {c} - addresses that belong to someone on the internet; traffic to them will go to you instead.",
                    "Use 10.0.0.0/8, 172.16.0.0/12 or 192.168.0.0/16.", v["name"])
    for i, a in enumerate(vpcs):
        for b in vpcs[i + 1:]:
            for x in a["cidr"]:
                for y in b["cidr"]:
                    if x.version == y.version and x.overlaps(y):
                        add("bad", "Networks overlap", f"{a['name']} {x} and {b['name']} {y} overlap - they cannot be peered or joined through a transit hub.",
                            "Re-address one before they need to talk; plan one range per network across every account and region.", a["name"])
    byname = {v["name"]: v for v in vpcs}
    rows = []
    for s in subs:
        v = byname.get(s["vpc"]) if s["vpc"] else next((x for x in vpcs if any(s["cidr"].version == c.version and s["cidr"].subnet_of(c) for c in x["cidr"])), None)
        p = (v["provider"] if v else prov)
        p = p if p in RESERVED else "other"
        size = s["cidr"].num_addresses
        res_n = RESERVED[p] if s["cidr"].version == 4 else 0
        row = {"name": s["name"], "cidr": str(s["cidr"]), "vpc": v["name"] if v else "", "zone": s["zone"], "size": size, "usable": max(0, size - res_n),
               "provider": p, "flags": []}
        if s["vpc"] and not v:
            row["flags"].append("unknown network")
            add("warn", "Unknown network", f"{s['name']} names network '{s['vpc']}' which is not described.", "Add a vpc line for it.", s["name"])
        if v and not any(s["cidr"].version == c.version and s["cidr"].subnet_of(c) for c in v["cidr"]):
            row["flags"].append("outside its network")
            add("bad", "Outside its network", f"{s['name']} {s['cidr']} is not inside {v['name']} ({', '.join(map(str, v['cidr']))}).", "Pick a range inside the network.", s["name"])
        if s["cidr"].version == 4 and s["cidr"].prefixlen > SMALLEST[p]:
            row["flags"].append("too small")
            add("bad", "Too small", f"{s['name']} is a /{s['cidr'].prefixlen}; {p.upper() if p != 'other' else 'the provider'} allows /{SMALLEST[p]} at the smallest.",
                f"Use at least a /{SMALLEST[p]}.", s["name"])
        rows.append(row)
    for i, a in enumerate(subs):
        for b in subs[i + 1:]:
            if a["cidr"].version == b["cidr"].version and a["cidr"].overlaps(b["cidr"]):
                add("bad", "Subnets overlap", f"{a['name']} {a['cidr']} and {b['name']} {b['cidr']} overlap.", "Give one of them a range of its own.", a["name"])
                next(r for r in rows if r["name"] == a["name"])["flags"].append("overlap")
                next(r for r in rows if r["name"] == b["name"])["flags"].append("overlap")
    space = []
    for v in vpcs:
        for c in v["cidr"]:
            inside = sorted({x["cidr"] for x in subs if x["cidr"].version == c.version and x["cidr"].subnet_of(c)}, key=lambda n: (n.network_address, n.prefixlen))
            free = [c]
            for sn in inside:
                nxt = []
                for f in free:
                    if sn.subnet_of(f):
                        nxt += list(f.address_exclude(sn)) if sn != f else []
                    elif f.subnet_of(sn):
                        continue
                    else:
                        nxt.append(f)
                free = nxt
            used = sum(sn.num_addresses for sn in ip.collapse_addresses(inside)) if inside else 0
            free = sorted(free, key=lambda n: (n.network_address, n.prefixlen))
            space.append({"vpc": v["name"], "cidr": str(c), "size": c.num_addresses, "used": used, "used_pct": used / c.num_addresses,
                          "free": [str(f) for f in ip.collapse_addresses(free)][:24], "largest_free": max((f.num_addresses for f in free), default=0)})
            if c.version == 4 and used / c.num_addresses > 0.85:
                add("warn", "Network nearly full", f"{v['name']} {c}: {used / c.num_addresses * 100:.0f}% given to subnets - little room for new zones or tiers.",
                    "Add a second range to the network, or plan a larger one.", v["name"])
    # rules
    rrows = []
    for r in rules:
        open_net = r["src"] in ("0.0.0.0/0", "::/0", "*", "any", "internet", "Internet")
        hits = []
        for a, b in r["ports"]:
            for p_, nm in ADMIN.items():
                if a <= p_ <= b:
                    hits.append(f"{nm} {p_}")
        every = any(a <= 1 and b >= 65535 for a, b in r["ports"])
        flags = []
        if r["dir"] == "in" and open_net:
            if every:
                flags.append("all ports to the internet")
                add("bad", "Everything open", f"{r['name']} lets the internet reach every port.", "Allow only the ports the service serves, from the ranges that need them.", r["name"])
            elif hits:
                flags.append("admin port to the internet")
                add("bad", "Admin port open", f"{r['name']} lets the internet reach {', '.join(hits[:4])}.",
                    "Close it to the internet - use a bastion, a VPN, or the provider's session manager.", r["name"])
            elif not all(a in WEB and b in WEB for a, b in r["ports"]):
                flags.append("internet")
                add("warn", "Open to the internet", f"{r['name']} lets the internet reach {', '.join(f'{a}' if a == b else f'{a}-{b}' for a, b in r['ports'])}.",
                    "Check this port is meant to be public.", r["name"])
        rrows.append({"name": r["name"], "dir": r["dir"], "proto": r["proto"], "ports": ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in r["ports"]),
                      "src": r["src"], "flags": flags})
    # plans
    plan_out = []
    for p in plans:
        need = p["zones"] * len(p["tiers"])
        bits = math.ceil(math.log2(max(1, need))) + max(0, p["spare"])
        newp = p["cidr"].prefixlen + bits
        if newp > SMALLEST.get(prov, 30):
            raise NetError(f"{p['cidr']} is too small for {need} subnets with spare room - start from a larger range.")
        nets = list(p["cidr"].subnets(new_prefix=newp))
        out = []
        k = 0
        for tier in p["tiers"]:
            for z in range(p["zones"]):
                sn = nets[k]
                out.append({"tier": tier, "zone": chr(ord("a") + z), "cidr": str(sn), "usable": sn.num_addresses - (RESERVED[prov] if sn.version == 4 else 0)})
                k += 1
        plan_out.append({"cidr": str(p["cidr"]), "prefix": newp, "subnets": out, "spare": [str(n) for n in nets[k:]][:16], "spare_count": len(nets) - k})
    if not (vpcs or subs or rules or plans):
        raise NetError("Nothing to check - use vpc, subnet, rule or plan lines.")
    res = {"provider": prov, "vpcs": [{"name": v["name"], "cidr": [str(c) for c in v["cidr"]], "provider": v["provider"]} for v in vpcs], "subnets": rows,
           "space": space, "rules": rrows, "plans": plan_out, "verdict": f"{len(vpcs)} network(s), {len(subs)} subnet(s), {len(rules)} rule(s)"
           + (f", {len(plans)} plan(s)" if plans else "")}
    res["note"] = (f"Usable addresses take off what the provider keeps in each subnet (AWS and Azure 5, Google Cloud 4). Rules are checked one by one - "
                   "a deny elsewhere or a network ACL can still block what a rule allows.")
    return finish(res, issues)
