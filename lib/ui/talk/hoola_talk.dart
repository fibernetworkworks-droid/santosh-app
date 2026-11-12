// v0.865 R5 TALK (docs/HOOLA_APP_REDESIGN_PLAN.md R5): the live call in the new design. The call itself is the same
// CallSession (app.voiceCall) the old screen drives - nothing about the engine changed; leaving this screen never ends
// the call.
//
//   top      close (the call keeps running) · "Santosh" · Live + the call clock
//   middle   the orb: it grows with HER voice while she talks and with HIS while he speaks, breathes when idle,
//            holds still under reduce motion (the level still shows); tap it while he speaks = stop him
//   below    what she said / what Santosh said (the last turn), the status in plain words
//   cards    approvals, files, pages that came during the call, one at a time, drawn with the R4 cards
//   bottom   Show something (photo / PDF / file) · Type · Mute · End (red); before a call: one "Start the call" pill
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../call_session.dart';
import '../../state.dart';
import '../artifact_screen.dart' show ArtifactCallPill;
import '../attach.dart';
import '../browser_live.dart' show BrowserCallThumb;
import '../chat/hoola_card.dart';
import '../chat_screen.dart' show feedCard;
import '../glass.dart' show santoshTheme;
import '../hoola_theme.dart';

class HoolaTalk extends StatefulWidget {
  const HoolaTalk({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaTalk> createState() => _HoolaTalkState();
}

class _HoolaTalkState extends State<HoolaTalk> with SingleTickerProviderStateMixin {
  late final AnimationController _tick = AnimationController(vsync: this, duration: const Duration(seconds: 4))..repeat();
  final _typeCtrl = TextEditingController();
  final _typeFocus = FocusNode();
  bool _typing = false;
  FeedItem? _focus;
  int _seenCards = 0;
  bool _cardsOpen = true;
  Timer? _clock;

  Santosh get app => widget.app;
  CallSession get call => app.voiceCall;

  @override
  void initState() {
    super.initState();
    call.screenOpen = true;
    if (!call.inCall) app.voiceMode = true;   // replies here are spoken by the call
    _clock = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && call.inCall) setState(() {});
    });
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
    _tick.dispose();
    _clock?.cancel();
    _typeCtrl.dispose();
    _typeFocus.dispose();
    super.dispose();
  }

  String get _clockText {
    final s = call.startedAt == null ? 0 : DateTime.now().difference(call.startedAt!).inSeconds.clamp(0, 359999);
    final h = s ~/ 3600, m = (s % 3600) ~/ 60, sec = s % 60;
    final mm = m.toString().padLeft(h > 0 ? 2 : 1, '0'), ss = sec.toString().padLeft(2, '0');
    return h > 0 ? '$h:$mm:$ss' : '$mm:$ss';
  }

  String get _status {
    if (call.inCall && call.linkNote != null) return call.linkNote!;
    if (call.inCall && call.onHold) {
      return call.holdReason == 'phone_call'
          ? '${app.aName} is quiet while you are on your phone call'
          : '${app.aName} is quiet. Say "${app.aName}" or tap Come back';
    }
    return switch (call.act) {
      CallAct.idle => call.note ?? 'Talk to ${app.aName} in your own words',
      CallAct.connecting => 'Calling ${app.aName}…',
      CallAct.listening => call.muted ? 'Your mic is off' : 'Listening',
      CallAct.userTalking => 'Listening',
      CallAct.working => call.tool == null ? 'Working on it…' : '${call.tool}…',
      CallAct.speaking => 'Speaking · tap the circle to stop',
    };
  }

  Future<void> _attach() async {
    final picked = await pickAttachments(context);
    if (picked.isEmpty) return;
    await call.attachFiles([for (final f in picked) (name: f.name, bytes: f.bytes)]);
  }

  void _sendTyped() {
    final t = _typeCtrl.text.trim();
    if (t.isEmpty) return;
    _typeCtrl.clear();
    HapticFeedback.lightImpact();
    call.sendText(t);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: ListenableBuilder(
          listenable: Listenable.merge([app, call]),
          builder: (context, _) {
            final cards = call.cards;
            if (cards.length > _seenCards) {
              _cardsOpen = true;
              _focus = null;
            }
            _seenCards = cards.length;
            final tray = cards.isNotEmpty && _cardsOpen;
            final keyboard = MediaQuery.viewInsetsOf(context).bottom > 0;
            return Column(children: [
              _top(c),
              if (call.inCall && call.lockIssue != null) _banner(c, Icons.lock_clock_outlined, call.lockIssue!, warn: true),
              if (call.inCall && call.onHold) _banner(c, Icons.voice_over_off_rounded, call.holdSay ?? 'You are talking to someone else'),
              if (!tray && call.backgroundCount > 0 && !keyboard)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('${call.backgroundCount} ${call.backgroundCount == 1 ? 'task is' : 'tasks are'} running in the chat',
                      style: HoolaType.small(c)),
                ),
              Expanded(
                child: tray
                    ? _cards(c, cards)
                    : keyboard
                        ? const SizedBox.shrink()
                        : Column(children: [
                            Expanded(
                              child: Stack(children: [
                                Positioned.fill(child: Center(child: _orb(c))),
                                // a page being built and a website being worked on during the call stay visible
                                Positioned(left: 0, right: 0, bottom: 4, child: ArtifactCallPill(app: app)),
                                Positioned(right: 12, top: 8, child: BrowserCallThumb(app: app)),
                              ]),
                            ),
                            if (call.inCall && call.speaker != null)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 4),
                                child: Text('Recognised by voice: ${call.speaker}',
                                    style: HoolaType.small(c).copyWith(color: call.speakerIsOwner ? c.ok : c.accent)),
                              ),
                            if (cards.isNotEmpty)
                              TextButton.icon(
                                onPressed: () => setState(() => _cardsOpen = true),
                                icon: const Icon(Icons.style_outlined, size: 18),
                                label: Text('${cards.length} ${cards.length == 1 ? 'card' : 'cards'} from this call'),
                              ),
                          ]),
              ),
              if (!keyboard || !tray) _words(c),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 6, 24, 10),
                child: AnimatedSwitcher(
                  duration: HoolaMotion.of(context, HoolaMotion.fade),
                  child: Text(_status, key: ValueKey(_status), textAlign: TextAlign.center,
                      style: HoolaType.body(c).copyWith(color: call.act == CallAct.idle ? c.ink3 : c.ink2)),
                ),
              ),
              if (call.fileNote != null)
                Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(call.fileNote!, style: HoolaType.small(c).copyWith(color: c.accent))),
              if (_typing && call.inCall) _typeBar(c),
              _controls(c),
              const SizedBox(height: 12),
            ]);
          },
        ),
      ),
    );
  }

  Widget _top(HoolaColors c) => SizedBox(
        height: 56,
        child: Row(children: [
          const SizedBox(width: 4),
          IconButton(
            tooltip: call.inCall ? 'Back to the chat (the call keeps going)' : 'Close',
            onPressed: () => Navigator.of(context).maybePop(),
            icon: Icon(Icons.keyboard_arrow_down_rounded, color: c.ink, size: 28),
          ),
          Expanded(
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text(app.aName, style: HoolaType.title(c)),
              if (call.inCall)
                Row(mainAxisSize: MainAxisSize.min, children: [
                  Container(width: 7, height: 7, decoration: BoxDecoration(color: c.bad, shape: BoxShape.circle)),
                  const SizedBox(width: 6),
                  Text(
                    '${call.engine == 'openai' ? 'Real voice' : 'Live'} · $_clockText',
                    style: HoolaType.small(c).copyWith(fontFeatures: const [FontFeature.tabularFigures()]),
                  ),
                ])
              else
                Text('Voice call', style: HoolaType.small(c)),
            ]),
          ),
          const SizedBox(width: 52),
        ]),
      );

  Widget _banner(HoolaColors c, IconData icon, String text, {bool warn = false}) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        child: HCNote(text, icon: icon, warn: warn),
      );

  /// The orb: her voice grows it while she talks, his while he speaks; it breathes when idle.
  Widget _orb(HoolaColors c) {
    final reduced = HoolaMotion.reduced(context);
    return Semantics(
      button: call.act == CallAct.speaking,
      label: call.act == CallAct.speaking ? 'Stop ${app.aName} speaking' : _status,
      child: GestureDetector(
        onTap: call.act == CallAct.speaking ? call.cutSpeech : null,
        child: AnimatedBuilder(
          animation: _tick,
          builder: (context, _) {
            final level = switch (call.act) {
              CallAct.userTalking => call.inLevel,
              CallAct.speaking => call.outLevel,
              _ => 0.0,
            }.clamp(0.0, 1.0);
            final breathe = reduced || !call.inCall ? 0.0 : (math.sin(_tick.value * 2 * math.pi) + 1) / 2 * .04;
            final working = call.act == CallAct.working || call.act == CallAct.connecting;
            final scale = 1 + level * .28 + breathe;
            return SizedBox(
              width: 260,
              height: 260,
              child: CustomPaint(
                painter: _OrbPainter(
                  scale: scale,
                  spin: reduced ? 0 : _tick.value,
                  working: working,
                  you: call.act == CallAct.userTalking,
                  live: call.inCall,
                  c: c,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  /// The last turn: what she said, what he said.
  Widget _words(HoolaColors c) {
    if (call.heard.isEmpty && call.reply.isEmpty) return const SizedBox(height: 4);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxHeight: 132),
        child: SingleChildScrollView(
          reverse: true,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (call.heard.isNotEmpty)
              Text(call.heard, textAlign: TextAlign.right, style: HoolaType.body(c).copyWith(color: c.ink2)),
            if (call.heard.isNotEmpty && call.reply.isNotEmpty) const SizedBox(height: 8),
            if (call.reply.isNotEmpty) Text(call.reply, style: HoolaType.reply(c).copyWith(fontSize: 17)),
          ]),
        ),
      ),
    );
  }

  Widget _cards(HoolaColors c, List<FeedItem> cards) {
    final focus = _focus != null && cards.contains(_focus) ? _focus! : cards.last;
    final mine = hoolaCardFor(context, app, focus);
    Widget card = mine ??
        ClipRRect(
          borderRadius: HoolaRadius.r(HoolaRadius.cardLg),
          child: Theme(
            data: santoshTheme(),
            child: ColoredBox(color: santoshTheme().scaffoldBackgroundColor,
                child: Padding(padding: const EdgeInsets.fromLTRB(8, 8, 8, 0), child: feedCard(context, app, focus) ?? const SizedBox.shrink())),
          ),
        );
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 8, 4),
        child: Row(children: [
          Expanded(child: Text('From this call · ${cards.length}', style: HoolaType.title(c))),
          IconButton(tooltip: 'Remove this card from the call', onPressed: () => call.dismiss(focus),
              icon: Icon(Icons.close_rounded, color: c.ink3)),
          TextButton(onPressed: () => setState(() => _cardsOpen = false), child: const Text('Back to call')),
        ]),
      ),
      if (cards.length > 1)
        SizedBox(
          height: 40,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
            for (final it in cards.reversed)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  selected: identical(it, focus),
                  onSelected: (_) => setState(() => _focus = it),
                  label: Text(_cardTitle(it), maxLines: 1, overflow: TextOverflow.ellipsis),
                ),
              ),
          ]),
        ),
      Expanded(child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 8), children: [card])),
    ]);
  }

  String _cardTitle(FeedItem f) {
    final t = '${f.data['title'] ?? f.data['what'] ?? f.data['label'] ?? f.data['name'] ?? ''}'.trim();
    return t.isEmpty ? f.kind.replaceAll('_', ' ') : (t.length > 26 ? '${t.substring(0, 26)}…' : t);
  }

  Widget _typeBar(HoolaColors c) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _typeCtrl,
              focusNode: _typeFocus,
              autofocus: true,
              minLines: 1,
              maxLines: 3,
              style: HoolaType.bodyLarge(c),
              decoration: InputDecoration(hintText: 'Type to ${app.aName} (a spelling, an address)', isDense: true),
              onSubmitted: (_) => _sendTyped(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            tooltip: 'Send',
            onPressed: _sendTyped,
            style: IconButton.styleFrom(backgroundColor: c.accent, foregroundColor: c.onAccent),
            icon: const Icon(Icons.arrow_upward_rounded),
          ),
        ]),
      );

  Widget _controls(HoolaColors c) {
    if (!call.inCall) {
      final connecting = call.act == CallAct.connecting;
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: SizedBox(
          width: double.infinity,
          height: 56,
          child: FilledButton.icon(
            onPressed: connecting
                ? null
                : () {
                    HapticFeedback.mediumImpact();
                    call.start();
                  },
            style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
            icon: connecting
                ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                : const Icon(Icons.graphic_eq_rounded),
            label: Text(connecting ? 'Calling…' : 'Start the call', style: HoolaType.button(c, color: c.onPill)),
          ),
        ),
      );
    }
    Widget round(String label, IconData icon, VoidCallback? onTap, {bool on = false, Color? bg, Color? fg}) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Semantics(
              button: true,
              label: label,
              toggled: on,
              excludeSemantics: true,
              child: Material(
                color: bg ?? (on ? c.ink : c.sunk),
                shape: const CircleBorder(),
                child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: onTap == null
                      ? null
                      : () {
                          HapticFeedback.selectionClick();
                          onTap();
                        },
                  child: SizedBox(width: 60, height: 60, child: Icon(icon, size: 24, color: fg ?? (on ? c.bg : c.ink))),
                ),
              ),
            ),
            const SizedBox(height: 6),
            Text(label, style: HoolaType.label(c)),
          ],
        );
    return Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
      round(call.uploading ? 'Sending' : 'Show', Icons.add_photo_alternate_outlined, call.uploading ? null : _attach),
      round('Type', Icons.keyboard_outlined, call.onHold ? null : () => setState(() => _typing = !_typing), on: _typing),
      if (call.holdReason == 'phone_call')
        round(call.muted ? 'Unmute' : 'Mute', call.muted ? Icons.mic_off_rounded : Icons.mic_none_rounded, call.toggleMute, on: call.muted)
      else if (call.onHold)
        round('Come back', Icons.record_voice_over_outlined, call.toggleHold, on: true)
      else
        round(call.muted ? 'Unmute' : 'Mute', call.muted ? Icons.mic_off_rounded : Icons.mic_none_rounded, call.toggleMute, on: call.muted),
      round('End', Icons.call_end_rounded, () {
        HapticFeedback.mediumImpact();
        call.end();
      }, bg: c.bad, fg: c.onAccent),
    ]);
  }
}

