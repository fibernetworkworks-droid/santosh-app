/// Profile > DPO Sahayak: Hoola as the business's data protection officer (DPDP Act 2023 + DPDP Rules 2025).
/// Aaj (cards waiting for her, breach clocks, requests due) · Register (records of processing, pre-filled from her Hoola modules,
/// DPIA) · Notice (Rule 3 privacy notice in Hindi / Marathi / English) · Maang (rights requests with the 90-day clock, identity by
/// method only, reply / erasure cards) · Breach (Board 72 h report + people + CERT-In via IT Helpdesk) · Vendor (DPA clauses) ·
/// Niyam (settings, phases, penalties, sources).
/// Publishing a notice, replying, erasing (fingerprint once a phone key is set up) and breach notices run ONLY after HER tap.
/// Everything is "jaankari", not legal advice.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();

const _disclaimer = 'This is a draft / information, not legal advice. Confirm it with a lawyer / CA / CS.';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Next', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  const multi = {'text', 'body', 'notes', 'nature', 'extent', 'impact', 'measures', 'safety', 'cause', 'findings', 'remedial',
    'details', 'consequences', 'people_report', 'affected', 'items', 'processors', 'purpose', 'rules'};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: multi.contains(k) ? 3 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

List<String> _lines(String? v) => (v ?? '').split(RegExp(r'[\n,]')).map((x) => x.trim()).where((x) => x.isNotEmpty).toList();

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

class DpoScreen extends StatefulWidget {
  const DpoScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DpoScreen> createState() => _DpoScreenState();
}

