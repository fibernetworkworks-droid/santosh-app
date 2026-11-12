/// Profile > PI Desk (private investigator DESK for businesses).
/// Aaj (her taps waiting, fraud not yet reported to 1930, consent pending, data to delete) · Cases (business due diligence,
/// document jaanch, dhokhe ki saboot file, employee verification with consent) · Niyam (firm, retention, what the desk NEVER does).
/// Every fact shows its source; document checks are "signals, not verdicts". Sending any report / evidence pack / complaint to
/// anyone happens ONLY on her tap here. The desk never tracks, locates or profiles a person (refused on the server).
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'desk/desk_kit.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _lvColor(String lv) => switch (lv) {
      'strong' || 'flag' || 'several' => C.bad,
      'warn' || 'some' || 'waiting' => C.warn,
      'ok' || 'none' || 'shared' => C.ok,
      _ => C.chip,
    };

const _kinds = <String, String>{
  'due_diligence': 'Business due diligence',
  'doc_check': 'Document check',
  'fraud_file': 'Fraud evidence file',
  'employee_verify': 'Employee verification (consent se)',
};

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}, String? note}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (note != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(note, style: const TextStyle(fontSize: 12, color: C.faint))),
          for (final (k, label) in fields)
            TextField(
                controller: c[k],
                decoration: InputDecoration(labelText: label),
                maxLines: (k == 'text' || k == 'purpose' || k == 'fact' || k == 'what' || k == 'address') ? 4 : 1),
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

Future<void> _showText(BuildContext context, String title, String text, {Map<String, dynamic> links = const {}, List<String> steps = const []}) =>
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: .7,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 8),
          for (final s in steps) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• $s', style: const TextStyle(fontSize: 13))),
          if (steps.isNotEmpty) const SizedBox(height: 8),
          SelectableText(text, style: const TextStyle(fontSize: 12.5, height: 1.4)),
          const SizedBox(height: 10),
          for (final e in links.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: GlassButton(
                  label: switch (e.key) {
                    'whatsapp' => 'Open WhatsApp draft',
                    'email' => 'Open email draft',
                    'call_1930' => 'Call 1930',
                    'portal' => 'Open cybercrime.gov.in',
                    _ => e.key,
                  },
                  icon: Icons.open_in_new_rounded,
                  onTap: () => Native.openExternal(url: _s(e.value))),
            ),
          const Text('Hoola sends or files nothing by itself: you do it.', style: TextStyle(fontSize: 11, color: C.faint)),
        ]),
      ),
    );

class PideskScreen extends StatefulWidget {
  const PideskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PideskScreen> createState() => _PideskScreenState();
}

