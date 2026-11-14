/// v0.878 HOOLA CODE ENVIRONMENTS - the phone's New session, laid out like Claude Code's mobile Code tab:
/// a quiet "Ready when you are" page, then under it two chips - the cloud ENVIRONMENT (Auto / Default / hers, each with
/// a settings gear, and Create environment) and the REPOSITORY (a searchable list, Connect more) - and one composer
/// ("Type or hold to talk", the mic, the send arrow). Create / edit environment is its own page: Name, Network access
/// (None / Limited - recommended - / Full), the package-manager switch and allowed domains under Limited, variables and
/// a setup script. Everything goes to the same server routes as the web page (/api/devsahayak/envs, /tasks/start).
library;

import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../state.dart';
import 'hoola_theme.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));

void _say(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t.replaceFirst('Exception: ', ''))));
}

const _levelWords = {'none': 'No network', 'limited': 'Limited network', 'full': 'Full network'};

/// The New session page. Pops with the started session's id.
class DevNewSessionPage extends StatefulWidget {
  const DevNewSessionPage({super.key, required this.app, required this.repos, this.repo = '', this.mode = 'auto', this.modes = const []});
  final Santosh app;
  final List<String> repos;
  final String repo;
  final String mode;
  final List<List<String>> modes;   // [id, words]: ask / auto / plan

  @override
  State<DevNewSessionPage> createState() => _DevNewSessionPageState();
}

