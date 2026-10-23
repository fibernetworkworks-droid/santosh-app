/// Profile > DevOps Sahayak: Hoola as the team's DevOps engineer.
/// Aaj (failed builds, deploy cards waiting for HER tap, sites down, SSL / disk) · Builds (GitHub Actions runs explained: job, step,
/// kind, fix; flaky; build time) · Deploy (production deploy / rollback cards, DORA) · Logs (paste / upload, error kinds, collector on
/// her own server) · Scripts (files she reviews + safety check, checklists) · Niyam (GitHub token typed only here, repos, endpoints).
/// Production deploy, environment approval and re-run happen ONLY from the buttons here. Hoola never runs a script anywhere.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body, timeout: const Duration(seconds: 60));
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Set<String> multi = const {}, Set<String> hidden = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(
              controller: c[k],
              obscureText: hidden.contains(k),
              decoration: InputDecoration(labelText: label),
              maxLines: hidden.contains(k) ? 1 : (multi.contains(k) ? 8 : 1),
              style: multi.contains(k) ? const TextStyle(fontFamily: 'monospace', fontSize: 12) : null,
            ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Color _concColor(String c) => switch (c) {
      'success' => C.ok,
      'failure' || 'timed_out' || 'startup_failure' => C.bad,
      'cancelled' => C.muted,
      _ => C.warn,
    };

Color _levelColor(String l) => switch (l) { 'block' => C.bad, 'warn' => C.warn, _ => C.muted };

class DevopsScreen extends StatefulWidget {
  const DevopsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DevopsScreen> createState() => _DevopsScreenState();
}

class _DevopsScreenState extends State<DevopsScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/devops'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  // ---------------------------------------------------------------- Aaj
  Widget _today() {
    final day = _m(_d?['day']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      for (final d in _list(day['waiting']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: DevopsDeployCard(app: widget.app, data: {'deploy': d}, onDone: _load)),
      for (final r in _list(day['failed']).take(6)) Padding(padding: const EdgeInsets.only(bottom: 8), child: _RunTile(app: widget.app, run: r, onDone: _load)),
      for (final e in _list(day['down']))
        Text('• Band: ${_s(e['name'])} (${_s(e['problem'])})', style: const TextStyle(fontSize: 12.5, color: C.bad)),
      for (final e in _list(day['ssl_soon']))
        Text('• SSL: ${_s(e['name'])} ${_s(e['ssl_days'])} din mein khatam', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      for (final d in _list(day['high_disk']))
        Text('• Disk: ${_s(d['server'])} ${_s(d['mount'])} ${_s(d['used_pct'])}%', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      for (final c in _list(day['new_errors']).take(5)) _ClusterTile(app: widget.app, c: c, onDone: _load),
    ]);
  }

  // ---------------------------------------------------------------- Builds
  Widget _builds() {
    final repos = _list(_d?['repos']);
    final joined = _m(_m(_d?['settings'])['github'])['joined'] == true;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (!joined)
        Glass(
          child: const Text('GitHub abhi juda nahi. Niyam tab mein apna fine-grained token jodiye (sirf yahan, chat mein kabhi nahi).',
              style: TextStyle(fontSize: 12.5)),
        ),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Abhi dekho', icon: Icons.sync_rounded, onTap: _busy || !joined ? null : () => _run('POST', '/api/devops/sync')),
        GlassButton(label: 'Build log samjhao', icon: Icons.manage_search_rounded, onTap: _busy ? null : _pasteCiLog),
      ]),
      const SizedBox(height: 10),
      if (repos.isNotEmpty) Text('Repos: ${repos.map((r) => _s(r['full_name'])).join(', ')}', style: const TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 6),
      for (final r in _list(_d?['runs'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: _RunTile(app: widget.app, run: r, onDone: _load)),
      if (_list(_d?['runs']).isEmpty) const Text('Abhi koi run nahi dikha.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 8),
      _HealthPanel(app: widget.app),
    ]);
  }

  Future<void> _pasteCiLog() async {
    final f = await _form(context, 'Build / CI ka log', const [('text', 'Log yahan chipkaiye')], ok: 'Samjhao', multi: {'text'});
    if (f == null || (f['text'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/devops/ci-log', {'text': f['text']});
    if (r != null && mounted) {
      await showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text(_s(r['label'])),
          content: SingleChildScrollView(child: _Diagnosis(diag: r)),
          actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))],
        ),
      );
    }
  }

  // ---------------------------------------------------------------- Deploy
  Widget _deploy() {
    final dora = _m(_d?['dora']);
    final repos = _list(_d?['repos']).where((r) => _s(r['deploy_workflow']).isNotEmpty).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Delivery ke number (30 din)', style: display(14)),
          const SizedBox(height: 4),
          Text(_s(dora['say']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            Pill('Hafte mein ${_s(dora['per_week'])}'),
            if (dora['lead_time_h'] != null) Pill('Lead ${_s(dora['lead_time_h'])} h'),
            if (dora['change_failure_pct'] != null) Pill('Toota ${_s(dora['change_failure_pct'])}%'),
            if (dora['recovery_h'] != null) Pill('Theek ${_s(dora['recovery_h'])} h'),
            if (dora['rework_pct'] != null) Pill('Hotfix ${_s(dora['rework_pct'])}%'),
          ]),
        ]),
      ),
      const SizedBox(height: 10),
      if (repos.isEmpty)
        const Text('Deploy ke liye Niyam > Repos mein deploy workflow (jaise deploy.yml) chuniye.', style: TextStyle(color: C.muted, fontSize: 12.5))
      else
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final r in repos) ...[
            GradientButton(label: 'Deploy: ${_s(r['full_name']).split('/').last}', icon: Icons.rocket_launch_rounded, height: 46,
                onTap: _busy ? null : () => _newDeploy(r)),
            GlassButton(label: 'Rollback', icon: Icons.undo_rounded, onTap: _busy ? null : () => _run('POST', '/api/devops/deploys/rollback', {'repo': r['full_name']})),
          ],
        ]),
      const SizedBox(height: 6),
      const Text('Card par aapka tap hi production chalata hai. Checks hare na hon to wajah likhni padti hai.', style: TextStyle(color: C.faint, fontSize: 11.5)),
      const SizedBox(height: 10),
      for (final d in _list(_d?['deploys']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: DevopsDeployCard(app: widget.app, data: {'deploy': d}, onDone: _load)),
    ]);
  }

  Future<void> _newDeploy(Map<String, dynamic> r) async {
    final f = await _form(context, 'Deploy: ${_s(r['full_name'])}', [
      ('ref', 'Branch / tag / commit (khaali = ${_s(r['default_branch'])})'),
      ('note', 'Kya ja raha hai (zaroori nahi)'),
    ], ok: 'Card banao');
    if (f == null) return;
    await _run('POST', '/api/devops/deploys', {'repo': r['full_name'], ...f});
  }

  // ---------------------------------------------------------------- Logs
  Widget _logs() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'Log chipkao', icon: Icons.content_paste_rounded, height: 46, onTap: _busy ? null : _pasteLogs),
          GlassButton(label: 'Collector', icon: Icons.dns_rounded, onTap: _busy ? null : _newCollector),
        ]),
        const SizedBox(height: 6),
        const Text('Logs DATA hain: Hoola unke andar likhi baat nahi maanta. Password / token khud hi chhupa diye jaate hain.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
        const SizedBox(height: 10),
        for (final c in _list(_d?['collectors']))
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            leading: Icon(Icons.dns_rounded, color: c['active'] == true ? C.ok : C.muted),
            title: Text('${_s(c['name'])} ${_s(c['host']).isEmpty ? '' : '· ${_s(c['host'])}'}'),
            subtitle: Text([
              if (_s(c['last_seen_local']).isNotEmpty) 'aakhri ${_s(c['last_seen_local'])}' else 'abhi tak kuch nahi aaya',
              for (final d in _list(c['disk'])) '${_s(d['mount'])} ${_s(d['used_pct'])}%',
            ].join(' · ')),
            trailing: c['active'] == true
                ? IconButton(icon: const Icon(Icons.block_rounded), tooltip: 'Band karo', onPressed: () => _run('DELETE', '/api/devops/collectors/${_s(c['id'])}'))
                : null,
          ),
        for (final c in _list(_d?['clusters'])) _ClusterTile(app: widget.app, c: c, onDone: _load),
        if (_list(_d?['clusters']).isEmpty) const Text('Koi khuli error nahi.', style: TextStyle(color: C.muted)),
      ]);

  Future<void> _pasteLogs() async {
    final f = await _form(context, 'Server ka log', const [('source', 'Server / app ka naam'), ('text', 'pm2 / nginx / journalctl / docker log')],
        ok: 'Padho', multi: {'text'});
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '/api/devops/logs', f);
  }

  Future<void> _newCollector() async {
    final f = await _form(context, 'Naya collector (aapke server par)', const [('name', 'Server ka naam')], ok: 'Banao');
    if (f == null) return;
    final r = await _run('POST', '/api/devops/collectors', f);
    if (r == null || !mounted) return;
    final setup = [
      'HOOLA_URL=${_s(r['base_url'])}',
      'HOOLA_COLLECTOR=${_s(r['id'])}',
      'HOOLA_SECRET=${_s(r['secret'])}',
    ].join('\n');
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Collector ka secret (sirf abhi)'),
        content: SingleChildScrollView(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            const Text('Ye apne server ki /etc/hoola-agent.env (chmod 600) mein rakhiye. Chat mein mat bhejiye.', style: TextStyle(fontSize: 12.5)),
            const SizedBox(height: 8),
            SelectableText(setup, style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5)),
            const SizedBox(height: 8),
            for (final s in _strs(r['steps'])) Text('• $s', style: const TextStyle(fontSize: 12, color: C.muted)),
          ]),
        ),
        actions: [
          TextButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: setup));
                _snack(context, 'Copy ho gaya');
              },
              child: const Text('Copy')),
          TextButton(
              onPressed: () async {
                try {
                  final t = await widget.app.api!.call('GET', _s(r['script_path']));
                  await Clipboard.setData(ClipboardData(text: '$t'));
                  if (context.mounted) _snack(context, 'Script copy ho gayi (hoola_log_agent.py)');
                } catch (e) {
                  if (context.mounted) _snack(context, '$e');
                }
              },
              child: const Text('Script copy')),
          TextButton(onPressed: () => Navigator.pop(d), child: const Text('Rakh liya')),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------- Scripts
  Widget _scripts() {
    final tpl = _list(_d?['templates']);
    final ck = _m(_d?['checklist_kinds']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Script / config banao (aap padh kar khud chalayengi)', style: display(14)),
      const SizedBox(height: 6),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final t in tpl) ActionChip(label: Text(_s(t['label'])), onPressed: _busy ? null : () => _makeScript(t)),
        ActionChip(label: const Text('Apne shabdon mein'), onPressed: _busy ? null : _customScript),
        ActionChip(label: const Text('Meri script jaancho'), onPressed: _busy ? null : _checkMine),
      ]),
      const SizedBox(height: 10),
      for (final s in _list(_d?['scripts'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: DevopsScriptCard(app: widget.app, data: {'script': s})),
      const SizedBox(height: 8),
      Text('Checklists', style: display(14)),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final e in ck.entries) ActionChip(label: Text(_s(e.value)), onPressed: _busy ? null : () => _run('POST', '/api/devops/checklists', {'kind': e.key})),
      ]),
      const SizedBox(height: 8),
      for (final c in _list(_d?['checklists'])) _ChecklistTile(app: widget.app, c: c, onDone: _load),
    ]);
  }

  Future<void> _makeScript(Map<String, dynamic> t) async {
    final params = _m(t['params']);
    final f = await _form(context, _s(t['label']), [for (final e in params.entries) (e.key, '${e.key} (${_s(e.value)})')], ok: 'Banao');
    if (f == null) return;
    final r = await _run('POST', '/api/devops/scripts', {'kind': t['kind'], 'params': f});
    if (r != null && mounted) _openScript(r);
  }

  Future<void> _customScript() async {
    final f = await _form(context, 'Kaunsi script chahiye?', const [('ask', 'Jaise: har raat uploads folder ka backup, 14 din rakho')], ok: 'Banao', multi: {'ask'});
    if (f == null || (f['ask'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/devops/scripts', {'kind': 'custom', 'ask': f['ask']});
    if (r != null && mounted) _openScript(r);
  }

  Future<void> _checkMine() async {
    final f = await _form(context, 'Aapki script', const [('name', 'File ka naam (deploy.sh / ci.yml / Dockerfile)'), ('content', 'Script yahan')],
        ok: 'Jaancho', multi: {'content'});
    if (f == null || (f['content'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/devops/scripts/check', f);
    if (r != null && mounted) _openScript(r);
  }

  void _openScript(Map<String, dynamic> s) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DevopsScriptPage(app: widget.app, script: s)));

  // ---------------------------------------------------------------- Niyam
  Widget _rules() {
    final st = _m(_d?['settings']);
    final gh = _m(st['github']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.hub_rounded, color: gh['joined'] == true ? C.ok : C.muted),
            const SizedBox(width: 8),
            Expanded(child: Text(gh['joined'] == true ? 'GitHub: @${_s(gh['login'])}' : 'GitHub juda nahi', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          const SizedBox(height: 4),
          const Text(
              'Fine-grained token, sirf apne repos: Actions read/write, Contents read, Checks + Commit statuses read, Deployments read/write. '
              'Token sirf yahan likhiye; Hoola use band (encrypted) rakhta hai aur kabhi dikhata nahi.',
              style: TextStyle(fontSize: 12, color: C.muted)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: gh['joined'] == true ? 'Token badlo' : 'Token jodo', icon: Icons.key_rounded, onTap: _busy ? null : _token),
            if (gh['joined'] == true) GlassButton(label: 'Hatao', icon: Icons.link_off_rounded, onTap: _busy ? null : () => _run('DELETE', '/api/devops/github')),
          ]),
        ]),
      ),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: Text('Repos', style: display(14))),
        TextButton.icon(onPressed: _busy ? null : _addRepo, icon: const Icon(Icons.add_rounded), label: const Text('Repo')),
      ]),
      for (final r in _list(_d?['repos']))
        ListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          title: Text(_s(r['full_name'])),
          subtitle: Text(_s(r['deploy_workflow']).isEmpty
              ? 'Sirf builds dekhe jaate hain'
              : 'Deploy: ${_s(r['deploy_workflow'])} -> ${_s(r['environment'])}${_s(r['rollback_workflow']).isEmpty ? '' : ' · rollback ${_s(r['rollback_workflow'])}'}'),
          trailing: IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: () => _run('DELETE', '/api/devops/repos/${_s(r['full_name'])}')),
        ),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: Text('Website / API ki nigrani', style: display(14))),
        TextButton.icon(onPressed: _busy ? null : _addEndpoint, icon: const Icon(Icons.add_rounded), label: const Text('Address')),
      ]),
      for (final e in _list(_d?['endpoints']))
        ListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          leading: Icon(Icons.circle, size: 12, color: e['up'] == true ? C.ok : (e['up'] == false ? C.bad : C.muted)),
          title: Text(_s(e['name'])),
          subtitle: Text([
            _s(e['url']),
            if (e['uptime_pct'] != null) 'uptime ${_s(e['uptime_pct'])}%',
            if (e['ssl_days'] != null) 'SSL ${_s(e['ssl_days'])} din',
            if (_s(e['problem']).isNotEmpty) _s(e['problem']),
          ].join(' · ')),
          trailing: IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: () => _run('DELETE', '/api/devops/endpoints/${_s(e['id'])}')),
        ),
      const SizedBox(height: 10),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Subah ka note: ${_s(st['morning_time'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
          if (_s(st['rules']).isNotEmpty) Text('Deploy ke niyam:\n${_s(st['rules'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          const SizedBox(height: 6),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _busy ? null : _settings),
        ]),
      ),
    ]);
  }

  Future<void> _token() async {
    final f = await _form(context, 'GitHub token', const [('token', 'github_pat_...')], ok: 'Jodo', hidden: {'token'});
    if (f == null || (f['token'] ?? '').isEmpty) return;
    await _run('PUT', '/api/devops/github', {'token': f['token']});
  }

  Future<void> _addRepo() async {
    final f = await _form(context, 'Repo jodo', const [
      ('repo', 'owner/repo'),
      ('deploy_workflow', 'Deploy workflow file (deploy.yml; khaali = sirf builds)'),
      ('environment', 'Environment (production)'),
      ('rollback_workflow', 'Rollback workflow (zaroori nahi)'),
    ], ok: 'Jodo');
    if (f == null || (f['repo'] ?? '').isEmpty) return;
    await _run('POST', '/api/devops/repos', f);
  }

  Future<void> _addEndpoint() async {
    final f = await _form(context, 'Address dekho', const [('url', 'https://...'), ('name', 'Naam'), ('keyword', 'Page mein ye shabd ho (zaroori nahi)')], ok: 'Jodo');
    if (f == null || (f['url'] ?? '').isEmpty) return;
    await _run('POST', '/api/devops/endpoints', f);
  }

  Future<void> _settings() async {
    final f = await _form(context, 'Niyam', const [
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('team', 'Team / company'),
      ('rules', 'Deploy ke niyam (har line ek; checklist mein judte hain)'),
    ], ok: 'Save', multi: {'rules'});
    if (f == null || f.isEmpty) return;
    await _run('PUT', '/api/devops/settings', f);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('DevOps Sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Builds'), (2, 'Deploy'), (3, 'Logs'), (4, 'Scripts'), (5, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _builds(), _deploy(), _logs(), _scripts(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Hoola builds aur logs padhta hai, scripts likhta hai; koi command / script khud nahi chalata, aapke server mein login nahi karta. '
                  'Production deploy sirf aapke tap se.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- pieces
class _Diagnosis extends StatelessWidget {
  const _Diagnosis({required this.diag});
  final Map<String, dynamic> diag;
  @override
  Widget build(BuildContext context) {
    final jobs = _list(diag['jobs']);
    final lines = _strs(diag['lines']).isNotEmpty ? _strs(diag['lines']) : (jobs.isEmpty ? <String>[] : _strs(jobs.first['lines']));
    final tests = _strs(diag['tests']).isNotEmpty ? _strs(diag['tests']) : (jobs.isEmpty ? <String>[] : _strs(jobs.first['tests']));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      if (_s(diag['job']).isNotEmpty || _s(diag['step']).isNotEmpty)
        Text('Job: ${_s(diag['job'])}${_s(diag['step']).isEmpty ? '' : '  ·  Step: ${_s(diag['step'])}'}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
      if (_s(diag['why']).isNotEmpty) Text(_s(diag['why']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
      if (_s(diag['fix']).isNotEmpty) Text('Theek kaise: ${_s(diag['fix'])}', style: const TextStyle(fontSize: 12.5, color: C.accentSoft, height: 1.3)),
      if (_s(diag['hint']).isNotEmpty) Text('Andaaza: ${_s(diag['hint'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
      if (_s(diag['note']).isNotEmpty) Text(_s(diag['note']), style: const TextStyle(fontSize: 12, color: C.warn)),
      if (diag['flaky_likely'] == true) const Text('Flaky jaisa: wahi commit dobara chala ke dekhiye.', style: TextStyle(fontSize: 12, color: C.warn)),
      for (final t in tests.take(5)) Text('✗ $t', style: const TextStyle(fontSize: 11.5, color: C.bad)),
      if (lines.isNotEmpty)
        Container(
          margin: const EdgeInsets.only(top: 6),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: const Color(0x22000000), borderRadius: BorderRadius.circular(8)),
          child: SelectableText(lines.take(8).join('\n'), style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
        ),
    ]);
  }
}

class _RunTile extends StatelessWidget {
  const _RunTile({required this.app, required this.run, this.onDone});
  final Santosh app;
  final Map<String, dynamic> run;
  final VoidCallback? onDone;
  @override
  Widget build(BuildContext context) {
    final diag = _m(run['diagnosis']);
    final conc = _s(run['conclusion']).isEmpty ? _s(run['status']) : _s(run['conclusion']);
    return Press(
      onTap: () => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (c) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: SingleChildScrollView(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(run['workflow'])} · ${_s(run['branch'])} · ${_s(run['sha'])}', style: display(15)),
                Text(_s(run['title']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                const SizedBox(height: 8),
                if (diag.isNotEmpty) _Diagnosis(diag: diag),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (_s(run['url']).isNotEmpty) GlassButton(label: 'GitHub par', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: _s(run['url']))),
                  if (const ['failure', 'timed_out', 'cancelled', 'startup_failure'].contains(conc) && run['is_deploy'] != true && run['is_rollback'] != true)
                    GlassButton(
                        label: 'Fail jobs dobara chalao',
                        icon: Icons.replay_rounded,
                        onTap: () async {
                          await _call(context, app, 'POST', '/api/devops/runs/${_s(run['key'])}/rerun');
                          if (c.mounted) Navigator.pop(c);
                          onDone?.call();
                        }),
                ]),
              ]),
            ),
          ),
        ),
      ),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: conc == 'failure' ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(conc == 'success' ? Icons.check_circle_rounded : (conc == 'failure' || conc == 'timed_out' ? Icons.cancel_rounded : Icons.timelapse_rounded),
                color: _concColor(conc), size: 18),
            const SizedBox(width: 6),
            Expanded(child: Text('${_s(run['workflow'])} · ${_s(run['branch'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            if (run['flaky'] == true) const Pill('flaky', fg: C.warn),
            if (run['is_deploy'] == true) const Pill('deploy'),
          ]),
          Text('${_s(run['repo'])} · ${_s(run['sha'])} · ${_s(run['duration'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
          if (_s(diag['label']).isNotEmpty)
            Text('${_s(diag['label'])}${_s(diag['step']).isEmpty ? '' : ' · ${_s(diag['step'])}'}', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
        ]),
      ),
    );
  }
}