class _PideskScreenState extends State<PideskScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/pidesk'));
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
      .push(MaterialPageRoute(builder: (_) => PideskCasePage(app: widget.app, caseRef: ref)))
      .then((_) => _load());

  Future<void> _newCase() async {
    final kind = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (d) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final e in _kinds.entries)
            ListTile(
                leading: Icon(switch (e.key) {
                  'due_diligence' => Icons.business_rounded,
                  'doc_check' => Icons.fact_check_rounded,
                  'fraud_file' => Icons.gavel_rounded,
                  _ => Icons.badge_rounded,
                }, color: C.accent),
                title: Text(e.value),
                onTap: () => Navigator.pop(d, e.key)),
        ]),
      ),
    );
    if (kind == null || !mounted) return;
    final fields = <(String, String)>[
      ('title', 'Case name'),
      if (kind != 'fraud_file') ('subject_name', kind == 'employee_verify' ? 'Candidate name' : 'Business name'),
      if (kind == 'due_diligence' || kind == 'doc_check') ('subject_kind', 'Who: company / firm / llp / vendor / supplier / customer / dealer'),
      if (kind == 'due_diligence') ('identifiers', 'GSTIN / CIN / Udyam / FSSAI (comma se)'),
      if (kind == 'employee_verify') ('role', 'For which job'),
      ('purpose', 'Purpose (why check?)'),
    ];
    final f = await _form(context, _kinds[kind]!, fields,
        ok: 'Open', note: 'Only businesses, your papers and your evidence. This desk does not trace, watch or profile any person.');
    if (f == null) return;
    final body = <String, dynamic>{...f, 'kind': kind};
    if ((f['identifiers'] ?? '').isNotEmpty) {
      body['identifiers'] = f['identifiers']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    }
    final r = await _run('POST', '/api/pidesk/cases', body);
    if (r != null && _s(r['id']).isNotEmpty && mounted) _open(_s(r['id']));
  }

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      GradientButton(label: 'New case', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newCase),
      const SizedBox(height: 12),
      for (final (key, title) in const [
        ('waiting', 'YOUR YES PENDING'),
        ('not_reported', '1930 / CYBERCRIME REPORT BAAKI'),
        ('need_consent', 'CONSENT BAAKI'),
        ('forget_due', 'TIME TO DELETE DATA'),
      ])
        if (_strs(day[key]).isNotEmpty) ...[
          Caption(title),
          for (final t in _strs(day[key])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
          const SizedBox(height: 8),
        ],
    ]);
  }

  Widget _casesTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New case', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newCase),
        const SizedBox(height: 12),
        for (final c in _list(_d?['cases']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _open(_s(c['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.folder_shared_rounded, color: C.accent, size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_s(c['status']), fg: _s(c['status']) == 'open' ? C.ok : C.chip),
                  ]),
                  Text(
                      [
                        _s(c['kind_label']),
                        _s(_m(c['subject'])['name']),
                        '${_s(_m(c['counts'])['findings'])} tathya',
                        if ((_m(c['counts'])['flags'] ?? 0) != 0) '${_s(_m(c['counts'])['flags'])} red flags',
                      ].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            ),
          ),
        if (_list(_d?['cases']).isEmpty) const Text('No cases yet.', style: TextStyle(color: C.muted)),
      ]);

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Niyam / firm', const [
      ('name', 'Your name'),
      ('firm', 'Firm'),
      ('address', 'Address (in the complaint draft)'),
      ('phone', 'Mobile'),
      ('email', 'Email'),
      ('retention_days', 'Delete closed-case data after how many days (30-3650)'),
    ], ok: 'Save', initial: {for (final k in ['name', 'firm', 'address', 'phone', 'email', 'retention_days']) k: _s(st[k])});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (f['retention_days'] != null) body['retention_days'] = _n(f['retention_days'])?.toInt();
    await _run('PUT', '/api/pidesk/settings', body);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['firm']).isEmpty ? (_s(st['name']).isEmpty ? 'Enter your name / firm' : _s(st['name'])) : _s(st['firm']),
              style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Closed-case data is set to be deleted after ${_s(st['retention_days'])} days · refused requests: ${_s(st['refused'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('THIS DESK NEVER DOES'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
      const SizedBox(height: 8),
      Text(_s(_d?['disclaimer']), style: const TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.868 R8 wave 1: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'PI desk',
      tabs: const ['Today', 'Cases', 'Rules'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      busy: _busy,
      onRefresh: _load,
      body: () => switch (_tab) { 0 => _today(), 1 => _casesTab(), _ => _rulesTab() },
    );
  }
}

/// One case file: findings with sources, evidence with SHA-256, timeline, custody check, report / share.
class PideskCasePage extends StatefulWidget {
  const PideskCasePage({super.key, required this.app, required this.caseRef});
  final Santosh app;
  final String caseRef;
  @override
  State<PideskCasePage> createState() => _PideskCasePageState();
}

class _PideskCasePageState extends State<PideskCasePage> {
  Map<String, dynamic>? _c;
  bool _busy = false;

  String get _ref => _s(_c?['id']).isEmpty ? widget.caseRef : _s(_c?['id']);
  String get _kind => _s(_c?['kind']);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = _m(await widget.app.api!.call('GET', '/api/pidesk/cases/${Uri.encodeComponent(widget.caseRef)}'));
      if (mounted) setState(() => _c = c);
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

  String get _base => '/api/pidesk/cases/${Uri.encodeComponent(_ref)}';

  Future<String?> _pickFile() async {
    final conv = widget.app.conversationId;
    if (conv == null) {
      _snack(context, 'Let the chat open first.');
      return null;
    }
    final files = await pickAttachmentsOfType(context, FileType.any);
    if (files.isEmpty) return null;
    try {
      final r = await widget.app.api!.chatFile(conv, files.first.name, files.first.bytes);
      return _s(r['file_id']);
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    }
  }

  Future<void> _ids() async {
    final f = await _form(context, 'GSTIN / CIN / LLPIN / Udyam / FSSAI', const [('ids', 'Number (comma se)')], ok: 'Check');
    if (f == null || (f['ids'] ?? '').isEmpty) return;
    await _run('POST', '$_base/ids', {'identifiers': f['ids']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList()});
  }

  Future<void> _page() async {
    final f = await _form(context, 'Read the official page', const [('url', 'Link (https://...)')],
        ok: 'Read', note: 'GST search, MCA master data, Udyam verify, FoSCoS, eCourts or the business\'s own website. Not social media.');
    if (f == null || (f['url'] ?? '').isEmpty) return;
    await _run('POST', '$_base/page', {'url': f['url']});
  }

  Future<void> _paste() async {
    final f = await _form(context, 'Paste the result', const [('where', 'From where (GST / MCA / eCourts)'), ('source_url', 'Link'), ('text', 'Text')],
        ok: 'Add', note: 'Open pages with a CAPTCHA yourself, then copy the result and paste it here.');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '$_base/paste', f);
  }

  Future<void> _news() async {
    final f = await _form(context, 'Web / news search', const [('query', 'More words (the business name is added automatically)')], ok: 'Search');
    if (f == null) return;
    await _run('POST', '$_base/news', {'query': f['query'] ?? ''});
  }

  Future<void> _note() async {
    final f = await _form(context, 'Tathya jodo', const [('fact', 'What was found'), ('source_url', 'Source link (ho to)')], ok: 'Add');
    if (f == null || (f['fact'] ?? '').isEmpty) return;
    await _run('POST', '$_base/note', f);
  }

  Future<void> _evidence() async {
    final kind = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (d) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, l) in const [
            ('chat_export', 'WhatsApp chat export (.txt / .zip)'),
            ('receipt', 'Receipt / payment screenshot'),
            ('screenshot', 'Screenshot'),
            ('bank_sms', 'Bank SMS / statement'),
            ('email', 'Email'),
            ('document', 'Document'),
            ('other', 'Something else'),
          ])
            ListTile(title: Text(l), onTap: () => Navigator.pop(d, k)),
        ]),
      ),
    );
    if (kind == null) return;
    final fid = await _pickFile();
    if (fid == null || fid.isEmpty) return;
    final f = await _form(context, 'About the evidence', const [('note', 'Note'), ('happened_at', 'When it happened (DD-MM-YYYY)')], ok: 'Add');
    await _run('POST', '$_base/evidence', {'file_id': fid, 'kind': kind, ...?f});
  }

  Future<void> _docCheck() async {
    final fid = await _pickFile();
    if (fid == null || fid.isEmpty) return;
    final f = await _form(context, 'What the paper says (to compare)', const [
      ('claimed_date', 'Date on the paper (DD-MM-YYYY)'),
      ('gstin', 'GSTIN'),
      ('doc_no', 'Bill number'),
      ('total', 'Total'),
    ], ok: 'Check');
    final exp = <String, dynamic>{
      if ((f?['gstin'] ?? '').isNotEmpty) 'gstin': f!['gstin'],
      if ((f?['doc_no'] ?? '').isNotEmpty) 'doc_no': f!['doc_no'],
      if ((f?['total'] ?? '').isNotEmpty) 'total': _n(f!['total']),
    };
    final r = await _run('POST', '$_base/doc_check', {'file_id': fid, 'claimed_date': f?['claimed_date'] ?? '', 'expect': exp});
    if (r != null && mounted) _showSignals(r);
  }

  void _showSignals(Map<String, dynamic> r) => showModalBottomSheet(
        context: context,
        backgroundColor: C.bgBottom,
        builder: (_) => ListView(padding: const EdgeInsets.all(16), children: [
          Text(_s(r['say']), style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          for (final s in _list(r['signals']))
            ListTile(
              dense: true,
              leading: Icon(Icons.circle, size: 12, color: _lvColor(_s(s['level']))),
              title: Text(_s(s['signal'])),
              subtitle: Text(_s(s['why'])),
            ),
        ]),
      );

  Future<void> _event() async {
    final f = await _form(context, 'Add an incident', const [('at', 'When (DD-MM-YYYY HH:MM)'), ('what', 'What happened'), ('amount', 'Amount'), ('ref', 'UTR / ref')],
        ok: 'Add');
    if (f == null || (f['what'] ?? '').isEmpty) return;
    await _run('POST', '$_base/event', {...f, 'amount': _n(f['amount'])});
  }

  Future<void> _money() async {
    final f = await _form(context, 'Loss', const [
      ('lost', 'How much money was lost'),
      ('mode', 'How (UPI / card / netbanking / cash)'),
      ('refs', 'UTR / ref (comma se)'),
      ('suspect', 'The other party\'s identity as seen (name / UPI ID / number / website)'),
    ], ok: 'Save', note: 'Hoola does not trace the other party; this is for a police complaint.');
    if (f == null) return;
    await _run('POST', '$_base/money', {
      'lost': _n(f['lost']),
      'mode': f['mode'] ?? '',
      'refs': (f['refs'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      'suspect': f['suspect'] ?? '',
    });
  }

  Future<void> _complaint(String to) async {
    final r = await _run('POST', '$_base/complaint', {'to': to});
    if (r != null && mounted) {
      await _showText(context, 'Shikayat DRAFT', _s(r['text']), links: _m(r['links']), steps: _strs(r['steps']));
    }
  }

  Future<void> _reported() async {
    final f = await _form(context, 'Report filed', const [('where', 'Where: cyber / police / bank'), ('ref', 'Complaint / acknowledgement number')],
        ok: 'Save');
    if (f == null) return;
    await _run('POST', '$_base/reported', f);
  }

  Future<void> _consent() async {
    final txt = await _call(context, widget.app, 'GET', '$_base/consent_text');
    if (txt != null && mounted) await _showText(context, 'Consent form (the candidate signs)', _s(txt['text']));
    if (!mounted) return;
    final fid = await _pickFile();
    if (fid == null || fid.isEmpty) return;
    final f = await _form(context, 'Signed consent', const [
      ('signed_on', 'Date of signing (DD-MM-YYYY)'),
      ('checks', 'Which check: identity, education, employment, address'),
      ('days', 'How many days to keep the data (30-730)'),
    ], ok: 'Add');
    if (f == null) return;
    await _run('POST', '$_base/consent', {
      'file_id': fid,
      'signed_on': f['signed_on'] ?? '',
      'checks': (f['checks'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      'days': _n(f['days'])?.toInt() ?? 180,
    });
  }

  Future<void> _reference() async {
    final f = await _form(context, 'Pushti ka draft', const [('about', 'education / employment'), ('to_name', 'Kisko'), ('to_contact', 'Email')], ok: 'Make');
    if (f == null) return;
    final r = await _run('POST', '$_base/reference', f);
    if (r != null && mounted) await _showText(context, 'Draft (you send it)', _s(r['text']), links: {'email': _s(r['link'])});
  }

  Future<void> _share() async {
    final files = _m(_c?['files']);
    if (files.isEmpty) {
      _snack(context, 'Make a report / pack / complaint first.');
      return;
    }
    final what = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (d) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final k in files.keys) ListTile(title: Text(k), subtitle: Text(_s(_m(files[k])['name'])), onTap: () => Navigator.pop(d, k)),
        ]),
      ),
    );
    if (what == null || !mounted) return;
    final f = await _form(context, 'Whom to send to', const [('to_name', 'Naam (vakil / police / client)'), ('to_contact', 'Email / mobile')],
        ok: 'Make card', note: 'A card for your yes will come before anything is sent.');
    if (f == null || (f['to_name'] ?? '').isEmpty) return;
    await _run('POST', '$_base/share', {'what': what, ...f});
  }

  Future<void> _custody() async {
    final r = await _call(context, widget.app, 'GET', '$_base/custody');
    if (r == null || !mounted) return;
    final lines = _list(r['custody']).map((x) => '${_s(x['seq'])}. ${_s(x['at'])} ${_s(x['action'])} — ${_s(x['detail'])}').join('\n');
    await _showText(context, _s(_m(r['check'])['say']), lines);
  }

  List<Widget> _actions() {
    final b = <(String, IconData, Future<void> Function())>[];
    if (_kind == 'due_diligence') {
      b.addAll([
        ('Check a number', Icons.pin_rounded, _ids),
        ('Read the official page', Icons.account_balance_rounded, _page),
        ('Result paste', Icons.content_paste_rounded, _paste),
        ('News search', Icons.newspaper_rounded, _news),
      ]);
    }
    if (_kind == 'employee_verify') {
      b.addAll([('Consent jodo', Icons.how_to_reg_rounded, _consent), ('Pushti ka draft', Icons.mail_rounded, _reference)]);
    }
    b.add(('Check a paper', Icons.fact_check_rounded, _docCheck));
    if (_kind == 'fraud_file') {
      b.addAll([
        ('Add evidence', Icons.attach_file_rounded, _evidence),
        ('Add an incident', Icons.timeline_rounded, _event),
        ('Loss', Icons.currency_rupee_rounded, _money),
        ('1930 complaint', Icons.local_police_rounded, () => _complaint('cyber')),
        ('Thana complaint', Icons.description_rounded, () => _complaint('police')),
        ('Bank complaint', Icons.account_balance_wallet_rounded, () => _complaint('bank')),
        ('Report filed', Icons.task_alt_rounded, _reported),
        ('Evidence ZIP', Icons.archive_rounded, () async => _run('POST', '$_base/pack')),
      ]);
    } else {
      b.add(('Add evidence', Icons.attach_file_rounded, _evidence));
    }
    b.addAll([
      ('Note jodo', Icons.edit_note_rounded, _note),
      ('Make report', Icons.picture_as_pdf_rounded, () async => _run('POST', '$_base/report')),
      ('Send (card)', Icons.send_rounded, _share),
      ('Custody check', Icons.verified_user_rounded, _custody),
    ]);
    return [
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final (l, i, fn) in b) GlassButton(label: l, icon: i, height: 40, onTap: _busy ? null : () => fn()),
      ]),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    return DeskPage(
      title: c == null ? 'Case' : '${_s(c['number'])} · ${_s(c['title'])}',
      loading: c == null,
      onRefresh: _load,
      actions: [
          PopupMenuButton<String>(
            onSelected: (v) async {
              if (v == 'close') await _run('POST', '$_base/close');
              if (v == 'forget') {
                final ok = await showDialog<bool>(
                    context: context,
                    builder: (d) => AlertDialog(
                          title: const Text('Data mitaaye?'),
                          content: const Text('The evidence files and personal details will be deleted for good.'),
                          actions: [
                            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('No')),
                            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, wipe')),
                          ],
                        ));
                if (ok == true) {
                  await _call(context, widget.app, 'POST', '$_base/forget');
                  if (mounted) Navigator.of(context).pop();
                }
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'close', child: Text('Close case')),
              PopupMenuItem(value: 'forget', child: Text('Delete data (closed case)')),
            ],
          ),
        ],
