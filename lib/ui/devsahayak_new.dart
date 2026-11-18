/// v0.878 HOOLA CODE ENVIRONMENTS + v0.879 HOOLA CODE PHONE (owner-approved design, docs/design/hoola_code/PhoneHome /
/// PhoneEnv / PhoneRepo / PhoneEnvCreate): the phone's New session - the drawer button, the H mark and "Ready when you
/// are", the ENVIRONMENT chip (Auto / Default / hers, each with a settings gear, Create environment) and the REPOSITORY
/// chip (a searchable, multi-select list, Connect more on GitHub), one pill composer (+ files, "Type or hold to talk",
/// the mic, the violet send) and the "Model · Effort   Mode" line under it. Create / edit environment is its own page.
/// Everything goes to the same server routes as the web page (/api/devsahayak/envs, /tasks/start, /repos).
library;

import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../state.dart';
import 'devsahayak_kit.dart';
import 'hoola_theme.dart';

const _levelWords = {'none': 'No network', 'limited': 'Limited network', 'full': 'Full network'};
const _imageExt = ['png', 'jpg', 'jpeg', 'webp', 'gif'];

/// "Hoola cloud · limited network · setup script" for an environment row.
String devEnvSub(Map<String, dynamic> e) {
  final level = hcS(hcM(e['net'])['level']);
  final words = <String>['Hoola cloud', (_levelWords[level] ?? 'Limited network').toLowerCase()];
  if (hcS(e['setup']).trim().isNotEmpty) words.add('setup script');
  return words.join(' · ');
}

/// The New session page (the Hoola Code home on the phone).
class DevNewSessionPage extends StatelessWidget {
  const DevNewSessionPage({
    super.key,
    required this.app,
    required this.repos,
    this.repo = '',
    this.mode = 'auto',
    this.modes = const [],
    this.models = const {},
    this.drawer,
    this.onStarted,
    this.notice = '',
  });
  final Santosh app;
  final List<String> repos;
  final String repo;
  final String mode;
  final List<List<String>> modes;
  final Map<String, dynamic> models;
  final Widget? drawer;
  final ValueChanged<String>? onStarted;
  final String notice;   // a line under the title (GitHub not connected yet)

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _DevNewSessionPageBody(app: app, repos: repos, repo: repo, mode: mode, modes: modes, models: models, drawer: drawer, onStarted: onStarted, notice: notice));
}

class _DevNewSessionPageBody extends StatefulWidget {
  const _DevNewSessionPageBody({
    super.key,
    required this.app,
    required this.repos,
    this.repo = '',
    this.mode = 'auto',
    this.modes = const [],
    this.models = const {},
    this.drawer,
    this.onStarted,
    this.notice = '',
  });
  final Santosh app;
  final List<String> repos;
  final String repo;
  final String mode;
  final List<List<String>> modes;   // [id, words]: ask / auto / plan
  final Map<String, dynamic> models;   // overview 'models': options, default, forced, efforts, default_effort
  final Widget? drawer;                // set = the home (drawer button); null = a pushed page (back button, pops with the id)
  final ValueChanged<String>? onStarted;
  final String notice;   // a line under the title (GitHub not connected yet)

  @override
  State<_DevNewSessionPageBody> createState() => _DevNewSessionPageState();
}

class _DevNewSessionPageState extends State<_DevNewSessionPageBody> {
  final _ask = TextEditingController();
  Map<String, dynamic> _envs = {};
  String _env = '';
  final List<String> _picked = [];   // the first is the session's repo; up to two more change in linked sessions
  String _mode = 'auto';
  String _model = '';
  String _effort = '';
  bool _busy = false;
  final List<Map<String, dynamic>> _images = [];   // {name, data}
  final List<Map<String, dynamic>> _docs = [];     // {name, text}

  @override
  void initState() {
    super.initState();
    _mode = widget.mode.isEmpty ? 'auto' : widget.mode;
    final first = widget.repo.isNotEmpty ? widget.repo : (widget.repos.isEmpty ? '' : widget.repos.first);
    if (first.isNotEmpty) _picked.add(first);
    _model = hcS(widget.models['default']);
    _effort = hcS(widget.models['default_effort']);
    _loadEnvs();
  }

