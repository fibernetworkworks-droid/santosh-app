/// Profile > Lawyer's junior (Vakil Sahayak).
/// Aaj (today's / tomorrow's dates, limitation near, dates not updated, her taps waiting) · Matters (case diary -> matter page:
/// hearings, list of dates & events, documents, drafts, cards, fees) · Limitation (andaaza from her dates) · eCourts (paste the
/// case status / cause list text she copied from the official eCourts app or court site) · Niyam.
/// Filing, any message / notice to a client or the other side, and fee requests happen ONLY on her tap here (fee with her
/// fingerprint once a phone key is set up). Hoola is not a lawyer: drafts and andaaza only.
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
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());

const _check = 'This is a draft / estimate, not advice: confirm with your lawyer.';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _stColor(String st) => switch (st) {
      'rejected' || 'stale' || 'missing' => C.bad,
      'waiting' || 'pending' || 'open' => C.warn,
      'approved' || 'done' || 'have' || 'disposed' => C.ok,
      _ => C.chip,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Continue', Map<String, String> initial = const {}, Set<String> big = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: big.contains(k) ? 6 : 1),
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

Future<void> _openLinks(BuildContext context, Map<String, dynamic> r) async {
  final links = _m(r['links']);
  final steps = _strs(r['steps']);
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
                    'whatsapp' => 'Open WhatsApp draft',
                    'sms' => 'Open SMS draft',
                    'email' => 'Open email draft',
                    'upi' => 'UPI link',
                    _ => e.key
                  },
                  icon: Icons.open_in_new_rounded,
                  onTap: () => Native.openExternal(url: _s(e.value))),
            ),
          if (_s(r['link']).isNotEmpty)
            GlassButton(label: 'Open eFiling portal', icon: Icons.gavel_rounded, onTap: () => Native.openExternal(url: _s(r['link']))),
          const SizedBox(height: 6),
          const Text('Hoola does not send or file it itself: you do it.', style: TextStyle(fontSize: 11, color: C.faint)),
        ]),
      ),
    ),
  );
}

class VakilScreen extends StatefulWidget {
  const VakilScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<VakilScreen> createState() => _VakilScreenState();
}

