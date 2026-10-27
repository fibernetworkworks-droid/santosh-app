/// Profile > IT Helpdesk Sahayak: Hoola as the office's IT helpdesk.
/// Aaj (open tickets, her Haan cards, CERT-In clocks, warranty / AMC) · Tickets (step by step, log, technician) ·
/// Devices (asset register + vendors) · Suraksha (suspicious mail / SMS check, incidents) · Niyam (office, SLA, morning note).
/// A step that changes a system setting / installs / resets runs only after HER tap on the card. Hoola never asks for a password.
library;

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

Color _prioColor(String p) => switch (p) { 'P1' => C.bad, 'P2' => C.warn, 'P3' => C.accentSoft, _ => C.chip };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {String ok = 'Aage'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields) TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'text' ? 4 : 1),
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

class HelpdeskScreen extends StatefulWidget {
  const HelpdeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HelpdeskScreen> createState() => _HelpdeskScreenState();
}

class _HelpdeskScreenState extends State<HelpdeskScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  bool _openOnly = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/helpdesk'));
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

  void _openTicket(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => HelpdeskTicketPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newTicket() async {
    final f = await _form(context, 'Nayi IT dikkat', const [
      ('text', 'Kya dikkat hai (apne shabdon mein)'),
      ('person', 'Kisko (naam)'),
      ('asset', 'Kaun sa device (tag / naam, ho to)'),
      ('error', 'Screen par error (jaisa likha hai)'),
      ('since', 'Kab se'),
    ], ok: 'Darj karo');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/helpdesk/tickets', f);
    final t = _m(r?['ticket']);
    if (t['id'] != null && mounted) _openTicket(_s(t['id']));
  }

  Widget _ticketTile(Map<String, dynamic> t) {
    final cur = _m(t['current']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _openTicket(_s(t['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: t['late'] == true ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Pill(_s(t['priority']), fg: _prioColor(_s(t['priority']))),
              const SizedBox(width: 6),
              Expanded(child: Text('${_s(t['number'])} · ${_s(t['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(t['status_label'])),
            ]),
            const SizedBox(height: 4),
            Text(_s(t['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
            Text(
                [
                  if (_s(t['person']).isNotEmpty) _s(t['person']),
                  if (t['asset'] is Map) _s(_m(t['asset'])['name']),
                  if (_s(t['raised_by']).isNotEmpty) 'darj: ${_s(t['raised_by'])}',
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12)),
            if (cur.isNotEmpty) Text('Abhi: ${_s(cur['title'])}', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
            if (t['late'] == true) const Text('Samay nikal gaya', style: TextStyle(fontSize: 12, color: C.bad)),
          ]),
        ),
      ),
    );
  }

  Widget _today() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      for (final c in _list(d['waiting_haan']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: HelpdeskChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      for (final i in _list(d['incidents']).where((i) => _s(i['report_due']).isNotEmpty && _s(i['reported_at']).isEmpty))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: _IncidentTile(app: widget.app, i: i, onDone: _load)),
      if (_list(d['open']).isNotEmpty) Text('Khule ticket', style: display(15)),
      const SizedBox(height: 6),
      for (final t in _list(d['open'])) _ticketTile(t),
      for (final e in _list(d['expiring']))
        Text('• ${_s(e['name'])}: ${_s(e['what'])} ${e['days']} din mein khatam (${_s(e['on'])})', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      for (final r in _list(d['repeat']))
        Text('• ${_s(r['name'])}: 90 din mein ${r['count_90d']} baar kharab (${_s(r['top_label'])})', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      for (final w in _list(d['old_windows']))
        Text('• ${_s(w['name'])}: ${_s(w['os'])} (purana Windows)', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  Widget _tickets() {
    final all = _list(_d?['tickets']);
    final shown = _openOnly ? all.where((t) => const ['new', 'working', 'waiting_haan', 'waiting_tech'].contains(t['status'])).toList() : all;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: GradientButton(label: 'Nayi dikkat', icon: Icons.add_rounded, height: 48, onTap: _busy ? null : _newTicket)),
        const SizedBox(width: 8),
        FilterChip(label: const Text('Sirf khule'), selected: _openOnly, onSelected: (v) => setState(() => _openOnly = v)),
      ]),
      const SizedBox(height: 10),
      if (shown.isEmpty) const Text('Koi ticket nahi.', style: TextStyle(color: C.muted)),
      for (final t in shown) _ticketTile(t),
      if (_list(_d?['known']).isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Is office mein kya kaam aaya', style: display(14)),
        for (final k in _list(_d?['known']).take(8))
          Text('• ${_s(k['label'])}: ${_s(k['title'])} (${k['fixed']}/${k['tried']})', style: const TextStyle(fontSize: 12.5, color: C.muted)),
      ],
    ]);
  }

  Future<void> _addAsset([Map<String, dynamic>? a]) async {
    final f = await _form(context, a == null ? 'Naya device' : _s(a['name']), [
      if (a == null) ('name', 'Naam (Accounts PC / Reception printer)'),
      if (a == null) ('kind', 'Kism: pc / laptop / printer / router / ups / cctv / projector / scanner / server'),
      ('brand', 'Brand'),
      ('model', 'Model'),
      ('serial', 'Serial no'),
      ('user', 'Kaun chalata hai'),
      ('os', 'Windows version (PC ho to)'),
      ('bought', 'Kab liya (dd-mm-yyyy)'),
      ('warranty_until', 'Warranty kab tak'),
      ('amc_until', 'AMC kab tak'),
      ('vendor', 'Vendor (list mein jo hai)'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    if (a == null) {
      await _run('POST', '/api/helpdesk/assets', f);
    } else {
      await _run('PATCH', '/api/helpdesk/assets/${_s(a['id'])}', f);
    }
  }

  Future<void> _addVendor() async {
    final f = await _form(context, 'Vendor / technician', const [
      ('name', 'Naam'),
      ('kind', 'Kism: amc / it / isp / printer / cctv / tally_partner / electrician / software'),
      ('phone', 'Phone (10 ank)'),
      ('email', 'Email'),
      ('amc_until', 'AMC kab tak'),
      ('sla_hours', 'Kitne ghante mein aane ka vaada'),
    ], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/helpdesk/vendors', {...f, if (f['sla_hours'] != null) 'sla_hours': double.tryParse(f['sla_hours']!) ?? 0});
  }

  Widget _devices() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Naya device', icon: Icons.devices_other_rounded, onTap: _busy ? null : () => _addAsset()),
          GlassButton(label: 'Mere PC jodo', icon: Icons.computer_rounded, onTap: _busy ? null : () => _run('POST', '/api/helpdesk/assets/sync_pcs')),
          GlassButton(label: 'Vendor', icon: Icons.engineering_rounded, onTap: _busy ? null : _addVendor),
        ]),
        const SizedBox(height: 10),
        for (final a in _list(_d?['assets']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _addAsset(a),
              child: Glass(
                padding: const EdgeInsets.all(12),
                border: _m(a['repeat']).isNotEmpty ? C.warn : null,
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(a['tag'])} · ${_s(a['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text(
                      [
                        _s(a['kind']),
                        if (_s(a['brand']).isNotEmpty) '${_s(a['brand'])} ${_s(a['model'])}'.trim(),
                        if (_s(a['user']).isNotEmpty) _s(a['user']),
                        if (_s(a['warranty_until']).isNotEmpty) 'warranty ${_s(a['warranty_until'])}',
                        if (_s(a['amc_until']).isNotEmpty) 'AMC ${_s(a['amc_until'])}',
                        if (_s(a['vendor']).isNotEmpty) _s(a['vendor']),
                      ].join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  for (final x in ((a['advice'] as List?) ?? const [])) Text('• $x', style: const TextStyle(fontSize: 12, color: C.warn)),
                ]),
              ),
            ),
          ),
        if (_list(_d?['vendors']).isNotEmpty) Text('Vendors', style: display(14)),
        for (final v in _list(_d?['vendors']))
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: Text('${_s(v['name'])} · ${_s(v['kind_label'])}'),
            subtitle: Text([_s(v['phone']), _s(v['email']), if (_s(v['amc_until']).isNotEmpty) 'AMC ${_s(v['amc_until'])}'].where((x) => x.isNotEmpty).join(' · ')),
            trailing: _s(v['phone']).isEmpty ? null : IconButton(icon: const Icon(Icons.call_rounded), onPressed: () => Native.openExternal(url: 'tel:+91${_s(v['phone'])}')),
          ),
      ]);

  Future<void> _phish() async {
    final text = TextEditingController();
    final sender = TextEditingController();
    final did = <String, bool>{'clicked': false, 'entered_password': false, 'opened_attachment': false, 'money': false, 'gave_otp': false, 'remote_access': false, 'personal_data': false};
    const labels = {
      'clicked': 'Link par click kiya',
      'entered_password': 'Password bhar diya',
      'opened_attachment': 'Attachment khola',
      'money': 'Paise gaye',
      'gave_otp': 'OTP bataya',
      'remote_access': 'AnyDesk / remote diya',
      'personal_data': 'Graahakon ka data gaya ho sakta hai',
    };
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('Shak wala mail / SMS'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Text copy karke yahan daaliye. Link mat kholiye; Hoola bhi nahi kholta.', style: TextStyle(fontSize: 12, color: C.muted)),
              TextField(controller: sender, decoration: const InputDecoration(labelText: 'Bhejne wala (email / number)')),
              TextField(controller: text, maxLines: 5, decoration: const InputDecoration(labelText: 'Mail / message ka text')),
              const SizedBox(height: 6),
              for (final e in labels.entries)
                CheckboxListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: did[e.key],
                  title: Text(e.value, style: const TextStyle(fontSize: 13)),
                  onChanged: (v) => set(() => did[e.key] = v ?? false),
                ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Jaancho')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    final r = await _run('POST', '/api/helpdesk/phish', {'text': text.text, 'sender': sender.text, ...did});
    if (r != null && mounted) {
      await showDialog<void>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Jaanch'),
          content: SingleChildScrollView(child: HelpdeskAlertCard(app: widget.app, data: {'kind': 'security', ...r, 'incident': r['incident']})),
          actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))],
        ),
      );
    }
  }

  Widget _security() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GradientButton(label: 'Shak wala mail / SMS jaancho', icon: Icons.shield_rounded, onTap: _busy ? null : _phish),
        const SizedBox(height: 8),
        const Text(
            'Paise gaye hon to turant 1930. Business ke computer par phishing se ghusna / virus / data leak = 6 ghante mein CERT-In ko report (incident@cert-in.org.in, 1800-11-4949).',
            style: TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 10),
        for (final i in _list(_d?['incidents'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: _IncidentTile(app: widget.app, i: i, onDone: _load)),
      ]);

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Office ki jaankari', [
      ('office_name', 'Office ka naam (${_s(st['office_name'])})'),
      ('entity', 'Roop: company / llp / partnership / proprietor / trust / society / govt / individual (${_s(st['entity'])})'),
      ('contact_name', 'Sampark vyakti'),
      ('contact_phone', 'Phone'),
      ('contact_email', 'Email'),
      ('it_person', 'Admin password kiske paas (naam)'),
      ('morning_time', 'Subah ka IT note (HH:MM, abhi ${_s(st['morning_time'])})'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    await _run('PUT', '/api/helpdesk/settings', f);
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    final sla = _m(st['sla']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['office_name']).isEmpty ? 'Office ka naam nahi diya' : _s(st['office_name']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Roop: ${_s(st['entity_label'])} · subah ka note ${_s(st['morning_time'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(st['it_person']).isNotEmpty) Text('Admin: ${_s(st['it_person'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      ),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _busy ? null : _settings),
        GlassButton(label: 'IT register Excel', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run('POST', '/api/helpdesk/register')),
      ]),
      const SizedBox(height: 10),
      Text('Jawab / theek karne ka samay', style: display(14)),
      for (final p in const ['P1', 'P2', 'P3', 'P4'])
        Text('$p: jawab ${_m(sla[p])['respond_h']} ghante, theek ${_m(sla[p])['resolve_h']} ghante', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 10),
      Text('Playbooks', style: display(14)),
      for (final p in _list(_d?['playbooks'])) Text('• ${_s(p['label'])} (${p['steps']} step, aage: ${_s(p['escalate'])})', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('IT Helpdesk Sahayak')),
        floatingActionButton: _tab <= 1 ? FloatingActionButton.extended(onPressed: _busy ? null : _newTicket, icon: const Icon(Icons.support_agent_rounded), label: const Text('Dikkat batao')) : null,
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Tickets'), (2, 'Devices'), (3, 'Suraksha'), (4, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _tickets(), _devices(), _security(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Hoola step-by-step batata hai; system ki setting badalna / install / reset sirf aapki haan ke baad. Password / OTP kabhi mat batayiye. Technician ko message aap bhejti hain; paisa Hoola nahi deta.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class _IncidentTile extends StatelessWidget {
  const _IncidentTile({required this.app, required this.i, this.onDone});
  final Santosh app;
  final Map<String, dynamic> i;
  final VoidCallback? onDone;

  @override
  Widget build(BuildContext context) {
    final due = _s(i['report_due']).isNotEmpty && _s(i['reported_at']).isEmpty;
    final an = _m(i['analysis']);
    return Glass(
      padding: const EdgeInsets.all(12),
      border: due ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.gpp_maybe_rounded, color: C.warn),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(i['kind_label'])}${_s(i['sender']).isNotEmpty ? ' · ${_s(i['sender'])}' : ''}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(i['status'])),
        ]),
        if (_s(an['say']).isNotEmpty) Text(_s(an['say']), style: const TextStyle(fontSize: 12.5)),
        Text('Mila: ${_s(i['detected_local'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (due) Text('CERT-In report ${_s(i['report_due_local'])} tak (${i['hours_left'] ?? ''} ghante)', style: const TextStyle(color: C.bad, fontSize: 12.5)),
        if (_s(i['reported_at']).isNotEmpty) Text('Report bheja${_s(i['reported_ref']).isNotEmpty ? ' (${_s(i['reported_ref'])})' : ''}', style: const TextStyle(color: C.ok, fontSize: 12.5)),
        if (due)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GlassButton(
                label: 'Maine CERT-In ko bhej diya',
                icon: Icons.mark_email_read_rounded,
                height: 40,
                onTap: () async {
                  final f = await _form(context, 'CERT-In report', const [('ref', 'Ticket / reference (ho to)')], ok: 'Ho gaya');
                  if (f == null || !context.mounted) return;
                  await _call(context, app, 'POST', '/api/helpdesk/incidents/${_s(i['id'])}/reported', f);
                  onDone?.call();
                }),
          ),
      ]),
    );
  }
}

