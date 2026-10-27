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

const _check = 'Draft / andaaza hai, salah nahi: vakil sahab se pakka karwaiye.';

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
    {String ok = 'Aage', Map<String, String> initial = const {}, Set<String> big = const {}}) async {
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
                    'whatsapp' => 'WhatsApp draft kholo',
                    'sms' => 'SMS draft kholo',
                    'email' => 'Email draft kholo',
                    'upi' => 'UPI link',
                    _ => e.key
                  },
                  icon: Icons.open_in_new_rounded,
                  onTap: () => Native.openExternal(url: _s(e.value))),
            ),
          if (_s(r['link']).isNotEmpty)
            GlassButton(label: 'eFiling portal kholo', icon: Icons.gavel_rounded, onTap: () => Native.openExternal(url: _s(r['link']))),
          const SizedBox(height: 6),
          const Text('Hoola khud nahi bhejta / file nahi karta: aap kijiye.', style: TextStyle(fontSize: 11, color: C.faint)),
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
    final f = await _form(context, 'Naya matter', const [
      ('title', "Matter ('Patil vs Deshmukh')"),
      ('client', 'Client ka naam'),
      ('client_phone', 'Client ka mobile'),
      ('kind', 'Kind: civil_suit / criminal / bail / cheque_138 / consumer / family / writ / appeal / other'),
      ('side', 'Hum: plaintiff / defendant / petitioner / respondent / complainant / accused / appellant'),
      ('opposite', 'Doosra paksh'),
      ('court', 'Court'),
      ('case', "Case number ('RCS 123/2024')"),
      ('cnr', 'CNR (16 akshar, ho to)'),
      ('next_date', 'Agli tareekh (DD-MM-YYYY)'),
      ('next_purpose', 'Agli tareekh par kya'),
    ], ok: 'Banao');
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
                Text('Agli tareekh: ${_s(m['next_date'])}${_s(m['next_purpose']).isEmpty ? '' : ' (${_s(m['next_purpose'])})'}',
                    style: TextStyle(fontSize: 12.5, color: m['date_stale'] == true ? C.warn : C.ink)),
              if (m['date_stale'] == true)
                const Text('Tareekh nikal gayi: haal / agli tareekh likhiye', style: TextStyle(fontSize: 12, color: C.warn)),
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
      GradientButton(label: 'Naya matter', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newMatter),
      const SizedBox(height: 12),
      for (final (key, title) in const [('today', 'AAJ KI TAREEKHEIN'), ('tomorrow', 'KAL'), ('stale', 'TAREEKH UPDATE KARNI HAI')])
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
        const Caption('LIMITATION PAAS (ANDAAZA)'),
        for (final r in _list(day['limitation']))
          Text('• ${_s(r['matter'])} ${_s(r['label'])}: ${_s(r['last_date'])} (${_s(r['days_left'])} din)',
              style: TextStyle(fontSize: 13, color: (r['days_left'] is num && (r['days_left'] as num) <= 3) ? C.bad : C.ink)),
        const SizedBox(height: 8),
      ],
      if (cards.isNotEmpty) ...[
        const Caption('AAPKI HAAN BAAKI'),
        for (final c in cards)
          Padding(padding: const EdgeInsets.only(bottom: 8), child: VakilCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      ],
      const Text(_check, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Widget _mattersTab() {
    final ms = _list(_d?['matters']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Naya matter', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newMatter),
      const SizedBox(height: 12),
      for (final m in ms) _matterTile(m),
      if (ms.isEmpty) const Text('Abhi diary khaali hai.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Diary Excel',
          icon: Icons.table_view_rounded,
          onTap: _busy ? null : () => _run('GET', '/api/vakil/register')),
    ]);
  }

  Future<void> _tryLimit() async {
    final f = await _form(context, 'Limitation (andaaza)', const [
      ('kind', 'Kaunsa: appeal_hc_civil / appeal_other_civil / review / revision / money_loan / ... / custom'),
      ('start', 'Shuruaat ki tareekh (order / decree / cause of action)'),
      ('cc_applied', 'Certified copy maangi (tareekh, ho to)'),
      ('cc_ready', 'Certified copy mili (tareekh, ho to)'),
      ('n', 'Vakil ka bataya period (sirf custom / table mein na ho)'),
      ('unit', 'Unit: d / m / y'),
      ('matter', 'Matter (save karne ke liye, ho to)'),
    ], ok: 'Nikaalo');
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
      GradientButton(label: 'Aakhri tareekh nikaalo', icon: Icons.event_busy_rounded, height: 46, onTap: _busy ? null : _tryLimit),
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
      const Caption('SAVE KI HUI DEADLINES'),
      for (final x in dl)
        ListTile(
          leading: Icon(Icons.timer_rounded, color: (x['days_left'] is num && (x['days_left'] as num) <= 7) ? C.bad : C.accent),
          title: Text('${_s(x['matter'])} · ${_s(x['label'])}'),
          subtitle: Text('Aakhri tareekh (andaaza) ${_s(x['last_date'])} · ${_s(x['days_left'])} din · ${_s(x['source'])}'),
          trailing: IconButton(
              icon: const Icon(Icons.check_circle_outline_rounded),
              onPressed: () => _run('POST', '/api/vakil/deadlines/${_s(x['id'])}', {'status': 'done'})),
        ),
      if (dl.isEmpty) const Text('Koi khuli deadline nahi.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 8),
      const Text(_check, style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Future<void> _paste(bool cause) async {
    final f = await _form(
        context,
        cause ? 'Cause list chipkaiye' : 'Case status chipkaiye',
        cause
            ? const [('text', 'eCourts app / court site se copy kiya cause list text'), ('on', 'Tareekh (agar text mein na ho)')]
            : const [('text', 'eCourts app / site ka Case Status text'), ('matter', 'Matter (agar CNR na ho)')],
        ok: 'Padho',
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
          const Text('Official raaste se', style: TextStyle(fontWeight: FontWeight.w800)),
          Text('• ${_s(off['app'])}', style: const TextStyle(fontSize: 12.5)),
          Text('• ${_s(off['sms'])}', style: const TextStyle(fontSize: 12.5)),
          const Text('Wahan se case status / cause list copy karke yahan chipkaiye; Hoola padhkar diary bharta hai.',
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
      GradientButton(label: 'Case status chipkaiye', icon: Icons.content_paste_rounded, height: 46, onTap: _busy ? null : () => _paste(false)),
      const SizedBox(height: 8),
      GradientButton(label: 'Cause list chipkaiye', icon: Icons.list_alt_rounded, height: 46, onTap: _busy ? null : () => _paste(true)),
      const SizedBox(height: 12),
      if (r != null)
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(r['say']), style: const TextStyle(fontSize: 13.5, height: 1.4)),
            for (final c in _strs(r['changes'])) Text('• $c', style: const TextStyle(fontSize: 12.5)),
            for (final x in _list(r['found']))
              Text('• ${_s(x['matter'])} item ${_s(x['item'])} (${_s(x['case'])})', style: const TextStyle(fontSize: 12.5)),
            for (final x in _list(r['not_listed']))
              Text('⚠ ${_s(x['matter'])} ${_s(x['title'])}: list mein nahi', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          ]),
        ),
    ]);
  }

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Niyam / office', const [
      ('advocate', 'Vakil ka naam'),
      ('enrolment_no', 'Bar Council enrolment no.'),
      ('office', 'Office / chamber ka naam'),
      ('address', 'Pata'),
      ('phone', 'Office mobile'),
      ('email', 'Email'),
      ('upi_id', 'UPI ID (fee note par)'),
      ('state', 'State'),
      ('place', 'Jagah (drafts par)'),
      ('closed_dates', 'Court ki chhuttiyan (YYYY-MM-DD, comma se)'),
      ('closed_weekdays', 'Band din (0=Som..6=Ravi, comma se)'),
      ('remind_days', 'Limitation yaad (din, jaise 30,15,7,3,1,0)'),
      ('morning_time', 'Subah ka note (HH:MM)'),
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
          Text(_s(st['advocate']).isEmpty ? 'Vakil ka naam daaliye' : _s(st['advocate']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Enrolment: ${_s(st['enrolment_no']).isEmpty ? '—' : _s(st['enrolment_no'])} · ${_s(st['office'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('Court band: ${_strs(st['closed_dates']).length} chhuttiyan, din ${_strs(st['closed_weekdays']).join(',')}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('HOOLA KABHI NAHI'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Aaj', 'Matters', 'Limitation', 'eCourts', 'Niyam'];
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
    final f = await _form(context, 'Matter badlo', const [
      ('title', 'Matter'),
      ('court', 'Court'),
      ('court_no', 'Court hall / judge'),
      ('case', "Case number ('RCS 123/2024')"),
      ('cnr', 'CNR'),
      ('stage', 'Stage'),
      ('next_date', 'Agli tareekh'),
      ('next_purpose', 'Agli tareekh par kya'),
      ('opposite', 'Doosra paksh'),
      ('opposite_advocate', 'Doosre paksh ke vakil'),
      ('opposite_contact', 'Unka phone / email'),
      ('acts', 'Acts / sections (vakil ke bataye)'),
      ('status', 'Status: pending / disposed / closed'),
    ], ok: 'Save', initial: {
      for (final k in ['title', 'court', 'court_no', 'cnr', 'stage', 'next_date', 'next_purpose', 'opposite', 'opposite_advocate', 'opposite_contact', 'acts', 'status'])
        k: _s(m[k]),
    });
    if (f == null) return;
    await _run('PATCH', '/api/vakil/matters/$_ref', f);
  }

  Future<void> _hearing() async {
    final f = await _form(context, 'Sunwaai ka haal', const [
      ('on', 'Kis din (DD-MM-YYYY)'),
      ('purpose', 'Kis kaam ke liye laga tha'),
      ('result', 'Kya hua'),
      ('stage', 'Ab stage'),
      ('next_date', 'Agli tareekh (court ne di)'),
      ('next_purpose', 'Agli tareekh par kya'),
    ], ok: 'Likho');
    if (f == null) return;
    await _run('POST', '/api/vakil/matters/$_ref/hearing', f);
  }

  Future<void> _event() async {
    final f = await _form(context, 'List of dates mein jodo', const [('on', 'Tareekh'), ('what', 'Kya hua')], ok: 'Jodo', big: const {'what'});
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
            ('notice_reply', 'Notice ka jawab (Lekhak)'),
            ('note', 'Brief note'),
          ])
            ListTile(title: Text(l), onTap: () => Navigator.pop(c, k)),
        ]),
      ),
    );
    if (kind == null) return;
    Map<String, String> f = {};
    if (kind == 'adjournment') {
      f = await _form(context, 'Adjournment ki wajah', const [('reason', 'Wajah (aapke shabdon mein)')], big: const {'reason'}) ?? {};
    } else if (kind == 'notice_reply' || kind == 'note' || kind == 'synopsis') {
      final r = await _form(context, 'Aapke shabd', const [('words', 'Notice mein kya hai / jawab mein kya kehna hai'), ('to', 'Kisko')],
          big: const {'words'});
      if (r == null) return;
      f = r;
    }
    await _run('POST', '/api/vakil/matters/$_ref/draft', {'kind': kind, ...f});
  }

  Future<void> _message(String to) async {
    Map<String, String>? f = {};
    if (to != 'client') {
      f = await _form(context, 'Doosre paksh ko kya bhejna hai', const [('text', 'Text (vakil sahab ka likha)'), ('phone', 'Phone'), ('email', 'Email')],
          big: const {'text'});
      if (f == null) return;
    } else {
      f = await _form(context, 'Client ko update', const [('text', 'Apna text (khaali = Hoola diary se banaye)')], big: const {'text'}, ok: 'Card banao');
      if (f == null) return;
    }
    await _run('POST', '/api/vakil/matters/$_ref/message', {'to': to, ...f});
  }

  Future<void> _filing() async {
    final f = await _form(context, 'Filing ka card', const [('what', 'Kya file karna hai'), ('note', 'Note')]);
    if (f == null || (f['what'] ?? '').isEmpty) return;
    final op = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        content: const Text('Haan ke baad Hoola ke browser mein eFiling portal khole? (login / OTP / court fee / eSign / Submit aap karengi)'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi, main khud')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, khole')),
        ],
      ),
    );
    await _run('POST', '/api/vakil/matters/$_ref/filing', {...f, 'use_operator': op == true});
  }

  Future<void> _fee(bool request) async {
    if (request) {
      final f = await _form(context, 'Fee maangna (card)', const [('amount', 'Rakam (aapki)'), ('for', 'Kis ke liye')]);
      if (f == null || _n(f['amount']) == null) return;
      await _run('POST', '/api/vakil/matters/$_ref/fee_request', {'amount': _n(f['amount']), 'for': f['for'] ?? ''});
      return;
    }
    final f = await _form(context, 'Fee ka hisaab', const [('kind', 'agreed / received / expense'), ('amount', 'Rakam'), ('note', 'Note'), ('ref_no', 'UTR / ref')]);
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
                    if (_s(m['opposite']).isNotEmpty) Text('Doosra paksh: ${_s(m['opposite'])} ${_s(m['opposite_advocate'])}', style: const TextStyle(fontSize: 12.5)),
                    Text('Stage: ${_s(m['stage']).isEmpty ? '—' : _s(m['stage'])} · Agli tareekh: ${_s(m['next_date']).isEmpty ? '—' : _s(m['next_date'])} ${_s(m['next_purpose'])}',
                        style: TextStyle(fontSize: 12.5, color: m['date_stale'] == true ? C.warn : C.ink)),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(label: 'Sunwaai ka haal', icon: Icons.event_note_rounded, onTap: _busy ? null : _hearing),
                  GlassButton(label: 'Ghatna jodo', icon: Icons.timeline_rounded, onTap: _busy ? null : _event),
                  GlassButton(label: 'Draft', icon: Icons.description_rounded, onTap: _busy ? null : _draft),
                  GlassButton(label: 'Client ko update', icon: Icons.chat_rounded, onTap: _busy ? null : () => _message('client')),
                  GlassButton(label: 'Doosre paksh ko', icon: Icons.mark_email_unread_rounded, onTap: _busy ? null : () => _message('opposite')),
                  GlassButton(label: 'Filing', icon: Icons.upload_file_rounded, onTap: _busy ? null : _filing),
                  GlassButton(label: 'Fee maango', icon: Icons.request_quote_rounded, onTap: _busy ? null : () => _fee(true)),
                  GlassButton(label: 'Fee hisaab', icon: Icons.account_balance_wallet_rounded, onTap: _busy ? null : () => _fee(false)),
                ]),
                const SizedBox(height: 12),
                for (final c in _list(m['cards']).where((c) => _s(c['status']) == 'waiting' || _s(c['status']) == 'approved'))
                  Padding(padding: const EdgeInsets.only(bottom: 8), child: VakilCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
                const Caption('SUNWAIYAN'),
                for (final h in _list(m['hearings']).reversed.take(20))
                  Text('• ${_s(h['on'])}: ${_s(h['result']).isEmpty ? _s(h['purpose']) : _s(h['result'])}${_s(h['next']).isEmpty ? '' : ' → ${_s(h['next'])}'}',
                      style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
                const Caption('LIST OF DATES & EVENTS'),
                for (final e in _list(m['events'])) Text('• ${_s(e['on'])}: ${_s(e['what'])}', style: const TextStyle(fontSize: 12.5)),
                const SizedBox(height: 10),
                const Caption('KAAGAZ (tap = have / na / missing)'),
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
                  return Text('Tay ${_s(t['agreed'])} · maangi ${_s(t['requested'])} · mili ${_s(t['received'])} · kharcha ${_s(t['expense'])} · baaki ${_s(f['due_text'])}',
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
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Fee ki haan' : _s(show['title']),
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
      f = await _form(context, 'File ho gaya', const [('ref_no', 'eFiling number')]) ?? {};
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
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'stale' => 'purana', 'rejected' => 'nahi', _ => st }, fg: _stColor(st)),
        ]),
        if (kind == 'message') ...[
          Text('Kisko: ${_s(b['name'])} ${_s(b['phone']).isEmpty ? '' : '· ${_s(b['phone'])}'} ${_s(b['email'])}',
              style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text(_s(b['text']), style: const TextStyle(fontSize: 13)),
        ],
        if (kind == 'filing') ...[
          Text('${_s(b['what'])} · ${_s(b['court'])} · ${_s(b['case'])}', style: const TextStyle(fontSize: 12.5)),
          for (final d in _list(b['deadlines'])) Text('⏱ ${_s(d['label'])}: ${_s(d['last_date'])} (andaaza)', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_strs(b['missing_docs']).isNotEmpty)
            Text('Kaagaz baaki: ${_strs(b['missing_docs']).take(5).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (b['use_operator'] == true)
            const Text('Haan ke baad Hoola ka browser portal kholega; login / OTP / fee / eSign / Submit aap.', style: TextStyle(fontSize: 12, color: C.muted)),
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
                    label: switch (kind) { 'filing' => 'Haan, filing shuru', 'fee' => 'Haan, fee note banao', _ => 'Haan, links do' },
                    height: 42,
                    onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved' && kind != 'fee')
          Row(children: [
            Expanded(child: GlassButton(label: 'Links / steps', icon: Icons.open_in_new_rounded, onTap: () => _openLinks(context, _m(c['result'])))),
            const SizedBox(width: 8),
            GlassButton(label: kind == 'filing' ? 'File ho gaya' : 'Bhej diya', icon: Icons.check_rounded, onTap: _busy ? null : _done),
          ]),
        if (st == 'approved' && kind == 'fee')
          GlassButton(label: 'Message / UPI link', icon: Icons.open_in_new_rounded, onTap: () => _openLinks(context, _m(c['result']))),
        if (st == 'stale') const Text('Card banne ke baad details badli: naya card banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        const Text('Hoola khud kuch nahi bhejta, file nahi karta, paise nahi leta.', style: TextStyle(fontSize: 11, color: C.faint)),
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
          if (blanks > 0) Text('$blanks jagah khaali: bhariye', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_s(d['text']).isNotEmpty)
            Text(_s(d['text']).length > 400 ? '${_s(d['text']).substring(0, 400)}…' : _s(d['text']), style: const TextStyle(fontSize: 12)),
          if (_s(data['matter']).isNotEmpty)
            TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VakilMatterPage(app: app, matterRef: _s(data['matter'])))),
                child: const Text('Matter kholo')),
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