class _DpoScreenState extends State<DpoScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic> _law = {};
  List<Map<String, dynamic>> _retention = [];
  List<Map<String, dynamic>> _consents = [];
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = widget.app.api!;
      final d = _m(await api.call('GET', '/api/dpo'));
      final law = _m(await api.call('GET', '/api/dpo/law'));
      final rt = _m(await api.call('GET', '/api/dpo/retention'));
      final cs = _m(await api.call('GET', '/api/dpo/consents'));
      if (mounted) {
        setState(() {
          _d = d;
          _law = law;
          _retention = _list(rt['retention']);
          _consents = _list(cs['consents']);
        });
      }
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

  // ---------------------------------------------------------------- actions
  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'DPO details', const [
      ('org', 'Business name (Data Fiduciary)'),
      ('contact_name', 'Person who replies (DPO / contact person)'),
      ('contact_email', 'Their email'),
      ('contact_phone', 'Their mobile'),
      ('link', 'Link to withdraw consent / make a request (https://)'),
      ('identifiers', 'How you will verify identity (e.g. registered mobile)'),
      ('reply_days', 'Days to reply (max 90)'),
      ('morning_time', 'Morning note (HH:MM)'),
      ('rules', 'Your rules'),
    ], ok: 'Save', initial: {for (final e in st.entries) if (e.value != null && e.value is! Map && e.value is! List) e.key: '${e.value}'});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['reply_days'] != null) body['reply_days'] = int.tryParse(f['reply_days']!) ?? 30;
    await _run('PUT', '/api/dpo/settings', body);
  }

  Future<void> _activity([Map<String, dynamic>? a]) async {
    final f = await _form(context, a == null ? 'New activity (processing)' : 'Change ${_s(a['number'])}', const [
      ('name', 'Activity name'),
      ('people', 'Whose data (customers / staff / children)'),
      ('items', 'Which data (comma separated)'),
      ('purpose', 'For what purpose'),
      ('basis', 'Aadhaar: consent / voluntary / employment / law / emergency'),
      ('retention', 'How long to keep (in words)'),
      ('retention_days', 'In days (for review)'),
      ('processors', 'Who processes it (comma separated)'),
    ], ok: 'Save', initial: a == null
        ? const {}
        : {
            'name': _s(a['name']),
            'people': _s(a['people']),
            'items': _strs(a['items']).join(', '),
            'purpose': _s(a['purpose']),
            'basis': _s(a['basis']),
            'retention': _s(a['retention']),
            'retention_days': _s(a['retention_days']),
            'processors': _strs(a['processors']).join(', '),
          });
    if (f == null) return;
    final body = <String, dynamic>{...f, 'confirmed': true};
    if (f['items'] != null) body['items'] = _lines(f['items']);
    if (f['processors'] != null) body['processors'] = _lines(f['processors']);
    if (f['retention_days'] != null) body['retention_days'] = int.tryParse(f['retention_days']!);
    if (a == null) {
      await _run('POST', '/api/dpo/activities', body);
    } else {
      await _run('PATCH', '/api/dpo/activities/${_s(a['id'])}', body);
    }
  }

  Future<void> _dpia(Map<String, dynamic> a) async {
    final qs = _list(_law['dpia']);
    final ans = <String, bool>{};
    for (final q in qs) {
      final prev = _m(_m(a['dpia'])['answers']);
      ans[_s(q['key'])] = prev[_s(q['key'])] == true;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: Text('DPIA: ${_s(a['number'])}'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              for (final q in qs)
                CheckboxListTile(
                  dense: true,
                  value: ans[_s(q['key'])] ?? false,
                  title: Text(_s(q['q']), style: const TextStyle(fontSize: 13)),
                  onChanged: (v) => set(() => ans[_s(q['key'])] = v ?? false),
                ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('View risks')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    await _run('POST', '/api/dpo/activities/${_s(a['id'])}/dpia', {'answers': ans});
  }

  Future<void> _newNotice() async {
    final lang = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, l) in const [('hi', 'हिन्दी'), ('mr', 'मराठी'), ('en', 'English')])
            ListTile(title: Text(l), onTap: () => Navigator.pop(context, k)),
        ]),
      ),
    );
    if (lang == null) return;
    await _run('POST', '/api/dpo/notices', {'lang': lang});
  }

  Future<void> _editNotice(Map<String, dynamic> n) async {
    final c = TextEditingController(text: _s(n['text']));
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('Notice v${_s(n['version'])}'),
        content: SizedBox(width: 500, child: TextField(controller: c, maxLines: 18)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok == true) await _run('PATCH', '/api/dpo/notices/${_s(n['id'])}', {'text': c.text});
  }

  Future<void> _newRequest() async {
    final f = await _form(context, 'New request (data principal)', const [
      ('text', 'Their words (e.g. "delete my data")'),
      ('name', 'Name'),
      ('phone', 'Registered mobile'),
      ('email', 'Email (if any)'),
      ('via', 'How it came (WhatsApp / email / shop)'),
      ('received', 'When received (YYYY-MM-DD, blank = today)'),
    ], ok: 'Save');
    if (f == null || ((f['text'] ?? '').isEmpty)) return;
    await _run('POST', '/api/dpo/requests', f);
  }

  Future<void> _newBreach() async {
    final f = await _form(context, 'Record a data breach', const [
      ('title', 'What happened (one line)'),
      ('aware', 'When you found out (YYYY-MM-DD HH:MM, blank = now)'),
      ('nature', 'What kind (theft / hack / sent by mistake)'),
      ('extent', 'How many people / which data'),
      ('when', 'When it happened'),
      ('location', 'Where / which system'),
      ('impact', 'Possible impact'),
      ('affected', 'Mobile / email of affected people (comma separated)'),
    ], ok: 'Save');
    if (f == null || (f['title'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f, 'cert_in': true};
    body['affected'] = _lines(f['affected']);
    await _run('POST', '/api/dpo/breaches', body);
  }

  Future<void> _newConsent() async {
    final f = await _form(context, 'Record consent', const [
      ('name', 'Name'),
      ('phone', 'Mobile'),
      ('activities', 'Activities (PA-01, PA-02)'),
      ('how', 'How it was taken (form / WhatsApp / paper)'),
      ('proof', 'Evidence reference'),
      ('child', 'Is it a child? (yes / no)'),
      ('parent_name', 'Parent\'s name (for the child)'),
      ('parent_check', 'How it was verified + reference (not the ID number)'),
    ], ok: 'Save');
    if (f == null) return;
    final body = <String, dynamic>{...f, 'activities': _lines(f['activities']), 'child': (f['child'] ?? '').toLowerCase().startsWith('h')};
    await _run('POST', '/api/dpo/consents', body);
  }

  Future<void> _vendor([Map<String, dynamic>? v]) async {
    final clauses = _list(_law['dpa']);
    final f = await _form(context, v == null ? 'New vendor (processor)' : _s(v['name']), const [
      ('name', 'Name'),
      ('service', 'What it does'),
      ('items', 'Which data goes there'),
      ('country', 'Data is in which country'),
      ('dpa_on', 'Contract (DPA) signed on (YYYY-MM-DD)'),
      ('review_on', 'Review on (YYYY-MM-DD)'),
    ], ok: 'Next', initial: v == null
        ? const {}
        : {'name': _s(v['name']), 'service': _s(v['service']), 'items': _strs(v['items']).join(', '), 'country': _s(v['country']),
            'dpa_on': _s(v['dpa_on']), 'review_on': _s(v['review_on'])});
    if (f == null || !mounted) return;
    final prev = _m(v?['clauses']);
    final cl = {for (final c in clauses) _s(c['key']): prev[_s(c['key'])] == true};
    bool signed = v?['dpa_signed'] == true;
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('What is in the contract (DPA)'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              SwitchListTile(value: signed, title: const Text('DPA signed'), onChanged: (x) => set(() => signed = x)),
              for (final c in clauses)
                CheckboxListTile(
                    dense: true,
                    value: cl[_s(c['key'])] ?? false,
                    title: Text(_s(c['text']), style: const TextStyle(fontSize: 12.5)),
                    onChanged: (x) => set(() => cl[_s(c['key'])] = x ?? false)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    await _run('POST', '/api/dpo/vendors', {
      if (v != null) 'vendor': _s(v['id']),
      ...f,
      'items': _lines(f['items']),
      'dpa_signed': signed,
      'clauses': cl,
    });
  }

  // ---------------------------------------------------------------- tabs
  Widget _cardsList(List<Map<String, dynamic>> cards) => Column(children: [
        for (final c in cards) ...[DpoCardCard(app: widget.app, data: {'card': c}, onDone: _load), const SizedBox(height: 8)],
      ]);

  Widget _todayTab() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 8),
      for (final p in _strs(day['phases'])) Text('ℹ $p', style: const TextStyle(fontSize: 12, color: C.muted)),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: GradientButton(label: 'New request', icon: Icons.person_search_rounded, height: 46, onTap: _busy ? null : _newRequest)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Breach', icon: Icons.warning_amber_rounded, color: C.bad, onTap: _busy ? null : _newBreach)),
      ]),
      const SizedBox(height: 12),
      if (_list(day['cards']).isNotEmpty) ...[const Caption('NEEDS YOUR YES'), _cardsList(_list(day['cards']))],
      if (_list(day['breaches']).isNotEmpty) ...[
        const Caption('OPEN BREACHES'),
        for (final b in _list(day['breaches'])) DpoBreachCard(app: widget.app, data: {'breach': b}),
      ],
      if (_list(day['requests']).isNotEmpty) ...[
        const Caption('OPEN REQUESTS'),
        for (final r in _list(day['requests'])) DpoRequestCard(app: widget.app, data: {'request': r}),
      ],
      const SizedBox(height: 8),
      const Text(_disclaimer, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _registerTab() {
    final acts = _list(_d?['activities']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(
            child: GradientButton(
                label: 'Fill from modules', icon: Icons.auto_fix_high_rounded, height: 46, onTap: _busy ? null : () => _run('POST', '/api/dpo/scan'))),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'New activity', icon: Icons.add_rounded, onTap: _busy ? null : () => _activity())),
      ]),
      const SizedBox(height: 8),
      GlassButton(label: 'Full register (Excel)', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/register')),
      const SizedBox(height: 12),
      for (final a in acts)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: _strs(a['checks']).isNotEmpty ? C.warn : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(a['number'])} · ${_s(a['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                if (a['children'] == true) const Pill('children', fg: C.bad),
                if ((a['records'] ?? 0) > 0) Pill('${_s(a['records'])} record'),
              ]),
              Text('${_s(a['people'])} · ${_strs(a['items']).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
              Text('Purpose: ${_s(a['purpose'])}', style: const TextStyle(fontSize: 12.5)),
              Text(_s(a['basis_label']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
              Text('Retention: ${_s(a['retention'])}', style: const TextStyle(fontSize: 12)),
              if (_strs(a['processors']).isNotEmpty) Text('Processors: ${_strs(a['processors']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.muted)),
              if (_s(_m(a['dpia'])['level']).isNotEmpty) Text('DPIA: ${_s(_m(a['dpia'])['level'])}', style: const TextStyle(fontSize: 12, color: C.teal)),
              for (final c in _strs(a['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12, color: C.warn)),
              const SizedBox(height: 6),
              Wrap(spacing: 6, children: [
                if (a['confirmed'] != true)
                  TextButton(
                      onPressed: _busy ? null : () => _run('PATCH', '/api/dpo/activities/${_s(a['id'])}', {'confirmed': true}),
                      child: const Text('Correct')),
                TextButton(onPressed: _busy ? null : () => _activity(a), child: const Text('Change')),
                TextButton(onPressed: _busy ? null : () => _dpia(a), child: const Text('DPIA')),
              ]),
            ]),
          ),
        ),
      if (acts.isEmpty) const Text('The register is empty. Tap "Fill from modules": Hoola will see which activities hold people\'s data.',
          style: TextStyle(color: C.muted)),
      if (_retention.any((r) => (r['older'] ?? 0) > 0)) ...[
        const SizedBox(height: 12),
        const Caption('RETENTION REVIEW'),
        for (final r in _retention.where((r) => (r['older'] ?? 0) > 0))
          Text('${_s(r['activity'])} ${_s(r['name'])}: ${_s(r['say'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      ],
    ]);
  }

  Widget _noticeTab() {
    final ns = _list(_d?['notices']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'New notice (Rule 3)', icon: Icons.policy_rounded, height: 46, onTap: _busy ? null : _newNotice),
      const SizedBox(height: 12),
      for (final n in ns)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: n['status'] == 'published' ? C.ok : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('v${_s(n['version'])} · ${_s(n['lang_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(n['status']), fg: n['status'] == 'published' ? C.ok : C.chip),
              ]),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
                child: Text(_s(n['text']), style: const TextStyle(fontSize: 12.5, height: 1.35), maxLines: 14, overflow: TextOverflow.ellipsis),
              ),
              if (n['blanks'] == true) const Text('⚠ [____] still blank: fill in the name / link / contact in Rules or write it yourself.',
                  style: TextStyle(fontSize: 12, color: C.warn)),
              Wrap(spacing: 6, children: [
                if (n['status'] == 'draft' || n['status'] == 'rejected') ...[
                  TextButton(onPressed: _busy ? null : () => _editNotice(n), child: const Text('Write it myself')),
                  TextButton(
                      onPressed: _busy || n['blanks'] == true ? null : () => _run('POST', '/api/dpo/notices/${_s(n['id'])}/publish'),
                      child: const Text('Card for your yes')),
                ],
                TextButton(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: _s(n['text'])));
                      _snack(context, 'Copied.');
                    },
                    child: const Text('Copy')),
              ]),
            ]),
          ),
        ),
    ]);
  }

  Widget _requestsTab() {
    final rs = _list(_d?['requests']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: GradientButton(label: 'New request', icon: Icons.person_search_rounded, height: 46, onTap: _busy ? null : _newRequest)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Consent', icon: Icons.how_to_reg_rounded, onTap: _busy ? null : _newConsent)),
      ]),
      const SizedBox(height: 12),
      for (final r in rs)
        Press(
          onTap: () => Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => DpoRequestPage(app: widget.app, id: _s(r['id']))))
              .then((_) => _load()),
          child: DpoRequestCard(app: widget.app, data: {'request': r}),
        ),
      if (_consents.isNotEmpty) ...[
        const SizedBox(height: 12),
        const Caption('CONSENT RECORD'),
        for (final c in _consents.take(40))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(c['status'] == 'active' ? Icons.check_circle_rounded : Icons.remove_circle_rounded,
                color: c['status'] == 'active' ? C.ok : C.faint),
            title: Text('${_s(c['name'])} ${_s(c['phone'])}${c['child'] == true ? ' · child' : ''}'),
            subtitle: Text('${_s(c['how'])} · ${_s(c['given_at']).split('T').first}${_s(c['withdrawn_at']).isEmpty ? '' : ' · withdrawn'}'),
            trailing: c['status'] == 'active'
                ? TextButton(
                    onPressed: _busy ? null : () => _run('POST', '/api/dpo/consents/withdraw', {'consent': _s(c['id']), 'how': 'app'}),
                    child: const Text('Returned'))
                : null,
          ),
      ],
    ]);
  }

  Widget _breachTab() {
    final bs = _list(_d?['breaches']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GlassButton(label: 'Record breach', icon: Icons.warning_amber_rounded, color: C.bad, onTap: _busy ? null : _newBreach),
      const SizedBox(height: 6),
      const Text('Tell the Board without delay, with the full report in 72 hours; tell the people affected without delay. For a cyber attack, CERT-In within 6 hours '
          '(clock in IT Helpdesk).', style: TextStyle(fontSize: 12, color: C.muted)),
      const SizedBox(height: 12),
      for (final b in bs)
        Press(
          onTap: () => Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => DpoBreachPage(app: widget.app, id: _s(b['id']))))
              .then((_) => _load()),
          child: DpoBreachCard(app: widget.app, data: {'breach': b}),
        ),
    ]);
  }

  Widget _vendorTab() {
    final vs = _list(_d?['vendors']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Add vendor', icon: Icons.handshake_rounded, height: 46, onTap: _busy ? null : () => _vendor()),
      const SizedBox(height: 12),
      for (final v in vs)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => _vendor(v),
            child: Glass(
              padding: const EdgeInsets.all(12),
              border: v['dpa_signed'] == true && _strs(v['missing']).isEmpty ? C.ok : C.warn,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(_s(v['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                  Pill(v['dpa_signed'] == true ? 'DPA in place' : 'No DPA', fg: v['dpa_signed'] == true ? C.ok : C.warn),
                ]),
                Text('${_s(v['service'])} · ${_s(v['country'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                if (v['abroad'] == true) const Text('Data is outside India: get the country written into the contract.', style: TextStyle(fontSize: 12, color: C.warn)),
                for (final m in _strs(v['missing']).take(4)) Text('• pending: $m', style: const TextStyle(fontSize: 11.5, color: C.faint)),
              ]),
            ),
          ),
        ),
    ]);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['org']).isEmpty ? 'No business name given' : _s(st['org']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Contact: ${[st['contact_name'], st['contact_email'], st['contact_phone']].where((x) => _s(x).isNotEmpty).join(', ')}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text('Link: ${_s(st['link'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text('Reply: ${_s(st['reply_days'])} days (legal max 90)', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text(_s(st['sdf_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          for (final m in _strs(st['missing'])) Text('⚠ pending: $m', style: const TextStyle(fontSize: 12, color: C.warn)),
          const SizedBox(height: 8),
          GlassButton(label: 'Change', icon: Icons.edit_rounded, onTap: _busy ? null : _settings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('NEVER'),
      for (final n in _strs(_law['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 12),
      const Caption('PENALTY (MAXIMUM)'),
      for (final p in (_law['penalties'] as List? ?? const []))
        if (p is List && p.length >= 2) Text('• ${p[0]}: ${p[1]}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 12),
      const Caption('SOURCES'),
      for (final s in _list(_law['sources']))
        InkWell(
          onTap: _s(s['url']).isEmpty ? null : () => Native.openExternal(url: _s(s['url'])),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text('${_s(s['what'])} (${_s(s['date'])})', style: TextStyle(fontSize: 11.5, color: _s(s['url']).isEmpty ? C.faint : C.teal)),
          ),
        ),
      const SizedBox(height: 8),
      const Text(_disclaimer, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Today', 'Register', 'Notice', 'Request', 'Breach', 'Vendor', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Data protection officer'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: Column(children: [
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ),
          ]),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: switch (_tab) {
                    0 => _todayTab(),
                    1 => _registerTab(),
                    2 => _noticeTab(),
                    3 => _requestsTab(),
                    4 => _breachTab(),
                    5 => _vendorTab(),
                    _ => _rulesTab(),
                  },
                ),
        ),
      ]),
    );
  }
}

