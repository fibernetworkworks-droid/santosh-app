/// Profile > After-sales Sahayak (Seva): Hoola as a dealer's / service business's after-sales coworker.
/// Aaj (visits per technician, charges waiting for her) · Due (service due / late, reminder drafts she sends) · Visit (book in
/// free slots grouped by area, job card, kaam poora with checklist / readings / parts / photos / customer sign, report) ·
/// Machine (installed base, import sheet) · Team (technicians) · AMC (revenue, renewals, warranty claims).
/// A charge to a customer and any business-WhatsApp message happen only by HER tap here. Hoola never takes money.
library;

import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).where((e) => e is Map).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) {
  if (t.isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

double? _n(String? v) => v == null ? null : double.tryParse(v.replaceAll(',', '').replaceAll('₹', '').trim());

String _rs(dynamic v) {
  final n = (v is num) ? v.toDouble() : double.tryParse('$v') ?? 0;
  final whole = n.abs().round();
  var s = '$whole';
  if (s.length > 3) {
    var head = s.substring(0, s.length - 3);
    final tail = s.substring(s.length - 3);
    final parts = <String>[];
    while (head.length > 2) {
      parts.insert(0, head.substring(head.length - 2));
      head = head.substring(0, head.length - 2);
    }
    if (head.isNotEmpty) parts.insert(0, head);
    s = '${parts.join(',')},$tail';
  }
  return '${n < 0 ? '-' : ''}₹$s';
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {Map<String, String>? initial}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial?[k] ?? '')};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields) TextField(controller: c[k], decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage')),
      ],
    ),
  );
  if (ok != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

List<String> _csv(String? v) => (v ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

Future<dynamic> _call(Santosh app, String method, String path, {Object? body, Map<String, String>? query}) =>
    app.api!.call(method, path, body: body, query: query);

class AftersalesScreen extends StatefulWidget {
  const AftersalesScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AftersalesScreen> createState() => _AftersalesScreenState();
}

class _AftersalesScreenState extends State<AftersalesScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _due;
  List<Map<String, dynamic>> _units = const [];
  int _tab = 0;
  bool _busy = false;
  final _q = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = _map(await _call(widget.app, 'GET', '/api/aftersales'));
      final due = _map(await _call(widget.app, 'GET', '/api/aftersales/due', query: {'within': '15'}));
      final u = _map(await _call(widget.app, 'GET', '/api/aftersales/units', query: {'q': _q.text.trim()}));
      if (mounted) {
        setState(() {
          _d = d;
          _due = due;
          _units = _list(u['units']);
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addUnit() async {
    final f = await _form(context, 'Nayi machine', const [
      ('name', 'Graahak ka naam'),
      ('phone', 'Mobile (10 ank)'),
      ('area', 'Area / mohalla'),
      ('pincode', 'Pincode'),
      ('ptype', 'Product (RO / AC / inverter / CCTV ...)'),
      ('brand', 'Brand'),
      ('model', 'Model'),
      ('serial', 'Serial no.'),
      ('installed_on', 'Install ki tareekh (dd-mm-yyyy)'),
      ('warranty_months', 'Warranty (mahine)'),
    ]);
    if (f == null) return;
    await _run(() => _call(widget.app, 'POST', '/api/aftersales/units', body: {
          ...f,
          if (f['warranty_months'] != null) 'warranty_months': _n(f['warranty_months']),
        }));
  }

  Future<void> _import() async {
    try {
      final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
      final f = res?.files.single;
      if (f == null || f.bytes == null) return;
      await _run(() => _call(widget.app, 'POST', '/api/aftersales/import', body: {'name': f.name, 'data_b64': base64Encode(f.bytes!)}));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _addTech([Map<String, dynamic>? t]) async {
    final f = await _form(context, t == null ? 'Naya technician' : _s(t['name']), const [
      ('name', 'Naam'),
      ('phone', 'Mobile'),
      ('skills', 'Kaam (comma se: ro, ac, inverter, cctv...)'),
      ('areas', 'Area / pincode (comma se; khaali = sab jagah)'),
      ('per_day', 'Din mein kitne visit'),
    ], initial: t == null
        ? null
        : {
            'name': _s(t['name']),
            'phone': _s(t['phone']),
            'skills': ((t['skills'] as List?) ?? const []).join(', '),
            'areas': ((t['areas'] as List?) ?? const []).join(', '),
            'per_day': _s(t['per_day']),
          });
    if (f == null) return;
    await _run(() => _call(widget.app, 'POST', '/api/aftersales/techs', body: {
          if (t != null) 'tech': t['id'],
          ...f,
          'skills': _csv(f['skills']),
          'areas': _csv(f['areas']),
          if (f['per_day'] != null) 'per_day': int.tryParse(f['per_day']!) ?? 6,
        }));
  }

  void _openUnit(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => AsUnitPage(app: widget.app, id: id)))
      .then((_) => _load());

  void _openVisit(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => AsVisitPage(app: widget.app, id: id)))
      .then((_) => _load());

  Widget _visitTile(Map<String, dynamic> v) {
    final c = _map(v['customer']);
    final u = _map(v['unit']);
    final ch = _map(v['charge']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _openVisit(_s(v['id'])),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: (ch['status'] == 'pending' || ch['status'] == 'needs_price') ? C.warn : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(v['number'])} · ${_s(c['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(_s(v['status'])),
            ]),
            Text('${_s(v['when'])} · ${_s(_map(v['tech'])['name'])} · ${_s(u['label'])} ${_s(u['brand'])} · ${_s(c['area'])}',
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if (ch['status'] == 'pending' || ch['status'] == 'needs_price')
              Text('Charge par aapki haan baaki', style: const TextStyle(color: C.warn, fontSize: 12.5)),
          ]),
        ),
      ),
    );
  }

  Widget _today() {
    final day = _map(_d?['day']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Text('Aaj ke visit', style: display(15)),
      const SizedBox(height: 6),
      if (_list(day['visits']).isEmpty) const Text('Aaj koi visit nahi.', style: TextStyle(color: C.muted)),
      for (final v in _list(day['visits'])) _visitTile(v),
      if (_list(_d?['drafts']).isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Bhejne baaki (draft)', style: display(15)),
        const SizedBox(height: 6),
        AftersalesRemindersCard(app: widget.app, data: {'messages': _d?['drafts'], 'say': '${_list(_d?['drafts']).length} draft'}),
      ],
    ]);
  }

  Widget _dueTab() {
    final d = _due ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(_s(d['say']), style: const TextStyle(fontSize: 13)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(
            label: 'Reminder draft banao',
            icon: Icons.notifications_active_rounded,
            onTap: _busy
                ? null
                : () async {
                    final r = await _run(() => _call(widget.app, 'POST', '/api/aftersales/remind', body: {'kind': 'due'}));
                    if (r != null && mounted && _list(r['messages']).isNotEmpty) {
                      await showModalBottomSheet<void>(
                          context: context,
                          isScrollControlled: true,
                          builder: (_) => Padding(
                              padding: const EdgeInsets.all(16),
                              child: SingleChildScrollView(child: AftersalesRemindersCard(app: widget.app, data: r))));
                    }
                  }),
        GlassButton(
            label: 'AMC khatam - draft',
            icon: Icons.event_repeat_rounded,
            onTap: _busy ? null : () => _run(() => _call(widget.app, 'POST', '/api/aftersales/remind', body: {'kind': 'amc'}))),
      ]),
      const SizedBox(height: 10),
      for (final u in _list(d['due']))
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => _openUnit(_s(u['id'])),
            child: Glass(
              padding: const EdgeInsets.all(12),
              border: u['overdue'] == true ? C.bad : null,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                      child: Text('${_s(_map(u['customer'])['name'])} · ${_s(u['label'])} ${_s(u['brand'])}',
                          style: const TextStyle(fontWeight: FontWeight.w800))),
                  if (u['booked'] != null) const Pill('booked') else if (u['reminded'] == true) const Pill('draft bana'),
                ]),
                Text('Due ${_s(u['next_due'])}${u['overdue'] == true ? ' (late)' : ''} · ${_s(_map(u['customer'])['area'])} ${_s(_map(u['customer'])['pincode'])}',
                    style: TextStyle(color: u['overdue'] == true ? C.bad : C.muted, fontSize: 12.5)),
              ]),
            ),
          ),
        ),
      for (final u in _list(d['amc_ending']))
        Text('• AMC ${_s(_map(u['amc'])['until'])}: ${_s(_map(u['customer'])['name'])} (${_s(u['label'])})', style: const TextStyle(fontSize: 12.5)),
      for (final u in _list(d['warranty_ending']))
        Text('• Warranty ${_s(u['warranty_until'])}: ${_s(_map(u['customer'])['name'])} (${_s(u['label'])})',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  Widget _visitsTab() => _AsVisitsTab(app: widget.app, onOpen: _openVisit);

  Widget _unitsTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Nayi machine', icon: Icons.add_rounded, onTap: _busy ? null : _addUnit),
          GlassButton(label: 'Sheet se (Excel / CSV)', icon: Icons.upload_file_rounded, onTap: _busy ? null : _import),
        ]),
        const SizedBox(height: 8),
        TextField(
          controller: _q,
          decoration: const InputDecoration(hintText: 'Naam, mobile, area, serial...', prefixIcon: Icon(Icons.search_rounded)),
          onSubmitted: (_) => _load(),
        ),
        const SizedBox(height: 8),
        for (final u in _units)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _openUnit(_s(u['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(_map(u['customer'])['name'])} · ${_s(u['label'])} ${_s(u['brand'])} ${_s(u['model'])}',
                      style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text(
                      'Sr ${_s(u['serial']).isEmpty ? '-' : _s(u['serial'])} · agli service ${_s(u['next_due'])}'
                      '${u['in_warranty'] == true ? ' · warranty' : ''}${_map(u['amc'])['active'] == true ? ' · AMC' : ''}',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            ),
          ),
      ]);

  Widget _teamTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(label: 'Naya technician', icon: Icons.engineering_rounded, onTap: _busy ? null : () => _addTech()),
        const SizedBox(height: 8),
        for (final t in _list(_d?['techs']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _addTech(t),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(_s(t['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                    if (t['active'] != true) const Pill('chhutti'),
                  ]),
                  Text(
                      'Kaam: ${((t['skills'] as List?) ?? const []).isEmpty ? 'sab' : (t['skills'] as List).join(', ')} · '
                      'Area: ${((t['areas'] as List?) ?? const []).isEmpty ? 'sab jagah' : (t['areas'] as List).join(', ')} · ${t['per_day']}/din',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  Text('Visit poore ${t['visits_done'] ?? 0} · comeback ${t['comebacks'] ?? 0}', style: const TextStyle(fontSize: 12)),
                ]),
              ),
            ),
          ),
      ]);

  Widget _amcTab() {
    final a = _map(_d?['amc']);
    final cl = _map(_d?['claims']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(a['say']), style: const TextStyle(fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 8),
      for (final r in _list(a['active']).take(30))
        Text('• ${_s(r['customer'])} · ${_s(r['label'])} · ${_s(r['plan'])} · ${_s(r['until'])} (${r['days_left']} din)${(r['price'] ?? 0) > 0 ? ' · ${_rs(r['price'])}' : ''}',
            style: const TextStyle(fontSize: 12.5)),
      if (_list(a['unpaid']).isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('Charge baaki', style: display(15)),
        for (final u in _list(a['unpaid'])) Text('• ${_s(u['number'])}: ${_rs(u['due'])} (${_s(u['on'])})', style: const TextStyle(fontSize: 12.5)),
      ],
      const SizedBox(height: 12),
      Text('Warranty claim (brand)', style: display(15)),
      Text(_s(cl['say']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
      for (final c in _list(cl['claims']).take(40))
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Press(
            onTap: () async {
              final f = await _form(context, 'Claim ${_s(c['number'])}', const [
                ('status', 'Status: raised / approved / part_received / rejected / settled'),
                ('brand_ref', 'Brand ka complaint no.'),
                ('settled', 'Brand se mila (₹)'),
              ], initial: {'status': _s(c['status']), 'brand_ref': _s(c['brand_ref'])});
              if (f == null) return;
              await _run(() => _call(widget.app, 'POST', '/api/aftersales/claims/${c['id']}',
                  body: {...f, if (f['settled'] != null) 'settled': _n(f['settled'])}));
            },
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                Expanded(
                    child: Text('${_s(c['number'])} · ${_s(c['brand'])} · ${_s(c['part'])}${_s(c['brand_ref']).isNotEmpty ? ' · #${_s(c['brand_ref'])}' : ''}',
                        style: const TextStyle(fontSize: 13))),
                Pill(_s(c['status'])),
              ]),
            ),
          ),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('After-sales Sahayak'), actions: [
          IconButton(
              icon: const Icon(Icons.chat_rounded),
              tooltip: 'WhatsApp templates',
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AsTemplatesPage(app: widget.app)))),
          IconButton(
              icon: const Icon(Icons.tune_rounded),
              tooltip: 'Niyam',
              onPressed: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => AsSettingsPage(app: widget.app, data: _map(_d?['settings']), schedules: _list(_d?['schedules']))))
                  .then((_) => _load())),
        ]),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Due'), (2, 'Visit'), (3, 'Machine'), (4, 'Team'), (5, 'AMC')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today, _dueTab, _visitsTab, _unitsTab, _teamTab, _amcTab][_tab](),
              const SizedBox(height: 14),
              const Text(
                  'Graahak ko message aap bhejti hain (ya business WhatsApp aapke tap se). Graahak se charge aapki haan ke baad. '
                  'Warranty install ki tareekh se. Hoola paisa nahi leta / deta.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class _AsVisitsTab extends StatefulWidget {
  const _AsVisitsTab({required this.app, required this.onOpen});
  final Santosh app;
  final void Function(String id) onOpen;
  @override
  State<_AsVisitsTab> createState() => _AsVisitsTabState();
}

