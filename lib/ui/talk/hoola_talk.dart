// v0.865 R5 TALK (docs/HOOLA_APP_REDESIGN_PLAN.md R5): the live call in the new design. The call itself is the same
// CallSession (app.voiceCall) the old screen drives - nothing about the engine changed; leaving this screen never ends
// the call.
//
// v0.896 CALL GLOW (owner, after the live preview of her Claude + Gemini call videos: "GO GLOW FROM BELOW and living
// pill like gemini both"): the screen now looks and moves like those two calls, in Hoola's colours.
//   top      back to the chat (the call keeps running) · Live + the call clock · the look switch (gear)
//   middle   the Hoola mark + a serif line: "Hold tight, connecting…" -> "Let's talk, <name>"; while it connects the
//            mark folds to its centre dot, opens again and its two rings turn opposite ways, then settle into place.
//            It fades once words start: hers in a bubble at the top right, his in serif in the middle.
//   light    a soft light rises from the bottom when the call opens and follows the voice every frame - cool blue
//            (the theme's info colour) while she speaks, Hoola violet while he speaks, a slow breath when quiet;
//            muted or on hold it drains away
//   bottom   'glow'  (Claude): the mic in the middle above + · Type · End
//            'pill'  (Gemini): + · Type · a living pill of moving light (tap = stop him) · mic · End
//            her pick lives in Settings > Call look (app.callLook) and the gear here.
//   cards    approvals, files, pages that came during the call, one at a time, drawn with the R4 cards (unchanged)
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';

import '../../call_session.dart';
import '../../state.dart';
import '../artifact_screen.dart' show ArtifactCallPill;
import '../attach.dart';
import '../browser_live.dart' show BrowserCallThumb;
import '../chat/hoola_card.dart' show HCNote;
import '../chat/hoola_cards_all.dart';
import '../hoola_theme.dart';

