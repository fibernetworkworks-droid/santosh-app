/// Profile > App Review Sahayak: Hoola reviews HER own app (APK / AAB / source ZIP / GitHub repo) or website for security,
/// privacy and store-policy risks, explains each in plain words with evidence + a fix, and makes a report + fix list.
/// Aaj (her apps with the latest score, new review) · Reviews · Niyam (stack, kids, iPhone, developer, GitHub read-only token,
/// verified domains). Static reading only. The fix list goes to the Developer Sahayak / her developer only after HER tap.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _sevColor(String s) => switch (s) {
      'critical' => C.bad,
      'high' => C.warn,
      'medium' => C.accentSoft,
      'low' => C.chip,
      _ => C.faint,
    };
String _sevLabel(String s) => switch (s) {
      'critical' => 'Bahut gambhir',
      'high' => 'Gambhir',
      'medium' => 'Dhyaan dein',
      'low' => 'Chhota',
      _ => 'Jaankari',
    };
Color _scoreColor(int s) => s >= 80 ? C.ok : (s >= 50 ? C.warn : C.bad);

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body, timeout: const Duration(seconds: 240));
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<String?> _ask(BuildContext context, String title, String label, {bool obscure = false, String hint = ''}) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(controller: c, obscureText: obscure, autocorrect: !obscure, enableSuggestions: !obscure,
          decoration: InputDecoration(labelText: label, hintText: hint)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage')),
      ],
    ),
  );
  final t = c.text.trim();
  return ok == true && t.isNotEmpty ? t : null;
}

Widget _chip(String t, Color c) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withOpacity(.18), borderRadius: BorderRadius.circular(10), border: Border.all(color: c.withOpacity(.6))),
      child: Text(t, style: TextStyle(color: c, fontSize: 11.5, fontWeight: FontWeight.w600)),
    );

Widget _scoreBadge(int score) => Container(
      width: 54,
      height: 54,
      alignment: Alignment.center,
      decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: _scoreColor(score), width: 3)),
      child: Text('$score', style: TextStyle(color: _scoreColor(score), fontSize: 18, fontWeight: FontWeight.w800)),
    );

Widget _counts(Map<String, dynamic> c) => Wrap(spacing: 6, runSpacing: 4, children: [
      for (final s in const ['critical', 'high', 'medium', 'low'])
        if ((c[s] ?? 0) is num && (c[s] as num) > 0) _chip('${_sevLabel(s)} ${c[s]}', _sevColor(s)),
    ]);

/// Start a review: her app file (upload), a GitHub repo or her website. Returns the new review id.
Future<String?> startReview(BuildContext context, Santosh app, String how) async {
  Map<String, dynamic>? r;
  if (how == 'file') {
    final pick = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['apk', 'aab', 'zip', 'apks', 'xapk']);
    final f = pick?.files.firstOrNull;
    if (f == null || f.bytes == null) return null;
    if (context.mounted) _snack(context, 'File bhej rahi hoon, phir jaanch (kuch der lag sakti hai)...');
    try {
      final up = await app.api!.uploadFile('/api/appreview/upload', f.name, f.bytes!, timeout: const Duration(seconds: 400), tries: 2);
      if (!context.mounted) return null;
      r = await _call(context, app, 'POST', '/api/appreview/reviews', {'file': _s(up['file'])});
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
      return null;
    }
  } else if (how == 'repo') {
    final repo = await _ask(context, 'GitHub repo', 'owner/naam ya github.com link', hint: 'meri-company/meri-app');
    if (repo == null || !context.mounted) return null;
    r = await _call(context, app, 'POST', '/api/appreview/reviews', {'repo': repo});
  } else {
    final url = await _ask(context, 'Aapki website', 'Address', hint: 'aapki-dukaan.in');
    if (url == null || !context.mounted) return null;
    r = await _call(context, app, 'POST', '/api/appreview/reviews', {'url': url});
  }
  return r == null ? null : _s(r['id']);
}

class AppReviewScreen extends StatefulWidget {
  const AppReviewScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AppReviewScreen> createState() => _AppReviewScreenState();
}

