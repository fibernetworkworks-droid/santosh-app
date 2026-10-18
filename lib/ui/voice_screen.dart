import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../state.dart';
import 'glass.dart';
import '../emotion.dart';
import 'live_santosh.dart';

enum _V { idle, listening, thinking, speaking }

/// Voice to voice: you speak, Santosh answers aloud, then listens again (hands-free).
class VoiceScreen extends StatefulWidget {
  const VoiceScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> with TickerProviderStateMixin {
  final _stt = SpeechToText();
  final _tts = FlutterTts();
  late final AnimationController _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 1600))..repeat();

  _V _state = _V.idle;
  bool _sttReady = false;
  bool _handsFree = true;
  bool _gotFinal = false;
  bool _turnHadReply = false;
  String _heard = '';
  String _reply = '';
  String? _hint;
  double _level = 0;
  final List<String> _queue = [];
  StreamSubscription<Map<String, dynamic>>? _replySub;
  Timer? _waitTimer;
  Completer<void>? _speaking;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.voiceMode = true;
    _replySub = app.replies.listen(_onReply);
    app.addListener(_onApp);
    _setupTts();
  }

  @override
  void dispose() {
    app.voiceMode = false;
    app.removeListener(_onApp);
    _replySub?.cancel();
    _waitTimer?.cancel();
    _stt.cancel();
    _tts.stop();
    _pulse.dispose();
    super.dispose();
  }

  void _endSpeak() {
    final c = _speaking;
    _speaking = null;
    if (c != null && !c.isCompleted) c.complete();
  }

  Future<void> _setupTts() async {
    void done() => _endSpeak();

    _tts.setCompletionHandler(done);
    _tts.setCancelHandler(done);
    _tts.setErrorHandler((_) => done());
    _tts.setProgressHandler((text, start, end, word) {
      // a little bob on every word he speaks
      if (mounted) setState(() => _level = .45 + (word.length % 4) * .15);
    });
    try {
      await _tts.setLanguage(app.language);
      await _tts.setSpeechRate(.48);
      await _tts.setPitch(.95);
      await _pickMaleVoice();
    } catch (_) {}
  }

  /// Santosh is male: prefer a male voice for the language when the phone has one.
  Future<void> _pickMaleVoice() async {
    final list = await _tts.getVoices;
    if (list is! List) return;
    final lang = app.language.toLowerCase();
    final mine = list.whereType<Map>().map((v) => {'name': '${v['name']}', 'locale': '${v['locale']}'})
        .where((v) => v['locale']!.toLowerCase().replaceAll('_', '-') == lang)
        .toList();
    if (mine.isEmpty) return;
    // Google voices: "...male..." in the name, or the known male Hindi voices
    const knownMale = ['hi-in-x-hie', 'hi-in-x-hid', 'mr-in-x-mrd', 'en-in-x-ene', 'en-in-x-end'];
    Map<String, String>? pick;
    for (final v in mine) {
      final n = v['name']!.toLowerCase();
      if ((n.contains('male') && !n.contains('female')) || knownMale.any(n.startsWith)) {
        pick = v;
        if (n.contains('local')) break; // offline voice answers faster
      }
    }
    if (pick != null) await _tts.setVoice(pick);
  }

  void _set(_V s, {String? hint}) {
    if (!mounted) return;
    setState(() {
      _state = s;
      _hint = hint;
    });
  }

  // ---------------- listening ----------------
  Future<void> _listen() async {
    if (!mounted) return;
    await _tts.stop();
    _sttReady = _sttReady ||
        await _stt.initialize(
          onStatus: (s) {
            if ((s == 'done' || s == 'notListening') && _state == _V.listening && !_gotFinal) {
              // stopped without a final result: send what we have, or go idle
              Future.delayed(const Duration(milliseconds: 400), () {
                if (_state == _V.listening && !_gotFinal) _finishHeard(_heard);
              });
            }
          },
          onError: (SpeechRecognitionError e) {
            if (_state == _V.listening) _finishHeard(_heard);
          },
        );
    if (!_sttReady) {
      _set(_V.idle, hint: 'Microphone permission chahiye. Phone settings mein Santosh ko mic allow kijiye.');
      return;
    }
    _gotFinal = false;
    setState(() {
      _heard = '';
      _level = 0;
    });
    _set(_V.listening);
    await _stt.listen(
      localeId: app.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 40),
      pauseFor: const Duration(milliseconds: 3500), // don't cut you off mid-thought
      partialResults: true,
      cancelOnError: true,
      onSoundLevelChange: (db) {
        // Android reports roughly -2..10 dB
        final v = ((db + 2) / 12).clamp(0.0, 1.0);
        if (mounted) setState(() => _level = _level * .6 + v * .4);
      },
      onResult: (r) {
        if (!mounted) return;
        setState(() => _heard = r.recognizedWords);
        if (r.finalResult) {
          _gotFinal = true;
          _finishHeard(r.recognizedWords);
        }
      },
    );
  }

  Future<void> _finishHeard(String words) async {
    if (_state != _V.listening) return;
    _gotFinal = true;
    words = words.trim();
    if (words.isEmpty) {
      _set(_V.idle, hint: 'Kuch suna nahi. Orb dabakar boliye.');
      return;
    }
    _turnHadReply = false;
    _queue.clear();
    setState(() => _reply = '');
    _set(_V.thinking);
    final ok = await app.send(words, spoken: true);
    if (!ok) {
      _set(_V.idle, hint: 'Message nahi gaya. Internet check kijiye.');
      return;
    }
    _waitTimer?.cancel();
    _waitTimer = Timer(const Duration(seconds: 90), () {
      if (_state == _V.thinking && !_turnHadReply) _set(_V.idle, hint: 'Santosh ko time lag raha hai. Jawab aate hi yahan dikhega.');
    });
  }

  // ---------------- replies ----------------
  void _onReply(Map<String, dynamic> p) {
    final text = (p['text'] as String? ?? '').trim();
    if (text.isEmpty || !mounted) return;
    setState(() => _reply = text);
    if (_state == _V.listening) return; // don't talk over the user; it's on screen
    _turnHadReply = true;
    _waitTimer?.cancel();
    _queue.add(text);
    if (_state != _V.speaking) _speakQueue();
  }

  void _onApp() {
    if (!mounted) return;
    if (_state == _V.thinking) {
      setState(() {});
      if (!app.typing && _turnHadReply && _queue.isEmpty) _turnDone();
    }
  }

  String _speakable(String t) => t
      .replaceAll(RegExp(r'https?://\S+'), '')
      .replaceAll(RegExp(r'[*_#`>|]'), '')
      .replaceAll(RegExp(r'\n+'), '. ')
      .trim();

  Future<void> _speakQueue() async {
    while (_queue.isNotEmpty && mounted) {
      final text = _speakable(_queue.removeAt(0));
      if (text.isEmpty) continue;
      _set(_V.speaking);
      final c = Completer<void>();
      _speaking = c;
      try {
        await _tts.setLanguage(app.language);
        await _tts.speak(text);
      } catch (_) {
        if (!c.isCompleted) c.complete();
      }
      // safety net in case the engine never reports completion
      await c.future.timeout(Duration(milliseconds: 6000 + text.length * 110), onTimeout: () {});
      if (_state != _V.speaking) return; // interrupted
    }
    if (!mounted) return;
    if (app.typing) {
      _set(_V.thinking); // more is coming (Santosh is still working)
    } else {
      _turnDone();
    }
  }

  void _turnDone() {
    if (_handsFree) {
      Future.delayed(const Duration(milliseconds: 350), () {
        if (mounted && (_state == _V.thinking || _state == _V.speaking)) _listen();
      });
    } else {
      _set(_V.idle);
    }
  }

  // ---------------- controls ----------------
  Future<void> _onOrb() async {
    switch (_state) {
      case _V.idle:
        await _listen();
      case _V.listening:
        await _stt.stop(); // final result follows
      case _V.thinking:
        _set(_V.idle, hint: 'Ruk gaya. Santosh ka jawab aayega to yahan dikhega.');
      case _V.speaking:
        _queue.clear();
        await _tts.stop();
        _endSpeak();
        await _listen(); // interrupt and talk
    }
  }

  Future<void> _stopAll() async {
    _queue.clear();
    _waitTimer?.cancel();
    await _stt.cancel();
    await _tts.stop();
    _endSpeak();
    _set(_V.idle);
  }

  String get _statusText => switch (_state) {
        _V.idle => _hint ?? 'Orb dabaiye aur boliye',
        _V.listening => 'Sun raha hoon…',
        _V.thinking => app.currentStep != null ? '${app.currentStep}…' : 'Soch raha hoon…',
        _V.speaking => 'Bol raha hoon… (beech mein bolne ke liye orb dabaiye)',
      };

  @override
  Widget build(BuildContext context) {
    final lang = languages[app.language] ?? app.language;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 14, 0),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Baat karein', style: display(28)),
              Text('Santosh se seedhe bolkar · $lang', style: const TextStyle(color: C.muted, fontSize: 12.5, fontWeight: FontWeight.w600)),
            ]),
          ),
          FilterChip(
            label: const Text('Lagatar'),
            selected: _handsFree,
            showCheckmark: false,
            avatar: Icon(_handsFree ? Icons.all_inclusive_rounded : Icons.touch_app_rounded, size: 18, color: _handsFree ? C.onAccent : C.chip),
            selectedColor: C.accent,
            backgroundColor: const Color(0x14FFFFFF),
            labelStyle: TextStyle(color: _handsFree ? C.onAccent : C.chip, fontWeight: FontWeight.w700),
            tooltip: 'Jawab ke baad apne aap phir sunna',
            onSelected: (v) => setState(() => _handsFree = v),
          ),
        ]),
      ),
      Expanded(
        child: Stack(children: [
          Positioned.fill(
            child: Center(
              child: ListenableBuilder(
                listenable: app,
                builder: (context, _) => LiveSantosh(
                  feeling: switch (_state) {
                    _V.listening => app.userStressed ? Mood.care : Mood.listening,
                    _V.thinking => app.currentStep != null ? Mood.work : Mood.think,
                    _V.speaking => const {Mood.happy, Mood.excited, Mood.care, Mood.wow}.contains(app.mood) ? app.mood : Mood.talking,
                    _V.idle => app.mood,
                  },
                  level: _state == _V.idle ? 0 : _level,
                  thought: _state != _V.speaking,
                  size: 290,
                ),
              ),
            ),
          ),
          if (!app.connected)
            const Positioned(left: 20, right: 20, top: 8, child: Pill('Server se connect ho raha hai…', fg: C.warn, bg: Color(0x2EFFB15C))),
        ]),
      ),
      _captions(),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
        child: Text(_statusText, textAlign: TextAlign.center, style: TextStyle(color: _state == _V.idle ? C.muted : C.accent, fontWeight: FontWeight.w700)),
      ),
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          _small(Icons.stop_rounded, 'Sab roko', _state == _V.idle ? null : _stopAll),
          const SizedBox(width: 26),
          _orb(),
          const SizedBox(width: 26),
          _small(Icons.replay_rounded, 'Phir se sunao', _reply.isEmpty || _state != _V.idle ? null : () {
            _queue.add(_reply);
            _speakQueue();
          }),
        ]),
      ),
    ]);
  }

  Widget _captions() {
    if (_heard.isEmpty && _reply.isEmpty) return const SizedBox(height: 8);
    return Glass(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxHeight: 150),
        child: SingleChildScrollView(
          reverse: true,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (_heard.isNotEmpty) ...[
              const Text('AAP', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.muted)),
              Text(_heard, style: const TextStyle(fontSize: 15, height: 1.35, color: C.ink)),
            ],
            if (_reply.isNotEmpty) ...[
              if (_heard.isNotEmpty) const SizedBox(height: 8),
              const Text('SANTOSH', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.accent)),
              Text(_reply, style: const TextStyle(fontSize: 15, height: 1.35, color: C.ink, fontWeight: FontWeight.w600)),
            ],
          ]),
        ),
      ),
    );
  }

  Widget _small(IconData icon, String label, VoidCallback? onTap) => Semantics(
        button: true,
        label: label,
        child: Opacity(
          opacity: onTap == null ? .35 : 1,
          child: GestureDetector(
            onTap: onTap,
            child: Glass(radius: 22, padding: const EdgeInsets.all(14), child: Icon(icon, color: C.chip)),
          ),
        ),
      );

  Widget _orb() {
    final icon = switch (_state) {
      _V.idle => Icons.mic_rounded,
      _V.listening => Icons.graphic_eq_rounded,
      _V.thinking => Icons.more_horiz_rounded,
      _V.speaking => Icons.record_voice_over_rounded,
    };
    return Semantics(
      button: true,
      label: _state == _V.idle ? 'Bolna shuru karein' : 'Orb',
      child: GestureDetector(
        onTap: _onOrb,
        child: AnimatedBuilder(
          animation: _pulse,
          builder: (context, _) => CustomPaint(
            painter: _OrbRings(_pulse.value, _state, _level),
            child: Container(
              width: 92,
              height: 92,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: C.gradient,
                boxShadow: [
                  BoxShadow(color: const Color(0x59FFA046), blurRadius: 26 + (_state == _V.listening ? _level * 30 : 0), offset: const Offset(0, 10)),
                ],
              ),
              child: Icon(icon, color: C.onAccent, size: 38),
            ),
          ),
        ),
      ),
    );
  }
}

