/// Profile > Contract manager (Contracts Sahayak).
/// Aaj (deadlines, her taps waiting, risky drafts, stamp pending) · Contracts (repository: add from a file or pasted text) ·
/// Renewal (notice deadlines + obligations) · Playbook (her standard positions) · Niyam (her business, seat city, state, stamp rates).
/// ContractPage: summary, risks in Hinglish with source links, clauses, redline (a NEW Word copy with track changes), versions,
/// obligations, and the cards that ONLY her tap decides: send to the other side, e-sign steps, e-stamp steps (fingerprint once a
/// phone key is set up), notices. Hoola is not a lawyer: draft / jaankari, vakil se pakka karwaiye.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());

const _draftLine = 'Draft / jaankari hai, legal advice nahi: vakil / CA / CS se pakka karwaiye.';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _lvlColor(String l) => switch (l) {
      'high' || 'blocked' || 'rejected' => C.bad,
      'medium' || 'waiting' || 'stale' => C.warn,
      'low' => C.chip,
      'ok' || 'approved' || 'done' || 'active' || 'signed' => C.ok,
      _ => C.chip,
    };

String _lvlText(String l) => switch (l) { 'high' => 'BADI', 'medium' => 'BEECH', 'low' => 'CHHOTI', _ => l.toUpperCase() };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}, Set<String> multi = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: multi.contains(k) ? 6 : 1),
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
    final r = await app.api!.call(method, path, body: body);
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<String?> _pickFile(BuildContext context, Santosh app) async {
  final conv = app.conversationId;
  if (conv == null) {
    _snack(context, 'Pehle chat khulne dijiye.');
    return null;
  }
  final files = await pickAttachmentsOfType(context, FileType.any);
  if (files.isEmpty) return null;
  try {
    final r = await app.api!.chatFile(conv, files.first.name, files.first.bytes);
    return _s(r['file_id']);
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<void> _openLinks(BuildContext context, Map<String, dynamic> r) async {
  final links = _m(r['links']);
  final steps = _strs(_m(_m(r['card'])['result'])['steps']);
  if (links.isEmpty && steps.isEmpty) return;
  await showModalBottomSheet(
    context: context,
    backgroundColor: C.bgBottom,
    isScrollControlled: true,
    builder: (_) => Padding(
      padding: const EdgeInsets.all(16),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (_s(r['text']).isNotEmpty) Text(_s(r['text']), style: const TextStyle(fontSize: 13)),
          for (final (i, t) in steps.indexed) Text('${i + 1}. $t', style: const TextStyle(fontSize: 13, height: 1.4)),
          const SizedBox(height: 10),
          for (final e in links.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: GlassButton(
                  label: switch (e.key) {
                    'whatsapp' => 'WhatsApp draft kholo',
                    'email' => 'Email draft kholo',
                    'portal' => 'E-stamp portal kholo',
                    _ => e.key
                  },
                  icon: Icons.open_in_new_rounded,
                  onTap: () => Native.openExternal(url: _s(e.value))),
            ),
          const Text('Hoola khud nahi bhejta / bharta: aap kijiye.', style: TextStyle(fontSize: 11, color: C.faint)),
        ]),
      ),
    ),
  );
}

class ContractsScreen extends StatefulWidget {
  const ContractsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ContractsScreen> createState() => _ContractsScreenState();
}