body: () => c == null ? const SizedBox.shrink() : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(c['kind_label']), style: const TextStyle(fontWeight: FontWeight.w800)),
                    if (_s(_m(c['subject'])['name']).isNotEmpty) Text(_s(_m(c['subject'])['name']), style: const TextStyle(color: C.muted)),
                    if (_s(c['purpose']).isNotEmpty) Text(_s(c['purpose']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (_kind == 'employee_verify')
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Pill(c['consent_ok'] == true ? 'Consent linked: ${_strs(_m(c['consent'])['checks']).join(', ')}' : 'Consent pending: no check',
                            fg: c['consent_ok'] == true ? C.ok : C.warn),
                      ),
                    if (_m(c['money'])['lost'] != null)
                      Text('Loss: Rs ${_s(_m(c['money'])['lost'])} · report: ${_m(_m(c['money'])['reported']).keys.join(', ').isEmpty ? 'not yet' : _m(_m(c['money'])['reported']).keys.join(', ')}',
                          style: const TextStyle(color: C.warn, fontSize: 12.5)),
                  ]),
                ),
                const SizedBox(height: 12),
                ..._actions(),
                const SizedBox(height: 14),
                for (final w in _list(c['waiting_shares'])) PideskShareCard(app: widget.app, data: {'share': w}),
                if (_list(c['findings']).isNotEmpty) const Caption('FACTS (SOURCE FOR EACH)'),
                for (final f in _list(c['findings']))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Glass(
                      padding: const EdgeInsets.all(10),
                      border: _s(f['level']) == 'flag' ? C.bad.withOpacity(.5) : null,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(children: [
                          Pill(_s(f['section']), fg: _lvColor(_s(f['level']))),
                          if (_s(f['level']) == 'flag') ...[const SizedBox(width: 6), const Pill('RED FLAG', fg: C.bad)],
                        ]),
                        const SizedBox(height: 4),
                        Text(_s(f['fact']), style: const TextStyle(fontSize: 13)),
                        Press(
                          onTap: _s(f['url']).startsWith('http') ? () => Native.openExternal(url: _s(f['url'])) : null,
                          child: Text(_s(f['source']) + (_s(f['url']).isEmpty ? '' : ' ↗'), style: const TextStyle(fontSize: 11.5, color: C.faint)),
                        ),
                      ]),
                    ),
                  ),
                if (_list(c['evidence']).isNotEmpty) const Caption('EVIDENCE (SHA-256)'),
                for (final e in _list(c['evidence']))
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.insert_drive_file_rounded, color: _lvColor(_s(e['level']))),
                    title: Text('${_s(e['n'])} · ${_s(e['name'])}'),
                    subtitle: Text('${_s(e['kind'])} · ${_s(e['sha256']).length > 16 ? _s(e['sha256']).substring(0, 16) : _s(e['sha256'])}…'
                        '${_list(e['signals']).isEmpty ? '' : ' · ${_list(e['signals']).length} signals'}'),
                    onTap: _list(e['signals']).isEmpty
                        ? null
                        : () => _showSignals({'say': '${_s(e['n'])} ke signals (not verdicts)', 'signals': e['signals']}),
                  ),
                if (_list(c['timeline']).isNotEmpty) const Caption('TIMELINE'),
                for (final t in _list(c['timeline']).where((t) => t['important'] == true).take(60))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text('${_s(t['at']).replaceAll('T', ' ')} · ${_s(t['what'])}', style: const TextStyle(fontSize: 12.5)),
                  ),
                const SizedBox(height: 16),
                const Text('Information / signals, not verdicts. Confirm with a lawyer / the police.', style: TextStyle(fontSize: 11, color: C.faint)),
              ]),
            ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards

/// pidesk_share: waits for HER tap (Haan bhejo / Nahi). Only this tap lets a report / pack / complaint go to anyone.
class PideskShareCard extends StatefulWidget {
  const PideskShareCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<PideskShareCard> createState() => _PideskShareCardState();
}

class _PideskShareCardState extends State<PideskShareCard> {
  String _state = '';
  bool _busy = false;

  Map<String, dynamic> get _sh => _m(widget.data['share']);

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/pidesk/shares/${_s(_sh['id'])}/decide', {'yes': yes, 'hash': _s(_sh['hash'])});
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r != null) _state = _s(_m(r['share'])['status']);
    });
    if (r != null && yes && _m(r['links']).isNotEmpty && mounted) {
      await _showText(context, 'You send it', _s(r['text']), links: _m(r['links']));
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = _state.isNotEmpty ? _state : _s(_sh['status']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        border: st == 'waiting' ? C.warn.withOpacity(.6) : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.send_rounded, color: C.accent, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(_sh['case'])} ${_s(_sh['what'])} → ${_s(_sh['to_name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(st, fg: _lvColor(st)),
          ]),
          if (_s(_sh['to_contact']).isNotEmpty) Text(_s(_sh['to_contact']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(widget.data['say']).isNotEmpty) Text(_s(widget.data['say']), style: const TextStyle(fontSize: 12.5)),
          if (st == 'waiting') ...[
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: GradientButton(label: 'Yes, let it be sent', height: 42, onTap: _busy ? null : () => _decide(true))),
              const SizedBox(width: 8),
              GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
            ]),
          ],
        ]),
      ),
    );
  }
}