/// One ticket: current step with Theek hua / Nahi hua, her Haan card, technician, log.
class HelpdeskTicketPage extends StatefulWidget {
  const HelpdeskTicketPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<HelpdeskTicketPage> createState() => _HelpdeskTicketPageState();
}

class _HelpdeskTicketPageState extends State<HelpdeskTicketPage> {
  Map<String, dynamic>? _t;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = _m(await widget.app.api!.call('GET', '/api/helpdesk/tickets/${widget.id}'));
      if (mounted) setState(() => _t = t);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/helpdesk/tickets/${widget.id}/$action', body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    final cur = _m(t?['current']);
    final ch = _m(t?['change']);
    final esc = _m(t?['escalation']);
    final open = t != null && const ['new', 'working', 'waiting_haan', 'waiting_tech'].contains(t['status']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(t?['number']).isEmpty ? 'Ticket' : _s(t?['number']))),
      body: Aurora(
        child: t == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Pill(_s(t['priority']), fg: _prioColor(_s(t['priority']))),
                        const SizedBox(width: 6),
                        Expanded(child: Text(_s(t['label']), style: const TextStyle(fontWeight: FontWeight.w800))),
                        Pill(_s(t['status_label'])),
                      ]),
                      const SizedBox(height: 6),
                      Text(_s(t['title']), style: const TextStyle(fontSize: 13.5)),
                      Text(
                          [
                            if (_s(t['person']).isNotEmpty) _s(t['person']),
                            if (t['asset'] is Map) '${_s(_m(t['asset'])['tag'])} ${_s(_m(t['asset'])['name'])}',
                            'darj: ${_s(t['raised_by'])}',
                          ].join(' · '),
                          style: const TextStyle(color: C.muted, fontSize: 12)),
                      for (final e in _m(t['details']).entries.where((e) => e.value is String && _s(e.value).isNotEmpty))
                        Text('${e.key}: ${e.value}', style: const TextStyle(fontSize: 12)),
                      if (_s(t['parent_number']).isNotEmpty) Text('Wahi dikkat: ${_s(t['parent_number'])} ke saath', style: const TextStyle(fontSize: 12, color: C.warn)),
                      if (((t['children'] as List?) ?? const []).isNotEmpty) Text('Saath jude: ${(t['children'] as List).join(', ')}', style: const TextStyle(fontSize: 12, color: C.warn)),
                      if (t['late'] == true) const Text('Theek karne ka samay nikal gaya', style: TextStyle(fontSize: 12, color: C.bad)),
                      if (_s(t['resolution']).isNotEmpty) Text('Hal: ${_s(t['resolution'])}', style: const TextStyle(fontSize: 12.5, color: C.ok)),
                    ]),
                  ),
                  const SizedBox(height: 10),
                  if (ch.isNotEmpty && ch['status'] == 'waiting') HelpdeskChangeCard(app: widget.app, data: {'change': ch}, onDone: _load),
                  if (open && cur.isNotEmpty && !(ch.isNotEmpty && ch['status'] == 'waiting'))
                    Glass(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Step ${t['step_no']}/${t['total']}: ${_s(cur['title'])}', style: display(15)),
                        const SizedBox(height: 6),
                        Text(_s(cur['how']), style: const TextStyle(fontSize: 13.5, height: 1.35)),
                        if (_s(cur['check']).isNotEmpty) Text('Dekhiye: ${_s(cur['check'])}', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
                        if (_s(cur['learned']).isNotEmpty) Text(_s(cur['learned']), style: const TextStyle(fontSize: 12, color: C.ok)),
                        const SizedBox(height: 10),
                        Wrap(spacing: 8, runSpacing: 8, children: [
                          GradientButton(label: 'Theek hua', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _act('step', {'result': 'fixed'})),
                          GlassButton(label: 'Nahi hua', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _act('step', {'result': 'not_fixed'})),
                          GlassButton(label: 'Chhodo', height: 44, onTap: _busy ? null : () => _act('step', {'result': 'skipped'})),
                        ]),
                      ]),
                    ),
                  const SizedBox(height: 10),
                  if (open)
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      GlassButton(label: 'Technician ko bhejo', icon: Icons.engineering_rounded, onTap: _busy ? null : () => _act('escalate')),
                      GlassButton(
                          label: 'Technician ne kiya',
                          icon: Icons.build_circle_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Technician', const [('note', 'Kya kiya'), ('cost', 'Kharcha (ho to)')], ok: 'Theek ho gaya');
                                  if (f != null) await _act('tech', {'note': f['note'] ?? '', 'fixed': true, if (f['cost'] != null) 'cost': double.tryParse(f['cost']!)});
                                }),
                      GlassButton(
                          label: 'Detail jodo',
                          icon: Icons.note_add_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Detail', const [('error', 'Error ka text'), ('since', 'Kab se'), ('location', 'Kahan'), ('tried', 'Kya try kiya')]);
                                  if (f == null || f.isEmpty) return;
                                  setState(() => _busy = true);
                                  await _call(context, widget.app, 'PATCH', '/api/helpdesk/tickets/${widget.id}', f);
                                  await _load();
                                  if (mounted) setState(() => _busy = false);
                                }),
                      GlassButton(label: 'Theek ho gaya', icon: Icons.done_all_rounded, onTap: _busy ? null : () => _act('resolve')),
                    ])
                  else
                    Wrap(spacing: 8, children: [
                      GlassButton(label: 'Dobara kholo', icon: Icons.replay_rounded, onTap: _busy ? null : () => _act('status', {'status': 'reopen'})),
                      if (t['status'] == 'resolved') GlassButton(label: 'Band karo', onTap: _busy ? null : () => _act('status', {'status': 'closed'})),
                    ]),
                  if (esc.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    HelpdeskEscalateCard(app: widget.app, data: {'escalation': esc, 'number': t['number']}),
                  ],
                  const SizedBox(height: 12),
                  if (((t['escalate_when'] as List?) ?? const []).isNotEmpty) ...[
                    Text('Technician kab', style: display(14)),
                    for (final x in (t['escalate_when'] as List)) Text('• $x', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                  ],
                  const SizedBox(height: 10),
                  Text('Steps', style: display(14)),
                  for (final st in _list(t['steps']))
                    Text(
                        '${st['result'] == 'fixed' ? '✓' : st['result'] == null ? '○' : '✗'} ${_s(st['title'])}${_s(st['change']).isNotEmpty ? ' (aapki haan)' : ''}${_s(st['note']).isNotEmpty ? ' - ${_s(st['note'])}' : ''}',
                        style: TextStyle(fontSize: 12.5, color: st['result'] == null ? C.ink : C.muted)),
                  const SizedBox(height: 10),
                  Text('Log', style: display(14)),
                  for (final l in _list(t['log']).reversed)
                    Text('${_s(l['at']).length >= 16 ? _s(l['at']).substring(5, 16).replaceAll('T', ' ') : ''} · ${_s(l['by'])}: ${_s(l['what'])}',
                        style: const TextStyle(fontSize: 11.5, color: C.faint)),
                ]),
              ),
      ),
    );
  }
}

