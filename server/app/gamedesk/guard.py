"""What a game script may not do. The game runs in the browsers of HER players, so it never talks to the network,
never reads or writes files outside its own save slot, never runs programs and never reaches into the page.
The build box also has no network; this check makes the refusal plain and early."""
from __future__ import annotations

import re

NAME = re.compile(r"^[a-z][a-z0-9_]{0,40}\.gd$")
MAX_FILES = 12
MAX_CHARS = 120_000

BANNED = [
    (r"\bOS\s*\.\s*(execute|execute_with_pipe|create_process|create_instance|shell_open|shell_show_in_file_manager|kill|"
     r"get_environment|set_environment|unset_environment|move_to_trash|crash)\b", "programs / environment of the computer"),
    (r"\b(HTTPRequest|HTTPClient|StreamPeerTCP|StreamPeerTLS|TCPServer|UDPServer|PacketPeerUDP|PacketPeerDTLS|"
     r"DTLSServer|WebSocketPeer|WebSocketMultiplayerPeer|WebRTCPeerConnection|WebRTCMultiplayerPeer|"
     r"WebRTCDataChannel|ENetConnection|ENetMultiplayerPeer|IP\s*\.\s*resolve)", "network"),
    (r"\b(JavaScriptBridge|JavaScriptObject|Engine\s*\.\s*get_singleton)\b", "the web page / engine internals"),
    (r"\bDirAccess\b", "folders"),
    (r"\b(ClassDB|Expression|GDExtension|NativeExtension)\b", "dynamic code"),
    (r"\bload\s*\(\s*[\"'](?!res://)", "loading files from outside the game"),
    (r"\bProjectSettings\s*\.\s*(set_setting|save)", "changing project settings"),
]
FILE_ACCESS = re.compile(r"FileAccess\s*\.\s*open\s*\(\s*([\"'])(.*?)\1")


def problems(scripts: dict[str, str]) -> list[str]:
    out: list[str] = []
    if "main.gd" not in scripts:
        out.append("main.gd is missing (the game starts there)")
    if len([n for n in scripts if n not in ("hoola_bible.gd", "hoola_assets.gd")]) > MAX_FILES:
        out.append(f"too many files ({len(scripts)} > {MAX_FILES})")
    total = 0
    for name, code in scripts.items():
        if name in ("hoola_bible.gd", "hoola_assets.gd"):   # Hoola's own data files (Bible v0.395, assets v0.414), own cap
            if len(code or "") > 600_000:
                out.append("hoola_bible.gd too long")
        else:
            total += len(code or "")
        if not NAME.match(name or "") or name == "hoola_probe.gd":
            out.append(f"bad file name: {name!r} (lowercase .gd names only)")
            continue
        for pat, why in BANNED:
            m = re.search(pat, code or "")
            if m:
                out.append(f"{name}: '{m.group(0)}' not allowed ({why})")
        for m in FILE_ACCESS.finditer(code or ""):
            if not m.group(2).startswith("user://"):
                out.append(f"{name}: files only in user:// (the game's own save slot), not {m.group(2)!r}")
        if re.search(r"FileAccess\s*\.\s*open\s*\(\s*[^\"'\s]", code or ""):
            out.append(f"{name}: FileAccess.open needs a fixed 'user://...' path")
    for name, code in scripts.items():                  # v0.406 class_name works (import step); never Hoola's own names
        m = re.search(r"^\s*class_name\s+(HoolaBible|HoolaProbe|HoolaAssets)\b", code or "", re.M)
        if m and name not in ("hoola_bible.gd", "hoola_assets.gd"):
            out.append(f"{name}: class_name {m.group(1)} is Hoola's own name; pick another")
    if total > MAX_CHARS:
        out.append(f"code too long ({total} > {MAX_CHARS} characters)")
    if "main.gd" in scripts and not re.search(r"^\s*extends\s+Node\b", scripts["main.gd"], re.M):
        out.append("main.gd must start with 'extends Node' (the root scene is a plain Node)")
    return out