  @override
  void dispose() {
    _ask.dispose();
    super.dispose();
  }

  Future<void> _loadEnvs() async {
    try {
      final r = hcM(await widget.app.api!.call('GET', '/api/devsahayak/envs'));
      if (!mounted) return;
      setState(() {
        _envs = r;
        if (_env.isEmpty) _env = hcS(r['pick']).isEmpty ? 'auto' : hcS(r['pick']);
      });
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  List<Map<String, dynamic>> get _envList => [for (final e in hcList(_envs['envs'])) if (e['archived'] != true) e];

  String get _envName {
    if (_env.isEmpty || _env == 'auto') return 'Auto';
    for (final e in _envList) {
      if (hcS(e['id']) == _env) return hcS(e['name']);
    }
    return 'Auto';
  }

  String get _repoLabel {
    if (_picked.isEmpty) return 'Add repository';
    final first = hcShortRepo(_picked.first);
    return _picked.length > 1 ? '$first +${_picked.length - 1}' : first;
  }

  Future<void> _start() async {
    final text = _ask.text.trim();
    if (text.isEmpty || _busy) return;
    if (_picked.isEmpty) {
      hcSay(context, 'Add a repository first.');
      return _pickRepo();
    }
    setState(() => _busy = true);
    final forced = widget.models['forced'] != null;
    try {
      final r = hcM(await widget.app.api!.call('POST', '/api/devsahayak/tasks/start',
          body: {
            'kind': 'auto',
            'text': text,
            'repo': _picked.first,
            'mode': _mode,
            'env': _env.isEmpty ? 'auto' : _env,
            if (!forced && _model.isNotEmpty) 'model': _model,
            if (!forced && _effort.isNotEmpty) 'effort': _effort,
            if (_picked.length > 1) 'also': _picked.sublist(1),
            if (_images.isNotEmpty) 'images': _images,
            if (_docs.isNotEmpty) 'docs': _docs,
          },
          timeout: const Duration(minutes: 2)));
      if (!mounted) return;
      final id = hcS(r['id']);
      if (id.isNotEmpty) {
        if (widget.onStarted != null) {
          setState(() {
            _busy = false;
            _ask.clear();
            _images.clear();
            _docs.clear();
          });
          widget.onStarted!(id);
        } else {
          Navigator.pop(context, id);
        }
        return;
      }
    } catch (e) {
      if (mounted) hcSay(context, 'Your new session could not start: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  // ---- + : pictures (PNG / JPEG / WebP / GIF, up to 3) and text files (code, logs, notes, up to 3)
  Future<void> _attach() async {
    try {
      final res = await FilePicker.platform.pickFiles(withData: true, allowMultiple: true);
      if (res == null || !mounted) return;
      var skipped = 0;
      for (final f in res.files) {
        final bytes = f.bytes;
        if (bytes == null) {
          skipped++;
          continue;
        }
        final ext = (f.extension ?? '').toLowerCase();
        if (_imageExt.contains(ext)) {
          if (_images.length >= 3 || bytes.length > 3000000) {
            skipped++;
            continue;
          }
          _images.add({'name': f.name, 'data': base64Encode(bytes)});
        } else {
          if (_docs.length >= 3) {
            skipped++;
            continue;
          }
          String text;
          try {
            text = utf8.decode(bytes);
          } catch (_) {
            skipped++;
            continue;
          }
          _docs.add({'name': f.name, 'text': text});
        }
      }
      setState(() {});
      if (skipped > 0) hcSay(context, 'Some files were left out: up to 3 pictures under 3 MB and 3 text files.');
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  // ---- Model · Effort and Mode
  Future<void> _pickModel() async {
    final c = CodeColors.of(context);
    final forced = hcM(widget.models['forced']);
    final options = hcList(widget.models['options']);
    final efforts = [for (final e in (widget.models['efforts'] as List?) ?? const []) '$e'];
    await hcSheet<void>(context, (sheet) => StatefulBuilder(builder: (sheet, redraw) {
          Widget row(String label, bool on, VoidCallback tap) => InkWell(
                onTap: tap,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 52),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Row(children: [
                      Expanded(child: Text(label, style: HcType.ui(c, 16))),
                      if (on) Icon(Icons.check_rounded, size: 22, color: c.ink),
                    ]),
                  ),
                ),
              );
          return SafeArea(
            top: false,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const HcSheetHead(title: 'Model and effort', sub: 'What writes the code for this session'),
                const SizedBox(height: 8),
                if (forced.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
                    child: Text('${hcS(forced['model'])} · ${hcS(forced['why'])}', style: HcType.ui(c, 14, color: c.ink3)),
                  )
                else ...[
                  for (final o in options)
                    row(hcS(o['label']).isEmpty ? hcS(o['id']) : hcS(o['label']), hcS(o['id']) == _model, () {
                      setState(() => _model = hcS(o['id']));
                      redraw(() {});
                    }),
                  if (efforts.isNotEmpty) ...[
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
                      child: Text('Effort', style: HcType.ui(c, 13, color: c.ink4)),
                    ),
                    for (final e in efforts)
                      row(_cap(e), e == _effort, () {
                        setState(() => _effort = e);
                        redraw(() {});
                      }),
                  ],
                ],
                const SizedBox(height: 12),
              ]),
            ),
          );
        }));
  }

