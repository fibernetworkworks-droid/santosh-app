import 'package:flutter/material.dart';

import '../api.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import '../emotion.dart';
import 'glass.dart';
import 'live_santosh.dart';

/// First run: say hello, pick a language, then log in or sign up the way Claude and ChatGPT do it - Continue with
/// Google, or your email and a 6-digit code (no password). A new person is then asked what to call them.
/// The server is fixed in the app; an API key stays under "More ways to sign in".
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
  late String _lang = widget.app.language;
  int _step = 0; // 0 = Google or email, 1 = the code, 2 = your name
  bool _busy = false;
  bool _advanced = false;
  String? _err;
  String _sent = '';

  Api get _open => Api(widget.app.serverUrl, '');

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

  Future<void> _google() => _run(() async {
        final h = await _open.health();
        if (h['google_login'] != true) throw 'Google sign-in is not switched on for this server yet. Use your email.';
        await widget.app.saveSettings(lang: _lang);
        // Google asks only for name + email; the app comes back through the santosh:// link with a one-time code
        await launchUrl(_open.googleSignInUrl(), mode: LaunchMode.externalApplication);
      });

  Future<void> _sendCode() => _run(() async {
        final e = _email.text.trim().toLowerCase();
        if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(e)) throw 'Enter a correct email address.';
        final r = await _open.emailStart(e);
        _sent = r['ok'] == true ? 'We sent a 6-digit code to $e. It works for 10 minutes.' : '${r['say'] ?? 'We sent a 6-digit code.'}';
        _code.clear();
        if (mounted) setState(() => _step = 1);
      });

  Future<void> _checkCode() => _run(() async {
        final c = _code.text.replaceAll(RegExp(r'\D'), '');
        if (c.length != 6) throw 'Type the 6-digit code from the email.';
        final r = await _open.emailVerify(_email.text.trim().toLowerCase(), c);
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

  Widget _primary(String label, VoidCallback? onTap) => GradientButton(
        label: _busy ? 'One moment…' : label, icon: Icons.arrow_forward_rounded, onTap: _busy ? null : onTap);

  Widget _link(String label, VoidCallback onTap) =>
      TextButton(onPressed: _busy ? null : onTap, child: Text(label, style: const TextStyle(color: C.muted)));

  List<Widget> _choose() => [
        Text('Log in or sign up', style: display(26)),
        const SizedBox(height: 6),
        const Text('Your AI companion. Use Google, or your email. New here? This makes your Hoola.',
            style: TextStyle(color: C.muted, fontSize: 14, height: 1.5)),
        const SizedBox(height: 16),
        const Text('YOUR LANGUAGE', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.2, color: C.muted)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final e in languages.entries)
            ChoiceChip(
              label: Text(e.value),
              selected: _lang == e.key,
              onSelected: (_) => setState(() => _lang = e.key),
              selectedColor: C.accent,
              labelStyle: TextStyle(color: _lang == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
              showCheckmark: false,
            ),
        ]),
        const SizedBox(height: 18),
        Press(
          onTap: _busy ? null : _google,
          child: Container(
            height: 54,
            decoration: BoxDecoration(color: C.ink, borderRadius: BorderRadius.circular(18)),
            child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text('G', style: TextStyle(color: Color(0xFF4285F4), fontWeight: FontWeight.w900, fontSize: 20)),
              SizedBox(width: 10),
              Text('Continue with Google', style: TextStyle(color: C.onAccent, fontWeight: FontWeight.w700, fontSize: 15.5)),
            ]),
          ),
        ),
        const SizedBox(height: 14),
        const Row(children: [
          Expanded(child: Divider(color: C.faint)),
          Padding(padding: EdgeInsets.symmetric(horizontal: 10), child: Text('or', style: TextStyle(color: C.muted, fontSize: 13))),
          Expanded(child: Divider(color: C.faint)),
        ]),
        const SizedBox(height: 10),
        TextField(
          controller: _email,
          keyboardType: TextInputType.emailAddress,
          autofillHints: const [AutofillHints.email],
          autocorrect: false,
          textInputAction: TextInputAction.go,
          onSubmitted: (_) => _sendCode(),
          decoration: const InputDecoration(labelText: 'Email'),
        ),
        const SizedBox(height: 12),
        _primary('Continue with email', _sendCode),
        const SizedBox(height: 4),
        Center(child: _link(_advanced ? 'Hide' : 'More ways to sign in', () => setState(() => _advanced = !_advanced))),
        if (_advanced) ...[
          TextField(controller: _key, obscureText: true, decoration: const InputDecoration(labelText: 'API key')),
          const SizedBox(height: 10),
          _primary('Connect with API key', _go),
        ],
      ];

  List<Widget> _codeStep() => [
        Text('Check your email', style: display(26)),
        const SizedBox(height: 6),
        Text(_sent, style: const TextStyle(color: C.muted, fontSize: 14, height: 1.5)),
        const SizedBox(height: 16),
        TextField(
          controller: _code,
          autofocus: true,
          keyboardType: TextInputType.number,
          autofillHints: const [AutofillHints.oneTimeCode],
          maxLength: 6,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 24, letterSpacing: 8, fontWeight: FontWeight.w600),
          onChanged: (v) {
            if (v.replaceAll(RegExp(r'\D'), '').length == 6 && !_busy) _checkCode();
          },
          decoration: const InputDecoration(labelText: '6-digit code', counterText: ''),
        ),
        const SizedBox(height: 12),
        _primary('Continue', _checkCode),
        const SizedBox(height: 4),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          _link('Use a different email', () => setState(() {
                _step = 0;
                _err = null;
              })),
          _link('Send a new code', _sendCode),
        ]),
      ];

  List<Widget> _nameStep() => [
        Text('What should Hoola call you?', style: display(24)),
        const SizedBox(height: 6),
        const Text('Your name, the way you like to hear it.', style: TextStyle(color: C.muted, fontSize: 14, height: 1.5)),
        const SizedBox(height: 16),
        TextField(
          controller: _name,
          autofocus: true,
          autofillHints: const [AutofillHints.name],
          textCapitalization: TextCapitalization.words,
          onSubmitted: (_) => _saveName(),
          decoration: const InputDecoration(labelText: 'Your name'),
        ),
        const SizedBox(height: 12),
        _primary('Continue', _saveName),
      ];

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Aurora(
          child: SafeArea(
            child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 24), children: [
              Center(child: LiveSantosh(feeling: Mood.happy, size: _step == 0 ? 220 : 160, thought: false)),
              const SizedBox(height: 8),
              Glass(
                radius: 30,
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  ...(_step == 0 ? _choose() : _step == 1 ? _codeStep() : _nameStep()),
                  if (_err != null) ...[
                    const SizedBox(height: 12),
                    Text(_err!, style: const TextStyle(color: C.bad, fontSize: 13)),
                  ],
                  const SizedBox(height: 14),
                  const Text('By continuing you agree to Hoola\'s Terms and Privacy Policy. Hoola never asks for your '
                      'bank PIN, card number or a bank OTP.',
                      textAlign: TextAlign.center, style: TextStyle(color: C.faint, fontSize: 12)),
                ]),
              ),
            ]),
          ),
        ),
      );
}