/// Chat / call card for `helpdesk_ticket`: the step to do now with Theek hua / Nahi hua.
class HelpdeskTicketCard extends StatefulWidget {
  const HelpdeskTicketCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<HelpdeskTicketCard> createState() => _HelpdeskTicketCardState();
}

class _HelpdeskTicketCardState extends State<HelpdeskTicketCard> {
  bool _busy = false;
  String _done = '';

  Future<void> _step(String result) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/helpdesk/tickets/${_s(widget.data['ticket'])}/step', {'result': result});
    if (mounted) setState(() {
      _busy = false;
      if (r != null) _done = result == 'fixed' ? 'Theek ho gaya' : 'Agla step chat mein';
    });
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final cur = _m(d['current']);
    final ch = _m(d['change']);
    final open = const ['new', 'working', 'waiting_tech'].contains(d['status']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HelpdeskTicketPage(app: widget.app, id: _s(d['ticket'])))),
      child: Glass(
        border: d['late'] == true ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.support_agent_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(d['number'])} · ${_s(d['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(d['priority']), fg: _prioColor(_s(d['priority']))),
          ]),
          Text(_s(d['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text(_s(d['status_label']), style: const TextStyle(fontSize: 12, color: C.chip)),
          if (cur.isNotEmpty && open) ...[
            const SizedBox(height: 6),
            Text('Step ${d['step_no']}/${d['total']}: ${_s(cur['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(_s(cur['how']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
          ],
          if (ch.isNotEmpty && ch['status'] == 'waiting') Text('Aapki haan ka card: ${_s(ch['number'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (_done.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 6), child: Text(_done, style: const TextStyle(color: C.ok, fontSize: 12.5)))
          else if (cur.isNotEmpty && open && !(ch.isNotEmpty && ch['status'] == 'waiting'))
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Wrap(spacing: 8, runSpacing: 6, children: [
                GlassButton(label: 'Theek hua', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () => _step('fixed')),
                GlassButton(label: 'Nahi hua', icon: Icons.close_rounded, height: 40, onTap: _busy ? null : () => _step('not_fixed')),
              ]),
            ),
        ]),
      ),
    );
  }
}

/// `helpdesk_change`: a system setting change / install / reset waiting for HER tap. Only this tap approves it.
class HelpdeskChangeCard extends StatefulWidget {
  const HelpdeskChangeCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<HelpdeskChangeCard> createState() => _HelpdeskChangeCardState();
}

class _HelpdeskChangeCardState extends State<HelpdeskChangeCard> {
  bool _busy = false;
  late String _status = _s(_m(widget.data['change'])['status']);

  Future<void> _decide(bool yes) async {
    final c = _m(widget.data['change']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyun nahi? (zaroori nahi)', const [('reason', 'Wajah')], ok: 'Mana karo');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/helpdesk/changes/${_s(c['id'])}/decide', {'yes': yes, 'hash': _s(c['hash']), 'reason': reason});
    if (mounted) setState(() {
      _busy = false;
      if (r != null) _status = _s(_m(r['change'])['status']);
    });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final c = _m(widget.data['change']);
    final careful = c['careful'] == true;
    return Glass(
      border: _status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(careful ? Icons.warning_amber_rounded : Icons.settings_suggest_rounded, color: careful ? C.bad : C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Aapki haan chahiye · ${_s(c['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(c['kind_label'])),
        ]),
        const SizedBox(height: 6),
        Text(_s(c['what']), style: const TextStyle(fontWeight: FontWeight.w700)),
        Text('Kahan: ${_s(c['where'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        const SizedBox(height: 4),
        Text(_s(c['how']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
        if (_s(c['risk']).isNotEmpty) Text('Dhyaan: ${_s(c['risk'])}', style: TextStyle(fontSize: 12, color: careful ? C.bad : C.warn)),
        if (_s(c['undo']).isNotEmpty) Text('Wapas: ${_s(c['undo'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (c['admin'] == true) const Text('Admin wale account se hoga.', style: TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (_status == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, karo', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else
          Text(
              switch (_status) {
                'approved' => 'Haan di: ab step karke batayiye theek hua ya nahi.',
                'rejected' => 'Mana kiya.',
                'done' => 'Ho gaya.',
                'failed' => 'Kiya, par theek nahi hua.',
                _ => _status,
              },
              style: TextStyle(color: _status == 'rejected' ? C.muted : C.ok, fontSize: 12.5)),
      ]),
    );
  }
}

/// `helpdesk_escalate`: what to tell the technician + WhatsApp / call / email drafts she sends herself.
class HelpdeskEscalateCard extends StatelessWidget {
  const HelpdeskEscalateCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final e = _m(data['escalation']);
    final v = _m(e['vendor']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.engineering_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(data['number'])} technician ke liye${v.isNotEmpty ? ' · ${_s(v['name'])}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        SelectableText(_s(e['text']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        for (final n in ((e['notes'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (_s(e['wa_link']).isNotEmpty) GlassButton(label: 'WhatsApp', icon: Icons.send_rounded, height: 40, onTap: () => Native.openExternal(url: _s(e['wa_link']))),
          if (_s(e['tel']).isNotEmpty) GlassButton(label: 'Call', icon: Icons.call_rounded, height: 40, onTap: () => Native.openExternal(url: _s(e['tel']))),
          if (_s(e['mailto']).isNotEmpty) GlassButton(label: 'Email', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: _s(e['mailto']))),
          GlassButton(
              label: 'Copy',
              icon: Icons.copy_rounded,
              height: 40,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _s(e['text'])));
                _snack(context, 'Copy ho gaya');
              }),
          for (final l in _list(e['links'])) GlassButton(label: _s(l['label']), icon: Icons.map_rounded, height: 40, onTap: () => Native.openExternal(url: _s(l['url']))),
        ]),
      ]),
    );
  }
}

