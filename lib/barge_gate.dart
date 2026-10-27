import 'dart:math' as math;
import 'dart:typed_data';

/// Keeps room noise from cutting Hoola off mid-sentence.
///
/// Gemini stops talking the moment it hears speech-like sound, and it cannot tell the owner from a TV, traffic or
/// people nearby. So while Hoola is speaking, the mic only goes through when someone talks clearly louder than
/// the background (whatever the mic hears while he talks: room noise, TV, far voices, leftover echo) for about a
/// quarter of a second; until then Gemini hears silence. When the gate opens, the last ~320 ms are sent first,
/// so the start of the owner's sentence is never lost. While Hoola is quiet, everything goes through untouched.
/// The background is remembered across the whole call, so a TV that is always on raises the bar for the call.
class BargeGate {
  /// Consecutive loud chunks (40 ms each) needed to open the gate while Hoola talks: 6 = 240 ms.
  static const int needChunks = 6;

  /// v0.181 when Silero is VERY sure it is a voice (>= speechFast), the gate opens in 3 chunks (120 ms) instead:
  /// a real interjection reaches Gemini almost at once. Set from the server's ready.vad.fast (VOICE_VAD_FAST).
  double? speechFast;
  static const int fastChunks = 3;

  /// Never treat anything quieter than this as talking (RMS, full scale = 1.0).
  static const double minSpeech = 0.02;

  /// Chunks kept to replay when the gate opens: 8 x 40 ms = 320 ms.
  static const int keep = 8;

  /// Background levels remembered (150 x 40 ms = 6 s of Hoola talking).
  static const int history = 150;

  bool open = true;
  bool _wasSpeaking = false;
  int _openFor = 0;
  int _loudRun = 0;
  int _quietRun = 0;
  int _gap = 0;
  final List<Uint8List> _recent = [];
  final List<double> _background = [];
  double _threshold = minSpeech;

  /// Times the gate kept a burst of noise away from Gemini while Hoola was talking.
  int heldBack = 0;

  /// What to send to the server for this mic chunk (possibly several chunks, possibly silence).
  /// v0.51 a human voice per the phone's Silero VAD (0..1). Below this, loud sound is not treated as talking.
  /// v0.53: set from the server's `ready.vad.need` (VOICE_VAD_NEED), so it can be tuned without an app update.
  double speechNeed = 0.5;

  /// v0.53 counters for the call's quality numbers (sent to the server as gate_stats).
  int chunks = 0;
  int vadBlocked = 0;   // loud enough, but Silero said it was not a voice (fan, music, clatter...)
  int opens = 0;

  /// [speech] = Silero VAD probability for this chunk (null on phones / builds without it: loudness only).
  List<Uint8List> process(Uint8List chunk, {required bool hoolaSpeaking, double? speech}) {
    chunks++;
    if (!hoolaSpeaking) {
      _wasSpeaking = false;
      _recent.clear();
      _loudRun = 0;
      _gap = 0;
      open = true;
      return [chunk];
    }
    if (!_wasSpeaking) {
      // he starts a reply: the owner has just finished, so the gate starts closed
      _wasSpeaking = true;
      open = false;
      _loudRun = 0;
      _gap = 0;
    }
    final level = rms(chunk);
    // loud AND (when the phone can tell) a human voice: clatter, music, fans and traffic no longer open it
    final voice = speech == null || speech >= speechNeed;
    final loud = level > _threshold && voice;
    if (speech != null && !voice && level > _threshold) vadBlocked++;
    _learn(level);
    if (open) {
      // Real talking over him makes Gemini stop within a moment, and then he is no longer speaking.
      // If he is still talking 1.2 s later, or it went quiet for 600 ms, it was noise: close again.
      _openFor++;
      _quietRun = loud ? 0 : _quietRun + 1;
      if (_quietRun < 15 && _openFor <= 30) return [chunk];
      open = false;
      _loudRun = 0;
      _gap = 0;
    }
    _recent.add(chunk);
    if (_recent.length > keep) _recent.removeAt(0);
    if (loud) {
      _loudRun++;
      _gap = 0;
    } else if (_loudRun > 0 && _gap < 1 && voice) {
      _gap++; // one softer chunk inside a word is fine (but a chunk that is not a voice at all breaks the run)
    } else {
      if (_loudRun > 1) heldBack++;
      _loudRun = 0;
      _gap = 0;
    }
    if (_loudRun >= (speech != null && speechFast != null && speech! >= speechFast! ? fastChunks : needChunks) &&
        _background.length >= 10) {
      open = true;
      opens++;
      _quietRun = 0;
      _openFor = 0;
      final out = List<Uint8List>.from(_recent);
      _recent.clear();
      return out;
    }
    return [Uint8List(chunk.length)]; // silence keeps the stream steady
  }

  /// Talking must be well above the background: 10 dB over its quiet part and 6 dB over its typical level.
  void _learn(double level) {
    _background.add(level);
    if (_background.length > history) _background.removeAt(0);
    if (_background.length < 10) return;
    final s = List<double>.from(_background)..sort();
    double at(double q) => s[((s.length - 1) * q).round()];
    _threshold = math.max(minSpeech, math.max(at(0.2) * 3.2, at(0.6) * 2.0));
  }

  /// Root-mean-square level of 16-bit little-endian PCM, 0..1.
  static double rms(Uint8List b) {
    final n = b.length ~/ 2;
    if (n == 0) return 0;
    final d = ByteData.sublistView(b);
    var sum = 0.0;
    for (var i = 0; i < n; i++) {
      final s = d.getInt16(i * 2, Endian.little) / 32768.0;
      sum += s * s;
    }
    return math.sqrt(sum / n);
  }
}


/// v0.53 While nobody is talking (Hoola quiet, owner quiet), pure noise reaches Gemini as silence, so a fan, traffic,
/// a pressure cooker or clatter can't make it think someone spoke. Uses the phone's Silero VAD: after 1 s with no
/// voice at all (probability < 0.15) the mic is muted; the moment a voice appears (>= need) it opens and the last
/// 320 ms are sent first, so the start of the sentence is never lost (simulated: voice found within 0-80 ms of the
/// real start, 100% of voiced audio passed; ~90% of fan / traffic / music time muted). TV talk is a voice: it passes.
class IdleGate {
  double need = 0.5;
  static const double low = 0.15;
  static const int quietChunks = 25;   // 1 s
  static const int keep = 8;           // 320 ms replay

  bool muted = false;
  int _lowRun = 0;
  final List<Uint8List> _recent = [];
  int mutedChunks = 0;

  void reset() {
    muted = false;
    _lowRun = 0;
    _recent.clear();
  }

  /// [speech] null = no VAD on this phone / stale: everything passes (old behaviour).
  List<Uint8List> process(Uint8List chunk, double? speech) {
    if (speech == null) {
      reset();
      return [chunk];
    }
    if (muted) {
      _recent.add(chunk);
      if (_recent.length > keep) _recent.removeAt(0);
      if (speech >= need) {
        muted = false;
        _lowRun = 0;
        final out = List<Uint8List>.from(_recent);
        _recent.clear();
        return out;
      }
      mutedChunks++;
      return [Uint8List(chunk.length)];
    }
    _lowRun = speech < low ? _lowRun + 1 : 0;
    if (_lowRun >= quietChunks) {
      muted = true;
      _recent
        ..clear()
        ..add(chunk);
    }
    return [chunk];
  }
}