class _ContractsScreenState extends State<ContractsScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _pb;
  int _tab = 0;
  bool _busy = false;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/contracts'));
      final pb = _m(await widget.app.api!.call('GET', '/api/contracts/playbook'));
      if (mounted) setState(() {
        _d = d;
        _pb = pb;
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

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => ContractPage(app: widget.app, contractRef: ref)))
      .then((_) => _load());

  Future<void> _add({bool paste = false}) async {
    String fid = '';
    String text = '';
    if (!paste) {
      fid = await _pickFile(context, widget.app) ?? '';
      if (fid.isEmpty) return;
    }
    if (!mounted) return;
    final f = await _form(context, paste ? 'Contract ka text' : 'Contract ki details', [
      ('title', 'Naam (jaise Acme service agreement)'),
      if (paste) ('text', 'Poora contract yahan paste kijiye'),
      ('kind', 'Kism: nda / msa / service / vendor / lease / employment / software / other'),
      ('counterparty', 'Doosri party (khaali = contract se)'),
      ('our_role', 'Aap kaun: vendor / customer / tenant / landlord / employer / recipient ...'),
      ('our_label', 'Contract aapko kya bulata hai (jaise Vendor)'),
      ('their_label', 'Doosri party ko kya (jaise Client)'),
      ('their_contact', 'Unka email / mobile'),
    ], ok: 'Padho', multi: const {'text'});
    if (f == null) return;
    text = f.remove('text') ?? '';
    if (paste && text.isEmpty) return;
    final r = await _run('POST', '/api/contracts/contracts', {...f, if (fid.isNotEmpty) 'file_id': fid, if (text.isNotEmpty) 'text': text});
    if (r != null && _s(r['id']).isNotEmpty && mounted) _open(_s(r['id']));
  }

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: GradientButton(label: 'File se contract', icon: Icons.upload_file_rounded, height: 46, onTap: _busy ? null : _add)),
        const SizedBox(width: 8),
        GlassButton(label: 'Text paste', icon: Icons.content_paste_rounded, height: 46, onTap: _busy ? null : () => _add(paste: true)),
      ]),
      const SizedBox(height: 12),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ContractsCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (key, title) in const [
        ('overdue', 'TAREEKH NIKAL GAYI'),
        ('deadlines', 'AANE WALI DEADLINE'),
        ('risky', 'REVIEW MEIN BADI BAATEIN'),
        ('stamp', 'STAMP BAAKI')
      ])
        if (_strs(day[key]).isNotEmpty) ...[
          Caption(title),
          for (final t in _strs(day[key])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
          const SizedBox(height: 8),
        ],
      const Text(_draftLine, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _contractTile(Map<String, dynamic> c) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _open(_s(c['id'])),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.description_rounded, color: C.accent, size: 20),
                const SizedBox(width: 8),
                Expanded(child: Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(c['status']), fg: _lvlColor(_s(c['status']))),
              ]),
              Text(
                  [_s(c['kind_label']), _s(c['counterparty']), if (_s(c['end']).isNotEmpty) 'tak ${_s(c['end'])}', 'score ${_s(c['score'])}']
                      .where((x) => x.isNotEmpty)
                      .join(' · '),
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if ((c['high'] ?? 0) != 0) Text('${_s(c['high'])} badi baat', style: const TextStyle(color: C.bad, fontSize: 12.5)),
              if (_s(c['notice_by']).isNotEmpty) Text('Notice ki aakhri tareekh: ${_s(c['notice_by'])}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
            ]),
          ),
        ),
      );

  Widget _contractsTab() {
    final rows = _list(_d?['contracts'])
        .where((c) => _q.isEmpty || '${c['number']} ${c['title']} ${c['counterparty']}'.toLowerCase().contains(_q.toLowerCase()))
        .toList();
    return ListView(padding: const EdgeInsets.all(16), children: [
      TextField(
          decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), hintText: 'Naam / party / number'),
          onChanged: (v) => setState(() => _q = v)),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: GradientButton(label: 'File se contract', icon: Icons.upload_file_rounded, height: 44, onTap: _busy ? null : _add)),
        const SizedBox(width: 8),
        GlassButton(label: 'Excel register', icon: Icons.table_chart_rounded, height: 44, onTap: _busy ? null : () => _run('GET', '/api/contracts/register')),
      ]),
      const SizedBox(height: 12),
      for (final c in rows) _contractTile(c),
      if (rows.isEmpty) const Text('Abhi koi contract nahi.', style: TextStyle(color: C.muted)),
    ]);
  }

  Widget _renewalTab() {
    final rows = _list(_d?['renewals']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Caption('NOTICE / RENEWAL (120 DIN)'),
      for (final o in rows)
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.event_rounded, color: (o['days_left'] ?? 99) < 8 ? C.bad : C.warn),
          title: Text(_s(o['what'])),
          subtitle: Text('${_s(o['contract'])} · ${_s(o['due'])}${o['days_left'] == null ? '' : ' · ${_s(o['days_left'])} din'}'),
          trailing: IconButton(
              icon: const Icon(Icons.check_rounded),
              onPressed: _busy ? null : () => _run('POST', '/api/contracts/obligations/${_s(o['id'])}/done', {})),
        ),
      if (rows.isEmpty) const Text('Agle 120 din mein koi notice deadline nahi.', style: TextStyle(color: C.muted)),
    ]);
  }

  Future<void> _editPosition(Map<String, dynamic> p) async {
    final f = await _form(context, _s(p['label']), const [
      ('position', 'Aapki position (Hinglish mein)'),
      ('level', 'Kitni badi baat: high / medium / low'),
      ('value', 'Number (jaise 45 din / 90 din / shehar)'),
      ('standard_text', 'Aapki standard wording (redline mein yahi jayegi)'),
    ], ok: 'Save', initial: {
      'position': _s(p['position']),
      'level': _s(p['level']),
      'value': _s(p['value']),
      'standard_text': _s(p['standard_text'])
    }, multi: const {'position', 'standard_text'});
    if (f == null) return;
    final body = <String, dynamic>{...f};
    if (_n(f['value']) != null) body['value'] = _n(f['value']);
    await _run('PUT', '/api/contracts/playbook/${_s(p['key'])}', body);
  }

  Widget _playbookTab() {
    final mine = _strs(_pb?['mine']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Har contract inhi positions se jaancha jaata hai. Starter positions ko apni position se badaliye.',
          style: TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 10),
      for (final p in _list(_pb?['positions']))
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(_s(p['label']), style: const TextStyle(fontWeight: FontWeight.w800))),
                if (mine.contains(_s(p['key']))) const Pill('AAPKI', fg: C.ok),
                const SizedBox(width: 6),
                Pill(p['off'] == true ? 'BAND' : _lvlText(_s(p['level'])), fg: p['off'] == true ? C.faint : _lvlColor(_s(p['level']))),
              ]),
              Text(_s(p['position']), style: const TextStyle(fontSize: 13)),
              Row(children: [
                TextButton(onPressed: _busy ? null : () => _editPosition(p), child: const Text('Badlo')),
                TextButton(
                    onPressed: _busy ? null : () => _run('PUT', '/api/contracts/playbook/${_s(p['key'])}', {'off': p['off'] != true}),
                    child: Text(p['off'] == true ? 'Chalu karo' : 'Band karo')),
                if (mine.contains(_s(p['key'])))
                  TextButton(
                      onPressed: _busy ? null : () => _run('PUT', '/api/contracts/playbook/${_s(p['key'])}', {'reset': true}),
                      child: const Text('Starter par')),
              ]),
            ]),
          ),
        ),
    ]);
  }

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Niyam', const [
      ('party_name', 'Aapke business ka naam (contracts mein jaisa)'),
      ('default_role', 'Aam taur par aap: vendor / customer / ...'),
      ('seat_city', 'Arbitration / court ka shehar (aapki pasand)'),
      ('state', 'State (stamp duty)'),
      ('email', 'Email'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('msme', 'Udyam MSME (haan / nahi)'),
    ], ok: 'Save', initial: {
      for (final k in ['party_name', 'default_role', 'seat_city', 'state', 'email', 'morning_time']) k: _s(st[k]),
      'msme': st['msme'] == true ? 'haan' : 'nahi',
    });
    if (f == null) return;
    await _run('PUT', '/api/contracts/settings', {...f, if (f['msme'] != null) 'msme': f['msme']!.toLowerCase().startsWith('h')});
  }

  Future<void> _addRate() async {
    final f = await _form(context, 'Stamp rate (aapke state ki schedule / CA se)', const [
      ('kind', 'Contract kism (service / nda / lease ... ya any)'),
      ('state', 'State'),
      ('mode', 'fixed (Rs) ya pct (%)'),
      ('rate', 'Rate'),
      ('min', 'Kam se kam (Rs, ho to)'),
      ('max', 'Zyada se zyada (Rs, ho to)'),
      ('note', 'Note (article / source)'),
    ], ok: 'Jodo');
    if (f == null || _n(f['rate']) == null) return;
    final rows = [..._list(_m(_d?['settings'])['stamp_rates'])];
    rows.add({
      'kind': f['kind'] ?? 'any',
      'state': f['state'] ?? '',
      'mode': f['mode'] ?? 'fixed',
      'rate': _n(f['rate']),
      'min': _n(f['min']),
      'max': _n(f['max']),
      'note': f['note'] ?? ''
    });
    await _run('PUT', '/api/contracts/settings', {'stamp_rates': rows});
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['party_name']).isEmpty ? 'Business ka naam daaliye' : _s(st['party_name']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Seat: ${_s(st['seat_city']).isEmpty ? '—' : _s(st['seat_city'])} · State: ${_s(st['state']).isEmpty ? '—' : _s(st['state'])}'
              ' · MSME: ${st['msme'] == true ? 'haan' : 'nahi'}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('STAMP RATE (SIRF AAPKE)'),
      for (final r in _list(st['stamp_rates']))
        Text('• ${_s(r['kind'])} ${_s(r['state'])}: ${_s(r['mode']) == 'pct' ? '${_s(r['rate'])}%' : 'Rs ${_s(r['rate'])}'}'
            '${r['min'] != null ? ' (min ${_s(r['min'])})' : ''}${r['max'] != null ? ' (max ${_s(r['max'])})' : ''} ${_s(r['note'])}',
            style: const TextStyle(fontSize: 13)),
      if (_list(st['stamp_rates']).isEmpty) const Text('Koi rate nahi: Hoola stamp duty ka andaaza nahi lagata.', style: TextStyle(fontSize: 12.5, color: C.muted)),
      TextButton(onPressed: _busy ? null : _addRate, child: const Text('Rate jodo')),
      const SizedBox(height: 12),
      const Caption('HOOLA KABHI NAHI'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
      const Text(_draftLine, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Aaj', 'Contracts', 'Renewal', 'Playbook', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('${widget.app.aName} · Contract manager'),
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
                  child: switch (_tab) { 0 => _today(), 1 => _contractsTab(), 2 => _renewalTab(), 3 => _playbookTab(), _ => _rulesTab() },
                ),
        ),
      ]),
    );
  }
}

