/// Profile > QA Sahayak: Hoola as the app tester.
/// Aaj (open bugs, latest runs, targets) · Targets (her own sites / apps: ownership proof, test cases, runs, test account,
/// release readiness) · Bugs (steps, expected vs actual, screenshot, fixed -> retest) · Niyam.
/// Hoola tests only HER OWN sites / apps, never pays, never types a real password (test accounts are typed only here),
/// and a bug goes into her GitHub only when she taps the card.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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

Color _sevColor(String s) => switch (s) { 'critical' => C.bad, 'major' => C.warn, 'minor' => C.accentSoft, _ => C.chip };
Color _resColor(String r) => switch (r) { 'pass' => C.ok, 'fail' || 'error' => C.bad, 'blocked' => C.warn, _ => C.chip };
String _resLabel(String r) =>
    switch (r) { 'pass' => 'Pass', 'fail' => 'Fail', 'error' => 'Error', 'blocked' => 'Ruka', 'manual' => 'Haath se', '' => 'Chala nahi', _ => r };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Set<String> secret = const {}, String? note}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (note != null) Text(note, style: const TextStyle(fontSize: 12.5, color: C.muted)),
          for (final (k, label) in fields)
            TextField(
              controller: c[k],
              obscureText: secret.contains(k),
              enableSuggestions: !secret.contains(k),
              autocorrect: !secret.contains(k),
              decoration: InputDecoration(labelText: label),
              maxLines: secret.contains(k) ? 1 : (k == 'text' ? 6 : 1),
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

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body, timeout: const Duration(seconds: 180));
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

class QaScreen extends StatefulWidget {
  const QaScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<QaScreen> createState() => _QaScreenState();
}

