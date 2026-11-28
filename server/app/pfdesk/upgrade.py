"""Kubernetes manifests checked before a cluster upgrade: every object's apiVersion and kind against the API versions Kubernetes
removed (from its deprecated API migration guide), so what would stop applying after the upgrade - and what goes in the next
releases - is named with the version to move to and what else changes. Reads plain manifests, many documents, `kubectl get -o
yaml` lists and Helm template output. Also counts what it read by kind."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

import yaml

from .common import PfInputError, finder, finish


class UpgradeError(PfInputError):
    pass


# (group/version, kinds or None for every kind in it, removed in 1.x, replacement, what else changes)
REMOVED: list[tuple[str, tuple[str, ...] | None, int, str, str]] = [
    ("extensions/v1beta1", ("Deployment", "DaemonSet", "ReplicaSet"), 16, "apps/v1", "spec.selector is required and cannot change"),
    ("apps/v1beta1", ("Deployment", "StatefulSet", "ReplicaSet"), 16, "apps/v1", "spec.selector is required and cannot change"),
    ("apps/v1beta2", ("Deployment", "DaemonSet", "StatefulSet", "ReplicaSet"), 16, "apps/v1", "spec.selector is required and cannot change"),
    ("extensions/v1beta1", ("NetworkPolicy",), 16, "networking.k8s.io/v1", ""),
    ("extensions/v1beta1", ("PodSecurityPolicy",), 16, "policy/v1beta1 (itself removed in 1.25)", ""),
    ("extensions/v1beta1", ("Ingress",), 22, "networking.k8s.io/v1", "backend.serviceName / servicePort become backend.service.name / port.number; pathType is required"),
    ("networking.k8s.io/v1beta1", ("Ingress",), 22, "networking.k8s.io/v1", "backend.serviceName / servicePort become backend.service.name / port.number; pathType is required"),
    ("networking.k8s.io/v1beta1", ("IngressClass",), 22, "networking.k8s.io/v1", ""),
    ("apiextensions.k8s.io/v1beta1", ("CustomResourceDefinition",), 22, "apiextensions.k8s.io/v1", "a structural schema is required; spec.version becomes spec.versions"),
    ("admissionregistration.k8s.io/v1beta1", ("MutatingWebhookConfiguration", "ValidatingWebhookConfiguration"), 22, "admissionregistration.k8s.io/v1",
     "sideEffects and admissionReviewVersions are required; failurePolicy defaults to Fail"),
    ("apiregistration.k8s.io/v1beta1", ("APIService",), 22, "apiregistration.k8s.io/v1", ""),
    ("authentication.k8s.io/v1beta1", ("TokenReview",), 22, "authentication.k8s.io/v1", ""),
    ("authorization.k8s.io/v1beta1", None, 22, "authorization.k8s.io/v1", "spec.group becomes spec.groups"),
    ("certificates.k8s.io/v1beta1", ("CertificateSigningRequest",), 22, "certificates.k8s.io/v1", "spec.signerName is required"),
    ("coordination.k8s.io/v1beta1", ("Lease",), 22, "coordination.k8s.io/v1", ""),
    ("rbac.authorization.k8s.io/v1beta1", None, 22, "rbac.authorization.k8s.io/v1", ""),
    ("scheduling.k8s.io/v1beta1", ("PriorityClass",), 22, "scheduling.k8s.io/v1", ""),
    ("storage.k8s.io/v1beta1", ("CSIDriver", "CSINode", "StorageClass", "VolumeAttachment"), 22, "storage.k8s.io/v1", ""),
    ("batch/v1beta1", ("CronJob",), 25, "batch/v1", ""),
    ("discovery.k8s.io/v1beta1", ("EndpointSlice",), 25, "discovery.k8s.io/v1", "topology becomes zone / hints per endpoint"),
    ("events.k8s.io/v1beta1", ("Event",), 25, "events.k8s.io/v1", ""),
    ("autoscaling/v2beta1", ("HorizontalPodAutoscaler",), 25, "autoscaling/v2", "targetAverageUtilization becomes target.averageUtilization"),
    ("policy/v1beta1", ("PodDisruptionBudget",), 25, "policy/v1", "an empty selector now selects every pod in the namespace"),
    ("policy/v1beta1", ("PodSecurityPolicy",), 25, "(none - use Pod Security Admission)", "label namespaces with pod-security.kubernetes.io/enforce"),
    ("node.k8s.io/v1beta1", ("RuntimeClass",), 25, "node.k8s.io/v1", ""),
    ("flowcontrol.apiserver.k8s.io/v1beta1", ("FlowSchema", "PriorityLevelConfiguration"), 26, "flowcontrol.apiserver.k8s.io/v1", ""),
    ("autoscaling/v2beta2", ("HorizontalPodAutoscaler",), 26, "autoscaling/v2", ""),
    ("storage.k8s.io/v1beta1", ("CSIStorageCapacity",), 27, "storage.k8s.io/v1", ""),
    ("flowcontrol.apiserver.k8s.io/v1beta2", ("FlowSchema", "PriorityLevelConfiguration"), 29, "flowcontrol.apiserver.k8s.io/v1", ""),
    ("flowcontrol.apiserver.k8s.io/v1beta3", ("FlowSchema", "PriorityLevelConfiguration"), 32, "flowcontrol.apiserver.k8s.io/v1", ""),
]


def minor(v: Any) -> int:
    m = re.fullmatch(r"\s*v?1\.(\d{1,2})(\.\d+)?\s*", str(v or ""))
    if not m:
        raise UpgradeError(f"'{v}' is not a Kubernetes version like 1.31.")
    return int(m.group(1))


def _objects(text: str) -> list[dict[str, Any]]:
    t = str(text or "").strip()
    if not t:
        raise UpgradeError("Paste the manifests: YAML (many documents with ---), `kubectl get ... -o yaml` or `helm template` output.")
    t = re.sub(r"(?m)^#\s*Source:.*$", "", t)
    try:
        docs = [d for d in yaml.safe_load_all(t) if d]
    except yaml.YAMLError as e:
        raise UpgradeError(f"The YAML could not be read: {str(e).splitlines()[0][:120]}")
    out = []
    for d in docs:
        if not isinstance(d, dict):
            continue
        if d.get("kind", "").endswith("List") and isinstance(d.get("items"), list):
            out += [x for x in d["items"] if isinstance(x, dict)]
        else:
            out.append(d)
    out = [o for o in out if o.get("apiVersion") and o.get("kind")]
    if not out:
        raise UpgradeError("No Kubernetes objects found (each needs apiVersion and kind).")
    return out


def check(text: str, current: Any = "", target: Any = "") -> dict[str, Any]:
    objs = _objects(text)
    tg = minor(target) if str(target or "").strip() else None
    cu = minor(current) if str(current or "").strip() else None
    if tg is not None and cu is not None and tg < cu:
        raise UpgradeError("The target version is older than the current one.")
    issues, add = finder()
    found = []
    for o in objs:
        av, kind = o["apiVersion"], o["kind"]
        md = o.get("metadata") or {}
        name = (md.get("namespace") + "/" if md.get("namespace") else "") + str(md.get("name", "?"))
        for gv, kinds, rem, to, note in REMOVED:
            if av == gv and (kinds is None or kind in kinds):
                when = "already gone" if cu is not None and rem <= cu else ("breaks at the target" if tg is not None and rem <= tg else "removed later")
                found.append({"kind": kind, "name": name, "api": av, "removed": f"1.{rem}", "to": to, "note": note, "when": when, "rem": rem})
                break
    found.sort(key=lambda f: (f["rem"], f["kind"], f["name"]))
    gone = [f for f in found if f["when"] == "already gone"]
    breaks = [f for f in found if f["when"] == "breaks at the target"]
    later = [f for f in found if f["when"] == "removed later"]
    if gone:
        add("bad", "Already removed", f"{len(gone)} object(s) use APIs your cluster ({'1.' + str(cu)}) no longer serves, e.g. {gone[0]['kind']} {gone[0]['name']} ({gone[0]['api']}).",
            "They fail to apply today - move them to the versions listed.")
    if breaks:
        add("bad", "Breaks the upgrade", f"{len(breaks)} object(s) use APIs removed by 1.{tg}, e.g. {breaks[0]['kind']} {breaks[0]['name']} ({breaks[0]['api']}, removed in {breaks[0]['removed']}).",
            "Move them before upgrading; objects already stored are served in the new version, but these files (and any Helm chart or GitOps repo holding them) will stop applying.")
    if later:
        add("warn" if tg is None else "info", "Removed later", f"{len(later)} object(s) use APIs removed in a later release ({', '.join(sorted({f['removed'] for f in later}))}).",
            "Move them now while both versions are served.")
    if tg is None and found:
        add("info", "Target", "No target version given - every removal is listed.", "Set the target (e.g. 1.31) to see what breaks at that upgrade.")
    if tg is not None and cu is not None and tg - cu > 1:
        add("info", "Skips", f"1.{cu} -> 1.{tg} is {tg - cu} minor versions: the control plane upgrades one minor version at a time.", "Plan each step; nodes may lag the control plane by at most three minor versions on current releases.")
    kinds = Counter(o["kind"] for o in objs)
    res = {"objects": len(objs), "kinds": kinds.most_common(), "found": found, "gone": len(gone), "breaks": len(breaks), "later": len(later),
           "current": f"1.{cu}" if cu is not None else "", "target": f"1.{tg}" if tg is not None else "",
           "verdict": (f"{len(breaks) + len(gone)} object(s) stop working at 1.{tg}" if tg is not None and (breaks or gone) else
                       f"Nothing in these {len(objs)} objects is removed by 1.{tg}" if tg is not None else
                       f"{len(found)} object(s) on removed or soon-removed APIs among {len(objs)}")}
    res["note"] = ("Checked against the API removals listed in the Kubernetes deprecated API migration guide up to 1.32 - check the guide for your "
                   "target, and add-ons (Ingress controllers, CRDs from operators) for their own removals. Only the files you pasted are checked; "
                   "`kubectl get` of the live cluster or a tool such as pluto also finds objects applied from elsewhere.")
    return finish(res, issues)