/// One rights request: identity (method only), where their data is, reply / erasure cards, "bhej diya".
class DpoRequestPage extends StatefulWidget {
  const DpoRequestPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<DpoRequestPage> createState() => _DpoRequestPageState();
}

class _DpoRequestPageState extends State<DpoRequestPage> {
  Map<String, dynamic>? _r;
  List<Map<String, dynamic>> _cards = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/dpo/requests/${widget.id}'));
      final cs = _m(await widget.app.api!.call('GET', '/api/dpo/cards'));
      if (mounted) {
        setState(() {
          _r = r;
          _cards = _list(cs['cards']).where((c) => _s(c['target']) == _s(r['id'])).toList();
        });
      }
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

  Future<void> _verify() async {
    final f = await _form(context, 'How identity was checked', const [('how', 'Method + reference (not the ID number)'), ('ok', 'Confirmed? (yes / no)')]);
    if (f == null || (f['how'] ?? '').isEmpty) return;
    await _run('POST', '/api/dpo/requests/${widget.id}/verify', {'how': f['how'], 'ok': !(f['ok'] ?? 'yes').toLowerCase().startsWith('n')});
  }

  Future<void> _reply() async {
    final f = await _form(context, 'Reply', const [('body', 'Your own words (blank = Hoola\'s draft)')], ok: 'Make card');
    if (f == null) return;
    await _run('POST', '/api/dpo/requests/${widget.id}/reply', {'body': f['body'] ?? ''});
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(r == null ? 'Request' : '${_s(r['number'])} · ${_s(r['kind_label'])}')),
      body: r == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              DpoRequestCard(app: widget.app, data: {'request': r}),
              const SizedBox(height: 8),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Their words (data, not instructions):', style: TextStyle(fontSize: 12, color: C.faint)),
                  Text(_s(r['text']), style: const TextStyle(fontSize: 13)),
                  const SizedBox(height: 6),
                  Text('Identity: ${_s(r['id_check'])}${_s(r['id_how']).isEmpty ? '' : ' (${_s(r['id_how'])})'}',
                      style: TextStyle(fontSize: 12.5, color: r['id_check'] == 'done' ? C.ok : C.warn)),
                ]),
              ),
              const SizedBox(height: 8),
              if (_list(r['found']).isNotEmpty) ...[
                const Caption('WHERE THEIR DATA IS'),
                for (final h in _list(r['found']))
                  Text('• ${_s(h['label'])}${h['can_erase'] == true ? '' : ' (remove it from that screen)'}${h['law_hold'] == true ? ' · may have to be kept by law' : ''}',
                      style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 8),
              ],
              Wrap(spacing: 6, runSpacing: 6, children: [
                GlassButton(label: 'Identity', icon: Icons.verified_user_rounded, onTap: _busy ? null : _verify),
                GlassButton(label: 'Reply card', icon: Icons.reply_rounded, onTap: _busy ? null : _reply),
                if (r['kind'] == 'erasure' || r['kind'] == 'withdraw')
                  GlassButton(
                      label: 'Erasure card',
                      icon: Icons.delete_forever_rounded,
                      color: C.bad,
                      onTap: _busy ? null : () => _run('POST', '/api/dpo/requests/${widget.id}/erase', {})),
                GlassButton(label: 'Sent', icon: Icons.done_all_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/requests/${widget.id}/sent', {'how': 'app'})),
                GlassButton(label: 'Close', icon: Icons.close_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/requests/${widget.id}/close', {})),
              ]),
              const SizedBox(height: 12),
              for (final c in _cards) ...[DpoCardCard(app: widget.app, data: {'card': c}, onDone: _load), const SizedBox(height: 8)],
              const Caption('LOG'),
              for (final l in _list(r['log']).reversed)
                Text('${_s(l['at']).replaceAll('T', ' ')} · ${_s(l['what'])}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
            ]),
    );
  }
}

