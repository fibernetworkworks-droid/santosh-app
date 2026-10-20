import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../call_session.dart';
import '../state.dart';
import 'artifact_screen.dart';
import 'attach.dart';
import 'browser_live.dart';
import 'glass.dart';
import 'lock_safe.dart';
import '../emotion.dart';
import 'live_santosh.dart';
import 'work_theatre.dart';
import 'chat_screen.dart' show feedCard;

/// Baat, live: a real-time voice call with the avatar (full duplex, interrupt any time).
/// The call itself lives in [CallSession] (app.voiceCall): leaving this screen does not end it.
class LiveVoiceScreen extends StatefulWidget {
  const LiveVoiceScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<LiveVoiceScreen> createState() => _LiveVoiceScreenState();
}

class _LiveVoiceScreenState extends State<LiveVoiceScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 1600))..repeat();
  bool _cardsOpen = true;
  int _seenCards = 0;

  Santosh get app => widget.app;
  CallSession get call => app.voiceCall;

  @override
  void initState() {
    super.initState();
    call.screenOpen = true;
    if (!call.inCall) app.voiceMode = true;   // replies here are spoken by the call, not by the phone
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (app.autoCall && app.realtimeVoice && !call.inCall) {
        app.autoCall = false;
        call.start();
      }
    });
  }

  @override
  void dispose() {
    call.screenOpen = false;
    if (!call.inCall) app.voiceMode = false;
    _pulse.dispose();
    super.dispose();
  }

  /// What his body shows: who is talking first, then how he feels about it.
  Mood _shownMood() {
    switch (call.act) {
      case CallAct.userTalking:
        return app.userStressed ? Mood.care : Mood.listening;
      case CallAct.working:
        return Mood.work;
      case CallAct.speaking:
        const expressive = {Mood.happy, Mood.excited, Mood.care, Mood.wow};
        return expressive.contains(app.mood) ? app.mood : Mood.talking;
      case CallAct.connecting:
        return Mood.think;
      default:
        return app.mood == Mood.think || app.mood == Mood.work ? Mood.idle : app.mood;
    }
  }

  String get _status {
    if (call.inCall && call.linkNote != null) return call.linkNote!;
    return switch (call.act) {
      CallAct.idle => call.note ?? 'Call button dabaiye aur ${app.aName} se seedhe baat kijiye',
      CallAct.connecting => '${app.aName} ko call lag raha hai…',
      CallAct.listening => call.muted ? 'Mic band hai' : app.g('Boliye, ${app.aName} sun raha hai'),
      CallAct.userTalking => app.g('Sun raha hoon…'),
      CallAct.working => '${call.tool ?? app.g('Kaam kar raha hoon')}…',
      CallAct.speaking => app.g('${app.aName} bol raha hai · beech mein bol sakte hain'),
    };
  }

  @override
  Widget build(BuildContext context) {
    final voice = app.voices.firstWhere((v) => v['id'] == app.voiceName, orElse: () => {'id': app.voiceName});
    return ListenableBuilder(
      listenable: Listenable.merge([app, call]),
      builder: (context, _) {
        final cards = call.cards;
        if (cards.length > _seenCards) _cardsOpen = true;   // a new card: show it
        _seenCards = cards.length;
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
              if (call.inCall) const Pill('● LIVE', fg: Colors.white, bg: Color(0xCCDC2626)),
              if (!call.inCall) Pill(moodStyles[app.mood]!.label, fg: moodStyles[app.mood]!.aura, bg: const Color(0x1FFFFFFF)),
            ]),
          ),
          if (call.inCall)
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 4, 20, 0),
              child: Text('Doosre section mein jaane par bhi call chalti rahegi.',
                  style: TextStyle(color: C.faint, fontSize: 11.5, fontWeight: FontWeight.w600)),
            ),
          Padding(padding: const EdgeInsets.only(top: 8), child: WorkTheatrePanel(app: app)),
          Expanded(
            child: Stack(children: [
              Positioned.fill(
                child: LayoutBuilder(
                  builder: (context, box) => Center(
                    child: LiveSantosh(
                      feeling: _shownMood(),
                      level: call.act == CallAct.speaking ? call.outLevel : (call.act == CallAct.userTalking ? call.inLevel : 0),
                      thought: call.act != CallAct.speaking,
                      size: math.min(box.maxHeight * .82, 330),
                    ),
                  ),
                ),
              ),
              if (cards.isNotEmpty) Positioned(left: 0, right: 0, top: 0, bottom: 0, child: _cardsTray(cards)),
              Positioned(left: 0, right: 0, bottom: 4, child: ArtifactCallPill(app: app)),
              Positioned(right: 12, top: 8, child: BrowserCallThumb(app: app)),
            ]),
          ),
          if (call.inCall && call.lockIssue != null) LockSafeBanner(text: call.lockIssue!),
          if (call.inCall && call.speaker != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(call.speakerIsOwner ? Icons.verified_user_rounded : Icons.record_voice_over_rounded,
                    size: 16, color: call.speakerIsOwner ? C.ok : C.accentSoft),
                const SizedBox(width: 6),
                Text('Awaaz se pehchana: ${call.speaker}',
                    style: TextStyle(color: call.speakerIsOwner ? C.ok : C.accentSoft, fontSize: 12.5, fontWeight: FontWeight.w700)),
              ]),
            ),
          _captions(),
          if (call.fileNote != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 6, 20, 0),
              child: Text(call.fileNote!, textAlign: TextAlign.center, style: const TextStyle(color: C.teal, fontSize: 12.5, fontWeight: FontWeight.w600)),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
            child: Text(_status, textAlign: TextAlign.center,
                style: TextStyle(color: call.act == CallAct.idle ? C.muted : C.accent, fontWeight: FontWeight.w700)),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              _small(call.muted ? Icons.mic_off_rounded : Icons.mic_none_rounded, call.muted ? 'Mic chalu karo' : 'Mic band karo',
                  !call.inCall ? null : call.toggleMute),
              const SizedBox(width: 26),
              _orb(),
              const SizedBox(width: 26),
              _small(Icons.front_hand_rounded, '${app.aName} ko roko', call.act == CallAct.speaking ? call.cutSpeech : null),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: TextButton.icon(
              onPressed: !call.inCall || call.uploading ? null : _attach,
              icon: call.uploading
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.attach_file_rounded, color: C.chip),
              label: Text(call.uploading ? 'File ja rahi hai…' : 'Photo / PDF / file dikhaiye',
                  style: const TextStyle(color: C.chip, fontWeight: FontWeight.w600)),
            ),
          ),
        ]);
      },
    );
  }

  /// Approvals, downloads, drafts and other cards that came during the call: right here, no need to open Chat.
  Widget _cardsTray(List<FeedItem> cards) {
    if (!_cardsOpen) {
      return Align(
        alignment: Alignment.topLeft,
        child: Padding(
          padding: const EdgeInsets.only(left: 12, top: 8),
          child: ActionChip(
            avatar: const Icon(Icons.style_rounded, size: 18, color: C.onAccent),
            backgroundColor: C.accent,
            label: Text('${cards.length} card${cards.length > 1 ? 's' : ''} dekhiye',
                style: const TextStyle(color: C.onAccent, fontWeight: FontWeight.w800)),
            onPressed: () => setState(() => _cardsOpen = true),
          ),
        ),
      );
    }
    return Container(
      margin: const EdgeInsets.fromLTRB(10, 4, 10, 40),
      decoration: BoxDecoration(
        color: const Color(0xF0151030),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0x33FFFFFF)),
        boxShadow: const [BoxShadow(color: Color(0x88000000), blurRadius: 24, offset: Offset(0, 10))],
      ),
      child: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 4, 0),
          child: Row(children: [
            const Icon(Icons.style_rounded, color: C.accentSoft, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text('Call ke dauraan · ${cards.length}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5))),
            TextButton(onPressed: () => setState(() => _cardsOpen = false), child: const Text('Chhota karo')),
          ]),
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(10, 4, 10, 10),
            children: [
              for (final it in cards.reversed)
                Stack(children: [
                  feedCard(context, app, it) ?? const SizedBox.shrink(),
                  Positioned(
                    right: 0, top: 0,
                    child: IconButton(
                      tooltip: 'Hataiye',
                      visualDensity: VisualDensity.compact,
                      onPressed: () => call.dismiss(it),
                      icon: const Icon(Icons.close_rounded, size: 18, color: C.faint),
                    ),
                  ),
                ]),
            ],
          ),
        ),
      ]),
    );
  }

  Widget _captions() {
    if (call.heard.isEmpty && call.reply.isEmpty) return const SizedBox(height: 8);
    return Glass(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxHeight: 150),
        child: SingleChildScrollView(
          reverse: true,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (call.heard.isNotEmpty) ...[
              const Text('AAP', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.muted)),
              Text(call.heard, style: const TextStyle(fontSize: 15, height: 1.35, color: C.ink)),
            ],
            if (call.reply.isNotEmpty) ...[
              if (call.heard.isNotEmpty) const SizedBox(height: 8),
              Text(app.aName.toUpperCase(), style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: C.accent)),
              Text(call.reply, style: const TextStyle(fontSize: 15, height: 1.35, color: C.ink, fontWeight: FontWeight.w600)),
            ],
          ]),
        ),
      ),
    );
  }

  Future<void> _attach() async {
    final picked = await pickAttachments(context);
    if (picked.isEmpty) return;
    await call.attachFiles([for (final f in picked) (name: f.name, bytes: f.bytes)]);
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
        label: call.inCall ? 'Call khatam karo' : '${app.aName} ko call karo',
        child: GestureDetector(
          onTap: call.act == CallAct.connecting ? null : (call.inCall ? call.end : call.start),
          child: AnimatedBuilder(
            animation: _pulse,
            builder: (context, _) => CustomPaint(
              painter: _Rings(_pulse.value, call.act, call.inLevel, call.outLevel),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: 92,
                height: 92,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: call.inCall
                      ? const LinearGradient(colors: [Color(0xFFEF4444), Color(0xFFB91C1C)], begin: Alignment.topLeft, end: Alignment.bottomRight)
                      : C.gradient,
                  boxShadow: [BoxShadow(color: (call.inCall ? const Color(0xFFEF4444) : C.accent).withOpacity(.45), blurRadius: 28, offset: const Offset(0, 10))],
                ),
                child: call.act == CallAct.connecting
                    ? const Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator(color: C.onAccent, strokeWidth: 3))
                    : Icon(call.inCall ? Icons.call_end_rounded : Icons.call_rounded, color: call.inCall ? Colors.white : C.onAccent, size: 38),
              ),
            ),
          ),
        ),
      );
}

