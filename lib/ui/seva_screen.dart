/// Profile > Seva sahayak (customer support): Hoola answers common questions only from her Gyaan (FAQ + niyam),
/// real problems become tickets with SLA timers, customers hear the status of their own tickets, and every refund /
/// exception waits for HER tap here (money cards with the phone's fingerprint).
/// Tabs: Aaj · Shikayat · Gyaan · Jawab (macros) · Niyam · Hisaab.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api.dart' show ApiException;
import '../native.dart';
import '../state.dart';
import 'desk/desk_kit.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());

const _priColor = {'urgent': C.bad, 'high': C.warn, 'normal': C.chip, 'low': C.faint};
const _statusLabel = {
  'new': 'New',
  'open': 'Work in progress',
  'pending': 'Reply from customer',
  'on_hold': 'On hold',
  'resolved': 'Fixed',
  'closed': 'Closed',
  'merged': 'Linked',
};

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {Map<String, String> initial = const {}, String ok = 'Next'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], minLines: 1, maxLines: k == 'answer' || k == 'text' || k == 'reason' ? 5 : 1,
                decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Leave it')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<dynamic> _call(Santosh app, String method, String path, {Object? body, Map<String, String>? query}) =>
    app.api!.call(method, path, body: body, query: query, timeout: const Duration(seconds: 90));

class SevaScreen extends StatefulWidget {
  const SevaScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SevaScreen> createState() => _SevaScreenState();
}