  Future<void> _pickMode() async {
    final c = CodeColors.of(context);
    final v = await hcSheet<String>(
      context,
      (sheet) => SafeArea(
        top: false,
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const HcSheetHead(title: 'Mode', sub: 'How Hoola works before the pull request'),
          const SizedBox(height: 8),
          for (final m in widget.modes)
            InkWell(
              onTap: () => Navigator.pop(sheet, m[0]),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 56),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(children: [
                    Expanded(child: Text(m[1], style: HcType.ui(c, 16))),
                    if (m[0] == _mode) Icon(Icons.check_rounded, size: 22, color: c.ink),
                  ]),
                ),
              ),
            ),
          const SizedBox(height: 12),
        ]),
      ),
    );
    if (v != null && mounted) setState(() => _mode = v);
  }

  String _cap(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);

  String get _modelWords {
    final forced = hcM(widget.models['forced']);
    if (forced.isNotEmpty) return hcS(forced['model']);
    var name = _model;
    for (final o in hcList(widget.models['options'])) {
      if (hcS(o['id']) == _model && hcS(o['label']).isNotEmpty) name = hcS(o['label']);
    }
    name = name.replaceFirst(RegExp(r'^Claude '), '');
    if (name.isEmpty) return '';
    return _effort.isEmpty ? name : '$name · ${_cap(_effort)}';
  }

  String get _modeShort => switch (_mode) { 'ask' => 'Ask first', 'plan' => 'Plan first', _ => 'Auto' };

  // ---- the environment sheet: Auto, hers (each with a settings gear), Create environment
  Future<void> _pickEnv() async {
    final c = CodeColors.of(context);
    await hcSheet<void>(context, (sheet) {
      Widget row(String id, String name, String sub, {Map<String, dynamic>? env}) {
        final on = _env == id || (_env.isEmpty && id == 'auto');
        return Semantics(
          button: true,
          selected: on,
          child: InkWell(
            onTap: () {
              setState(() => _env = id);
              Navigator.pop(sheet);
            },
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 64),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(children: [
                  Icon(Icons.cloud_outlined, size: 20, color: c.ink2),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 17)),
                      const SizedBox(height: 2),
                      Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 14, color: c.ink3)),
                    ]),
                  ),
                  if (env != null)
                    HcIconButton(
                      icon: Icons.settings_outlined,
                      label: 'Edit $name',
                      size: 20,
                      onTap: () async {
                        Navigator.pop(sheet);
                        await _editEnv(env);
                      },
                    )
                  else
                    const SizedBox(width: 48),
                  SizedBox(width: 22, child: on ? Icon(Icons.check_rounded, size: 22, color: c.ink, semanticLabel: 'Selected') : null),
                ]),
              ),
            ),
          ),
        );
      }

      return SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 20),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              HcSheetHead(
                title: 'Select environment',
                sub: 'Choose an environment for your Hoola Code session',
                trailing: HcIconButton(
                  icon: Icons.help_outline_rounded,
                  label: 'What is an environment?',
                  color: c.ink,
                  onTap: () => hcSay(sheet,
                      'An environment is where Hoola runs your repo\'s commands: its network, variables and setup script. Auto follows each repo\'s own settings.'),
                ),
              ),
              const SizedBox(height: 10),
              row('auto', 'Auto', 'Follows your repositories'),
              for (final e in _envList) row(hcS(e['id']), hcS(e['name']), devEnvSub(e), env: e),
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 18, 12, 0),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: HcOutlineButton(
                    label: 'Create environment',
                    icon: Icons.add_rounded,
                    filled: true,
                    height: 52,
                    size: 17,
                    weight: FontWeight.w600,
                    onTap: () async {
                      Navigator.pop(sheet);
                      await _editEnv(null);
                    },
                  ),
                ),
              ),
            ]),
          ),
        ),
      );
    });
  }

  Future<void> _editEnv(Map<String, dynamic>? env) async {
    final saved = await Navigator.push<Map<String, dynamic>>(
        context, MaterialPageRoute(builder: (_) => DevEnvPage(app: widget.app, env: env, netOn: _envs['net_on'] == true)));
    if (saved == null || !mounted) return;
    await _loadEnvs();
    if (!mounted) return;
    if (saved['archived'] == true) {
      if (_env == hcS(saved['id'])) setState(() => _env = 'auto');
    } else if (env == null && hcS(saved['id']).isNotEmpty) {
      setState(() => _env = hcS(saved['id']));
    }
  }

  // ---- the repository sheet: search, owner over name, a square initial, a violet checkbox, Connect more on GitHub
  Future<void> _pickRepo() async {
    final c = CodeColors.of(context);
    var q = '';
    await hcSheet<void>(
      context,
      tall: true,
      (sheet) => StatefulBuilder(builder: (sheet, redraw) {
        final shown = [for (final r in widget.repos) if (q.isEmpty || r.toLowerCase().contains(q.toLowerCase())) r];
        void toggle(String r) {
          setState(() {
            if (_picked.contains(r)) {
              _picked.remove(r);
            } else if (_picked.length < 3) {
              _picked.add(r);
            } else {
              hcSay(sheet, 'Up to three repositories in one go.');
            }
          });
          redraw(() {});
        }

        return SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              HcSheetHead(
                title: 'Repositories',
                trailing: TextButton(
                  style: TextButton.styleFrom(minimumSize: const Size(56, 48)),
                  onPressed: () => Navigator.pop(sheet),
                  child: Text('Done', style: HcType.ui(c, 16, weight: FontWeight.w600, color: c.accentInk)),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 10, 8, 6),
                child: TextField(
                  style: HcType.ui(c, 16),
                  cursorColor: c.accent,
                  onChanged: (v) => redraw(() => q = v.trim()),
                  decoration: InputDecoration(
                    hintText: 'Search repositories',
                    hintStyle: HcType.ui(c, 16, color: c.ink4),
                    prefixIcon: Icon(Icons.search_rounded, size: 20, color: c.ink4),
                    filled: true,
                    fillColor: c.bg,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 14),
                    border: OutlineInputBorder(borderRadius: HoolaRadius.r(14), borderSide: BorderSide(color: c.line3)),
                    enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(14), borderSide: BorderSide(color: c.line3)),
                    focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(14), borderSide: BorderSide(color: c.accent)),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Text('Selected · ${_picked.length}', style: HcType.ui(c, 13, color: c.ink4)),
              ),
              Expanded(
                child: shown.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(widget.repos.isEmpty ? 'No repositories yet. Connect one below.' : 'No repository matches.',
                            textAlign: TextAlign.center, style: HcType.ui(c, 14, color: c.ink4)),
                      )
                    : ListView.builder(
                        itemCount: shown.length,
                        itemBuilder: (_, i) {
                          final r = shown[i];
                          final owner = r.contains('/') ? r.split('/').first : '';
                          final name = hcShortRepo(r);
                          final on = _picked.contains(r);
                          return Semantics(
                            checked: on,
                            label: r,
                            excludeSemantics: true,
                            child: InkWell(
                              onTap: () => toggle(r),
                              child: Container(
                                constraints: const BoxConstraints(minHeight: 64),
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
                                child: Row(children: [
                                  Container(
                                    width: 36,
                                    height: 36,
                                    alignment: Alignment.center,
                                    decoration: BoxDecoration(color: c.raised, borderRadius: HoolaRadius.r(10)),
                                    child: Text(name.isEmpty ? '?' : name[0].toUpperCase(),
                                        style: HcType.ui(c, 15, weight: FontWeight.w600, color: c.ink2)),
                                  ),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                                      if (owner.isNotEmpty) Text(owner, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink4)),
                                      Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 16)),
                                    ]),
                                  ),
                                  const SizedBox(width: 12),
                                  _Check(on: on),
                                ]),
                              ),
                            ),
                          );
                        },
                      ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
                child: Text(
                    'Pick up to three repos and Hoola works on all of them together, one pull request in each. It pushes only to its own hoola/… branches.',
                    style: HcType.ui(c, 13, color: c.ink4, height: 1.45)),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: SizedBox(
                  width: double.infinity,
                  child: HcOutlineButton(
                    label: 'Connect more on GitHub',
                    icon: Icons.add_rounded,
                    filled: true,
                    height: 52,
                    size: 16,
                    weight: FontWeight.w600,
                    onTap: () async {
                      Navigator.pop(sheet);
                      await _connectMore();
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

  /// Connect more: the repos her GitHub token reaches that are not on her list yet (tap = add), or owner/name by hand.
  Future<void> _connectMore() async {
    final c = CodeColors.of(context);
    List<Map<String, dynamic>> reach = [];
    String why = '';
    try {
      reach = hcList(hcM(await widget.app.api!.call('GET', '/api/devsahayak/github_repos'))['repos']);
    } catch (e) {
      why = '$e'.replaceFirst('Exception: ', '');
    }
    if (!mounted) return;
    final have = {for (final r in widget.repos) r.toLowerCase()};
    final fresh = [for (final r in reach) if (hcS(r['repo']).isNotEmpty && !have.contains(hcS(r['repo']).toLowerCase())) r];
    final pick = await hcSheet<String>(
      context,
      tall: true,
      (sheet) => SafeArea(
        top: false,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const HcSheetHead(title: 'Connect a repository', sub: 'Repositories your GitHub token can reach'),
          const SizedBox(height: 8),
          Expanded(
            child: fresh.isEmpty
                ? Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                        why.isNotEmpty ? why : 'Every repository your token reaches is already on your list.',
                        textAlign: TextAlign.center,
                        style: HcType.ui(c, 14, color: c.ink4)),
                  )
                : ListView.builder(
                    itemCount: fresh.length,
                    itemBuilder: (_, i) {
                      final r = hcS(fresh[i]['repo']);
                      return InkWell(
                        onTap: () => Navigator.pop(sheet, r),
                        child: Container(
                          constraints: const BoxConstraints(minHeight: 56),
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
                          child: Row(children: [
                            Icon(fresh[i]['private'] == true ? Icons.lock_outline_rounded : Icons.public_rounded, size: 18, color: c.ink4),
                            const SizedBox(width: 12),
                            Expanded(child: Text(r, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 15))),
                            Icon(Icons.add_rounded, size: 20, color: c.ink2),
                          ]),
                        ),
                      );
                    },
                  ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            child: HcOutlineButton(label: 'Type owner/name', onTap: () => Navigator.pop(sheet, '__type__')),
          ),
        ]),
      ),
    );
    if (pick == null || !mounted) return;
    var name = pick;
    if (pick == '__type__') {
      final tc = TextEditingController();
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Connect a repository'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            TextField(controller: tc, autofocus: true, decoration: const InputDecoration(labelText: 'owner/name')),
            const SizedBox(height: 8),
            const Text('Your GitHub token must reach it. The token itself is added only in Hoola Code settings.'),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Connect')),
          ],
        ),
      );
      name = tc.text.trim();
      tc.dispose();
      if (ok != true || name.isEmpty) return;
    }
    try {
      final r = hcM(await widget.app.api!.call('POST', '/api/devsahayak/repos', body: {'repo': name}));
      if (!mounted) return;
      final full = hcS(r['repo']).isNotEmpty ? hcS(r['repo']) : name;
      setState(() {
        if (!widget.repos.contains(full)) widget.repos.add(full);
        if (!_picked.contains(full) && _picked.length < 3) _picked.add(full);
      });
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  Widget _chip({required IconData icon, required String label, required String semantics, VoidCallback? onTap}) {
    final c = CodeColors.of(context);
    return Semantics(
      button: true,
      label: semantics,
      excludeSemantics: true,
      child: Material(
        color: Colors.transparent,
        shape: StadiumBorder(side: BorderSide(color: c.line3)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(icon, size: 20, color: c.ink3),
                const SizedBox(width: 8),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 170),
                  child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 16)),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _attachTray(CodeColors c) {
    final all = [
      for (final (i, x) in _images.indexed) ('i', i, hcS(x['name'])),
      for (final (i, x) in _docs.indexed) ('d', i, hcS(x['name'])),
    ];
    if (all.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Wrap(spacing: 8, runSpacing: 8, children: [
        for (final (k, i, name) in all)
          InputChip(
            label: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: HcType.ui(c, 13, color: c.ink2)),
            avatar: Icon(k == 'i' ? Icons.image_outlined : Icons.description_outlined, size: 16, color: c.ink3),
            backgroundColor: c.chip,
            side: BorderSide(color: c.line3),
            shape: const StadiumBorder(),
            deleteIcon: Icon(Icons.close_rounded, size: 16, color: c.ink3),
            onDeleted: () => setState(() {
              if (k == 'i') {
                _images.removeAt(i);
              } else {
                _docs.removeAt(i);
              }
            }),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Builder(builder: (context) {
      final c = CodeColors.of(context);
      final mw = _modelWords;
      return Scaffold(
        backgroundColor: c.bg,
        drawer: widget.drawer,
        drawerScrimColor: c.scrim,
        body: SafeArea(
          child: Column(children: [
            SizedBox(
              height: 56,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Row(children: [
                  if (widget.drawer != null)
                    Builder(
                        builder: (ctx) => HcIconButton(icon: Icons.notes_rounded, label: 'Sessions', onTap: () => Scaffold.of(ctx).openDrawer()))
                  else
                    HcIconButton(icon: Icons.arrow_back_rounded, label: 'Back', onTap: () => Navigator.maybePop(context)),
                  Expanded(child: Text('New session', textAlign: TextAlign.center, style: HcType.ui(c, 17, weight: FontWeight.w500))),
                  const SizedBox(width: 48),
                ]),
              ),
            ),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    const HcMark(size: 64),
                    const SizedBox(height: 16),
                    Text('Ready when you are', textAlign: TextAlign.center, style: HcType.serif(c, 28)),
                    if (widget.notice.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Text(widget.notice, textAlign: TextAlign.center, style: HcType.ui(c, 14, color: c.ink3, height: 1.45)),
                    ],
                  ]),
                ),
              ),
            ),
            _attachTray(c),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: [
                  _chip(icon: Icons.cloud_outlined, label: _envName, semantics: 'Environment: $_envName', onTap: _busy ? null : _pickEnv),
                  const SizedBox(width: 10),
                  _chip(
                    icon: Icons.description_outlined,
                    label: _repoLabel,
                    semantics: _picked.isEmpty ? 'Add repository' : 'Repositories: ${_picked.join(', ')}',
                    onTap: _busy ? null : _pickRepo,
                  ),
                ]),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 0),
              child: HcComposer(
                controller: _ask,
                hint: 'Type or hold to talk',
                language: widget.app.language,
                sendLabel: 'Start session',
                busy: _busy,
                onPlus: _busy ? null : _attach,
                onSend: _start,
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 2, 16, 12),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                if (mw.isNotEmpty) _metaButton(c, mw, 'Model and effort: $mw', _busy ? null : _pickModel),
                if (widget.modes.isNotEmpty) _metaButton(c, _modeShort, 'Mode: $_modeShort', _busy ? null : _pickMode),
              ]),
            ),
          ]),
        ),
      );
    });
  }

  Widget _metaButton(CodeColors c, String text, String semantics, VoidCallback? onTap) => Semantics(
        button: true,
        label: semantics,
        excludeSemantics: true,
        child: InkWell(
          borderRadius: HoolaRadius.r(HoolaRadius.chip),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 40),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Center(widthFactor: 1, child: Text(text, style: HcType.ui(c, 13, color: c.ink3))),
            ),
          ),
        ),
      );
}