class _HealthPanel extends StatefulWidget {
  const _HealthPanel({required this.app});
  final Santosh app;
  @override
  State<_HealthPanel> createState() => _HealthPanelState();
}

class _HealthPanelState extends State<_HealthPanel> {
  Map<String, dynamic>? _h;
  @override
  void initState() {
    super.initState();
    widget.app.api!.call('GET', '/api/devops/health').then((v) {
      if (mounted) setState(() => _h = _m(v));
    }).catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    final h = _h;
    if (h == null) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Builds ki sehat', style: display(14)),
      for (final w in _list(h['workflows']))
        Text('• ${_s(w['workflow'])} (${_s(w['repo'])}): ${_s(w['fail_pct'])}% fail, ${_s(w['say']).split(': ').last}',
            style: TextStyle(fontSize: 12.5, color: _m(w['time'])['slower'] == true ? C.warn : C.muted)),
      if (_list(h['flaky_tests']).isNotEmpty) ...[
        const SizedBox(height: 6),
        const Text('Flaky tests (kabhi fail, kabhi paas)', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
        for (final t in _list(h['flaky_tests']).take(8)) Text('• ${_s(t['name'])} (${_s(t['flips'])}x)', style: const TextStyle(fontSize: 12, color: C.warn)),
      ],
    ]);
  }
}

