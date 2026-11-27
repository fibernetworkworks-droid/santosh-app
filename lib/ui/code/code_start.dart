// v0.924 HOOLA CODE FIRST SCREEN (owner, on her Claude Code screenshot: "WE WANT SAME ... FOR HOOLA CODE WHEN ITS OWN
// HOOLA CODE CHAT SESSION ... AND BAR" -> design canvas claude.ai/artifact/Au9zBc5gmkVsNLwVc41rCM -> "GO"):
//   * CodeNewSessionPage = the New session screen: back + "New session", the Hoola mark and "What should we build today?",
//     two chips (the environment, the repository + branch), one pill bar;
//   * CodeBar = that pill bar, also used inside every session: +, the field, the mic (tap = dictate, hold = talk,
//     slide left to cancel, let go to send), the round send (grey until there are words) or Stop while Hoola works.
// Same routes as before: GET /api/devsahayak, GET /api/devsahayak/envs, GET /api/devsahayak/branches,
// POST /api/devsahayak/tasks/start (now with env). Nothing starts until she taps send.
import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../../state.dart';
import '../hoola_mark.dart';
import '../hoola_theme.dart';
import '../shell/hoola_credits.dart' show HoolaCreditsPage, hoolaCountry;
import '../shell/hoola_quality.dart' show hoolaTierLoad, hoolaTierName, hoolaTierNow, showHoolaTierSheet;
import '../shell/hoola_settings.dart' show hoolaOpenNew;
import '../shell/hoola_tool_icons.dart' show svgPath;
import 'code_env.dart';
import 'code_home.dart';
import 'code_kit.dart';
import 'code_more.dart';

// ---------------------------------------------------------------------------------------------- small drawings
const _gitHubPath = 'M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49'
    '-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 '
    '2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 '
    '2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 '
    '2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8'
    'c0-4.42-3.58-8-8-8z';
Path? _gitHub;

/// The GitHub mark (it names GitHub, like the platform's own buttons do), drawn in the text colour.
class CodeGitHubIcon extends StatelessWidget {
  const CodeGitHubIcon({super.key, this.size = 17, this.color});
  final double size;
  final Color? color;
  @override
  Widget build(BuildContext context) =>
      CustomPaint(size: Size.square(size), painter: _GitHubPainter(color ?? HoolaColors.of(context).ink));
}

class _GitHubPainter extends CustomPainter {
  _GitHubPainter(this.color);
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final p = _gitHub ??= svgPath(_gitHubPath);
    canvas.save();
    canvas.scale(size.width / 16, size.height / 16);
    canvas.drawPath(p, Paint()..color = color);
    canvas.restore();
  }

  @override
  bool shouldRepaint(_GitHubPainter old) => old.color != color;
}

/// A chip above the bar: 36 high, white, a hairline; [picked] = the violet tint once something is chosen.
class CodeBarChip extends StatelessWidget {
  const CodeBarChip({super.key, required this.icon, required this.label, this.sub = '', this.picked = false, this.chevron = true, this.onTap, this.semantics});
  final Widget icon;
  final String label, sub;
  final bool picked, chevron;
  final VoidCallback? onTap;
  final String? semantics;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: semantics ?? (sub.isEmpty ? label : '$label $sub'),
      excludeSemantics: true,
      child: Material(
        color: picked ? c.accentSoft : c.surface,
        shape: StadiumBorder(side: BorderSide(color: picked ? c.accent.withOpacity(.3) : c.line)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: Container(
            height: 36,
            padding: const EdgeInsets.fromLTRB(10, 0, 11, 0),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              icon,
              const SizedBox(width: 7),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 170),
                child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 14, weight: FontWeight.w500, height: 1.2)),
              ),
              if (sub.isNotEmpty) ...[
                const SizedBox(width: 5),
                Text('· $sub', maxLines: 1, style: codeSans(c, size: 14, color: c.ink2, height: 1.2)),
              ],
              if (chevron) ...[
                const SizedBox(width: 4),
                Icon(Icons.keyboard_arrow_down_rounded, size: 17, color: c.ink3),
              ],
            ]),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------------------------- the bar
/// The one pill bar of Hoola Code: on the New session screen and inside every session.
class CodeBar extends StatefulWidget {
  const CodeBar({
    super.key,
    required this.app,
    required this.controller,
    required this.hint,
    this.focus,
    this.onPlus,
    this.plusLabel = 'Add files, photos or a mode',
    this.onSend,
    this.sendLabel = 'Send',
    this.onStop,
    this.stopLabel = 'Stop',
    this.busy = false,
    this.canSendEmpty = false,
    this.onListening,
    this.maxLength = 20000,
    this.top,
  });
  final Santosh app;
  final TextEditingController controller;
  final String hint;
  final FocusNode? focus;
  final VoidCallback? onPlus;
  final String plusLabel;
  final VoidCallback? onSend;
  final String sendLabel;
  /// While Hoola works: the round button is Stop when the field is empty.
  final VoidCallback? onStop;
  final String stopLabel;
  final bool busy;
  /// Send is live with an empty field (a plan's "Yes, start", comments on lines).
  final bool canSendEmpty;
  final ValueChanged<bool>? onListening;
  final int maxLength;
  /// v0.936 a line inside the bar above the field (Hoola's suggested next message as a chip, like Claude Code).
  final Widget? top;
  @override
  State<CodeBar> createState() => _CodeBarState();
}