class _VakilScreenState extends State<VakilScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  Map<String, dynamic>? _lastPaste;
  Map<String, dynamic>? _lastLimit;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/vakil'));
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
      .push(MaterialPageRoute(builder: (_) => VakilMatterPage(app: widget.app, matterRef: ref)))
      .then((_) => _load());

  Future<void> _newMatter() async {
    final f = await _form(context, 'New matter', const [
      ('title', "Matter ('Patil vs Deshmukh')"),
      ('client', 'Client name'),
      ('client_phone', 'Client mobile'),
      ('kind', 'Kind: civil_suit / criminal / bail / cheque_138 / consumer / family / writ / appeal / other'),
      ('side', 'Our side: plaintiff / defendant / petitioner / respondent / complainant / accused / appellant'),
      ('opposite', 'Other side'),
      ('court', 'Court'),
      ('case', "Case number ('RCS 123/2024')"),
      ('cnr', 'CNR (16 characters, if any)'),
      ('next_date', 'Next date (DD-MM-YYYY)'),
      ('next_purpose', 'What is next on the next date'),
    ], ok: 'Create');
    if (f == null || (f['title'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/vakil/matters', f);
    if (r != null && _s(r['id']).isNotEmpty && mounted) _open(_s(r['id']));
  }

  Widget _matterTile(Map<String, dynamic> m) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _open(_s(m['id'])),
          child: Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.gavel_rounded, color: C.accent, size: 20),
                const SizedBox(width: 8),
                Expanded(child: Text('${_s(m['number'])} · ${_s(m['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(m['status']), fg: _stColor(_s(m['status']))),
              ]),
              Text([_s(m['case']), _s(m['court']), _s(m['client'])].where((x) => x.isNotEmpty).join(' · '),
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (_s(m['next_date']).isNotEmpty)
                Text('Next date: ${_s(m['next_date'])}${_s(m['next_purpose']).isEmpty ? '' : ' (${_s(m['next_purpose'])})'}',
                    style: TextStyle(fontSize: 12.5, color: m['date_stale'] == true ? C.warn : C.ink)),
              if (m['date_stale'] == true)
                const Text('The date has passed: write the status / next date', style: TextStyle(fontSize: 12, color: C.warn)),
            ]),
          ),
        ),
      );

  Widget _today() {
    final day = _m(_d?['day']);
    final cards = _list(_d?['cards']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      GradientButton(label: 'New matter', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newMatter),
      const SizedBox(height: 12),
      for (final (key, title) in const [('today', 'TODAY\'S HEARING DATES'), ('tomorrow', 'TOMORROW'), ('stale', 'DATES TO UPDATE')])
        if (_list(day[key]).isNotEmpty) ...[
          Caption(title),
          for (final r in _list(day[key]))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Press(
                onTap: () => _open(_s(r['matter'])),
                child: Text('• ${_s(r['matter'])} ${_s(r['title'])} ${_s(r['court']).isEmpty ? '' : '· ${_s(r['court'])}'}',
                    style: const TextStyle(fontSize: 13)),
              ),
            ),
          const SizedBox(height: 8),
        ],
      if (_list(day['limitation']).isNotEmpty) ...[
        const Caption('LIMITATION NEARING (ESTIMATE)'),
        for (final r in _list(day['limitation']))
          Text('• ${_s(r['matter'])} ${_s(r['label'])}: ${_s(r['last_date'])} (${_s(r['days_left'])} days)',
              style: TextStyle(fontSize: 13, color: (r['days_left'] is num && (r['days_left'] as num) <= 3) ? C.bad : C.ink)),
        const SizedBox(height: 8),
      ],
      if (cards.isNotEmpty) ...[
        const Caption('YOUR APPROVAL PENDING'),
        for (final c in cards)
          Padding(padding: const EdgeInsets.only(bottom: 8), child: VakilCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      ],
      const Text(_check, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _mattersTab() {
    final ms = _list(_d?['matters']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'New matter', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newMatter),
      const SizedBox(height: 12),
      for (final m in ms) _matterTile(m),
      if (ms.isEmpty) const Text('The diary is empty.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Diary Excel',
          icon: Icons.table_view_rounded,
          onTap: _busy ? null : () => _run('GET', '/api/vakil/register')),
    ]);
  }

  Future<void> _tryLimit() async {
    final f = await _form(context, 'Limitation (estimate)', const [
      ('kind', 'Which: appeal_hc_civil / appeal_other_civil / review / revision / money_loan / ... / custom'),
      ('start', 'Starting date (order / decree / cause of action)'),
      ('cc_applied', 'Certified copy requested (date, if any)'),
      ('cc_ready', 'Certified copy received (date, if any)'),
      ('n', 'Period told by the lawyer (only for custom / not in the table)'),
      ('unit', 'Unit: d / m / y'),
      ('matter', 'Matter (to save, if any)'),
    ], ok: 'Find');
    if (f == null || (f['kind'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    if (f['n'] != null) body['n'] = _n(f['n']);
    final path = (f['matter'] ?? '').isNotEmpty ? '/api/vakil/matters/${Uri.encodeComponent(f['matter']!)}/limitation' : '/api/vakil/limitation';
    final r = await _run('POST', path, body);
    if (r != null && mounted) setState(() => _lastLimit = r);
  }

  Widget _limitTab() {
    final dl = _list(_d?['deadlines']);
    final r = _lastLimit;
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Find the last date', icon: Icons.event_busy_rounded, height: 46, onTap: _busy ? null : _tryLimit),
      const SizedBox(height: 12),
      if (r != null)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(r['say']).isEmpty ? _s(r['ask']) : _s(r['say']), style: const TextStyle(fontWeight: FontWeight.w700)),
            for (final st in _strs(r['steps'])) Text('• $st', style: const TextStyle(fontSize: 12.5)),
            if (_s(r['source']).isNotEmpty) Text('Source: ${_s(r['source'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
            for (final n in _strs(r['notes'])) Text(n, style: const TextStyle(fontSize: 12, color: C.warn)),
          ]),
        ),
      const SizedBox(height: 12),
      const Caption('SAVED DEADLINES'),
      for (final x in dl)
        ListTile(
          leading: Icon(Icons.timer_rounded, color: (x['days_left'] is num && (x['days_left'] as num) <= 7) ? C.bad : C.accent),
          title: Text('${_s(x['matter'])} · ${_s(x['label'])}'),
          subtitle: Text('Last date (estimate) ${_s(x['last_date'])} · ${_s(x['days_left'])} days · ${_s(x['source'])}'),
          trailing: IconButton(
              icon: const Icon(Icons.check_circle_outline_rounded),
              onPressed: () => _run('POST', '/api/vakil/deadlines/${_s(x['id'])}', {'status': 'done'})),
        ),
      if (dl.isEmpty) const Text('No open deadlines.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 8),
      const Text(_check, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Future<void> _paste(bool cause) async {
    final f = await _form(
        context,
        cause ? 'Paste cause list' : 'Paste case status',
        cause
            ? const [('text', 'Cause list text copied from the eCourts app / court site'), ('on', 'Date (if not in the text)')]
            : const [('text', 'Case Status text from the eCourts app / site'), ('matter', 'Matter (if no CNR)')],
        ok: 'Read',
        big: const {'text'});
    if (f == null || (f['text'] ?? '').isEmpty) return;
    final r = await _run('POST', cause ? '/api/vakil/paste/cause_list' : '/api/vakil/paste/status', f);
    if (r != null && mounted) setState(() => _lastPaste = r);
  }

  Widget _ecourtsTab() {
    final off = _m(_m(_d?['settings'])['official']);
    final r = _lastPaste;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Through official routes', style: TextStyle(fontWeight: FontWeight.w800)),
          Text('• ${_s(off['app'])}', style: const TextStyle(fontSize: 12.5)),
          Text('• ${_s(off['sms'])}', style: const TextStyle(fontSize: 12.5)),
          const Text('Copy the case status / cause list from there and paste it here; Hoola reads it and fills the diary.',
              style: TextStyle(fontSize: 12.5, color: C.muted)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(
                label: 'eCourts case status',
                icon: Icons.open_in_new_rounded,
                onTap: () => Native.openExternal(url: _s(off['case_status']))),
            GlassButton(label: 'eFiling', icon: Icons.open_in_new_rounded, onTap: () => Native.openExternal(url: _s(off['efiling']))),
          ]),
        ]),
      ),
      const SizedBox(height: 12),
      GradientButton(label: 'Paste case status', icon: Icons.content_paste_rounded, height: 46, onTap: _busy ? null : () => _paste(false)),
      const SizedBox(height: 8),
      GradientButton(label: 'Paste cause list', icon: Icons.list_alt_rounded, height: 46, onTap: _busy ? null : () => _paste(true)),
      const SizedBox(height: 12),
      if (r != null)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(r['say']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
            for (final c in _strs(r['changes'])) Text('• $c', style: const TextStyle(fontSize: 12.5)),
            for (final x in _list(r['found']))
              Text('• ${_s(x['matter'])} item ${_s(x['item'])} (${_s(x['case'])})', style: const TextStyle(fontSize: 12.5)),
            for (final x in _list(r['not_listed']))
              Text('⚠ ${_s(x['matter'])} ${_s(x['title'])}: not in the list', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          ]),
        ),
    ]);
  }

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Rules / office', const [
      ('advocate', 'Lawyer name'),
      ('enrolment_no', 'Bar Council enrolment no.'),
      ('office', 'Office / chamber name'),
      ('address', 'Address'),
      ('phone', 'Office mobile'),
      ('email', 'Email'),
      ('upi_id', 'UPI ID (on fee notes)'),
      ('state', 'State'),
      ('place', 'Place (on drafts)'),
      ('closed_dates', 'Court holidays (YYYY-MM-DD, comma separated)'),
      ('closed_weekdays', 'Closed days (0=Mon..6=Sun, comma separated)'),
      ('remind_days', 'Limitation reminders (days, e.g. 30,15,7,3,1,0)'),
      ('morning_time', 'Morning note (HH:MM)'),
    ], ok: 'Save', initial: {
      for (final k in ['advocate', 'enrolment_no', 'office', 'address', 'phone', 'email', 'upi_id', 'state', 'place', 'morning_time']) k: _s(st[k]),
      'closed_dates': _strs(st['closed_dates']).join(', '),
      'closed_weekdays': _strs(st['closed_weekdays']).join(','),
      'remind_days': _strs(st['remind_days']).join(','),
    });
    if (f == null) return;
    await _run('PUT', '/api/vakil/settings', f);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['advocate']).isEmpty ? 'Enter the lawyer name' : _s(st['advocate']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Enrolment: ${_s(st['enrolment_no']).isEmpty ? '—' : _s(st['enrolment_no'])} · ${_s(st['office'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('Court closed: ${_strs(st['closed_dates']).length} holidays, days ${_strs(st['closed_weekdays']).join(',')}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Edit', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('HOOLA WILL NEVER DO'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Today', 'Matters', 'Limitation', 'eCourts', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text("${widget.app.aName} · Lawyer's junior"),
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
                  child: switch (_tab) { 0 => _today(), 1 => _mattersTab(), 2 => _limitTab(), 3 => _ecourtsTab(), _ => _rulesTab() },
                ),
        ),
      ]),
    );
  }
}