/// Shown on every other screen while a call is on: who you are talking to, how long, mute, hang up, tap to return.
class CallBar extends StatelessWidget {
  const CallBar({super.key, required this.app, required this.onOpen});
  final Santosh app;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final call = app.voiceCall;
    return ListenableBuilder(
      listenable: call,
      builder: (context, _) {
        if (!call.inCall) return const SizedBox.shrink();
        final e = call.elapsed;
        final t = '${e.inMinutes}:${(e.inSeconds % 60).toString().padLeft(2, '0')}';
        final n = call.cards.length;
        final what = switch (call.act) {
          CallAct.connecting => 'call lag raha hai…',
          CallAct.speaking => 'bol raha hai',
          CallAct.userTalking => 'sun raha hai',
          CallAct.working => call.tool ?? 'kaam kar raha hai',
          _ => call.muted ? 'mic band' : 'call chal rahi hai',
        };
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
          child: Material(
            color: const Color(0xFF15803D),
            borderRadius: BorderRadius.circular(20),
            child: InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: onOpen,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 6, 6, 6),
                child: Row(children: [
                  const Icon(Icons.graphic_eq_rounded, color: Colors.white, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text('${app.aName} · $t · $what${n > 0 ? ' · $n card' : ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
                  ),
                  IconButton(
                    tooltip: call.muted ? 'Mic chalu karo' : 'Mic band karo',
                    onPressed: call.toggleMute,
                    icon: Icon(call.muted ? Icons.mic_off_rounded : Icons.mic_rounded, color: Colors.white),
                  ),
                  IconButton(
                    tooltip: 'Call khatam karo',
                    onPressed: call.end,
                    style: IconButton.styleFrom(backgroundColor: const Color(0xFFDC2626)),
                    icon: const Icon(Icons.call_end_rounded, color: Colors.white),
                  ),
                ]),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Rings extends CustomPainter {
  _Rings(this.t, this.act, this.inLevel, this.outLevel);
  final double t;
  final CallAct act;
  final double inLevel;
  final double outLevel;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    final p = Paint()..style = PaintingStyle.stroke;
    switch (act) {
      case CallAct.userTalking:
        for (var i = 0; i < 3; i++) {
          final k = (t + i / 3) % 1;
          p
            ..strokeWidth = 3
            ..color = C.teal.withOpacity((1 - k) * (.25 + inLevel * .7));
          canvas.drawCircle(c, r + 6 + k * (16 + inLevel * 40), p);
        }
      case CallAct.speaking:
        p
          ..strokeWidth = 4
          ..color = C.accent.withOpacity(.55);
        canvas.drawCircle(c, r + 6 + outLevel * 22, p);
        p
          ..strokeWidth = 2
          ..color = C.accent.withOpacity(.25);
        canvas.drawCircle(c, r + 14 + outLevel * 34, p);
      case CallAct.working:
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