class _SevaScreenState extends State<SevaScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _tickets = const [];
  List<Map<String, dynamic>> _kb = const [];
  List<Map<String, dynamic>> _gaps = const [];
  Map<String, dynamic>? _report;
  String _ticketFilter = 'open';
  int _days = 30;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await _call(widget.app, 'GET', '/api/seva'));
      final t = _map(await _call(widget.app, 'GET', '/api/seva/tickets', query: {'status': _ticketFilter}));
      final k = _map(await _call(widget.app, 'GET', '/api/seva/kb'));
      final r = _map(await _call(widget.app, 'GET', '/api/seva/report', query: {'days': '$_days'}));
      if (!mounted) return;
      setState(() {
        _d = d;
        _tickets = _list(t['tickets']);
        _kb = _list(k['entries']);
        _gaps = _list(k['gaps']);
        _report = r;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ---------------------------------------------------------------- Aaj
  Widget _today() {
    final day = _map(_d?['day']);
    final exc = _list(_d?['exceptions']);
    final dups = _list(_d?['duplicates']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(day['say']).isEmpty ? 'Service: all fine.' : _s(day['say']),
          style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'New complaint', icon: Icons.add_comment_rounded, onTap: _busy ? null : _newTicket),
        GlassButton(label: 'Check the reply', icon: Icons.quiz_rounded, onTap: _busy ? null : _askTest),
      ]),
      if (exc.isNotEmpty) ...[
        const SizedBox(height: 14),
        Text('Needs your yes', style: display(15)),
        for (final e in exc)
          Padding(padding: const EdgeInsets.only(top: 8), child: SevaExceptionCard(key: ValueKey('ex${e['id']}${e['status']}'), app: widget.app, data: e, onDone: _load)),
      ],
      if (dups.isNotEmpty) ...[
        const SizedBox(height: 14),
        Text('Similar complaints (same customer)', style: display(15)),
        for (final d in dups)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                Expanded(child: Text('${_s(d['a'])} + ${_s(d['b'])} · ${_s(d['customer'])}', style: const TextStyle(fontSize: 13))),
                TextButton(
                    onPressed: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/seva/tickets/${d['b']}/merge', body: {'into': d['a']})),
                    child: const Text('Add')),
              ]),
            ),
          ),
      ],
      const SizedBox(height: 14),
      Text('Open complaints', style: display(15)),
      for (final t in _list(_d?['tickets']).take(8)) Padding(padding: const EdgeInsets.only(top: 8), child: _ticketTile(t)),
      const SizedBox(height: 14),
      for (final r in _list(_d?['rules'])) Text('• $r', style: const TextStyle(fontSize: 12, color: C.muted, height: 1.4)),
    ]);
  }

  Future<void> _newTicket() async {
    final f = await _form(context, 'New complaint', const [
      ('name', 'Customer name'),
      ('phone', 'Phone (the WhatsApp number, if any)'),
      ('text', 'What is the problem (in their words)'),
      ('channel', 'From where: phone / walk-in / email'),
    ]);
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run(() => _call(widget.app, 'POST', '/api/seva/tickets', body: {...f, 'channel': f['channel'] ?? 'phone'}));
  }

  Future<void> _askTest() async {
    final f = await _form(context, 'What should Hoola say if the customer asks?', const [('question', 'Question')], ok: 'View');
    if (f == null || f['question'] == null) return;
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/seva/kb/ask', body: {'question': f['question']}));
      if (!mounted) return;
      final st = _s(r['status']);
      await showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text(st == 'answered' ? 'Will get an answer' : st == 'clarify' ? 'Not sure (will ask)' : 'Not in knowledge base'),
          content: Text([
            if (_s(r['reply']).isNotEmpty) _s(r['reply']),
            if (_s(r['source']).isNotEmpty) 'Source: ${_s(r['source'])}',
            'Trust: ${((r['confidence'] ?? 0) * 100).round()}%',
            if (_s(r['say']).isNotEmpty) _s(r['say']),
            if (_s(r['exception']).isNotEmpty) _s(r['exception']),
          ].join('\n\n')),
          actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK'))],
        ),
      );
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  // ---------------------------------------------------------------- Shikayat
  Widget _ticketTile(Map<String, dynamic> t) {
    final sla = _map(t['sla']);
    final late = sla['late'] == true;
    final left = sla['first_response_left_h'] ?? sla['resolve_left_h'];
    return Press(
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => SevaTicketPage(app: widget.app, id: _s(t['id']))))
          .then((_) => _load()),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: late ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(t['number'])} · ${_s(t['customer'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(t['priority']), fg: _priColor[_s(t['priority'])] ?? C.chip),
            const SizedBox(width: 6),
            Pill(_statusLabel[_s(t['status'])] ?? _s(t['status'])),
          ]),
          const SizedBox(height: 4),
          Text(_s(t['text']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
          Text(
              '${_s(t['category_label'])} · ${_s(t['channel'])}'
              '${sla['paused'] == true ? ' · time paused (waiting for customer\'s reply)' : left != null ? (late ? ' · late against SLA' : ' · ${(left as num).toStringAsFixed(1)} hours left') : ''}',
              style: TextStyle(fontSize: 12, color: late ? C.bad : C.muted)),
        ]),
      ),
    );
  }

  Widget _ticketsTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final (k, label) in const [('open', 'Open'), ('pending', 'Reply from customer'), ('resolved', 'Fixed'), ('closed', 'Closed'), ('', 'All')])
            ChoiceChip(
                label: Text(label),
                selected: _ticketFilter == k,
                onSelected: (_) {
                  setState(() => _ticketFilter = k);
                  _load();
                }),
        ]),
        const SizedBox(height: 8),
        GlassButton(label: 'New complaint', icon: Icons.add_comment_rounded, onTap: _busy ? null : _newTicket),
        const SizedBox(height: 8),
        if (_tickets.isEmpty) const Text('No complaints.', style: TextStyle(color: C.muted)),
        for (final t in _tickets) Padding(padding: const EdgeInsets.only(bottom: 8), child: _ticketTile(t)),
      ]);

  // ---------------------------------------------------------------- Gyaan
  Future<void> _kbAdd([Map<String, dynamic>? e, String prefill = '']) async {
    final f = await _form(context, e == null ? 'New question and answer' : 'Change', const [
      ('question', 'What customers ask'),
      ('answer', 'Your answer (only the truth, what you say)'),
      ('aliases', 'Other ways they ask (comma separated)'),
      ('kind', 'faq or policy (rule)'),
    ], initial: e == null
        ? {if (prefill.isNotEmpty) 'question': prefill}
        : {'question': _s(e['question']), 'answer': _s(e['answer']), 'aliases': ((e['aliases'] as List?) ?? const []).join(', '), 'kind': _s(e['kind'])});
    if (f == null) return;
    final body = {
      ...f,
      'aliases': (f['aliases'] ?? '').split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList(),
      if (f['kind'] != 'policy') 'kind': 'faq',
    };
    await _run(() => e == null
        ? _call(widget.app, 'POST', '/api/seva/kb', body: body)
        : _call(widget.app, 'PATCH', '/api/seva/kb/${e['id']}', body: body));
  }

  Future<void> _kbImportFile() async {
    final res = await FilePicker.platform.pickFiles(withData: true);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    await _run(() => widget.app.api!.uploadFile('/api/seva/kb/import', f.name, f.bytes!, tries: 1, timeout: const Duration(seconds: 180)));
  }

  Future<void> _kbImportLink() async {
    final f = await _form(context, 'Your website page', const [('url', 'https://...')], ok: 'Read');
    if (f == null || f['url'] == null) return;
    await _run(() => _call(widget.app, 'POST', '/api/seva/kb/import_link', body: {'url': f['url']}));
  }

  Widget _kbTab() {
    final drafts = _kb.where((e) => e['status'] == 'draft').toList();
    final live = _kb.where((e) => e['status'] != 'draft').toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Hoola answers customers only from here, with the source. What is not here, it gives to you.',
          style: TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Write', icon: Icons.edit_note_rounded, onTap: _busy ? null : () => _kbAdd()),
        GlassButton(label: 'From file', icon: Icons.upload_file_rounded, onTap: _busy ? null : _kbImportFile),
        GlassButton(label: 'From website', icon: Icons.language_rounded, onTap: _busy ? null : _kbImportLink),
      ]),
      if (_gaps.isNotEmpty) ...[
        const SizedBox(height: 14),
        Text('Customers asked, not in knowledge base', style: display(15)),
        for (final g in _gaps)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              border: C.warn,
              child: Row(children: [
                Expanded(child: Text('"${_s(g['question'])}" · ${g['times']}x', style: const TextStyle(fontSize: 13))),
                TextButton(onPressed: _busy ? null : () => _kbAdd(null, _s(g['question'])),
                    child: const Text('Give answer')),
              ]),
            ),
          ),
      ],
      if (drafts.isNotEmpty) ...[
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: Text('Draft (${drafts.length}): only after your yes', style: display(15))),
          TextButton(
              onPressed: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/seva/kb/approve', body: {'ids': [for (final d in drafts) d['id']]})),
              child: const Text('All yes')),
        ]),
        for (final e in drafts) _kbTile(e, draft: true),
      ],
      const SizedBox(height: 14),
      Text('Knowledge (${live.length})', style: display(15)),
      for (final e in live) _kbTile(e),
    ]);
  }

  Widget _kbTile(Map<String, dynamic> e, {bool draft = false}) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: draft ? C.warn : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(_s(e['question']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5))),
              Pill(e['kind'] == 'policy' ? 'rule' : 'faq'),
            ]),
            const SizedBox(height: 4),
            Text(_s(e['answer']), style: const TextStyle(fontSize: 13, height: 1.35)),
            Text('${_s(e['source'])}${(e['hits'] ?? 0) > 0 ? ' · ${e['hits']} times it helped' : ''}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
            Row(children: [
              if (draft)
                TextButton(onPressed: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/seva/kb/approve', body: {'ids': [e['id']]})), child: const Text('Yes')),
              TextButton(onPressed: _busy ? null : () => _kbAdd(e), child: const Text('Change')),
              TextButton(onPressed: _busy ? null : () => _run(() => _call(widget.app, 'DELETE', '/api/seva/kb/${e['id']}')), child: const Text('Remove')),
            ]),
          ]),
        ),
      );

  // ---------------------------------------------------------------- Jawab (macros)
  Widget _macrosTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Ready replies: write in one language and Hoola makes it Hinglish / Hindi / Marathi / English. Used only after your approval.',
            style: TextStyle(fontSize: 12.5, color: C.muted)),
        const SizedBox(height: 8),
        GlassButton(
            label: 'New ready reply',
            icon: Icons.bolt_rounded,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Ready replies', const [
                      ('name', 'Name (for example "technician is coming")'),
                      ('text', 'Text ({name}, {ticket}, {status} can be used)'),
                    ]);
                    if (f != null) await _run(() => _call(widget.app, 'POST', '/api/seva/macros', body: f));
                  }),
        for (final m in _list(_d?['macros']))
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Glass(
              padding: const EdgeInsets.all(12),
              border: m['status'] == 'draft' ? C.warn : null,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(_s(m['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                  Pill(m['status'] == 'approved' ? 'approved' : 'draft'),
                ]),
                for (final e in _map(m['texts']).entries)
                  Padding(padding: const EdgeInsets.only(top: 4), child: Text('${e.key}: ${e.value}', style: const TextStyle(fontSize: 12.5))),
                Row(children: [
                  if (m['status'] != 'approved')
                    TextButton(onPressed: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/seva/macros/${m['id']}/approve')), child: const Text('Yes, approve')),
                  TextButton(onPressed: _busy ? null : () => _run(() => _call(widget.app, 'DELETE', '/api/seva/macros/${m['id']}')), child: const Text('Remove')),
                ]),
              ]),
            ),
          ),
      ]);

  // ---------------------------------------------------------------- Niyam
  Widget _rulesTab() {
    final st = _map(_d?['settings']);
    final pol = _map(st['policy']);
    final sla = _map(st['sla']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Type of work (SLA)', style: display(15)),
      Wrap(spacing: 8, children: [
        for (final k in ((st['presets'] as List?) ?? const ['shop', 'isp', 'ecommerce', 'clinic']))
          ChoiceChip(label: Text('$k'), selected: st['kind'] == k, onSelected: (_) => _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: {'kind': k}))),
      ]),
      const SizedBox(height: 6),
      for (final p in const ['urgent', 'high', 'normal', 'low'])
        Press(
          onTap: () async {
            final v = (sla[p] as List?) ?? const [24, 72];
            final f = await _form(context, 'SLA: $p', const [('fr', 'First reply (hours)'), ('rs', 'Resolution (hours)')],
                initial: {'fr': '${v[0]}', 'rs': '${v[1]}'});
            final fr = _n(f?['fr']), rsv = _n(f?['rs']);
            if (fr != null && rsv != null) {
              await _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: {
                    'sla': {p: [fr, rsv]}
                  }));
            }
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text('$p: first reply ${((sla[p] as List?) ?? const ['-'])[0]} hours · resolution ${((sla[p] as List?) ?? const ['-', '-'])[1]} hours  ✎',
                style: const TextStyle(fontSize: 13)),
          ),
        ),
      const SizedBox(height: 12),
      Text('Refund / exchange rules (as written)', style: display(15)),
      Text(
          'Refund: ${pol['refund_days'] ?? '-'} days, max ₹${pol['refund_max'] ?? '-'} · Exchange:${pol['replace_days'] ?? '-'} days · Goodwill max ₹${pol['goodwill_max'] ?? '-'}'
          '${_s(pol['refund_mode']).isNotEmpty ? ' · ${pol['refund_mode']}' : ''}',
          style: const TextStyle(fontSize: 13)),
      const Text('Even within these rules, every refund happens only with your tap; if outside them, the card says so clearly.',
          style: TextStyle(fontSize: 12, color: C.muted)),
      GlassButton(
          label: 'Change rules',
          icon: Icons.rule_rounded,
          onTap: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Refund rules', const [
                    ('refund_days', 'Refund within how many days'),
                    ('refund_max', 'Maximum refund (₹)'),
                    ('replace_days', 'Exchange within how many days'),
                    ('goodwill_max', 'Goodwill / discount limit (₹)'),
                    ('refund_mode', 'Refund mode (UPI / cash / credit note)'),
                  ], initial: {for (final k in ['refund_days', 'refund_max', 'replace_days', 'goodwill_max', 'refund_mode']) if (pol[k] != null) k: '${pol[k]}'});
                  if (f == null) return;
                  await _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: {
                        'policy': {for (final e in f.entries) e.key: e.key == 'refund_mode' ? e.value : (_n(e.value) ?? '')}
                      }));
                }),
      const SizedBox(height: 12),
      SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('I sell online (E-Commerce Rules)'),
          subtitle: const Text('Acknowledge in 48 hours, resolve in 1 month; the grievance officer\'s name must be shown'),
          value: st['ecommerce'] == true,
          onChanged: (v) => _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: {'ecommerce': v}))),
      SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Ask for a rating (1-5) when closed'),
          value: st['csat_on'] != false,
          onChanged: (v) => _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: {'csat_on': v}))),
      SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Acknowledge a new complaint at once'),
          value: st['auto_ack'] != false,
          onChanged: (v) => _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: {'auto_ack': v}))),
      GlassButton(
          label: 'Grievance officer: ${_s(st['officer']).isEmpty ? 'set' : _s(st['officer'])}',
          icon: Icons.badge_rounded,
          onTap: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Grievance officer', const [('officer', 'Name'), ('officer_contact', 'Phone / email')],
                      initial: {'officer': _s(st['officer']), 'officer_contact': _s(st['officer_contact'])});
                  if (f != null) await _run(() => _call(widget.app, 'PUT', '/api/seva/settings', body: f));
                }),
    ]);
  }

  // ---------------------------------------------------------------- Hisaab
  Widget _reportTab() {
    final r = _report ?? const {};
    String h(dynamic v) => v == null ? '-' : '${(v as num).toStringAsFixed(1)} hours';
    String pct(dynamic v) => v == null ? '-' : '$v%';
    final ex = _map(r['exceptions']);
    Widget tile(String label, String value) => Glass(
          padding: const EdgeInsets.all(12),
          child: SizedBox(
              width: 130,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(value, style: display(18)),
                Text(label, style: const TextStyle(fontSize: 11.5, color: C.muted)),
              ])),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, children: [
        for (final d in const [7, 30, 90])
          ChoiceChip(
              label: Text('$d days'),
              selected: _days == d,
              onSelected: (_) {
                setState(() => _days = d);
                _load();
              }),
      ]),
      const SizedBox(height: 8),
      Text(_s(r['say']), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        tile('Ticket', '${r['tickets'] ?? 0}'),
        tile('First reply (middle)', h(r['first_response_median_h'])),
        tile('Resolution (middle)', h(r['resolution_median_h'])),
        tile('First reply on time', pct(r['first_response_sla_pct'])),
        tile('Resolved on time', pct(r['resolution_sla_pct'])),
        tile('Answered directly from knowledge base', pct(r['deflection_pct'])),
        tile('Happy customers (4-5)', pct(r['csat_pct'])),
        tile('Refund / exception approval', '${ex['approved'] ?? 0} / ${ex['asked'] ?? 0}'),
      ]),
      const SizedBox(height: 12),
      Text('Most asked', style: display(15)),
      for (final q in _list(r['top_questions'])) Text('• ${_s(q['question'])} (${q['times']})', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 8),
      Text('What the complaint is about', style: display(15)),
      for (final c in _list(r['by_category'])) Text('• ${_s(c['label'])}: ${c['count']}', style: const TextStyle(fontSize: 12.5)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    // v0.868 R8 wave 1: the shared desk frame (lib/ui/desk/desk_kit.dart)
    return DeskScaffold(
      title: 'Customer support',
      tabs: const ['Today', 'Complaint', 'Knowledge', 'Reply', 'Rules', 'Account'],
      tab: _tab,
      onTab: (i) => setState(() => _tab = i),
      loading: _d == null,
      onRefresh: _load,
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
        switch (_tab) { 0 => _today(), 1 => _ticketsTab(), 2 => _kbTab(), 3 => _macrosTab(), 4 => _rulesTab(), _ => _reportTab() },
      ]),
    );
  }

}