/// One contract: summary, risks, clauses, versions + redline, obligations, cards, her real-world facts (signed / stamped).
class ContractPage extends StatefulWidget {
  const ContractPage({super.key, required this.app, required this.contractRef});
  final Santosh app;
  final String contractRef;
  @override
  State<ContractPage> createState() => _ContractPageState();
}

class _ContractPageState extends State<ContractPage> {
  Map<String, dynamic>? _c;
  int _tab = 0;
  bool _busy = false;

  String get _ref => _s(_c?['id']).isEmpty ? widget.contractRef : _s(_c?['id']);
  String get _base => '/api/contracts/contracts/${Uri.encodeComponent(_ref)}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = _m(await widget.app.api!.call('GET', '/api/contracts/contracts/${Uri.encodeComponent(widget.contractRef)}'));
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

  Future<void> _edit() async {
    final c = _c ?? {};
    final f = await _form(context, 'Contract ki details', const [
      ('title', 'Naam'),
      ('counterparty', 'Doosri party'),
      ('their_contact', 'Unka email / mobile'),
      ('our_role', 'Aap kaun (vendor / customer / ...)'),
      ('our_label', 'Contract aapko kya bulata hai'),
      ('their_label', 'Doosri party ko kya'),
      ('start', 'Shuru (YYYY-MM-DD)'),
      ('end', 'Khatam (YYYY-MM-DD)'),
      ('notice_days', 'Notice (din)'),
      ('renew_months', 'Renewal avadhi (mahine)'),
      ('value', 'Value (Rs)'),
    ], ok: 'Save', initial: {
      for (final k in ['title', 'counterparty', 'their_contact', 'our_role', 'our_label', 'their_label', 'start', 'end', 'notice_days', 'renew_months', 'value'])
        k: _s(c[k]),
    });
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['notice_days', 'renew_months', 'value']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('PATCH', _base, body);
  }