/// One breach: facts (her words), drafts for the Board / people, cards and "bhej diya".
class DpoBreachPage extends StatefulWidget {
  const DpoBreachPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<DpoBreachPage> createState() => _DpoBreachPageState();
}

class _DpoBreachPageState extends State<DpoBreachPage> {
  Map<String, dynamic>? _b;
  List<Map<String, dynamic>> _cards = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', '/api/dpo/breaches/${widget.id}'));
      final cs = _m(await widget.app.api!.call('GET', '/api/dpo/cards'));
      if (mounted) {
        setState(() {
          _b = b;
          _cards = _list(cs['cards']).where((c) => _s(c['target']) == _s(b['id'])).toList();
        });
      }
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

  Future<void> _facts() async {
    final f0 = _m(_b?['facts']);
    final f = await _form(context, 'Fill in the details', const [
      ('nature', 'What kind'),
      ('extent', 'How many people / which data'),
      ('when', 'When it happened'),
      ('location', 'Where / system'),
      ('impact', 'Possible impact'),
      ('consequences', 'Impact on people'),
      ('measures', 'What we did'),
      ('safety', 'What people should do themselves'),
      ('cause', 'Reason'),
      ('findings', 'Who did it: what is known'),
      ('remedial', 'Steps so it does not happen again'),
      ('details', 'Latest full details'),
      ('people_report', 'Report on informing people'),
    ], ok: 'Save', initial: {for (final e in f0.entries) e.key: '${e.value}'});
    if (f == null) return;
    await _run('PATCH', '/api/dpo/breaches/${widget.id}', f);
  }