class _CodeBarState extends State<CodeBar> with SingleTickerProviderStateMixin {
  final _stt = SpeechToText();
  late final AnimationController _wave = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100));
  bool _listening = false, _hold = false, _cancel = false, _pressing = false;
  String _before = '';
  DateTime _from = DateTime.now();
  Timer? _tick;
  double _level = .3;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_redraw);
  }

  @override
  void didUpdateWidget(CodeBar old) {
    super.didUpdateWidget(old);
    if (old.controller != widget.controller) {
      old.controller.removeListener(_redraw);
      widget.controller.addListener(_redraw);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_redraw);
    _tick?.cancel();
    _wave.dispose();
    if (_listening) _stt.stop();
    super.dispose();
  }

  void _redraw() {
    if (mounted) setState(() {});
  }

  void _set(bool on) {
    _listening = on;
    widget.onListening?.call(on);
    _tick?.cancel();
    if (on) {
      _from = DateTime.now();
      _tick = Timer.periodic(const Duration(seconds: 1), (_) => _redraw());
      if (!HoolaMotion.reduced(context)) _wave.repeat();
    } else {
      _wave.stop();
    }
  }

  Future<void> _start({required bool hold}) async {
    if (_listening) return;
    final ok = await _stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted && _listening && !_hold) setState(() => _set(false));
    });
    if (!mounted) return;
    if (hold && !_pressing) return;   // she let go before the microphone was ready
    if (!ok) {
      codeToast(context, 'Hoola needs the microphone to hear you. Allow it in your phone settings.');
      return;
    }
    _before = widget.controller.text.trim();
    setState(() {
      _hold = hold;
      _cancel = false;
      _level = .3;
      _set(true);
    });
    await _stt.listen(
      localeId: widget.app.language.replaceAll('-', '_'),
      listenFor: const Duration(minutes: 2),
      pauseFor: Duration(seconds: hold ? 60 : 4),
      partialResults: true,
      onSoundLevelChange: (l) {
        if (mounted) setState(() => _level = ((l + 2) / 12).clamp(.12, 1.0));
      },
      onResult: (r) {
        if (!mounted || _cancel) return;
        final t = _before.isEmpty ? r.recognizedWords : '$_before ${r.recognizedWords}';
        widget.controller.text = t;
        widget.controller.selection = TextSelection.collapsed(offset: t.length);
      },
    );
  }

  Future<void> _end({required bool send}) async {
    if (!_listening) return;
    await _stt.stop();
    await Future<void>.delayed(const Duration(milliseconds: 250));   // the last words land after stop
    if (!mounted) return;
    final cancel = _cancel;
    setState(() {
      _set(false);
      _hold = false;
      _cancel = false;
    });
    if (cancel) {
      widget.controller.text = _before;
      widget.controller.selection = TextSelection.collapsed(offset: _before.length);
      return;
    }
    if (send && widget.controller.text.trim().isNotEmpty && widget.onSend != null && !widget.busy) widget.onSend!();
  }

  Widget _round({required Key key, required String label, required Widget child, required Color fill, VoidCallback? onTap, double size = 40}) => Semantics(
        key: key,
        button: true,
        label: label,
        enabled: onTap != null,
        excludeSemantics: true,
        child: InkResponse(
          onTap: onTap,
          radius: 24,
          child: SizedBox(
            width: math.max(48, size),
            height: math.max(48, size),
            child: Center(
              child: AnimatedContainer(
                duration: HoolaMotion.of(context, HoolaMotion.fade),
                width: size,
                height: size,
                decoration: BoxDecoration(color: fill, shape: BoxShape.circle),
                child: Center(child: child),
              ),
            ),
          ),
        ),
      );

  /// The bar's row, with her suggested next message above it when there is one (never while listening).
  Widget _withTop(Widget row) {
    final top = widget.top;
    if (top == null || _listening) return row;
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Padding(padding: const EdgeInsets.fromLTRB(8, 6, 8, 4), child: Align(alignment: Alignment.centerLeft, child: top)),
      row,
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final hasWords = widget.controller.text.trim().isNotEmpty;
    final live = hasWords || widget.canSendEmpty;
    final stop = widget.onStop != null && !hasWords && !widget.canSendEmpty;
    final secs = DateTime.now().difference(_from).inSeconds;
    final reduced = HoolaMotion.reduced(context);

    final mic = GestureDetector(
      key: const ValueKey('mic'),
      onTap: () => _listening ? _end(send: false) : _start(hold: false),
      onLongPressStart: (_) {
        _pressing = true;
        _start(hold: true);
      },
      onLongPressMoveUpdate: (d) {
        final out = d.offsetFromOrigin.dx < -70;
        if (out != _cancel && _listening) setState(() => _cancel = out);
      },
      onLongPressEnd: (_) {
        _pressing = false;
        _end(send: _hold);
      },
      child: Semantics(
        button: true,
        label: _listening ? 'Stop listening' : 'Hold to talk, or tap to speak',
        excludeSemantics: true,
        child: SizedBox(
          width: _listening ? 56 : 48,
          height: _listening ? 56 : 48,
          child: Stack(alignment: Alignment.center, children: [
            if (_listening && !reduced)
              AnimatedBuilder(
                animation: _wave,
                builder: (_, __) => Container(
                  width: 48 + 14 * _wave.value,
                  height: 48 + 14 * _wave.value,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: c.accent.withOpacity(.28 * (1 - _wave.value))),
                ),
              ),
            Container(
              width: _listening ? 48 : 40,
              height: _listening ? 48 : 40,
              decoration: BoxDecoration(shape: BoxShape.circle, color: _listening ? (_cancel ? c.bad : c.accent) : Colors.transparent),
              child: Icon(_cancel && _listening ? Icons.close_rounded : Icons.mic_none_rounded,
                  size: _listening ? 23 : 22, color: _listening ? c.onAccent : c.ink2),
            ),
          ]),
        ),
      ),
    );

    final bar = AnimatedContainer(
      duration: HoolaMotion.of(context, HoolaMotion.fade),
      padding: EdgeInsets.fromLTRB(_listening ? 16 : 4, 4, 4, 4),
      decoration: BoxDecoration(
        color: _listening ? c.accentSoft : c.surface,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: _listening ? c.accent.withOpacity(.3) : c.line),
        boxShadow: c.dark || _listening
            ? null
            : [BoxShadow(color: c.shadow.withOpacity(.14), blurRadius: 24, spreadRadius: -14, offset: const Offset(0, 8))],
      ),
      child: _withTop(Row(crossAxisAlignment: _listening ? CrossAxisAlignment.center : CrossAxisAlignment.end, children: [
        if (_listening) ...[
          Container(key: const ValueKey('dot'), width: 8, height: 8, decoration: BoxDecoration(color: _cancel ? c.bad : c.accent, shape: BoxShape.circle)),
          const SizedBox(width: 10),
          Text(codeClock(secs), key: const ValueKey('clock'), style: codeMono(c, size: 14, color: c.accent)),
          const SizedBox(width: 12),
          Expanded(
            key: const ValueKey('wave'),
            child: SizedBox(
              height: 30,
              child: _cancel
                  ? Align(alignment: Alignment.centerLeft, child: Text('Let go to cancel', style: codeSans(c, size: 14, color: c.bad)))
                  : ExcludeSemantics(
                      child: AnimatedBuilder(
                        animation: _wave,
                        builder: (_, __) => CustomPaint(painter: _WavePainter(c.accent, _level, reduced ? .25 : _wave.value)),
                      ),
                    ),
            ),
          ),
          const SizedBox(width: 8),
        ] else ...[
          if (widget.onPlus != null)
            _round(
                key: const ValueKey('plus'),
                label: widget.plusLabel,
                fill: c.sunk,
                onTap: widget.onPlus,
                child: Icon(Icons.add_rounded, size: 21, color: c.ink)),
          Expanded(
            key: const ValueKey('field'),
            child: Padding(
              padding: EdgeInsets.only(left: widget.onPlus == null ? 14 : 6, right: 2),
              child: TextField(
                controller: widget.controller,
                focusNode: widget.focus,
                minLines: 1,
                maxLines: 6,
                maxLength: widget.maxLength,
                textInputAction: TextInputAction.newline,
                style: codeSans(c, size: 16, height: 1.45),
                textAlignVertical: TextAlignVertical.center,
                cursorColor: c.accent,
                decoration: codeBareInput(c, hint: widget.hint),
              ),
            ),
          ),
        ],
        mic,
        if (!_listening)
          stop
              ? _round(
                  key: const ValueKey('send'),
                  label: widget.stopLabel,
                  fill: c.pill,
                  onTap: widget.busy ? null : widget.onStop,
                  child: Container(width: 12, height: 12, decoration: BoxDecoration(color: c.onPill, borderRadius: BorderRadius.circular(3))))
              : _round(
                  key: const ValueKey('send'),
                  label: live ? widget.sendLabel : '${widget.sendLabel} (type something first)',
                  fill: live && widget.onSend != null ? c.pill : c.navOn,
                  onTap: live && !widget.busy ? widget.onSend : null,
                  child: widget.busy
                      ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                      : Icon(Icons.arrow_upward_rounded, size: 20, color: live && widget.onSend != null ? c.onPill : c.ink3)),
      ])),
    );

    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      bar,
      if (_listening)
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: _hold
              ? Row(children: [
                  Icon(Icons.chevron_left_rounded, size: 16, color: c.ink2),
                  Text('Slide left to cancel', style: codeSans(c, size: 13, color: c.ink2)),
                  const Spacer(),
                  Text('Let go to send', style: codeSans(c, size: 13, color: c.ink2)),
                ])
              : Text('Listening · tap the mic when you are done', textAlign: TextAlign.center, style: codeSans(c, size: 13, color: c.ink2)),
        ),
    ]);
  }
}

