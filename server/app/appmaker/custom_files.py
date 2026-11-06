"""v0.425 RANG: the files the Android / iPhone generators write for her approved custom components.

No server imports on purpose: android/gen.py and ios/gen.py also run as plain scripts in CI (python3 gen.py spec out),
where a relative import of custom.py (which needs the database) cannot work.
"""
from __future__ import annotations

import json
from typing import Any


def android_files(custom: list[dict[str, Any]]) -> dict[str, str]:
    """{relative path under java/hoola/kit: source} - the components + the Components check screen."""
    if not custom:
        return {}
    out = {f"custom/{c['name']}.kt": c["kotlin"] for c in custom}
    rows = "\n".join(f'        block {{ Title({json.dumps(c["name"])}) }}\n        block {{ {c["sample_kt"]} }}' for c in custom)
    out["custom/ComponentsGallery.kt"] = f"""package hoola.kit

// Made by Hoola App Sahayak (v0.425): every custom component with its sample, so the device check opens each one.
import androidx.compose.runtime.Composable

@Composable
fun ComponentsGallery() {{
    Page("Components") {{
{rows}
    }}
}}
"""
    return out


def swift_files(custom: list[dict[str, Any]]) -> dict[str, str]:
    if not custom:
        return {}
    out = {f"Custom/{c['name']}.swift": c["swift"] for c in custom}
    blocks = [f'                VStack(alignment: .leading, spacing: 6) {{ Text({json.dumps(c["name"])}).font(.headline); {c["sample_swift"]} }}'
              for c in custom]
    rows = "\n".join("            Group {\n" + "\n".join(blocks[i:i + 8]) + "\n            }" for i in range(0, len(blocks), 8))
    out["Custom/ComponentsGallery.swift"] = f"""// Made by Hoola App Sahayak (v0.425): every custom component with its sample (the simulator check opens it).
import SwiftUI

struct ComponentsGallery: View {{
    var body: some View {{
        Page("Components") {{
{rows}
        }}
    }}
}}
"""
    return out