class _AsVisitsTabState extends State<_AsVisitsTab> {
  List<Map<String, dynamic>> _v = const [];
  String _filter = 'open';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _map(await _call(widget.app, 'GET', '/api/aftersales/visits', query: {'status': _filter}));
      if (mounted) setState(() => _v = _list(r['visits']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GlassButton(
            label: 'Naya visit',
            icon: Icons.add_task_rounded,
            onTap: () async {
              final id = await showModalBottomSheet<String>(
                  context: context, isScrollControlled: true, builder: (_) => AsBookSheet(app: widget.app));
              if (id != null && id.isNotEmpty) widget.onOpen(id);
              await _load();
            }),
        const SizedBox(height: 8),
        Wrap(spacing: 6, children: [
          for (final (k, t) in const [('open', 'Khule'), ('done', 'Poore'), ('cancelled', 'Radd')])
            ChoiceChip(
                label: Text(t),
                selected: _filter == k,
                onSelected: (_) {
                  setState(() => _filter = k);
                  _load();
                }),
        ]),
        const SizedBox(height: 8),
        for (final v in _v)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => widget.onOpen(_s(v['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text('${_s(v['number'])} · ${_s(_map(v['customer'])['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_s(v['status'])),
                  ]),
                  Text('${_s(v['when'])} · ${_s(_map(v['tech'])['name'])} · ${_s(_map(v['unit'])['label'])} · ${_s(_map(v['customer'])['area'])}',
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            ),
          ),
      ]);
}

/// Pick a machine -> free slots (grouped by area) -> book. Returns the visit id.
class AsBookSheet extends StatefulWidget {
  const AsBookSheet({super.key, required this.app, this.unitId});
  final Santosh app;
  final String? unitId;
  @override
  State<AsBookSheet> createState() => _AsBookSheetState();
}

class _AsBookSheetState extends State<AsBookSheet> {
  final _q = TextEditingController();
  final _problem = TextEditingController();
  List<Map<String, dynamic>> _units = const [];
  String? _unit;
  Map<String, dynamic>? _slots;
  String _kind = 'service';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _unit = widget.unitId;
    if (_unit != null) _loadSlots();
  }

  @override
  void dispose() {
    _q.dispose();
    _problem.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    try {
      final r = _map(await _call(widget.app, 'GET', '/api/aftersales/units', query: {'q': _q.text.trim()}));
      if (mounted) setState(() => _units = _list(r['units']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _loadSlots() async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'GET', '/api/aftersales/slots', query: {'unit': _unit!, 'days': '7'}));
      if (mounted) setState(() => _slots = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _book(Map<String, dynamic> slot, {bool force = false}) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/aftersales/visits', body: {
        'unit': _unit,
        'start': slot['start'],
        'tech': slot['tech_id'],
        'kind': _kind,
        'problem': _problem.text.trim(),
        if (force) 'force': true,
      }));
      if (!mounted) return;
      _snack(context, _s(r['say']));
      Navigator.pop(context, _s(_map(r['visit'])['id']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Naya visit', style: display(17)),
            const SizedBox(height: 8),
            if (_unit == null) ...[
              TextField(
                controller: _q,
                decoration: const InputDecoration(hintText: 'Graahak / mobile / serial', prefixIcon: Icon(Icons.search_rounded)),
                onSubmitted: (_) => _search(),
              ),
              for (final u in _units.take(12))
                ListTile(
                  dense: true,
                  title: Text('${_s(_map(u['customer'])['name'])} · ${_s(u['label'])} ${_s(u['brand'])}'),
                  subtitle: Text('${_s(_map(u['customer'])['area'])} · due ${_s(u['next_due'])}'),
                  onTap: () {
                    setState(() => _unit = _s(u['id']));
                    _loadSlots();
                  },
                ),
            ] else ...[
              Wrap(spacing: 6, children: [
                for (final (k, t) in const [('service', 'Service'), ('repair', 'Repair'), ('install', 'Install'), ('amc', 'AMC visit'), ('warranty', 'Warranty')])
                  ChoiceChip(label: Text(t), selected: _kind == k, onSelected: (_) => setState(() => _kind = k)),
              ]),
              TextField(controller: _problem, decoration: const InputDecoration(labelText: 'Shikayat (ho to)')),
              const SizedBox(height: 8),
              if (_busy) const LinearProgressIndicator(),
              if (_slots != null) ...[
                Text(_s(_slots!['say']), style: const TextStyle(fontSize: 12.5)),
                if (_s(_slots!['note']).isNotEmpty) Text(_s(_slots!['note']), style: const TextStyle(fontSize: 12, color: C.warn)),
                const SizedBox(height: 6),
                for (final sl in _list(_slots!['slots']))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Press(
                      onTap: _busy ? null : () => _book(sl),
                      child: Glass(
                        padding: const EdgeInsets.all(10),
                        child: Row(children: [
                          const Icon(Icons.schedule_rounded, color: C.accent, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${_s(sl['start'])} · ${_s(sl['tech'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                            Text(_s(sl['why']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
                          ])),
                        ]),
                      ),
                    ),
                  ),
                TextButton(
                    onPressed: _busy
                        ? null
                        : () async {
                            final f = await _form(context, 'Apna samay', const [('start', 'Samay (25-10-2026 11:00 / kal 4 baje)'), ('tech', 'Technician (naam)')]);
                            if (f != null && f['start'] != null) await _book({'start': f['start'], 'tech_id': f['tech'] ?? ''});
                          },
                    child: const Text('Apna samay likho')),
              ],
            ],
          ]),
        ),
      );
}

/// One machine: details, history, book, AMC.
class AsUnitPage extends StatefulWidget {
  const AsUnitPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AsUnitPage> createState() => _AsUnitPageState();
}

class _AsUnitPageState extends State<AsUnitPage> {
  Map<String, dynamic>? _u;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final u = _map(await _call(widget.app, 'GET', '/api/aftersales/units/${widget.id}'));
      if (mounted) setState(() => _u = u);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _amc() async {
    final f = await _form(context, 'AMC likho', const [
      ('plan', 'comprehensive (part + labour) / non_comprehensive'),
      ('start', 'Shuru (dd-mm-yyyy)'),
      ('months', 'Mahine'),
      ('visits', 'Visit (saal mein)'),
      ('price', 'Daam (₹)'),
    ]);
    if (f == null) return;
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/aftersales/units/${widget.id}/amc', body: {
        ...f,
        for (final k in ['months', 'visits', 'price']) if (f[k] != null) k: _n(f[k]),
      }));
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final u = _u;
    final c = _map(u?['customer']);
    final amc = _map(u?['amc']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(u == null ? 'Machine' : '${_s(u['label'])} · ${_s(c['name'])}')),
      body: Aurora(
        child: u == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(u['brand'])} ${_s(u['model'])} · Sr ${_s(u['serial']).isEmpty ? '-' : _s(u['serial'])}',
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text('${_s(c['name'])} · ${_s(c['phone'])} · ${_s(c['area'])} ${_s(c['pincode'])}', style: const TextStyle(color: C.muted)),
                    const SizedBox(height: 6),
                    Text('Install ${_s(u['installed_on'])} · warranty ${_s(u['warranty_until'])}${u['in_warranty'] == true ? ' (chal rahi)' : ''}'),
                    if (_s(u['warranty_note']).isNotEmpty) Text(_s(u['warranty_note']), style: const TextStyle(fontSize: 12, color: C.warn)),
                    if (amc.isNotEmpty) Text('AMC ${_s(amc['plan'])} ${_s(amc['start'])} - ${_s(amc['until'])}${amc['active'] == true ? '' : ' (khatam)'}'),
                    Text('Pichhli service ${_s(u['last_service']).isEmpty ? '-' : _s(u['last_service'])} · agli ${_s(u['next_due'])} (${_s(u['due_why'])})',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ]),
                ),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GradientButton(
                      label: 'Visit book karo',
                      icon: Icons.event_available_rounded,
                      height: 46,
                      onTap: () async {
                        final id = await showModalBottomSheet<String>(
                            context: context, isScrollControlled: true, builder: (_) => AsBookSheet(app: widget.app, unitId: widget.id));
                        if (id != null && id.isNotEmpty && context.mounted) {
                          await Navigator.of(context).push(MaterialPageRoute(builder: (_) => AsVisitPage(app: widget.app, id: id)));
                        }
                        await _load();
                      }),
                  GlassButton(label: 'AMC likho', icon: Icons.verified_user_rounded, onTap: _amc),
                ]),
                const SizedBox(height: 12),
                Text('Visit', style: display(15)),
                for (final v in _list(u['visits']))
                  ListTile(
                    dense: true,
                    title: Text('${_s(v['number'])} · ${_s(v['kind'])} · ${_s(v['status'])}'),
                    subtitle: Text('${_s(v['start'])} · ${_s(v['tech'])}${(v['total'] ?? 0) > 0 ? ' · ${_rs(v['total'])}' : ''}'),
                    onTap: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => AsVisitPage(app: widget.app, id: _s(v['id']))))
                        .then((_) => _load()),
                  ),
                if (_list(u['claims']).isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text('Claim', style: display(15)),
                  for (final c2 in _list(u['claims'])) Text('• ${_s(c2['number'])} ${_s(c2['part'])}: ${_s(c2['status'])}'),
                ],
              ]),
      ),
    );
  }
}