class _DevNewSessionPageState extends State<DevNewSessionPage> {
  final _ask = TextEditingController();
  final _stt = SpeechToText();
  Map<String, dynamic> _envs = {};
  String _env = '';
  String _repo = '';
  String _mode = 'auto';
  bool _busy = false, _listening = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.mode.isEmpty ? 'auto' : widget.mode;
    _repo = widget.repo.isNotEmpty ? widget.repo : (widget.repos.isEmpty ? '' : widget.repos.first);
    _ask.addListener(() => setState(() {}));
    _loadEnvs();
  }

  @override
  void dispose() {
    _ask.dispose();
    _stt.stop();
    super.dispose();
  }

  Future<void> _loadEnvs() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/devsahayak/envs'));
      if (!mounted) return;
      setState(() {
        _envs = r;
        if (_env.isEmpty) _env = _s(r['pick']).isEmpty ? 'auto' : _s(r['pick']);
      });
    } catch (e) {
      if (mounted) _say(context, '$e');
    }
  }

  List<Map<String, dynamic>> get _envList => [for (final e in _list(_envs['envs'])) if (e['archived'] != true) e];

  String get _envName {
    if (_env.isEmpty || _env == 'auto') return 'Auto';
    for (final e in _envList) {
      if (_s(e['id']) == _env) return _s(e['name']);
    }
    return 'Auto';
  }

  String _short(String r) => r.contains('/') ? r.split('/').last : r;

  Future<void> _start() async {
    final text = _ask.text.trim();
    if (text.isEmpty || _busy) return;
    if (_repo.isEmpty) {
      _say(context, 'Add a repository first.');
      return _pickRepo();
    }
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/devsahayak/tasks/start',
          body: {'kind': 'auto', 'text': text, 'repo': _repo, 'mode': _mode, 'env': _env.isEmpty ? 'auto' : _env},
          timeout: const Duration(minutes: 2)));
      if (!mounted) return;
      if (_s(r['id']).isNotEmpty) {
        Navigator.pop(context, _s(r['id']));
        return;
      }
    } catch (e) {
      if (mounted) _say(context, 'Your new session could not start: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _mic({bool hold = false}) async {
    if (_listening) {
      await _stt.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }
    final ok = await _stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted) setState(() => _listening = false);
    });
    if (!ok) {
      if (mounted) _say(context, 'Microphone permission is needed.');
      return;
    }
    final before = _ask.text.trim();
    setState(() => _listening = true);
    await _stt.listen(
      localeId: widget.app.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 90),
      pauseFor: Duration(seconds: hold ? 30 : 4),
      partialResults: true,
      onResult: (r) {
        if (!mounted) return;
        _ask.text = before.isEmpty ? r.recognizedWords : '$before ${r.recognizedWords}';
        _ask.selection = TextSelection.collapsed(offset: _ask.text.length);
      },
    );
  }

  String get _modeWords {
    for (final m in widget.modes) {
      if (m[0] == _mode) return m[1];
    }
    return _mode;
  }

  Future<void> _pickMode() async {
    final c = HoolaColors.of(context);
    final v = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (sheet) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          _sheetHead(sheet, 'Mode', 'How Hoola works before the pull request'),
          for (final m in widget.modes)
            ListTile(
              title: Text(m[1], style: HoolaType.title(c)),
              trailing: m[0] == _mode ? Icon(Icons.check_rounded, color: c.ink) : null,
              onTap: () => Navigator.pop(sheet, m[0]),
            ),
          const SizedBox(height: 12),
        ]),
      ),
    );
    if (v != null && mounted) setState(() => _mode = v);
  }

  // ---- the environment sheet: Auto, hers (with a settings gear), Create environment
  Future<void> _pickEnv() async {
    final c = HoolaColors.of(context);
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: c.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (sheet) => StatefulBuilder(builder: (sheet, redraw) {
        Widget row(String id, String name, String sub, {Map<String, dynamic>? env}) => ListTile(
              minVerticalPadding: 12,
              leading: Icon(Icons.cloud_outlined, color: c.ink2),
              title: Text(name, style: HoolaType.title(c)),
              subtitle: Text(sub, style: HoolaType.small(c)),
              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                if (env != null)
                  IconButton(
                    tooltip: 'Edit $name',
                    icon: Icon(Icons.settings_outlined, color: c.ink2),
                    onPressed: () async {
                      Navigator.pop(sheet);
                      await _editEnv(env);
                    },
                  ),
                if (_env == id || (_env.isEmpty && id == 'auto')) Icon(Icons.check_rounded, color: c.ink),
              ]),
              onTap: () {
                setState(() => _env = id);
                Navigator.pop(sheet);
              },
            );
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 8, 8, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              _sheetHead(sheet, 'Select environment', 'Choose an environment for your Hoola Code session'),
              row('auto', 'Auto', 'Follows your repositories'),
              for (final e in _envList)
                row(_s(e['id']), _s(e['name']),
                    '${_levelWords[_s(_m(e['net'])['level'])] ?? 'Hoola cloud'}${_s(e['setup']).isNotEmpty ? ' · setup script' : ''}',
                    env: e),
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _PillButton(
                    icon: Icons.add_rounded,
                    label: 'Create environment',
                    onTap: () async {
                      Navigator.pop(sheet);
                      await _editEnv(null);
                    },
                  ),
                ),
              ),
            ]),
          ),
        );
      }),
    );
  }

  Future<void> _editEnv(Map<String, dynamic>? env) async {
    final saved = await Navigator.push<Map<String, dynamic>>(
        context, MaterialPageRoute(builder: (_) => DevEnvPage(app: widget.app, env: env, netOn: _envs['net_on'] == true)));
    if (saved == null || !mounted) return;
    await _loadEnvs();
    if (saved['archived'] == true) {
      if (_env == _s(saved['id'])) setState(() => _env = 'auto');
    } else if (env == null) {
      setState(() => _env = _s(saved['id']));
    }
  }

  // ---- the repository sheet: a searchable list, Connect more
  Future<void> _pickRepo() async {
    final c = HoolaColors.of(context);
    var q = '';
    var searching = false;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: c.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (sheet) => StatefulBuilder(builder: (sheet, redraw) {
        final shown = [for (final r in widget.repos) if (q.isEmpty || r.toLowerCase().contains(q.toLowerCase())) r];
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(8, 8, 8, 16 + MediaQuery.viewInsetsOf(sheet).bottom),
            child: ConstrainedBox(
              constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(sheet).height * .75),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                _sheetHead(sheet, 'Repositories', ''),
                if (searching)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                    child: TextField(
                      autofocus: true,
                      style: HoolaType.body(c),
                      decoration: const InputDecoration(hintText: 'Search repositories', prefixIcon: Icon(Icons.search_rounded)),
                      onChanged: (v) => redraw(() => q = v.trim()),
                    ),
                  ),
                Flexible(
                  child: shown.isEmpty
                      ? Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(widget.repos.isEmpty ? 'No repositories yet. Connect one below.' : 'No repository matches.',
                              textAlign: TextAlign.center, style: HoolaType.small(c)),
                        )
                      : ListView.separated(
                          shrinkWrap: true,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          itemCount: shown.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 4),
                          itemBuilder: (_, i) {
                            final r = shown[i];
                            final owner = r.contains('/') ? r.split('/').first : '';
                            return Material(
                              color: r == _repo ? c.navOn : c.sunk,
                              borderRadius: HoolaRadius.r(HoolaRadius.tile),
                              child: InkWell(
                                borderRadius: HoolaRadius.r(HoolaRadius.tile),
                                onTap: () {
                                  setState(() => _repo = r);
                                  Navigator.pop(sheet);
                                },
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                    if (owner.isNotEmpty) Text(owner, style: HoolaType.small(c)),
                                    Text(_short(r), style: HoolaType.title(c), overflow: TextOverflow.ellipsis),
                                  ]),
                                ),
                              ),
                            );
                          },
                        ),
                ),
                const SizedBox(height: 12),
                Row(children: [
                  const SizedBox(width: 8),
                  _RoundButton(icon: Icons.search_rounded, label: 'Search', onTap: () => redraw(() => searching = !searching)),
                  const Spacer(),
                  _PillButton(
                    icon: Icons.add_rounded,
                    label: 'Connect more',
                    onTap: () async {
                      Navigator.pop(sheet);
                      await _connectMore();
                    },
                  ),
                  const SizedBox(width: 8),
                ]),
              ]),
            ),
          ),
        );
      }),
    );
  }

  /// Connect more: add a repo her GitHub token can reach (owner/name), the same call as Repos > Add.
  Future<void> _connectMore() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Connect a repository'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(controller: c, autofocus: true, decoration: const InputDecoration(labelText: 'owner/name')),
          const SizedBox(height: 8),
          const Text('Your GitHub token must reach it. The token itself is added only in Hoola Code > Rules.'),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Connect')),
        ],
      ),
    );
    final name = c.text.trim();
    c.dispose();
    if (ok != true || name.isEmpty) return;
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/devsahayak/repos', body: {'repo': name}));
      if (!mounted) return;
      final full = _s(r['repo']).isNotEmpty ? _s(r['repo']) : name;
      setState(() {
        if (!widget.repos.contains(full)) widget.repos.add(full);
        _repo = full;
      });
    } catch (e) {
      if (mounted) _say(context, '$e');
    }
  }

  Widget _sheetHead(BuildContext sheet, String title, String sub) {
    final c = HoolaColors.of(sheet);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        IconButton(tooltip: 'Close', icon: Icon(Icons.close_rounded, color: c.ink), onPressed: () => Navigator.pop(sheet)),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Column(children: [
              Text(title, style: HoolaType.heading(c), textAlign: TextAlign.center),
              if (sub.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(sub, style: HoolaType.small(c), textAlign: TextAlign.center),
              ],
            ]),
          ),
        ),
        const SizedBox(width: 48),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return HoolaTheme(appearance: widget.app.appearance, child: Builder(builder: (context) {
      final c = HoolaColors.of(context);
      final canSend = _ask.text.trim().isNotEmpty && !_busy;
      return Scaffold(
        backgroundColor: c.bg,
        appBar: AppBar(
          backgroundColor: c.bg,
          elevation: 0,
          centerTitle: true,
          title: Text('New session', style: HoolaType.title(c)),
        ),
        body: SafeArea(
          top: false,
          child: Column(children: [
            Expanded(
              child: Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.terminal_rounded, size: 56, color: c.accent),
                  const SizedBox(height: 16),
                  Text('Ready when you are', style: HoolaType.hero(c), textAlign: TextAlign.center),
                  const SizedBox(height: 8),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Text('Hoola works on its own branch, runs your tests and opens a pull request. Nothing is merged without you.',
                        style: HoolaType.small(c), textAlign: TextAlign.center),
                  ),
                ]),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: [
                  _Chip(icon: Icons.cloud_outlined, label: _envName, onTap: _busy ? null : _pickEnv, semantics: 'Environment: $_envName'),
                  const SizedBox(width: 10),
                  _Chip(
                    icon: Icons.source_outlined,
                    label: _repo.isEmpty ? 'Add repository' : _short(_repo),
                    onTap: _busy ? null : _pickRepo,
                    semantics: _repo.isEmpty ? 'Add repository' : 'Repository: $_repo',
                  ),
                  if (widget.modes.isNotEmpty) ...[
                    const SizedBox(width: 10),
                    _Chip(icon: Icons.tune_rounded, label: _modeWords, onTap: _busy ? null : _pickMode, semantics: 'Mode: $_modeWords'),
                  ],
                ]),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 4, 6, 4),
                decoration: BoxDecoration(color: c.surface, borderRadius: HoolaRadius.r(28), border: Border.all(color: c.line)),
                child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Expanded(
                    child: TextField(
                      controller: _ask,
                      minLines: 1,
                      maxLines: 6,
                      maxLength: 20000,
                      style: HoolaType.body(c),
                      textInputAction: TextInputAction.newline,
                      decoration: InputDecoration(
                        hintText: _listening ? 'Listening…' : 'Type or hold to talk',
                        counterText: '',
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        filled: false,
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: GestureDetector(
                      onLongPressStart: (_) => _mic(hold: true),
                      onLongPressEnd: (_) {
                        if (_listening) _mic();
                      },
                      child: IconButton(
                        tooltip: _listening ? 'Stop listening' : 'Speak (hold to talk)',
                        onPressed: _busy ? null : _mic,
                        icon: Icon(_listening ? Icons.stop_circle_outlined : Icons.mic_none_rounded,
                            color: _listening ? c.accent : c.ink2),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Semantics(
                      button: true,
                      label: 'Start session',
                      child: Material(
                        color: canSend ? c.accent : c.sunk,
                        shape: const CircleBorder(),
                        child: InkWell(
                          customBorder: const CircleBorder(),
                          onTap: canSend ? _start : null,
                          child: SizedBox(
                            width: HoolaSpace.touch,
                            height: HoolaSpace.touch,
                            child: _busy
                                ? Padding(
                                    padding: const EdgeInsets.all(14),
                                    child: CircularProgressIndicator(strokeWidth: 2, color: c.ink2))
                                : Icon(Icons.arrow_upward_rounded, color: canSend ? c.onAccent : c.ink3),
                          ),
                        ),
                      ),
                    ),
                  ),
                ]),
              ),
            ),
          ]),
        ),
      );
    }));
  }
}