class HoolaTalk extends StatefulWidget {
  const HoolaTalk({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaTalk> createState() => _HoolaTalkState();
}

/// Everything that moves every frame: the voice level, how far the light has risen, how violet it is (him) or blue
/// (her), and the mark's rings. One notifier, so a frame repaints the light and the mark and nothing else.
class CallMotion extends ChangeNotifier {
  double t = 0;            // seconds since the screen opened
  double level = 0;        // 0..1, smoothed
  double appear = 0;       // 0 = no light, 1 = risen
  double mix = 0;          // 0 = her colour, 1 = his
  double ringO = 0, ringI = 0;           // ring angles, degrees
  double ring = 1, core = 1, needle = 1; // ring scale, core scale, needle opacity
  bool spin = false;
  double _tO = 0, _tI = 0;
  double? _foldAt;   // t when the call started opening
  bool reduced = false;

  void fold() {
    _foldAt = t;
  }

  void step(double dt, {required double target, required bool lit, required bool him, required bool spinning}) {
    t += dt;
    level += (target - level) * math.min(1, dt * 12);
    appear += ((lit ? 1 : 0) - appear) * math.min(1, dt * (lit ? 2.6 : 3.4));
    mix += ((him ? 1 : 0) - mix) * math.min(1, dt * 3.5);
    final folding = _foldAt != null && t - _foldAt! < .26;
    final spinNow = spinning && !folding && !reduced;
    if (spin && !spinNow) {          // settle into place: the next full turn in the way each ring was going
      _tO = (ringO / 360).ceilToDouble() * 360;
      _tI = (ringI / 360).floorToDouble() * 360;
    }
    spin = spinNow;
    final k = math.min(1.0, dt * 9);
    ring += ((folding ? .25 : 1) - ring) * k;
    core += ((folding ? 1.25 : 1) - core) * k;
    needle += ((folding ? 0 : spinning ? .35 : 1) - needle) * math.min(1, dt * 6);
    if (spin) {
      ringO += 300 * dt;
      ringI -= 380 * dt;
    } else {
      final s = math.min(1.0, dt * 4.5);
      ringO += (_tO - ringO) * s;
      ringI += (_tI - ringI) * s;
    }
    notifyListeners();
  }
}

class _HoolaTalkState extends State<HoolaTalk> with SingleTickerProviderStateMixin {
  late final Ticker _ticker = createTicker(_onTick);
  final _m = CallMotion();
  Duration _last = Duration.zero;
  CallAct _lastAct = CallAct.idle;
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
    _ticker.start();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (app.autoCall && app.realtimeVoice && !call.inCall) {
        app.autoCall = false;
        call.start();
      }
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _m.reduced = HoolaMotion.reduced(context);
  }

  @override
  void dispose() {
    call.screenOpen = false;
    if (!call.inCall) app.voiceMode = false;
    _ticker.dispose();
    _m.dispose();
    _clock?.cancel();
    _typeCtrl.dispose();
    _typeFocus.dispose();
    super.dispose();
  }

  void _onTick(Duration now) {
    final dt = ((now - _last).inMicroseconds / 1e6).clamp(0.0, .05);
    _last = now;
    final act = call.act;
    if (act == CallAct.connecting && _lastAct != CallAct.connecting) _m.fold();
    _lastAct = act;
    final live = call.inCall && !call.muted && !call.onHold;
    final breath = _m.reduced ? .1 : .1 + .06 * math.sin(_m.t * 1.6);
    final target = !live
        ? 0.0
        : switch (act) {
            CallAct.userTalking => call.inLevel.clamp(0.0, 1.0),
            CallAct.speaking => call.outLevel.clamp(0.0, 1.0),
            CallAct.working => breath + .06,
            _ => breath,
          };
    _m.step(dt,
        target: target,
        lit: live,
        him: act == CallAct.speaking,
        spinning: act == CallAct.connecting || act == CallAct.working);
  }

  String get _clockText {
    final s = call.startedAt == null ? 0 : DateTime.now().difference(call.startedAt!).inSeconds.clamp(0, 359999);
    final h = s ~/ 3600, m = (s % 3600) ~/ 60, sec = s % 60;
    final mm = m.toString().padLeft(h > 0 ? 2 : 1, '0'), ss = sec.toString().padLeft(2, '0');
    return h > 0 ? '$h:$mm:$ss' : '$mm:$ss';
  }

  String get _firstName => ((app.account?['name'] as String?) ?? '').trim().split(' ').first;

  /// The serif line under the mark.
  String get _hello {
    if (call.act == CallAct.connecting) return 'Hold tight, connecting…';
    if (call.inCall) return _firstName.isEmpty ? "Let's talk" : "Let's talk, $_firstName";
    return call.note ?? 'Talk to ${app.aName} in your own words';
  }

  /// A quiet line under the words, only when there is something to say (Claude's call shows none while listening).
  String? get _status {
    if (!call.inCall) return null;
    if (call.linkNote != null) return call.linkNote!;
    if (call.onHold) {
      return call.holdReason == 'phone_call'
          ? '${app.aName} is quiet while you are on your phone call'
          : '${app.aName} is quiet. Say "${app.aName}" or tap Come back';
    }
    return switch (call.act) {
      CallAct.working => call.tool == null ? 'Working on it…' : '${call.tool}…',
      CallAct.speaking => 'Tap to stop ${app.aName}',
      CallAct.listening when call.muted => 'Your mic is off',
      _ => null,
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

  Future<void> _pickLook() async {
    final c = HoolaColors.of(context);
    final picked = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 8),
            child: Align(alignment: Alignment.centerLeft, child: Text('Call look', style: HoolaType.heading(c))),
          ),
          for (final l in Santosh.callLooks)
            ListTile(
              leading: Icon(l == 'pill' ? Icons.blur_linear_rounded : Icons.wb_twilight_rounded, color: c.ink2),
              title: Text(Santosh.callLookLabels[l]!, style: HoolaType.bodyLarge(c)),
              subtitle: Text(l == 'pill' ? 'A living pill of light between the buttons' : 'A soft light rises from the bottom, the mic in the middle',
                  style: HoolaType.small(c)),
              trailing: app.callLook == l ? Icon(Icons.check_rounded, color: c.accent) : null,
              onTap: () => Navigator.pop(ctx, l),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (picked != null) await app.setCallLook(picked);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: ListenableBuilder(
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
          final pill = app.callLook == 'pill';
          return Stack(children: [
            // the light from below, under everything
            Positioned.fill(child: IgnorePointer(child: CustomPaint(painter: CallGlowPainter(_m, c, pill: pill)))),
            SafeArea(
              child: Column(children: [
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
                          : _middle(c, cards),
                ),
                if (_status != null)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 4, 24, 8),
                    child: AnimatedSwitcher(
                      duration: HoolaMotion.of(context, HoolaMotion.fade),
                      child: Text(_status!, key: ValueKey(_status), textAlign: TextAlign.center, style: HoolaType.small(c).copyWith(color: c.ink2)),
                    ),
                  ),
                if (call.fileNote != null)
                  Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(call.fileNote!, style: HoolaType.small(c).copyWith(color: c.accent))),
                if (_typing && call.inCall) _typeBar(c),
                _controls(c, pill: pill),
                const SizedBox(height: 14),
              ]),
            ),
          ]);
        },
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
            child: Center(
              child: call.inCall
                  ? Row(mainAxisSize: MainAxisSize.min, children: [
                      Container(width: 7, height: 7, decoration: BoxDecoration(color: c.bad, shape: BoxShape.circle)),
                      const SizedBox(width: 6),
                      Text(
                        '${call.engine == 'openai' ? 'Real voice' : 'Live'} · $_clockText',
                        style: HoolaType.small(c).copyWith(fontFeatures: const [FontFeature.tabularFigures()]),
                      ),
                    ])
                  : Text(app.aName, style: HoolaType.title(c)),
            ),
          ),
          IconButton(
            tooltip: 'Call look',
            onPressed: _pickLook,
            style: IconButton.styleFrom(backgroundColor: c.sunk),
            icon: Icon(Icons.settings_outlined, color: c.ink, size: 20),
          ),
          const SizedBox(width: 10),
        ]),
      );

  Widget _banner(HoolaColors c, IconData icon, String text, {bool warn = false}) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        child: HCNote(text, icon: icon, warn: warn),
      );

  /// The middle: the mark + greeting until words come, then her bubble (top right) and his words (serif).
  Widget _middle(HoolaColors c, List<FeedItem> cards) {
    final talked = call.inCall && (call.heard.isNotEmpty || call.reply.isNotEmpty);
    final fade = HoolaMotion.of(context, HoolaMotion.fade);
    final speaking = call.act == CallAct.speaking;
    return Semantics(
      button: speaking,
      label: speaking ? 'Stop ${app.aName} speaking' : null,
      child: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onTap: speaking ? call.cutSpeech : null,
        child: Stack(children: [
          // the mark + the greeting
          Positioned(
            left: 24,
            right: 24,
            top: 0,
            bottom: 0,
            child: Align(
              alignment: const Alignment(0, -.35),
              child: AnimatedOpacity(
                opacity: talked ? 0 : 1,
                duration: fade,
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  CallMark(motion: _m, size: 46, color: c.accent),
                  const SizedBox(height: 16),
                  AnimatedSwitcher(
                    duration: fade,
                    child: Text(_hello, key: ValueKey(_hello), textAlign: TextAlign.center,
                        style: HoolaType.reply(c).copyWith(fontSize: 23, height: 1.3)),
                  ),
                ]),
              ),
            ),
          ),
          // what she said: a bubble at the top right
          if (call.inCall && call.heard.isNotEmpty)
            Positioned(
              top: 8,
              right: 16,
              left: 72,
              child: Align(
                alignment: Alignment.topRight,
                child: Container(
                  constraints: const BoxConstraints(maxHeight: 120),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                  decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(18)),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: Text(call.heard, style: HoolaType.body(c).copyWith(color: c.ink)),
                  ),
                ),
              ),
            ),
          // what he says: serif in the middle, in step with his voice
          if (call.inCall && call.reply.isNotEmpty)
            Positioned(
              left: 26,
              right: 26,
              top: 0,
              bottom: 0,
              child: Align(
                alignment: const Alignment(0, .05),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 220),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: SizedBox(
                      width: double.infinity,
                      child: Text(call.reply, style: HoolaType.reply(c).copyWith(fontSize: 19, height: 1.45)),
                    ),
                  ),
                ),
              ),
            ),
          // a page being built and a website being worked on during the call stay visible
          Positioned(left: 0, right: 0, bottom: 4, child: ArtifactCallPill(app: app)),
          Positioned(left: 12, top: 8, child: BrowserCallThumb(app: app)),
          if (call.inCall && call.speaker != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 44,
              child: Text('Recognised by voice: ${call.speaker}', textAlign: TextAlign.center,
                  style: HoolaType.small(c).copyWith(color: call.speakerIsOwner ? c.ok : c.accent)),
            ),
          if (cards.isNotEmpty)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Center(
                child: TextButton.icon(
                  onPressed: () => setState(() => _cardsOpen = true),
                  icon: const Icon(Icons.style_outlined, size: 18),
                  label: Text('${cards.length} ${cards.length == 1 ? 'card' : 'cards'} from this call'),
                ),
              ),
            ),
        ]),
      ),
    );
  }

  Widget _cards(HoolaColors c, List<FeedItem> cards) {
    final focus = _focus != null && cards.contains(_focus) ? _focus! : cards.last;
    // v0.900 the same new-design cards as the chat (Details / Review opens a kind's full card)
    Widget card = hoolaCardAll(context, app, focus) ?? const SizedBox.shrink();
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

  Widget _controls(HoolaColors c, {required bool pill}) {
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
    Widget round(String label, IconData icon, VoidCallback? onTap, {double size = 48, Color? bg, Color? fg, bool on = false}) => Semantics(
          button: true,
          label: label,
          toggled: on,
          excludeSemantics: true,
          child: Tooltip(
            message: label,
            child: Material(
              color: bg ?? c.sunk,
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: onTap == null
                    ? null
                    : () {
                        HapticFeedback.selectionClick();
                        onTap();
                      },
                child: SizedBox(width: size, height: size, child: Icon(icon, size: size > 50 ? 24 : 22, color: fg ?? c.ink)),
              ),
            ),
          ),
        );
    // the mic: mute / unmute; on hold it brings him back
    final Widget mic;
    if (call.onHold && call.holdReason != 'phone_call') {
      mic = round('Come back', Icons.record_voice_over_outlined, call.toggleHold, size: pill ? 48 : 56, bg: c.ink, fg: c.bg, on: true);
    } else {
      mic = round(call.muted ? 'Unmute' : 'Mute', call.muted ? Icons.mic_off_rounded : Icons.mic_none_rounded, call.toggleMute,
          size: pill ? 48 : 56, bg: call.muted ? c.bad : null, fg: call.muted ? c.onAccent : null, on: call.muted);
    }
    final plus = round(call.uploading ? 'Sending' : 'Show a photo or file', Icons.add_rounded, call.uploading ? null : _attach);
    final end = round('End the call', Icons.close_rounded, () {
      HapticFeedback.mediumImpact();
      call.end();
    }, bg: c.ink, fg: c.bg);
    final type = call.onHold ? null : () => setState(() => _typing = !_typing);
    if (pill) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Row(children: [
          plus,
          const SizedBox(width: 8),
          round('Type', Icons.keyboard_outlined, type, bg: _typing ? c.ink : null, fg: _typing ? c.bg : null, on: _typing),
          const SizedBox(width: 8),
          Expanded(
            child: Semantics(
              button: call.act == CallAct.speaking,
              label: call.act == CallAct.speaking ? 'Stop ${app.aName} speaking' : 'The voice',
              child: GestureDetector(
                onTap: call.act == CallAct.speaking ? call.cutSpeech : null,
                child: ClipRRect(
                  borderRadius: HoolaRadius.r(28),
                  child: SizedBox(height: 56, child: CustomPaint(painter: CallPillPainter(_m, c, muted: call.muted || call.onHold))),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          mic,
          const SizedBox(width: 8),
          end,
        ]),
      );
    }
    return Column(mainAxisSize: MainAxisSize.min, children: [
      mic,
      const SizedBox(height: 16),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Row(children: [
          plus,
          const SizedBox(width: 10),
          Semantics(
            button: true,
            toggled: _typing,
            label: 'Type',
            excludeSemantics: true,
            child: Material(
              color: _typing ? c.ink : c.sunk,
              shape: const StadiumBorder(),
              child: InkWell(
                customBorder: const StadiumBorder(),
                onTap: type,
                child: SizedBox(
                  height: 48,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.keyboard_outlined, size: 20, color: _typing ? c.bg : c.ink),
                      const SizedBox(width: 8),
                      Text('Type', style: HoolaType.button(c, color: _typing ? c.bg : c.ink)),
                    ]),
                  ),
                ),
              ),
            ),
          ),
          const Spacer(),
          end,
        ]),
      ),
    ]);
  }
}