/// One visit: job card, kaam poora (checklist / readings / parts), photos, customer sign, charge (her tap), report.
class AsVisitPage extends StatefulWidget {
  const AsVisitPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AsVisitPage> createState() => _AsVisitPageState();
}

class _AsVisitPageState extends State<AsVisitPage> {
  Map<String, dynamic>? _v;
  Map<String, dynamic>? _card;
  final Map<String, String> _marks = {};
  final Map<String, TextEditingController> _read = {};
  final _parts = TextEditingController();
  final _labour = TextEditingController();
  final _notes = TextEditingController();
  final _signedBy = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _read.values) {
      c.dispose();
    }
    _parts.dispose();
    _labour.dispose();
    _notes.dispose();
    _signedBy.dispose();
    super.dispose();
  }

  String get _vid => _s(_v?['id']).isEmpty ? widget.id : _s(_v?['id']);

  Future<void> _load() async {
    try {
      final v = _map(await _call(widget.app, 'GET', '/api/aftersales/visits/${widget.id}'));
      Map<String, dynamic>? card;
      if (v['status'] == 'booked' || v['status'] == 'on_way') {
        card = _map(await _call(widget.app, 'POST', '/api/aftersales/visits/${widget.id}/job_card', body: const {}));
      }
      if (!mounted) return;
      setState(() {
        _v = v;
        _card = card;
        for (final k in ((card?['readings'] as List?) ?? const [])) {
          _read.putIfAbsent('$k', () => TextEditingController());
        }
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _act(String action, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/aftersales/visits/$_vid/$action', body: body));
      if (mounted) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _photo(ImageSource src, String kind) async {
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 75, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      await _act('photo', {'kind': kind, 'data_b64': base64Encode(bytes)});
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _sign() async {
    final png = await showDialog<Uint8List>(context: context, builder: (_) => const _SignatureDialog());
    if (png == null) return;
    await _act('photo', {'kind': 'signature', 'data_b64': base64Encode(png)});
  }

  List<Map<String, dynamic>> _partList() {
    // "Sediment filter 250, Membrane x1 1900" -> [{name, qty, price}]
    final out = <Map<String, dynamic>>[];
    for (final raw in _parts.text.split(RegExp(r'[,\n]'))) {
      final t = raw.trim();
      if (t.isEmpty) continue;
      final m = RegExp(r'^(.*?)(?:\s*x\s*(\d+))?(?:\s+₹?\s*(\d+(?:\.\d+)?))?$', caseSensitive: false).firstMatch(t);
      final name = (m?.group(1) ?? t).trim();
      if (name.isEmpty) continue;
      out.add({
        'name': name,
        if (m?.group(2) != null) 'qty': int.tryParse(m!.group(2)!) ?? 1,
        if (m?.group(3) != null) 'price': double.tryParse(m!.group(3)!),
      });
    }
    return out;
  }

  Future<void> _done() async {
    await _act('done', {
      'checklist': {for (final e in _marks.entries) e.key: e.value},
      'readings': {for (final e in _read.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()},
      'parts': _partList(),
      if (_n(_labour.text) != null) 'labour': _n(_labour.text),
      'notes': _notes.text.trim(),
      'signed_by': _signedBy.text.trim(),
    });
  }

  Widget _open(Map<String, dynamic> v) {
    final card = _card ?? const {};
    final items = List<String>.from(((card['checklist'] as List?) ?? const []).map((e) => '$e'));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: SelectableText(_s(card['text']), style: const TextStyle(fontSize: 12.5, height: 1.4))),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        if (_s(card['wa_link']).isNotEmpty)
          GlassButton(label: 'Technician ko bhejo', icon: Icons.send_rounded, onTap: () => Native.openExternal(url: _s(card['wa_link']))),
        GlassButton(label: 'Raste mein', icon: Icons.directions_bike_rounded, onTap: _busy ? null : () => _act('on_way', const {})),
        GlassButton(
            label: 'Samay badlo',
            icon: Icons.edit_calendar_rounded,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Naya samay', const [('start', 'Samay (25-10-2026 11:00 / kal 4 baje)'), ('tech', 'Technician (khaali = wahi)')]);
                    if (f != null && f['start'] != null) await _act('reschedule', f);
                  }),
        GlassButton(label: 'Radd', icon: Icons.close_rounded, color: C.bad, onTap: _busy ? null : () => _act('cancel', const {})),
      ]),
      const SizedBox(height: 12),
      Text('Kaam poora likho', style: display(15)),
      for (final it in items)
        Row(children: [
          Expanded(child: Text(it, style: const TextStyle(fontSize: 13))),
          for (final (k, t) in const [('ok', 'OK'), ('not_ok', 'Kharab'), ('na', 'N/A')])
            Padding(
              padding: const EdgeInsets.only(left: 4),
              child: ChoiceChip(
                  label: Text(t, style: const TextStyle(fontSize: 11)),
                  selected: _marks[it] == k,
                  onSelected: (_) => setState(() => _marks[it] = k)),
            ),
        ]),
      for (final e in _read.entries)
        TextField(controller: e.value, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: e.key.replaceAll('_', ' '))),
      TextField(controller: _parts, decoration: const InputDecoration(labelText: 'Part (comma se, daam ho to: "Sediment filter 250")')),
      TextField(controller: _labour, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Labour (₹, khaali = list se)')),
      TextField(controller: _notes, maxLines: 2, decoration: const InputDecoration(labelText: 'Note')),
      TextField(controller: _signedBy, decoration: const InputDecoration(labelText: 'Sign karne wale ka naam')),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Photo (camera)', icon: Icons.photo_camera_rounded, onTap: _busy ? null : () => _photo(ImageSource.camera, 'work')),
        GlassButton(label: 'Gallery', icon: Icons.photo_library_rounded, onTap: _busy ? null : () => _photo(ImageSource.gallery, 'work')),
        GlassButton(label: v['signed'] == true ? 'Sign liya ✓' : 'Graahak ka sign', icon: Icons.draw_rounded, onTap: _busy ? null : _sign),
      ]),
      Text('${((v['photos'] as List?) ?? const []).length} photo', style: const TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 10),
      GradientButton(label: 'Kaam poora', icon: Icons.task_alt_rounded, onTap: _busy ? null : _done),
    ]);
  }

  Widget _closed(Map<String, dynamic> v) {
    final ch = _map(v['charge']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Poora: ${_s(v['done_on'])} · ${_s(_map(v['cover'])['say'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final e in _map(v['checklist']).entries) Text('${e.value == 'ok' ? '✓' : e.value == 'na' ? '–' : '✗'} ${e.key}', style: const TextStyle(fontSize: 12.5)),
          for (final e in _map(v['readings']).entries) Text('${e.key.replaceAll('_', ' ')}: ${e.value}', style: const TextStyle(fontSize: 12.5)),
          for (final p in _list(v['parts'])) Text('Part: ${_s(p['name'])} x${p['qty']}', style: const TextStyle(fontSize: 12.5)),
          if (_s(v['notes']).isNotEmpty) Text(_s(v['notes']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
          Text('${((v['photos'] as List?) ?? const []).length} photo · ${v['signed'] == true ? 'sign liya' : 'sign nahi'}', style: const TextStyle(fontSize: 12)),
        ]),
      ),
      const SizedBox(height: 8),
      if (ch['status'] == 'pending' || ch['status'] == 'needs_price' || ch['status'] == 'approved')
        AftersalesChargeCard(
            key: ValueKey('ch$_vid${ch['status']}${ch['total']}'),
            app: widget.app,
            data: {
              'visit_id': _vid,
              'number': v['number'],
              'customer': _map(v['customer'])['name'],
              'label': _map(v['unit'])['label'],
              ...ch,
            },
            onDone: _load),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GradientButton(
            label: 'Report + message',
            icon: Icons.picture_as_pdf_rounded,
            height: 46,
            onTap: _busy
                ? null
                : () async {
                    final r = await _act('report', const {});
                    final m = _map(r?['message']);
                    if (m.isNotEmpty && mounted) {
                      await showModalBottomSheet<void>(
                          context: context,
                          builder: (_) => Padding(padding: const EdgeInsets.all(16), child: AftersalesMessageTile(app: widget.app, m: m)));
                    }
                  }),
        if (ch['status'] == 'approved' && ((ch['paid'] ?? 0) as num) < ((ch['total'] ?? 0) as num))
          GlassButton(
              label: 'Paisa mila',
              icon: Icons.payments_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form(context, 'Kitna mila', const [('amount', 'Raqam (khaali = poora)'), ('how', 'Kaise (cash / UPI)')]);
                      if (f != null) await _act('paid', {if (_n(f['amount']) != null) 'amount': _n(f['amount']), 'how': f['how'] ?? ''});
                    }),
        GlassButton(
            label: 'Warranty claim',
            icon: Icons.assignment_return_rounded,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Brand se claim', const [('part', 'Part (khaali = jo badla)'), ('fault', 'Kya kharab tha'), ('brand_ref', 'Brand complaint no.')]);
                    if (f != null) await _act('claim', f);
                  }),
      ]),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(v == null ? 'Visit' : '${_s(v['number'])} · ${_s(_map(v['customer'])['name'])}')),
      body: Aurora(
        child: v == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Text('${_s(v['when'])} · ${_s(_map(v['tech'])['name'])} · ${_s(_map(v['unit'])['label'])} · ${_s(v['status'])}',
                    style: const TextStyle(color: C.muted)),
                const SizedBox(height: 8),
                if (_busy) const LinearProgressIndicator(),
                if (v['status'] == 'booked' || v['status'] == 'on_way') _open(v) else if (v['status'] == 'done') _closed(v) else Text('Visit ${_s(v['status'])}.'),
              ]),
      ),
    );
  }
}

