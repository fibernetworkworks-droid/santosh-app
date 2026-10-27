/// Profile > NOC Sahayak (ISP network): Hoola as the FTTH ISP's network engineer.
/// Aaj (open faults with the real cause in plain words, late tickets, changes waiting for HER haan) · Alarm (paste OLT log /
/// syslog / NMS CSV or pick a file) · Tickets · Network (OLTs, splitters, customer ONT sheet) · Badlav (changes on live
/// equipment: exact commands + rollback, only her tap approves) · Niyam (ISP, teams, SLA hours, BSNL SLA, collector, sources).
/// Hoola never logs in to her equipment and never asks for a device password.
library;

import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
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

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String>? initial, Set<String> multi = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial?[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: multi.contains(k) ? 5 : 1),
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

Color _confColor(dynamic c) {
  final v = (c is num) ? c.toDouble() : 0.0;
  return v >= 0.8 ? C.bad : (v >= 0.55 ? C.warn : C.chip);
}

IconData _faultIcon(String kind) => switch (kind) {
      'olt_down' => Icons.dns_rounded,
      'uplink' || 'uplink_flap' => Icons.swap_vert_rounded,
      'area_power' || 'customer_power' => Icons.power_off_rounded,
      'feeder_cut' || 'splitter_branch' || 'drop_fibre' => Icons.content_cut_rounded,
      'rx_bad' || 'rx_high' || 'pon_degrade' => Icons.light_mode_rounded,
      'storm' => Icons.all_inclusive_rounded,
      'bng' => Icons.lock_rounded,
      _ => Icons.router_rounded,
    };

Future<void> _open(BuildContext context, String url) async {
  if (url.isEmpty) return;
  final r = await Native.openExternal(url: url);
  if (context.mounted && r.isNotEmpty && r != 'ok') _snack(context, r);
}

/// Ticket sheet: team chips + who + ETA + note -> POST /faults/{id}/ticket.
Future<Map<String, dynamic>?> _ticketSheet(BuildContext context, Santosh app, Map<String, dynamic> f) async {
  String team = _s(f['team']);
  final who = TextEditingController();
  final phone = TextEditingController();
  final eta = TextEditingController();
  final note = TextEditingController();
  final extRef = TextEditingController();
  const teams = [
    ('field_fibre', 'Field fibre'),
    ('noc', 'NOC'),
    ('bsnl', 'BSNL'),
    ('upstream', 'Upstream'),
    ('customer', 'Customer'),
    ('electricity', 'Bijli'),
    ('vendor', 'OLT vendor'),
  ];
  final ok = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, set) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Ticket: ${_s(f['number'])} ${_s(f['title'])}', style: display(15)),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final (k, l) in teams) ChoiceChip(label: Text(l), selected: team == k, onSelected: (_) => set(() => team = k)),
            ]),
            TextField(controller: who, decoration: const InputDecoration(labelText: 'Kisko (khaali = team ka pehla aadmi)')),
            TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Mobile (ho to)')),
            TextField(controller: eta, decoration: const InputDecoration(labelText: 'ETA: "2 ghante", "shaam 6 baje" (pata ho to)')),
            if (team == 'bsnl' || team == 'upstream')
              TextField(controller: extRef, decoration: const InputDecoration(labelText: 'Docket / complaint number (ho to)')),
            TextField(controller: note, decoration: const InputDecoration(labelText: 'Note')),
            const SizedBox(height: 12),
            GradientButton(label: 'Ticket banao', icon: Icons.assignment_rounded, height: 48, onTap: () => Navigator.pop(ctx, true)),
          ]),
        ),
      ),
    ),
  );
  if (ok != true || !context.mounted) return null;
  return _call(context, app, 'POST', '/api/ispnoc/faults/${_s(f['id'])}/ticket', {
    'team': team,
    if (who.text.trim().isNotEmpty) 'assignee': who.text.trim(),
    if (phone.text.trim().isNotEmpty) 'phone': phone.text.trim(),
    if (eta.text.trim().isNotEmpty) 'eta': eta.text.trim(),
    if (note.text.trim().isNotEmpty) 'note': note.text.trim(),
    if (extRef.text.trim().isNotEmpty) 'ext_ref': extRef.text.trim(),
  });
}

Future<void> _customerMessage(BuildContext context, Santosh app, Map<String, dynamic> f) async {
  final r = await _call(context, app, 'GET', '/api/ispnoc/faults/${_s(f['id'])}/message');
  if (r == null || !context.mounted) return;
  final text = _s(r['text']);
  if (text.isEmpty) return;
  final phones = _strs(r['phones']);
  await showDialog<void>(
    context: context,
    builder: (d) => AlertDialog(
      title: const Text('Customers ke liye message'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          SelectableText(text),
          const SizedBox(height: 8),
          if (_strs(r['blanks']).isNotEmpty)
            Text('Bharna baaki: ${_strs(r['blanks']).join(', ')}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
          Text('${phones.length} customer ke number. Aap apne WhatsApp / SMS / broadcast se bhejiye; Hoola khud nahi bhejta.',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      ),
      actions: [
        TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: text));
              Navigator.pop(d);
            },
            child: const Text('Message copy')),
        if (phones.isNotEmpty)
          TextButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: phones.join(', ')));
                Navigator.pop(d);
              },
              child: const Text('Numbers copy')),
        TextButton(
            onPressed: () {
              Navigator.pop(d);
              _open(context, _s(r['wa_link']));
            },
            child: const Text('WhatsApp')),
      ],
    ),
  );
}