/// Rings around the orb: grow with your voice while listening, orbit while thinking, ripple while speaking.
class _OrbRings extends CustomPainter {
  _OrbRings(this.t, this.state, this.level);
  final double t;
  final _V state;
  final double level;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    final paint = Paint()..style = PaintingStyle.stroke;
    switch (state) {
      case _V.idle:
        paint
          ..strokeWidth = 2
          ..color = C.accent.withOpacity(.18 + .1 * math.sin(t * 2 * math.pi));
        canvas.drawCircle(c, r + 8, paint);
      case _V.listening:
        for (var i = 0; i < 3; i++) {
          final p = (t + i / 3) % 1;
          paint
            ..strokeWidth = 3
            ..color = const Color(0xFF2DD4BF).withOpacity((1 - p) * (.25 + level * .6));
          canvas.drawCircle(c, r + 6 + p * (18 + level * 36), paint);
        }
      case _V.thinking:
        paint
          ..strokeWidth = 4
          ..strokeCap = StrokeCap.round
          ..color = C.accent.withOpacity(.7);
        final a = t * 2 * math.pi;
        canvas.drawArc(Rect.fromCircle(center: c, radius: r + 9), a, 1.2, false, paint);
        canvas.drawArc(Rect.fromCircle(center: c, radius: r + 9), a + math.pi, 1.2, false, paint..color = const Color(0xFF2DD4BF).withOpacity(.6));
      case _V.speaking:
        for (var i = 0; i < 2; i++) {
          final p = (t * 1.6 + i / 2) % 1;
          paint
            ..strokeWidth = 2.5
            ..color = C.accent.withOpacity((1 - p) * .45);
          canvas.drawCircle(c, r + 4 + p * 26, paint);
        }
    }
  }

  @override
  bool shouldRepaint(_OrbRings o) => o.t != t || o.state != state || o.level != level;
}