/// Finger signature -> PNG bytes.
class _SignatureDialog extends StatefulWidget {
  const _SignatureDialog();
  @override
  State<_SignatureDialog> createState() => _SignatureDialogState();
}

class _SignatureDialogState extends State<_SignatureDialog> {
  final List<List<Offset>> _strokes = [];
  static const _size = Size(320, 160);

  Future<void> _save() async {
    if (_strokes.isEmpty) return;
    final rec = ui.PictureRecorder();
    final canvas = Canvas(rec);
    canvas.drawRect(Offset.zero & _size, Paint()..color = Colors.white);
    _paint(canvas);
    final img = await rec.endRecording().toImage(_size.width.toInt(), _size.height.toInt());
    final data = await img.toByteData(format: ui.ImageByteFormat.png);
    if (!mounted || data == null) return;
    Navigator.pop(context, data.buffer.asUint8List());
  }

  void _paint(Canvas canvas) {
    final p = Paint()
      ..color = Colors.black
      ..strokeWidth = 2.6
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    for (final s in _strokes) {
      if (s.length == 1) canvas.drawCircle(s.first, 1.3, p..style = PaintingStyle.fill);
      final path = Path();
      for (var i = 0; i < s.length; i++) {
        if (i == 0) {
          path.moveTo(s[i].dx, s[i].dy);
        } else {
          path.lineTo(s[i].dx, s[i].dy);
        }
      }
      canvas.drawPath(path, p..style = PaintingStyle.stroke);
    }
  }