  Future<void> _redline() async {
    final r = await _run('POST', '$_base/redline', {});
    if (r != null && mounted) {
      final ins = _strs(r['inserted']);
      final del = _strs(r['deleted']);
      await showDialog(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('Redline v${_s(r['version'])}'),
          content: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              for (final t in del) Text('− $t', style: const TextStyle(color: C.bad, fontSize: 12.5, decoration: TextDecoration.lineThrough)),
              for (final t in ins) Text('+ $t', style: const TextStyle(color: C.ok, fontSize: 12.5)),
              for (final x in _list(r['skipped'])) Text('! ${_s(x['why'])}', style: const TextStyle(color: C.warn, fontSize: 12)),
              const SizedBox(height: 8),
              const Text('Asli file waisi hi hai; yeh nayi Word copy hai (track changes).', style: TextStyle(fontSize: 11, color: C.faint)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek')),
            TextButton(
                onPressed: () {
                  Navigator.pop(d);
                  _card('send', {'version': r['version']});
                },
                child: const Text('Bhejne ka card')),
          ],
        ),
      );
    }
  }

  Future<void> _myEdit() async {
    final f = await _form(context, 'Apna badlav (contract ke shabd)', const [
      ('find', 'Contract mein yeh shabd (bilkul waise)'),
      ('replace', 'Inki jagah yeh'),
    ], ok: 'Redline', multi: const {'find', 'replace'});
    if (f == null || (f['find'] ?? '').isEmpty) return;
    await _run('POST', '$_base/redline', {
      'keys': ['none'],
      'edits': [
        {'op': (f['replace'] ?? '').isEmpty ? 'delete' : 'replace', 'find': f['find'], 'replace': f['replace'] ?? ''}
      ]
    });
  }

  Future<void> _card(String kind, [Map<String, dynamic> extra = const {}]) async {
    Map<String, dynamic> body = {'kind': kind, ...extra};
    if (kind == 'send' && extra.isEmpty) {
      final f = await _form(context, 'Doosri party ko bhejna', const [
        ('to', 'Email / mobile'),
        ('via', 'email / whatsapp'),
        ('version', 'Redline version (khaali = sabse nayi)'),
        ('message', 'Message (khaali = Hoola ka draft)'),
      ], ok: 'Card banao', initial: {'to': _s(_c?['their_contact'])}, multi: const {'message'});
      if (f == null) return;
      body = {...body, ...f, if (_n(f['version']) != null) 'version': _n(f['version'])};
    } else if (kind == 'esign') {
      final f = await _form(context, 'E-sign: kaun sign karega', const [
        ('n1', 'Signer 1 naam'),
        ('r1', 'Signer 1 role / company'),
        ('c1', 'Signer 1 email / mobile'),
        ('n2', 'Signer 2 naam'),
        ('r2', 'Signer 2 role / company'),
        ('c2', 'Signer 2 email / mobile'),
        ('mode', 'aadhaar_esign / dsc'),
      ], ok: 'Card banao');
      if (f == null) return;
      body['signers'] = [
        for (final i in ['1', '2'])
          if ((f['n$i'] ?? '').isNotEmpty) {'name': f['n$i'], 'role': f['r$i'] ?? '', 'contact': f['c$i'] ?? ''}
      ];
      if (f['mode'] != null) body['mode'] = f['mode'];
    } else if (kind == 'estamp') {
      final f = await _form(context, 'E-stamp', const [
        ('amount', 'Amount (khaali = aapke saved rate se)'),
        ('state', 'State'),
        ('payer', 'Kaun bharega'),
      ], ok: 'Card banao');
      if (f == null) return;
      body = {...body, ...f, if (_n(f['amount']) != null) 'amount': _n(f['amount'])};
    } else if (kind == 'notice') {
      final f = await _form(context, 'Notice', const [
        ('notice_kind', 'stop_renewal / terminate / renew'),
        ('effective', 'Kab se (YYYY-MM-DD)'),
        ('to', 'Email / mobile'),
      ], ok: 'Card banao', initial: {'notice_kind': 'stop_renewal', 'to': _s(_c?['their_contact'])});
      if (f == null) return;
      body = {...body, ...f};
    }
    await _run('POST', '$_base/cards', body);
  }

  Future<void> _signed() async {
    final f = await _form(context, 'Sign ho gaya', const [('on', 'Kis din (YYYY-MM-DD)')], ok: 'Save');
    if (f == null || !mounted) return;
    final fid = await _pickFile(context, widget.app) ?? '';
    await _run('POST', '$_base/signed', {...f, if (fid.isNotEmpty) 'file_id': fid});
  }

  Future<void> _stamped() async {
    final f = await _form(context, 'Stamp ho gaya', const [
      ('cert_no', 'E-stamp certificate no. (UIN)'),
      ('on', 'Tareekh'),
      ('amount', 'Kitna bhara'),
    ], ok: 'Save');
    if (f == null) return;
    await _run('POST', '$_base/stamped', {...f, if (_n(f['amount']) != null) 'amount': _n(f['amount'])});
  }

  Future<void> _newVersion() async {
    final fid = await _pickFile(context, widget.app) ?? '';
    if (fid.isEmpty) return;
    await _run('POST', '$_base/version', {'file_id': fid, 'note': 'doosri party ki nayi copy'});
  }

  Future<void> _addOblig() async {
    final f = await _form(context, 'Register mein kaam', const [
      ('what', 'Kya karna hai'),
      ('due', 'Kab tak (YYYY-MM-DD)'),
      ('who', 'Kaun: us / them / both'),
      ('kind', 'payment / delivery / report / insurance / lockin / other'),
      ('every_months', 'Har kitne mahine (ho to)'),
    ], ok: 'Jodo');
    if (f == null || (f['what'] ?? '').isEmpty) return;
    await _run('POST', '$_base/obligations', {...f, if (_n(f['every_months']) != null) 'every_months': _n(f['every_months'])});
  }

  Future<void> _more() async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label, icon) in const [
            ('edit', 'Details badlo', Icons.edit_rounded),
            ('review', 'Playbook se dobara jaancho', Icons.rule_rounded),
            ('version', 'Doosri party ki nayi copy jodo', Icons.file_upload_rounded),
            ('share0', 'Asli file meri files mein', Icons.folder_open_rounded),
            ('signed', 'Sign ho gaya', Icons.draw_rounded),
            ('stamped', 'Stamp ho gaya (UIN)', Icons.verified_rounded),
            ('nostamp', 'Stamp zaroori nahi', Icons.block_rounded),
            ('archived', 'Archive karo', Icons.archive_rounded),
            ('terminated', 'Khatam ho gaya (terminated)', Icons.cancel_rounded),
            ('forget', 'Mita do (DPDP)', Icons.delete_forever_rounded),
          ])
            ListTile(leading: Icon(icon), title: Text(label), onTap: () => Navigator.pop(c, k)),
        ]),
      ),
    );
    switch (choice) {
      case 'edit':
        await _edit();
      case 'review':
        await _run('POST', '$_base/review', {});
      case 'version':
        await _newVersion();
      case 'share0':
        await _run('POST', '$_base/share', {'version': 0});
      case 'signed':
        await _signed();
      case 'stamped':
        await _stamped();
      case 'nostamp':
        await _run('POST', '$_base/stamped', {'not_needed': true});
      case 'archived' || 'terminated':
        await _run('POST', '$_base/status', {'status': choice});
      case 'forget':
        if (!mounted) return;
        final ok = await showDialog<bool>(
            context: context,
            builder: (d) => AlertDialog(
                  title: const Text('Mita dein?'),
                  content: const Text('Text, files aur doosri party ke contact hamesha ke liye mitenge; number aur tareekhen bachengi.'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                    TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, mitao')),
                  ],
                ));
        if (ok == true) await _run('POST', '$_base/forget', {});
      default:
        break;
    }
  }

  Widget _summary() {
    final c = _c ?? {};
    final stamp = _m(c['stamp']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
            Pill('score ${_s(c['score'])}', fg: (c['high'] ?? 0) != 0 ? C.bad : C.ok),
          ]),
          Text('${_s(c['kind_label'])} · ${_s(c['counterparty'])} · ${_s(c['status'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 6),
          Text(_s(c['summary']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
          const SizedBox(height: 6),
          Text(
              [
                if (_s(c['start']).isNotEmpty) 'Shuru ${_s(c['start'])}',
                if (_s(c['end']).isNotEmpty) 'Khatam ${_s(c['end'])}',
                if (c['auto_renew'] == true) 'auto-renew',
                if (c['notice_days'] != null) 'notice ${_s(c['notice_days'])} din',
                if (_s(c['governing_law']).isNotEmpty) 'kanoon ${_s(c['governing_law'])}',
                if (_s(c['seat']).isNotEmpty) 'seat ${_s(c['seat'])}',
                'stamp: ${_s(stamp['paid']).isEmpty ? 'pata nahi' : _s(stamp['paid'])}',
              ].join(' · '),
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          if (_s(c['notice_by']).isNotEmpty)
            Text('Notice ki aakhri tareekh: ${_s(c['notice_by'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_s(c['our_label']).isEmpty)
            const Text('Contract mein aap kaun ho (Vendor / Client ...) batane se review pakka hoga: Details badlo.',
                style: TextStyle(fontSize: 12, color: C.warn)),
        ]),
      ),
      const SizedBox(height: 12),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Redline banao', icon: Icons.difference_rounded, height: 42, onTap: _busy ? null : _redline),
        GlassButton(label: 'Apna badlav', icon: Icons.edit_note_rounded, height: 42, onTap: _busy ? null : _myEdit),
        GlassButton(label: 'Bhejna', icon: Icons.send_rounded, height: 42, onTap: _busy ? null : () => _card('send')),
        GlassButton(label: 'E-stamp', icon: Icons.local_post_office_rounded, height: 42, onTap: _busy ? null : () => _card('estamp')),
        GlassButton(label: 'E-sign', icon: Icons.draw_rounded, height: 42, onTap: _busy ? null : () => _card('esign')),
        GlassButton(label: 'Notice', icon: Icons.mail_rounded, height: 42, onTap: _busy ? null : () => _card('notice')),
        GlassButton(label: 'Aur', icon: Icons.more_horiz_rounded, height: 42, onTap: _busy ? null : _more),
      ]),
      const SizedBox(height: 12),
      for (final x in _list(c['cards']).where((x) => ['waiting', 'blocked', 'approved'].contains(_s(x['status']))))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: ContractsCardCard(app: widget.app, data: {'card': x}, onDone: _load)),
      const Text(_draftLine, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _risksTab() => ListView(padding: const EdgeInsets.all(16), children: [
        for (final r in _list(_c?['risks']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              padding: const EdgeInsets.all(12),
              border: _s(r['level']) == 'high' ? C.bad : null,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Pill(_lvlText(_s(r['level'])), fg: _lvlColor(_s(r['level']))),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_s(r['title']), style: const TextStyle(fontWeight: FontWeight.w800))),
                ]),
                const SizedBox(height: 4),
                Text(_s(r['why']), style: const TextStyle(fontSize: 13, height: 1.4)),
                if (_s(r['quote']).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text('“${_s(r['quote'])}”', style: const TextStyle(fontSize: 12, color: C.muted, fontStyle: FontStyle.italic)),
                  ),
                if (_m(r['fix']).isNotEmpty) const Text('Redline mein sujhav hai.', style: TextStyle(fontSize: 11.5, color: C.ok)),
                if (_s(r['source']).isNotEmpty)
                  TextButton.icon(
                      onPressed: () => Native.openExternal(url: _s(r['source'])),
                      icon: const Icon(Icons.link_rounded, size: 16),
                      label: const Text('Source padhiye')),
              ]),
            ),
          ),
        if (_list(_c?['risks']).isEmpty) const Text('Playbook se koi bada farq nahi mila.', style: TextStyle(color: C.muted)),
        const Text(_draftLine, style: TextStyle(fontSize: 11, color: C.faint)),
      ]);

  Widget _clausesTab() => ListView(padding: const EdgeInsets.all(16), children: [
        for (final cl in _list(_c?['clauses']))
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            leading: Icon(cl['found'] == true ? Icons.check_circle_rounded : Icons.help_outline_rounded,
                color: cl['found'] == true ? C.ok : C.faint, size: 20),
            title: Text(_s(cl['label'])),
            children: [
              Text(cl['found'] == true ? _s(cl['text']) : 'Contract mein nahi mila.', style: const TextStyle(fontSize: 12.5, height: 1.4)),
              const SizedBox(height: 8),
            ],
          ),
      ]);

  Widget _registerTab() {
    final vers = _list(_c?['versions']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Caption('OBLIGATIONS / TAREEKHEN'),
      for (final o in _list(_c?['obligations']))
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(o['status'] == 'open' ? Icons.radio_button_unchecked_rounded : Icons.check_circle_rounded,
              color: o['status'] == 'open' ? C.warn : C.ok),
          title: Text(_s(o['what']), style: const TextStyle(fontSize: 13.5)),
          subtitle: Text('${_s(o['number'])} · ${_s(o['due'])} · ${_s(o['who'])}${o['every_months'] == null ? '' : ' · har ${_s(o['every_months'])} mahine'}'),
          trailing: o['status'] == 'open'
              ? IconButton(
                  icon: const Icon(Icons.check_rounded),
                  onPressed: _busy ? null : () => _run('POST', '/api/contracts/obligations/${_s(o['id'])}/done', {}))
              : null,
        ),
      TextButton(onPressed: _busy ? null : _addOblig, child: const Text('Kaam jodo')),
      const SizedBox(height: 12),
      const Caption('VERSIONS'),
      for (final v in vers)
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.history_rounded),
          title: Text('v${_s(v['n'])} · ${_s(v['kind'])}${v['changes'] == null ? '' : ' · ${_s(v['changes'])} badlav'}'),
          subtitle: Text('${_s(v['name'])} ${_s(v['note'])}'),
          trailing: IconButton(
              icon: const Icon(Icons.download_rounded),
              onPressed: _busy ? null : () => _run('POST', '$_base/share', {'version': v['n']})),
        ),
      if (vers.isEmpty) const Text('Abhi sirf asli copy.', style: TextStyle(color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Saar', 'Jokhim', 'Clauses', 'Register'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(_s(_c?['number']).isEmpty ? 'Contract' : '${_s(_c?['number'])} · ${_s(_c?['title'])}'),
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
          child: _c == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: switch (_tab) { 0 => _summary(), 1 => _risksTab(), 2 => _clausesTab(), _ => _registerTab() },
                ),
        ),
      ]),
    );
  }
}