class _Check extends StatelessWidget {
  const _Check({required this.on});
  final bool on;

  @override
  Widget build(BuildContext context) {
    final c = CodeColors.of(context);
    return Container(
      width: 26,
      height: 26,
      decoration: BoxDecoration(
        color: on ? c.accent : Colors.transparent,
        borderRadius: HoolaRadius.r(HoolaRadius.chip),
        border: on ? null : Border.all(color: c.handle, width: 2),
      ),
      child: on ? Icon(Icons.check_rounded, size: 18, color: c.onAccent) : null,
    );
  }
}

/// Create / edit one environment (design PhoneEnvCreate): Name, Network access (None / Limited (Recommended) / Full),
/// the package-manager switch and allowed domains, .env variables, the setup script, a sticky cream button.
class DevEnvPage extends StatelessWidget {
  const DevEnvPage({super.key, required this.app, this.env, this.netOn = false});
  final Santosh app;
  final Map<String, dynamic>? env;
  final bool netOn;

  @override
  Widget build(BuildContext context) => HoolaTheme(appearance: app.appearance, child: _DevEnvPageBody(app: app, env: env, netOn: netOn));
}

class _DevEnvPageBody extends StatefulWidget {
  const _DevEnvPageBody({super.key, required this.app, this.env, this.netOn = false});
  final Santosh app;
  final Map<String, dynamic>? env;
  final bool netOn;