  Offset _clamp(Offset o) => Offset(o.dx.clamp(0.0, _size.width).toDouble(), o.dy.clamp(0.0, _size.height).toDouble());

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Graahak ka sign'),
        content: Container(
          width: _size.width,
          height: _size.height,
          color: Colors.white,
          child: GestureDetector(
            onPanStart: (d) => setState(() => _strokes.add([_clamp(d.localPosition)])),
            onPanUpdate: (d) => setState(() => _strokes.last.add(_clamp(d.localPosition))),
            child: CustomPaint(size: _size, painter: _SigPainter(this)),
          ),
        ),
        actions: [
          TextButton(onPressed: () => setState(_strokes.clear), child: const Text('Mitao')),
          TextButton(onPressed: _save, child: const Text('Rakho')),
        ],
      );
}

class _SigPainter extends CustomPainter {
  _SigPainter(this.s);
  final _SignatureDialogState s;
  @override
  void paint(Canvas canvas, Size size) => s._paint(canvas);
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// Her settings: business, prices, hours, travel time, schedules per product.
class AsSettingsPage extends StatelessWidget {
  const AsSettingsPage({super.key, required this.app, required this.data, required this.schedules});
  final Santosh app;
  final Map<String, dynamic> data;
  final List<Map<String, dynamic>> schedules;