class _WavePainter extends CustomPainter {
  _WavePainter(this.color, this.level, this.t);
  final Color color;
  final double level, t;
  @override
  void paint(Canvas canvas, Size size) {
    const gap = 6.0;
    final n = (size.width / gap).floor().clamp(4, 40);
    final mid = size.height / 2;
    for (var i = 0; i < n; i++) {
      final wob = (math.sin((t * 2 * math.pi) + i * .72) + 1) / 2;
      final fade = i > n - 4 ? .45 : 1.0;
      final h = math.max(4.0, size.height * (.18 + .82 * level * (.35 + .65 * wob)));
      final x = i * gap + 1.5;
      final paint = Paint()
        ..color = color.withOpacity((i.isEven ? 1.0 : .62) * fade)
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(Offset(x, mid - h / 2), Offset(x, mid + h / 2), paint);
    }
  }

  @override
  bool shouldRepaint(_WavePainter old) => old.level != level || old.t != t || old.color != color;
}

// ---------------------------------------------------------------------------------------------- the first screen
/// Opens the New session screen. [onStarted] gets the new session's id once the screen has closed.
Future<void> showCodeNewSession(BuildContext context, Santosh app, {String prefill = '', required ValueChanged<String> onStarted}) async {
  final id = await codePush<String>(context, app, CodeNewSessionPage(app: app, prefill: prefill));
  if (id != null && id.isNotEmpty) onStarted(id);
}