class IspnocScreen extends StatefulWidget {
  const IspnocScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<IspnocScreen> createState() => _IspnocScreenState();
}

class _IspnocScreenState extends State<IspnocScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  final _alarm = TextEditingController();
  final _olt = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _alarm.dispose();
    _olt.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/ispnoc'));
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

  void _openFault(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => IspnocFaultPage(app: widget.app, id: id)))
      .then((_) => _load());

  Widget _faultTile(Map<String, dynamic> f) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: () => _openFault(_s(f['id'])),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: _list(f['tickets']).isEmpty ? C.accent : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(_faultIcon(_s(f['kind'])), color: _confColor(f['confidence']), size: 20),
                const SizedBox(width: 6),
                Expanded(child: Text('${_s(f['number'])} · ${_s(f['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill(_s(f['confidence_label']), fg: _confColor(f['confidence'])),
              ]),
              const SizedBox(height: 4),
              Text(
                  [
                    if (_s(f['olt']).isNotEmpty) _s(f['olt']),
                    if (_s(f['pon']).isNotEmpty) 'PON ${_s(f['pon'])}',
                    '${f['n_affected']} customer',
                    _s(f['duration']),
                    _list(f['tickets']).isEmpty ? 'ticket nahi' : 'ticket: ${_s(_list(f['tickets']).last['number'])}',
                  ].join(' · '),
                  style: const TextStyle(color: C.muted, fontSize: 12)),
              Text(_s(f['explain']), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, height: 1.3)),
            ]),
          ),
        ),
      );

  Widget _today() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      for (final c in _list(d['waiting_haan']))
        Padding(padding: const EdgeInsets.only(bottom: 8), child: IspnocChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      if (_list(d['faults']).isNotEmpty) Text('Khuli dikkat', style: display(15)),
      const SizedBox(height: 6),
      for (final f in _list(d['faults'])) _faultTile(f),
      for (final t in _list(d['late']))
        Text('• ${_s(t['number'])} ${_s(t['team_label'])}: SLA se der (due ${_s(t['due'])})', style: const TextStyle(fontSize: 12.5, color: C.bad)),
      for (final c in _list(d['collectors']).where((c) => c['online'] != true && _s(c['last_seen']).isNotEmpty))
        Text('• Collector ${_s(c['name'])} band (aakhri baar ${_s(c['last_seen'])})', style: const TextStyle(fontSize: 12.5, color: C.warn)),
    ]);
  }

  Future<void> _pickAlarmFile() async {
    try {
      final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['txt', 'log', 'csv']);
      final f = res?.files.single;
      if (f == null || f.bytes == null) return;
      await _run('POST', '/api/ispnoc/alarms', {
        'data_b64': base64Encode(f.bytes!),
        'source': 'file',
        if (_olt.text.trim().isNotEmpty) 'olt': _olt.text.trim(),
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _alarms() {
    final olts = _list(_m(_d?['network'])['olts']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('OLT ka alarm log, syslog, NMS ki CSV ya alert email yahan daaliye. Hoola asli wajah dhoondhega.',
          style: TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      TextField(
        controller: _alarm,
        maxLines: 10,
        minLines: 6,
        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
        decoration: const InputDecoration(hintText: '2026-10-23 10:15:01 OLT-AKOT EPON0/1:12 ONU LOS ...', border: OutlineInputBorder()),
      ),
      const SizedBox(height: 8),
      TextField(controller: _olt, decoration: const InputDecoration(labelText: 'Kaun sa OLT (log mein naam na ho to)')),
      if (olts.isNotEmpty)
        Wrap(spacing: 6, children: [
          for (final o in olts) ActionChip(label: Text(_s(o['name'])), onPressed: () => setState(() => _olt.text = _s(o['name']))),
        ]),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(
            child: GradientButton(
                label: 'Jaancho',
                icon: Icons.search_rounded,
                height: 48,
                onTap: _busy
                    ? null
                    : () async {
                        if (_alarm.text.trim().isEmpty) return;
                        final r = await _run('POST', '/api/ispnoc/alarms', {
                          'text': _alarm.text,
                          if (_olt.text.trim().isNotEmpty) 'olt': _olt.text.trim(),
                        });
                        if (r != null && mounted) {
                          _alarm.clear();
                          final news = _list(r['new']);
                          if (news.length == 1) _openFault(_s(news.first['id']));
                        }
                      })),
        const SizedBox(width: 8),
        GlassButton(label: 'File', icon: Icons.upload_file_rounded, onTap: _busy ? null : _pickAlarmFile),
      ]),
    ]);
  }

  Widget _tickets() {
    final all = _list(_d?['tickets']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (all.isEmpty) const Text('Koi khula ticket nahi.', style: TextStyle(color: C.muted)),
      for (final t in all) Padding(padding: const EdgeInsets.only(bottom: 8), child: IspnocTicketCard(app: widget.app, data: {'ticket': t}, onDone: _load)),
      const SizedBox(height: 8),
      GlassButton(
          label: 'Report (30 din)',
          icon: Icons.insights_rounded,
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => _IspnocReportPage(app: widget.app)))),
    ]);
  }

  Future<void> _import() async {
    try {
      final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
      final f = res?.files.single;
      if (f == null || f.bytes == null) return;
      await _run('POST', '/api/ispnoc/import', {'name': f.name, 'data_b64': base64Encode(f.bytes!)});
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _addOlt([Map<String, dynamic>? o]) async {
    final f = await _form(context, o == null ? 'Naya OLT' : _s(o['name']), [
      if (o == null) ('name', 'Naam (jaise OLT-AKOT-1)'),
      ('make', 'Make: syrotech / vsol / cdata / bdcom / huawei / zte / other'),
      ('model', 'Model'),
      ('tech', 'gpon / epon'),
      ('optics', 'Optics: gpon_b+ / gpon_c+ / epon_px20 / epon_px20+'),
      ('ip', 'Management IP'),
      ('site', 'Site / POP'),
      ('pon_ports', 'PON ports'),
      ('uplinks', 'Uplink ports (comma se: ge0/9, xe0/1)'),
      ('upstream', 'Uplink kahan jaata hai (BSNL / ISP)'),
    ], initial: o == null
        ? null
        : {
            'make': _s(o['make']),
            'model': _s(o['model']),
            'tech': _s(o['tech']),
            'optics': _s(o['optics']),
            'ip': _s(o['ip']),
            'site': _s(o['site']),
            'pon_ports': _s(o['pon_ports']),
            'uplinks': _strs(o['uplinks']).join(', '),
            'upstream': _s(o['upstream']),
          }, ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/ispnoc/olts', {if (o != null) 'olt': o['id'], ...f});
  }

  Future<void> _findCustomer() async {
    final f = await _form(context, 'Customer dhoondho', const [('q', 'Naam / mobile / SN / MAC / account')], ok: 'Dhoondho');
    if (f == null || (f['q'] ?? '').isEmpty || !mounted) return;
    final r = await _call(context, widget.app, 'GET', '/api/ispnoc/onts?q=${Uri.encodeQueryComponent(f['q']!)}');
    if (r == null || !mounted) return;
    final onts = _list(r['onts']);
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('${onts.length} mile'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final o in onts.take(30))
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                    '${_s(o['customer'])} · ${_s(o['olt'])} PON ${_s(o['pon'])} ONU ${_s(o['onu'])} · ${_s(o['state']).isEmpty ? '?' : _s(o['state'])}'
                    '${o['rx_last'] != null ? ' · Rx ${_s(o['rx_last'])} (${_s(o['rx_band'])})' : ''}',
                    style: const TextStyle(fontSize: 12.5)),
              ),
          ]),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))],
      ),
    );
  }

  Widget _network() {
    final n = _m(_d?['network']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Text(
            '${_list(n['olts']).length} OLT · ${n['onts'] ?? 0} customer ONT · ${n['onts_down'] ?? 0} band · ${n['weak_rx'] ?? 0} ki light kam · '
            '${_list(n['splitters']).length} splitter',
            style: const TextStyle(fontWeight: FontWeight.w700)),
      ),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Naya OLT', icon: Icons.add_rounded, onTap: _busy ? null : () => _addOlt()),
        GlassButton(label: 'Sheet se daalo', icon: Icons.table_view_rounded, onTap: _busy ? null : _import),
        GlassButton(label: 'Customer dhoondho', icon: Icons.search_rounded, onTap: _findCustomer),
        GlassButton(
            label: 'Light ka hisaab',
            icon: Icons.calculate_rounded,
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => _OpticsPage(app: widget.app)))),
      ]),
      const SizedBox(height: 6),
      const Text('Sheet ke columns: customer, mobile, sn / mac, olt, pon, onu, splitter, route, address. Password ka column kabhi mat daaliye.',
          style: TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 10),
      for (final o in _list(n['olts']))
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => _addOlt(o),
            child: Glass(
              padding: const EdgeInsets.all(12),
              child: Row(children: [
                Icon(Icons.dns_rounded, color: (o['down'] ?? 0) > 0 ? C.bad : C.ok),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(o['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text(
                        '${_s(o['make'])} ${_s(o['model'])} · ${_s(o['tech']).toUpperCase()} · ${_s(o['ip'])} · ${_s(o['site'])} · '
                        '${o['onts']} ONT, ${o['down']} band',
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
    ]);
  }

  Future<void> _newChange() async {
    final f = await _form(context, 'Equipment par badlav (card banega)', const [
      ('action', 'Kya: reboot_ont / pon_reset / ont_disable / ont_enable / uplink_reset / custom'),
      ('olt', 'OLT (naam ya IP)'),
      ('pon', 'PON (jaise 0/1)'),
      ('onu', 'ONU number'),
      ('port', 'Uplink port (uplink_reset ke liye)'),
      ('commands', 'Apni lines (custom ho to, har line nayi line par)'),
      ('reason', 'Kyun'),
    ], ok: 'Card banao', multi: const {'commands'});
    if (f == null) return;
    await _run('POST', '/api/ispnoc/changes', {
      ...f,
      if ((f['commands'] ?? '').isNotEmpty) 'commands': f['commands']!.split('\n').where((x) => x.trim().isNotEmpty).toList(),
    });
  }

  Widget _changes() {
    final all = _list(_d?['changes']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('OLT / ONT par koi bhi badlav sirf aapki haan se. Collector ho to wahi chalata hai, warna steps milte hain.',
          style: TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 8),
      GlassButton(label: 'Naya badlav card', icon: Icons.add_task_rounded, onTap: _busy ? null : _newChange),
      const SizedBox(height: 10),
      if (all.isEmpty) const Text('Koi badlav nahi.', style: TextStyle(color: C.muted)),
      for (final c in all) Padding(padding: const EdgeInsets.only(bottom: 8), child: IspnocChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
    ]);
  }

  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    final teams = _m(st['teams']);
    String first(String team, String k) {
      final l = _list(teams[team]);
      return l.isEmpty ? '' : _s(l.first[k]);
    }

    final f = await _form(context, 'ISP ki jaankari', [
      ('isp_name', 'ISP / franchise ka naam'),
      ('model', 'isp (apna licence) / franchise (BSNL TIP) / lco'),
      ('upstream', 'Bandwidth kahan se (BSNL / Airtel / ...)'),
      ('optics', 'Optics: gpon_b+ / gpon_c+ / epon_px20 / epon_px20+'),
      ('bsnl_sla_hours', 'BSNL agreement ke SLA ghante (agreement se)'),
      ('field_name', 'Field fibre team: naam'),
      ('field_phone', 'Field fibre team: mobile'),
      ('noc_name', 'NOC: naam'),
      ('noc_phone', 'NOC: mobile'),
      ('bsnl_name', 'BSNL sampark: naam (SDE / JTO)'),
      ('bsnl_phone', 'BSNL sampark: mobile'),
      ('morning_time', 'Subah ka note (HH:MM)'),
    ], initial: {
      'isp_name': _s(st['isp_name']),
      'model': _s(st['model']),
      'upstream': _s(st['upstream']),
      'optics': _s(st['optics']),
      'bsnl_sla_hours': _s(st['bsnl_sla_hours']),
      'field_name': first('field_fibre', 'name'),
      'field_phone': first('field_fibre', 'phone'),
      'noc_name': first('noc', 'name'),
      'noc_phone': first('noc', 'phone'),
      'bsnl_name': first('bsnl', 'name'),
      'bsnl_phone': first('bsnl', 'phone'),
      'morning_time': _s(st['morning_time']),
    }, ok: 'Save');
    if (f == null) return;
    final t = <String, dynamic>{};
    for (final (team, k) in const [('field_fibre', 'field'), ('noc', 'noc'), ('bsnl', 'bsnl')]) {
      if ((f['${k}_name'] ?? '').isNotEmpty) {
        t[team] = [
          {'name': f['${k}_name'], 'phone': f['${k}_phone'] ?? ''}
        ];
      }
    }
    await _run('PUT', '/api/ispnoc/settings', {
      for (final k in const ['isp_name', 'model', 'upstream', 'optics', 'morning_time']) if (f[k] != null) k: f[k],
      if (f['bsnl_sla_hours'] != null) 'bsnl_sla_hours': double.tryParse(f['bsnl_sla_hours']!),
      if (t.isNotEmpty) 'teams': t,
    });
  }

  Future<void> _newCollector() async {
    final f = await _form(context, 'Naya collector', const [('name', 'Naam (jaise Akot POP box)'), ('site', 'Site / POP')], ok: 'Banao');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/ispnoc/collectors', f);
    if (r == null || !mounted) return;
    final c = _m(r['collector']);
    final secret = _s(r['secret']);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (d) => AlertDialog(
        title: const Text('Collector ka secret (sirf abhi)'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('collector_id: ${_s(c['id'])}', style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
          const SizedBox(height: 6),
          SelectableText(secret, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
          const SizedBox(height: 8),
          const Text(
              'Ise apne POP / office ke computer par HOOLA_COLLECTOR_SECRET mein daaliye. Device ke password / SSH key wahi rahenge, Hoola ke paas nahi. '
              'Yeh secret dobara nahi dikhega.',
              style: TextStyle(fontSize: 12.5, color: C.muted)),
        ]),
        actions: [
          TextButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: 'collector_id=${_s(c['id'])}\nHOOLA_COLLECTOR_SECRET=$secret'));
                Navigator.pop(d);
              },
              child: const Text('Copy karke band')),
        ],
      ),
    );
  }

  Future<void> _collectorOlts(Map<String, dynamic> c) async {
    final olts = _list(_m(_d?['network'])['olts']);
    final picked = {for (final o in olts) if (_s(o['collector_id']) == _s(c['id'])) _s(o['name'])};
    bool changes = c['changes_ok'] == true;
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: Text(_s(c['name'])),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Yeh collector kin OLT ke liye bolega:', style: TextStyle(fontSize: 12.5)),
              for (final o in olts)
                CheckboxListTile(
                  dense: true,
                  value: picked.contains(_s(o['name'])),
                  title: Text(_s(o['name'])),
                  onChanged: (v) => set(() => v == true ? picked.add(_s(o['name'])) : picked.remove(_s(o['name']))),
                ),
              SwitchListTile(
                dense: true,
                value: changes,
                title: const Text('Haan kiye hue badlav yeh chala sakta hai'),
                subtitle: const Text('Band = sirf alarm aur "show" padhega'),
                onChanged: (v) => set(() => changes = v),
              ),
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
    await _run('PATCH', '/api/ispnoc/collectors/${_s(c['id'])}', {'olts': picked.toList(), 'changes_ok': changes});
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    final sla = _m(st['sla']);
    final facts = _m(_d?['facts']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['isp_name']).isEmpty ? 'ISP ka naam nahi diya' : _s(st['isp_name']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('Roop: ${_s(st['model'])} · upstream: ${_s(st['upstream'])} · optics: ${_s(st['optics_label'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text(st['bsnl_sla_hours'] == null ? 'BSNL SLA ghante: nahi diye (agreement se daaliye)' : 'BSNL SLA: ${_s(st['bsnl_sla_hours'])} ghante',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          for (final e in _m(st['teams']).entries)
            Text('${_s(_m(_d?['teams_all'])[e.key])}: ${_list(e.value).map((p) => _s(p['name'])).join(', ')}', style: const TextStyle(fontSize: 12.5)),
        ]),
      ),
      const SizedBox(height: 8),
      GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _busy ? null : _settings),
      const SizedBox(height: 10),
      Text('Collector (aapke network par)', style: display(14)),
      const Text('Ek chhota script jo aapke POP ke computer par chalta hai: OLT ka syslog leta hai, sirf "show" commands chalata hai, Hoola ko signed bhejta hai.',
          style: TextStyle(color: C.muted, fontSize: 12)),
      for (final c in _list(_d?['collectors']))
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.memory_rounded, color: c['online'] == true ? C.ok : C.muted),
          title: Text(_s(c['name'])),
          subtitle: Text('${c['online'] == true ? 'juda hai' : 'band'} · ${_s(c['last_seen'])} · badlav: ${c['changes_ok'] == true ? 'haan' : 'nahi'}'),
          onTap: () => _collectorOlts(c),
        ),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Naya collector', icon: Icons.add_link_rounded, onTap: _busy ? null : _newCollector),
        GlassButton(
            label: 'Script ka link copy',
            icon: Icons.code_rounded,
            onTap: () {
              Clipboard.setData(const ClipboardData(text: '/api/ispnoc/collector-script'));
              _snack(context, 'Apne Hoola server ke address ke aage yeh path jodkar script download kijiye (app ki key ke saath).');
            }),
      ]),
      const SizedBox(height: 10),
      Text('Theek karne ke ghante (shuruaati, aap badal sakti hain)', style: display(14)),
      Text(sla.entries.where((e) => (e.value is num) && (e.value as num) > 0).map((e) => '${e.key} ${e.value}h').join(' · '),
          style: const TextStyle(fontSize: 12, color: C.muted)),
      const SizedBox(height: 10),
      Text('Niyam aur sources', style: display(14)),
      for (final v in facts.values) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• ${_s(v)}', style: const TextStyle(fontSize: 12))),
      for (final src in _list(_d?['sources']))
        InkWell(
          onTap: () => _open(context, _s(src['url'])),
          child: Text(_s(src['title']), style: const TextStyle(fontSize: 12, color: C.accentSoft, decoration: TextDecoration.underline)),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('NOC Sahayak (ISP network)')),
        floatingActionButton: _tab == 0
            ? FloatingActionButton.extended(onPressed: () => setState(() => _tab = 1), icon: const Icon(Icons.notifications_active_rounded), label: const Text('Alarm daalo'))
            : null,
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Alarm'), (2, 'Tickets'), (3, 'Network'), (4, 'Badlav'), (5, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 12),
              if (_d == null)
                const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator()))
              else
                switch (_tab) {
                  0 => _today(),
                  1 => _alarms(),
                  2 => _tickets(),
                  3 => _network(),
                  4 => _changes(),
                  _ => _rules(),
                },
            ]),
          ),
        ),
      );
}