class _QaScreenState extends State<QaScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _bugs = [];
  String _bugFilter = 'open';
  int _tab = 0;
  bool _busy = false;
  final _rules = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/qa'));
      final b = _m(await widget.app.api!.call('GET', '/api/qa/bugs', query: {'status': _bugFilter == 'all' ? '' : _bugFilter}));
      if (!mounted) return;
      setState(() {
        _d = d;
        _bugs = _list(b['bugs']);
        if (_rules.text.isEmpty) _rules.text = _s(_m(d['settings'])['rules']);
      });
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

  void _openTarget(String id) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => QaTargetPage(app: widget.app, id: id))).then((_) => _load());
  void _openBug(String id) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => QaBugPage(app: widget.app, id: id))).then((_) => _load());

  Future<void> _addTarget() async {
    String kind = 'url';
    bool govt = false;
    final ref = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('Kya test karna hai?'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (k, l) in const [('url', 'Meri website'), ('site', 'Hoola ki banayi site'), ('app', 'Hoola ka app design'), ('apk', 'Android APK')])
                  ChoiceChip(label: Text(l), selected: kind == k, onSelected: (_) => set(() => kind = k)),
              ]),
              const SizedBox(height: 8),
              TextField(
                controller: ref,
                decoration: InputDecoration(
                    labelText: kind == 'url' ? 'Website address (https://...)' : (kind == 'site' ? 'Website number (S-0001)' : 'App number (A-0001)')),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: govt,
                onChanged: (v) => set(() => govt = v),
                title: const Text('Sarkari / sarkar se juda (GIGW 3.0)'),
              ),
              if (kind == 'url')
                const Text('Hoola sirf aapki apni site test karta hai: agle step mein ownership pakki karni hogi (DNS / meta tag / file).',
                    style: TextStyle(fontSize: 12, color: C.muted)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Jodo')),
          ],
        ),
      ),
    );
    if (ok != true || ref.text.trim().isEmpty) return;
    final r = await _run('POST', '/api/qa/targets', {
      'kind': kind,
      if (kind == 'url') 'url': ref.text.trim() else 'ref': ref.text.trim(),
      'govt_facing': govt,
    });
    final t = _m(r?['target']);
    if (t['id'] != null && mounted) _openTarget(_s(t['id']));
  }

  Widget _targetTile(Map<String, dynamic> t) {
    final cs = _m(t['cases']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _openTarget(_s(t['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: t['verified'] == true ? null : C.warn,
          child: Row(children: [
            Icon(
                switch (_s(t['kind'])) { 'app' => Icons.phone_android_rounded, 'apk' => Icons.android_rounded, 'site' => Icons.web_rounded, _ => Icons.language_rounded },
                color: C.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(t['number'])} · ${_s(t['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('${cs['active'] ?? 0} cases (${cs['auto'] ?? 0} apne aap)${_s(t['schedule']).isNotEmpty ? ' · roz ${_s(t['schedule'])}' : ''}',
                    style: const TextStyle(color: C.muted, fontSize: 12)),
              ]),
            ),
            Pill(t['verified'] == true ? 'Aapki site' : 'Pakka karo', fg: t['verified'] == true ? C.ok : C.warn),
          ]),
        ),
      ),
    );
  }

  Widget _bugTile(Map<String, dynamic> b) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _openBug(_s(b['id'])),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Pill(_s(b['severity_label']), fg: _sevColor(_s(b['severity']))),
                const SizedBox(width: 6),
                Expanded(child: Text('${_s(b['number'])} · ${_s(b['target'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(b['status_label'])),
              ]),
              const SizedBox(height: 4),
              Text(_s(b['title']), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
              if (b['regression'] == true) const Text('Regression: theek hone ke baad phir toota', style: TextStyle(color: C.bad, fontSize: 12)),
              if ((b['seen'] ?? 1) > 1) Text('${b['seen']} baar dikha', style: const TextStyle(color: C.muted, fontSize: 12)),
            ]),
          ),
        ),
      );

  Widget _today() {
    final d = _d!;
    final oc = _m(d['open_counts']);
    final runs = _list(d['runs']);
    final ts = _list(d['targets']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(d['say']), style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final s in const ['critical', 'major', 'minor', 'trivial'])
              Pill('${const {'critical': 'Bahut gambhir', 'major': 'Gambhir', 'minor': 'Chhote', 'trivial': 'Mamuli'}[s]}: ${oc[s] ?? 0}', fg: _sevColor(s)),
          ]),
        ]),
      ),
      const SizedBox(height: 10),
      if (ts.isEmpty)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Abhi kuch test nahi ho raha.', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            GlassButton(label: 'Site / app jodo', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _addTarget),
          ]),
        ),
      for (final t in ts.take(4)) _targetTile(t),
      if (runs.isNotEmpty) const Text('Haal ke test', style: TextStyle(fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      for (final r in runs.take(6))
        Padding(padding: const EdgeInsets.only(bottom: 6), child: QaRunCard(app: widget.app, data: {'run': r})),
    ]);
  }

  Widget _targets() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final t in _list(_d!['targets'])) _targetTile(t),
        GlassButton(label: 'Naya target jodo', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _addTarget),
      ]);

  Widget _bugList() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final (k, l) in const [('open', 'Khule'), ('fixed', 'Fix ki jaanch baaki'), ('verified', 'Sahi ho gaye'), ('all', 'Sab')])
            ChoiceChip(
                label: Text(l),
                selected: _bugFilter == k,
                onSelected: (_) {
                  setState(() => _bugFilter = k);
                  _load();
                }),
        ]),
        const SizedBox(height: 8),
        if (_bugs.isEmpty) const Text('Koi bug nahi.', style: TextStyle(color: C.muted)),
        for (final b in _bugs) _bugTile(b),
        const SizedBox(height: 8),
        GlassButton(
            label: 'Excel + Jira CSV banao',
            icon: Icons.table_view_rounded,
            height: 40,
            onTap: _busy ? null : () => _run('POST', '/api/qa/register', {})),
      ]);

  Widget _niyam() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Testing ke aapke niyam', style: TextStyle(fontWeight: FontWeight.w800)),
            TextField(controller: _rules, maxLines: 4, decoration: const InputDecoration(hintText: 'Jaise: har release se pehle checkout flow, Hindi page bhi')),
            const SizedBox(height: 6),
            GlassButton(label: 'Save', height: 40, onTap: _busy ? null : () => _run('PUT', '/api/qa/settings', {'rules': _rules.text})),
          ]),
        ),
        const SizedBox(height: 10),
        const Glass(
          child: Text(
              'Kaise kaam karta hai: cases aapke spec / PRD / Hoola ke banaye design se banate hain (ISTQB: equivalence partitions, boundary values, '
              'negative cases). Accessibility WCAG 2.2 AA par; sarkari ke liye GIGW 3.0 / IS 17802; SEBI wale ke liye IS 17802 + WCAG 2.1. '
              'Hoola kabhi pay nahi dabata, asli password nahi bharta, live site par form tab tak nahi bhejta jab tak aap staging ke liye ijazat na dein.',
              style: TextStyle(fontSize: 12.5, height: 1.35)),
        ),
      ]);

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('QA Sahayak')),
        floatingActionButton: _tab <= 1
            ? FloatingActionButton.extended(onPressed: _busy ? null : _addTarget, icon: const Icon(Icons.bug_report_rounded), label: const Text('Test karo'))
            : null,
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Targets'), (2, 'Bugs'), (3, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _targets(), _bugList(), _niyam()][_tab],
              const SizedBox(height: 14),
              const Text('Sirf aapki apni site / app. Pay kabhi nahi dabaya jaata, asli password kabhi nahi. GitHub issue sirf aapke tap se.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- one target
class QaTargetPage extends StatefulWidget {
  const QaTargetPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<QaTargetPage> createState() => _QaTargetPageState();
}

class _QaTargetPageState extends State<QaTargetPage> {
  Map<String, dynamic>? _t;
  List<Map<String, dynamic>> _cases = [];
  Map<String, dynamic>? _ready;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _m(await widget.app.api!.call('GET', '/api/qa/targets/${widget.id}'));
      final c = _m(await widget.app.api!.call('GET', '/api/qa/cases', query: {'target': widget.id}));
      if (mounted) setState(() {
        _t = t;
        _cases = _list(c['cases']);
      });
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

  Future<void> _write() async {
    final f = await _form(context, 'Test cases banao', const [('text', 'Spec / zaroorat (apne shabdon mein, khaali bhi chalega)')],
        ok: 'Banao', note: 'Hoola pehle site / app khol kar dekhega, phir aapki zarooraton ke cases banayega.');
    if (f == null) return;
    await _run('POST', '/api/qa/targets/${widget.id}/generate', {'text': f['text'] ?? ''});
  }

  Future<void> _start() async {
    final which = await showModalBottomSheet<String>(
      context: context,
      builder: (d) => SafeArea(
        child: Wrap(children: [
          for (final (k, l) in const [
            ('smoke', 'Smoke (zaroori cheezein, jaldi)'),
            ('regression', 'Regression (har release se pehle)'),
            ('all', 'Saare cases'),
            ('failed', 'Sirf fail wale dobara'),
            ('accessibility', 'Sirf accessibility'),
          ])
            ListTile(title: Text(l), onTap: () => Navigator.pop(d, k)),
        ]),
      ),
    );
    if (which == null) return;
    await _run('POST', '/api/qa/runs', {'target': widget.id, 'which': which});
  }

  Future<void> _account() async {
    final f = await _form(context, 'Test account (asli nahi)', const [('label', 'Naam (test)'), ('username', 'Username / email'), ('password', 'Password')],
        ok: 'Save', secret: const {'password'}, note: 'Sirf TEST account. Password Hoola ko dikhta nahi; sirf test ke waqt page ke khane mein jaata hai.');
    if (f == null) return;
    await _run('PUT', '/api/qa/targets/${widget.id}/accounts', {'label': f['label'] ?? 'test', 'username': f['username'] ?? '', 'password': f['password'] ?? ''});
  }

  Future<void> _readiness() async {
    final r = await _call(context, widget.app, 'GET', '/api/qa/targets/${widget.id}/readiness');
    if (r != null && mounted) setState(() => _ready = _m(r['readiness']));
  }

  void _caseSheet(Map<String, dynamic> c) => showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        builder: (d) => Padding(
          padding: const EdgeInsets.all(16),
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text('${_s(c['type_label'])} · ${_s(c['priority'])} · ${_s(c['technique'])}${c['auto'] == true ? '' : ' · haath se'}',
                  style: const TextStyle(color: C.muted, fontSize: 12)),
              if (_s(c['preconditions']).isNotEmpty) Text('Pehle: ${_s(c['preconditions'])}', style: const TextStyle(fontSize: 12.5)),
              const SizedBox(height: 6),
              for (final (i, st) in _strs(c['steps_text']).indexed) Text('${i + 1}. $st', style: const TextStyle(fontSize: 13)),
              const SizedBox(height: 6),
              Text('Hona chahiye: ${_s(c['expected'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (c['auto'] == true)
                  GlassButton(
                      label: 'Abhi chalao',
                      icon: Icons.play_arrow_rounded,
                      height: 40,
                      onTap: () {
                        Navigator.pop(d);
                        _run('POST', '/api/qa/runs', {'target': widget.id, 'cases': [c['id']]});
                      }),
                GlassButton(
                    label: 'Pass',
                    icon: Icons.check_rounded,
                    height: 40,
                    color: C.ok,
                    onTap: () {
                      Navigator.pop(d);
                      _run('POST', '/api/qa/cases/${_s(c['id'])}/mark', {'result': 'pass'});
                    }),
                GlassButton(
                    label: 'Fail',
                    icon: Icons.close_rounded,
                    height: 40,
                    color: C.bad,
                    onTap: () async {
                      Navigator.pop(d);
                      final f = await _form(context, 'Kya galat hua?', const [('note', 'Jo dikha (actual)')], ok: 'Bug banao');
                      if (f == null) return;
                      await _run('POST', '/api/qa/cases/${_s(c['id'])}/mark', {'result': 'fail', 'note': f['note'] ?? ''});
                    }),
                GlassButton(
                    label: 'Hatao',
                    icon: Icons.archive_outlined,
                    height: 40,
                    onTap: () {
                      Navigator.pop(d);
                      _run('PATCH', '/api/qa/cases/${_s(c['id'])}', {'status': 'retired'});
                    }),
              ]),
            ]),
          ),
        ),
      );

  Widget _verifyBox(Map<String, dynamic> t) {
    final v = _m(t['verify']);
    return Glass(
      border: C.warn,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(v['say']), style: const TextStyle(fontWeight: FontWeight.w800)),
        for (final w in _strs(v['ways'])) Padding(padding: const EdgeInsets.only(top: 4), child: SelectableText('• $w', style: const TextStyle(fontSize: 12.5))),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(
              label: 'Code copy karo',
              icon: Icons.copy_rounded,
              height: 40,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _s(v['token'])));
                _snack(context, 'Code copy ho gaya');
              }),
          GlassButton(label: 'Jaanch karo', icon: Icons.verified_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/qa/targets/${widget.id}/verify')),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(t == null ? 'Target' : '${_s(t['number'])} · ${_s(t['name'])}')),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: t == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  if (_busy) const LinearProgressIndicator(),
                  if (t['verified'] != true) _verifyBox(t),
                  if (t['verified'] != true) const SizedBox(height: 10),
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(t['kind']) == 'url' ? _s(t['host']) : _s(t['kind']).toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text(_s(t['standard']), style: const TextStyle(fontSize: 12, color: C.muted)),
                      if (_list(t['accounts']).isNotEmpty)
                        Text('Test account: ${_list(t['accounts']).map((a) => '${_s(a['label'])} (${_s(a['hint'])})').join(', ')}',
                            style: const TextStyle(fontSize: 12.5)),
                      const SizedBox(height: 8),
                      Wrap(spacing: 8, runSpacing: 8, children: [
                        GlassButton(label: 'Cases banao', icon: Icons.auto_awesome_rounded, height: 40, onTap: _busy ? null : _write),
                        if (_s(t['kind']) != 'apk') GlassButton(label: 'Test chalao', icon: Icons.play_arrow_rounded, height: 40, onTap: _busy ? null : _start),
                        GlassButton(label: 'Release taiyaar?', icon: Icons.rocket_launch_rounded, height: 40, onTap: _busy ? null : _readiness),
                        if (_s(t['kind']) == 'url' || _s(t['kind']) == 'site')
                          GlassButton(label: 'Test account', icon: Icons.key_rounded, height: 40, onTap: _busy ? null : _account),
                      ]),
                      if (_s(t['kind']) == 'url')
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: t['allow_writes'] == true,
                          title: const Text('Forms sach mein bhejo (sirf staging / test site)'),
                          onChanged: _busy ? null : (v) => _run('PATCH', '/api/qa/targets/${widget.id}', {'allow_writes': v}),
                        ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: t['govt_facing'] == true,
                        title: const Text('Sarkari / GIGW 3.0 (accessibility fail = release ruke)'),
                        onChanged: _busy ? null : (v) => _run('PATCH', '/api/qa/targets/${widget.id}', {'govt_facing': v}),
                      ),
                      if (_s(t['kind']) != 'apk')
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(_s(t['schedule']).isEmpty ? 'Roz regression: band' : 'Roz regression: ${_s(t['schedule'])}'),
                          trailing: const Icon(Icons.schedule_rounded),
                          onTap: () async {
                            final p = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 21, minute: 30));
                            if (p == null) return;
                            await _run('PATCH', '/api/qa/targets/${widget.id}',
                                {'schedule': '${p.hour.toString().padLeft(2, '0')}:${p.minute.toString().padLeft(2, '0')}'});
                          },
                        ),
                    ]),
                  ),
                  if (_ready != null) ...[const SizedBox(height: 10), QaReadyCard(app: widget.app, data: {'readiness': _ready, 'target': t})],
                  const SizedBox(height: 12),
                  Text('Test cases (${_cases.length})', style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  for (final c in _cases)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Press(
                        onTap: () => _caseSheet(c),
                        child: Glass(
                          padding: const EdgeInsets.all(10),
                          child: Row(children: [
                            Pill(_s(c['priority'])),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text(_s(c['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                                Text('${_s(c['number'])} · ${_s(c['type_label'])}${c['auto'] == true ? '' : ' · haath se'}',
                                    style: const TextStyle(fontSize: 11.5, color: C.muted)),
                              ]),
                            ),
                            Pill(_resLabel(_s(c['last_result'])), fg: _resColor(_s(c['last_result']))),
                          ]),
                        ),
                      ),
                    ),
                  const SizedBox(height: 10),
                  if (t['status'] == 'active')
                    TextButton(
                        onPressed: _busy
                            ? null
                            : () async {
                                final r = await _run('DELETE', '/api/qa/targets/${widget.id}');
                                if (r != null && context.mounted) Navigator.pop(context);
                              },
                        child: const Text('Yeh target hatao', style: TextStyle(color: C.bad))),
                ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- one bug
