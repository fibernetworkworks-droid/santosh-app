/// Profile > Edit desk: Hoola as the video editor's professional desk on top of the Video Editor engine.
/// Aaj (late / due, client silent on review, money due, cards waiting) · Projects (brief, footage, deliverables per platform with
/// engine versions, client notes with timecodes, revision rounds vs the quote, quote / invoices / payments, delivery) · Licence
/// (music / stock register with what blocks) · Niyam (studio, GST, UPI, rounds, extra round fee, advance %, rate card).
/// The quote, invoices, review link, messages, extra charges / paid rounds, final delivery and refunds run only after HER tap
/// (refund with her fingerprint once a phone key is set up). Hoola never sends anything and never takes or pays money.
library;

import 'package:flutter/material.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());
String _rs(dynamic v) => v == null ? '[price?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Continue', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  const long = {'text', 'brief', 'terms', 'rules', 'notes', 'lines'};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: long.contains(k) ? 5 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body);
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']), mail = _s(draft['mail']), upi = _s(draft['upi']);
  if (wa.isEmpty && sms.isEmpty && mail.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (mail.isNotEmpty) GlassButton(label: 'Email', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (upi.isNotEmpty) const Pill('UPI link of your UPI ID'),
  ]);
}

/// Lines like "Reel edit, 2, 3000" -> [{what, qty, rate}] (rate blank = her rate card / a blank).
List<Map<String, dynamic>> _parseLines(String text) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split('\n')) {
    final parts = raw.split(',').map((e) => e.trim()).toList();
    if (parts.isEmpty || parts.first.isEmpty) continue;
    final row = <String, dynamic>{'what': parts.first, 'code': parts.first};
    if (parts.length > 1 && _n(parts[1]) != null) row['qty'] = _n(parts[1]);
    if (parts.length > 2 && _n(parts[2]) != null) row['rate'] = _n(parts[2]);
    out.add(row);
  }
  return out;
}

class EditdeskScreen extends StatefulWidget {
  const EditdeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<EditdeskScreen> createState() => _EditdeskScreenState();
}