/// One fault: why Hoola thinks so, the alarm timeline, who is affected, where, ticket, customer message.
class IspnocFaultPage extends StatefulWidget {
  const IspnocFaultPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<IspnocFaultPage> createState() => _IspnocFaultPageState();
}

class _IspnocFaultPageState extends State<IspnocFaultPage> {
  Map<String, dynamic>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final f = _m(await widget.app.api!.call('GET', '/api/ispnoc/faults/${widget.id}'));
      if (mounted) setState(() => _f = f);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final f = _f;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(f == null ? 'Dikkat' : '${_s(f['number'])} · ${_s(f['title'])}')),
      body: Aurora(
        child: f == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  IspnocFaultCard(app: widget.app, data: {'fault': f}, onDone: _load, full: true),
                  const SizedBox(height: 10),
                  Text('Alarm ki timeline', style: display(14)),
                  for (final e in _list(f['evidence']))
                    Text('${_s(e['at']).replaceFirst('T', ' ')}  ${_s(e['line'])}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
                  const SizedBox(height: 10),
                  Text('Asar wale customer (${f['n_affected']})', style: display(14)),
                  for (final a in _list(f['affected']))
                    Text(
                        '• ${_s(a['customer']).isEmpty ? _s(a['label']) : _s(a['customer'])} ${_s(a['phone'])} ${_s(a['address'])}'
                        '${_s(a['splitter']).isNotEmpty ? ' · ${_s(a['splitter'])}' : ''}',
                        style: const TextStyle(fontSize: 12.5)),
                  if (_m(f['location']).isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Text('Jagah', style: display(14)),
                    for (final e in _m(f['location']).entries.where((e) => _s(e.value).isNotEmpty && !_s(e.key).endsWith('maps')))
                      Text('${e.key}: ${_s(e.value)}', style: const TextStyle(fontSize: 12.5)),
                    Wrap(spacing: 8, children: [
                      for (final k in const ['maps', 'splitter_maps', 'customer_maps'])
                        if (_s(_m(f['location'])[k]).isNotEmpty)
                          GlassButton(label: 'Map', icon: Icons.map_rounded, height: 40, onTap: () => _open(context, _s(_m(f['location'])[k]))),
                    ]),
                  ],
                  for (final n in _strs(f['notes'])) Padding(padding: const EdgeInsets.only(top: 8), child: Text(n, style: const TextStyle(color: C.warn, fontSize: 12.5))),
                  const SizedBox(height: 10),
                  for (final t in _list(f['tickets']))
                    Padding(padding: const EdgeInsets.only(bottom: 8), child: IspnocTicketCard(app: widget.app, data: {'ticket': t}, onDone: _load)),
                  for (final l in _list(f['log'])) Text('${_s(l['by'])}: ${_s(l['text'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
                ]),
              ),
      ),
    );
  }
}