/// One matter: diary, hearings, list of dates & events, documents, drafts, cards, fees.
class VakilMatterPage extends StatefulWidget {
  const VakilMatterPage({super.key, required this.app, required this.matterRef});
  final Santosh app;
  final String matterRef;
  @override
  State<VakilMatterPage> createState() => _VakilMatterPageState();
}

class _VakilMatterPageState extends State<VakilMatterPage> {
  Map<String, dynamic>? _m0;
  bool _busy = false;

  String get _ref => Uri.encodeComponent(_s(_m0?['id']).isEmpty ? widget.matterRef : _s(_m0?['id']));

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/vakil/matters/${Uri.encodeComponent(widget.matterRef)}'));
      if (mounted) setState(() => _m0 = d);
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
    final m = _m0 ?? {};
    final f = await _form(context, 'Edit matter', const [
      ('title', 'Matter'),
      ('court', 'Court'),
      ('court_no', 'Court hall / judge'),
      ('case', "Case number ('RCS 123/2024')"),
      ('cnr', 'CNR'),
      ('stage', 'Stage'),
      ('next_date', 'Next date'),
      ('next_purpose', 'What is next on the next date'),
      ('opposite', 'Other side'),
      ('opposite_advocate', 'Opposing lawyer'),
      ('opposite_contact', 'Their phone / email'),
      ('acts', 'Acts / sections (as told by the lawyer)'),
      ('status', 'Status: pending / disposed / closed'),
    ], ok: 'Save', initial: {
      for (final k in ['title', 'court', 'court_no', 'cnr', 'stage', 'next_date', 'next_purpose', 'opposite', 'opposite_advocate', 'opposite_contact', 'acts', 'status'])
        k: _s(m[k]),
    });
    if (f == null) return;
    await _run('PATCH', '/api/vakil/matters/$_ref', f);
  }

  Future<void> _hearing() async {
    final f = await _form(context, 'Hearing status', const [
      ('on', 'On which day (DD-MM-YYYY)'),
      ('purpose', 'Purpose of the hearing'),
      ('result', 'What happened'),
      ('stage', 'Ab stage'),
      ('next_date', 'Next date (given by the court)'),
      ('next_purpose', 'What is next on the next date'),
    ], ok: 'Write');
    if (f == null) return;
    await _run('POST', '/api/vakil/matters/$_ref/hearing', f);
  }

  Future<void> _event() async {
    final f = await _form(context, 'Add to list of dates', const [('on', 'Date'), ('what', 'What happened')], ok: 'Add', big: const {'what'});
    if (f == null) return;
    await _run('POST', '/api/vakil/matters/$_ref/event', f);
  }

  Future<void> _draft() async {
    final kind = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, l) in const [
            ('adjournment', 'Adjournment application'),
            ('vakalatnama', 'Vakalatnama checklist'),
            ('dates_events', 'List of dates & events'),
            ('synopsis', 'Synopsis'),
            ('notice_reply', 'Reply to notice (drafter)'),
            ('note', 'Brief note'),
          ])
            ListTile(title: Text(l), onTap: () => Navigator.pop(c, k)),
        ]),
      ),
    );
    if (kind == null) return;
    Map<String, String> f = {};
    if (kind == 'adjournment') {
      f = await _form(context, 'Reason for adjournment', const [('reason', 'Reason (in your words)')], big: const {'reason'}) ?? {};
    } else if (kind == 'notice_reply' || kind == 'note' || kind == 'synopsis') {
      final r = await _form(context, 'Your words', const [('words', 'What the notice says / what the reply should say'), ('to', 'To')],
          big: const {'words'});
      if (r == null) return;
      f = r;
    }
    await _run('POST', '/api/vakil/matters/$_ref/draft', {'kind': kind, ...f});
  }

  Future<void> _message(String to) async {
    Map<String, String>? f = {};
    if (to != 'client') {
      f = await _form(context, 'What to send to the other side', const [('text', 'Text (written by the lawyer)'), ('phone', 'Phone'), ('email', 'Email')],
          big: const {'text'});
      if (f == null) return;
    } else {
      f = await _form(context, 'Update to client', const [('text', 'Your own text (empty = Hoola writes from the diary)')], big: const {'text'}, ok: 'Make card');
      if (f == null) return;
    }
    await _run('POST', '/api/vakil/matters/$_ref/message', {'to': to, ...f});
  }

  Future<void> _filing() async {
    final f = await _form(context, 'Filing card', const [('what', 'What to file'), ('note', 'Note')]);
    if (f == null || (f['what'] ?? '').isEmpty) return;
    final op = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        content: const Text('After your yes, open the eFiling portal in Hoola\'s browser? (You do login / OTP / court fee / eSign / Submit.)'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('No, I will do it myself')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Yes, open it')),
        ],
      ),
    );
    await _run('POST', '/api/vakil/matters/$_ref/filing', {...f, 'use_operator': op == true});
  }

  Future<void> _fee(bool request) async {
    if (request) {
      final f = await _form(context, 'Ask for fee (card)', const [('amount', 'Amount (yours)'), ('for', 'For what')]);
      if (f == null || _n(f['amount']) == null) return;
      await _run('POST', '/api/vakil/matters/$_ref/fee_request', {'amount': _n(f['amount']), 'for': f['for'] ?? ''});
      return;
    }
    final f = await _form(context, 'Fee account', const [('kind', 'agreed / received / expense'), ('amount', 'Amount'), ('note', 'Note'), ('ref_no', 'UTR / ref')]);
    if (f == null || _n(f['amount']) == null) return;
    await _run('POST', '/api/vakil/matters/$_ref/fee', {...f, 'amount': _n(f['amount'])});
  }

  Future<void> _docState(Map<String, dynamic> d) async {
    final next = switch (_s(d['state'])) { 'missing' => 'have', 'have' => 'na', _ => 'missing' };
    await _run('POST', '/api/vakil/matters/$_ref/docs', {'key': _s(d['key']), 'state': next, 'label': _s(d['label'])});
  }

  @override
  Widget build(BuildContext context) {
    final m = _m0;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(m == null ? 'Matter' : '${_s(m['number'])} · ${_s(m['title'])}'),
        actions: [IconButton(onPressed: _edit, icon: const Icon(Icons.edit_rounded))],
      ),
      body: m == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(m['case'])} · ${_s(m['kind_label'])} · ${_s(m['side'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text([_s(m['court']), _s(m['court_no'])].where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (_s(m['cnr']).isNotEmpty) Text('CNR ${_s(m['cnr'])}', style: const TextStyle(fontSize: 12.5)),
                    Text('Client: ${_s(m['client'])} ${_s(m['client_phone'])}', style: const TextStyle(fontSize: 12.5)),
                    if (_s(m['opposite']).isNotEmpty) Text('Other side: ${_s(m['opposite'])} ${_s(m['opposite_advocate'])}', style: const TextStyle(fontSize: 12.5)),
                    Text('Stage: ${_s(m['stage']).isEmpty ? '—' : _s(m['stage'])} · Next date: ${_s(m['next_date']).isEmpty ? '—' : _s(m['next_date'])} ${_s(m['next_purpose'])}',
                        style: TextStyle(fontSize: 12.5, color: m['date_stale'] == true ? C.warn : C.ink)),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(label: 'Hearing status', icon: Icons.event_note_rounded, onTap: _busy ? null : _hearing),
                  GlassButton(label: 'Add event', icon: Icons.timeline_rounded, onTap: _busy ? null : _event),
                  GlassButton(label: 'Draft', icon: Icons.description_rounded, onTap: _busy ? null : _draft),
                  GlassButton(label: 'Update to client', icon: Icons.chat_rounded, onTap: _busy ? null : () => _message('client')),
                  GlassButton(label: 'To the other side', icon: Icons.mark_email_unread_rounded, onTap: _busy ? null : () => _message('opposite')),
                  GlassButton(label: 'Filing', icon: Icons.upload_file_rounded, onTap: _busy ? null : _filing),
                  GlassButton(label: 'Ask for fee', icon: Icons.request_quote_rounded, onTap: _busy ? null : () => _fee(true)),
                  GlassButton(label: 'Fee account', icon: Icons.account_balance_wallet_rounded, onTap: _busy ? null : () => _fee(false)),
                ]),
                const SizedBox(height: 12),
                for (final c in _list(m['cards']).where((c) => _s(c['status']) == 'waiting' || _s(c['status']) == 'approved'))
                  Padding(padding: const EdgeInsets.only(bottom: 8), child: VakilCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
                const Caption('HEARINGS'),
                for (final h in _list(m['hearings']).reversed.take(20))
                  Text('• ${_s(h['on'])}: ${_s(h['result']).isEmpty ? _s(h['purpose']) : _s(h['result'])}${_s(h['next']).isEmpty ? '' : ' → ${_s(h['next'])}'}',
                      style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
                const Caption('LIST OF DATES & EVENTS'),
                for (final e in _list(m['events'])) Text('• ${_s(e['on'])}: ${_s(e['what'])}', style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
                const Caption('DOCUMENTS (tap = have / no / missing)'),
                for (final d in _list(m['docs']))
                  ListTile(
                    dense: true,
                    onTap: _busy ? null : () => _docState(d),
                    leading: Icon(_s(d['state']) == 'have' ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                        color: _stColor(_s(d['state']))),
                    title: Text(_s(d['label']), style: const TextStyle(fontSize: 13)),
                    trailing: Pill(_s(d['state']), fg: _stColor(_s(d['state']))),
                  ),
                const SizedBox(height: 10),
                const Caption('LIMITATION'),
                for (final x in _list(m['deadlines']))
                  Text('• ${_s(x['label'])}: ${_s(x['last_date'])} (${_s(x['status'])}) · ${_s(x['source'])}', style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
                const Caption('DRAFTS'),
                for (final d in _list(m['drafts'])) VakilDraftCard(app: widget.app, data: {'draft': d}),
                const SizedBox(height: 10),
                const Caption('FEE'),
                Builder(builder: (_) {
                  final f = _m(m['fees']);
                  final t = _m(f['totals']);
                  return Text('Agreed ${_s(t['agreed'])} · asked ${_s(t['requested'])} · received ${_s(t['received'])} · expenses ${_s(t['expense'])} · due ${_s(f['due_text'])}',
                      style: const TextStyle(fontSize: 12.5));
                }),
                const SizedBox(height: 10),
                const Text(_check, style: TextStyle(fontSize: 11, color: C.faint)),
              ]),
            ),
    );
  }
}