class CodeNewSessionPage extends StatefulWidget {
  const CodeNewSessionPage({super.key, required this.app, this.prefill = ''});
  final Santosh app;
  final String prefill;
  @override
  State<CodeNewSessionPage> createState() => _CodeNewSessionPageState();
}

class _CodeNewSessionPageState extends State<CodeNewSessionPage> {
  final d = CodeDraft();
  Map<String, dynamic>? _ov;
  Map<String, dynamic> _envs = {};
  String _env = '';
  String? _error;
  bool _busy = false, _listening = false;

  Map<String, dynamic> get _st => cm(_ov?['settings']);
  List<Map<String, dynamic>> get _repoRows => [for (final r in cl(_ov?['repos'])) if (cs(r['repo']).isNotEmpty) r];
  List<String> get _repos => [for (final r in _repoRows) cs(r['repo'])];
  List<Map<String, dynamic>> get _envList => [for (final e in cl(_envs['envs'])) if (e['archived'] != true) e];

  String get repo {
    if (_repos.contains(d.repo)) return d.repo;
    final def = cs(_st['default_repo']);
    if (_repos.contains(def)) return def;
    return _repos.isEmpty ? '' : _repos.first;
  }

  String get mode => d.mode.isNotEmpty ? d.mode : (_st['ask_before_pr'] == true ? 'ask' : 'auto');

  String get _branch {
    if (d.base.isNotEmpty) return d.base;
    for (final r in _repoRows) {
      if (cs(r['repo']) == repo) return cs(r['default_branch']).isEmpty ? 'main' : cs(r['default_branch']);
    }
    return 'main';
  }

  String get _envName {
    if (_env.isEmpty || _env == 'auto') return 'Auto';
    for (final e in _envList) {
      if (cs(e['id']) == _env) return cs(e['name']);
    }
    return 'Auto';
  }

  @override
  void initState() {
    super.initState();
    if (widget.prefill.isNotEmpty) d.prefill(widget.prefill);
    _load();
  }

  @override
  void dispose() {
    d.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    try {
      final r = cm(await api.call('GET', '/api/devsahayak'));
      Map<String, dynamic> e = {};
      try {
        e = cm(await api.call('GET', '/api/devsahayak/envs'));
      } catch (_) {}   // an older server without environments: Auto only
      if (!mounted) return;
      _loadQuality();
      setState(() {
        _ov = r;
        _envs = e;
        _env = cs(e['pick']).isEmpty ? 'auto' : cs(e['pick']);
        _error = null;
      });
    } catch (x) {
      if (mounted) setState(() => _error = '$x'.replaceFirst('Exception: ', ''));
    }
  }

  // v0.999.27 THE BOTTOM ROW (owner: "DEPLOY SAME FOR PHONE HOOLA CODE ALSO" after the console's): her quality tier (the
  // chat's own five, the same choice everywhere) and her credits beside the repository - no model picker, no rupees.
  Map<String, dynamic>? _wallet;
  int _planCredits = 0;

  Future<void> _loadQuality() async {
    final api = widget.app.api;
    if (api == null) return;
    if (hoolaTierNow.value == null) hoolaTierLoad(widget.app);
    try {
      final v = await api.credits(hoolaCountry());
      final w = cm(v['wallet']);
      var plan = 0;
      for (final p in cl(cm(v['prices'])['plans'])) {
        if (cs(p['id']) == cs(w['plan'])) plan = (p['credits'] as num?)?.toInt() ?? 0;
      }
      if (mounted) setState(() { _wallet = w; _planCredits = plan; });
    } catch (_) {}   // an older server without credits: no credits chip
  }

  String get _creditsLabel {
    final w = _wallet!;
    String n(Object? v) => ((v as num?) ?? 0).round().toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
    return w['unlocked'] == true ? '${n(w['paid_left'])} credits' : '${n(w['free_left'])} free today';
  }

  Future<void> _openCredits() async {
    await hoolaOpenNew(context, widget.app, HoolaCreditsPage(app: widget.app));
    if (mounted) _loadQuality();
  }

  // ---- the sheets
  String _envLine(Map<String, dynamic> e) {
    final net = cm(e['net']);
    final hosts = ((net['hosts'] as List?) ?? const []).length;
    final words = switch (cs(net['level'])) {
      'none' => 'No network',
      'full' => 'Full network · any public site',
      _ => [
          'Limited',
          if (net['pkgs'] == true) 'package registries',
          if (hosts > 0) cPlural(hosts, 'allowed host'),
        ].join(' · '),
    };
    final vars = cm(e['env_vars']).length;
    return [words, if (vars > 0) cPlural(vars, 'variable'), if (cs(e['setup']).isNotEmpty) 'setup script'].join(' · ');
  }