/// `ispnoc_fault`: the real fault in plain words + Ticket / Customer message / Theek / Kholo.
class IspnocFaultCard extends StatefulWidget {
  const IspnocFaultCard({super.key, required this.app, required this.data, this.onDone, this.full = false});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  final bool full;
  @override
  State<IspnocFaultCard> createState() => _IspnocFaultCardState();
}

class _IspnocFaultCardState extends State<IspnocFaultCard> {
  late Map<String, dynamic> _f = _m(widget.data['fault']);
  bool _busy = false;

  @override
  void didUpdateWidget(covariant IspnocFaultCard old) {
    super.didUpdateWidget(old);
    _f = _m(widget.data['fault']);
  }

  Future<void> _after(Map<String, dynamic>? r) async {
    if (r != null && r['fault'] is Map && mounted) setState(() => _f = _m(r['fault']));
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final f = _f;
    final open = const ['open', 'ticketed'].contains(_s(f['status']));
    return Glass(
      border: open && _list(f['tickets']).isEmpty ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_faultIcon(_s(f['kind'])), color: open ? _confColor(f['confidence']) : C.ok),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(f['number'])} · ${_s(f['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(open ? _s(f['confidence_label']) : _s(f['status_label']), fg: open ? _confColor(f['confidence']) : C.ok),
        ]),
        const SizedBox(height: 4),
        Text(
            [
              if (_s(f['olt']).isNotEmpty) _s(f['olt']),
              if (_s(f['pon']).isNotEmpty) 'PON ${_s(f['pon'])}',
              if (_s(f['scope']) == 'ont' || _s(f['scope']) == 'splitter') _s(f['target']),
              '${f['n_affected']} customer',
              'kab se ${_s(f['started'])} (${_s(f['duration'])})',
            ].join(' · '),
            style: const TextStyle(color: C.muted, fontSize: 12)),
        const SizedBox(height: 6),
        Text(_s(f['explain']), style: const TextStyle(fontSize: 13, height: 1.35)),
        for (final r in _strs(f['reasons']).take(widget.full ? 6 : 2)) Text('• $r', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(f['due']).isNotEmpty && open)
          Text('${_s(f['team_label'])} · SLA ${_s(f['sla_hours'])} ghante (due ${_s(f['due'])})', style: const TextStyle(fontSize: 12, color: C.accentSoft)),
        for (final n in _strs(f['notes']).take(widget.full ? 0 : 1)) Text(n, style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (open)
            GradientButton(
                label: _list(f['tickets']).isEmpty ? 'Ticket banao' : 'Aur ticket',
                icon: Icons.assignment_rounded,
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        setState(() => _busy = true);
                        final r = await _ticketSheet(context, widget.app, f);
                        if (mounted) setState(() => _busy = false);
                        await _after(r);
                      }),
          if (_s(f['customer_msg']).isNotEmpty || !open)
            GlassButton(label: 'Customer message', icon: Icons.campaign_rounded, height: 40, onTap: () => _customerMessage(context, widget.app, f)),
          if (open)
            GlassButton(
                label: 'Theek ho gaya',
                icon: Icons.check_circle_rounded,
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        final n = await _form(context, 'Kya kiya?', const [('note', 'Note (jaise "splice kiya")')], ok: 'Theek');
                        if (n == null || !context.mounted) return;
                        await _after(await _call(context, widget.app, 'POST', '/api/ispnoc/faults/${_s(f['id'])}/resolve', n));
                      }),
          for (final sg in _list(f['suggest']))
            GlassButton(
                label: 'Card: ${_s(sg['action'])}',
                icon: Icons.settings_suggest_rounded,
                height: 40,
                onTap: () async => _after(await _call(context, widget.app, 'POST', '/api/ispnoc/changes', {...sg, 'fault': f['id'], 'reason': sg['why']}))),
          if (!widget.full)
            GlassButton(
                label: 'Kholo',
                icon: Icons.open_in_new_rounded,
                height: 40,
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => IspnocFaultPage(app: widget.app, id: _s(f['id']))))),
        ]),
      ]),
    );
  }
}