  @override
  Widget build(BuildContext context) {
    final prices = _map(data['prices']);
    Future<void> save(Map<String, dynamic> body) async {
      try {
        await _call(app, 'POST', '/api/aftersales/settings', body: body);
        if (context.mounted) _snack(context, 'Save ho gaya');
      } catch (e) {
        if (context.mounted) _snack(context, '$e');
      }
    }

    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('After-sales niyam')),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(data['business']).isEmpty ? '(dukaan ka naam nahi)' : _s(data['business']), style: const TextStyle(fontWeight: FontWeight.w800)),
              Text('Samay ${_s(data['day_start'])}-${_s(data['day_end'])} · aane-jaane ${data['travel_minutes']} min · reminder ${data['remind_days']} din pehle',
                  style: const TextStyle(color: C.muted, fontSize: 12.5)),
              Text('Visit charge: ${prices['visit'] == null ? 'nahi likha' : _rs(prices['visit'])}${data['gst_on'] == true ? ' · GST ${data['gst_pct']}%' : ''}',
                  style: const TextStyle(fontSize: 12.5)),
            ]),
          ),
          const SizedBox(height: 8),
          GlassButton(
              label: 'Badlo',
              icon: Icons.edit_rounded,
              onTap: () async {
                final f = await _form(context, 'Niyam', const [
                  ('business', 'Dukaan / company ka naam'),
                  ('phone', 'Phone'),
                  ('address', 'Pata'),
                  ('visit', 'Visit charge (₹)'),
                  ('day_start', 'Kaam shuru (09:30)'),
                  ('day_end', 'Kaam band (18:30)'),
                  ('travel_minutes', 'Do area ke beech (min)'),
                  ('remind_days', 'Reminder kitne din pehle'),
                  ('terms', 'Report par shartein'),
                ], initial: {
                  'business': _s(data['business']),
                  'phone': _s(data['phone']),
                  'address': _s(data['address']),
                  'visit': _s(prices['visit']),
                  'day_start': _s(data['day_start']),
                  'day_end': _s(data['day_end']),
                  'travel_minutes': _s(data['travel_minutes']),
                  'remind_days': _s(data['remind_days']),
                  'terms': _s(data['terms']),
                });
                if (f == null) return;
                await save({
                  for (final k in ['business', 'phone', 'address', 'day_start', 'day_end', 'terms']) if (f[k] != null) k: f[k],
                  if (_n(f['travel_minutes']) != null) 'travel_minutes': _n(f['travel_minutes']),
                  if (_n(f['remind_days']) != null) 'remind_days': _n(f['remind_days']),
                  if (_n(f['visit']) != null) 'prices': {'visit': _n(f['visit'])},
                });
              }),
          const SizedBox(height: 12),
          Text('Service kitne din mein (har product)', style: display(15)),
          for (final sc in schedules)
            ListTile(
              dense: true,
              title: Text(_s(sc['label'])),
              subtitle: Text('Har ${sc['months']} mahine${sc['usage'] != null ? ' ya ${sc['usage']} ${_s(sc['usage_unit'])}' : ''}${sc['mine'] == true ? ' (aapka)' : ''}'),
              trailing: const Icon(Icons.edit_rounded, size: 18),
              onTap: () async {
                final f = await _form(context, _s(sc['label']), const [('months', 'Har kitne mahine'), ('usage', 'Ya kitne km / ghante (ho to)')],
                    initial: {'months': _s(sc['months'])});
                if (f == null) return;
                try {
                  final r = _map(await _call(app, 'POST', '/api/aftersales/schedules',
                      body: {'ptype': sc['ptype'], 'months': _n(f['months']), if (_n(f['usage']) != null) 'usage': _n(f['usage'])}));
                  if (context.mounted) _snack(context, _s(r['say']));
                } catch (e) {
                  if (context.mounted) _snack(context, '$e');
                }
              },
            ),
        ]),
      ),
    );
  }
}

