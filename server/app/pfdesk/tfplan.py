"""A Terraform (or OpenTofu) plan read before anyone types apply: what is created, changed, destroyed and replaced; data stores
and keys that would be destroyed or replaced (data lost); why a resource is replaced; network rules opened to the whole internet,
databases made public, policies that allow every action on every resource, encryption or deletion protection switched off,
tags her rules require. Reads `terraform show -json plan` output (full detail) or the plain `terraform plan` text (counts,
addresses, replacements)."""
from __future__ import annotations

import json
import re
from typing import Any

from .common import PfInputError, finder, finish


class TfError(PfInputError):
    pass


STATEFUL = ("db_instance", "rds_cluster", "rds_", "_database", "sql_database", "sql_server", "sql_instance", "db_cluster", "s3_bucket",
            "storage_bucket", "storage_account", "storage_container", "ebs_volume", "_disk", "volume", "efs_file_system", "filestore",
            "dynamodb_table", "kms_key", "key_vault", "elasticache", "redis", "memorystore", "cosmosdb", "bigquery_dataset", "bigquery_table",
            "bigtable", "spanner", "docdb", "neptune", "opensearch", "elasticsearch_domain", "redshift", "secretsmanager_secret",
            "secret_manager_secret", "kinesis_stream", "msk_cluster", "sqs_queue", "pubsub_topic", "backup_vault", "glacier")
SAFE_PORTS = {80, 443}


SETTINGS_OF = ("_policy", "_attachment", "_notification", "_versioning", "_lifecycle_configuration", "_public_access_block",
               "_server_side_encryption_configuration", "_acl", "_iam_member", "_iam_binding", "_cors_configuration", "_ownership_controls")


def stateful(rtype: str, extra: list[str]) -> bool:
    """A resource that holds data (destroying it loses the data); settings attached to one (its policy, ACL...) do not."""
    t = rtype.lower()
    if t.endswith(SETTINGS_OF):
        return any(t == e or t.startswith(e) for e in extra)
    return any(x in t for x in STATEFUL) or any(t == e or t.startswith(e) for e in extra)


def _kind(actions: list[str]) -> str:
    a = list(actions or [])
    if a in (["delete", "create"], ["create", "delete"]):
        return "replace"
    if a == ["create"]:
        return "create"
    if a == ["delete"]:
        return "delete"
    if a == ["update"]:
        return "update"
    if a in (["read"],):
        return "read"
    return "no-op"