class _EditdeskScreenState extends State<EditdeskScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/editdesk'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => EditdeskProjectPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Future<void> _newProject() async {
    final f = await _form(context, 'New project', const [
      ('client', 'Client name'),
      ('title', 'Project name'),
      ('brief', 'Brief (client\'s words: platform, length, date, style)'),
      ('due', 'Delivery date (optional)'),
    ], ok: 'Create');
    if (f == null || !mounted) return;
    final r = await _call(context, widget.app, 'POST', '/api/editdesk/projects', f);
    final p = _m(r?['project']);
    await _load();
    if (p.isNotEmpty) _open(_s(p['number']));
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('WAITING FOR YOUR APPROVAL'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: EditdeskCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('late', 'LATE'), ('due_soon', 'DELIVERY IN 2 DAYS'), ('review_silent', 'NO REPLY FROM CLIENT'),
        ('unpaid', 'PAYMENTS PENDING'), ('licences_soon', 'LICENCES EXPIRING')])
        if (_strs(day[k]).isNotEmpty) ...[
          Caption(label),
          for (final x in _strs(day[k])) Text('• $x', style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 8),
        ],
    ]);
  }

  Widget _projects() {
    final ps = _list(_d?['projects']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'New project', icon: Icons.add_rounded, height: 46, onTap: _newProject),
      const SizedBox(height: 12),
      if (ps.isEmpty) const Text('No projects yet.', style: TextStyle(color: C.muted)),
      for (final p in ps)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: InkWell(
            onTap: () => _open(_s(p['number'])),
            child: Row(children: [
              const Icon(Icons.movie_creation_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text('${_s(p['client'])} · ${_strs(p['deliverables']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.muted)),
                  Text('Rounds ${_s(p['rounds_used'])}/${_s(p['rounds_quoted'])}${_s(p['due']).isEmpty ? '' : ' · ${_s(p['due'])}'}',
                      style: const TextStyle(fontSize: 12, color: C.faint)),
                ]),
              ),
              Pill(_s(p['status_label'])),
            ]),
          ),
        ),
    ]);
  }

  Widget _licences() {
    final ls = _list(_d?['licences']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Keep here the licence of every song / stock clip / font used in the video. Songs from the in-app library of Instagram / YouTube'
          'cannot be used in a brand video.', style: TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 10),
      GlassButton(label: 'Add licence', icon: Icons.add_rounded, height: 42, onTap: () async {
        await addLicence(context, widget.app, '');
        _load();
      }),
      const SizedBox(height: 10),
      for (final x in ls) _licTile(x),
    ]);
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final cards = _list(st['rate_card']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['studio']).isEmpty ? 'No studio name' : _s(st['studio']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('GSTIN ${_s(st['gstin']).isEmpty ? '-' : _s(st['gstin'])} · GST ${st['gst_on'] == true ? 'on' : 'off'} · UPI ${_s(st['upi_id'])}',
              style: const TextStyle(fontSize: 12.5)),
          Text('${_s(st['rounds'])} rounds in the quote · extra round ${_rs(st['extra_round_fee'])} · advance ${_s(st['advance_pct'])}%',
              style: const TextStyle(fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Edit', icon: Icons.edit_rounded, height: 40, onTap: () async {
            final f = await _form(context, 'Rules', const [
              ('studio', 'Studio / your name'), ('gstin', 'GSTIN'), ('upi_id', 'UPI ID'), ('phone', 'Phone'), ('email', 'Email'),
              ('rounds', 'Revision rounds in the quote'), ('extra_round_fee', 'Price of an extra round (₹)'), ('advance_pct', 'Advance %'),
              ('terms', 'Your terms'),
            ], initial: {
              for (final k in ['studio', 'gstin', 'upi_id', 'phone', 'email', 'rounds', 'extra_round_fee', 'advance_pct', 'terms'])
                if (_s(st[k]).isNotEmpty) k: _s(st[k]),
            });
            if (f == null || !mounted) return;
            final body = <String, dynamic>{...f};
            for (final k in ['rounds', 'extra_round_fee', 'advance_pct']) {
              if (f[k] != null) body[k] = _n(f[k]);
            }
            await _call(context, widget.app, 'PUT', '/api/editdesk/settings', body);
            _load();
          }),
        ]),
      ),
      const SizedBox(height: 8),
      SwitchListTile(
        value: st['gst_on'] == true,
        title: const Text('Add GST (I am registered)'),
        onChanged: (v) async {
          await _call(context, widget.app, 'PUT', '/api/editdesk/settings', {'gst_on': v});
          _load();
        },
      ),
      SwitchListTile(
        value: st['hold_final_unpaid'] == true,
        title: const Text('Final files only after full payment'),
        onChanged: (v) async {
          await _call(context, widget.app, 'PUT', '/api/editdesk/settings', {'hold_final_unpaid': v});
          _load();
        },
      ),
      const Caption('RATE CARD (YOUR PRICES)'),
      for (final r in cards) Text('• ${_s(r['what'])} · ${_rs(r['rate'])} / ${_s(r['unit'])}', style: const TextStyle(fontSize: 13)),
      const SizedBox(height: 6),
      GlassButton(label: 'Write rate card', icon: Icons.price_change_rounded, height: 40, onTap: () async {
        final f = await _form(context, 'Rate card', const [('lines', 'One per line: work, price (e.g. "Reel edit, 3000")')], ok: 'Save');
        if (f == null || !mounted) return;
        final rows = <Map<String, dynamic>>[];
        for (final raw in (f['lines'] ?? '').split('\n')) {
          final p = raw.split(',').map((e) => e.trim()).toList();
          if (p.isEmpty || p.first.isEmpty) continue;
          rows.add({'what': p.first, 'rate': p.length > 1 ? _n(p[1]) : null});
        }
        await _call(context, widget.app, 'PUT', '/api/editdesk/settings', {'rate_card': rows});
        _load();
      }),
      const SizedBox(height: 12),
      for (final x in _strs(st['notes'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(x, style: const TextStyle(fontSize: 11.5, color: C.faint))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Today', 'Projects', 'Licence', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Edit desk'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: Column(children: [
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i))),
          ]),
        ),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _projects, _licences, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

Widget _licTile(Map<String, dynamic> x) => Glass(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(x['ok'] == true ? Icons.verified_rounded : Icons.block_rounded, color: x['ok'] == true ? C.ok : C.bad, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · ${_s(x['title'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
          Pill(_s(x['kind'])),
        ]),
        Text('${_s(x['source'])} · ${_s(x['type_label'])}${_s(x['expires']).isEmpty ? '' : ' · until ${_s(x['expires'])}'}',
            style: const TextStyle(fontSize: 12, color: C.muted)),
        for (final b in _strs(x['blockers'])) Text('✗ $b', style: const TextStyle(fontSize: 12, color: C.bad)),
        for (final w in _strs(x['warnings'])) Text('! $w', style: const TextStyle(fontSize: 11.5, color: C.warn)),
      ]),
    );