/// contracts_card: send a draft / redline to the other side, e-sign steps, e-stamp steps (fingerprint once a phone key is active),
/// notice letters. Decided ONLY by her tap here. Also in calls.
class ContractsCardCard extends StatefulWidget {
  const ContractsCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ContractsCardCard> createState() => _ContractsCardCardState();
}

class _ContractsCardCardState extends State<ContractsCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['card']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/contracts/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'E-stamp ki haan' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
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
    final id = _s(_x['id']);
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_x['hash'])};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/contracts/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/contracts/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        if (_m(m['card']).isNotEmpty) setState(() => _x = _m(m['card']));
        _snack(context, _s(m['say']));
        if (yes) await _openLinks(context, m);
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _done() async {
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', '/api/contracts/cards/${_s(_x['id'])}/done', body: {'note': 'aapne bheja'}));
      if (mounted) {
        if (_s(m['id']).isNotEmpty) setState(() => _x = m);
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
    final x = _x;
    final st = _s(x['status']);
    final show = _m(x['show']);
    final kind = _s(x['kind']);
    final blockers = _strs(show['blockers']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(
              switch (kind) {
                'send' => Icons.send_rounded,
                'esign' => Icons.draw_rounded,
                'estamp' => Icons.local_post_office_rounded,
                _ => Icons.mail_rounded
              },
              color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · ${_s(x['kind_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'blocked' => 'rukawat', 'stale' => 'purana', 'rejected' => 'nahi', _ => st },
              fg: _lvlColor(st)),
        ]),
        Text('${_s(show['contract'])} · ${_s(show['counterparty'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (kind == 'send') ...[
          Text('${_s(show['via'])} → ${_s(show['to']).isEmpty ? '—' : _s(show['to'])} · ${_s(show['what'])}', style: const TextStyle(fontSize: 12.5)),
          if (_s(show['message']).isNotEmpty) Text(_s(show['message']), maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
        ],
        if (kind == 'esign')
          for (final g in _list(show['signers'])) Text('• ${_s(g['name'])} ${_s(g['role'])}', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'estamp')
          Text('${_s(show['amount_text'])} · ${_s(show['state'])} · bharega ${_s(show['payer'])}\n${_s(show['rate_note'])}',
              style: const TextStyle(fontSize: 12.5)),
        if (kind == 'notice') ...[
          Text('${_s(show['notice_label'])}${_s(show['deadline']).isEmpty ? '' : ' · deadline ${_s(show['deadline'])}'}', style: const TextStyle(fontSize: 12.5)),
          Text(_s(show['letter']), maxLines: 5, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
        ],
        for (final b in blockers) Text('✗ $b', style: const TextStyle(fontSize: 12.5, color: C.bad)),
        for (final w in _strs(show['warnings'])) Text('! $w', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: switch (kind) { 'send' => 'Haan, bhejne do', 'esign' => 'Haan, e-sign karna hai', 'estamp' => 'Haan, stamp lena hai', _ => 'Haan, notice banao' },
                    height: 42,
                    onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved' && (kind == 'notice' || kind == 'send'))
          GlassButton(label: 'Maine bhej diya', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : _done),
        if (st == 'stale') const Text('Contract badal gaya: naya card banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        Text(kind == 'estamp' ? 'Paise aap portal par khud bharti hain.' : 'Hoola khud nahi bhejta / sign karta.',
            style: const TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// contracts_review: what Hoola found in a new contract (score + top risks). Also in calls: no.
class ContractsReviewCard extends StatelessWidget {
  const ContractsReviewCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final c = _m(data['contract']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.gavel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill('score ${_s(c['score'])}', fg: (c['high'] ?? 0) != 0 ? C.bad : C.ok),
        ]),
        for (final r in _list(data['risks']).take(5))
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${_lvlText(_s(r['level']))}: ${_s(r['title'])}', style: TextStyle(fontSize: 12.5, color: _lvlColor(_s(r['level'])))),
          ),
        if (_s(c['notice_by']).isNotEmpty) Text('Notice ki aakhri tareekh ${_s(c['notice_by'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        TextButton(
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => ContractPage(app: app, contractRef: _s(c['id'])))),
            child: const Text('Contract kholo')),
        const Text(_draftLine, style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// contracts_alert / contracts_day: reminders and the morning note. Calls: no.
class ContractsNoteCard extends StatelessWidget {
  const ContractsNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.event_note_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4))),
          IconButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ContractsScreen(app: app))),
              icon: const Icon(Icons.open_in_new_rounded, size: 18)),
        ]),
      );
}
