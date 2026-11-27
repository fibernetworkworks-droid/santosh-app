"""A light GLSL / WGSL / HLSL check in code: the mistakes that compile on one driver and fail on another, or that are slow or wrong
everywhere. It is NOT a compiler - the real compile is her browser's WebGL2 (on the page) or her own toolchain (glslang, DXC, naga),
and this says so. A shader is DATA, never instructions."""
from __future__ import annotations

import re
from typing import Any

MAX = 200_000
LANGS = ("glsl", "wgsl", "hlsl")


def lang_of(src: str) -> str:
    if re.search(r"@(?:vertex|fragment|compute)\b|\bfn\s+\w+\s*\(|var<", src):
        return "wgsl"
    if re.search(r"\b(?:float4|SV_Target|SV_Position|cbuffer|Texture2D|SamplerState)\b", src):
        return "hlsl"
    return "glsl"


def _strip(src: str) -> str:
    """Comments out (lines kept, so line numbers stay right)."""
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


RULES_GLSL: list[tuple[str, str, str, str]] = [
    (r"\bgl_FragColor\b", "error", "gl_FragColor is removed in GLSL ES 3.00 (#version 300 es): declare `out vec4 fragColor;` and write to it.", "es3"),
    (r"\btexture2D\s*\(|\btextureCube\s*\(", "error", "texture2D / textureCube are removed in GLSL ES 3.00: use texture().", "es3"),
    (r"\bvarying\b|\battribute\b", "error", "varying / attribute are removed in GLSL ES 3.00: use in / out.", "es3"),
    (r"==\s*\d+\.\d*\b|\b\d+\.\d*\s*==", "warning", "Comparing a float with == rarely holds after maths: compare with a small tolerance (abs(a - b) < 1e-4).", ""),
    (r"\bpow\s*\(\s*[-\w.]+\s*,", "info", "pow(x, y) is undefined for x < 0 and for x = 0 with y <= 0: clamp x with max(x, 0.0) if it can be negative.", ""),
    (r"/\s*length\s*\(", "warning", "Dividing by length() gives NaN for a zero vector: use normalize() on a vector you know is not zero, or add a small epsilon.", ""),
    (r"\bnormalize\s*\(\s*vec3\s*\(\s*0", "error", "normalize of a zero vector is NaN.", ""),
    (r"\bdiscard\b", "info", "discard turns off early depth testing on many GPUs: fine for cut-outs, slow for big areas.", ""),
    (r"\bfor\s*\([^;]*;[^;]*\b(?:u_\w+|uniform\w*|i?Count\w*)\b", "info", "A loop bound from a uniform cannot be unrolled; on older mobile GPUs it may fail to compile.", ""),
    (r"\bsqrt\s*\(\s*[^)]*-", "info", "sqrt of a negative number is NaN: clamp with max(x, 0.0).", ""),
    (r"\b(?:highp|mediump)\s+float\s+\w+\s*=\s*\d{5,}", "warning", "A large constant can lose precision in mediump on mobile GPUs.", ""),
    (r"\bgl_FragCoord\.xy\s*/\s*\d", "warning", "Dividing gl_FragCoord by a fixed number assumes one screen size: pass the resolution as a uniform.", ""),
]
RULES_WGSL: list[tuple[str, str, str, str]] = [
    (r"\bvar\s+\w+\s*:\s*array<[^>]*>\s*;", "info", "A runtime-sized array must be in a storage buffer binding.", ""),
    (r"==\s*\d+\.\d*\b", "warning", "Comparing a float with == rarely holds after maths: compare with a small tolerance.", ""),
    (r"/\s*length\s*\(", "warning", "Dividing by length() gives NaN for a zero vector.", ""),
    (r"\bdiscard\s*;", "info", "discard turns off early depth testing on many GPUs.", ""),
]
RULES_HLSL: list[tuple[str, str, str, str]] = [
    (r"==\s*\d+\.\d*\b", "warning", "Comparing a float with == rarely holds after maths: compare with a small tolerance.", ""),
    (r"/\s*length\s*\(", "warning", "Dividing by length() gives NaN for a zero vector.", ""),
    (r"\bclip\s*\(", "info", "clip() turns off early depth testing on many GPUs.", ""),
    (r"\btex2D\s*\(", "warning", "tex2D is Shader Model 3 style: use Texture2D.Sample() with a SamplerState.", ""),
]