/// One ticket: status, SLA, customer line, internal notes, reply (text or macro), exception, merge.
class SevaTicketPage extends StatefulWidget {
  const SevaTicketPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<SevaTicketPage> createState() => _SevaTicketPageState();
}

class _SevaTicketPageState extends State<SevaTicketPage> {
  Map<String, dynamic>? _t;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _map(await _call(widget.app, 'GET', '/api/seva/tickets/${widget.id}'));
      if (mounted) setState(() => _t = t);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _act(String action, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/seva/tickets/${widget.id}/$action', body: body));
      final told = _map(r['told']);
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      final draft = _s(told['draft']);
      if (draft.isNotEmpty && mounted) {
        final go = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
            title: const Text('You send it to the customer'),
            content: Text(_s(told['text'])),
            actions: [
              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Later')),
              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Open WhatsApp')),
            ],
          ),
        );
        if (go == true) await launchUrl(Uri.parse(draft), mode: LaunchMode.externalApplication);
      }
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    final sla = _map(t?['sla']);
    return DeskPage(
      title: _s(t?['number']).isEmpty ? 'Complaint' : _s(t?['number']),
      loading: t == null,
      onRefresh: _load,
      body: () => t == null ? const SizedBox.shrink() : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text(_s(t['customer']), style: display(16))),
                      Pill(_s(t['priority']), fg: _priColor[_s(t['priority'])] ?? C.chip),
                    ]),
                    const SizedBox(height: 6),
                    Text(_s(t['text']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
                    const SizedBox(height: 6),
                    Text('${_s(t['category_label'])} · ${_s(t['channel'])} · ${_statusLabel[_s(t['status'])] ?? _s(t['status'])}',
                        style: const TextStyle(fontSize: 12, color: C.muted)),
                    Text(
                        'SLA: first reply ${sla['first_response_h'] ?? '-'} hours · resolution ${sla['resolve_h'] ?? '-'} hours'
                        '${sla['paused'] == true ? ' · time paused' : ''}${sla['late'] == true ? ' · LATE' : ''}',
                        style: TextStyle(fontSize: 12, color: sla['late'] == true ? C.bad : C.muted)),
                    const SizedBox(height: 6),
                    Text('The customer sees: ${_s(t['status_line'])}', style: const TextStyle(fontSize: 12.5, color: C.teal)),
                    for (final l in ((t['legal'] as List?) ?? const []))
                      Padding(padding: const EdgeInsets.only(top: 4), child: Text('ℹ $l', style: const TextStyle(fontSize: 12, color: C.warn))),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final (k, label) in const [('open', 'Work in progress'), ('pending', 'Reply from customer'), ('on_hold', 'On hold'), ('resolved', 'Fixed'), ('closed', 'Closed')])
                    ChoiceChip(
                        label: Text(label),
                        selected: t['status'] == k,
                        onSelected: _busy
                            ? null
                            : (_) async {
                                final f = await _form(context, label, const [('public', 'What to tell the customer (can be left blank)')], ok: 'Change');
                                if (f != null) await _act('update', {'status': k, ...f});
                              }),
                ]),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(
                      label: 'Send reply',
                      icon: Icons.send_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'To customer', const [('text', 'Your reply'), ('macro', 'Or the name of a ready reply')]);
                              if (f != null) await _act('reply', f);
                            }),
                  GlassButton(
                      label: 'Internal note',
                      icon: Icons.sticky_note_2_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Note (the customer does not see this)', const [('text', 'Note')]);
                              if (f != null) await _act('note', f);
                            }),
                  GlassButton(
                      label: 'Refund / discount request',
                      icon: Icons.currency_rupee_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Request (card for your yes)', const [
                                ('kind', 'refund / waiver / goodwill / replacement / extension / other'),
                                ('amount', 'Amount (₹)'),
                                ('reason', 'Why'),
                              ]);
                              if (f != null) await _act('exception', {...f, 'amount': _n(f['amount']) ?? 0, 'kind': f['kind'] ?? 'refund'});
                            }),
                  GlassButton(
                      label: 'Link to another ticket',
                      icon: Icons.merge_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Which ticket (same customer)', const [('into', 'Ticket number')]);
                              if (f != null) await _act('merge', f);
                            }),
                ]),
                for (final e in _list(t['exceptions']))
                  Padding(padding: const EdgeInsets.only(top: 10), child: SevaExceptionCard(key: ValueKey('ex${e['id']}${e['status']}'), app: widget.app, data: e, onDone: _load)),
                const SizedBox(height: 12),
                Text('Account', style: display(15)),
                for (final n in _list(t['notes']).reversed)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text('${_s(n['at']).length >= 16 ? _s(n['at']).substring(5, 16).replaceFirst('T', ' ') : ''} · ${_s(n['by'])}'
                        '${n['public'] == true ? ' (to customer)' : ''}: ${_s(n['text'])}',
                        style: TextStyle(fontSize: 12.5, color: n['public'] == true ? C.teal : C.ink)),
                  ),
              ]),
    );
  }
}