class QaBugPage extends StatefulWidget {
  const QaBugPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<QaBugPage> createState() => _QaBugPageState();
}

class _QaBugPageState extends State<QaBugPage> {
  Map<String, dynamic>? _b;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', '/api/qa/bugs/${widget.id}'));
      if (mounted) setState(() => _b = b);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _status(String st, {bool reason = false}) async {
    String why = '';
    if (reason) {
      final f = await _form(context, 'Wajah', const [('reason', 'Kyun?')], ok: 'Theek');
      if (f == null || (f['reason'] ?? '').isEmpty) return;
      why = f['reason']!;
    }
    await _run('POST', '/api/qa/bugs/${widget.id}/status', {'status': st, 'reason': why});
  }

  Future<void> _github() async {
    final f = await _form(context, 'GitHub issue', const [('repo', 'Repo (owner/naam)')],
        ok: 'Card banao', note: 'Pehle card aayega; issue sirf aapke "Haan" tap se banega.');
    if (f == null || (f['repo'] ?? '').isEmpty) return;
    await _run('POST', '/api/qa/bugs/${widget.id}/github', {'repo': f['repo']});
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    final api = widget.app.api!;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(b == null ? 'Bug' : _s(b['number']))),
      body: Aurora(
        child: b == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                if (_busy) const LinearProgressIndicator(),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Pill(_s(b['severity_label']), fg: _sevColor(_s(b['severity']))),
                      const SizedBox(width: 6),
                      Pill(_s(b['priority'])),
                      const Spacer(),
                      Pill(_s(b['status_label'])),
                    ]),
                    const SizedBox(height: 6),
                    Text(_s(b['title']), style: const TextStyle(fontWeight: FontWeight.w800)),
                    if (_s(b['page_url']).isNotEmpty) SelectableText(_s(b['page_url']), style: const TextStyle(fontSize: 12, color: C.muted)),
                    const SizedBox(height: 8),
                    const Text('Kaise dikhta hai', style: TextStyle(fontWeight: FontWeight.w700)),
                    for (final (i, st) in _strs(b['steps']).indexed) Text('${i + 1}. $st', style: const TextStyle(fontSize: 13)),
                    const SizedBox(height: 6),
                    Text('Hona chahiye: ${_s(b['expected'])}', style: const TextStyle(fontSize: 13, color: C.ok)),
                    Text('Hua: ${_s(b['actual'])}', style: const TextStyle(fontSize: 13, color: C.bad)),
                    if (_strs(b['console']).isNotEmpty) ...[
                      const SizedBox(height: 6),
                      const Text('Console errors', style: TextStyle(fontWeight: FontWeight.w700)),
                      for (final e in _strs(b['console'])) Text(e, style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace')),
                    ],
                  ]),
                ),
                if (_s(b['shot']).contains('/')) ...[
                  const SizedBox(height: 10),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: Image.network(api.absolute('/api/qa/shots/${_s(b['shot'])}'),
                        headers: api.authHeaders,
                        fit: BoxFit.contain,
                        errorBuilder: (_, __, ___) => const Padding(padding: EdgeInsets.all(12), child: Text('Screenshot nahi khula'))),
                  ),
                ],
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (['open', 'reopened'].contains(_s(b['status'])))
                    GlassButton(label: 'Theek kar diya', icon: Icons.build_rounded, height: 40, onTap: _busy ? null : () => _status('fixed')),
                  GlassButton(
                      label: 'Dobara test karo', icon: Icons.replay_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/qa/bugs/${widget.id}/retest')),
                  if (['open', 'reopened', 'fixed'].contains(_s(b['status'])))
                    GlassButton(label: 'Nahi badlenge', icon: Icons.block_rounded, height: 40, onTap: _busy ? null : () => _status('wont_fix', reason: true)),
                  GlassButton(label: 'GitHub issue', icon: Icons.code_rounded, height: 40, onTap: _busy ? null : _github),
                  if (_s(b['status']) != 'closed')
                    GlassButton(label: 'Band karo', icon: Icons.done_all_rounded, height: 40, onTap: _busy ? null : () => _status('closed', reason: true)),
                ]),
                if (_m(_m(b['tracker'])['github']).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: SelectableText('GitHub: ${_s(_m(_m(b['tracker'])['github'])['url'])}', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
                  ),
                const SizedBox(height: 12),
                const Text('Itihaas', style: TextStyle(fontWeight: FontWeight.w800)),
                for (final l in _list(b['log']).reversed)
                  Text('${_s(l['at']).replaceFirst('T', ' ')} · ${_s(l['by'])}: ${_s(l['what'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// qa_run: one test run's result.
class QaRunCard extends StatelessWidget {
  const QaRunCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final r = _m(data['run']);
    final c = _m(r['counts']);
    final bugs = _m(r['bugs']);
    final failed = _s(r['status']) == 'failed';
    return Glass(
      padding: const EdgeInsets.all(12),
      border: (c['fail'] ?? 0) > 0 || failed ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.fact_check_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Test ${_s(r['number'])} · ${_s(r['target'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(r['status']) == 'running' ? 'Chal raha' : (failed ? 'Nahi chala' : 'Ho gaya')),
        ]),
        if (_s(data['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(data['say']), style: const TextStyle(fontSize: 12.5))),
        if (c.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Wrap(spacing: 6, runSpacing: 6, children: [
              Pill('Pass ${c['pass'] ?? 0}', fg: C.ok),
              Pill('Fail ${c['fail'] ?? 0}', fg: C.bad),
              if ((c['blocked'] ?? 0) > 0) Pill('Ruke ${c['blocked']}', fg: C.warn),
              if ((c['not_auto'] ?? 0) > 0) Pill('Haath se ${c['not_auto']}'),
            ]),
          ),
        if (_strs(bugs['new']).isNotEmpty) Text('Naye bug: ${_strs(bugs['new']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.bad)),
        if (_strs(bugs['verified']).isNotEmpty) Text('Fix pakke: ${_strs(bugs['verified']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.ok)),
        if (_s(r['target_id']).isNotEmpty)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => QaTargetPage(app: app, id: _s(r['target_id'])))),
                child: const Text('Dekho')),
          ),
      ]),
    );
  }
}

