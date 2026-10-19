import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../live_voice.dart';
import '../native.dart';
import '../state.dart';
import 'artifact_screen.dart';
import 'browser_live.dart';
import 'glass.dart';
import 'lock_safe.dart';
import '../emotion.dart';
import 'live_santosh.dart';

enum _Act { idle, connecting, listening, userTalking, working, speaking }

/// Baat, live: a real-time voice call with Santosh (full duplex, interrupt any time).
class LiveVoiceScreen extends StatefulWidget {
  const LiveVoiceScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<LiveVoiceScreen> createState() => _LiveVoiceScreenState();
}

class _LiveVoiceScreenState extends State<LiveVoiceScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 1600))..repeat();
  LiveVoice? _call;
  Timer? _tick;
  _Act _act = _Act.idle;
  bool _inCall = false;
  bool _muted = false;
  String _heard = '';
  String _reply = '';
  String? _tool;
  String? _note;
  String? _lockIssue;   // why the call may stop when the phone locks (checked after the call starts)
  DateTime _lastHeard = DateTime.fromMillisecondsSinceEpoch(0);
  bool _turnOpen = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.voiceMode = true;
    app.pushLocation();
    app.addListener(_onApp);
    WidgetsBinding.instance.addPostFrameCallback((_) => _onApp());
  }

  /// "Hey Santosh" was heard: pick up straight away.
  void _onApp() {
    if (!mounted || !app.autoCall) return;
    app.autoCall = false;
    if (!_inCall) _start();
  }

  /// Call over: give the mic back to the wake word, and drop the lock-screen view.
  void _afterCall() {
    Native.wakeResume();
    app.leaveLockedMode();
  }

  @override
  void dispose() {
    app.voiceMode = false;
    app.removeListener(_onApp);
    if (_inCall) _afterCall();
    _tick?.cancel();
    _call?.stop();
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    if (app.conversationId == null || !app.connected) {
      setState(() => _note = 'Pehle server se connect hone dijiye.');
      return;
    }
    setState(() {
      _inCall = true;
      _act = _Act.connecting;
      _note = null;
      _heard = _reply = '';
    });
    await Native.wakePause();
    final call = LiveVoice(onEvent: _onEvent, onClosed: _onClosed);
    _call = call;
    final err = await call.start(
        server: app.serverUrl, key: app.apiKey, conv: app.conversationId!, voice: app.voiceName, lang: app.language);
    if (!mounted) return;
    if (err != null) {
      _call = null;
      Native.wakeResume();
      setState(() {
        _inCall = false;
        _act = _Act.idle;
        _note = err;
      });
      return;
    }
    _tick = Timer.periodic(const Duration(milliseconds: 50), (_) => _update());
    Future.delayed(const Duration(seconds: 2), () async {
      if (!mounted || !_inCall) return;
      final st = await LockSafe.status();
      if (mounted && _inCall) setState(() => _lockIssue = LockSafe.issue(st, inCall: true));
    });
  }

  Future<void> _end() async {
    _tick?.cancel();
    await _call?.stop();
    _call = null;
    _afterCall();
    if (mounted) {
      setState(() {
        _inCall = false;
        _act = _Act.idle;
        _tool = null;
      });
    }
  }

  void _onClosed(String? reason) {
    _tick?.cancel();
    _call = null;
    _afterCall();
    if (!mounted) return;
    setState(() {
      if (_inCall && reason != null && reason.isNotEmpty) _note = 'Call band ho gayi: $reason';
      _inCall = false;
      _act = _Act.idle;
      _tool = null;
    });
  }

  void _onEvent(Map<String, dynamic> e) {
    if (!mounted) return;
    switch (e['type']) {
      case 'ready':
        setState(() => _act = _Act.listening);
      case 'user_text':
        if (!_turnOpen) _reply = '';
        _turnOpen = true;
        _lastHeard = DateTime.now();
        setState(() => _heard = e['text'] as String? ?? '');
      case 'santosh_text':
        setState(() => _reply = e['text'] as String? ?? '');
      case 'turn_done':
        _turnOpen = false;
        if (_heard.isNotEmpty) app.feelUser(_heard);
        if (_reply.isNotEmpty) Future.delayed(const Duration(milliseconds: 600), () => mounted ? app.feelReply(_reply) : null);
      case 'tool':
        setState(() => _tool = e['state'] == 'running' ? e['label'] as String? : null);
      case 'error':
        setState(() => _note = e['message'] as String?);
    }
  }

  /// Every 50 ms: work out who is talking and drive the 3D Santosh.
  void _update() {
    final call = _call;
    if (call == null || !mounted) return;
    _Act next;
    if (_act == _Act.connecting) {
      next = _Act.connecting;
    } else if (call.santoshSpeaking) {
      next = _Act.speaking;
    } else if (!_muted && (call.inLevel > .14 || DateTime.now().difference(_lastHeard) < const Duration(milliseconds: 900))) {
      next = _Act.userTalking;
    } else if (_tool != null) {
      next = _Act.working;
    } else {
      next = _Act.listening;
    }
    if (next != _act) {
      if (next == _Act.userTalking) app.setMood(app.userStressed ? Mood.care : Mood.listening, hold: Duration.zero);
      setState(() => _act = next);
    } else if (next == _Act.speaking || next == _Act.userTalking) {
      setState(() {}); // keep his body in time with the voice level
    }
    switch (next) {
      case _Act.speaking:
      case _Act.userTalking:
      case _Act.working:
      default:
    }
  }

  /// What his body shows: who is talking first, then how he feels about it.
  Mood _shownMood() {
    switch (_act) {
      case _Act.userTalking:
        return app.userStressed ? Mood.care : Mood.listening;
      case _Act.working:
        return Mood.work;
      case _Act.speaking:
        const expressive = {Mood.happy, Mood.excited, Mood.care, Mood.wow};
        return expressive.contains(app.mood) ? app.mood : Mood.talking;
      case _Act.connecting:
        return Mood.think;
      default:
        return app.mood == Mood.think || app.mood == Mood.work ? Mood.idle : app.mood;
    }
  }

  String get _status => switch (_act) {
        _Act.idle => _note ?? 'Call button dabaiye aur ${app.aName} se seedhe baat kijiye',
        _Act.connecting => '${app.aName} ko call lag raha hai…',
        _Act.listening => _muted ? 'Mic band hai' : app.g('Boliye, ${app.aName} sun raha hai'),
        _Act.userTalking => app.g('Sun raha hoon…'),
        _Act.working => '${_tool ?? app.g('Kaam kar raha hoon')}…',
        _Act.speaking => app.g('${app.aName} bol raha hai · beech mein bol sakte hain'),
      };

  @override
  Widget build(BuildContext context) {
    final voice = app.voices.firstWhere((v) => v['id'] == app.voiceName, orElse: () => {'id': app.voiceName});
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 14, 0),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Baat karein', style: display(28)),
              Text('Live call · awaaz: ${voice['id']}${voice['style'] != null ? ' (${voice['style']})' : ''}',
                  style: const TextStyle(color: C.muted, fontSize: 12.5, fontWeight: FontWeight.w600)),
            ]),
          ),
          if (_inCall) const Pill('● LIVE', fg: Colors.white, bg: Color(0xCCDC2626)),
          if (!_inCall) ListenableBuilder(listenable: app, builder: (context, _) => Pill(moodStyles[app.mood]!.label, fg: moodStyles[app.mood]!.aura, bg: const Color(0x1FFFFFFF))),
        ]),
      ),
      Expanded(
        child: Stack(children: [
          Positioned.fill(
            child: LayoutBuilder(
              builder: (context, box) => Center(
                child: ListenableBuilder(
                  listenable: app,
                  builder: (context, _) => LiveSantosh(
                    feeling: _shownMood(),
                    level: _act == _Act.speaking ? (_call?.outLevel ?? 0) : (_act == _Act.userTalking ? (_call?.inLevel ?? 0) : 0),
                    thought: _act != _Act.speaking,
                    size: math.min(box.maxHeight * .82, 330),
                  ),
                ),
              ),
            ),
          ),
          Positioned(left: 0, right: 0, bottom: 4, child: ArtifactCallPill(app: app)),
          Positioned(right: 12, top: 8, child: BrowserCallThumb(app: app)),
        ]),
      ),
      if (_inCall && _lockIssue != null) LockSafeBanner(text: _lockIssue!),
      _captions(),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
        child: Text(_status, textAlign: TextAlign.center,
            style: TextStyle(color: _act == _Act.idle ? C.muted : C.accent, fontWeight: FontWeight.w700)),
      ),
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          _small(_muted ? Icons.mic_off_rounded : Icons.mic_none_rounded, _muted ? 'Mic chalu karo' : 'Mic band karo', !_inCall ? null : () {
            setState(() => _muted = !_muted);
            _call?.setMuted(_muted);
          }),
          const SizedBox(width: 26),
          _orb(),
          const SizedBox(width: 26),
          _small(Icons.front_hand_rounded, '${app.aName} ko roko', _act == _Act.speaking ? () => _call?.cutSpeech() : null),
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

  Widget _orb() => Semantics(
        button: true,
        label: _inCall ? 'Call khatam karo' : '${app.aName} ko call karo',
        child: GestureDetector(
          onTap: _act == _Act.connecting ? null : (_inCall ? _end : _start),
          child: AnimatedBuilder(
            animation: _pulse,
            builder: (context, _) => CustomPaint(
              painter: _Rings(_pulse.value, _act, _call?.inLevel ?? 0, _call?.outLevel ?? 0),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: 92,
                height: 92,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: _inCall
                      ? const LinearGradient(colors: [Color(0xFFEF4444), Color(0xFFB91C1C)], begin: Alignment.topLeft, end: Alignment.bottomRight)
                      : C.gradient,
                  boxShadow: [BoxShadow(color: (_inCall ? const Color(0xFFEF4444) : C.accent).withOpacity(.45), blurRadius: 28, offset: const Offset(0, 10))],
                ),
                child: _act == _Act.connecting
                    ? const Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator(color: C.onAccent, strokeWidth: 3))
                    : Icon(_inCall ? Icons.call_end_rounded : Icons.call_rounded, color: _inCall ? Colors.white : C.onAccent, size: 38),
              ),
            ),
          ),
        ),
      );
}

