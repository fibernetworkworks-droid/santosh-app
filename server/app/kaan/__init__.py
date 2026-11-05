"""KAAN PACK v0.589.0 — WhisperAI fed to HOOLA, Wave W0: the transcription core.

The owner fed whisperai.com (17 features, all wrapper-layer around the open model) to HOOLA.
Wave W0 lands the engine + ingest + store + ONE tool `kaan` (transcribe / status / list / get / search).

Design laws this pack obeys:
- PORT LAW: zero upstream code copied. The MIT-licensed openai-whisper package is a DEPENDENCY
  (imported lazily, never vendored); everything HOOLA-facing here is hand-built.
- INERTNESS LAW: importing app.kaan touches no env var, no file, no thread, no model download.
  `import whisper` happens only inside engine._load(), on first real use.
- AUDIO GATE: `kaan_audio` config flag, default OFF (the HOME-gate pattern, PC se alag). Until the
  owner sets KAAN_AUDIO=1 on the VPS, transcribe refuses with one honest line; status always works.
- LOCAL FIRST: audio and transcripts stay on her server. Nothing is uploaded anywhere; there is no
  API key on this path. Retention is a later wave (W6); rows are plain rows she can delete.
"""