/// qa_bug: a new or reopened bug.
class QaBugCard extends StatelessWidget {
  const QaBugCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final b = _m(data['bug']);
    return Glass(
      padding: const EdgeInsets.all(12),
      border: _sevColor(_s(b['severity'])),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.bug_report_rounded, color: C.bad),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(b['number'])} · ${_s(b['severity_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(b['status_label'])),
        ]),
        const SizedBox(height: 4),
        Text(_s(b['title']), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
        if (b['regression'] == true) const Text('Regression', style: TextStyle(color: C.bad, fontSize: 12)),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => QaBugPage(app: app, id: _s(b['id'])))),
              child: const Text('Bug kholo')),
        ),
      ]),
    );
  }
}

/// qa_export: a GitHub issue that is filed ONLY when she taps "Haan".
class QaExportCard extends StatefulWidget {
  const QaExportCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<QaExportCard> createState() => _QaExportCardState();
}

class _QaExportCardState extends State<QaExportCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['export'])['status']);
  String _url = '';

  Future<void> _go(bool yes) async {
    final e = _m(widget.data['export']);
    setState(() => _busy = true);
    final r = yes
        ? await _call(context, widget.app, 'POST', '/api/qa/exports/${_s(e['id'])}/push', {'hash': _s(e['hash'])})
        : await _call(context, widget.app, 'POST', '/api/qa/exports/${_s(e['id'])}/cancel');
    if (mounted) setState(() {
      _busy = false;
      if (r != null) {
        _status = _s(_m(r['export'])['status']);
        _url = _s(_m(r['export'])['url']);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final e = _m(widget.data['export']);
    return Glass(
      border: _status == 'card' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.code_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('GitHub issue · ${_s(e['repo'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (_status) { 'card' => 'Aapki haan chahiye', 'done' => 'Ban gaya', 'failed' => 'Nahi bana', _ => 'Radd' }),
        ]),
        const SizedBox(height: 6),
        Text(_s(e['title']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        Container(
          margin: const EdgeInsets.only(top: 6),
          padding: const EdgeInsets.all(8),
          constraints: const BoxConstraints(maxHeight: 180),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
          child: SingleChildScrollView(child: Text(_s(e['body']), style: const TextStyle(fontSize: 11.5, height: 1.3))),
        ),
        Text('Labels: ${_strs(e['labels']).join(', ')}', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        if (_url.isNotEmpty || _s(e['url']).isNotEmpty) SelectableText(_url.isNotEmpty ? _url : _s(e['url']), style: const TextStyle(color: C.accentSoft)),
        if (_status == 'card')
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(children: [
              Expanded(child: GlassButton(label: 'Haan, issue banao', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : () => _go(true))),
              const SizedBox(width: 8),
              Expanded(child: GlassButton(label: 'Nahi', icon: Icons.close_rounded, height: 42, onTap: _busy ? null : () => _go(false))),
            ]),
          ),
      ]),
    );
  }
}

/// qa_ready: release readiness of one target.
class QaReadyCard extends StatelessWidget {
  const QaReadyCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final r = _m(data['readiness']);
    final v = _s(r['verdict']);
    final col = v == 'ready' ? C.ok : (v == 'risky' ? C.warn : C.bad);
    return Glass(
      border: col,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(v == 'ready' ? Icons.rocket_launch_rounded : Icons.report_rounded, color: col),
          const SizedBox(width: 8),
          Expanded(child: Text('Release: ${_s(_m(data['target'])['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (v) { 'ready' => 'Taiyaar', 'risky' => 'Khatra', _ => 'Abhi nahi' }, fg: col),
        ]),
        const SizedBox(height: 4),
        Text(_s(r['say']), style: const TextStyle(fontSize: 13)),
        Text('Pass ${r['pass_rate'] ?? 0}%', style: const TextStyle(fontSize: 12, color: C.muted)),
        for (final b in _strs(r['blockers']).take(8)) Text('• $b', style: const TextStyle(fontSize: 12.5, color: C.bad)),
        for (final b in _strs(r['risks']).take(6)) Text('• $b', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (_s(r['standard']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(r['standard']), style: const TextStyle(fontSize: 11.5, color: C.faint))),
      ]),
    );
  }
}

/// qa_cases: test cases were written for a target.
class QaCasesCard extends StatelessWidget {
  const QaCasesCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final t = _m(data['target']);
    return Glass(
      padding: const EdgeInsets.all(12),
      child: Row(children: [
        const Icon(Icons.checklist_rounded, color: C.accent),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13))),
        TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => QaTargetPage(app: app, id: _s(t['id'])))),
            child: const Text('Cases')),
      ]),
    );
  }
}
