/// Profile > Notary & documentation (Notary Sahayak).
/// Aaj (print cards waiting, drafts with blanks, final docs not notarised, apostille cases, renewal / annual return) · Documents
/// (affidavits, declarations, POA, indemnity, NOC, rent summary; English / Hindi / Marathi from the party's facts) · Register
/// (Form XV lines + fee receipts, Excel) · Apostille (MEA steps) · Niyam (her stamp rate table, fees vs Rule 10 caps, mode).
/// Final print happens ONLY on her tap here (hash-checked). Notarising, signing, sealing and e-stamping are her acts.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'desk/desk_kit.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _stColor(String st) => switch (st) {
      'waiting' || 'draft' => C.warn,
      'final' || 'executed' || 'done' => C.ok,
      'rejected' || 'dropped' => C.bad,
      _ => C.chip,
    };

String _stLabel(String st) => switch (st) {
      'draft' => 'draft',
      'waiting' => 'your yes?',
      'final' => 'final print',
      'executed' => 'notarised',
      'rejected' => 'no',
      _ => st,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}, Set<String> long = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: long.contains(k) ? 4 : 1),
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

Future<String?> _pick(BuildContext context, String title, Map<String, String> options) => showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      isScrollControlled: true,
      builder: (_) => SafeArea(
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(padding: const EdgeInsets.all(16), child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800))),
            for (final e in options.entries) ListTile(title: Text(e.value), onTap: () => Navigator.pop(context, e.key)),
          ]),
        ),
      ),
    );

const _partyFields = [
  ('name', 'Party name'),
  ('relation', 'Relation: so / do / wo / ho'),
  ('relative', 'Father / husband name'),
  ('age', 'Umar'),
  ('occupation', 'Kaam / vyavsay'),
  ('address', 'Full address'),
  ('gender', 'm / f'),
  ('phone', 'Mobile'),
  ('id_number', 'Aadhaar / PAN (goes straight to the locker)'),
];

class NotaryScreen extends StatefulWidget {
  const NotaryScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<NotaryScreen> createState() => _NotaryScreenState();
}