class _AppReviewScreenState extends State<AppReviewScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/appreview'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void _open(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => AppReviewPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _start(String how) async {
    setState(() => _busy = true);
    final id = await startReview(context, widget.app, how);
    await _load();
    if (mounted) setState(() => _busy = false);
    if (id != null && id.isNotEmpty && mounted) _open(id);
  }

  Future<void> _put(Map<String, dynamic> body) async {
    await _call(context, widget.app, 'PUT', '/api/appreview/settings', body);
    await _load();
  }

  Widget _reviewTile(Map<String, dynamic> r) {
    final cmp = _m(r['compare']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _open(_s(r['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            _scoreBadge((r['score'] as num?)?.toInt() ?? 0),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(r['number'])} · ${_s(r['title'])}', style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text('${_s(r['kind']).toUpperCase()} · ${_s(r['created_at']).split('T').first}', style: const TextStyle(color: C.faint, fontSize: 12)),
                const SizedBox(height: 4),
                _counts(_m(r['counts'])),
                if (cmp['previous'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text('Pichhli ${_s(cmp['previous'])} se: ${(_list(cmp['fixed'])).length} theek, ${_s(cmp['still_open'])} baaki, ${_s(cmp['new'])} naye',
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ),
              ]),
            ),
            const Icon(Icons.chevron_right, color: C.faint),
          ]),
        ),
      ),
    );
  }

  Widget _aaj() {
    final targets = _list(_d?['targets']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Nayi jaanch', style: TextStyle(color: C.ink, fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Apni app ki file (APK / AAB / code ki ZIP), GitHub repo ya website. Hoola sirf padhta hai, app chalata nahi, kahin upload nahi karta.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            FilledButton.icon(onPressed: _busy ? null : () => _start('file'), icon: const Icon(Icons.android), label: const Text('App file')),
            OutlinedButton.icon(onPressed: _busy ? null : () => _start('repo'), icon: const Icon(Icons.code), label: const Text('GitHub repo')),
            OutlinedButton.icon(onPressed: _busy ? null : () => _start('web'), icon: const Icon(Icons.language), label: const Text('Website')),
          ]),
          if (_busy) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator()),
        ]),
      ),
      const SizedBox(height: 14),
      if (targets.isEmpty)
        const Text('Abhi koi jaanch nahi hui.', style: TextStyle(color: C.muted))
      else ...[
        const Text('Aapke apps / sites (aakhri jaanch)', style: TextStyle(color: C.muted, fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        for (final t in targets) _reviewTile(t),
      ],
    ]);
  }

  Widget _reviews() {
    final rs = _list(_d?['reviews']);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(14), children: [
        if (rs.isEmpty) const Text('Koi review nahi.', style: TextStyle(color: C.muted)),
        for (final r in rs) _reviewTile(r),
      ]),
    );
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final gh = _m(st['github']);
    final doms = _list(_d?['domains']);
    final pt = _m(st['play_target']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('App kis cheez se bani hai', style: TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, children: [
            for (final (k, l) in const [('', 'Khud pehchano'), ('android', 'Kotlin / Java'), ('flutter', 'Flutter'), ('react_native', 'React Native'), ('web', 'Website')])
              ChoiceChip(label: Text(l), selected: _s(st['stack']) == k, onSelected: (_) => _put({'stack': k})),
          ]),
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: st['kids'] == true,
              onChanged: (v) => _put({'kids': v}),
              title: const Text('App bachchon (18 se kam) ke liye bhi hai'),
              subtitle: const Text('Play Families policy + DPDP parent consent ki jaanch')),
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: st['ios'] == true,
              onChanged: (v) => _put({'ios': v}),
              title: const Text('iPhone (App Store) version bhi hai')),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Developer ka naam (fix list par)'),
            subtitle: Text(_s(st['developer']).isEmpty ? 'Nahi likha' : _s(st['developer'])),
            trailing: const Icon(Icons.edit, size: 18),
            onTap: () async {
              final n = await _ask(context, 'Developer', 'Naam / company');
              if (n != null) _put({'developer': n});
            },
          ),
          Text('Play niyam: ${_s(pt['since'])} se naye update ko API ${_s(pt['new_and_updates'])} target karna zaroori (jaanch ${_s(st['checked_on'])}).',
              style: const TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('GitHub (sirf padhne ke liye)', style: TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Private repo ke liye fine-grained token banaiye: sirf "Contents: Read-only". Token yahin likhiye, chat mein kabhi nahi.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: Text(gh['joined'] == true ? 'Juda hai ${_s(gh['label'])}' : 'Juda nahi', style: const TextStyle(color: C.ink))),
            if (gh['joined'] == true)
              TextButton(
                  onPressed: () async {
                    await _call(context, widget.app, 'DELETE', '/api/appreview/github');
                    await _load();
                  },
                  child: const Text('Hatao'))
            else
              TextButton(
                  onPressed: () async {
                    final t = await _ask(context, 'GitHub token', 'github_pat_...', obscure: true);
                    if (t == null || !mounted) return;
                    await _call(context, widget.app, 'PUT', '/api/appreview/github', {'token': t});
                    await _load();
                  },
                  child: const Text('Jodo')),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Meri websites (verify)', style: TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('.git / .env jaisi khuli files ki jaanch sirf usi domain par hoti hai jo aapka hai (DNS TXT ya ek file se dikhaiye).',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          for (final d in doms) _domainRow(d),
          TextButton.icon(
              onPressed: () async {
                final u = await _ask(context, 'Domain jodiye', 'aapki-dukaan.in');
                if (u == null || !mounted) return;
                await _call(context, widget.app, 'POST', '/api/appreview/domains', {'url': u});
                await _load();
              },
              icon: const Icon(Icons.add),
              label: const Text('Domain jodo')),
        ]),
      ),
    ]);
  }

  Widget _domainRow(Map<String, dynamic> d) {
    final how = _m(_m(d['how'])['dns']);
    final ok = d['verified'] == true;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(ok ? Icons.verified : Icons.pending_outlined, size: 18, color: ok ? C.ok : C.warn),
          const SizedBox(width: 6),
          Expanded(child: Text(_s(d['host']), style: const TextStyle(color: C.ink))),
          if (!ok)
            TextButton(
                onPressed: () async {
                  await _call(context, widget.app, 'POST', '/api/appreview/domains/verify', {'url': _s(d['host'])});
                  await _load();
                },
                child: const Text('Verify karo')),
        ]),
        if (!ok) ...[
          SelectableText('TXT  ${_s(how['name'])}  =  ${_s(how['value'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
          TextButton(
              onPressed: () => Clipboard.setData(ClipboardData(text: _s(how['value']))),
              child: const Text('Value copy karo')),
        ],
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.app.aName;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: Text('$name · App reviewer'), backgroundColor: Colors.transparent),
      body: _d == null ? const Center(child: CircularProgressIndicator()) : [_aaj, _reviews, _niyam][_tab](),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.shield_outlined), label: 'Aaj'),
          NavigationDestination(icon: Icon(Icons.list_alt), label: 'Reviews'),
          NavigationDestination(icon: Icon(Icons.tune), label: 'Niyam'),
        ],
      ),
    );
  }
}

