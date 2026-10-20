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
  static const double speechNeed = 0.5;

  /// [speech] = Silero VAD probability for this chunk (null on phones / builds without it: loudness only).
  List<Uint8List> process(Uint8List chunk, {required bool hoolaSpeaking, double? speech}) {
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
    final loud = level > _threshold && (speech == null || speech >= speechNeed);
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
    } else if (_loudRun > 0 && _gap < 1) {
      _gap++; // one softer chunk inside a word is fine
    } else {
      if (_loudRun > 1) heldBack++;
      _loudRun = 0;
      _gap = 0;
    }
    if (_loudRun >= needChunks && _background.length >= 10) {
      open = true;
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
