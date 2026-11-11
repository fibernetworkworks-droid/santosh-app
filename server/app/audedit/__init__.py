"""Audio editing for Hoola (one tool, `audio_edit`), built on ffmpeg that is already on the server.

Every edit is LOCAL and deterministic - no key, no network, no model: trim, cut a part out, fade, volume, loudness
normalise to a named target (podcast / social / broadcast), speed without chipmunk pitch, pitch, noise reduction, voice
clean-up chain, silence removal, bass / treble, mono / stereo, sample rate, reverse, join with crossfade, voice + music with
the music ducked under the voice, split, loudness report, waveform picture, audio pulled out of a video.

Not built, said plainly: AI stem separation (vocals / instruments) and voice cloning / voice changing into another person.
Output is re-encoded with its metadata dropped (no tags, no recorder / phone details travel)."""