class AppReviewPage extends StatefulWidget {
  const AppReviewPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AppReviewPage> createState() => _AppReviewPageState();
}

class _AppReviewPageState extends State<AppReviewPage> {
  Map<String, dynamic>? _r;
  String _area = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/appreview/reviews/${widget.id}'));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _mark(Map<String, dynamic> risk, bool ignore) async {
    String note = '';
    if (ignore) {
      final n = await _ask(context, 'Jaan-boojh kar hai?', 'Wajah (jaise: Play declaration bhara hai)');
      if (n == null) return;
      note = n;
    }
    if (!mounted) return;
    await _call(context, widget.app, 'POST', '/api/appreview/reviews/${widget.id}/mark',
        {'key': _s(risk['key']), 'status': ignore ? 'ignored' : 'open', 'note': note});
    await _load();
  }

  Widget _risk(Map<String, dynamic> r) {
    final sev = _s(r['sev']);
    final ignored = r['status'] == 'ignored';
    final ev = _list(r['evidence']);
    final sn = _m(r['snippet']);
    final src = _list(r['sources']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
        border: sev == 'critical' && !ignored ? C.bad : null,
        child: Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text(_s(r['title']),
                style: TextStyle(color: ignored ? C.faint : C.ink, fontWeight: FontWeight.w600, decoration: ignored ? TextDecoration.lineThrough : null)),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Wrap(spacing: 6, runSpacing: 4, children: [
                _chip(_sevLabel(sev), _sevColor(sev)),
                _chip(_s(r['area_label']), C.chip),
                if (r['change'] == 'new') _chip('Naya', C.accent),
                if (ignored) _chip('Aapne chhoda', C.faint),
              ]),
            ),
            childrenPadding: const EdgeInsets.only(bottom: 10),
            expandedCrossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_s(r['explain']), style: const TextStyle(color: C.muted)),
              if (ev.isNotEmpty) ...[
                const SizedBox(height: 8),
                const Text('Kahan mila', style: TextStyle(color: C.ink, fontWeight: FontWeight.w600, fontSize: 12.5)),
                for (final e in ev)
                  Text('• ${_s(e['where'])}${e['line'] != null ? ':${_s(e['line'])}' : ''}${_s(e['text']).isNotEmpty ? '  ${_s(e['text'])}' : ''}',
                      style: const TextStyle(color: C.faint, fontSize: 12, fontFamily: 'monospace')),
              ],
              const SizedBox(height: 8),
              const Text('Kya karein', style: TextStyle(color: C.ink, fontWeight: FontWeight.w600, fontSize: 12.5)),
              Text(_s(r['fix']), style: const TextStyle(color: C.muted)),
              if (_s(sn['code']).isNotEmpty) ...[
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
                  child: SelectableText(_s(sn['code']), style: const TextStyle(color: C.ink, fontSize: 12, fontFamily: 'monospace')),
                ),
                TextButton.icon(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: _s(sn['code'])));
                      _snack(context, 'Code copy ho gaya');
                    },
                    icon: const Icon(Icons.copy, size: 16),
                    label: Text('Copy (${_s(sn['for'])})')),
              ],
              if (src.isNotEmpty)
                Wrap(spacing: 4, children: [
                  for (final s in src.take(2))
                    TextButton(
                        onPressed: () => Native.openExternal(url: _s(s['url'])),
                        child: Text('Source: ${_s(s['date'])}', style: const TextStyle(fontSize: 12))),
                ]),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                    onPressed: () => _mark(r, !ignored), child: Text(ignored ? 'Phir se khula maano' : 'Jaan-boojh kar hai (chhodo)')),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    if (r == null) return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    final risks = _list(r['risks']);
    final areas = <String>{for (final x in risks) _s(x['area_label'])}.toList();
    final shown = _area.isEmpty ? risks : risks.where((x) => _s(x['area_label']) == _area).toList();
    final cmp = _m(r['compare']);
    final facts = _m(r['facts']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(title: Text('${_s(r['number'])} · ${_s(r['title'])}'), backgroundColor: Colors.transparent),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(14), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                _scoreBadge((r['score'] as num?)?.toInt() ?? 0),
                const SizedBox(width: 12),
                Expanded(child: Text(_s(r['say']), style: const TextStyle(color: C.ink))),
              ]),
              const SizedBox(height: 8),
              _counts(_m(r['counts'])),
              const SizedBox(height: 8),
              Wrap(spacing: 10, runSpacing: 2, children: [
                for (final k in const ['package', 'version_name', 'target_sdk', 'min_sdk', 'built_with', 'repo', 'host'])
                  if (_s(facts[k]).isNotEmpty) Text('$k: ${_s(facts[k])}', style: const TextStyle(color: C.faint, fontSize: 12)),
              ]),
              if (_list(cmp['fixed']).isNotEmpty) ...[
                const SizedBox(height: 8),
                Text('Theek hue (${_s(cmp['previous'])} ke baad)', style: const TextStyle(color: C.ok, fontWeight: FontWeight.w600)),
                for (final f in _list(cmp['fixed']).take(8)) Text('✓ ${_s(f['title'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
              ],
            ]),
          ),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            FilledButton.icon(
                onPressed: () => _call(context, widget.app, 'POST', '/api/appreview/reviews/${widget.id}/files'),
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('Report + fix list')),
            OutlinedButton.icon(
                onPressed: () async {
                  final m = await _call(context, widget.app, 'GET', '/api/appreview/reviews/${widget.id}/fixlist');
                  if (m == null) return;
                  Clipboard.setData(ClipboardData(text: _s(m['markdown'])));
                  if (context.mounted) _snack(context, 'Fix list copy ho gayi');
                },
                icon: const Icon(Icons.copy),
                label: const Text('Fix list copy')),
            OutlinedButton.icon(
                onPressed: () => _call(context, widget.app, 'POST', '/api/appreview/reviews/${widget.id}/handoff', {'to': 'devsahayak'}),
                icon: const Icon(Icons.engineering),
                label: const Text('Developer Sahayak ko do')),
            OutlinedButton.icon(
                onPressed: () => _call(context, widget.app, 'POST', '/api/appreview/reviews/${widget.id}/handoff', {'to': 'developer'}),
                icon: const Icon(Icons.send),
                label: const Text('Developer ko message')),
          ]),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              Padding(padding: const EdgeInsets.only(right: 6), child: ChoiceChip(label: const Text('Sab'), selected: _area.isEmpty, onSelected: (_) => setState(() => _area = ''))),
              for (final a in areas)
                Padding(padding: const EdgeInsets.only(right: 6), child: ChoiceChip(label: Text(a), selected: _area == a, onSelected: (_) => setState(() => _area = a))),
            ]),
          ),
          const SizedBox(height: 8),
          for (final x in shown) _risk(x),
          for (final l in ((r['limits'] as List?) ?? const [])) Text('ℹ ${_s(l)}', style: const TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// appreview_report: score, counts, top risks, compare; tap = the full review.
class AppReviewReportCard extends StatelessWidget {
  const AppReviewReportCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final top = _list(data['top']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _scoreBadge((data['score'] as num?)?.toInt() ?? 0),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('App review ${_s(data['number'])}', style: const TextStyle(color: C.faint, fontSize: 12)),
              Text(_s(data['title']), style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
            ]),
          ),
        ]),
        const SizedBox(height: 6),
        _counts(_m(data['counts'])),
        const SizedBox(height: 6),
        for (final t in top.take(4))
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.circle, size: 9, color: _sevColor(_s(t['sev']))),
              const SizedBox(width: 6),
              Expanded(child: Text(_s(t['title']), style: const TextStyle(color: C.muted, fontSize: 13))),
            ]),
          ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppReviewPage(app: app, id: _s(data['id'])))),
              child: const Text('Poori review dekho')),
        ),
      ]),
    );
  }
}