/// `ispnoc_ticket`: the team's message + WhatsApp / call buttons she presses, status / ETA.
class IspnocTicketCard extends StatefulWidget {
  const IspnocTicketCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<IspnocTicketCard> createState() => _IspnocTicketCardState();
}

class _IspnocTicketCardState extends State<IspnocTicketCard> {
  late Map<String, dynamic> _t = _m(widget.data['ticket']);

  @override
  void didUpdateWidget(covariant IspnocTicketCard old) {
    super.didUpdateWidget(old);
    _t = _m(widget.data['ticket']);
  }

  Future<void> _patch(Map<String, dynamic> body) async {
    final r = await _call(context, widget.app, 'PATCH', '/api/ispnoc/tickets/${_s(_t['id'])}', body);
    if (r != null && r['ticket'] is Map && mounted) setState(() => _t = _m(r['ticket']));
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    final open = const ['open', 'assigned', 'on_site'].contains(_s(t['status']));
    return Glass(
      border: t['late'] == true && open ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.assignment_ind_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(t['number'])} · ${_s(t['team_label'])}${_s(t['assignee']).isNotEmpty ? ' · ${_s(t['assignee'])}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(t['status']), fg: open ? C.warn : C.ok),
        ]),
        const SizedBox(height: 4),
        Text(
            [
              if (_s(t['fault']).isNotEmpty) _s(t['fault']),
              if (_s(t['eta']).isNotEmpty) 'ETA ${_s(t['eta'])}',
              if (_s(t['due']).isNotEmpty) 'SLA due ${_s(t['due'])}',
              if (t['mttr_hours'] != null) 'MTTR ${_s(t['mttr_hours'])} ghante',
              if (_s(t['ext_ref']).isNotEmpty) 'Docket ${_s(t['ext_ref'])}',
            ].join(' · '),
            style: TextStyle(color: t['late'] == true ? C.bad : C.muted, fontSize: 12)),
        const SizedBox(height: 6),
        Text(_s(t['text']), maxLines: 8, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, height: 1.3)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'WhatsApp', icon: Icons.chat_rounded, height: 40, onTap: () => _open(context, _s(t['wa_link']))),
          if (_s(t['tel']).isNotEmpty) GlassButton(label: 'Call', icon: Icons.call_rounded, height: 40, onTap: () => _open(context, _s(t['tel']))),
          if (open) ...[
            GlassButton(label: 'Pahunch gaye', icon: Icons.place_rounded, height: 40, onTap: () => _patch({'status': 'on_site'})),
            GlassButton(
                label: 'ETA',
                icon: Icons.schedule_rounded,
                height: 40,
                onTap: () async {
                  final f = await _form(context, 'Naya ETA', const [('eta', '"2 ghante" / "shaam 6 baje" / "18:30"')], ok: 'Save');
                  if (f != null && (f['eta'] ?? '').isNotEmpty) await _patch({'eta': f['eta']});
                }),
            GradientButton(label: 'Theek ho gaya', icon: Icons.check_rounded, height: 40, onTap: () => _patch({'status': 'fixed'})),
          ],
        ]),
      ]),
    );
  }
}