/// `helpdesk_alert`: security check result (red flags, what to do, CERT-In draft) or an SLA / CERT-In reminder.
class HelpdeskAlertCard extends StatelessWidget {
  const HelpdeskAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final inc = _m(data['incident']);
    final an = _m(inc['analysis']);
    final draft = _s(data['cert_in_draft']);
    final security = data['kind'] == 'security';
    return Glass(
      border: security ? C.warn : C.bad,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(security ? Icons.gpp_maybe_rounded : Icons.alarm_rounded, color: security ? C.warn : C.bad),
          const SizedBox(width: 8),
          Expanded(
              child: Text(security ? 'Suraksha jaanch${_s(data['number']).isNotEmpty ? ' · ${_s(data['number'])}' : ''}' : 'IT yaad dilana',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        for (final f in _list(an['flags']))
          Text('• ${_s(f['text'])}', style: TextStyle(fontSize: 12, color: f['level'] == 'bad' ? C.bad : C.warn)),
        for (final a in ((data['actions'] as List?) ?? const [])) Text('→ $a', style: const TextStyle(fontSize: 12.5)),
        if (draft.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 6, children: [
            GlassButton(
                label: 'CERT-In draft copy',
                icon: Icons.copy_rounded,
                height: 40,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: draft));
                  _snack(context, 'Draft copy ho gaya: apne email se bhejiye');
                }),
            GlassButton(label: '1930 call', icon: Icons.call_rounded, height: 40, onTap: () => Native.openExternal(url: 'tel:1930')),
          ]),
        ],
      ]),
    );
  }
}

/// `helpdesk_day`: the morning IT note.
class HelpdeskDayCard extends StatelessWidget {
  const HelpdeskDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HelpdeskScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.computer_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['say']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
          ]),
        ),
      );
}