  Future<void> _sent(String which) async {
    final f = await _form(context, 'Sent: $which', const [('ref', 'Reference (mail / portal number)')]);
    if (f == null) return;
    await _run('POST', '/api/dpo/breaches/${widget.id}/sent', {'which': which, 'ref': f['ref'] ?? ''});
  }

  @override
  Widget build(BuildContext context) {
    final b = _b;
    final dr = _m(b?['drafts']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(b == null ? 'Breach' : '${_s(b['number'])} · ${_s(b['title'])}')),
      body: b == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              DpoBreachCard(app: widget.app, data: {'breach': b}),
              const SizedBox(height: 8),
              GlassButton(label: 'Fill in the details', icon: Icons.edit_note_rounded, onTap: _busy ? null : _facts),
              for (final (k, title) in const [('initial', 'Board: first notice'), ('report', 'Board: 72-hour report'), ('people', 'Informing people')]) ...[
                const SizedBox(height: 12),
                Caption(title.toUpperCase()),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
                  child: Text(_s(dr[k]), style: const TextStyle(fontSize: 12.5, height: 1.35)),
                ),
                Wrap(spacing: 6, children: [
                  TextButton(onPressed: _busy ? null : () => _run('POST', '/api/dpo/breaches/${widget.id}/send', {'which': k}), child: const Text('Card for your yes')),
                  TextButton(onPressed: _busy ? null : () => _sent(k), child: const Text('Sent')),
                ]),
              ],
              const SizedBox(height: 12),
              for (final c in _cards) ...[DpoCardCard(app: widget.app, data: {'card': c}, onDone: _load), const SizedBox(height: 8)],
              GlassButton(label: 'Close breach', icon: Icons.task_alt_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/breaches/${widget.id}/close')),
            ]),
    );
  }
}