/// `ispnoc_change`: a change on live equipment. Exact commands + rollback + who loses service; ONLY her tap approves.
class IspnocChangeCard extends StatefulWidget {
  const IspnocChangeCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<IspnocChangeCard> createState() => _IspnocChangeCardState();
}

class _IspnocChangeCardState extends State<IspnocChangeCard> {
  late Map<String, dynamic> _c = _m(widget.data['change']);
  bool _busy = false;

  @override
  void didUpdateWidget(covariant IspnocChangeCard old) {
    super.didUpdateWidget(old);
    _c = _m(widget.data['change']);
  }

  Future<void> _post(String path, Map<String, dynamic> body, {String method = 'POST'}) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['change'] is Map) _c = _m(r['change']);
      });
    }
    widget.onDone?.call();
  }

  Future<void> _decide(bool yes) async {
    String reason = '';
    if (yes) {
      final sure = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Pakka?'),
          content: Text('${_s(_c['action_label'])} on ${_s(_c['olt'])}. ${_s(_c['risk'])}'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, karo')),
          ],
        ),
      );
      if (sure != true) return;
    } else {
      final f = await _form(context, 'Kyun nahi? (zaroori nahi)', const [('reason', 'Wajah')], ok: 'Mana karo');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    if (!mounted) return;
    await _post('/api/ispnoc/changes/${_s(_c['id'])}/decide', {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason});
  }

  Future<void> _edit() async {
    final f = await _form(context, 'Lines badlo (har line nayi line par)', const [('commands', 'Commands'), ('rollback', 'Rollback')],
        initial: {'commands': _strs(_c['commands']).join('\n'), 'rollback': _strs(_c['rollback']).join('\n')}, multi: const {'commands', 'rollback'}, ok: 'Naya card');
    if (f == null || (f['commands'] ?? '').isEmpty) return;
    List<String> lines(String? v) => (v ?? '').split('\n').where((x) => x.trim().isNotEmpty).toList();
    await _post('/api/ispnoc/changes/${_s(_c['id'])}', {'commands': lines(f['commands']), 'rollback': lines(f['rollback'])}, method: 'PUT');
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final st = _s(c['status']);
    const mono = TextStyle(fontFamily: 'monospace', fontSize: 11.5);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.settings_suggest_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${st == 'waiting' ? 'Aapki haan chahiye' : _s(c['status_label'])} · ${_s(c['number'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(c['make']).isEmpty ? 'OLT' : _s(c['make'])),
        ]),
        const SizedBox(height: 4),
        Text(
            '${_s(c['action_label'])} · ${_s(c['olt'])} ${_s(c['olt_ip'])}'
            '${_s(c['pon']).isNotEmpty ? ' · PON ${_s(c['pon'])}' : ''}${_s(c['onu']).isNotEmpty ? ' ONU ${_s(c['onu'])}' : ''}',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        if (_s(c['reason']).isNotEmpty) Text('Kyun: ${_s(c['reason'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(c['risk']).isNotEmpty) Text('Dhyaan: ${_s(c['risk'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 6),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final l in _strs(c['commands'])) Text(l, style: mono),
            if (_strs(c['rollback']).isNotEmpty) ...[
              const SizedBox(height: 6),
              const Text('Wapas (rollback):', style: TextStyle(fontSize: 11, color: C.muted)),
              for (final l in _strs(c['rollback'])) Text(l, style: mono),
            ],
          ]),
        ),
        if (_s(c['warn']).isNotEmpty && st == 'waiting') Text(_s(c['warn']), style: const TextStyle(fontSize: 11.5, color: C.warn)),
        if (st == 'approved' && _s(c['steps']).isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(_s(c['steps']), style: const TextStyle(fontSize: 12, height: 1.3)),
        ],
        if (_s(c['output']).isNotEmpty) Text(_s(c['output']), maxLines: 8, overflow: TextOverflow.ellipsis, style: mono),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, karo', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 8),
            GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 44, onTap: _busy ? null : _edit),
          ])
        else if (st == 'approved')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: 'Maine kar diya', icon: Icons.done_all_rounded, height: 42, onTap: _busy ? null : () => _post('/api/ispnoc/changes/${_s(c['id'])}/done', {'ok': true}))),
            const SizedBox(width: 8),
            Expanded(
                child: GlassButton(
                    label: 'Nahi hua', icon: Icons.error_outline_rounded, height: 42, onTap: _busy ? null : () => _post('/api/ispnoc/changes/${_s(c['id'])}/done', {'ok': false}))),
          ]),
      ]),
    );
  }
}