/// vakil_card: filing / message / fee request. Decided ONLY by her tap here (fee: fingerprint once a phone key is active).
/// Also in calls.
class VakilCardCard extends StatefulWidget {
  const VakilCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<VakilCardCard> createState() => _VakilCardCardState();
}

class _VakilCardCardState extends State<VakilCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/vakil/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Fee approval' : _s(show['title']),
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
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash'])};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/vakil/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/vakil/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        if (_m(m['card']).isNotEmpty) setState(() => _c = _m(m['card']));
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
    Map<String, String> f = {};
    if (_s(_c['kind']) == 'filing') {
      f = await _form(context, 'Filed', const [('ref_no', 'eFiling number')]) ?? {};
    }
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', '/api/vakil/cards/${_s(_c['id'])}/done', body: f));
      if (mounted) {
        if (_m(m['card']).isNotEmpty) setState(() => _c = _m(m['card']));
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
    final c = _c;
    final st = _s(c['status']);
    final b = _m(c['body']);
    final kind = _s(c['kind']);
    final icon = switch (kind) { 'filing' => Icons.upload_file_rounded, 'fee' => Icons.request_quote_rounded, _ => Icons.chat_rounded };
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(icon, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_s(c['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'yes', 'stale' => 'stale', 'rejected' => 'no', _ => st }, fg: _stColor(st)),
        ]),
        if (kind == 'message') ...[
          Text('To: ${_s(b['name'])} ${_s(b['phone']).isEmpty ? '' : '· ${_s(b['phone'])}'} ${_s(b['email'])}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text(_s(b['text']), style: const TextStyle(fontSize: 13)),
        ],
        if (kind == 'filing') ...[
          Text('${_s(b['what'])} · ${_s(b['court'])} · ${_s(b['case'])}', style: const TextStyle(fontSize: 12.5)),
          for (final d in _list(b['deadlines'])) Text('⏱ ${_s(d['label'])}: ${_s(d['last_date'])} (estimate)', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_strs(b['missing_docs']).isNotEmpty)
            Text('Documents pending: ${_strs(b['missing_docs']).take(5).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (b['use_operator'] == true)
            const Text('After your yes, Hoola\'s browser will open the portal; you do login / OTP / fee / eSign / Submit.', style: TextStyle(fontSize: 12, color: C.muted)),
        ],
        if (kind == 'fee') ...[
          Text('${_s(b['amount_text'])} · ${_s(b['for'])} · ${_s(b['client'])}', style: const TextStyle(fontSize: 13)),
          Text(_s(b['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ],
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: switch (kind) { 'filing' => 'Yes, start filing', 'fee' => 'Yes, make the fee note', _ => 'Yes, give the links' },
                    height: 42,
                    onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved' && kind != 'fee')
          Row(children: [
            Expanded(child: GlassButton(label: 'Links / steps', icon: Icons.open_in_new_rounded, onTap: () => _openLinks(context, _m(c['result'])))),
            const SizedBox(width: 8),
            GlassButton(label: kind == 'filing' ? 'Filed' : 'Sent', icon: Icons.check_rounded, onTap: _busy ? null : _done),
          ]),
        if (st == 'approved' && kind == 'fee')
          GlassButton(label: 'Message / UPI link', icon: Icons.open_in_new_rounded, onTap: () => _openLinks(context, _m(c['result']))),
        if (st == 'stale') const Text('Details changed after the card was made: make a new card.', style: TextStyle(fontSize: 12, color: C.warn)),
        const Text('Hoola does not send or file anything itself and does not take money.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// vakil_draft: a draft (Word) for the advocate. Calls: no.
class VakilDraftCard extends StatelessWidget {
  const VakilDraftCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final d = _m(data['draft']);
    final blanks = d['blanks'] is num ? (d['blanks'] as num).toInt() : 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.description_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(d['number'])} · ${_s(d['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            const Pill('DRAFT', fg: C.warn),
          ]),
          if (blanks > 0) Text('$blanks blanks: fill them in', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_s(d['text']).isNotEmpty)
            Text(_s(d['text']).length > 400 ? '${_s(d['text']).substring(0, 400)}…' : _s(d['text']), style: const TextStyle(fontSize: 12)),
          if (_s(data['matter']).isNotEmpty)
            TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VakilMatterPage(app: app, matterRef: _s(data['matter'])))),
                child: const Text('Open matter')),
          const Text(_check, style: TextStyle(fontSize: 11, color: C.faint)),
        ]),
      ),
    );
  }
}

/// vakil_alert / vakil_day: reminders and the morning note. Calls: no.
class VakilNoteCard extends StatelessWidget {
  const VakilNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.gavel_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4))),
          IconButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VakilScreen(app: app))),
              icon: const Icon(Icons.open_in_new_rounded, size: 18)),
        ]),
      );
}