/// pidesk_report: report DRAFT made (summary, red flags, gaps). Tap = open the case.
class PideskReportCard extends StatelessWidget {
  const PideskReportCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PideskCasePage(app: app, caseRef: _s(data['case'])))),
          child: Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.picture_as_pdf_rounded, color: C.accent, size: 18),
                const SizedBox(width: 8),
                Expanded(child: Text('${_s(data['case'])} report DRAFT', style: const TextStyle(fontWeight: FontWeight.w800))),
                if ((data['flags'] ?? 0) != 0) Pill('${_s(data['flags'])} red flags', fg: C.bad),
              ]),
              const SizedBox(height: 4),
              Text(_s(data['summary']), style: const TextStyle(fontSize: 13)),
              for (final g in _strs(data['gaps']).take(3)) Text('• $g', style: const TextStyle(fontSize: 12, color: C.warn)),
            ]),
          ),
        ),
      );
}

/// pidesk_doc: document check signals (not verdicts).
class PideskDocCard extends StatelessWidget {
  const PideskDocCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Glass(
          border: _lvColor(_s(data['level'])).withOpacity(.5),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(Icons.fact_check_rounded, color: _lvColor(_s(data['level'])), size: 18),
              const SizedBox(width: 8),
              Expanded(child: Text('${_s(data['n'])} ${_s(data['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            ]),
            const SizedBox(height: 4),
            Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
            for (final s in _list(data['signals']).where((s) => _s(s['level']) != 'info').take(4))
              Text('• ${_s(s['signal'])}', style: TextStyle(fontSize: 12, color: _lvColor(_s(s['level'])))),
          ]),
        ),
      );
}

/// pidesk_case (case opened / updated) and pidesk_alert (reminders): a short line, tap opens the desk.
class PideskNoteCard extends StatelessWidget {
  const PideskNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final cs = _m(data['case']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => _s(cs['id']).isNotEmpty ? PideskCasePage(app: app, caseRef: _s(cs['id'])) : PideskScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.folder_shared_rounded, color: C.accent, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