/// dpo_card: notice publish / reply / erasure / breach notice waiting for HER tap. Also in calls.
class DpoCardCard extends StatefulWidget {
  const DpoCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<DpoCardCard> createState() => _DpoCardCardState();
}

class _DpoCardCardState extends State<DpoCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  Map<String, dynamic> _send = {};
  List<Map<String, dynamic>> _sendList = [];
  List<Map<String, dynamic>> _erased = [];
  String _text = '';

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/dpo/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Delete data' : _s(show['title']), '');
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'No fingerprint was given, so it was not approved.',
        'key_invalidated' => 'A new fingerprint was added to the phone: link this phone again in Profile > Fingerprint approval.',
        _ => 'Could not approve with fingerprint (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not', const [('reason', 'Reason (for you)')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/dpo/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/dpo/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          _c = _m(m['card']).isEmpty ? _c : _m(m['card']);
          if (m['send'] is Map) _send = _m(m['send']);
          if (m['send'] is List) _sendList = _list(m['send']);
          _erased = _list(m['erased']);
          _text = _s(m['text']);
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

  List<Widget> _details(String kind, Map<String, dynamic> d) {
    Widget box(String t) => Container(
          margin: const EdgeInsets.only(top: 6),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
          child: Text(t, style: const TextStyle(fontSize: 12.5, height: 1.35), maxLines: 20, overflow: TextOverflow.ellipsis),
        );
    switch (kind) {
      case 'notice':
        return [Text('${_s(d['lang_label'])} · v${_s(d['version'])}', style: const TextStyle(fontSize: 12.5)), box(_s(d['text']))];
      case 'reply':
        return [
          Text('To: ${_s(d['to'])} ${_s(d['phone'])} ${_s(d['email'])} · due ${_s(d['due_on'])}', style: const TextStyle(fontSize: 12.5)),
          box(_s(d['text'])),
        ];
      case 'erase':
        return [
          Text('Mobile ${_s(d['phone'])}', style: const TextStyle(fontSize: 12.5)),
          for (final t in _list(d['targets'])) Text('• ${_s(t['label'])}', style: const TextStyle(fontSize: 12.5)),
          if (_strs(d['manual']).isNotEmpty) Text('Remove yourself: ${_strs(d['manual']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.muted)),
          for (final w in _strs(d['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12, color: C.warn)),
          Text(_s(d['note']), style: const TextStyle(fontSize: 11.5, color: C.bad)),
        ];
      default:
        return [
          if (_s(d['hours_left']).isNotEmpty) Text('72 hours: ${_s(d['report_due'])} (${_s(d['hours_left'])} hours)', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          box(_s(d['text'])),
          Text(_s(d['where']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
          if ((d['affected'] ?? 0) is num && (d['affected'] ?? 0) > 0) Text('${_s(d['affected'])} people', style: const TextStyle(fontSize: 12)),
        ];
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final st = _s(c['status']);
    final kind = _s(c['kind']);
    final d = _m(c['data']);
    return Glass(
      border: st == 'waiting' ? (kind == 'erase' ? C.bad : C.accent) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'notice' => Icons.policy_rounded,
            'reply' => Icons.reply_rounded,
            'erase' => Icons.delete_forever_rounded,
            _ => Icons.warning_amber_rounded,
          }, color: kind == 'erase' ? C.bad : C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(c['title']), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your yes?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'old', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'approved' ? C.ok : C.bad)),
        ]),
        ..._details(kind, d),
        const SizedBox(height: 6),
        const Text(_disclaimer, style: TextStyle(fontSize: 10.5, color: C.faint)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: kind == 'erase' ? 'Yes, wipe (fingerprint)' : 'Yes', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_send.isNotEmpty)
          Wrap(spacing: 6, children: [
            if (_s(_send['wa']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(_send['wa'])), child: const Text('WhatsApp')),
            if (_s(_send['mail']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(_send['mail'])), child: const Text('Email')),
            TextButton(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: _s(_send['text'])));
                  _snack(context, 'Copied.');
                },
                child: const Text('Copy')),
          ]),
        for (final x in _sendList)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('${_s(x['name'])} ${_s(x['phone'])}'),
            trailing: Wrap(children: [
              if (_s(x['wa']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(x['wa'])), child: const Text('WhatsApp')),
              if (_s(x['mail']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(x['mail'])), child: const Text('Email')),
            ]),
          ),
        if (_text.isNotEmpty && _sendList.isEmpty)
          GlassButton(
              label: 'Copy text (you send it)',
              icon: Icons.copy_rounded,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _text));
                _snack(context, 'Copied.');
              }),
        for (final e in _erased)
          Text('${e['ok'] == true ? '✓' : '✗'} ${_s(e['module'])}: ${_s(e['say'])}',
              style: TextStyle(fontSize: 12, color: e['ok'] == true ? C.ok : C.warn)),
      ]),
    );
  }
}