/// Create / edit one environment (Claude Code: "Create a new environment").
class DevEnvPage extends StatefulWidget {
  const DevEnvPage({super.key, required this.app, this.env, this.netOn = false});
  final Santosh app;
  final Map<String, dynamic>? env;
  final bool netOn;

  @override
  State<DevEnvPage> createState() => _DevEnvPageState();
}

class _DevEnvPageState extends State<DevEnvPage> {
  late final TextEditingController _name, _hosts, _vars, _setup;
  String _level = 'limited';
  bool _pkgs = true, _busy = false;

  bool get _isNew => widget.env == null;

  @override
  void initState() {
    super.initState();
    final e = widget.env ?? const {};
    final net = _m(e['net']);
    _name = TextEditingController(text: _s(e['name']).isEmpty ? (_isNew ? 'Default' : '') : _s(e['name']));
    _hosts = TextEditingController(text: [for (final h in (net['hosts'] as List? ?? const [])) '$h'].join('\n'));
    _vars = TextEditingController(text: [for (final kv in _m(e['env_vars']).entries) '${kv.key}=${kv.value}'].join('\n'));
    _setup = TextEditingController(text: _s(e['setup']));
    if (_s(net['level']).isNotEmpty) _level = _s(net['level']);
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
    setState(() => _busy = true);
    final body = {
      'name': _name.text.trim().isEmpty ? 'Default' : _name.text.trim(),
      'net': {'level': _level, 'pkgs': _pkgs, 'hosts': _hosts.text},
      'env_vars': _vars.text,
      'setup': _setup.text,
    };
    try {
      final r = _m(_isNew
          ? await widget.app.api!.call('POST', '/api/devsahayak/envs', body: body)
          : await widget.app.api!.call('PATCH', '/api/devsahayak/envs/${_s(widget.env!['id'])}', body: body));
      if (mounted) Navigator.pop(context, r);
      return;
    } catch (e) {
      if (mounted) _say(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _archive() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('Archive ${_s(widget.env!['name'])}?'),
        content: const Text('Sessions already in it keep running. New sessions cannot pick it.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Archive')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/devsahayak/envs/${_s(widget.env!['id'])}/archive'));
      if (mounted) Navigator.pop(context, {...r, 'archived': true});
    } catch (e) {
      if (mounted) _say(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return HoolaTheme(appearance: widget.app.appearance, child: Builder(builder: (context) {
      final c = HoolaColors.of(context);
      Widget level(String k, String title, String sub, {bool rec = false}) {
        final on = _level == k;
        return InkWell(
          onTap: () => setState(() => _level = k),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Text(title, style: HoolaType.title(c)),
                    if (rec) ...[
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(
                            color: c.infoSoft, borderRadius: HoolaRadius.r(HoolaRadius.chip), border: Border.all(color: c.info)),
                        child: Text('Recommended', style: HoolaType.label(c).copyWith(color: c.info)),
                      ),
                    ],
                  ]),
                  const SizedBox(height: 4),
                  Text(sub, style: HoolaType.small(c)),
                ]),
              ),
              Icon(on ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded, color: on ? c.accent : c.ink3),
            ]),
          ),
        );
      }

      InputDecoration box(String hint) => InputDecoration(
            hintText: hint,
            border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.card), borderSide: BorderSide(color: c.line)),
            enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.card), borderSide: BorderSide(color: c.line)),
          );

      return Scaffold(
        backgroundColor: c.bg,
        appBar: AppBar(backgroundColor: c.bg, elevation: 0, actions: [
          if (!_isNew) IconButton(tooltip: 'Archive', icon: Icon(Icons.archive_outlined, color: c.ink2), onPressed: _busy ? null : _archive),
        ]),
        body: SafeArea(
          top: false,
          child: ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 24), children: [
            Text(_isNew ? 'Create a new environment' : 'Edit environment', style: HoolaType.hero(c)),
            const SizedBox(height: 10),
            Text('Cloud environments are where Hoola Code runs your repo\'s commands. You can always create or edit environments later.',
                style: HoolaType.body(c).copyWith(color: c.ink2)),
            const SizedBox(height: 28),
            Text('Name', style: HoolaType.title(c)),
            const SizedBox(height: 10),
            TextField(controller: _name, maxLength: 60, style: HoolaType.body(c), decoration: box('Default').copyWith(counterText: '')),
            const SizedBox(height: 24),
            Text('Network access', style: HoolaType.title(c)),
            const SizedBox(height: 10),
            Container(
              decoration: BoxDecoration(borderRadius: HoolaRadius.r(HoolaRadius.card), border: Border.all(color: c.line)),
              clipBehavior: Clip.antiAlias,
              child: Column(children: [
                level('none', 'None', 'Sessions can\'t reach the internet.'),
                Divider(height: 1, color: c.line),
                level('limited', 'Limited', 'Sessions reach only what you allow below.', rec: true),
                Divider(height: 1, color: c.line),
                level('full', 'Full', 'Sessions can reach any public site.'),
              ]),
            ),
            if (!widget.netOn && _level != 'none') ...[
              const SizedBox(height: 8),
              Text('The network is not switched on for this server yet, so commands run offline until the server check passes. Your choice is kept.',
                  style: HoolaType.small(c)),
            ],
            if (_level == 'limited') ...[
              const SizedBox(height: 12),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: _pkgs,
                onChanged: (v) => setState(() => _pkgs = v),
                title: Text('Allow package managers', style: HoolaType.body(c)),
                subtitle: Text('PyPI, npm, Maven, crates, Go, RubyGems and others', style: HoolaType.small(c)),
              ),
              const SizedBox(height: 8),
              Text('Allowed domains', style: HoolaType.label(c)),
              const SizedBox(height: 6),
              TextField(
                controller: _hosts,
                minLines: 2,
                maxLines: 6,
                style: HoolaType.code(c),
                decoration: box('api.example.com\n*.example.com'),
              ),
            ],
            const SizedBox(height: 24),
            Text('Environment variables', style: HoolaType.title(c)),
            const SizedBox(height: 4),
            Text('.env format, one NAME=value per line. Never keys or passwords - add those in Rules > repo keys.', style: HoolaType.small(c)),
            const SizedBox(height: 8),
            TextField(controller: _vars, minLines: 2, maxLines: 8, style: HoolaType.code(c), decoration: box('NODE_ENV=test')),
            const SizedBox(height: 24),
            Text('Setup script', style: HoolaType.title(c)),
            const SizedBox(height: 4),
            Text('Runs once with the network, before the first command, and is cached.', style: HoolaType.small(c)),
            const SizedBox(height: 8),
            TextField(controller: _setup, minLines: 3, maxLines: 10, style: HoolaType.code(c), decoration: box('pip install -r requirements.txt')),
            const SizedBox(height: 28),
            SizedBox(
              height: 56,
              child: FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
                onPressed: _busy ? null : _save,
                child: Text(_isNew ? 'Create' : 'Save changes', style: HoolaType.button(c, color: c.onPill)),
              ),
            ),
          ]),
        ),
      );
    }));
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.icon, required this.label, required this.onTap, required this.semantics});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final String semantics;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Semantics(
      button: true,
      label: semantics,
      excludeSemantics: true,
      child: Material(
        color: c.surface,
        shape: StadiumBorder(side: BorderSide(color: c.line)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: HoolaSpace.touch),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(icon, size: 22, color: c.ink2),
                const SizedBox(width: 8),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 180),
                  child: Text(label, style: HoolaType.body(c), overflow: TextOverflow.ellipsis),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class _PillButton extends StatelessWidget {
  const _PillButton({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Material(
      color: c.sunk,
      shape: StadiumBorder(side: BorderSide(color: c.line)),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, color: c.ink),
            const SizedBox(width: 8),
            Text(label, style: HoolaType.button(c)),
          ]),
        ),
      ),
    );
  }
}

class _RoundButton extends StatelessWidget {
  const _RoundButton({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Material(
      color: c.sunk,
      shape: CircleBorder(side: BorderSide(color: c.line)),
      child: IconButton(tooltip: label, onPressed: onTap, icon: Icon(icon, color: c.ink)),
    );
  }
}