class _NotaryScreenState extends State<NotaryScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic> _kinds = {};
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/notary'));
      if (_kinds.isEmpty) _kinds = _m(await widget.app.api!.call('GET', '/api/notary/kinds'));
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

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => NotaryDocPage(app: widget.app, docRef: ref, kinds: _kinds)))
      .then((_) => _load());

  Future<void> _newDoc() async {
    final kinds = _m(_kinds['kinds']);
    final kind = await _pick(context, 'Which document?', {for (final e in kinds.entries) e.key: _s(_m(e.value)['label'])});
    if (kind == null || !mounted) return;
    final lang = await _pick(context, 'Language', const {'en': 'English', 'hi': 'हिन्दी', 'mr': 'मराठी'});
    if (lang == null || !mounted) return;
    final party = await _form(context, 'Party (who will sign)', _partyFields, ok: 'Aage');
    if (party == null || !mounted) return;
    final fields = _list(_m(kinds[kind])['fields']);
    final facts = await _form(
        context,
        _s(_m(kinds[kind])['label']),
        [for (final f in fields) (_s(f['key']), '${_s(f['label'])}${f['required'] == true ? ' *' : ''}')],
        ok: 'Make draft',
        long: const {'statements', 'powers', 'matter', 'act'});
    if (facts == null) return;
    final r = await _run('POST', '/api/notary/docs', {'kind': kind, 'lang': lang, 'party': party, 'facts': facts});
    final id = _s(_m(r?['doc'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Future<void> _fromWords() async {
    final f = await _form(context, 'In your own words', const [('words', 'Which document, for whom, what points (as you would say it)')],
        ok: 'Make draft', long: const {'words'});
    if (f == null || (f['words'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/notary/docs', {'words': f['words']});
    final id = _s(_m(r?['doc'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Future<void> _fromRentdesk() async {
    final f = await _form(context, 'Rentdesk se rent summary', const [('tenancy', 'Tenancy no. (jaise T-0001)'), ('lang', 'en / hi / mr')]);
    if (f == null || (f['tenancy'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/notary/docs/from_rentdesk', f);
    final id = _s(_m(r?['doc'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      GradientButton(label: 'New document', icon: Icons.note_add_rounded, height: 46, onTap: _busy ? null : _newDoc),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(child: GlassButton(label: 'Spoken / written', icon: Icons.record_voice_over_rounded, height: 42, onTap: _busy ? null : _fromWords)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'Rentdesk se', icon: Icons.home_work_rounded, height: 42, onTap: _busy ? null : _fromRentdesk)),
      ]),
      const SizedBox(height: 12),
      for (final (key, title) in const [
        ('waiting', 'FINAL PRINT: YOUR YES PENDING'),
        ('blanks', 'BLANKS IN THE DRAFT'),
        ('final_old', 'FINAL, NOT YET NOTARISED'),
        ('apostille', 'APOSTILLE CASE'),
        ('dates', 'DATES'),
      ])
        if (_strs(day[key]).isNotEmpty) ...[
          Caption(title),
          for (final t in _strs(day[key])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
          const SizedBox(height: 8),
        ],
      Text('In the register today: ${_s(day['today_entries'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
    ]);
  }

  Widget _docsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New document', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newDoc),
        const SizedBox(height: 12),
        for (final d in _list(_d?['docs']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _open(_s(d['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.gavel_rounded, color: C.accent, size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${_s(d['number'])} · ${_s(d['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_stLabel(_s(d['status'])), fg: _stColor(_s(d['status']))),
                  ]),
                  Text(
                      [
                        _list(d['parties']).map((p) => _s(p['name'])).where((x) => x.isNotEmpty).join(', '),
                        _s(d['lang_label']),
                        'Stamp ${_s(_m(d['stamp'])['amount_text'])}',
                      ].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (_strs(d['blanks']).isNotEmpty)
                    Text('Khaali: ${_strs(d['blanks']).take(3).join(', ')}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
                ]),
              ),
            ),
          ),
        if (_list(_d?['docs']).isEmpty) const Text('No documents yet.', style: TextStyle(color: C.muted)),
      ]);

  Future<void> _addEntry() async {
    final f = await _form(context, 'Enter in the register (outside document)', const [
      ('act', 'Act: affidavit / attest / true_copy / translation / outside_attest / other'),
      ('name', 'Executant name'),
      ('address', 'Executant\'s full address'),
      ('id_number', 'Aadhaar / PAN (straight to the locker)'),
      ('contents', 'What the document contains'),
      ('stamp_text', 'Stamp (jaise ₹500 e-SBTR no.)'),
      ('fee', 'Notarial fee (₹)'),
      ('pages', 'Pages (true copy)'),
      ('typing', 'Typing charge (₹)'),
    ], ok: 'Write in register');
    if (f == null) return;
    final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              title: const Text('Did you notarise it?'),
              content: const Text('Write the register line only after the party has signed in front of you and you have sealed / signed.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Not now')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, I did it')),
              ],
            ));
    if (ok != true) return;
    await _run('POST', '/api/notary/register', {
      'act': f['act'] ?? 'attest',
      'executants': [
        {'name': f['name'], 'address': f['address'], if ((f['id_number'] ?? '').isNotEmpty) 'id_number': f['id_number']}
      ],
      'contents': f['contents'],
      'stamp_text': f['stamp_text'],
      'fee': _n(f['fee']),
      'pages': int.tryParse(f['pages'] ?? '') ?? 1,
      if (_n(f['typing']) != null) 'charges': {'typing': _n(f['typing'])},
    });
  }

  Widget _registerTab() {
    final reg = _m(_d?['register']);
    final entries = _list(reg['entries']).reversed.toList();
    final mode = _s(_m(_d?['settings'])['mode']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Register ${_s(reg['year'])}: ${_s(reg['total_acts'])} acts · fee ₹${_s(reg['fees_total'])}',
              style: const TextStyle(fontWeight: FontWeight.w800)),
          const Text('Form XV (Notaries Rules 1956, Rule 11). A line is never changed: if there is a mistake, add a correction line.',
              style: TextStyle(fontSize: 11.5, color: C.faint)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
                child: GlassButton(
                    label: 'Excel', icon: Icons.table_chart_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/notary/register/file', {}))),
            const SizedBox(width: 8),
            if (mode == 'notary')
              Expanded(child: GlassButton(label: 'Line jodo', icon: Icons.playlist_add_rounded, height: 40, onTap: _busy ? null : _addEntry)),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      if (mode != 'notary') const Text('Desk mode: only a notary keeps the notarial register.', style: TextStyle(color: C.muted)),
      for (final e in entries)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(e['serial'])} · ${_s(e['on'])} ${_s(e['at'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
              Text(_s(e['act_label']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
              for (final x in _list(e['executants']))
                Text('${_s(x['name'])}, ${_s(x['address'])}${_s(x['id_masked']).isEmpty ? '' : ' · ${_s(x['id_kind'])} ${_s(x['id_masked'])}'}',
                    style: const TextStyle(fontSize: 12.5)),
              Text(_s(e['contents']), style: const TextStyle(fontSize: 12.5)),
              Text('Stamp: ${_s(e['stamp_text'])} · Fee ₹${_s(e['fee'])} · Receipt ${_s(e['receipt_no'])}',
                  style: const TextStyle(fontSize: 12, color: C.muted)),
              if (_s(e['corrects']).isNotEmpty) Text('Correction of ${_s(e['corrects'])}: ${_s(e['remarks'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
              if (_s(e['corrects']).isEmpty)
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                      onPressed: () async {
                        final f = await _form(context, 'Correction (${_s(e['serial'])})', const [('remarks', 'What was wrong, and what is right')],
                            long: const {'remarks'});
                        if (f != null && (f['remarks'] ?? '').isNotEmpty) {
                          await _run('POST', '/api/notary/register/correct', {'serial': e['serial'], 'remarks': f['remarks']});
                        }
                      },
                      child: const Text('Correction')),
                ),
            ]),
          ),
        ),
    ]);
  }

  Future<void> _newApostille() async {
    final type = await _pick(context, 'What kind of document?', {for (final e in _m(_kinds['doc_types']).entries) e.key: _s(e.value)});
    if (type == null || !mounted) return;
    final f = await _form(context, 'Apostille / attestation', const [
      ('doc_title', 'Document (jaise Birth certificate)'),
      ('country', 'For which country'),
      ('hague', 'Hague member? yes / no / (blank = not known)'),
      ('party', 'Party name'),
      ('phone', 'Mobile'),
      ('doc', 'Hoola document no. (if any, ND-0001)'),
    ], ok: 'Make');
    if (f == null) return;
    await _run('POST', '/api/notary/apostilles', {...f, 'doc_type': type});
  }

  Widget _apostilleTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New apostille case', icon: Icons.public_rounded, height: 46, onTap: _busy ? null : _newApostille),
        const SizedBox(height: 12),
        for (final a in _list(_d?['apostilles'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: _apCard(a)),
        if (_list(_d?['apostilles']).isEmpty) const Text('No open cases.', style: TextStyle(color: C.muted)),
        const SizedBox(height: 8),
        const Text('MEA does not take documents from individuals directly: it goes through MEA\'s outsourced agency. Check the fees on the MEA site.',
            style: TextStyle(fontSize: 11.5, color: C.faint)),
      ]);

  Widget _apCard(Map<String, dynamic> a) => Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
                child: Text('${_s(a['number'])} · ${_s(a['doc_title'])} → ${_s(a['country'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(a['hague']).isEmpty ? 'hague?' : (_s(a['hague']) == 'yes' ? 'apostille' : 'attestation'), fg: C.chip),
          ]),
          if (_s(a['hague']).isEmpty)
            Row(children: [
              TextButton(onPressed: () => _run('POST', '/api/notary/apostilles/${_s(a['id'])}', {'hague': 'yes'}), child: const Text('Hague member')),
              TextButton(onPressed: () => _run('POST', '/api/notary/apostilles/${_s(a['id'])}', {'hague': 'no'}), child: const Text('Not a member')),
            ]),
          for (final st in _list(a['steps']))
            CheckboxListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              value: _s(st['done']).isNotEmpty,
              title: Text(_s(st['text']), style: const TextStyle(fontSize: 12.5)),
              onChanged: _busy
                  ? null
                  : (v) => _run('POST', '/api/notary/apostilles/${_s(a['id'])}', {'step': st['key'], 'done': v == true}),
            ),
        ]),
      );

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    const keys = ['mode', 'office', 'notary_name', 'reg_no', 'area', 'appointed_by', 'cop_valid_to', 'address', 'phone', 'state', 'default_lang', 'morning_time'];
    final f = await _form(context, 'Niyam', const [
      ('mode', 'notary (I am a notary) / desk (typing / documentation centre)'),
      ('office', 'Office / desk name'),
      ('notary_name', 'Notary name'),
      ('reg_no', 'Registration no. (on the seal)'),
      ('area', 'Area of practice'),
      ('appointed_by', 'Kisne appoint kiya (Central / State Govt)'),
      ('cop_valid_to', 'Certificate of practice valid till (YYYY-MM-DD)'),
      ('address', 'Office address'),
      ('phone', 'Office mobile'),
      ('state', 'State (MH / Maharashtra)'),
      ('default_lang', 'Default language: en / hi / mr'),
      ('morning_time', 'Subah ka note (HH:MM)'),
    ], ok: 'Save', initial: {for (final k in keys) k: _s(st[k])});
    if (f == null) return;
    await _run('PUT', '/api/notary/settings', f);
  }

  Future<void> _stampRate() async {
    final st = _m(_d?['settings']);
    final key = await _pick(context, 'Kis document ka stamp?', {for (final k in _strs(st['stamp_keys'])) k: k});
    if (key == null || !mounted) return;
    final f = await _form(context, 'Stamp rate: $key', const [
      ('state', 'State (MH / DL / ...)'),
      ('amount', 'Amount ₹ (from the state\'s official schedule; 0 = no stamp; blank = remove)'),
      ('mode', 'e_stamp / esbtr / franking / paper / kaveri (blank = per state)'),
    ], ok: 'Save', initial: {'state': _s(st['state'])});
    if (f == null) return;
    await _run('POST', '/api/notary/stamp_rates', {'key': key, 'state': f['state'] ?? _s(st['state']), 'amount': _n(f['amount']), 'mode': f['mode'] ?? ''});
  }

  Future<void> _fee() async {
    final st = _m(_d?['settings']);
    final acts = _m(st['acts']);
    final act = await _pick(context, 'Kis act ki fee?', {for (final e in acts.entries) e.key: '${_s(_m(e.value)['label'])}${_m(e.value)['cap'] == null ? '' : ' (max ₹${_s(_m(e.value)['cap'])})'}'});
    if (act == null || !mounted) return;
    final f = await _form(context, 'Your fee', const [('amount', 'Fee ₹')], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/notary/fees', {'act': act, 'amount': _n(f['amount'])});
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    final rates = _m(st['stamp_rates']);
    final fees = _m(st['fees']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['notary_name']).isEmpty ? (_s(st['office']).isEmpty ? 'Enter the name' : _s(st['office'])) : _s(st['notary_name']),
              style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Mode: ${_s(st['mode'])} · Reg ${_s(st['reg_no']).isEmpty ? '—' : _s(st['reg_no'])} · ${_s(st['state_label'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(st['cop_valid_to']).isNotEmpty)
            Text('Certificate of practice: valid until ${_s(st['cop_valid_to'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('YOUR STAMP RATE TABLE'),
      if (rates.isEmpty) const Text('Empty for now: documents will show [stamp ₹ ?] for the stamp amount.', style: TextStyle(fontSize: 12.5, color: C.warn)),
      for (final e in rates.entries)
        for (final r in _m(e.value).entries)
          Text('• ${e.key} · ${r.key}: ${r.value is Map ? '₹${_s(_m(r.value)['amount'])} (${_s(_m(r.value)['mode'])})' : '₹${_s(r.value)}'}',
              style: const TextStyle(fontSize: 13)),
      GlassButton(label: 'Stamp rate jodo / badlo', icon: Icons.approval_rounded, height: 40, onTap: _stampRate),
      const SizedBox(height: 12),
      const Caption('YOUR FEES'),
      for (final e in fees.entries) Text('• ${_s(_m(_m(st['acts'])[e.key])['label'])}: ₹${_s(e.value)}', style: const TextStyle(fontSize: 13)),
      GlassButton(label: 'Fee jodo / badlo', icon: Icons.currency_rupee_rounded, height: 40, onTap: _fee),
      Text(_s(st['fee_source']), style: const TextStyle(fontSize: 11, color: C.faint)),
      const SizedBox(height: 12),
      const Caption('HOOLA NEVER'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
      const SizedBox(height: 8),
      const Caption('SOURCES'),
      for (final t in _strs(_d?['sources'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(t, style: const TextStyle(fontSize: 11, color: C.faint))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.868 R8 wave 1: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'Notary desk',
      tabs: const ['Today', 'Documents', 'Register', 'Apostille', 'Rules'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      busy: _busy,
      onRefresh: _load,
      body: () => switch (_tab) { 0 => _today(), 1 => _docsTab(), 2 => _registerTab(), 3 => _apostilleTab(), _ => _rulesTab() },
    );
  }
}

/// One document: text, blanks, checks, stamp + e-stamp steps, edit facts / party / text, final print card, register.
class NotaryDocPage extends StatefulWidget {
  const NotaryDocPage({super.key, required this.app, required this.docRef, this.kinds = const {}});
  final Santosh app;
  final String docRef;
  final Map<String, dynamic> kinds;
  @override
  State<NotaryDocPage> createState() => _NotaryDocPageState();
}

class _NotaryDocPageState extends State<NotaryDocPage> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _card;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/notary/docs/${widget.docRef}'));
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

  String get _id => _s(_d?['id']);

  Future<void> _editFacts() async {
    final fields = _list(_d?['fields']);
    final facts = _m(_d?['facts']);
    final f = await _form(context, 'Facts badlo', [for (final x in fields) (_s(x['key']), _s(x['label']))],
        ok: 'Save', initial: {for (final x in fields) _s(x['key']): facts[x['key']] is List ? _strs(facts[x['key']]).join('\n') : _s(facts[x['key']])},
        long: const {'statements', 'powers', 'matter', 'act'});
    if (f == null) return;
    await _run('PATCH', '/api/notary/docs/$_id', {'facts': f});
  }

  Future<void> _editParty() async {
    final ps = _list(_d?['parties']);
    final p = ps.isNotEmpty ? ps.first : <String, dynamic>{};
    final f = await _form(context, 'Party badlo', _partyFields, ok: 'Save', initial: {for (final (k, _) in _partyFields) k: k == 'id_number' ? '' : _s(p[k])});
    if (f == null) return;
    await _run('PATCH', '/api/notary/docs/$_id', {'party': f});
  }

  Future<void> _editText() async {
    final f = await _form(context, 'Write it myself (full text)', const [('text', 'Text')], ok: 'Save', initial: {'text': _s(_d?['text'])}, long: const {'text'});
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('PATCH', '/api/notary/docs/$_id', {'text': f['text']});
  }

  Future<void> _stamp() async {
    final f = await _form(context, 'Stamp (party / aapne kharida)', const [
      ('ref', 'e-Stamp UIN / e-SBTR / franking / stamp paper no.'),
      ('mode', 'e_stamp / esbtr / franking / paper / none'),
      ('state', 'State (badalni ho to)'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/notary/docs/$_id/stamp', f);
  }

  Future<void> _print() async {
    final r = await _run('POST', '/api/notary/docs/$_id/print');
    if (r != null && _m(r['doc']).isNotEmpty && _s(_m(r['doc'])['status']) == 'waiting' && mounted) setState(() => _card = r);
  }

  Future<void> _lang() async {
    final l = await _pick(context, 'Copy in which language?', const {'en': 'English', 'hi': 'हिन्दी', 'mr': 'मराठी', 'other': 'Another language (translated by the writer)'});
    if (l == null || !mounted) return;
    if (l == 'other') {
      final f = await _form(context, 'Translation', const [('to', 'Language (e.g. Gujarati)')]);
      if (f == null || (f['to'] ?? '').isEmpty) return;
      await _run('POST', '/api/notary/docs/$_id/translate', f);
      return;
    }
    await _run('POST', '/api/notary/docs/$_id/copy', {'lang': l});
  }

  Future<void> _notarise() async {
    final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              title: const Text('Did you notarise it?'),
              content: const Text('Write in the register only when the party has signed in front of you, you have seen the original ID, and you have sealed / signed.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Not now')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, I did it')),
              ],
            ));
    if (ok != true || !mounted) return;
    final f = await _form(context, 'Fee and charges (what you took)', const [
      ('fee', 'Notarial fee ₹ (blank = your set fee)'),
      ('typing', 'Typing / drafting ₹'),
      ('xerox', 'Xerox / print ₹'),
      ('mode', 'cash / upi'),
      ('ref', 'UPI ref (ho to)'),
    ], ok: 'Write in register');
    if (f == null) return;
    await _run('POST', '/api/notary/register', {
      'doc': _id,
      if (_n(f['fee']) != null) 'fee': _n(f['fee']),
      'charges': {if (_n(f['typing']) != null) 'typing': _n(f['typing']), if (_n(f['xerox']) != null) 'xerox': _n(f['xerox'])},
      'mode': f['mode'] ?? 'cash',
      'ref': f['ref'] ?? '',
    });
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final st = _s(d?['status']);
    final stamp = _m(d?['stamp']);
    return DeskPage(
      title: d == null ? 'Document' : '${_s(d['number'])} · ${_s(d['kind_label'])}',
      loading: d == null,
      onRefresh: _load,
      body: () => d == null ? const SizedBox.shrink() : ListView(padding: const EdgeInsets.all(16), children: [
              if (_busy) const LinearProgressIndicator(minHeight: 2),
              Row(children: [
                Pill(_stLabel(st), fg: _stColor(st)),
                const SizedBox(width: 6),
                Pill(_s(d['lang_label'])),
                const SizedBox(width: 6),
                Pill('Stamp ${_s(stamp['amount_text'])}', fg: stamp['amount'] == null && _s(stamp['mode']) != 'none' ? C.warn : C.chip),
              ]),
              const SizedBox(height: 10),
              for (final p in _list(d['parties']))
                Text('${_s(p['name'])}${_s(p['id_masked']).isEmpty ? '' : ' · ${_s(p['id_kind'])} ${_s(p['id_masked'])} (locker)'}',
                    style: const TextStyle(fontSize: 13, color: C.muted)),
              const SizedBox(height: 10),
              for (final c in _list(d['checks']))
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('${_s(c['level']) == 'block' ? '⛔' : (_s(c['level']) == 'warn' ? '⚠' : 'ℹ')} ${_s(c['text'])}',
                      style: TextStyle(fontSize: 12.5, color: _s(c['level']) == 'block' ? C.bad : (_s(c['level']) == 'warn' ? C.warn : C.muted))),
                ),
              const SizedBox(height: 10),
              Glass(child: SelectableText(_s(d['text']), style: const TextStyle(fontSize: 13.5, height: 1.5))),
              const SizedBox(height: 12),
              const Caption('STAMP STEPS (you / the party yourselves)'),
              for (final t in _strs(d['stamp_steps'])) Text('• $t', style: const TextStyle(fontSize: 12.5)),
              const SizedBox(height: 12),
              if (st == 'draft' || st == 'rejected') ...[
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(label: 'Facts', icon: Icons.edit_note_rounded, height: 40, onTap: _busy ? null : _editFacts),
                  GlassButton(label: 'Party', icon: Icons.person_rounded, height: 40, onTap: _busy ? null : _editParty),
                  GlassButton(label: 'Write it myself', icon: Icons.edit_rounded, height: 40, onTap: _busy ? null : _editText),
                  GlassButton(label: 'Stamp no.', icon: Icons.approval_rounded, height: 40, onTap: _busy ? null : _stamp),
                ]),
                const SizedBox(height: 10),
                GradientButton(label: 'Final print ka card', icon: Icons.print_rounded, height: 46, onTap: _busy ? null : _print),
              ],
              if (_card != null || st == 'waiting') ...[
                const SizedBox(height: 10),
                NotaryPrintCard(app: widget.app, data: _card ?? {'doc': d}, onDone: _load),
              ],
              if (st == 'final') ...[
                GlassButton(label: 'Notarised: write in the register', icon: Icons.verified_rounded, height: 44, onTap: _busy ? null : _notarise),
                const SizedBox(height: 6),
                GlassButton(
                    label: 'Desk: the notary did it',
                    icon: Icons.done_all_rounded,
                    height: 40,
                    onTap: _busy
                        ? null
                        : () async {
                            final f = await _form(context, 'Kis notary ne?', const [('notary', 'Notary name'), ('on', 'Tareekh')]);
                            if (f != null) await _run('POST', '/api/notary/docs/$_id/executed', f);
                          }),
              ],
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                GlassButton(label: 'Another language', icon: Icons.translate_rounded, height: 40, onTap: _busy ? null : _lang),
                GlassButton(label: 'Copy', icon: Icons.copy_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/notary/docs/$_id/copy', {})),
                GlassButton(
                    label: 'Delete details (DPDP)',
                    icon: Icons.delete_sweep_rounded,
                    height: 40,
                    color: C.bad,
                    onTap: _busy ? null : () => _run('POST', '/api/notary/docs/$_id/forget')),
              ]),
              const SizedBox(height: 10),
              const Text('This is a draft / information, not legal advice: confirm with a lawyer. PDF / Word files come in the chat.',
                  style: TextStyle(fontSize: 11, color: C.faint)),
            ]),
    );
  }
}

/// notary_print: final print ONLY on her tap (hash-checked on the server). Also in calls.
class NotaryPrintCard extends StatefulWidget {
  const NotaryPrintCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<NotaryPrintCard> createState() => _NotaryPrintCardState();
}

class _NotaryPrintCardState extends State<NotaryPrintCard> {
  bool _busy = false;
  late Map<String, dynamic> _doc = _m(widget.data['doc']);

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/notary/docs/${_s(_doc['id'])}/decide', body: {'yes': yes, 'hash': _s(_doc['hash'])}));
      if (mounted) {
        setState(() => _doc = {..._doc, ..._m(r['doc'])});
        _snack(context, _s(r['say']));
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
    final d = _doc;
    final st = _s(d['status']);
    final stamp = _m(d['stamp']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.print_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(d['number'])} · ${_s(d['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_stLabel(st), fg: _stColor(st)),
        ]),
        Text(
            [
              _list(d['parties']).map((p) => _s(p['name'])).join(', '),
              _s(d['lang_label']),
              'Stamp ${_s(stamp['amount_text'])} ${_s(stamp['mode_label'])}',
            ].where((x) => x.trim().isNotEmpty).join(' · '),
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (_s(widget.data['say']).isNotEmpty) Text(_s(widget.data['say']), style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, final print', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'draft') const Text('The document changed after the card: make a new card.', style: TextStyle(fontSize: 12, color: C.warn)),
        const Text('Final = PDF + Word without the DRAFT mark. Signing / sealing / notarising is your job.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// notary_doc: a draft (updated in place); tap opens the document page.
class NotaryDocCard extends StatelessWidget {
  const NotaryDocCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final d = _m(data['doc']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotaryDocPage(app: app, docRef: _s(d['id'])))),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.gavel_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(d['number'])} · ${_s(d['kind_label'])} (${_s(d['lang_label'])})', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_stLabel(_s(d['status'])), fg: _stColor(_s(d['status']))),
          ]),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
          if (_strs(d['blanks']).isNotEmpty)
            Text('Khaali: ${_strs(d['blanks']).take(5).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        ]),
      ),
    );
  }
}

/// notary_entry: register line + fee receipt that were just written.
class NotaryEntryCard extends StatelessWidget {
  const NotaryEntryCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final e = _m(data['entry']);
    final r = _m(data['receipt']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.menu_book_rounded, color: C.ok),
          const SizedBox(width: 8),
          Expanded(child: Text('Register ${_s(e['serial'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          if (r.isNotEmpty) Pill('₹${_s(r['total'])}', fg: C.ok),
        ]),
        Text(_s(e['act_label']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final x in _list(e['executants'])) Text(_s(x['name']), style: const TextStyle(fontSize: 12.5)),
        if (r.isNotEmpty) Text('Receipt ${_s(r['number'])} · ${_s(r['mode'])}', style: const TextStyle(fontSize: 12.5)),
        const Text('You took the fee; Hoola only recorded it.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// notary_alert / notary_day: renewal / annual return reminders and the morning note.
class NotaryNoteCard extends StatelessWidget {
  const NotaryNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.gavel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4))),
          IconButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotaryScreen(app: app))),
              icon: const Icon(Icons.open_in_new_rounded, size: 18)),
        ]),
      );
}