/// The Hoola mark of the call: the four layers of the app mark (assets/images/mark_*.png) moved by [CallMotion] -
/// folded to the core while the call opens, rings turning opposite ways while it connects or works, then in place.
class CallMark extends StatelessWidget {
  const CallMark({super.key, required this.motion, this.size = 46, required this.color});
  final CallMotion motion;
  final double size;
  final Color color;

  Widget _layer(String name, {double angle = 0, double scale = 1, double opacity = 1}) => Transform(
        alignment: Alignment.center,
        transform: Matrix4.identity()
          ..rotateZ(angle * math.pi / 180)
          ..scale(scale, scale),
        child: Opacity(
          opacity: opacity.clamp(0.0, 1.0),
          child: Image.asset('assets/images/mark_$name.png',
              width: size, height: size, color: color, colorBlendMode: BlendMode.srcIn, filterQuality: FilterQuality.medium),
        ),
      );

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
        child: SizedBox(
          width: size,
          height: size,
          child: AnimatedBuilder(
            animation: motion,
            builder: (context, _) {
              final m = motion;
              final ro = ((m.ring - .25) / .75).clamp(0.0, 1.0);
              final pulse = m.spin ? 1 + .08 * math.sin(m.t * 8) : 1.0;
              return Stack(children: [
                _layer('outer', angle: m.ringO, scale: m.ring, opacity: ro),
                _layer('inner', angle: m.ringI, scale: m.ring, opacity: ro),
                _layer('needle', scale: m.ring, opacity: m.needle * ro),
                _layer('core', scale: m.core * pulse),
              ]);
            },
          ),
        ),
      );
}