/// `ispnoc_alert`: SLA / ETA / big outage / collector offline.
class IspnocAlertCard extends StatelessWidget {
  const IspnocAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        border: C.warn,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.warning_amber_rounded, color: C.warn),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13, height: 1.35))),
        ]),
      );
}

/// `ispnoc_day`: morning network note.
class IspnocDayCard extends StatelessWidget {
  const IspnocDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.lan_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('Aaj ka network', style: display(14))),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['text']).isEmpty ? _s(data['say']) : _s(data['text']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
          const SizedBox(height: 8),
          GlassButton(
              label: 'NOC kholo',
              icon: Icons.open_in_new_rounded,
              height: 40,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => IspnocScreen(app: app)))),
        ]),
      );
}

class _IspnocReportPage extends StatefulWidget {
  const _IspnocReportPage({required this.app});
  final Santosh app;
  @override
  State<_IspnocReportPage> createState() => _IspnocReportPageState();
}

class _IspnocReportPageState extends State<_IspnocReportPage> {
  Map<String, dynamic>? _r;
  int _days = 30;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/ispnoc/report', query: {'days': '$_days'}));
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Network report')),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Wrap(spacing: 6, children: [
            for (final d in const [7, 30, 90])
              ChoiceChip(
                  label: Text('$d din'),
                  selected: _days == d,
                  onSelected: (_) {
                    setState(() => _days = d);
                    _load();
                  }),
          ]),
          const SizedBox(height: 10),
          if (r == null)
            const Center(child: CircularProgressIndicator())
          else ...[
            Glass(child: Text(_s(r['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
            const SizedBox(height: 8),
            for (final k in _list(r['by_kind']))
              Text('• ${_s(k['title'])}: ${k['count']} baar${k['mttr_hours'] != null ? ', ausat ${_s(k['mttr_hours'])} ghante' : ''}',
                  style: const TextStyle(fontSize: 12.5)),
            const SizedBox(height: 8),
            for (final t in _list(r['teams']))
              Text('• ${_s(t['label'])}: ${t['tickets']} ticket, ${t['fixed']} theek${t['sla_pct'] != null ? ', SLA mein ${t['sla_pct']}%' : ''}',
                  style: const TextStyle(fontSize: 12.5)),
            const SizedBox(height: 8),
            for (final p in _list(r['top_pons'])) Text('• ${_s(p['pon'])}: ${p['count']} baar', style: const TextStyle(fontSize: 12.5, color: C.warn)),
            for (final tip in _strs(r['tips'])) Text(tip, style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
          ],
        ]),
      ),
    );
  }
}