/// appreview_handoff: the fix list goes to the Developer Sahayak / her developer only on HER tap here.
class AppReviewHandoffCard extends StatefulWidget {
  const AppReviewHandoffCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<AppReviewHandoffCard> createState() => _AppReviewHandoffCardState();
}

class _AppReviewHandoffCardState extends State<AppReviewHandoffCard> {
  String _done = '';
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/appreview/handoffs/${_s(widget.data['id'])}/decide',
        {'yes': yes, 'hash': _s(widget.data['hash'])});
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r != null) _done = _s(r['status']);
    });
    final wa = _s(r?['wa']);
    if (yes && wa.isNotEmpty) Native.openExternal(url: wa);
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final tasks = _list(d['tasks']);
    final dev = _s(d['to']) == 'devsahayak';
    return Glass(
      border: _done.isEmpty ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(dev ? 'Developer Sahayak ko fix list?' : 'Developer ke liye fix list', style: const TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text(_s(d['say']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        for (final t in tasks.take(6))
          Text('${_s(t['n'])}. ${_s(t['title'])}', style: TextStyle(color: _sevColor(_s(t['severity'])), fontSize: 12.5)),
        if (tasks.length > 6) Text('... aur ${tasks.length - 6}', style: const TextStyle(color: C.faint, fontSize: 12)),
        const SizedBox(height: 8),
        if (_done.isNotEmpty)
          Text(_done == 'sent' ? 'Ho gaya' : (_done == 'rejected' ? 'Mana kiya' : 'Nahi ho paya'), style: const TextStyle(color: C.faint))
        else
          Row(children: [
            FilledButton(onPressed: _busy ? null : () => _decide(true), child: const Text('Haan')),
            const SizedBox(width: 8),
            OutlinedButton(onPressed: _busy ? null : () => _decide(false), child: const Text('Mana')),
          ]),
      ]),
    );
  }
}

/// appreview_alert: e.g. her app still targets an old Android API (Play won't take the next update).
class AppReviewAlertCard extends StatelessWidget {
  const AppReviewAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        border: C.warn,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.warning_amber_rounded, color: C.warn, size: 20),
            SizedBox(width: 6),
            Text('App review', style: TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(color: C.muted)),
          if (_s(data['id']).isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AppReviewPage(app: app, id: _s(data['id'])))),
                  child: const Text('Review kholo')),
            ),
        ]),
      );
}
