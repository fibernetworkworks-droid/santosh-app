// Hoola Code (new design) - create or edit one environment: where Hoola runs code in its locked box and what that
// box may reach. Name, network access (none / limited / full), package registries, allowed domains, .env variables
// and a setup script. Same routes as the old DevEnvPage: POST /api/devsahayak/envs (new) and
// PATCH /api/devsahayak/envs/{id} (edit); the saved environment comes back to the page that opened this one.
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'code_kit.dart';

class CodeEnvPage extends StatefulWidget {
  const CodeEnvPage({super.key, required this.app, this.env, this.netOn = false});
  final Santosh app;
  /// The environment to edit; null = a new one.
  final Map<String, dynamic>? env;
  /// Whether the server's network is switched on yet (until then commands run offline).
  final bool netOn;
  @override
  State<CodeEnvPage> createState() => _CodeEnvPageState();
}

class _CodeEnvPageState extends State<CodeEnvPage> {
  late final TextEditingController _name, _hosts, _vars, _setup;
  String _level = 'limited';
  bool _pkgs = true, _busy = false;

  bool get _isNew => widget.env == null;

  @override
  void initState() {
    super.initState();
    final e = widget.env ?? const <String, dynamic>{};
    final net = cm(e['net']);
    _name = TextEditingController(text: cs(e['name']).isEmpty ? (_isNew ? 'Default' : '') : cs(e['name']));
    _hosts = TextEditingController(text: [for (final h in (net['hosts'] as List? ?? const [])) '$h'].join('\n'));
    _vars = TextEditingController(text: [for (final kv in cm(e['env_vars']).entries) '${kv.key}=${kv.value}'].join('\n'));
    _setup = TextEditingController(text: cs(e['setup']));
    if (cs(net['level']).isNotEmpty) _level = cs(net['level']);
    if (net.containsKey('pkgs')) _pkgs = net['pkgs'] != false;
  }

  @override
  void dispose() {
    _name.dispose();
    _hosts.dispose();
    _vars.dispose();
    _setup.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_busy) return;
    setState(() => _busy = true);
    final body = {
      'name': _name.text.trim().isEmpty ? 'Default' : _name.text.trim(),
      'net': {'level': _level, 'pkgs': _pkgs, 'hosts': _hosts.text},
      'env_vars': _vars.text,
      'setup': _setup.text,
    };
    final r = _isNew
        ? await codeCall(context, widget.app, 'POST', '/api/devsahayak/envs', body: body, quiet: true)
        : await codeCall(context, widget.app, 'PATCH', '/api/devsahayak/envs/${Uri.encodeComponent(cs(widget.env!['id']))}', body: body, quiet: true);
    if (!mounted) return;
    if (r != null) {
      Navigator.pop(context, r);
      return;
    }
    setState(() => _busy = false);
    codeToast(context, 'Could not save the environment. Check your connection and try again.');
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: Column(children: [
          CodeTopBar(title: _isNew ? 'New environment' : 'Edit environment'),
          Expanded(
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
              Text('Where Hoola runs your code in its own locked box, and what that box may reach.',
                  style: codeSans(c, size: 14, color: c.ink2)),
              const SizedBox(height: 16),
              CodeField(controller: _name, label: 'Name', hint: 'Default'),
              const CodeSection('Network access'),
              CodeChoiceRow(label: 'None', sub: 'No internet at all', on: _level == 'none', onTap: () => setState(() => _level = 'none')),
              CodeChoiceRow(
                  label: 'Limited (recommended)',
                  sub: 'Package registries and the domains you list',
                  on: _level == 'limited',
                  onTap: () => setState(() => _level = 'limited')),
              CodeChoiceRow(label: 'Full', sub: 'Any public website', on: _level == 'full', onTap: () => setState(() => _level = 'full')),
              if (!widget.netOn && _level != 'none')
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
                  child: Text(
                      'The network is not switched on for this server yet, so commands run offline until the server check passes. Your choice is kept.',
                      style: codeSans(c, size: 13, color: c.ink3)),
                ),
              if (_level == 'limited') ...[
                const SizedBox(height: 4),
                CodeCard(
                  padding: EdgeInsets.zero,
                  child: CodeSwitchRow(
                    label: 'Allow package managers',
                    sub: 'npm, PyPI, crates.io and other registries',
                    value: _pkgs,
                    last: true,
                    onChanged: (v) => setState(() => _pkgs = v),
                  ),
                ),
                const SizedBox(height: 14),
                CodeField(controller: _hosts, label: 'Allowed domains, one per line', hint: 'api.example.com', lines: 2, mono: true),
              ],
              const SizedBox(height: 6),
              CodeField(controller: _vars, label: 'Environment variables (.env format)', hint: 'NODE_ENV=test', lines: 2, mono: true),
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 0, 4, 14),
                child: Text('Not for secrets. Add keys in Repos & GitHub, per repo.', style: codeSans(c, size: 13, color: c.ink3)),
              ),
              CodeField(controller: _setup, label: 'Setup command (runs once, then cached)', hint: 'npm ci', lines: 2, mono: true),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 14),
            child: CodeMain(_isNew ? 'Create environment' : 'Save changes', busy: _busy, onTap: _save),
          ),
        ]),
      ),
    );
  }
}
