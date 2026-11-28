import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'hoola_mark.dart';
import 'hoola_theme.dart';

/// First run: log in or sign up the way Claude and ChatGPT do it (v0.999.178 LOGIN, PREMIUM - the design the owner
/// picked): Continue with Google, or your email and a 6-digit code (no password), then - for a new person - "What
/// should Hoola call you?". The language sits top right; an API key stays under "More ways to sign in".
class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key, required this.app, this.onDone});
  final Santosh app;
  final VoidCallback? onDone;
  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  late final _key = TextEditingController(text: widget.app.apiKey);
  final _email = TextEditingController();
  final _code = TextEditingController();
  final _name = TextEditingController();
  final _codeFocus = FocusNode();
  late String _lang = widget.app.language;
  int _step = 0; // 0 = Google or email, 1 = the code, 2 = your name
  bool _busy = false;
  bool _emailOpen = false;
  bool _advanced = false;
  String? _err;
  int _wait = 0;
  Timer? _timer;

  Api get _open => Api(widget.app.serverUrl, '');
  String get _addr => _email.text.trim().toLowerCase();

  @override
  void dispose() {
    _timer?.cancel();
    _codeFocus.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() fn) async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      await fn();
    } catch (e) {
      if (mounted) setState(() => _err = e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _countdown() {
    _timer?.cancel();
    setState(() => _wait = 30);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted || _wait <= 1) {
        t.cancel();
        if (mounted) setState(() => _wait = 0);
        return;
      }
      setState(() => _wait--);
    });
  }

  Future<void> _google() => _run(() async {
        final h = await _open.health();
        if (h['google_login'] != true) throw 'Google sign-in is not switched on for this server yet. Use your email.';
        await widget.app.saveSettings(lang: _lang);
        // Google asks only for name + email; the app comes back through the santosh:// link with a one-time code
        await launchUrl(_open.googleSignInUrl(), mode: LaunchMode.externalApplication);
      });

  Future<void> _sendCode() => _run(() async {
        if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(_addr)) throw 'Enter a correct email address.';
        await _open.emailStart(_addr);
        _code.clear();
        if (!mounted) return;
        setState(() => _step = 1);
        _countdown();
        _codeFocus.requestFocus();
      });

  Future<void> _checkCode() => _run(() async {
        final c = _code.text.replaceAll(RegExp(r'\D'), '');
        if (c.length != 6) throw 'Type the 6-digit code from the email.';
        final r = await _open.emailVerify(_addr, c);
        await widget.app.saveSettings(lang: _lang);
        await widget.app.applySession('${r['session_token']}');
        if (!widget.app.connected) throw widget.app.error ?? 'Could not connect';
        if (r['needs_name'] == true) {
          if (mounted) setState(() => _step = 2);
          return;
        }
        widget.onDone?.call();
      });

  Future<void> _saveName() => _run(() async {
        final n = _name.text.trim();
        if (n.isEmpty) throw 'Type your name.';
        await widget.app.api!.emailName(n);
        try {
          await widget.app.api!.saveProfile({'name': n, 'language': languages[_lang]});
        } catch (_) {}
        widget.onDone?.call();
      });

  Future<void> _go() => _run(() async {
        final url = widget.app.serverUrl;
        if (_key.text.trim().isEmpty) throw 'Add API key';
        final h = await Api(url, _key.text.trim()).health();
        if (h['ok'] != true) throw 'Hoola is not answering right now';
        await widget.app.saveSettings(key: _key.text, lang: _lang);
        await widget.app.connect(fresh: true);
        if (!widget.app.connected) throw widget.app.error ?? 'Could not connect';
        widget.onDone?.call();
      });

  Future<void> _pickLanguage(HoolaColors c) async {
    final pick = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: c.surface,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: ListView(shrinkWrap: true, padding: const EdgeInsets.only(bottom: 12), children: [
          for (final e in languages.entries)
            ListTile(
              title: Text(e.value, style: TextStyle(fontFamily: HoolaFont.sans, fontSize: 16, color: c.ink)),
              trailing: _lang == e.key ? Icon(Icons.check_rounded, color: c.ink) : null,
              onTap: () => Navigator.pop(ctx, e.key),
            ),
        ]),
      ),
    );
    if (pick != null && mounted) setState(() => _lang = pick);
  }

  // ---------------------------------------------------------------- parts
  TextStyle _sans(HoolaColors c, double size, {FontWeight w = FontWeight.w400, Color? color}) =>
      TextStyle(fontFamily: HoolaFont.sans, fontSize: size, fontWeight: w, color: color ?? c.ink, height: 1.5);

  Text _title(HoolaColors c, String t) => Text(t,
      style: HoolaType.hero(c));

  Widget _primary(HoolaColors c, String label, VoidCallback onTap, {IconData? icon}) => SizedBox(
        height: 52,
        child: FilledButton(
          onPressed: _busy ? null : onTap,
          style: FilledButton.styleFrom(
            backgroundColor: c.pill,
            foregroundColor: c.onPill,
            disabledBackgroundColor: c.pill.withOpacity(0.5),
            disabledForegroundColor: c.onPill,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            textStyle: _sans(c, 16, w: FontWeight.w600),
          ),
          child: _busy
              ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
              : Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  if (icon != null) ...[Icon(icon, size: 19), const SizedBox(width: 10)],
                  Text(label),
                ]),
        ),
      );

  Widget _outline(HoolaColors c, Widget lead, String label, VoidCallback onTap) => SizedBox(
        height: 52,
        child: OutlinedButton(
          onPressed: _busy ? null : onTap,
          style: OutlinedButton.styleFrom(
            backgroundColor: c.surface,
            foregroundColor: c.ink,
            side: BorderSide(color: c.lineStrong),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            textStyle: _sans(c, 16, w: FontWeight.w500),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [lead, const SizedBox(width: 10), Text(label)]),
        ),
      );

  Widget _link(HoolaColors c, String label, VoidCallback? onTap, {bool strong = false}) => TextButton(
        onPressed: _busy ? null : onTap,
        style: TextButton.styleFrom(minimumSize: const Size(44, 44), foregroundColor: strong ? c.accent : c.ink2),
        child: Text(label, style: _sans(c, 14, w: strong ? FontWeight.w600 : FontWeight.w500, color: onTap == null ? c.ink3 : null)),
      );

  InputDecoration _field(HoolaColors c, String label, {String? hint}) => InputDecoration(
        labelText: label,
        hintText: hint,
        filled: true,
        fillColor: c.surface,
        labelStyle: _sans(c, 15, color: c.ink2),
        hintStyle: _sans(c, 15, color: c.ink3),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.lineStrong)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: c.ink, width: 2)),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      );

  // ---------------------------------------------------------------- the three steps
  Widget _welcome(HoolaColors c) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Align(
          alignment: Alignment.centerRight,
          child: OutlinedButton.icon(
            onPressed: () => _pickLanguage(c),
            icon: Icon(Icons.language_rounded, size: 17, color: c.ink2),
            label: Text(languages[_lang] ?? 'English', style: _sans(c, 14, color: c.ink2)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(44, 40),
              side: BorderSide(color: c.lineStrong),
              shape: const StadiumBorder(),
            ),
          ),
        ),
        const Spacer(),
        const Align(alignment: Alignment.centerLeft, child: HoolaMark(size: 56, animate: false)),
        const SizedBox(height: 24),
        _title(c, 'Your Hoola,\nready when you are.'),
        const SizedBox(height: 12),
        Text('Bills, mail, reminders and calls — handled, and nothing goes out until you say yes.',
            style: _sans(c, 16, color: c.ink2)),
        const Spacer(),
        _outline(c, const _GoogleG(), 'Continue with Google', _google),
        const SizedBox(height: 12),
        if (!_emailOpen)
          _primary(c, 'Continue with email', () => setState(() => _emailOpen = true), icon: Icons.mail_outline_rounded)
        else ...[
          TextField(
            controller: _email,
            autofocus: true,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            autocorrect: false,
            textInputAction: TextInputAction.go,
            onSubmitted: (_) => _sendCode(),
            style: _sans(c, 16),
            cursorColor: c.ink,
            decoration: _field(c, 'Email address', hint: 'you@company.com'),
          ),
          const SizedBox(height: 12),
          _primary(c, 'Send me a code', _sendCode),
        ],
        Center(child: _link(c, _advanced ? 'Hide' : 'More ways to sign in', () => setState(() => _advanced = !_advanced))),
        if (_advanced) ...[
          TextField(controller: _key, obscureText: true, style: _sans(c, 16), decoration: _field(c, 'API key')),
          const SizedBox(height: 10),
          _outline(c, Icon(Icons.key_rounded, size: 18, color: c.ink2), 'Connect with API key', _go),
          const SizedBox(height: 8),
        ],
        Text('By continuing you agree to Hoola\'s Terms and Privacy Policy.',
            textAlign: TextAlign.center, style: _sans(c, 12.5, color: c.ink3)),
      ]);

  Widget _codeStep(HoolaColors c) {
    final gmail = RegExp(r'@(gmail|googlemail)\.com$').hasMatch(_addr);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Align(
        alignment: Alignment.centerLeft,
        child: IconButton(
          tooltip: 'Use a different email',
          onPressed: _busy ? null : () => setState(() {
                _step = 0;
                _err = null;
              }),
          icon: Icon(Icons.chevron_left_rounded, size: 28, color: c.ink),
        ),
      ),
      const SizedBox(height: 12),
      _title(c, 'Check your email'),
      const SizedBox(height: 10),
      Text.rich(TextSpan(style: _sans(c, 16, color: c.ink2), children: [
        const TextSpan(text: 'We sent a 6-digit code to '),
        TextSpan(text: _addr, style: _sans(c, 16, w: FontWeight.w600)),
        const TextSpan(text: '. It works for 10 minutes.'),
      ])),
      const SizedBox(height: 28),
      _CodeBoxes(controller: _code, focus: _codeFocus, colors: c, onFull: () {
        if (!_busy) _checkCode();
      }),
      const SizedBox(height: 20),
      if (gmail) ...[
        _outline(c, Icon(Icons.mail_outline_rounded, size: 19, color: c.ink), 'Open Gmail',
            () => launchUrl(Uri.parse('https://mail.google.com/'), mode: LaunchMode.externalApplication)),
        const SizedBox(height: 10),
      ],
      _primary(c, 'Continue', _checkCode),
      const Spacer(),
      Text('Didn\'t get it? Check spam, or', textAlign: TextAlign.center, style: _sans(c, 14, color: c.ink2)),
      Wrap(alignment: WrapAlignment.center, children: [
        _link(c, _wait > 0 ? 'Send a new code in 0:${_wait.toString().padLeft(2, '0')}' : 'Send a new code',
            _wait > 0 ? null : _sendCode, strong: true),
        _link(c, 'Use a different email', () => setState(() {
              _step = 0;
              _err = null;
            })),
      ]),
    ]);
  }

  Widget _nameStep(HoolaColors c) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        SizedBox(
          height: 44,
          child: Row(children: [
            for (final on in const [false, false, true]) ...[
              Container(width: 22, height: 4, decoration: BoxDecoration(color: on ? c.accent : c.ink, borderRadius: BorderRadius.circular(2))),
              const SizedBox(width: 8),
            ],
            const SizedBox(width: 6),
            Text('Last step', style: _sans(c, 13, color: c.ink3)),
          ]),
        ),
        const SizedBox(height: 12),
        _title(c, 'What should Hoola call you?'),
        const SizedBox(height: 10),
        Text('Your name the way you like to hear it. You can change it any time.', style: _sans(c, 16, color: c.ink2)),
        const SizedBox(height: 28),
        TextField(
          controller: _name,
          autofocus: true,
          autofillHints: const [AutofillHints.name],
          textCapitalization: TextCapitalization.words,
          onChanged: (_) => setState(() {}),
          onSubmitted: (_) => _saveName(),
          style: _sans(c, 17),
          cursorColor: c.ink,
          decoration: _field(c, 'Your name'),
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: c.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: c.line)),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const HoolaMark(size: 30, animate: false),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                '“Good to meet you${_name.text.trim().isEmpty ? '' : ', ${_name.text.trim().split(RegExp(r'\s+')).first}'}. '
                'What shall we get done first?”',
                style: TextStyle(fontFamily: HoolaFont.serif, fontSize: 16, height: 1.5, color: c.ink),
              ),
            ),
          ]),
        ),
        const Spacer(),
        _primary(c, 'Start using Hoola', _saveName),
      ]);

  @override
  Widget build(BuildContext context) {
    final gw = widget.app.takeGoogleWelcome();   // GOOGLE SIGN UP: new with Google -> the name step, her name filled
    if (gw != null) {
      _step = 2;
      _name.text = gw;
    }
    final b = MediaQuery.platformBrightnessOf(context);
    final c = b == Brightness.dark ? HoolaColors.darkSet : HoolaColors.light;
    return Theme(
      data: hoolaTheme(b),
      child: Scaffold(
        backgroundColor: c.bg,
        body: SafeArea(
          child: LayoutBuilder(
            builder: (ctx, box) => SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: box.maxHeight - 36),
                child: IntrinsicHeight(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Expanded(child: _step == 0 ? _welcome(c) : _step == 1 ? _codeStep(c) : _nameStep(c)),
                    if (_err != null) ...[
                      const SizedBox(height: 12),
                      Text(_err!, textAlign: TextAlign.center, style: _sans(c, 13.5, color: c.bad)),
                    ],
                  ]),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Six boxes over one hidden field: paste or the phone's code autofill fills all six at once.
class _CodeBoxes extends StatelessWidget {
  const _CodeBoxes({required this.controller, required this.focus, required this.colors, required this.onFull});
  final TextEditingController controller;
  final FocusNode focus;
  final HoolaColors colors;
  final VoidCallback onFull;

  @override
  Widget build(BuildContext context) {
    final c = colors;
    return SizedBox(
      height: 60,
      child: Stack(children: [
        ValueListenableBuilder<TextEditingValue>(
          valueListenable: controller,
          builder: (_, v, __) {
            final digits = v.text.replaceAll(RegExp(r'\D'), '');
            final at = digits.length.clamp(0, 5);
            return Row(children: [
              for (var i = 0; i < 6; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: c.surface,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: i == at ? c.ink : (i < digits.length ? c.ink3 : c.lineStrong),
                        width: i == at ? 2 : 1,
                      ),
                    ),
                    child: Text(i < digits.length ? digits[i] : '',
                        style: TextStyle(fontFamily: HoolaFont.sans, fontSize: 26, fontWeight: FontWeight.w600, color: c.ink,
                            fontFeatures: const [FontFeature.tabularFigures()])),
                  ),
                ),
              ],
            ]);
          },
        ),
        Positioned.fill(
          child: Opacity(
            opacity: 0.01,
            child: Semantics(
              label: '6-digit code',
              child: TextField(
                controller: controller,
                focusNode: focus,
                autofocus: true,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                maxLength: 6,
                showCursor: false,
                enableInteractiveSelection: false,
                decoration: const InputDecoration(counterText: '', border: InputBorder.none, enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none, filled: false),
                onChanged: (t) {
                  final d = t.replaceAll(RegExp(r'\D'), '');
                  if (d != t) {
                    controller.value = TextEditingValue(text: d, selection: TextSelection.collapsed(offset: d.length));
                  }
                  if (d.length == 6) onFull();
                },
              ),
            ),
          ),
        ),
      ]),
    );
  }
}

/// Google's "G", drawn in its four colours.
class _GoogleG extends StatelessWidget {
  const _GoogleG();
  @override
  Widget build(BuildContext context) => const SizedBox(width: 19, height: 19, child: CustomPaint(painter: _GPainter()));
}

class _GPainter extends CustomPainter {
  const _GPainter();
  @override
  void paint(Canvas canvas, Size size) {
    final r = Rect.fromLTWH(size.width * .12, size.height * .12, size.width * .76, size.height * .76);
    final p = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * .19;
    const tau = 6.283185307;
    void arc(Color col, double start, double sweep) => canvas.drawArc(r, start * tau, sweep * tau, false, p..color = col);
    arc(const Color(0xFFEA4335), .60, .17); // red, top
    arc(const Color(0xFFFBBC05), .44, .16); // yellow, left
    arc(const Color(0xFF34A853), .19, .25); // green, bottom
    arc(const Color(0xFF4285F4), .0, .19); // blue, right
    canvas.drawRect(Rect.fromLTWH(size.width * .5, size.height * .405, size.width * .38, size.height * .19),
        Paint()..color = const Color(0xFF4285F4));
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