class _Rings extends CustomPainter {
  _Rings(this.t, this.act, this.inLevel, this.outLevel);
  final double t;
  final _Act act;
  final double inLevel;
  final double outLevel;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    final p = Paint()..style = PaintingStyle.stroke;
    switch (act) {
      case _Act.userTalking:
        for (var i = 0; i < 3; i++) {
          final k = (t + i / 3) % 1;
          p
            ..strokeWidth = 3
            ..color = C.teal.withOpacity((1 - k) * (.25 + inLevel * .7));
          canvas.drawCircle(c, r + 6 + k * (16 + inLevel * 40), p);
        }
      case _Act.speaking:
        p
          ..strokeWidth = 4
          ..color = C.accent.withOpacity(.55);
        canvas.drawCircle(c, r + 6 + outLevel * 22, p);
        p
          ..strokeWidth = 2
          ..color = C.accent.withOpacity(.25);
        canvas.drawCircle(c, r + 14 + outLevel * 34, p);
      case _Act.working:
        p
          ..strokeWidth = 4
          ..strokeCap = StrokeCap.round
          ..color = C.accent.withOpacity(.7);
        final a = t * 2 * math.pi;
        canvas.drawArc(Rect.fromCircle(center: c, radius: r + 9), a, 1.2, false, p);
        canvas.drawArc(Rect.fromCircle(center: c, radius: r + 9), a + math.pi, 1.2, false, p);
      default:
        p
          ..strokeWidth = 2
          ..color = C.accent.withOpacity(.16 + .1 * math.sin(t * 2 * math.pi));
        canvas.drawCircle(c, r + 8, p);
    }
  }

  @override
  bool shouldRepaint(_Rings o) => true;
}