class _ClusterTile extends StatelessWidget {
  const _ClusterTile({required this.app, required this.c, this.onDone});
  final Santosh app;
  final Map<String, dynamic> c;
  final VoidCallback? onDone;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => showModalBottomSheet<void>(
            context: context,
            isScrollControlled: true,
            builder: (s) => SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SingleChildScrollView(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(c['label'])} · ${_s(c['count'])} baar', style: display(15)),
                    Text('${_s(c['source'])} · ${_s(c['format'])} · pehli ${_s(c['first_seen'])} · aakhri ${_s(c['last_seen'])}',
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                    const SizedBox(height: 6),
                    Text(_s(c['why']), style: const TextStyle(fontSize: 12.5)),
                    Text('Theek kaise: ${_s(c['fix'])}', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
                    for (final x in _strs(c['samples']).take(2))
                      Container(
                        margin: const EdgeInsets.only(top: 6),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(color: const Color(0x22000000), borderRadius: BorderRadius.circular(8)),
                        child: SelectableText(x, style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
                      ),
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      if (_s(c['runbook']).isNotEmpty)
                        GlassButton(
                            label: 'Runbook',
                            icon: Icons.menu_book_rounded,
                            onTap: () async {
                              try {
                                final rb = _m(await app.api!.call('GET', '/api/devops/runbooks/${_s(c['runbook'])}'));
                                if (!s.mounted) return;
                                await showDialog<void>(
                                  context: s,
                                  builder: (d) => AlertDialog(
                                    title: Text(_s(rb['title'])),
                                    content: SingleChildScrollView(
                                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                                        for (final (i, st) in _strs(rb['steps']).indexed) Text('${i + 1}. $st', style: const TextStyle(fontSize: 12.5)),
                                        const SizedBox(height: 6),
                                        Text(_s(rb['note']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                                      ]),
                                    ),
                                    actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))],
                                  ),
                                );
                              } catch (_) {}
                            }),
                      for (final (st, label) in const [('fixed', 'Theek ho gaya'), ('ignored', 'Chhodo'), ('seen', 'Dekh liya')])
                        GlassButton(
                            label: label,
                            onTap: () async {
                              await _call(s, app, 'PATCH', '/api/devops/clusters/${_s(c['id'])}', {'status': st});
                              if (s.mounted) Navigator.pop(s);
                              onDone?.call();
                            }),
                    ]),
                  ]),
                ),
              ),
            ),
          ),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: c['serious'] == true ? C.bad : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(c['label']), style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill('${_s(c['count'])}x'),
                if (_s(c['status']) == 'new') const Padding(padding: EdgeInsets.only(left: 4), child: Pill('nayi', fg: C.warn)),
              ]),
              Text(_s(c['pattern']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: C.muted)),
              Text(_s(c['source']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
            ]),
          ),
        ),
      );
}

