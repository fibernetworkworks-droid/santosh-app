"""v0.625 EK AWAAZ (owner: "when task perform suddenly get voice like radio, different voices"). The 'ek second' acks, the
listening murmurs and the progress sounds were PRE-RENDERED clips from a separate TTS model (the legacy model on any failure,
kept on disk for ever) played into the call - a second voice beside Gemini Live's own. Off by default: on a call only the
call's own voice speaks; the persona already has Gemini say one short line itself before a slow tool."""
from app import voice
from app.config import Settings


def test_no_tts_clips_play_by_default():
    f = Settings.model_fields
    assert f["voice_tool_ack"].default is False and f["voice_backchannel"].default is False


def test_the_call_still_says_its_own_filler_line():
    p = voice.persona_prompt("Santosh", "m")
    assert "say ONE short line" in p