/// dpo_request: one rights request with its 90-day clock. Also in calls.
class DpoRequestCard extends StatelessWidget {
  const DpoRequestCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final r = _m(data['request']);
    final left = r['days_left'];
    final late = left is num && left < 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: late ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.person_search_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(r['number'])} · ${_s(r['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(r['status'])),
          ]),
          Text('${_s(r['name'])} ${_s(r['phone'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text(late ? 'Date ${_s(r['due_on'])} has passed' : 'Reply by ${_s(r['due_on'])} (${_s(left)} days)',
              style: TextStyle(fontSize: 12.5, color: late ? C.bad : C.warn)),
          if (_s(data['say']).isNotEmpty) Text(_s(data['say']), style: const TextStyle(fontSize: 12)),
        ]),
      ),
    );
  }
}

/// dpo_breach: a breach with the 72-hour clock and CERT-In link. Also in calls.
class DpoBreachCard extends StatelessWidget {
  const DpoBreachCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final b = _m(data['breach']);
    final ci = _m(b['cert_in']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: b['status'] == 'open' ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.warning_amber_rounded, color: C.bad, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(b['number'])} · ${_s(b['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(b['status'])),
          ]),
          Text('Found out: ${_s(b['aware_at'])} · report ${_s(b['report_due'])}${b['hours_left'] == null ? '' : ' (${_s(b['hours_left'])} hours)'}',
              style: const TextStyle(fontSize: 12.5, color: C.warn)),
          Text(
              [
                'Board first notice: ${_s(b['initial_at']).isEmpty ? 'baaki' : _s(b['initial_at'])}',
                'report: ${_s(b['report_at']).isEmpty ? 'baaki' : _s(b['report_at'])}',
                'people: ${_s(b['people_at']).isEmpty ? 'baaki' : _s(b['people_at'])}',
              ].join(' · '),
              style: const TextStyle(fontSize: 12, color: C.muted)),
          if (_s(ci['incident']).isNotEmpty) Text('CERT-In: IT Helpdesk incident (${_s(ci['due'])})', style: const TextStyle(fontSize: 12, color: C.teal)),
          if (_s(ci['error']).isNotEmpty) Text(_s(ci['error']), style: const TextStyle(fontSize: 12, color: C.warn)),
          if (_s(data['say']).isNotEmpty) Text(_s(data['say']), style: const TextStyle(fontSize: 12)),
        ]),
      ),
    );
  }
}

/// dpo_alert: a clock (breach 72 h, request due, vendor review, law phase, retention).
class DpoAlertCard extends StatelessWidget {
  const DpoAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        padding: const EdgeInsets.all(12),
        border: data['kind'] == 'breach' ? C.bad : C.warn,
        child: Row(children: [
          Icon(data['kind'] == 'breach' ? Icons.warning_amber_rounded : Icons.shield_rounded, color: data['kind'] == 'breach' ? C.bad : C.warn),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
          IconButton(
              icon: const Icon(Icons.open_in_new_rounded),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DpoScreen(app: app)))),
        ]),
      );
}

/// dpo_day: the morning note.
class DpoDayCard extends StatelessWidget {
  const DpoDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.shield_rounded, color: C.accent),
            SizedBox(width: 8),
            Text('Data protection today', style: TextStyle(fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
          const SizedBox(height: 8),
          GlassButton(
              label: 'Open DPO',
              icon: Icons.open_in_new_rounded,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DpoScreen(app: app)))),
        ]),
      );
}