/// The light from below: a wide dome rising from the bottom edge with three soft lights drifting inside it, its height
/// and brightness following the voice. Her colour = the theme's info blue, his = Hoola violet; no raw colours here.
class CallGlowPainter extends CustomPainter {
  CallGlowPainter(this.m, this.c, {required this.pill}) : super(repaint: m);
  final CallMotion m;
  final HoolaColors c;
  final bool pill;

  @override
  void paint(Canvas canvas, Size size) {
    if (m.appear < .004) return;
    final w = size.width, h = size.height;
    final her = c.info, him = c.accent;
    final col = Color.lerp(her, him, m.mix)!;
    final col2 = Color.lerp(Color.lerp(her, c.bg, .25)!, Color.lerp(him, c.bad, .35)!, m.mix)!;
    final a = m.appear * (c.dark ? 1 : .75);
    final base = h * (pill ? .5 : .34);
    final hh = base * (.78 + .5 * m.level) * (.55 + .45 * m.appear);
    // the dome
    canvas.save();
    canvas.translate(w / 2, h + hh * .12);
    canvas.scale(1, hh / (w * .95));
    final r = w * .95;
    canvas.drawRect(
      Rect.fromLTWH(-w, -r * 1.2, w * 2, r * 1.3),
      Paint()
        ..shader = RadialGradient(colors: [
          col.withOpacity(((pill ? .85 : .62) * a * (.65 + .45 * m.level)).clamp(0.0, 1.0)),
          col.withOpacity((pill ? .45 : .30) * a),
          col.withOpacity(0),
        ], stops: const [0, .45, 1])
            .createShader(Rect.fromCircle(center: Offset.zero, radius: r)),
    );
    canvas.restore();
    // three soft lights drifting inside it
    final tt = m.reduced ? 0.0 : m.t;
    for (var i = 0; i < 3; i++) {
      final x = w * (.5 + .3 * math.sin(tt * .28 + i * 2.1));
      final y = h - hh * (.18 + .1 * i);
      final rr = w * (.26 + .06 * i) * (.8 + .7 * m.level * (i == 1 ? 1 : .6));
      final cc = i == 1 ? col2 : col;
      canvas.drawCircle(
        Offset(x, y),
        rr,
        Paint()
          ..shader = RadialGradient(colors: [cc.withOpacity((.32 * a * (.5 + m.level)).clamp(0.0, 1.0)), cc.withOpacity(0)])
              .createShader(Rect.fromCircle(center: Offset(x, y), radius: rr)),
      );
    }
  }