class _ChecklistTile extends StatelessWidget {
  const _ChecklistTile({required this.app, required this.c, this.onDone});
  final Santosh app;
  final Map<String, dynamic> c;
  final VoidCallback? onDone;
  @override
  Widget build(BuildContext context) => Glass(
        padding: const EdgeInsets.all(10),
        child: ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: Text('${_s(c['title'])} · ${_s(c['done'])}/${_s(c['total'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          children: [
            for (final i in _list(c['items']))
              CheckboxListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                value: i['done'] == true,
                title: Text(_s(i['text']), style: const TextStyle(fontSize: 12.5)),
                subtitle: Text(_s(i['section']), style: const TextStyle(fontSize: 11, color: C.muted)),
                onChanged: (v) async {
                  await _call(context, app, 'POST', '/api/devops/checklists/${_s(c['id'])}/items/${_s(i['id'])}', {'done': v ?? false});
                  onDone?.call();
                },
              ),
            TextButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: _s(c['text'])));
                  _snack(context, 'Copy ho gaya');
                },
                icon: const Icon(Icons.copy_rounded, size: 16),
                label: const Text('Text copy')),
          ],
        ),
      );
}

class DevopsScriptPage extends StatelessWidget {
  const DevopsScriptPage({super.key, required this.app, required this.script});
  final Santosh app;
  final Map<String, dynamic> script;
  @override
  Widget build(BuildContext context) {
    final fs = _list(script['findings']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(script['name']))),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Glass(
            border: _levelColor(_s(script['verdict']) == 'ok' ? '' : _s(script['verdict'])),
            child: Text(_s(script['say']).isEmpty ? 'Safety jaanch: ${_s(script['verdict'])}' : _s(script['say']),
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(height: 8),
          for (final f in fs)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text('${_s(f['level']).toUpperCase()} · line ${_s(f['line'])}: ${_s(f['why'])}\n→ ${_s(f['fix'])}',
                  style: TextStyle(fontSize: 12.5, color: _levelColor(_s(f['level'])))),
            ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: const Color(0x33000000), borderRadius: BorderRadius.circular(10)),
            child: SelectableText(_s(script['content']), style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5)),
          ),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(
                label: 'Copy',
                icon: Icons.copy_rounded,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: _s(script['content'])));
                  _snack(context, 'Copy ho gaya');
                }),
            if (_s(script['id']).isNotEmpty)
              GlassButton(label: 'Padh li', icon: Icons.done_all_rounded, onTap: () => _call(context, app, 'POST', '/api/devops/scripts/${_s(script['id'])}/reviewed')),
          ]),
          const SizedBox(height: 10),
          const Text('Hoola ise kabhi nahi chalata. Padh kar, test server par pehle, khud chalaiye.', style: TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// `devops_build`: a failed GitHub Actions run explained (job, step, kind, fix).
class DevopsBuildCard extends StatelessWidget {
  const DevopsBuildCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final run = _m(data['run']);
    final diag = _m(run['diagnosis']);
    return Glass(
      border: C.bad,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.build_circle_rounded, color: C.bad),
          const SizedBox(width: 8),
          Expanded(child: Text('Build fail · ${_s(run['repo'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          if (_s(diag['label']).isNotEmpty) Pill(_s(diag['label'])),
        ]),
        Text('${_s(run['workflow'])} · ${_s(run['branch'])} · ${_s(run['sha'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
        const SizedBox(height: 6),
        _Diagnosis(diag: diag),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (_s(run['url']).isNotEmpty) GlassButton(label: 'GitHub par', icon: Icons.open_in_new_rounded, height: 40, onTap: () => Native.openExternal(url: _s(run['url']))),
          if (run['is_deploy'] != true && run['is_rollback'] != true)
            GlassButton(label: 'Dobara chalao', icon: Icons.replay_rounded, height: 40, onTap: () => _call(context, app, 'POST', '/api/devops/runs/${_s(run['key'])}/rerun')),
        ]),
      ]),
    );
  }
}