Future<void> addLicence(BuildContext context, Santosh app, String project) async {
  final f = await _form(context, 'Licence', const [
    ('title', 'Song / clip / font name'),
    ('kind', 'What: music / stock_video / stock_photo / sfx / font'),
    ('source', 'From where (Artlist, Epidemic, Pixabay, given by client ...)'),
    ('licence_type', 'Type: royalty_free / subscription / sync / cc / client_owned / own / platform_only'),
    ('licence_ref', 'Licence / order number'),
    ('expires', 'Valid until (optional)'),
    ('file_id', 'file_id of the music file (optional)'),
  ], ok: 'Save');
  if (f == null || !context.mounted) return;
  await _call(context, app, 'POST', '/api/editdesk/licences', {...f, if (project.isNotEmpty) 'project': project});
}

class EditdeskProjectPage extends StatefulWidget {
  const EditdeskProjectPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<EditdeskProjectPage> createState() => _EditdeskProjectPageState();
}

class _EditdeskProjectPageState extends State<EditdeskProjectPage> {
  Map<String, dynamic>? _p;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _base => '/api/editdesk/projects/${Uri.encodeComponent(widget.ref)}';

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('POST', '$_base/sync'));
      if (mounted) setState(() => _p = _m(r['project']));
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

  Widget _deliverable(Map<String, dynamic> d) {
    final vs = _list(d['versions']);
    final active = ['queued', 'watching', 'planning', 'rendering', 'checking'].contains(_s(d['job_status']));
    return Glass(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.crop_portrait_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(d['label']), style: const TextStyle(fontWeight: FontWeight.w700))),
          Pill(_s(d['status'])),
        ]),
        if (active) ...[
          const SizedBox(height: 6),
          LinearProgressIndicator(value: ((d['progress'] as num?) ?? 0) / 100),
          Text(_s(d['job_stage']), style: const TextStyle(fontSize: 12, color: C.muted)),
        ],
        for (final v in vs)
          Text('v${_s(v['n'])}${d['approved_n'] == v['n'] ? ' · client OK' : ''}${_s(v['change']).isEmpty ? '' : ' · ${_s(v['change'])}'}',
              style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (_s(d['job_id']).isEmpty)
            GlassButton(label: 'Edit started', icon: Icons.play_arrow_rounded, height: 38,
                onTap: _busy ? null : () => _run('POST', '$_base/edit', {'deliverable': d['id']})),
          if (vs.isNotEmpty)
            GlassButton(label: 'Client approved', icon: Icons.thumb_up_rounded, height: 38,
                onTap: _busy ? null : () => _run('POST', '$_base/client_ok', {'deliverable': d['id']})),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.ref),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: p == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                Text(_s(p['title']), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                Text('${_s(_m(p['client'])['name'])} · ${_s(p['kind_label'])} · ${_s(p['status_label'])}'
                    '${_s(p['due']).isEmpty ? '' : ' · until ${_s(p['due'])}'}', style: const TextStyle(color: C.muted)),
                const SizedBox(height: 8),
                Pill('Revision rounds ${_s(p['rounds_used'])} / ${_s(p['rounds_quoted'])} · ${_s(p['rounds_left'])} left', fg: C.accent),
                const SizedBox(height: 10),
                for (final c in _list(p['cards']))
                  Padding(padding: const EdgeInsets.only(bottom: 10), child: EditdeskCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
                if (_strs(p['questions']).isNotEmpty) ...[
                  const Caption('PENDING IN THE BRIEF'),
                  for (final q in _strs(p['questions'])) Text('• $q', style: const TextStyle(fontSize: 12.5)),
                  const SizedBox(height: 8),
                ],
                GlassButton(label: 'Add to brief', icon: Icons.notes_rounded, height: 40, onTap: () async {
                  final f = await _form(context, 'Brief', const [('brief', 'Client\'s words (data)')], ok: 'Add');
                  if (f != null) await _run('PATCH', _base, f);
                }),
                const SizedBox(height: 12),
                const Caption('DELIVERABLES (HAR PLATFORM)'),
                for (final d in _list(p['deliverables'])) _deliverable(d),
                GlassButton(label: 'Add platform', icon: Icons.add_rounded, height: 38, onTap: () async {
                  final f = await _form(context, 'Platform', const [('platform', 'reel / short / status / youtube / square / portrait')]);
                  if (f != null && f['platform'] != null) await _run('PATCH', _base, {'platforms': [f['platform']]});
                }),
                const SizedBox(height: 12),
                const Caption('FOOTAGE CHECKLIST'),
                for (final x in _list(p['footage']))
                  CheckboxListTile(
                    dense: true,
                    value: x['have'] == true,
                    title: Text(_s(x['item'])),
                    onChanged: (v) => _run('POST', '$_base/footage', {'item': x['item'], 'have': v == true}),
                  ),
                Text('Footage files: ${_strs(p['files']).length} '
                    '(attach it in chat and say "add to this project")', style: const TextStyle(fontSize: 12, color: C.faint)),
                const SizedBox(height: 12),
                const Caption('CLIENT NOTES'),
                for (final c in _list(p['comments']))
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Text(_s(c['at']).isEmpty ? '—' : _s(c['at']), style: const TextStyle(fontWeight: FontWeight.w700, color: C.accent)),
                    title: Text(_s(c['text'])),
                    subtitle: Text('${_s(c['status'])}${c['scope'] == 'extra' ? ' · outside the quote?' : ''}'
                        '${(c['round'] ?? 0) != 0 ? ' · round ${_s(c['round'])}' : ''}'),
                    trailing: _s(c['status']) == 'sent'
                        ? IconButton(icon: const Icon(Icons.check_rounded),
                            onPressed: () => _run('PATCH', '/api/editdesk/comments/${_s(c['id'])}', {'status': 'done'}))
                        : null,
                  ),
                Wrap(spacing: 8, runSpacing: 6, children: [
                  GlassButton(label: 'Add client notes', icon: Icons.rate_review_rounded, height: 40, onTap: () async {
                    final f = await _form(context, 'Client notes', const [('text', 'One per line: 0:15 make the logo smaller')], ok: 'Add');
                    if (f != null) await _run('POST', '$_base/comments', f);
                  }),
                  GradientButton(label: 'Run the change round', icon: Icons.autorenew_rounded, height: 40,
                      onTap: _busy ? null : () => _run('POST', '$_base/revise', {})),
                  GlassButton(label: 'Free round do', height: 40, onTap: _busy ? null : () => _run('POST', '$_base/revise', {'free': true})),
                ]),
                const SizedBox(height: 12),
                const Caption('LICENCE'),
                for (final x in _list(p['licences'])) _licTile(x),
                GlassButton(label: 'Add licence', icon: Icons.library_music_rounded, height: 38, onTap: () async {
                  await addLicence(context, widget.app, _s(p['number']));
                  _load();
                }),
                const SizedBox(height: 12),
                const Caption('MONEY'),
                _money(p),
                const SizedBox(height: 12),
                const Caption('TO THE CLIENT (WITH YOUR APPROVAL)'),
                Wrap(spacing: 8, runSpacing: 6, children: [
                  GlassButton(label: 'Review link', icon: Icons.link_rounded, height: 40, onTap: () => _run('POST', '$_base/review', {})),
                  GlassButton(label: 'Message', icon: Icons.chat_rounded, height: 40, onTap: () async {
                    final f = await _form(context, 'Message to client', const [('text', 'Message')]);
                    if (f != null) await _run('POST', '$_base/message', f);
                  }),
                  GradientButton(label: 'Final delivery', icon: Icons.send_rounded, height: 40, onTap: () => _run('POST', '$_base/deliver')),
                  GlassButton(label: 'Cancel', icon: Icons.cancel_rounded, height: 40, color: C.bad, onTap: () async {
                    final f = await _form(context, 'Cancel', const [('reason', 'Reason'), ('refund', 'Refund ₹ (optional)')], ok: 'Cancel');
                    if (f != null) await _run('POST', '$_base/cancel', {'reason': f['reason'], 'refund': _n(f['refund'])});
                  }),
                ]),
                const SizedBox(height: 12),
                for (final x in _strs(p['notes'])) Padding(padding: const EdgeInsets.only(bottom: 6),
                    child: Text(x, style: const TextStyle(fontSize: 11, color: C.faint))),
              ]),
            ),
    );
  }

  Widget _money(Map<String, dynamic> p) {
    final m = _m(p['money']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Agreed: ${_s(m['agreed_text'])} · Received: ${_rs(m['received'])} · Due: ${_rs(m['balance'])}',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        for (final q in _list(p['quotes'])) Text('Quote ${_s(q['number'])} · ${_s(q['total_text'])} · ${_s(q['status'])}', style: const TextStyle(fontSize: 12.5)),
        for (final i in _list(p['invoices']))
          Text('${_s(i['number'])} (${_s(i['kind'])}) ${_rs(i['total'])} · ${_s(i['status'])} · mile ${_rs(i['received'])}', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: 'Make quote', icon: Icons.request_quote_rounded, height: 38, onTap: () async {
            final f = await _form(context, 'Quote', const [
              ('lines', 'One per line: work, qty, price (empty price = rate card)'), ('rounds', 'Revision rounds'),
            ], ok: 'Draft');
            if (f == null) return;
            await _run('POST', '$_base/quote', {'lines': _parseLines(f['lines'] ?? ''), if (f['rounds'] != null) 'rounds': _n(f['rounds'])});
          }),
          GlassButton(label: 'Send quote', height: 38, onTap: () => _run('POST', '$_base/quote_send')),
          GlassButton(label: 'Client accepted the quote', height: 38, onTap: () => _run('POST', '$_base/quote_accept')),
          GlassButton(label: 'Ask for advance', height: 38, onTap: () => _run('POST', '$_base/invoice', {'kind': 'advance'})),
          GlassButton(label: 'Final invoice', height: 38, onTap: () => _run('POST', '$_base/invoice', {'kind': 'final'})),
          GlassButton(label: 'Extra charge', height: 38, onTap: () async {
            final f = await _form(context, 'Extra work', const [('what', 'What work'), ('amount', 'Price ₹')]);
            if (f != null) await _run('POST', '$_base/charge', {'what': f['what'], 'amount': _n(f['amount'])});
          }),
          GradientButton(label: 'Money received', icon: Icons.currency_rupee_rounded, height: 38, onTap: () async {
            final f = await _form(context, 'Money received', const [('amount', 'How many ₹ received'), ('tds', 'TDS deducted ₹ (optional)'), ('utr', 'UTR (optional)')]);
            if (f != null) await _run('POST', '$_base/paid', {'amount': _n(f['amount']), 'tds': _n(f['tds']), 'utr': f['utr']});
          }),
        ]),
      ]),
    );
  }
}

