import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../live_voice.dart';
import '../state.dart';
import 'glass.dart';
import 'santosh3d.dart';

enum _Act { idle, connecting, listening, userTalking, working, speaking }

/// Baat, live: a real-time voice call with Santosh (full duplex, interrupt any time).
class LiveVoiceScreen extends StatefulWidget {
  const LiveVoiceScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<LiveVoiceScreen> createState() => _LiveVoiceScreenState();
}

class _LiveVoiceScreenState extends State<LiveVoiceScreen> with SingleTickerProviderStateMixin {
  final _ctl = Santosh3DController();
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
  DateTime _lastHeard = DateTime.fromMillisecondsSinceEpoch(0);
  bool _turnOpen = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.voiceMode = true;
    app.pushLocation();
  }

  @override
  void dispose() {
    app.voiceMode = false;
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
    final call = LiveVoice(onEvent: _onEvent, onClosed: _onClosed);
    _call = call;
    final err = await call.start(
        server: app.serverUrl, key: app.apiKey, conv: app.conversationId!, voice: app.voiceName, lang: app.language);
    if (!mounted) return;
    if (err != null) {
      _call = null;
      setState(() {
        _inCall = false;
        _act = _Act.idle;
        _note = err;
      });
      return;
    }
    _tick = Timer.periodic(const Duration(milliseconds: 50), (_) => _update());
  }

  Future<void> _end() async {
    _tick?.cancel();
    await _call?.stop();
    _call = null;
    if (mounted) {
      setState(() {
        _inCall = false;
        _act = _Act.idle;
        _tool = null;
      });
    }
    _ctl.talk(false);
    _ctl.listen(false);
    _ctl.mood('idle');
  }

  void _onClosed(String? reason) {
    _tick?.cancel();
    _call = null;
    if (!mounted) return;
    setState(() {
      if (_inCall && reason != null && reason.isNotEmpty) _note = 'Call band ho gayi: $reason';
      _inCall = false;
      _act = _Act.idle;
      _tool = null;
    });
    _ctl.talk(false);
    _ctl.listen(false);
    _ctl.mood('idle');
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
    if (next != _act) setState(() => _act = next);
    switch (next) {
      case _Act.speaking:
        _ctl.listen(false);
        _ctl.talk(true);
        _ctl.mood('happy');
        _ctl.level(call.outLevel);
      case _Act.userTalking:
        _ctl.talk(false);
        _ctl.listen(true);
        _ctl.mood('happy');
        _ctl.level(call.inLevel);
      case _Act.working:
        _ctl.talk(false);
        _ctl.listen(false);
        _ctl.mood('working');
      default:
        _ctl.talk(false);
        _ctl.listen(false);
        _ctl.mood('idle');
    }
  }

  String get _status => switch (_act) {
        _Act.idle => _note ?? 'Orb dabaiye aur Santosh se seedhe baat kijiye',
        _Act.connecting => 'Santosh ko call lag raha hai…',
        _Act.listening => _muted ? 'Mic band hai' : 'Boliye, Santosh sun raha hai',
        _Act.userTalking => 'Sun raha hoon…',
        _Act.working => '${_tool ?? 'Kaam kar raha hoon'}…',
        _Act.speaking => 'Santosh bol raha hai · beech mein bol sakte hain',
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
          if (_inCall) const Pill('LIVE', fg: Colors.white, bg: Color(0xFFDC2626)),
        ]),
      ),
      Expanded(child: Santosh3D(controller: _ctl)),
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
          _small(Icons.front_hand_rounded, 'Santosh ko roko', _act == _Act.speaking ? () => _call?.cutSpeech() : null),
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
        label: _inCall ? 'Call khatam karo' : 'Santosh ko call karo',
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
                  boxShadow: const [BoxShadow(color: Color(0x667C3AED), blurRadius: 26, offset: Offset(0, 10))],
                ),
                child: _act == _Act.connecting
                    ? const Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3))
                    : Icon(_inCall ? Icons.call_end_rounded : Icons.call_rounded, color: Colors.white, size: 38),
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
            ..color = const Color(0xFFA21CAF).withOpacity((1 - k) * (.25 + inLevel * .7));
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
