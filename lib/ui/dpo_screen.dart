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

const _disclaimer = 'Yeh draft / jaankari hai, kanooni salah nahi. Vakil / CA / CS se pakka karwaiye.';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}}) async {
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
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
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
    final f = await _form(context, 'DPO jaankari', const [
      ('org', 'Business ka naam (Data Fiduciary)'),
      ('contact_name', 'Jawab dene wala (DPO / contact person)'),
      ('contact_email', 'Unka email'),
      ('contact_phone', 'Unka mobile'),
      ('link', 'Consent wapas / maang ka link (https://)'),
      ('identifiers', 'Pehchaan kaise karengi (jaise registered mobile)'),
      ('reply_days', 'Jawab ke din (max 90)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('rules', 'Aapke niyam'),
    ], ok: 'Save', initial: {for (final e in st.entries) if (e.value != null && e.value is! Map && e.value is! List) e.key: '${e.value}'});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['reply_days'] != null) body['reply_days'] = int.tryParse(f['reply_days']!) ?? 30;
    await _run('PUT', '/api/dpo/settings', body);
  }

  Future<void> _activity([Map<String, dynamic>? a]) async {
    final f = await _form(context, a == null ? 'Naya kaam (processing)' : '${_s(a['number'])} badlo', const [
      ('name', 'Kaam ka naam'),
      ('people', 'Kiska data (graahak / staff / bachche)'),
      ('items', 'Kaunsa data (comma se)'),
      ('purpose', 'Kis kaam ke liye'),
      ('basis', 'Aadhaar: consent / voluntary / employment / law / emergency'),
      ('retention', 'Kitne samay rakhna (shabdon mein)'),
      ('retention_days', 'Din mein (review ke liye)'),
      ('processors', 'Kaun process karta hai (comma se)'),
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
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Jokhim dekho')),
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
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok == true) await _run('PATCH', '/api/dpo/notices/${_s(n['id'])}', {'text': c.text});
  }

  Future<void> _newRequest() async {
    final f = await _form(context, 'Nayi maang (data principal)', const [
      ('text', 'Unke shabd (jaise "mera data mitao")'),
      ('name', 'Naam'),
      ('phone', 'Registered mobile'),
      ('email', 'Email (ho to)'),
      ('via', 'Kaise aayi (WhatsApp / email / dukaan)'),
      ('received', 'Kab mili (YYYY-MM-DD, khaali = aaj)'),
    ], ok: 'Darj karo');
    if (f == null || ((f['text'] ?? '').isEmpty)) return;
    await _run('POST', '/api/dpo/requests', f);
  }

  Future<void> _newBreach() async {
    final f = await _form(context, 'Data breach darj karo', const [
      ('title', 'Kya hua (ek line)'),
      ('aware', 'Kab pata chala (YYYY-MM-DD HH:MM, khaali = abhi)'),
      ('nature', 'Kis tarah ka (chori / hack / galti se bheja)'),
      ('extent', 'Kitne log / kaunsa data'),
      ('when', 'Ghatna kab hui'),
      ('location', 'Kahan / kaunsa system'),
      ('impact', 'Sambhavit asar'),
      ('affected', 'Prabhavit logon ke mobile / email (comma se)'),
    ], ok: 'Darj karo');
    if (f == null || (f['title'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f, 'cert_in': true};
    body['affected'] = _lines(f['affected']);
    await _run('POST', '/api/dpo/breaches', body);
  }

  Future<void> _newConsent() async {
    final f = await _form(context, 'Consent darj karo', const [
      ('name', 'Naam'),
      ('phone', 'Mobile'),
      ('activities', 'Kaam (PA-01, PA-02)'),
      ('how', 'Kaise li (form / WhatsApp / kaagaz)'),
      ('proof', 'Saboot ka reference'),
      ('child', 'Bachcha hai? (haan / nahi)'),
      ('parent_name', 'Maa / baap ka naam (bachche ke liye)'),
      ('parent_check', 'Kaise verify kiya + reference (ID number nahi)'),
    ], ok: 'Darj karo');
    if (f == null) return;
    final body = <String, dynamic>{...f, 'activities': _lines(f['activities']), 'child': (f['child'] ?? '').toLowerCase().startsWith('h')};
    await _run('POST', '/api/dpo/consents', body);
  }

  Future<void> _vendor([Map<String, dynamic>? v]) async {
    final clauses = _list(_law['dpa']);
    final f = await _form(context, v == null ? 'Naya vendor (processor)' : _s(v['name']), const [
      ('name', 'Naam'),
      ('service', 'Kya karta hai'),
      ('items', 'Kaunsa data jaata hai'),
      ('country', 'Data kis desh mein'),
      ('dpa_on', 'Contract (DPA) kab sign (YYYY-MM-DD)'),
      ('review_on', 'Review kab (YYYY-MM-DD)'),
    ], ok: 'Aage', initial: v == null
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
          title: const Text('Contract (DPA) mein kya hai'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              SwitchListTile(value: signed, title: const Text('DPA sign hai'), onChanged: (x) => set(() => signed = x)),
              for (final c in clauses)
                CheckboxListTile(
                    dense: true,
                    value: cl[_s(c['key'])] ?? false,
                    title: Text(_s(c['text']), style: const TextStyle(fontSize: 12.5)),
                    onChanged: (x) => set(() => cl[_s(c['key'])] = x ?? false)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
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
        Expanded(child: GradientButton(label: 'Nayi maang', icon: Icons.person_search_rounded, height: 46, onTap: _busy ? null : _newRequest)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Breach', icon: Icons.warning_amber_rounded, color: C.bad, onTap: _busy ? null : _newBreach)),
      ]),
      const SizedBox(height: 12),
      if (_list(day['cards']).isNotEmpty) ...[const Caption('AAPKI HAAN CHAHIYE'), _cardsList(_list(day['cards']))],
      if (_list(day['breaches']).isNotEmpty) ...[
        const Caption('KHULE BREACH'),
        for (final b in _list(day['breaches'])) DpoBreachCard(app: widget.app, data: {'breach': b}),
      ],
      if (_list(day['requests']).isNotEmpty) ...[
        const Caption('KHULI MAANGEIN'),
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
                label: 'Modules se bharo', icon: Icons.auto_fix_high_rounded, height: 46, onTap: _busy ? null : () => _run('POST', '/api/dpo/scan'))),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Naya kaam', icon: Icons.add_rounded, onTap: _busy ? null : () => _activity())),
      ]),
      const SizedBox(height: 8),
      GlassButton(label: 'Poora register (Excel)', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/register')),
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
                if (a['children'] == true) const Pill('bachche', fg: C.bad),
                if ((a['records'] ?? 0) > 0) Pill('${_s(a['records'])} record'),
              ]),
              Text('${_s(a['people'])} · ${_strs(a['items']).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
              Text('Kaam: ${_s(a['purpose'])}', style: const TextStyle(fontSize: 12.5)),
              Text(_s(a['basis_label']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
              Text('Rakhna: ${_s(a['retention'])}', style: const TextStyle(fontSize: 12)),
              if (_strs(a['processors']).isNotEmpty) Text('Processors: ${_strs(a['processors']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.muted)),
              if (_s(_m(a['dpia'])['level']).isNotEmpty) Text('DPIA: ${_s(_m(a['dpia'])['level'])}', style: const TextStyle(fontSize: 12, color: C.teal)),
              for (final c in _strs(a['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12, color: C.warn)),
              const SizedBox(height: 6),
              Wrap(spacing: 6, children: [
                if (a['confirmed'] != true)
                  TextButton(
                      onPressed: _busy ? null : () => _run('PATCH', '/api/dpo/activities/${_s(a['id'])}', {'confirmed': true}),
                      child: const Text('Sahi hai')),
                TextButton(onPressed: _busy ? null : () => _activity(a), child: const Text('Badlo')),
                TextButton(onPressed: _busy ? null : () => _dpia(a), child: const Text('DPIA')),
              ]),
            ]),
          ),
        ),
      if (acts.isEmpty) const Text('Abhi register khaali. "Modules se bharo" dabaiye: Hoola dekhega kis kaam mein logon ka data hai.',
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
      GradientButton(label: 'Naya notice (Rule 3)', icon: Icons.policy_rounded, height: 46, onTap: _busy ? null : _newNotice),
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
              if (n['blanks'] == true) const Text('⚠ [____] baaki: Niyam mein naam / link / contact bhariye ya khud likhiye.',
                  style: TextStyle(fontSize: 12, color: C.warn)),
              Wrap(spacing: 6, children: [
                if (n['status'] == 'draft' || n['status'] == 'rejected') ...[
                  TextButton(onPressed: _busy ? null : () => _editNotice(n), child: const Text('Khud likho')),
                  TextButton(
                      onPressed: _busy || n['blanks'] == true ? null : () => _run('POST', '/api/dpo/notices/${_s(n['id'])}/publish'),
                      child: const Text('Haan ke liye card')),
                ],
                TextButton(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: _s(n['text'])));
                      _snack(context, 'Copy ho gaya.');
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
        Expanded(child: GradientButton(label: 'Nayi maang', icon: Icons.person_search_rounded, height: 46, onTap: _busy ? null : _newRequest)),
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
            title: Text('${_s(c['name'])} ${_s(c['phone'])}${c['child'] == true ? ' · bachcha' : ''}'),
            subtitle: Text('${_s(c['how'])} · ${_s(c['given_at']).split('T').first}${_s(c['withdrawn_at']).isEmpty ? '' : ' · wapas'}'),
            trailing: c['status'] == 'active'
                ? TextButton(
                    onPressed: _busy ? null : () => _run('POST', '/api/dpo/consents/withdraw', {'consent': _s(c['id']), 'how': 'app'}),
                    child: const Text('Wapas'))
                : null,
          ),
      ],
    ]);
  }

  Widget _breachTab() {
    final bs = _list(_d?['breaches']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GlassButton(label: 'Breach darj karo', icon: Icons.warning_amber_rounded, color: C.bad, onTap: _busy ? null : _newBreach),
      const SizedBox(height: 6),
      const Text('Board ko bina der pehli soochna, 72 ghante mein poori report; logon ko bina der. Cyber hamla ho to CERT-In 6 ghante '
          '(IT Helpdesk mein clock).', style: TextStyle(fontSize: 12, color: C.muted)),
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
      GradientButton(label: 'Vendor jodo', icon: Icons.handshake_rounded, height: 46, onTap: _busy ? null : () => _vendor()),
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
                  Pill(v['dpa_signed'] == true ? 'DPA hai' : 'DPA nahi', fg: v['dpa_signed'] == true ? C.ok : C.warn),
                ]),
                Text('${_s(v['service'])} · ${_s(v['country'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                if (v['abroad'] == true) const Text('Data India ke bahar: contract mein desh likhwaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
                for (final m in _strs(v['missing']).take(4)) Text('• baaki: $m', style: const TextStyle(fontSize: 11.5, color: C.faint)),
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
          Text(_s(st['org']).isEmpty ? 'Business ka naam nahi diya' : _s(st['org']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Contact: ${[st['contact_name'], st['contact_email'], st['contact_phone']].where((x) => _s(x).isNotEmpty).join(', ')}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text('Link: ${_s(st['link'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text('Jawab: ${_s(st['reply_days'])} din (kanoon max 90)', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text(_s(st['sdf_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          for (final m in _strs(st['missing'])) Text('⚠ baaki: $m', style: const TextStyle(fontSize: 12, color: C.warn)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _busy ? null : _settings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('KABHI NAHI'),
      for (final n in _strs(_law['never'])) Text('• $n', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 12),
      const Caption('JURMANA (ZYADA SE ZYADA)'),
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
    final tabs = ['Aaj', 'Register', 'Notice', 'Maang', 'Breach', 'Vendor', 'Niyam'];
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
    final f = await _form(context, 'Pehchaan kaise ki', const [('how', 'Tareeka + reference (ID number nahi)'), ('ok', 'Pakki hui? (haan / nahi)')]);
    if (f == null || (f['how'] ?? '').isEmpty) return;
    await _run('POST', '/api/dpo/requests/${widget.id}/verify', {'how': f['how'], 'ok': !(f['ok'] ?? 'haan').toLowerCase().startsWith('n')});
  }

  Future<void> _reply() async {
    final f = await _form(context, 'Jawab', const [('body', 'Apne shabd (khaali = Hoola ka draft)')], ok: 'Card banao');
    if (f == null) return;
    await _run('POST', '/api/dpo/requests/${widget.id}/reply', {'body': f['body'] ?? ''});
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(r == null ? 'Maang' : '${_s(r['number'])} · ${_s(r['kind_label'])}')),
      body: r == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              DpoRequestCard(app: widget.app, data: {'request': r}),
              const SizedBox(height: 8),
              Glass(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Unke shabd (data, hukm nahi):', style: TextStyle(fontSize: 12, color: C.faint)),
                  Text(_s(r['text']), style: const TextStyle(fontSize: 13)),
                  const SizedBox(height: 6),
                  Text('Pehchaan: ${_s(r['id_check'])}${_s(r['id_how']).isEmpty ? '' : ' (${_s(r['id_how'])})'}',
                      style: TextStyle(fontSize: 12.5, color: r['id_check'] == 'done' ? C.ok : C.warn)),
                ]),
              ),
              const SizedBox(height: 8),
              if (_list(r['found']).isNotEmpty) ...[
                const Caption('UNKA DATA KAHAN HAI'),
                for (final h in _list(r['found']))
                  Text('• ${_s(h['label'])}${h['can_erase'] == true ? '' : ' (us screen se hataiye)'}${h['law_hold'] == true ? ' · kanoon ke liye rakhna pad sakta' : ''}',
                      style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 8),
              ],
              Wrap(spacing: 6, runSpacing: 6, children: [
                GlassButton(label: 'Pehchaan', icon: Icons.verified_user_rounded, onTap: _busy ? null : _verify),
                GlassButton(label: 'Jawab card', icon: Icons.reply_rounded, onTap: _busy ? null : _reply),
                if (r['kind'] == 'erasure' || r['kind'] == 'withdraw')
                  GlassButton(
                      label: 'Mitaane ka card',
                      icon: Icons.delete_forever_rounded,
                      color: C.bad,
                      onTap: _busy ? null : () => _run('POST', '/api/dpo/requests/${widget.id}/erase', {})),
                GlassButton(label: 'Bhej diya', icon: Icons.done_all_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/requests/${widget.id}/sent', {'how': 'app'})),
                GlassButton(label: 'Band', icon: Icons.close_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/requests/${widget.id}/close', {})),
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
    final f = await _form(context, 'Jaankari bhariye', const [
      ('nature', 'Kis tarah ka'),
      ('extent', 'Kitne log / kaunsa data'),
      ('when', 'Kab hua'),
      ('location', 'Kahan / system'),
      ('impact', 'Sambhavit asar'),
      ('consequences', 'Logon par asar'),
      ('measures', 'Humne kya kiya'),
      ('safety', 'Log khud kya karein'),
      ('cause', 'Wajah'),
      ('findings', 'Kisne kiya: jo pata chala'),
      ('remedial', 'Dobara na ho uske kadam'),
      ('details', 'Taaza poori jaankari'),
      ('people_report', 'Logon ko soochna ki report'),
    ], ok: 'Save', initial: {for (final e in f0.entries) e.key: '${e.value}'});
    if (f == null) return;
    await _run('PATCH', '/api/dpo/breaches/${widget.id}', f);
  }

  Future<void> _sent(String which) async {
    final f = await _form(context, 'Bhej diya: $which', const [('ref', 'Reference (mail / portal number)')]);
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
              GlassButton(label: 'Jaankari bhariye', icon: Icons.edit_note_rounded, onTap: _busy ? null : _facts),
              for (final (k, title) in const [('initial', 'Board: pehli soochna'), ('report', 'Board: 72 ghante report'), ('people', 'Logon ko soochna')]) ...[
                const SizedBox(height: 12),
                Caption(title.toUpperCase()),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
                  child: Text(_s(dr[k]), style: const TextStyle(fontSize: 12.5, height: 1.35)),
                ),
                Wrap(spacing: 6, children: [
                  TextButton(onPressed: _busy ? null : () => _run('POST', '/api/dpo/breaches/${widget.id}/send', {'which': k}), child: const Text('Haan ke liye card')),
                  TextButton(onPressed: _busy ? null : () => _sent(k), child: const Text('Bhej diya')),
                ]),
              ],
              const SizedBox(height: 12),
              for (final c in _cards) ...[DpoCardCard(app: widget.app, data: {'card': c}, onDone: _load), const SizedBox(height: 8)],
              GlassButton(label: 'Breach band karo', icon: Icons.task_alt_rounded, onTap: _busy ? null : () => _run('POST', '/api/dpo/breaches/${widget.id}/close')),
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
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Data mitaana' : _s(show['title']), '');
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'Fingerprint nahi diya, isliye haan nahi hui.',
        'key_invalidated' => 'Phone mein naya fingerprint juda hai: Profile > Fingerprint se haan mein phone phir se jodiye.',
        _ => 'Fingerprint se haan nahi ho payi (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyon nahi', const [('reason', 'Wajah (aapke liye)')]);
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
          Text('Kisko: ${_s(d['to'])} ${_s(d['phone'])} ${_s(d['email'])} · due ${_s(d['due_on'])}', style: const TextStyle(fontSize: 12.5)),
          box(_s(d['text'])),
        ];
      case 'erase':
        return [
          Text('Mobile ${_s(d['phone'])}', style: const TextStyle(fontSize: 12.5)),
          for (final t in _list(d['targets'])) Text('• ${_s(t['label'])}', style: const TextStyle(fontSize: 12.5)),
          if (_strs(d['manual']).isNotEmpty) Text('Khud hataiye: ${_strs(d['manual']).join(', ')}', style: const TextStyle(fontSize: 12, color: C.muted)),
          for (final w in _strs(d['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12, color: C.warn)),
          Text(_s(d['note']), style: const TextStyle(fontSize: 11.5, color: C.bad)),
        ];
      default:
        return [
          if (_s(d['hours_left']).isNotEmpty) Text('72 ghante: ${_s(d['report_due'])} (${_s(d['hours_left'])} ghante)', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          box(_s(d['text'])),
          Text(_s(d['where']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
          if ((d['affected'] ?? 0) is num && (d['affected'] ?? 0) > 0) Text('${_s(d['affected'])} log', style: const TextStyle(fontSize: 12)),
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
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
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
                    label: kind == 'erase' ? 'Haan, mitao (fingerprint)' : 'Haan', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_send.isNotEmpty)
          Wrap(spacing: 6, children: [
            if (_s(_send['wa']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(_send['wa'])), child: const Text('WhatsApp')),
            if (_s(_send['mail']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(_send['mail'])), child: const Text('Email')),
            TextButton(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: _s(_send['text'])));
                  _snack(context, 'Copy ho gaya.');
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
              label: 'Text copy (aap bhejiye)',
              icon: Icons.copy_rounded,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _text));
                _snack(context, 'Copy ho gaya.');
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
          Text(late ? 'Taarikh ${_s(r['due_on'])} nikal gayi' : 'Jawab ${_s(r['due_on'])} tak (${_s(left)} din)',
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
          Text('Pata chala: ${_s(b['aware_at'])} · report ${_s(b['report_due'])}${b['hours_left'] == null ? '' : ' (${_s(b['hours_left'])} ghante)'}',
              style: const TextStyle(fontSize: 12.5, color: C.warn)),
          Text(
              [
                'Board pehli: ${_s(b['initial_at']).isEmpty ? 'baaki' : _s(b['initial_at'])}',
                'report: ${_s(b['report_at']).isEmpty ? 'baaki' : _s(b['report_at'])}',
                'log: ${_s(b['people_at']).isEmpty ? 'baaki' : _s(b['people_at'])}',
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
            Text('Aaj data suraksha mein', style: TextStyle(fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
          const SizedBox(height: 8),
          GlassButton(
              label: 'DPO kholo',
              icon: Icons.open_in_new_rounded,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DpoScreen(app: app)))),
        ]),
      );
}