/// editdesk_card: quote / invoice / review / message / extra / delivery / refund waiting for HER tap.
class EditdeskCardCard extends StatefulWidget {
  const EditdeskCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<EditdeskCardCard> createState() => _EditdeskCardCardState();
}

class _EditdeskCardCardState extends State<EditdeskCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/editdesk/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Refund' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'No fingerprint given, so it was not approved.',
        'key_invalidated' => 'A new fingerprint was added to the phone: re-link this phone in Profile > Fingerprint approval.',
        _ => 'Could not approve with fingerprint (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not?', const [('reason', 'Reason (optional)')], ok: 'No');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/editdesk/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/editdesk/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
          _draft = _m(m['draft']);
        });
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c, sh = _m(c['show']);
    final st = _s(c['status']), kind = _s(c['kind']);
    final money = c['money'] == true;
    final amount = _s(sh['amount_text']).isNotEmpty ? _s(sh['amount_text']) : _s(sh['total_text']);
    final blockers = _strs(sh['blockers']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'quote' => Icons.request_quote_rounded, 'invoice' => Icons.receipt_long_rounded, 'review' => Icons.rate_review_rounded,
            'extra' => Icons.add_circle_rounded, 'delivery' => Icons.send_rounded, 'refund' => Icons.undo_rounded, _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['project'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'stale', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['client'])} · ${_s(sh['title'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(sh['what']).isNotEmpty) Text(_s(sh['what'])),
        if (kind == 'quote') Text('${_s(sh['rounds'])} revision rounds · advance ${_s(sh['advance_pct'])}% · until ${_s(sh['valid_until'])}',
            style: const TextStyle(fontSize: 12)),
        for (final v in _list(sh['versions'])) Text('• ${_s(v['label'])}', style: const TextStyle(fontSize: 12)),
        for (final f in _list(sh['files'])) Text('• ${_s(f['label'])} v${_s(f['n'])}', style: const TextStyle(fontSize: 12)),
        for (final b in blockers) Text('✗ $b', style: const TextStyle(fontSize: 12, color: C.bad)),
        for (final w in _strs(sh['warnings'])) Text('! $w', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        if (_s(sh['why']).isNotEmpty) Text(_s(sh['why']), style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Yes (fingerprint)' : 'Yes', height: 42,
                onTap: (_busy || blockers.isNotEmpty) ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola does not send anything or take or give money: you send the messages.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// editdesk_note / editdesk_alert / editdesk_day: new version ready, due / late, client silent, unpaid, licence ending, morning note.
class EditdeskNoteCard extends StatelessWidget {
  const EditdeskNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final project = _s(data['project']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.movie_creation_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          if (project.isNotEmpty)
            TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => EditdeskProjectPage(app: app, ref: project))),
              child: Text('Open $project'),
            ),
        ])),
      ]),
    );
  }
}