  Future<void> _pickEnv() async {
    final c = HoolaColors.of(context);
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Environment',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Where Hoola runs your code in its own locked box, and what that box may reach.', style: codeSans(c, size: 14, color: c.ink2)),
              const SizedBox(height: 12),
              _envRow(ctx, 'auto', 'Auto', 'Follows each repo\'s own settings', Icons.auto_mode_rounded),
              for (final e in _envList)
                _envRow(ctx, cs(e['id']), cs(e['name']), _envLine(e),
                    switch (cs(cm(e['net'])['level'])) { 'none' => Icons.cloud_off_outlined, 'full' => Icons.public_rounded, _ => Icons.cloud_outlined }),
              if (_envList.length < ci(_envs['max'] ?? 12))
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: _envRow(ctx, '+new', 'New environment', 'Network, variables and a setup script', Icons.add_rounded, dashed: true),
                ),
              if (_envs.isNotEmpty && _envs['net_on'] != true)
                _small(c, Icons.info_outline_rounded, 'The network turns on once the server\'s network check passes. Until then commands run offline.'),
              _small(c, Icons.shield_outlined, 'Keys are added in Settings and never enter the box.'),
            ]));
    if (!mounted || pick == null) return;
    if (pick == '+new') {
      final saved = await codePush<Map<String, dynamic>>(context, widget.app, CodeEnvPage(app: widget.app, netOn: _envs['net_on'] == true));
      if (saved == null || !mounted) return;
      await _load();
      if (mounted && cs(saved['id']).isNotEmpty) setState(() => _env = cs(saved['id']));
      return;
    }
    setState(() => _env = pick);
  }

  Widget _small(HoolaColors c, IconData icon, String text) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 12, 4, 0),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 16, color: c.ink3),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: codeSans(c, size: 13, color: c.ink3))),
        ]),
      );

  Widget _envRow(BuildContext ctx, String id, String name, String line, IconData icon, {bool dashed = false}) {
    final c = HoolaColors.of(ctx);
    final on = !dashed && (id == _env || (id == 'auto' && (_env.isEmpty || _env == 'auto')));
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Semantics(
        button: true,
        selected: on,
        label: '$name, $line',
        excludeSemantics: true,
        child: Material(
          color: on ? c.accentSoft.withOpacity(.55) : c.surface,
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16), side: BorderSide(color: on ? c.accent.withOpacity(.3) : (dashed ? c.lineStrong : c.line))),
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => Navigator.pop(ctx, id),
            child: Container(
              constraints: const BoxConstraints(minHeight: 64),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(color: on ? c.accentSoft : c.sunk, shape: BoxShape.circle),
                  child: Icon(icon, size: 19, color: on ? c.accent : c.ink2),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(name, style: codeSans(c, size: 16, weight: on ? FontWeight.w600 : FontWeight.w500)),
                    if (line.isNotEmpty) Text(line, style: codeSans(c, size: 13, color: c.ink2)),
                  ]),
                ),
                if (on) Icon(Icons.check_rounded, size: 22, color: c.accent),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _pickRepo() async {
    final q = TextEditingController();
    String pickRepo = repo, pickBase = d.base;
    final done = await codeSheet<bool>(context, widget.app,
        title: 'Add repository',
        body: (ctx) => StatefulBuilder(builder: (ctx, set) {
              final c = HoolaColors.of(ctx);
              final w = q.text.trim().toLowerCase();
              final rows = [for (final r in _repoRows) if (w.isEmpty || cs(r['repo']).toLowerCase().contains(w)) r];
              String branchOf(String full) {
                if (full == pickRepo && pickBase.isNotEmpty) return pickBase;
                for (final r in _repoRows) {
                  if (cs(r['repo']) == full) return cs(r['default_branch']).isEmpty ? 'main' : cs(r['default_branch']);
                }
                return 'main';
              }

              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                if (_repoRows.length > 4)
                  Container(
                    height: 44,
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(22)),
                    child: Row(children: [
                      Icon(Icons.search_rounded, size: 19, color: c.ink3),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: q,
                          onChanged: (_) => set(() {}),
                          style: codeSans(c, size: 15),
                          cursorColor: c.accent,
                          decoration: codeBareInput(c, hint: 'Search your repositories', size: 15, minHeight: 44, padding: EdgeInsets.zero),
                        ),
                      ),
                    ]),
                  ),
                if (_repoRows.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text('No repository yet. Add the ones Hoola may work in.', style: codeSans(c, color: c.ink2)),
                  ),
                for (final r in rows) _repoRow(ctx, r, cs(r['repo']) == pickRepo, () => set(() {
                      if (pickRepo != cs(r['repo'])) pickBase = '';
                      pickRepo = cs(r['repo']);
                    })),
                if (pickRepo.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(4, 10, 4, 6),
                    child: Text('Branch to work from', style: codeSans(c, size: 12.5, weight: FontWeight.w600, color: c.ink3)),
                  ),
                  Material(
                    color: c.surface,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: c.line)),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () async {
                        final b = await _pickBranch(pickRepo, branchOf(pickRepo));
                        if (b != null) set(() => pickBase = b);
                      },
                      child: Container(
                        height: 52,
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        child: Row(children: [
                          Icon(Icons.call_split_rounded, size: 19, color: c.ink2),
                          const SizedBox(width: 10),
                          Expanded(child: Text(branchOf(pickRepo), style: codeMono(c, size: 14))),
                          Icon(Icons.keyboard_arrow_down_rounded, color: c.ink3),
                        ]),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                TextButton.icon(
                  style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48), foregroundColor: c.accent),
                  onPressed: () => Navigator.pop(ctx, false),
                  icon: const Icon(Icons.open_in_new_rounded, size: 18),
                  label: Text('Give Hoola more repositories', style: codeSans(c, size: 15, weight: FontWeight.w500, color: c.accent)),
                ),
                if (pickRepo.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  CodeMain('Use ${cRepoShort(pickRepo)}', onTap: () => Navigator.pop(ctx, true)),
                ],
              ]);
            }));
    q.dispose();
    if (!mounted) return;
    if (done == true) {
      setState(() {
        d.repo = pickRepo;
        d.base = pickBase;
      });
    } else if (done == false) {
      await codePush<void>(context, widget.app, CodeSettingsPage(app: widget.app));
      if (mounted) _load();
    }
  }

  Widget _repoRow(BuildContext ctx, Map<String, dynamic> r, bool on, VoidCallback onTap) {
    final c = HoolaColors.of(ctx);
    final full = cs(r['repo']);
    final owner = full.contains('/') ? full.split('/').first : '';
    final sub = [owner, r['private'] == true ? 'private' : 'public', cs(r['language'])].where((e) => e.isNotEmpty).join(' · ');
    return Semantics(
      button: true,
      selected: on,
      label: '${cRepoShort(full)}, $sub',
      excludeSemantics: true,
      child: Material(
        color: on ? c.accentSoft.withOpacity(.55) : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 60),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Row(children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                    color: c.surface, borderRadius: BorderRadius.circular(10), border: Border.all(color: on ? c.accent.withOpacity(.3) : c.line)),
                child: const Center(child: CodeGitHubIcon(size: 18)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(cRepoShort(full), maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 15, weight: on ? FontWeight.w600 : FontWeight.w500)),
                  Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeSans(c, size: 13, color: c.ink2)),
                ]),
              ),
              if (on) Icon(Icons.check_rounded, size: 22, color: c.accent),
            ]),
          ),
        ),
      ),
    );
  }

  Future<String?> _pickBranch(String full, String now) async {
    final r = await codeCall(context, widget.app, 'GET', '/api/devsahayak/branches', query: {'repo': full}, quiet: true);
    if (!mounted) return null;
    final list = [
      for (final b in ((r?['branches'] as List?) ?? const []))
        if (!cs(b is Map ? b['name'] : b).startsWith('hoola/')) cs(b is Map ? b['name'] : b)
    ];
    if (list.isEmpty) list.add(now);
    return codeSheet<String>(context, widget.app,
        title: 'Start from',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final b in list.take(40)) CodeChoiceRow(label: b, mono: true, on: b == now, onTap: () => Navigator.pop(ctx, b)),
            ]));
  }

  Future<void> _plus() async {
    final pick = await codeSheet<String>(context, widget.app,
        title: 'Add to the session',
        body: (ctx) {
          final c = HoolaColors.of(ctx);
          final modeLabel = codeModes.firstWhere((x) => x.$1 == mode, orElse: () => codeModes.first).$2;
          Widget row(String id, IconData icon, String label, String sub) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Material(
                  color: c.surface,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: c.line)),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () => Navigator.pop(ctx, id),
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 58),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      child: Row(children: [
                        Icon(icon, color: c.ink2),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(label, style: codeSans(c, weight: FontWeight.w500)),
                            Text(sub, style: codeSans(c, size: 13, color: c.ink2)),
                          ]),
                        ),
                        Icon(Icons.chevron_right_rounded, color: c.ink3),
                      ]),
                    ),
                  ),
                ),
              );
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            row('pic', Icons.photo_library_outlined, 'Pictures', 'A screenshot of the problem · up to 3'),
            row('doc', Icons.description_outlined, 'Text file', 'A log, an error, a spec · up to 3'),
            row('mode', Icons.fact_check_outlined, 'How it works: $modeLabel', 'Ask first, plan first, each step or on its own'),
          ]);
        });
    if (!mounted || pick == null) return;
    switch (pick) {
      case 'pic':
      case 'doc':
        await _attach(pick);
      case 'mode':
        await _pickMode();
    }
  }

  Future<void> _attach(String kind) async {
    try {
      if (kind == 'pic') {
        final xs = await ImagePicker().pickMultiImage(imageQuality: 85, maxWidth: 2400, maxHeight: 2400);
        for (final x in xs) {
          if (d.images.length >= 3) break;
          final b = await x.readAsBytes();
          if (b.length > 3000000) {
            if (mounted) codeToast(context, '${x.name} is bigger than 3 MB.');
            continue;
          }
          d.images.add((name: x.name, bytes: b));
        }
      } else {
        final res = await FilePicker.platform.pickFiles(withData: true, allowMultiple: true, type: FileType.any);
        for (final f in res?.files ?? const <PlatformFile>[]) {
          if (d.docs.length >= 3) break;
          final b = f.bytes;
          if (b == null) continue;
          final text = utf8.decode(b, allowMalformed: true);
          if (text.contains('\u0000')) {
            if (mounted) codeToast(context, '${f.name} is not a text file.');
            continue;
          }
          d.docs.add((name: f.name, text: text.length > 12000 ? text.substring(0, 12000) : text));
        }
      }
    } catch (e) {
      if (mounted) codeToast(context, 'It did not open: $e');
    }
    if (mounted) setState(() {});
  }

  Future<void> _pickMode() async {
    final pick = await codeSheet<String>(context, widget.app,
        title: 'How it works',
        body: (ctx) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (final (id, label, sub) in codeModes) CodeChoiceRow(label: label, sub: sub, on: id == mode, onTap: () => Navigator.pop(ctx, id)),
              Text('Nothing is ever merged without your tap.', style: codeSans(HoolaColors.of(ctx), size: 13, color: HoolaColors.of(ctx).ink3)),
            ]));
    if (pick != null && mounted) setState(() => d.mode = pick);
  }

  /// Slash words she can type at the start: /fix /tests /docs /explain /feature /plan.
  static const _slash = {'fix': 'fix', 'bug': 'fix', 'tests': 'tests', 'test': 'tests', 'docs': 'docs', 'explain': 'explain', 'feature': 'write', 'write': 'write'};

  Future<void> _start() async {
    var text = d.text.text.trim();
    var kind = 'auto';
    var m = mode;
    final sl = RegExp(r'^/([a-z]+)\b\s*').firstMatch(text);
    if (sl != null) {
      final w = sl.group(1)!;
      if (w == 'plan') {
        m = 'plan';
      } else if (_slash.containsKey(w)) {
        kind = _slash[w]!;
      }
      text = text.substring(sl.end).trim();
    }
    if (text.isEmpty) {
      codeToast(context, 'Describe the task, or paste the error.');
      return;
    }
    if (repo.isEmpty) {
      _pickRepo();
      return;
    }
    setState(() => _busy = true);
    final r = await codeCall(context, widget.app, 'POST', '/api/devsahayak/tasks/start', body: {
      'kind': kind,
      'text': text,
      'repo': repo,
      'base': d.base,
      'mode': m,
      'model': '',          // v0.999.27 her quality tier decides the model
      'effort': '',
      'env': _env.isEmpty ? 'auto' : _env,
      'images': [for (final i in d.images) {'name': i.name, 'data': base64Encode(i.bytes)}],
      'docs': [for (final x in d.docs) {'name': x.name, 'text': x.text}],
    });
    if (!mounted) return;
    setState(() => _busy = false);
    final id = cs(r?['id']);
    if (id.isNotEmpty) Navigator.of(context).pop(id);
  }

  // ---- the screen
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final ov = _ov;
    final words = d.text.text.trim();
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          SizedBox(
            height: 52,
            child: Row(children: [
              const SizedBox(width: 4),
              CodeIconButton(icon: Icons.arrow_back_rounded, label: 'Back', onTap: () => Navigator.of(context).maybePop()),
              Expanded(child: Text('New session', textAlign: TextAlign.center, style: codeSans(c, size: 17, weight: FontWeight.w600))),
              const SizedBox(width: 52),
            ]),
          ),
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(32, 8, 32, 24),
                child: ov == null
                    ? (_error == null
                        ? const CodeRing(size: 22)
                        : Column(mainAxisSize: MainAxisSize.min, children: [
                            Text(_error!, textAlign: TextAlign.center, style: codeSans(c, color: c.ink2)),
                            const SizedBox(height: 14),
                            CodeOutline('Try again', onTap: _load, icon: Icons.refresh_rounded),
                          ]))
                    : AnimatedSwitcher(
                        duration: HoolaMotion.of(context, HoolaMotion.fade),
                        child: _listening && words.isNotEmpty
                            ? Column(key: const ValueKey('words'), mainAxisSize: MainAxisSize.min, children: [
                                const HoolaMark(size: 44),
                                const SizedBox(height: 22),
                                Text(words, textAlign: TextAlign.center, style: HoolaType.hero(c).copyWith(fontSize: 24, height: 1.4)),
                                const SizedBox(height: 14),
                                Text('Your words appear as you speak', style: codeSans(c, size: 13, color: c.ink3)),
                              ])
                            : Column(key: const ValueKey('ready'), mainAxisSize: MainAxisSize.min, children: [
                                const HoolaMark(size: 58),
                                const SizedBox(height: 20),
                                Text('What should we build today?', textAlign: TextAlign.center, style: HoolaType.hero(c)),
                                if (_st['github'] != true) ...[
                                  const SizedBox(height: 18),
                                  CodeOutline('Connect GitHub first', icon: Icons.link_rounded, onTap: () async {
                                    await codePush<void>(context, widget.app, CodeSettingsPage(app: widget.app));
                                    if (mounted) _load();
                                  }),
                                ],
                              ]),
                      ),
              ),
            ),
          ),
          if (d.images.isNotEmpty || d.docs.isNotEmpty)
            SizedBox(
              height: 70,
              child: ListView(padding: const EdgeInsets.symmetric(horizontal: 16), scrollDirection: Axis.horizontal, children: [
                for (final (i, im) in d.images.indexed)
                  _thumb(c, Image.memory(im.bytes, width: 56, height: 56, fit: BoxFit.cover), () => setState(() => d.images.removeAt(i)), im.name),
                for (final (i, x) in d.docs.indexed) _docChip(c, x.name, () => setState(() => d.docs.removeAt(i))),
              ]),
            ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
            child: Row(children: [
              CodeBarChip(
                icon: Icon(_envName == 'Auto' ? Icons.auto_mode_rounded : Icons.cloud_outlined, size: 18, color: c.ink2),
                label: _envName,
                semantics: 'Environment: $_envName',
                onTap: ov == null ? null : _pickEnv,
              ),
              const SizedBox(width: 8),
              CodeBarChip(
                icon: const CodeGitHubIcon(size: 17),
                label: repo.isEmpty ? 'Add repository' : cRepoShort(repo),
                sub: repo.isEmpty ? '' : _branch,
                picked: d.repo.isNotEmpty,
                semantics: repo.isEmpty ? 'Add repository' : 'Repository ${cRepoShort(repo)}, branch $_branch',
                onTap: ov == null ? null : _pickRepo,
              ),
              ValueListenableBuilder<Map<String, dynamic>?>(
                valueListenable: hoolaTierNow,
                builder: (context, v, _) => v == null
                    ? const SizedBox.shrink()
                    : Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: CodeBarChip(
                          icon: Icon(Icons.auto_awesome_rounded, size: 17, color: c.ink2),
                          label: hoolaTierName(v),
                          semantics: 'Quality: ${hoolaTierName(v)}',
                          onTap: () => showHoolaTierSheet(context, widget.app),
                        ),
                      ),
              ),
              if (_wallet != null && _wallet!['on'] == true && _wallet!['exempt'] != true) ...[
                const SizedBox(width: 8),
                CodeBarChip(
                  icon: _CreditPie(frac: _wallet!['unlocked'] == true
                      ? (_planCredits > 0 ? (((_wallet!['plan_left'] as num?) ?? 0) / _planCredits) : 1.0)
                      : (((_wallet!['free_left'] as num?) ?? 0) / (((_wallet!['free_daily'] as num?) ?? 60).clamp(1, 1 << 30))),
                      color: c.ink2),
                  label: _creditsLabel,
                  chevron: false,
                  semantics: '$_creditsLabel. Open credits and plans',
                  onTap: _openCredits,
                ),
              ],
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
            child: CodeBar(
              app: widget.app,
              controller: d.text,
              hint: 'Type or hold to talk',
              onPlus: ov == null ? null : _plus,
              onSend: ov == null ? null : _start,
              sendLabel: 'Start session',
              busy: _busy,
              onListening: (on) {
                if (mounted) setState(() => _listening = on);
              },
            ),
          ),
        ]),
      ),
    );
  }

  Widget _thumb(HoolaColors c, Widget img, VoidCallback remove, String name) => Padding(
        padding: const EdgeInsets.fromLTRB(0, 8, 12, 4),
        child: Stack(clipBehavior: Clip.none, children: [
          ClipRRect(borderRadius: BorderRadius.circular(12), child: img),
          Positioned(
            top: -6,
            right: -6,
            child: Semantics(
              button: true,
              label: 'Remove $name',
              child: GestureDetector(
                onTap: remove,
                child: Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(color: c.pill, shape: BoxShape.circle, border: Border.all(color: c.bg, width: 2)),
                  child: Icon(Icons.close_rounded, size: 13, color: c.onPill),
                ),
              ),
            ),
          ),
        ]),
      );

  Widget _docChip(HoolaColors c, String name, VoidCallback remove) => Padding(
        padding: const EdgeInsets.fromLTRB(0, 8, 10, 4),
        child: Container(
          height: 56,
          padding: const EdgeInsets.only(left: 12),
          decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.line)),
          child: Row(children: [
            Icon(Icons.description_outlined, size: 18, color: c.ink2),
            const SizedBox(width: 8),
            ConstrainedBox(constraints: const BoxConstraints(maxWidth: 140), child: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: codeMono(c, size: 12))),
            CodeIconButton(icon: Icons.close_rounded, size: 16, label: 'Remove $name', onTap: remove),
          ]),
        ),
      );
}

/// v0.999.27 the credits pie: a ring with a filled slice for what is left (the chat's memory gauge shape).
class _CreditPie extends StatelessWidget {
  const _CreditPie({required this.frac, required this.color});
  final double frac;
  final Color color;
  @override
  Widget build(BuildContext context) => CustomPaint(size: const Size(17, 17), painter: _PiePainter(frac.clamp(0.0, 1.0).toDouble(), color));
}

class _PiePainter extends CustomPainter {
  _PiePainter(this.frac, this.color);
  final double frac;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final o = size.center(Offset.zero), r = size.width / 2 - 1;
    canvas.drawCircle(o, r, Paint()..style = PaintingStyle.stroke..strokeWidth = 1.4..color = color);
    final f = math.max(frac, 0.08);
    canvas.drawArc(Rect.fromCircle(center: o, radius: r - 2.6), -math.pi / 2, 2 * math.pi * f, true, Paint()..color = color);
  }

  @override
  bool shouldRepaint(_PiePainter old) => old.frac != frac || old.color != color;
}