def lint(src: str, lang: str = "", stage: str = "fragment") -> dict[str, Any]:
    src = str(src or "")[:MAX]
    if not src.strip():
        return {"ok": False, "error": "Paste the shader first."}
    lang = lang if lang in LANGS else lang_of(src)
    body = _strip(src)
    lines = body.split("\n")
    issues: list[dict[str, Any]] = []
    rules = {"glsl": RULES_GLSL, "wgsl": RULES_WGSL, "hlsl": RULES_HLSL}[lang]
    ver = ""
    if lang == "glsl":
        first = next((ln.strip() for ln in src.split("\n") if ln.strip()), "")
        m = re.match(r"#version\s+(\d+)\s*(es)?", first)
        ver = (m.group(1) + (" es" if m.group(2) else "")) if m else ""
        if not m and "#version" in src:
            issues.append({"line": 1, "sev": "error", "text": "#version must be the very first line (nothing before it, not even a blank line in WebGL)."})
        if not ver:
            issues.append({"line": 1, "sev": "info", "text": "No #version: WebGL2 needs `#version 300 es` on the first line."})
        es3 = ver.startswith("300") or ver.startswith("310") or ver.startswith("320")
        if es3 and stage == "fragment" and not re.search(r"\bprecision\s+(?:lowp|mediump|highp)\s+float\s*;", body):
            issues.append({"line": 1, "sev": "error", "text": "A GLSL ES fragment shader needs a default float precision: `precision highp float;`."})
        if es3 and stage == "fragment" and not re.search(r"\bout\s+(?:lowp\s+|mediump\s+|highp\s+)?vec4\s+\w+\s*;", body) and "gl_FragColor" not in body:
            issues.append({"line": 1, "sev": "error", "text": "No `out vec4` colour output declared."})
        if not re.search(r"\bvoid\s+main\s*\(\s*(?:void)?\s*\)", body):
            issues.append({"line": 1, "sev": "error", "text": "No `void main()`."})
    else:
        es3 = False
    for i, ln in enumerate(lines, 1):
        for rx, sev, text, need in rules:
            if need == "es3" and not es3:
                continue
            if re.search(rx, ln):
                issues.append({"line": i, "sev": sev, "text": text, "code": src.split("\n")[i - 1].strip()[:160]})
    # unused uniforms
    for m in re.finditer(r"\buniform\s+(?:lowp\s+|mediump\s+|highp\s+)?\w+\s+(\w+)\s*(?:\[[^\]]*\])?\s*;", body):
        name = m.group(1)
        if len(re.findall(r"\b" + re.escape(name) + r"\b", body)) == 1:
            ln = body[:m.start()].count("\n") + 1
            issues.append({"line": ln, "sev": "warning", "text": f"Uniform `{name}` is declared but never used: the compiler removes it and "
                                                                    "getUniformLocation returns null."})
    # brace balance
    if body.count("{") != body.count("}"):
        issues.append({"line": len(lines), "sev": "error", "text": f"Braces do not match: {body.count('{')} open, {body.count('}')} close."})
    if body.count("(") != body.count(")"):
        issues.append({"line": len(lines), "sev": "error", "text": "Parentheses do not match."})
    order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda x: (order[x["sev"]], x["line"]))
    counts = {k: sum(1 for x in issues if x["sev"] == k) for k in order}
    return {"ok": True, "lang": lang, "version": ver, "stage": stage, "lines": len(lines), "issues": issues[:200], "counts": counts,
            "note": "A check in code, not a compiler: the real compile is WebGL2 in your browser (Run on the page) or your own glslang / DXC / "
                    "naga.",
            "verdict": ("No problems found by the check." if not issues else
                        f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} note(s).")}


STARTER = """#version 300 es
precision highp float;
uniform vec2 u_res;
uniform float u_time;
out vec4 fragColor;

// Hoola starter: a lit sphere, ray-marched. Change anything and press Run.
float sdSphere(vec3 p, float r) { return length(p) - r; }

void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - u_res) / u_res.y;
    vec3 ro = vec3(0.0, 0.0, 3.0);
    vec3 rd = normalize(vec3(uv, -1.6));
    float t = 0.0;
    for (int i = 0; i < 96; i++) {
        float d = sdSphere(ro + rd * t, 1.0);
        if (d < 0.001 || t > 20.0) break;
        t += d;
    }
    vec3 col = mix(vec3(0.06, 0.07, 0.1), vec3(0.18, 0.2, 0.28), uv.y * 0.5 + 0.5);
    if (t < 20.0) {
        vec3 p = ro + rd * t;
        vec3 n = normalize(p);
        vec3 l = normalize(vec3(cos(u_time), 0.8, sin(u_time)));
        float diff = max(dot(n, l), 0.0);
        float spec = pow(max(dot(reflect(-l, n), -rd), 0.0), 32.0);
        col = vec3(0.85, 0.45, 0.25) * (0.12 + diff) + spec;
    }
    fragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
}
"""