def _walk(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def _ports(blk: dict[str, Any]) -> tuple[int | None, int | None]:
    fp, tp = blk.get("from_port"), blk.get("to_port")
    if fp is None and blk.get("port_range"):
        p = str(blk["port_range"]).split("-")
        fp, tp = p[0], p[-1]
    if fp is None and blk.get("destination_port_range"):
        p = str(blk["destination_port_range"]).replace("*", "0-65535").split("-")
        fp, tp = p[0], p[-1]
    try:
        return int(fp), int(tp)
    except (TypeError, ValueError):
        return None, None


def _policy_open(doc: Any) -> bool:
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except ValueError:
            return False
    if not isinstance(doc, dict):
        return False
    st = doc.get("Statement") or []
    st = st if isinstance(st, list) else [st]
    for s in st:
        if not isinstance(s, dict) or s.get("Effect", "Allow") != "Allow":
            continue
        a, r = s.get("Action"), s.get("Resource")
        a = a if isinstance(a, list) else [a]
        r = r if isinstance(r, list) else [r]
        if "*" in a and "*" in r:
            return True
    return False


def _checks(rc: dict[str, Any], add, required_tags: list[str]) -> None:
    addr, after = rc["address"], rc.get("after") or {}
    if not isinstance(after, dict):
        return
    open_ = []
    for path, v in _walk(after):
        if v in ("0.0.0.0/0", "::/0", "*", "Internet") and re.search(r"(cidr|source_address|source_ranges|address_prefix|ip_range)", path, re.I):
            parts = re.findall(r"[^.\[\]]+|\[\d+\]", path)
            while parts and parts[-1].startswith("["):
                parts.pop()
            parts = parts[:-1]   # the rule that holds the address, not the address list
            blk: Any = after
            for part in parts:
                blk = blk[int(part[1:-1])] if part.startswith("[") and isinstance(blk, list) else blk.get(part, {}) if isinstance(blk, dict) else {}
            if not isinstance(blk, dict):
                blk = {}
            egress = "egress" in path.lower() or str(blk.get("type", "")).lower() == "egress" or str(blk.get("direction", "")).lower() == "outbound"
            if egress:
                continue
            fp, tp = _ports(blk if isinstance(blk, dict) else {})
            if fp is None or not (fp == tp and fp in SAFE_PORTS):
                open_.append("all ports" if fp is None or (fp in (0, -1) and tp in (0, 65535, -1)) else f"port {fp}" + (f"-{tp}" if tp != fp else ""))
    if open_:
        add("bad", "Open to the internet", f"{addr} accepts traffic from anywhere on {', '.join(sorted(set(open_)))}.",
            "Limit it to known addresses, a VPN or a load balancer; keep only 80 / 443 public.", addr)
    if after.get("publicly_accessible") is True:
        add("bad", "Public", f"{addr} is set publicly_accessible - the database answers from the internet.", "Keep databases in private subnets.", addr)
    for k in ("block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"):
        if after.get(k) is False:
            add("warn", "Public", f"{addr}: {k} = false - the bucket can be made public.", "Leave all four public-access blocks on.", addr)
            break
    if str(after.get("acl", "")).startswith("public"):
        add("bad", "Public", f"{addr} has acl {after['acl']}.", "Use private and share through signed links or a CDN.", addr)
    for k in ("policy", "assume_role_policy", "inline_policy", "policy_document"):
        if k in after and _policy_open(after[k]):
            add("bad", "Permissions", f"{addr} allows every action on every resource (Action * on Resource *).", "Grant only the actions and resources it needs.", addr)
            break
    for k, word in (("storage_encrypted", "storage encryption"), ("encrypted", "encryption"), ("enable_key_rotation", "key rotation")):
        if after.get(k) is False:
            add("warn", "Encryption", f"{addr}: {word} is off.", "", addr)
    if after.get("deletion_protection") is False and stateful(rc["type"], []):
        add("warn", "Protection", f"{addr}: deletion protection is off.", "Turn it on for production data stores.", addr)
    if after.get("skip_final_snapshot") is True:
        add("warn", "Protection", f"{addr} skips the final snapshot - deleting it keeps no copy.", "", addr)
    if required_tags and "tags" in after and rc["kind"] in ("create", "update", "replace"):
        tags = after.get("tags_all") or after.get("tags") or {}
        miss = [t for t in required_tags if t not in (tags or {})]
        if miss:
            add("warn", "Tags", f"{addr} is missing tag(s): {', '.join(miss)}.", "Add them (or default_tags on the provider).", addr)


def _from_json(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for rc in d.get("resource_changes") or []:
        if rc.get("mode") == "data":
            continue
        ch = rc.get("change") or {}
        k = _kind(ch.get("actions") or [])
        rp = ch.get("replace_paths") or []
        out.append({"address": rc.get("address", ""), "type": rc.get("type", ""), "kind": k, "after": ch.get("after"), "before": ch.get("before"),
                    "why": [".".join(str(x) for x in p) for p in rp][:6], "reason": rc.get("action_reason", "")})
    return out


_HEAD = re.compile(r"^\s*#\s+(\S+)\s+(will be created|will be destroyed|will be updated in-place|must be replaced|will be read during apply|is tainted, so must be replaced|has moved to \S+)(.*)$")


def _from_text(t: str) -> tuple[list[dict[str, Any]], dict[str, int] | None]:
    out: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    summary = None
    for line in t.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)
        m = _HEAD.match(line)
        if m:
            addr, what = m.group(1), m.group(2)
            if what.startswith("has moved") or "read during" in what:
                cur = None
                continue
            k = {"will be created": "create", "will be destroyed": "delete", "will be updated in-place": "update"}.get(what, "replace")
            typ = re.sub(r"\[.*?\]", "", addr).split(".")
            typ = typ[-2] if len(typ) >= 2 else addr
            cur = {"address": addr, "type": typ, "kind": k, "after": None, "before": None, "why": [], "reason": "tainted" if "tainted" in what else ""}
            out.append(cur)
            continue
        if cur is not None and "# forces replacement" in line:
            w = line.split("#")[0].strip().lstrip("~+-/ ").split("=")[0].strip().strip('"')
            if w and len(cur["why"]) < 6:
                cur["why"].append(w)
        s = re.search(r"Plan:\s*(\d+) to add,\s*(\d+) to change,\s*(\d+) to destroy", line)
        if s:
            summary = {"add": int(s.group(1)), "change": int(s.group(2)), "destroy": int(s.group(3))}
    return out, summary


def analyse(text: str, max_destroy: float | None = None, protected: str = "", required_tags: str = "") -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise TfError("Paste the plan: `terraform show -json plan.out` (best) or the text `terraform plan` prints.")
    extra = [x.strip().lower() for x in str(protected or "").split(",") if x.strip()]
    req = [x.strip() for x in str(required_tags or "").split(",") if x.strip()]
    summary = None
    if t.startswith("{"):
        try:
            d = json.loads(t)
        except ValueError:
            raise TfError("That JSON could not be read - paste the output of `terraform show -json plan.out`.")
        if "resource_changes" not in d and "planned_values" not in d:
            raise TfError("That JSON is not a plan (no resource_changes) - use `terraform show -json plan.out`.")
        rcs, fmt = _from_json(d), "JSON plan"
        tfv = d.get("terraform_version", "")
    else:
        rcs, summary = _from_text(t)
        fmt, tfv = "plan text", ""
        if not rcs and not summary:
            if "No changes" in t:
                rcs = []
            else:
                raise TfError("No resource changes found - paste the full `terraform plan` output.")
    issues, add = finder()
    cnt = {k: sum(1 for r in rcs if r["kind"] == k) for k in ("create", "update", "delete", "replace")}
    if summary and fmt == "plan text":
        ex = {"add": cnt["create"] + cnt["replace"], "change": cnt["update"], "destroy": cnt["delete"] + cnt["replace"]}
        if ex != summary:
            add("info", "Plan", f"The plan's own line says {summary['add']} to add, {summary['change']} to change, {summary['destroy']} to destroy; "
                f"{len(rcs)} resource blocks were read from the text.", "Paste the whole plan (or the JSON) for full detail.")
    lost = []
    for r in rcs:
        if r["kind"] in ("delete", "replace") and stateful(r["type"], extra):
            lost.append(r)
            add("bad", "Data loss", f"{r['address']} would be {'destroyed' if r['kind'] == 'delete' else 'replaced (destroyed and created again)'} - the data in it goes with it."
                + (f" Replaced because of: {', '.join(r['why'])}." if r["why"] else ""),
                "Stop: add lifecycle { prevent_destroy = true }, use moved / import blocks if it was renamed, or change the attribute that forces replacement.", r["address"])
        elif r["kind"] == "replace":
            add("warn", "Replaced", f"{r['address']} will be destroyed and created again" + (f" (because of {', '.join(r['why'])})" if r["why"] else "") + " - expect a short outage.",
                "Use create_before_destroy where the provider allows it.", r["address"])
        if r["kind"] != "delete":
            _checks(r, add, req)
    destroys = cnt["delete"] + cnt["replace"]
    if max_destroy is not None and max_destroy >= 0 and destroys > max_destroy:
        add("bad", "Destroys", f"{destroys} resource(s) would be destroyed - over your limit of {max_destroy:g}.", "Check it is not a renamed module or a wrong workspace / state.")
    if cnt["delete"] >= 10 and cnt["create"] >= 10 and fmt == "JSON plan":
        add("warn", "Renames?", f"{cnt['delete']} destroyed and {cnt['create']} created together - often a module renamed or moved.", "Add moved { from = ..., to = ... } blocks instead.")
    types: dict[str, dict[str, int]] = {}
    for r in rcs:
        types.setdefault(r["type"], {"create": 0, "update": 0, "delete": 0, "replace": 0})
        if r["kind"] in types[r["type"]]:
            types[r["type"]][r["kind"]] += 1
    res: dict[str, Any] = {"format": fmt, "terraform": tfv, "actions": cnt, "changes": [{k: r[k] for k in ("address", "type", "kind", "why", "reason")} | {"stateful": stateful(r["type"], extra)}
                                                                                    for r in rcs if r["kind"] in ("create", "update", "delete", "replace")][:500],
           "types": types, "lost": [r["address"] for r in lost], "summary": summary}
    res["verdict"] = ("No changes" if not any(cnt.values()) else
                      f"{cnt['create']} to create, {cnt['update']} to change, {cnt['replace']} to replace, {cnt['delete']} to destroy") + (f" - {len(lost)} data store(s) at risk" if lost else "")
    res["note"] = ("Read from the plan only - it shows what Terraform intends, not what the cloud allows. " + ("The text plan carries no values: paste the JSON (`terraform show -json`) to check network rules, policies and tags." if fmt == "plan text" else ""))
    return finish(res, issues)