/// WhatsApp templates (Meta): status + "Meta ko bhejo" (her tap).
class AsTemplatesPage extends StatefulWidget {
  const AsTemplatesPage({super.key, required this.app});
  final Santosh app;
  @override
  State<AsTemplatesPage> createState() => _AsTemplatesPageState();
}

class _AsTemplatesPageState extends State<AsTemplatesPage> {
  List<Map<String, dynamic>> _t = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = _map(await _call(widget.app, 'GET', '/api/aftersales/templates'));
      if (mounted) setState(() => _t = _list(r['templates']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('WhatsApp templates')),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
            const Text(
                'Business number se 24 ghante ke baad sirf Meta-approved template jaata hai. Service / visit / report = UTILITY; '
                'AMC renewal = MARKETING (sirf jinhone offers ki haan di).',
                style: TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 8),
            for (final t in _t)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Glass(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text(_s(t['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                      Pill(_s(t['category'])),
                      const SizedBox(width: 4),
                      Pill(_s(t['status']), fg: t['status'] == 'APPROVED' ? C.ok : C.chip),
                    ]),
                    Text(_s(t['body']), style: const TextStyle(fontSize: 12.5)),
                    if (_s(t['reason']).isNotEmpty) Text(_s(t['reason']), style: const TextStyle(color: C.bad, fontSize: 12)),
                    if (t['status'] == 'NOT_SUBMITTED' || t['status'] == 'REJECTED')
                      TextButton(
                          onPressed: () async {
                            try {
                              final r = _map(await _call(widget.app, 'POST', '/api/aftersales/templates/${t['name']}/submit', body: const {}));
                              if (mounted) _snack(context, _s(r['say']));
                              await _load();
                            } catch (e) {
                              if (mounted) _snack(context, '$e');
                            }
                          },
                          child: const Text('Meta ko bhejo')),
                  ]),
                ),
              ),
          ]),
        ),
      );
}

// ---------------------------------------------------------------- chat / call cards

/// `aftersales_charge`: a charge to the customer waits for HER tap (Haan / total badlo / Mana).
class AftersalesChargeCard extends StatefulWidget {
  const AftersalesChargeCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<AftersalesChargeCard> createState() => _AftersalesChargeCardState();
}

class _AftersalesChargeCardState extends State<AftersalesChargeCard> {
  bool _busy = false;
  late String _status = _s(widget.data['status']);
  late num _total = (widget.data['total'] is num) ? widget.data['total'] as num : 0;

  Future<void> _decide(bool yes, [double? total]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', '/api/aftersales/visits/${widget.data['visit_id']}/charge', body: {
        'yes': yes,
        if (total != null) 'total': total,
        if (_s(widget.data['hash']).isNotEmpty) 'hash': widget.data['hash'],
      }));
      final ch = _map(r['charge']);
      if (mounted) {
        setState(() {
          _status = _s(ch['status']);
          _total = (ch['total'] is num) ? ch['total'] as num : _total;
        });
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
    final d = widget.data;
    final waiting = _status == 'pending' || _status == 'needs_price';
    return Glass(
      border: waiting ? C.warn : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.request_quote_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(d['number'])} · ${_s(d['customer'])} · ${_s(d['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(waiting ? 'haan chahiye' : _status),
        ]),
        if (_s(d['cover']).isNotEmpty) Text(_s(d['cover']), style: const TextStyle(fontSize: 12, color: C.muted)),
        for (final l in _list(d['lines']))
          Row(children: [
            Expanded(child: Text(_s(l['what']), style: const TextStyle(fontSize: 12.5))),
            Text(l['amount'] == null ? '[daam?]' : _rs(l['amount']), style: TextStyle(fontSize: 12.5, color: l['amount'] == null ? C.warn : C.ink)),
          ]),
        if ((d['gst'] ?? 0) is num && (d['gst'] ?? 0) > 0) Text('GST ${_rs(d['gst'])}', style: const TextStyle(fontSize: 12.5)),
        Text('Total ${_rs(_total)}', style: const TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        if (waiting) ...[
          if (_status == 'pending')
            GradientButton(label: 'Haan, ${_rs(_total)} lena hai', icon: Icons.check_rounded, height: 46, onTap: _busy ? null : () => _decide(true)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(
                label: _status == 'needs_price' ? 'Total likho' : 'Total badlo',
                icon: Icons.edit_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Graahak se kitna', const [('total', 'Total (₹)')]);
                        final t = _n(f?['total']);
                        if (t != null) await _decide(true, t);
                      }),
            GlassButton(label: 'Mana (free)', icon: Icons.money_off_rounded, color: C.bad, onTap: _busy ? null : () => _decide(false)),
          ]),
        ],
      ]),
    );
  }
}

