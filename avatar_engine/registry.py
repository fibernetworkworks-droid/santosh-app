"""Hoola Interactive - the Model Lab's model list (docs/INTERACTIVE_AVATAR_PLAN.md sections 2 and 10).

One row per model the lab may download. `use` is the licence verdict, read from each model's own model card / LICENSE
on 2 Nov 2026:
  commercial - may ship in the product
  lab_only   - may be downloaded and TESTED in the lab, never shipped until the open question in `note` is closed
  refused    - never downloaded at all (non-commercial licence)

Plain Python, no third-party imports: the Hoola server's tests import it, and so does the GPU app.
"""
from __future__ import annotations

MODELS: dict[str, dict] = {
    # ------------------------------------------------------------------ voices (Hoola Voice)
    "chatterbox": {
        "kind": "voice", "repo": "ResembleAI/chatterbox", "licence": "MIT", "use": "commercial",
        "langs": ["hi", "en", "ar", "da", "de", "el", "es", "fi", "fr", "he", "it", "ja", "ko", "ms", "nl", "no",
                  "pl", "pt", "ru", "sv", "sw", "tr", "zh"],
        "clone": True,
        "note": "Multilingual V3; every output carries Resemble's Perth watermark.",
    },
    "indicf5": {
        "kind": "voice", "repo": "ai4bharat/IndicF5", "licence": "MIT (weights)", "use": "lab_only", "gated": True,
        "langs": ["hi", "mr", "bn", "gu", "kn", "ml", "or", "pa", "ta", "te", "as"],
        "clone": True,
        "note": "Gated download (accept AI4Bharat's terms on Hugging Face). Lab only until its training-data terms are read.",
    },
    "indic_parler": {
        "kind": "voice", "repo": "ai4bharat/indic-parler-tts", "licence": "Apache-2.0", "use": "commercial", "gated": True,
        "langs": ["hi", "mr", "bn", "gu", "kn", "ml", "or", "pa", "ta", "te", "as", "en"],
        "clone": False,
        "note": "Voice described in words; no cloning. Gated download (accept terms).",
    },
    # ------------------------------------------------------------------ face (the face engine)
    "musetalk": {
        "kind": "face", "repo": "TMElyralab/MuseTalk", "licence": "MIT (code + weights)", "use": "commercial",
        "note": "MuseTalk 1.5. Its helper models are listed below and judged on their own.",
    },
    "sd_vae": {"kind": "face_helper", "repo": "stabilityai/sd-vae-ft-mse", "licence": "MIT", "use": "commercial"},
    "whisper_tiny": {"kind": "face_helper", "repo": "openai/whisper-tiny", "licence": "Apache-2.0", "use": "commercial"},
    "dwpose": {
        "kind": "face_helper", "repo": "yzd-v/DWPose", "licence": "Apache-2.0 (code)", "use": "lab_only",
        "note": "Weights' training-data terms not yet read.",
    },
    "face_parse_bisenet": {
        "kind": "face_helper", "repo": "(Google Drive file named by MuseTalk's download script)", "licence": "unclear",
        "use": "lab_only",
        "note": "Face-parsing model commonly trained on CelebAMask-HQ, whose terms are non-commercial: must be replaced "
                "by a commercially licensed segmenter before any public release.",
    },
    # ------------------------------------------------------------------ speech to text (Hoola Studio: transcribe + dubbing)
    "faster_whisper_small": {
        "kind": "speech_to_text", "repo": "Systran/faster-whisper-small", "licence": "MIT (code + weights; OpenAI Whisper is MIT)",
        "use": "commercial", "note": "CPU int8; says what was spoken, in which language, with word times.",
    },
    # ------------------------------------------------------------------ refused (non-commercial)
    "f5_tts": {"kind": "voice", "repo": "SWivid/F5-TTS", "licence": "CC-BY-NC-4.0", "use": "refused"},
    "xtts_v2": {"kind": "voice", "repo": "coqui/XTTS-v2", "licence": "Coqui Public Model Licence", "use": "refused"},
    "fish_s1_mini": {"kind": "voice", "repo": "fishaudio/s1-mini", "licence": "CC-BY-NC-SA-4.0", "use": "refused"},
    "wav2lip": {"kind": "face", "repo": "Rudrabha/Wav2Lip", "licence": "research / personal only", "use": "refused"},
}

USES = ("commercial", "lab_only", "refused")


class Refused(Exception):
    pass


def check(model_id: str, purpose: str = "lab") -> dict:
    """The one gate every download and every call goes through.

    purpose 'lab'  -> commercial + lab_only allowed (testing)
    purpose 'ship' -> commercial only (anything a real user receives)"""
    m = MODELS.get(model_id)
    if m is None:
        raise Refused(f"Unknown model '{model_id}'.")
    if m["use"] == "refused":
        raise Refused(f"{model_id} is refused: licence {m['licence']} does not allow commercial use.")
    if purpose == "ship" and m["use"] != "commercial":
        raise Refused(f"{model_id} is lab-only: {m.get('note', 'licence question open')}")
    if purpose not in ("lab", "ship"):
        raise Refused(f"Unknown purpose '{purpose}'.")
    return m


def voices(purpose: str = "lab") -> list[str]:
    return [k for k, m in MODELS.items() if m["kind"] == "voice" and m["use"] != "refused"
            and (purpose == "lab" or m["use"] == "commercial")]


def public() -> list[dict]:
    """What the console shows: every row, with its verdict (no secrets live here)."""
    return [{"id": k, **{f: m.get(f) for f in ("kind", "repo", "licence", "use", "langs", "clone", "gated", "note")}}
            for k, m in MODELS.items()]