/// The orb: a soft disc in the accent, its rim widening with the voice level; a turning arc while it works.
class _OrbPainter extends CustomPainter {
  _OrbPainter({required this.scale, required this.spin, required this.working, required this.you, required this.live, required this.c});
  final double scale;
  final double spin;
  final bool working;
  final bool you;
  final bool live;
  final HoolaColors c;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final base = size.shortestSide * .30;
    final r = base * scale;
    final tone = you ? c.ink : c.accent;
    // the halo
    canvas.drawCircle(center, r * 1.35, Paint()..color = tone.withOpacity(live ? .08 : .05));
    canvas.drawCircle(center, r * 1.15, Paint()..color = tone.withOpacity(live ? .12 : .07));
    // the disc
    final disc = Paint()
      ..shader = RadialGradient(colors: [tone.withOpacity(.95), tone.withOpacity(.70)], radius: .9)
          .createShader(Rect.fromCircle(center: center, radius: r));
    canvas.drawCircle(center, r, disc);
    // working: a turning arc around it
    if (working) {
      final arc = Paint()
        ..color = c.accent
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(Rect.fromCircle(center: center, radius: r * 1.28), spin * 2 * math.pi, math.pi * .6, false, arc);
    }
  }

  @override
  bool shouldRepaint(covariant _OrbPainter o) =>
      o.scale != scale || o.spin != spin || o.working != working || o.you != you || o.live != live || o.c != c;
}