/// One draft message: WhatsApp from her phone / SMS / business WhatsApp (her tap) / "Bhej diya".
class AftersalesMessageTile extends StatefulWidget {
  const AftersalesMessageTile({super.key, required this.app, required this.m});
  final Santosh app;
  final Map<String, dynamic> m;
  @override
  State<AftersalesMessageTile> createState() => _AftersalesMessageTileState();
}

class _AftersalesMessageTileState extends State<AftersalesMessageTile> {
  late String _status = _s(widget.m['status']).isEmpty ? 'draft' : _s(widget.m['status']);
  bool _busy = false;

  Future<void> _post(String path, [Object? body]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await _call(widget.app, 'POST', path, body: body ?? const {}));
      if (mounted) {
        setState(() => _status = _s(r['status']).isEmpty ? _status : _s(r['status']));
        _snack(context, _s(r['say']));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.m;
    final id = _s(m['id']);
    return Glass(
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${_s(m['customer']).isEmpty ? _s(m['phone']) : _s(m['customer'])} · ${_s(m['kind'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
          Pill(_s(m['category']), fg: m['category'] == 'MARKETING' ? C.warn : C.chip),
          const SizedBox(width: 4),
          Pill(_status),
        ]),
        const SizedBox(height: 4),
        SelectableText(_s(m['text']), style: const TextStyle(fontSize: 12.5)),
        if (_status == 'draft') ...[
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            if (_s(m['wa_link']).isNotEmpty)
              GlassButton(label: 'WhatsApp', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: _s(m['wa_link']))),
            if (_s(m['sms_link']).isNotEmpty)
              GlassButton(label: 'SMS', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: _s(m['sms_link']))),
            GlassButton(label: 'Copy', icon: Icons.copy_rounded, height: 40, onTap: () => Clipboard.setData(ClipboardData(text: _s(m['text'])))),
            GlassButton(label: 'Bhej diya', icon: Icons.done_all_rounded, height: 40, onTap: _busy ? null : () => _post('/api/aftersales/messages/$id/sent')),
            GlassButton(
                label: 'Business WhatsApp',
                icon: Icons.storefront_rounded,
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        final via = await showDialog<String>(
                            context: context,
                            builder: (d) => SimpleDialog(title: const Text('Business number se'), children: [
                                  SimpleDialogOption(onPressed: () => Navigator.pop(d, 'template'), child: const Text('Approved template (kabhi bhi)')),
                                  SimpleDialogOption(onPressed: () => Navigator.pop(d, 'business'), child: const Text('Seedha message (24 ghante ke andar)')),
                                ]));
                        if (via != null) await _post('/api/aftersales/messages/$id/send', {'via': via});
                      }),
            TextButton(onPressed: _busy ? null : () => _post('/api/aftersales/messages/$id/skipped'), child: const Text('Nahi bhejna')),
          ]),
        ],
      ]),
    );
  }
}

/// `aftersales_reminders`: reminder drafts (service due / AMC) she sends.
class AftersalesRemindersCard extends StatelessWidget {
  const AftersalesRemindersCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final ms = _list(data['messages']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.notifications_active_rounded, color: C.accent),
        const SizedBox(width: 8),
        Expanded(child: Text(_s(data['say']).isEmpty ? '${ms.length} reminder draft' : _s(data['say']), style: const TextStyle(fontWeight: FontWeight.w800))),
      ]),
      const SizedBox(height: 6),
      for (final m in ms.take(15)) Padding(padding: const EdgeInsets.only(bottom: 6), child: AftersalesMessageTile(app: app, m: m)),
      if (ms.length > 15) Text('+${ms.length - 15} aur (After-sales > Aaj)', style: const TextStyle(color: C.muted, fontSize: 12)),
    ]);
  }
}

/// `aftersales_visit`: a visit booked / moved, with the customer confirmation draft.
class AftersalesVisitCard extends StatelessWidget {
  const AftersalesVisitCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final msg = _map(data['message']);
    final warns = List<String>.from(((data['warnings'] as List?) ?? const []).map((e) => '$e'));
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.event_available_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(data['number'])} · ${_s(data['customer'])} · ${_s(data['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        Text('${_s(data['when'])} · ${_s(data['tech'])}${_s(data['area']).isNotEmpty ? ' · ${_s(data['area'])}' : ''}', style: const TextStyle(color: C.muted)),
        for (final w in warns) Text(w, style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 6),
        if (msg['id'] != null) AftersalesMessageTile(app: app, m: msg),
        TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AsVisitPage(app: app, id: _s(data['visit_id'])))),
            child: const Text('Visit kholo')),
      ]),
    );
  }
}

/// `aftersales_report`: the visit report PDF is in chat (pc_file card); this card holds the customer message draft.
class AftersalesReportCard extends StatelessWidget {
  const AftersalesReportCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final msg = _map(data['message']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.picture_as_pdf_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Service report ${_s(data['number'])} · ${_s(data['customer'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        Text(_s(_map(data['file'])['name']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        if (msg['id'] != null) AftersalesMessageTile(app: app, m: msg),
      ]),
    );
  }
}

/// `aftersales_day`: the morning note.
class AftersalesDayCard extends StatelessWidget {
  const AftersalesDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          const Icon(Icons.home_repair_service_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['text']), style: const TextStyle(fontWeight: FontWeight.w700, height: 1.35))),
          IconButton(
              icon: const Icon(Icons.open_in_new_rounded, size: 18),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AftersalesScreen(app: app)))),
        ]),
      );
}