  @override
  State<_DevEnvPageBody> createState() => _DevEnvPageState();
}

class _DevEnvPageState extends State<_DevEnvPageBody> {
  late final TextEditingController _name, _hosts, _vars, _setup;
  String _level = 'limited';
  bool _pkgs = true, _busy = false;

  bool get _isNew => widget.env == null;

  @override
  void initState() {
    super.initState();
    final e = widget.env ?? const <String, dynamic>{};
    final net = hcM(e['net']);
    _name = TextEditingController(text: hcS(e['name']).isEmpty ? (_isNew ? 'Default' : '') : hcS(e['name']));
    _hosts = TextEditingController(text: [for (final h in (net['hosts'] as List? ?? const [])) '$h'].join('\n'));
    _vars = TextEditingController(text: [for (final kv in hcM(e['env_vars']).entries) '${kv.key}=${kv.value}'].join('\n'));
    _setup = TextEditingController(text: hcS(e['setup']));
    if (hcS(net['level']).isNotEmpty) _level = hcS(net['level']);
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
      final r = hcM(_isNew
          ? await widget.app.api!.call('POST', '/api/devsahayak/envs', body: body)
          : await widget.app.api!.call('PATCH', '/api/devsahayak/envs/${hcS(widget.env!['id'])}', body: body));
      if (mounted) Navigator.pop(context, r);
      return;
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _archive() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('Archive ${hcS(widget.env!['name'])}?'),
        content: const Text('Sessions already in it keep running. New sessions cannot pick it.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Archive')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = hcM(await widget.app.api!.call('POST', '/api/devsahayak/envs/${hcS(widget.env!['id'])}/archive'));
      if (mounted) Navigator.pop(context, {...r, 'archived': true, 'id': hcS(widget.env!['id'])});
    } catch (e) {
      if (mounted) hcSay(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Builder(builder: (context) {
      final c = CodeColors.of(context);

      InputDecoration box(String hint) => InputDecoration(
            hintText: hint,
            hintStyle: HcType.ui(c, 15, color: c.ink4),
            filled: true,
            fillColor: c.surface,
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
            enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.line3)),
            focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.accent)),
          );