/// `devops_deploy`: production deploy / rollback / environment approval card. Haan here = HER tap (the only way it runs).
class DevopsDeployCard extends StatefulWidget {
  const DevopsDeployCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<DevopsDeployCard> createState() => _DevopsDeployCardState();
}

class _DevopsDeployCardState extends State<DevopsDeployCard> {
  bool _busy = false;
  late Map<String, dynamic> _d = _m(widget.data['deploy']);

  @override
  void didUpdateWidget(covariant DevopsDeployCard old) {
    super.didUpdateWidget(old);
    _d = _m(widget.data['deploy']);
  }

  Future<void> _decide(bool yes) async {
    String reason = '';
    final checks = _m(_d['checks']);
    final green = _s(checks['state']) == 'success' || _s(checks['state']) == 'skip';
    if (!yes || (!green && _s(_d['kind']) != 'rollback')) {
      final f = await _form(context, yes ? 'Checks hare nahi: phir bhi kyun?' : 'Kyun nahi? (zaroori nahi)', const [('reason', 'Wajah')],
          ok: yes ? 'Haan, phir bhi' : 'Mana karo');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    if (yes) {
      final sure = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text(_s(_d['kind']) == 'rollback' ? 'Rollback karein?' : 'Production par bhejein?'),
          content: Text('${_s(_d['repo'])} @ ${_s(_d['sha'])} -> ${_s(_d['environment'])}'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Ruko')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan')),
          ],
        ),
      );
      if (sure != true) return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/devops/deploys/${_s(_d['id'])}/decide', {'yes': yes, 'hash': _s(_d['hash']), 'reason': reason});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['deploy'] is Map) _d = _m(r['deploy']);
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final checks = _m(d['checks']);
    final changes = _m(d['changes']);
    final rb = _m(d['rollback']);
    final status = _s(d['status']);
    final kind = _s(d['kind']);
    final title = switch (kind) { 'rollback' => 'Rollback', 'env_review' => 'GitHub approval', _ => 'Production deploy' };
    final cs = _s(checks['state']);
    return Glass(
      border: status == 'card' ? C.accent : (status == 'failed' ? C.bad : null),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(kind == 'rollback' ? Icons.undo_rounded : Icons.rocket_launch_rounded, color: status == 'card' ? C.accent : C.muted),
          const SizedBox(width: 8),
          Expanded(child: Text('$title · ${_s(d['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(d['status_label'])),
        ]),
        const SizedBox(height: 4),
        Text('${_s(d['repo'])} @ ${_s(d['sha'])} (${_s(d['ref'])}) -> ${_s(d['environment'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        Text('Workflow: ${_s(d['workflow'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (cs.isNotEmpty && cs != 'skip')
          Text(
              'Checks: ${switch (cs) { 'success' => 'sab hare (${_s(checks['ok'])})', 'failure' => 'FAIL: ${_strs(checks['failed']).join(', ')}', 'pending' => 'abhi chal rahe: ${_strs(checks['pending']).join(', ')}', _ => 'koi check nahi' }}',
              style: TextStyle(fontSize: 12.5, color: cs == 'success' ? C.ok : (cs == 'failure' ? C.bad : C.warn))),
        if (_s(changes['say']).isNotEmpty) Text(_s(changes['say']), style: TextStyle(fontSize: 12.5, color: changes['migration'] == true ? C.warn : C.ink)),
        for (final c in _list(changes['commits']).take(6))
          Text('• ${_s(c['sha'])} ${_s(c['msg'])}${_s(c['by']).isEmpty ? '' : ' (${_s(c['by'])})'}', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        if (_s(rb['how']).isNotEmpty) Text('Wapas: ${_s(rb['how'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(d['forced']).isNotEmpty) Text('Aapki wajah: ${_s(d['forced'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(d['error']).isNotEmpty) Text(_s(d['error']), style: const TextStyle(fontSize: 12, color: C.bad)),
        const SizedBox(height: 8),
        if (status == 'card')
          Row(children: [
            Expanded(child: GradientButton(label: kind == 'env_review' ? 'Haan, approve' : 'Haan, chalao', icon: Icons.check_rounded, height: 44,
                onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else if (_s(d['run_url']).isNotEmpty)
          GlassButton(label: 'GitHub par dekho', icon: Icons.open_in_new_rounded, height: 40, onTap: () => Native.openExternal(url: _s(d['run_url']))),
      ]),
    );
  }
}

/// `devops_alert`: site down / back up, SSL soon, disk full, a serious new error in her logs.
class DevopsAlertCard extends StatelessWidget {
  const DevopsAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final kind = _s(data['kind']);
    final up = kind == 'up';
    final cl = _m(data['cluster']);
    return Glass(
      border: up ? C.ok : C.bad,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) { 'up' => Icons.check_circle_rounded, 'ssl' => Icons.lock_clock_rounded, 'disk' => Icons.storage_rounded, 'log' => Icons.bug_report_rounded, _ => Icons.error_rounded },
              color: up ? C.ok : C.bad),
          const SizedBox(width: 8),
          Expanded(child: Text(switch (kind) { 'up' => 'Phir chal raha', 'ssl' => 'SSL', 'disk' => 'Disk', 'log' => 'Logs mein error', _ => 'Band hai' },
              style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 4),
        Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
        if (_s(cl['fix']).isNotEmpty) Text('Theek kaise: ${_s(cl['fix'])}', style: const TextStyle(fontSize: 12, color: C.accentSoft)),
        if (cl.isNotEmpty && _strs(cl['samples']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(_strs(cl['samples']).first, maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: C.muted)),
          ),
      ]),
    );
  }
}

/// `devops_script`: a script / config file made for her to review (never run by Hoola).
class DevopsScriptCard extends StatelessWidget {
  const DevopsScriptCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final s = _m(data['script']);
    final v = _s(s['verdict']);
    return Press(
      onTap: () async {
        try {
          final full = _m(await app.api!.call('GET', '/api/devops/scripts/${_s(s['id'])}'));
          if (context.mounted) Navigator.of(context).push(MaterialPageRoute(builder: (_) => DevopsScriptPage(app: app, script: full)));
        } catch (e) {
          if (context.mounted) _snack(context, '$e');
        }
      },
      child: Glass(
        border: v == 'block' ? C.bad : null,
        child: Row(children: [
          Icon(Icons.description_rounded, color: v == 'block' ? C.bad : (v == 'warn' ? C.warn : C.ok)),
          const SizedBox(width: 8),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(s['label'])} · ${_s(s['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text(
                  switch (v) {
                    'block' => '${_s(s['blocks'])} khatarnaak cheezein: chalane se pehle badliye',
                    'warn' => '${_s(s['warns'])} baatein sudhaariye',
                    _ => 'Jaanch saaf'
                  },
                  style: TextStyle(fontSize: 12, color: v == 'block' ? C.bad : C.muted)),
            ]),
          ),
          const Icon(Icons.chevron_right_rounded, color: C.muted),
        ]),
      ),
    );
  }
}

/// `devops_day`: the morning DevOps note.
class DevopsDayCard extends StatelessWidget {
  const DevopsDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.wb_sunny_rounded, color: C.accentSoft),
            const SizedBox(width: 8),
            Expanded(child: Text('Aaj ka DevOps note', style: display(14))),
          ]),
          const SizedBox(height: 4),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
          const SizedBox(height: 6),
          TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DevopsScreen(app: app))),
              child: const Text('DevOps kholo')),
        ]),
      );
}
