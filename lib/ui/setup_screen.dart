import 'package:flutter/material.dart';

import '../api.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import '../emotion.dart';
import 'glass.dart';
import 'live_santosh.dart';

/// First run: say hello, pick a language, sign in (Google, or an API key). The server is fixed in the app.
class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key, required this.app, this.onDone});
  final Santosh app;
  final VoidCallback? onDone;
  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  late final _key = TextEditingController(text: widget.app.apiKey);
  final _name = TextEditingController();
  late String _lang = widget.app.language;
  bool _busy = false;
  bool _advanced = false;
  String? _err;

  Future<void> _google() async {
    final url = widget.app.serverUrl;
    try {
      final h = await Api(url, '').health();
      if (h['google_login'] != true) {
        setState(() => _err = 'Google sign-in is not on yet on this server.');
        return;
      }
      await widget.app.saveSettings(lang: _lang);
      // opens Google consent; the app comes back via the santosh:// deep link
      await launchUrl(widget.app.api?.googleSignInUrl() ?? Api(url, '').googleSignInUrl(), mode: LaunchMode.externalApplication);
    } catch (e) {
      setState(() => _err = 'Google sign-in did not start. Check the internet and press again.');
    }
  }

  Future<void> _go() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    final url = widget.app.serverUrl;
    try {
      if (_key.text.trim().isEmpty) throw 'Add API key';
      final h = await Api(url, _key.text.trim()).health();
      if (h['ok'] != true) throw 'Hoola is not answering right now';
      await widget.app.saveSettings(key: _key.text, lang: _lang);
      await widget.app.connect(fresh: true);
      if (widget.app.connected && _name.text.trim().isNotEmpty) {
        await widget.app.api!.saveProfile({'name': _name.text.trim(), 'language': languages[_lang]});
      }
      if (!widget.app.connected) throw widget.app.error ?? 'Could not connect';
      widget.onDone?.call();
    } catch (e) {
      setState(() => _err = 'Could not connect: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Aurora(
          child: SafeArea(
            child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 24), children: [
              const Center(child: LiveSantosh(feeling: Mood.happy, size: 260, thought: false)),
              const SizedBox(height: 8),
              Glass(
                radius: 30,
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('Hello, I am Hoola', style: display(30)),
                  const SizedBox(height: 8),
                  const Text('Your AI companion. Paying bills, groceries from the shop, cabs, email, reminders — just say it and I will do it.',
                      style: TextStyle(color: C.muted, fontSize: 14, height: 1.5)),
                  const SizedBox(height: 18),
                  Text(softCaps('YOUR LANGUAGE'), style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, letterSpacing: .1, color: C.muted)),
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
                  TextField(controller: _name, decoration: const InputDecoration(labelText: 'Your name')),
                  const SizedBox(height: 14),
                  Press(
                    onTap: _busy ? null : _google,
                    child: Container(
                      height: 54,
                      decoration: BoxDecoration(color: C.ink, borderRadius: BorderRadius.circular(18)),
                      child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                        Text('G', style: TextStyle(color: Color(0xFF4285F4), fontWeight: FontWeight.w900, fontSize: 20)),
                        SizedBox(width: 10),
                        Text('Start with Google', style: TextStyle(color: C.onAccent, fontWeight: FontWeight.w800, fontSize: 15.5)),
                      ]),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Center(
                    child: TextButton(
                      onPressed: () => setState(() => _advanced = !_advanced),
                      child: Text(_advanced ? 'Hide API key' : 'Or connect with an API key', style: const TextStyle(color: C.muted)),
                    ),
                  ),
                  if (_advanced)
                    TextField(controller: _key, obscureText: true, decoration: const InputDecoration(labelText: 'API key')),
                  if (_err != null) ...[
                    const SizedBox(height: 12),
                    Text(_err!, style: const TextStyle(color: C.bad, fontSize: 13)),
                  ],
                  const SizedBox(height: 14),
                  const Text('Your data is only yours. Hoola will never ask for a PIN, OTP or password.',
                      textAlign: TextAlign.center, style: TextStyle(color: C.faint, fontSize: 11.5)),
                  const SizedBox(height: 14),
                  if (_advanced)
                    GradientButton(label: _busy ? 'Connecting…' : 'Connect with API key', icon: Icons.arrow_forward_rounded, onTap: _busy ? null : _go),
                ]),
              ),
            ]),
          ),
        ),
      );
}