      Widget label(String t) => Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(t, style: HcType.ui(c, 14, color: c.ink3)));

      Widget level(String k, String title, String sub, {bool top = false}) {
        final on = _level == k;
        return Semantics(
          inMutuallyExclusiveGroup: true,
          checked: on,
          label: '$title. $sub',
          excludeSemantics: true,
          child: InkWell(
            onTap: () => setState(() => _level = k),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
              decoration: BoxDecoration(
                color: on ? c.accentTint : Colors.transparent,
                border: top ? null : Border(top: BorderSide(color: c.line2)),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Container(
                    width: 20,
                    height: 20,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: on ? c.accent : c.radioOff, width: 2)),
                    child: on ? HcDot(c.accent, size: 10) : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(title, style: HcType.ui(c, 16, weight: FontWeight.w600)),
                    const SizedBox(height: 3),
                    Text(sub, style: HcType.ui(c, 14, color: c.ink3, height: 1.4)),
                  ]),
                ),
              ]),
            ),
          ),
        );
      }

      return Scaffold(
        backgroundColor: c.bg,
        body: SafeArea(
          child: Column(children: [
            Container(
              height: 56,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
              child: Row(children: [
                HcIconButton(icon: Icons.arrow_back_ios_new_rounded, label: 'Back', color: c.ink, size: 20, onTap: () => Navigator.maybePop(context)),
                Expanded(
                  child: Text(_isNew ? 'Create a new environment' : 'Edit environment',
                      textAlign: TextAlign.center, style: HcType.ui(c, 17, weight: FontWeight.w600)),
                ),
                if (!_isNew)
                  HcIconButton(icon: Icons.archive_outlined, label: 'Archive', onTap: _busy ? null : _archive)
                else
                  const SizedBox(width: 48),
              ]),
            ),
            Expanded(
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
                label('Name'),
                TextField(
                  controller: _name,
                  maxLength: 60,
                  style: HcType.ui(c, 16),
                  cursorColor: c.accent,
                  decoration: box('Default').copyWith(counterText: ''),
                ),
                const SizedBox(height: 18),
                label('Network access'),
                Container(
                  decoration: BoxDecoration(borderRadius: HoolaRadius.r(14), border: Border.all(color: c.line3)),
                  clipBehavior: Clip.antiAlias,
                  child: Column(children: [
                    level('none', 'None', 'No internet at all', top: true),
                    level('limited', 'Limited (Recommended)', 'Package registries and the domains you list'),
                    level('full', 'Full', 'Any public website'),
                  ]),
                ),
                if (!widget.netOn && _level != 'none') ...[
                  const SizedBox(height: 8),
                  Text('The network is not switched on for this server yet, so commands run offline until the server check passes. Your choice is kept.',
                      style: HcType.ui(c, 13, color: c.ink4, height: 1.4)),
                ],
                if (_level == 'limited') ...[
                  const SizedBox(height: 18),
                  Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Allow package managers', style: HcType.ui(c, 16)),
                        const SizedBox(height: 2),
                        Text('npm, PyPI, crates.io and other registries', style: HcType.ui(c, 13, color: c.ink4)),
                      ]),
                    ),
                    HcSwitch(value: _pkgs, label: 'Allow package managers', onChanged: (v) => setState(() => _pkgs = v)),
                  ]),
                  const SizedBox(height: 18),
                  label('Allowed domains · one per line'),
                  TextField(
                    controller: _hosts,
                    minLines: 2,
                    maxLines: 6,
                    style: HcType.mono(c, 14),
                    cursorColor: c.accent,
                    decoration: box('api.example.com'),
                  ),
                ],
                const SizedBox(height: 18),
                label('Environment variables · .env format'),
                TextField(
                  controller: _vars,
                  minLines: 2,
                  maxLines: 8,
                  style: HcType.mono(c, 14),
                  cursorColor: c.accent,
                  decoration: box('NODE_ENV=test'),
                ),
                const SizedBox(height: 8),
                Text('Not for secrets. Add keys in Hoola Code settings, per repo.', style: HcType.ui(c, 13, color: c.ink4)),
                const SizedBox(height: 18),
                label('Setup script · runs once, then cached'),
                TextField(
                  controller: _setup,
                  minLines: 2,
                  maxLines: 10,
                  style: HcType.mono(c, 14),
                  cursorColor: c.accent,
                  decoration: box('npm ci'),
                ),
              ]),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
              decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.line))),
              child: SizedBox(
                width: double.infinity,
                child: HcCreamButton(
                  label: _isNew ? 'Create environment' : 'Save changes',
                  busy: _busy,
                  onTap: _busy ? null : _save,
                ),
              ),
            ),
          ]),
        ),
      );
    });
  }
}
