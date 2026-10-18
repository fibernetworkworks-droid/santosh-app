import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';

/// First run: say hello, pick a language, point the app at the Santosh server.
class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key, required this.app, this.onDone});
  final Santosh app;
  final VoidCallback? onDone;
  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  late final _server = TextEditingController(text: widget.app.serverUrl.isEmpty ? 'https://' : widget.app.serverUrl);
  late final _key = TextEditingController(text: widget.app.apiKey);
  final _name = TextEditingController();
  late String _lang = widget.app.language;
  bool _busy = false;
  String? _err;

  Future<void> _go() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    final url = _server.text.trim();
    try {
      final h = await Api(url, _key.text.trim()).health();
      if (h['ok'] != true) throw 'Not a Santosh server';
      await widget.app.saveSettings(server: url, key: _key.text, lang: _lang);
      await widget.app.connect(fresh: true);
      if (widget.app.connected && _name.text.trim().isNotEmpty) {
        await widget.app.api!.saveProfile({'name': _name.text.trim(), 'language': languages[_lang]});
      }
      if (!widget.app.connected) throw widget.app.error ?? 'Could not connect';
      widget.onDone?.call();
    } catch (e) {
      setState(() => _err = 'Connect nahi ho paya: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Aurora(
          child: SafeArea(
            child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 24), children: [
              Center(child: Image.asset('assets/images/santosh_happy.png', height: 300)),
              const SizedBox(height: 8),
              Glass(
                radius: 30,
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('Main Santosh hoon,', style: display(30)),
                  ShaderMask(
                    shaderCallback: (r) => C.gradient.createShader(r),
                    child: Text('aapka AI coworker.', style: display(30, color: Colors.white)),
                  ),
                  const SizedBox(height: 8),
                  const Text('Bas boliye kya karna hai. Main yaad rakhunga, karunga, aur batauga.',
                      style: TextStyle(color: C.muted, fontSize: 14, height: 1.5)),
                  const SizedBox(height: 18),
                  const Text('APNI BHASHA', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.4, color: C.muted)),
                  const SizedBox(height: 8),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    for (final e in languages.entries)
                      ChoiceChip(
                        label: Text(e.value),
                        selected: _lang == e.key,
                        onSelected: (_) => setState(() => _lang = e.key),
                        selectedColor: C.accent,
                        labelStyle: TextStyle(color: _lang == e.key ? Colors.white : C.chip, fontWeight: FontWeight.w600),
                        showCheckmark: false,
                      ),
                  ]),
                  const SizedBox(height: 18),
                  TextField(controller: _name, decoration: const InputDecoration(labelText: 'Aapka naam')),
                  TextField(
                    controller: _server,
                    keyboardType: TextInputType.url,
                    decoration: const InputDecoration(labelText: 'Santosh server address', hintText: 'https://santosh.yourdomain.com'),
                  ),
                  TextField(controller: _key, obscureText: true, decoration: const InputDecoration(labelText: 'API key')),
                  if (_err != null) ...[
                    const SizedBox(height: 12),
                    Text(_err!, style: const TextStyle(color: C.bad, fontSize: 13)),
                  ],
                  const SizedBox(height: 20),
                  GradientButton(label: _busy ? 'Connect ho raha hai…' : 'Santosh se miliye', icon: Icons.arrow_forward_rounded, onTap: _busy ? null : _go),
                ]),
              ),
            ]),
          ),
        ),
      );
}