class _OpticsPage extends StatefulWidget {
  const _OpticsPage({required this.app});
  final Santosh app;
  @override
  State<_OpticsPage> createState() => _OpticsPageState();
}

class _OpticsPageState extends State<_OpticsPage> {
  String _cls = 'gpon_b+';
  final _km = TextEditingController(text: '3');
  final _splits = TextEditingController(text: '8, 8');
  final _rx = TextEditingController();
  Map<String, dynamic>? _out;

  @override
  void dispose() {
    _km.dispose();
    _splits.dispose();
    _rx.dispose();
    super.dispose();
  }

  Future<void> _go() async {
    final splits = _splits.text.split(RegExp(r'[,\s]+')).map((e) => int.tryParse(e.replaceAll('1:', ''))).whereType<int>().toList();
    final r = await _call(context, widget.app, 'POST', '/api/ispnoc/optics', {
      'class': _cls,
      'km': double.tryParse(_km.text) ?? 0,
      'splits': splits,
      if (double.tryParse(_rx.text) != null) 'rx': double.parse(_rx.text),
    });
    if (mounted) setState(() => _out = r);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Light ka hisaab (power budget)')),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            Wrap(spacing: 6, children: [
              for (final c in const ['gpon_b+', 'gpon_c+', 'epon_px20', 'epon_px20+'])
                ChoiceChip(label: Text(c), selected: _cls == c, onSelected: (_) => setState(() => _cls = c)),
            ]),
            TextField(controller: _km, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Fibre km')),
            TextField(controller: _splits, decoration: const InputDecoration(labelText: 'Splitter (jaise 8, 8 ya 4, 16)')),
            TextField(controller: _rx, keyboardType: const TextInputType.numberWithOptions(signed: true, decimal: true), decoration: const InputDecoration(labelText: 'Naapa hua Rx dBm (ho to)')),
            const SizedBox(height: 10),
            GradientButton(label: 'Hisaab lagao', icon: Icons.calculate_rounded, height: 46, onTap: _go),
            if (_out != null) ...[
              const SizedBox(height: 10),
              Glass(child: Text(_s(_out!['say']), style: const TextStyle(fontSize: 13, height: 1.35))),
            ],
          ]),
        ),
      );
}