  @override
  bool shouldRepaint(covariant CallGlowPainter o) => o.c != c || o.pill != pill || o.m != m;
}

/// The living pill (Gemini): moving lights lit from below inside a dark pill - blue and violet, a warm touch when he
/// speaks - brighter and taller with the voice; dim when muted.
class CallPillPainter extends CustomPainter {
  CallPillPainter(this.m, this.c, {required this.muted}) : super(repaint: m);
  final CallMotion m;
  final HoolaColors c;
  final bool muted;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final base = c.dark ? Color.lerp(c.bg, c.info, .06)! : Color.lerp(c.sunk, c.info, .08)!;
    canvas.drawRect(Offset.zero & size, Paint()..color = base);
    final lv = muted ? 0.0 : m.level;
    final strength = (muted ? .18 : .55) + .6 * lv;
    final cols = [c.info, c.accent, Color.lerp(c.accent, c.bad, .6)!];
    final tt = m.reduced ? 0.0 : m.t;
    for (var i = 0; i < 3; i++) {
      final x = w * (.5 + .38 * math.sin(tt * (.9 + i * .3) + i * 2));
      final y = h * (.95 - .2 * lv);
      final r = h * (.75 + .5 * lv) * (i == 2 ? .55 + .5 * m.mix : 1);
      final op = i == 2 ? strength * .7 * m.mix : strength * (i == 1 ? .5 + .5 * m.mix : 1 - .4 * m.mix);
      canvas.drawCircle(
        Offset(x, y),
        r,
        Paint()
          ..shader = RadialGradient(colors: [cols[i].withOpacity(op.clamp(0.0, 1.0)), cols[i].withOpacity(0)])
              .createShader(Rect.fromCircle(center: Offset(x, y), radius: r)),
      );
    }
    // the dark top edge, the pill lit only from below
    canvas.drawRect(
      Rect.fromLTWH(0, 0, w, h * .6),
      Paint()
        ..shader = LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [base.withOpacity(.92), base.withOpacity(0)])
            .createShader(Rect.fromLTWH(0, 0, w, h * .6)),
    );
  }

  @override
  bool shouldRepaint(covariant CallPillPainter o) => o.c != c || o.muted != muted || o.m != m;
}