/// Chat / call card `seva_exception`: refund / waiver / goodwill / anything outside her policy. ONLY her tap decides;
/// a money card is signed with the phone's fingerprint key (428 -> challenge -> sign -> resend).
class SevaExceptionCard extends StatefulWidget {
  const SevaExceptionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SevaExceptionCard> createState() => _SevaExceptionCardState();
}

class _SevaExceptionCardState extends State<SevaExceptionCard> {
  bool _busy = false;
  late String _status = _s(widget.data['status']).isEmpty ? 'pending' : _s(widget.data['status']);

  String get _id => _s(widget.data['id']);

  Future<Map<String, dynamic>> _proof() async {
    final c = _map(await _call(widget.app, 'POST', '/api/seva/exceptions/$_id/challenge'));
    final show = _map(c['show']);
    final sub = [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · ');
    final r = await Native.approveKeySign('${c['message']}', '${show['title'] ?? 'Fingerprint to give your yes'}', sub);
    if (r['signature'] == null) {
      throw ApiException(428, switch ('${r['error'] ?? ''}') {
        'cancelled' => 'Fingerprint was not given, so approval did not happen.',
        'key_invalidated' => 'A new fingerprint was added on this phone: go to Profile > Approve with fingerprint and connect this phone again.',
        _ => 'This card is approved only by fingerprint; approve from the connected phone.',
      });
    }
    return {'challenge_id': c['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    String note = '';
    double? amount;
    if (!yes) {
      final f = await _form(context, 'Reason for declining (the customer will see this)', const [('note', 'Reason (can be left blank)')], ok: 'Decline');
      if (f == null) return;
      note = f['note'] ?? '';
    } else if ((widget.data['amount'] ?? 0) > 0) {
      final f = await _form(context, 'How much to approve?', const [('amount', 'Amount (₹)')],
          initial: {'amount': '${widget.data['amount']}'}, ok: 'Yes');
      if (f == null) return;
      amount = _n(f['amount']);
    }
    setState(() => _busy = true);
    final body = <String, dynamic>{'yes': yes, 'hash': widget.data['hash'], 'note': note, if (amount != null) 'amount': amount};
    try {
      dynamic r;
      try {
        r = await _call(widget.app, 'POST', '/api/seva/exceptions/$_id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        r = await _call(widget.app, 'POST', '/api/seva/exceptions/$_id/decide', body: {...body, 'proof': await _proof()});
      }
      final m = _map(r);
      if (mounted) {
        setState(() => _status = _s(_map(m['exception'])['status']).isEmpty ? (yes ? 'approved' : 'rejected') : _s(_map(m['exception'])['status']));
        _snack(context, _s(m['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sent() async {
    final f = await _form(context, 'Did you send the money?', const [('ref', 'UTR / ref (last 4 digits are enough)')], ok: 'Yes, I sent it');
    if (f == null) return;
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/seva/exceptions/$_id/sent', body: f));
      if (mounted) {
        setState(() => _status = 'sent');
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
    final v = widget.data;
    final chk = _map(v['check']);
    final within = chk['within'] == true;
    final money = ['refund', 'waiver', 'goodwill'].contains(v['kind']) && (v['amount'] ?? 0) > 0;
    return Glass(
      border: _status == 'pending' ? (within ? C.ok : C.warn) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.gavel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(v['kind_label'])}${_s(v['amount_text']).isNotEmpty ? ' · ${v['amount_text']}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(v['number'])),
        ]),
        const SizedBox(height: 4),
        Text('${_s(v['customer'])}: ${_s(v['reason'])}', style: const TextStyle(fontSize: 13, height: 1.35)),
        const SizedBox(height: 4),
        Text(within ? 'Within the rules you wrote (the decision is still yours)' : 'Outside the rules', style: TextStyle(fontSize: 12.5, color: within ? C.ok : C.warn, fontWeight: FontWeight.w700)),
        for (final r in ((chk['reasons'] as List?) ?? const [])) Text('• $r', style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (_status == 'pending') ...[
          if (money) const Text('Yes, with fingerprint. Hoola does not send money itself.', style: TextStyle(fontSize: 11.5, color: C.muted)),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes', icon: money ? Icons.fingerprint_rounded : Icons.check_rounded, height: 46, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Decline', icon: Icons.close_rounded, onTap: _busy ? null : () => _decide(false))),
          ]),
        ] else if (_status == 'approved' && money)
          GlassButton(label: 'I sent the money', icon: Icons.done_all_rounded, onTap: _busy ? null : _sent)
        else
          Pill(switch (_status) { 'approved' => 'approved', 'rejected' => 'declined', 'sent' => 'money sent', 'cancelled' => 'taken back', _ => _status },
              fg: _status == 'rejected' ? C.bad : C.ok),
      ]),
    );
  }
}

/// Chat card `seva_ticket` (new / updated ticket) and `seva_sla` (deadline warning): opens the ticket.
class SevaTicketCard extends StatelessWidget {
  const SevaTicketCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final sla = data.containsKey('kind') && data.containsKey('text') && !data.containsKey('status');
    final id = _s(data['ticket_id']).isNotEmpty ? _s(data['ticket_id']) : _s(data['id']);
    return Press(
      onTap: id.isEmpty ? null : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SevaTicketPage(app: app, id: id))),
      child: Glass(
        border: sla ? (data['breach'] == true ? C.bad : C.warn) : (data['priority'] == 'urgent' ? C.bad : null),
        child: Row(children: [
          Icon(sla ? Icons.timer_rounded : Icons.support_agent_rounded, color: sla ? C.warn : C.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                  sla
                      ? _s(data['text'])
                      : '${_s(data['number'])} · ${_s(data['customer'])} · ${_statusLabel[_s(data['status'])] ?? _s(data['status'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
              if (!sla) Text(_s(data['text']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ]),
          ),
          if (!sla) Pill(_s(data['priority']), fg: _priColor[_s(data['priority'])] ?? C.chip),
        ]),
      ),
    );
  }
}

/// Chat card `seva_day`: the morning support note.
class SevaDayCard extends StatelessWidget {
  const SevaDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SevaScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.support_agent_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['text']), style: const TextStyle(fontWeight: FontWeight.w700, height: 1.35))),
            IconButton(
                icon: const Icon(Icons.copy_rounded, size: 18),
                onPressed: () => Clipboard.setData(ClipboardData(text: _s(data['text'])))),
          ]),
        ),
      );
}
