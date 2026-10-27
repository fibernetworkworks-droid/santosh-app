/// Profile > Architect's assistant (Archassist Sahayak).
/// Aaj (her taps waiting, late RFIs, approvals expiring, unpaid invoices) · Projects (project file: plot + title papers, area
/// statement + zoning checks, drawing register + revisions, transmittals, approvals / NOCs + submission card, RFIs, minutes, fee +
/// invoices) · Consultants · Niyam (firm, CoA no., GSTIN, rule set). Issuing drawings, "submit karo" and invoices happen ONLY on
/// her tap here (invoices with her fingerprint once a phone key is set up). FSI checks are andaaza: rule book decides.
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

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _stColor(String st) => switch (st) {
      'fail' || 'refused' || 'rejected' => C.bad,
      'warn' || 'check' || 'needed' || 'query' || 'waiting' => C.warn,
      'ok' || 'granted' || 'issued' || 'paid' || 'approved' => C.ok,
      _ => C.chip,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(
                controller: c[k],
                decoration: InputDecoration(labelText: label),
                maxLines: (k == 'points' || k == 'question' || k == 'note' || k == 'site' || k == 'terms') ? 3 : 1),
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
  if (links.isEmpty) return;
  await showModalBottomSheet(
    context: context,
    backgroundColor: C.bgBottom,
    builder: (_) => Padding(
      padding: const EdgeInsets.all(16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(r['text']), style: const TextStyle(fontSize: 13)),
        const SizedBox(height: 10),
        for (final e in links.entries)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: GlassButton(
                label: switch (e.key) { 'whatsapp' => 'WhatsApp draft kholo', 'email' => 'Email draft kholo', 'upi' => 'UPI link', _ => e.key },
                icon: Icons.open_in_new_rounded,
                onTap: () => Native.openExternal(url: _s(e.value))),
          ),
        const Text('Hoola khud nahi bhejta: aap bhejiye.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    ),
  );
}

class ArchassistScreen extends StatefulWidget {
  const ArchassistScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ArchassistScreen> createState() => _ArchassistScreenState();
}

class _ArchassistScreenState extends State<ArchassistScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/archassist'));
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
      .push(MaterialPageRoute(builder: (_) => ArchProjectPage(app: widget.app, projectRef: ref)))
      .then((_) => _load());

  Future<void> _newProject() async {
    final f = await _form(context, 'Naya project', const [
      ('name', 'Project ka naam'),
      ('client', 'Client'),
      ('client_phone', 'Client ka mobile'),
      ('site', 'Site ka pata'),
      ('pin', 'PIN code'),
      ('city', 'Shehar'),
      ('area', 'Plot area (jaise 1000 sqm / 2400 sqft / 5 guntha)'),
      ('road_width_m', 'Saamne ki road (metre)'),
      ('survey_no', 'Survey / gat no.'),
      ('cts_no', 'CTS no.'),
    ], ok: 'Banao');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f};
    if (f['road_width_m'] != null) body['road_width_m'] = _n(f['road_width_m']);
    final r = await _run('POST', '/api/archassist/projects', body);
    if (r != null && _s(r['id']).isNotEmpty && mounted) _open(_s(r['id']));
  }

  Widget _today() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14.5, height: 1.4))),
      const SizedBox(height: 12),
      GradientButton(label: 'Naya project', icon: Icons.add_home_work_rounded, height: 46, onTap: _busy ? null : _newProject),
      const SizedBox(height: 12),
      for (final (key, title) in const [('waiting', 'AAPKI HAAN BAAKI'), ('rfi_late', 'RFI LATE'), ('expiring', 'APPROVAL KI TAREEKH'), ('unpaid', 'PAYMENT BAAKI')])
        if (_strs(day[key]).isNotEmpty) ...[
          Caption(title),
          for (final t in _strs(day[key])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
          const SizedBox(height: 8),
        ],
    ]);
  }

  Widget _projectsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya project', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newProject),
        const SizedBox(height: 12),
        for (final p in _list(_d?['projects']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _open(_s(p['id'])),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.architecture_rounded, color: C.accent, size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${_s(p['number'])} · ${_s(p['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_s(p['status']), fg: _s(p['status']) == 'active' ? C.ok : C.warn),
                  ]),
                  Text(
                      [
                        _s(p['client']),
                        _s(p['city']),
                        if (p['plot_area_sqm'] != null) '${p['plot_area_sqm']} sq m',
                        _s(p['ruleset_label']),
                      ].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (_strs(p['docs_missing']).isNotEmpty)
                    Text('Kaagaz baaki: ${_strs(p['docs_missing']).take(3).join(', ')}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
                ]),
              ),
            ),
          ),
        if (_list(_d?['projects']).isEmpty) const Text('Abhi koi project nahi.', style: TextStyle(color: C.muted)),
      ]);

  Future<void> _addConsultant() async {
    final f = await _form(context, 'Consultant', const [
      ('name', 'Naam'),
      ('kind', 'Kaun: structural / mep / electrical / plumbing / hvac / fire / landscape'),
      ('firm', 'Firm'),
      ('phone', 'Mobile'),
      ('email', 'Email'),
      ('licence', 'Licence no.'),
    ], ok: 'Save');
    if (f == null || (f['name'] ?? '').isEmpty) return;
    await _run('POST', '/api/archassist/consultants', f);
  }

  Widget _consultantsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Consultant jodo', icon: Icons.engineering_rounded, height: 46, onTap: _busy ? null : _addConsultant),
        const SizedBox(height: 12),
        for (final c in _list(_d?['consultants']))
          ListTile(
            leading: const Icon(Icons.person_rounded, color: C.accent),
            title: Text('${_s(c['name'])} · ${_s(c['kind_label'])}'),
            subtitle: Text([_s(c['firm']), _s(c['phone']), _s(c['email'])].where((x) => x.isNotEmpty).join(' · ')),
          ),
      ]);

  Future<void> _editSettings() async {
    final st = _m(_d?['settings']);
    final f = await _form(context, 'Niyam / firm', const [
      ('firm', 'Firm ka naam'),
      ('architect', 'Architect ka naam'),
      ('coa_no', 'CoA registration no.'),
      ('coa_valid_to', 'CoA registration valid till (YYYY-MM-DD)'),
      ('gstin', 'GSTIN (ho to)'),
      ('address', 'Office address'),
      ('phone', 'Office mobile'),
      ('email', 'Email'),
      ('upi_id', 'UPI ID (invoice par)'),
      ('ruleset', 'Rule set: udcpr / udcpr_congested / dcpr_suburbs / dcpr_island / custom'),
      ('inv_prefix', 'Invoice prefix'),
      ('morning_time', 'Subah ka note (HH:MM)'),
      ('terms', 'Invoice terms'),
    ], ok: 'Save', initial: {for (final k in ['firm', 'architect', 'coa_no', 'coa_valid_to', 'gstin', 'address', 'phone', 'email', 'upi_id', 'ruleset', 'inv_prefix', 'morning_time', 'terms']) k: _s(st[k])});
    if (f == null) return;
    await _run('PUT', '/api/archassist/settings', f);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['firm']).isEmpty ? 'Firm ka naam daaliye' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('CoA: ${_s(st['coa_no']).isEmpty ? '—' : _s(st['coa_no'])} · GSTIN: ${_s(st['gstin']).isEmpty ? '—' : _s(st['gstin'])}',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('Rule set: ${_s(_m(st['rulesets'])[_s(st['ruleset'])])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: _editSettings),
        ]),
      ),
      const SizedBox(height: 12),
      const Caption('FEE STAGES'),
      for (final x in _list(st['fee_stages'])) Text('• ${_s(x['label'])}: ${_s(x['pct'])}%', style: const TextStyle(fontSize: 13)),
      if (st['fee_starter'] == true)
        const Text('CoA reference wala starter split; aapke agreement ke hisaab se project mein badaliye.', style: TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 12),
      const Caption('HOOLA KABHI NAHI'),
      for (final t in _strs(_d?['never'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $t', style: const TextStyle(fontSize: 13))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Aaj', 'Projects', 'Consultants', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text("${widget.app.aName} · Architect's assistant"),
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
                  child: switch (_tab) { 0 => _today(), 1 => _projectsTab(), 2 => _consultantsTab(), _ => _rulesTab() },
                ),
        ),
      ]),
    );
  }
}

/// One project file: plot + papers, area statement, drawings, transmittals, approvals, RFIs, minutes, fee + invoices.
class ArchProjectPage extends StatefulWidget {
  const ArchProjectPage({super.key, required this.app, required this.projectRef});
  final Santosh app;
  final String projectRef;
  @override
  State<ArchProjectPage> createState() => _ArchProjectPageState();
}

class _ArchProjectPageState extends State<ArchProjectPage> {
  Map<String, dynamic>? _p;
  int _tab = 0;
  bool _busy = false;

  String get _ref => _s(_p?['id']).isEmpty ? widget.projectRef : _s(_p?['id']);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = _m(await widget.app.api!.call('GET', '/api/archassist/projects/${Uri.encodeComponent(widget.projectRef)}'));
      if (mounted) setState(() => _p = p);
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

  Future<String?> _pickFile() async {
    final conv = widget.app.conversationId;
    if (conv == null) {
      _snack(context, 'Pehle chat khulne dijiye.');
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

  // ---- plot + papers
  Future<void> _editPlot() async {
    final plot = _m(_p?['plot']);
    final f = await _form(context, 'Plot', const [
      ('area', 'Plot area (sqm / sqft / guntha)'),
      ('road_width_m', 'Road width (m)'),
      ('road_widening_sqm', 'Road widening mein jaane wala (sq m)'),
      ('reservation_sqm', 'Reservation (sq m)'),
      ('survey_no', 'Survey / gat no.'),
      ('cts_no', 'CTS no.'),
      ('ruleset', 'Rule set (udcpr / dcpr_suburbs / ...)'),
      ('authority', 'Authority (maha_bpms / mcgm_autodcr / pmrda / midc_bpams)'),
      ('rera_no', 'RERA no. (ho to)'),
      ('client_gstin', 'Client GSTIN (ho to)'),
    ], ok: 'Save', initial: {
      'area': _s(plot['area_sqm']),
      'road_width_m': _s(plot['road_width_m']),
      'survey_no': _s(plot['survey_no']),
      'cts_no': _s(plot['cts_no']),
      'ruleset': _s(_p?['ruleset']),
      'authority': _s(_p?['authority']),
      'rera_no': _s(_p?['rera_no']),
    });
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['road_width_m', 'road_widening_sqm', 'reservation_sqm']) {
      if (f[k] != null) body[k] = _n(f[k]);
    }
    await _run('PATCH', '/api/archassist/projects/$_ref', body);
  }

  Future<void> _flag(String key, bool v) => _run('PATCH', '/api/archassist/projects/$_ref', {key: v});

  Future<void> _docTap(Map<String, dynamic> d) async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(title: Text(_s(d['label']))),
        ListTile(leading: const Icon(Icons.check_rounded, color: C.ok), title: const Text('Mil gaya'), onTap: () => Navigator.pop(c, 'have')),
        ListTile(leading: const Icon(Icons.attach_file_rounded), title: const Text('File jodo (mil gaya)'), onTap: () => Navigator.pop(c, 'file')),
        ListTile(leading: const Icon(Icons.hourglass_empty_rounded, color: C.warn), title: const Text('Baaki'), onTap: () => Navigator.pop(c, 'missing')),
        ListTile(leading: const Icon(Icons.block_rounded), title: const Text('Zaroori nahi'), onTap: () => Navigator.pop(c, 'na')),
      ]),
    );
    if (choice == null) return;
    String fid = '';
    var state = choice;
    if (choice == 'file') {
      fid = await _pickFile() ?? '';
      if (fid.isEmpty) return;
      state = 'have';
    }
    await _run('POST', '/api/archassist/projects/$_ref/docs', {'key': d['key'], 'state': state, 'file_id': fid});
  }

  Widget _plotTab() {
    final plot = _m(_p?['plot']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_s(_p?['client'])} · ${_s(_p?['site'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
          Text(
              [
                if (plot['area_sqm'] != null) 'Plot ${plot['area_sqm']} sq m',
                if (plot['road_width_m'] != null) 'Road ${plot['road_width_m']} m',
                if (_s(plot['survey_no']).isNotEmpty) 'S.No ${plot['survey_no']}',
                if (_s(plot['cts_no']).isNotEmpty) 'CTS ${plot['cts_no']}',
              ].join(' · '),
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text('${_s(_p?['ruleset_label'])} · ${_s(_p?['authority_label'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Plot badlo', icon: Icons.edit_rounded, onTap: _editPlot),
        ]),
      ),
      const SizedBox(height: 8),
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final (k, label) in const [('trees', 'Ped hain'), ('near_airport', 'Airport ke paas'), ('heritage', 'Heritage'), ('coastal', 'CRZ / samundar'), ('railway', 'Railway paas'), ('highway', 'Highway paas'), ('promoter', 'Bechne ke liye (RERA)')])
          FilterChip(label: Text(label), selected: plot[k] == true, onSelected: (v) => _flag(k, v)),
      ]),
      const SizedBox(height: 12),
      const Caption('KAAGAZ (7/12, PROPERTY CARD, TITLE...)'),
      for (final d in _list(_p?['docs']))
        ListTile(
          dense: true,
          leading: Icon(
              switch (_s(d['state'])) { 'have' => Icons.check_circle_rounded, 'na' => Icons.remove_circle_outline_rounded, _ => Icons.radio_button_unchecked_rounded },
              color: switch (_s(d['state'])) { 'have' => C.ok, 'na' => C.faint, _ => C.warn }),
          title: Text(_s(d['label'])),
          subtitle: _s(d['file_id']).isEmpty ? null : const Text('File judi'),
          onTap: () => _docTap(d),
        ),
    ]);
  }

  // ---- area statement
  Future<void> _area() async {
    final prop = _m(_p?['proposal']);
    final f = await _form(context, 'Area statement (aapke number)', const [
      ('bua_sqm', 'Proposed total built-up (sq m)'),
      ('height_m', 'Building height (m)'),
      ('front_m', 'Front margin (m)'),
      ('side_m', 'Side margin (m)'),
      ('rear_m', 'Rear margin (m)'),
      ('units', 'Flats / units'),
      ('parking', 'Parking (kitni)'),
      ('basic', 'Apna basic FSI (khaali = table)'),
      ('premium', 'Apna premium FSI (khaali = table)'),
      ('tdr', 'Apna TDR (khaali = table)'),
      ('parking_per_unit', 'Parking per unit (aapki table se)'),
    ], ok: 'Jaancho', initial: {for (final k in ['bua_sqm', 'height_m', 'front_m', 'side_m', 'rear_m', 'units', 'parking']) k: _s(prop[k])});
    if (f == null) return;
    final proposal = <String, dynamic>{};
    final overrides = <String, dynamic>{};
    for (final k in ['bua_sqm', 'height_m', 'front_m', 'side_m', 'rear_m', 'units', 'parking']) {
      if (f[k] != null) proposal[k] = _n(f[k]);
    }
    for (final k in ['basic', 'premium', 'tdr', 'parking_per_unit']) {
      if (f[k] != null) overrides[k] = _n(f[k]);
    }
    await _run('POST', '/api/archassist/projects/$_ref/area', {'proposal': proposal, 'overrides': overrides});
  }

  Widget _areaTab() {
    final a = _m(_p?['area']);
    final st = _m(a['statement']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Area statement / FSI jaancho', icon: Icons.square_foot_rounded, height: 46, onTap: _busy ? null : _area),
      const SizedBox(height: 12),
      if (a.isNotEmpty) ArchAreaCard(app: widget.app, data: {'say': a['say'], 'checks': a['checks'], 'statement': st, 'project': _p?['number']}),
      if (a.isEmpty) const Text('Abhi area statement nahi bana.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 8),
      for (final n in _strs(a['notes'])) Text('• $n', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  // ---- drawings + transmittals
  Future<void> _addDrawing({Map<String, dynamic>? d}) async {
    final f = await _form(context, d == null ? 'Nayi sheet' : 'Nayi revision: ${_s(d['sheet'])}', [
      if (d == null) ('sheet', 'Sheet no. (A-101)'),
      if (d == null) ('title', 'Title'),
      if (d == null) ('scale', 'Scale (1:100)'),
      ('note', d == null ? 'Note (ho to)' : 'Kya badla'),
      ('status', 'Status: draft / for_approval / for_construction'),
    ], ok: 'Aage');
    if (f == null) return;
    final fid = await _pickFile();
    final body = <String, dynamic>{...f, 'file_id': fid ?? ''};
    if (d != null) {
      body['sheet'] = d['sheet'];
      body['revise'] = true;
    }
    await _run('POST', '/api/archassist/projects/$_ref/drawings', body);
  }

  Future<void> _transmittal() async {
    final sheets = _list(_p?['drawings']).where((d) => _s(d['status']) != 'superseded').map((d) => _s(d['sheet'])).toList();
    if (sheets.isEmpty) {
      _snack(context, 'Pehle drawing register mein sheets daaliye.');
      return;
    }
    final f = await _form(context, 'Transmittal', [
      ('to_kind', 'Kise: client / authority / consultant / contractor'),
      ('to_name', 'Naam'),
      ('to_contact', 'Mobile / email'),
      ('sheets', 'Sheets (comma se): ${sheets.join(', ')}'),
      ('purpose', 'for_approval / for_construction / for_information / for_submission'),
      ('note', 'Note'),
    ], ok: 'Card banao', initial: {'to_kind': 'client', 'to_name': _s(_p?['client']), 'sheets': sheets.join(', '), 'purpose': 'for_approval'});
    if (f == null) return;
    final body = <String, dynamic>{...f, 'sheets': (f['sheets'] ?? '').split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList()};
    final r = await _run('POST', '/api/archassist/projects/$_ref/transmittals', body);
    if (r != null && _s(r['id']).isNotEmpty && mounted) {
      await showModalBottomSheet(
        context: context,
        backgroundColor: C.bgBottom,
        isScrollControlled: true,
        builder: (_) => Padding(padding: const EdgeInsets.all(16), child: SingleChildScrollView(child: ArchTransmittalCard(app: widget.app, data: {'transmittal': r}))),
      );
      await _load();
    }
  }

  Widget _drawingsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Sheet jodo', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : () => _addDrawing())),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Transmittal', icon: Icons.send_rounded, onTap: _busy ? null : _transmittal)),
        ]),
        const SizedBox(height: 12),
        for (final d in _list(_p?['drawings']))
          ExpansionTile(
            title: Text('${_s(d['sheet'])} · rev ${_s(d['rev'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text('${_s(d['title'])} · ${_s(d['status'])}', style: const TextStyle(fontSize: 12.5)),
            children: [
              for (final r in _list(d['revisions']))
                ListTile(dense: true, title: Text('${_s(r['rev'])} · ${_s(r['on'])}'), subtitle: Text(_s(r['note'])),
                    trailing: _s(r['file_id']).isEmpty ? null : const Icon(Icons.attach_file_rounded, size: 16)),
              for (final x in _list(d['issued']))
                ListTile(dense: true, leading: const Icon(Icons.outbox_rounded, size: 18), title: Text('${_s(x['transmittal'])} · ${_s(x['rev'])} → ${_s(x['to'])}'),
                    subtitle: Text(_s(x['on']))),
              Align(alignment: Alignment.centerLeft, child: TextButton.icon(onPressed: () => _addDrawing(d: d), icon: const Icon(Icons.history_edu_rounded), label: const Text('Nayi revision'))),
            ],
          ),
        const SizedBox(height: 8),
        const Caption('TRANSMITTALS'),
        for (final t in _list(_p?['transmittals'])) ...[ArchTransmittalCard(app: widget.app, data: {'transmittal': t}, onDone: _load), const SizedBox(height: 8)],
      ]);

  // ---- approvals
  Future<void> _setApproval(Map<String, dynamic> a) async {
    final f = await _form(context, _s(a['label']), const [
      ('status', 'pending / needed / applied / query / granted / refused / not_needed'),
      ('ref_no', 'Number / inward no.'),
      ('on', 'Tareekh (YYYY-MM-DD)'),
      ('valid_to', 'Valid till (YYYY-MM-DD)'),
    ], ok: 'Save', initial: {'status': _s(a['status']), 'ref_no': _s(a['ref']), 'valid_to': _s(a['valid_to'])});
    if (f == null) return;
    await _run('POST', '/api/archassist/projects/$_ref/approvals', {...f, 'key': a['key']});
  }

  Future<void> _submit() async {
    final stage = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final a in _list(_m(_p?['approvals'])['items'])) ListTile(title: Text(_s(a['label'])), onTap: () => Navigator.pop(c, _s(a['key']))),
        ]),
      ),
    );
    if (stage == null) return;
    final r = await _run('POST', '/api/archassist/projects/$_ref/submissions', {'stage': stage});
    if (r != null && _s(r['id']).isNotEmpty && mounted) {
      await showModalBottomSheet(
        context: context,
        backgroundColor: C.bgBottom,
        isScrollControlled: true,
        builder: (_) => Padding(padding: const EdgeInsets.all(16), child: SingleChildScrollView(child: ArchSubmissionCard(app: widget.app, data: {'submission': r}))),
      );
      await _load();
    }
  }

  Widget _approvalsTab() {
    final ap = _m(_p?['approvals']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(ap['authority']), style: const TextStyle(fontWeight: FontWeight.w800)),
          for (final (i, st) in _strs(ap['steps']).indexed) Text('${i + 1}. $st', style: const TextStyle(fontSize: 12.5)),
          Text(_s(ap['note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
      const SizedBox(height: 8),
      GradientButton(label: 'Submission ka card banao', icon: Icons.fact_check_rounded, height: 46, onTap: _busy ? null : _submit),
      const SizedBox(height: 12),
      for (final a in _list(ap['items']))
        ListTile(
          dense: true,
          leading: Icon(Icons.verified_rounded, color: _stColor(_s(a['status']))),
          title: Text('${_s(a['label'])} · ${_s(a['status'])}'),
          subtitle: Text([_s(a['ref']), if (_s(a['valid_to']).isNotEmpty) 'valid ${_s(a['valid_to'])}', _s(a['why'])].where((x) => x.isNotEmpty).join(' · ')),
          onTap: () => _setApproval(a),
        ),
      const SizedBox(height: 8),
      const Caption('SUBMISSIONS'),
      for (final x in _list(ap['submissions'])) ...[ArchSubmissionCard(app: widget.app, data: {'submission': x}, onDone: _load), const SizedBox(height: 8)],
    ]);
  }

  // ---- RFIs + minutes
  Future<void> _rfi() async {
    final f = await _form(context, 'RFI', const [
      ('party', 'Kisse (consultant / contractor)'),
      ('subject', 'Vishay'),
      ('question', 'Sawaal'),
      ('sheets', 'Sheets (comma se)'),
      ('due', 'Jawab kab tak (YYYY-MM-DD)'),
    ], ok: 'Banao');
    if (f == null) return;
    final r = await _run('POST', '/api/archassist/projects/$_ref/rfis',
        {...f, 'sheets': (f['sheets'] ?? '').split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList()});
    if (r != null && mounted) await _openLinks(context, r);
  }

  Future<void> _answer(Map<String, dynamic> r) async {
    final f = await _form(context, '${_s(r['number'])} jawab', const [('answer', 'Jawab')], ok: 'Save');
    if (f == null) return;
    await _run('POST', '/api/archassist/rfis/${_s(r['id'])}/answer', {'answer': f['answer'] ?? '', 'close': true});
  }

  Future<void> _meeting() async {
    final f = await _form(context, 'Meeting minutes', const [
      ('attendees', 'Kaun the (comma se)'),
      ('place', 'Jagah'),
      ('points', 'Points: har line "point - kaun - tareekh"'),
    ], ok: 'Minutes banao');
    if (f == null) return;
    final pts = <Map<String, dynamic>>[];
    for (final line in (f['points'] ?? '').split('\n')) {
      final parts = line.split(' - ').map((x) => x.trim()).toList();
      if (parts.first.isEmpty) continue;
      pts.add({'point': parts[0], if (parts.length > 1) 'by': parts[1], if (parts.length > 2) 'due': parts[2]});
    }
    final r = await _run('POST', '/api/archassist/projects/$_ref/meetings',
        {'points': pts, 'place': f['place'] ?? '', 'attendees': (f['attendees'] ?? '').split(',').map((x) => x.trim()).where((x) => x.isNotEmpty).toList()});
    if (r != null && mounted) await _openLinks(context, r);
  }

  Widget _coordTab() => ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'RFI', icon: Icons.help_center_rounded, height: 46, onTap: _busy ? null : _rfi)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Minutes', icon: Icons.groups_rounded, onTap: _busy ? null : _meeting)),
        ]),
        const SizedBox(height: 12),
        const Caption('RFI'),
        for (final r in _list(_p?['rfis']))
          ListTile(
            dense: true,
            leading: Icon(Icons.help_outline_rounded, color: r['late'] == true ? C.bad : (_s(r['status']) == 'open' ? C.warn : C.ok)),
            title: Text('${_s(r['number'])} · ${_s(r['party'])}: ${_s(r['subject'])}'),
            subtitle: Text(_s(r['answer']).isNotEmpty ? 'Jawab: ${_s(r['answer'])}' : (_s(r['due']).isEmpty ? _s(r['status']) : 'Due ${_s(r['due'])}')),
            onTap: _s(r['status']) == 'open' ? () => _answer(r) : null,
          ),
        const SizedBox(height: 8),
        const Caption('MEETINGS'),
        for (final m in _list(_p?['meetings']))
          ExpansionTile(
            title: Text('${_s(m['number'])} · ${_s(m['on'])}'),
            children: [
              for (final x in _list(m['points']))
                CheckboxListTile(
                  dense: true,
                  value: x['done'] == true,
                  title: Text(_s(x['point'])),
                  subtitle: Text([_s(x['by']), _s(x['due'])].where((y) => y.isNotEmpty).join(' · ')),
                  onChanged: x['done'] == true ? null : (_) => _run('POST', '/api/archassist/meetings/${_s(m['id'])}/done', {'n': x['n']}),
                ),
            ],
          ),
      ]);

  // ---- fee + invoices
  Future<void> _fee() async {
    final fee = _m(_p?['fee']);
    final f = await _form(context, 'Fee (aapke agreement se)', const [
      ('basis', 'percent / lump'),
      ('percent', 'Fee % (project cost ka)'),
      ('project_cost', 'Project cost (Rs)'),
      ('lump', 'Lump sum (Rs)'),
    ], ok: 'Save', initial: {'basis': _s(fee['basis']).isEmpty ? 'percent' : _s(fee['basis']), 'percent': _s(fee['percent']), 'project_cost': _s(fee['project_cost']), 'lump': _s(fee['lump'])});
    if (f == null) return;
    await _run('POST', '/api/archassist/projects/$_ref/fee', {
      'basis': f['basis'] ?? 'percent',
      if (f['percent'] != null) 'percent': _n(f['percent']),
      if (f['project_cost'] != null) 'project_cost': _n(f['project_cost']),
      if (f['lump'] != null) 'lump': _n(f['lump']),
    });
  }

  Future<void> _invoice(String stage) async {
    final r = await _run('POST', '/api/archassist/projects/$_ref/invoices', {'stage': stage});
    if (r != null && _s(r['id']).isNotEmpty && mounted) {
      await showModalBottomSheet(
        context: context,
        backgroundColor: C.bgBottom,
        isScrollControlled: true,
        builder: (_) => Padding(padding: const EdgeInsets.all(16), child: SingleChildScrollView(child: ArchInvoiceCard(app: widget.app, data: {'invoice': r}))),
      );
      await _load();
    }
  }

  Widget _feeTab() {
    final fee = _m(_p?['fee']);
    final stages = _list(fee['stages']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Fee set karo', icon: Icons.currency_rupee_rounded, height: 46, onTap: _busy ? null : _fee),
      const SizedBox(height: 12),
      for (final x in stages)
        ListTile(
          dense: true,
          title: Text('${_s(x['label'])} · ${_s(x['pct'])}%'),
          trailing: _s(x['invoice']).isEmpty
              ? TextButton(onPressed: _busy ? null : () => _invoice(_s(x['key'])), child: const Text('Invoice'))
              : const Icon(Icons.receipt_long_rounded, color: C.ok),
        ),
      if (stages.isEmpty) const Text('Pehle fee set kijiye (percent + project cost, ya lump sum).', style: TextStyle(color: C.muted)),
      const SizedBox(height: 12),
      const Caption('INVOICES'),
      for (final i in _list(_p?['invoices'])) ...[ArchInvoiceCard(app: widget.app, data: {'invoice': i}, onDone: _load), const SizedBox(height: 8)],
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['Plot', 'Area / FSI', 'Drawings', 'Approval', 'Coordination', 'Fee'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(_p == null ? 'Project' : '${_s(_p?['number'])} · ${_s(_p?['name'])}'),
        actions: [
          IconButton(
              tooltip: 'Register Excel',
              onPressed: () => _run('GET', '/api/archassist/projects/$_ref/register'),
              icon: const Icon(Icons.table_view_rounded)),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
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
          child: _p == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: switch (_tab) { 0 => _plotTab(), 1 => _areaTab(), 2 => _drawingsTab(), 3 => _approvalsTab(), 4 => _coordTab(), _ => _feeTab() },
                ),
        ),
      ]),
    );
  }
}

// ======================================================================= cards

/// archassist_area: the area statement with checks (andaaza, rule book decides). Also in calls.
class ArchAreaCard extends StatelessWidget {
  const ArchAreaCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final st = _m(data['statement']);
    String f(dynamic v) => v == null ? '—' : '$v';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.square_foot_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Area statement ${_s(data['project'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        if (st.isNotEmpty) ...[
          Text('Net plot ${f(st['net_plot'])} sq m · road ${f(st['road_width_m'])} m', style: const TextStyle(fontSize: 12.5)),
          Text('Basic ${f(st['basic_fsi'])} · premium ${f(st['premium_fsi'])} · TDR ${f(st['tdr_fsi'])} → max ${f(st['max_area'])} sq m',
              style: const TextStyle(fontSize: 12.5)),
          if (st['proposed_bua'] != null) Text('Proposed ${f(st['proposed_bua'])} sq m (FSI ${f(st['consumed_fsi'])})', style: const TextStyle(fontSize: 12.5)),
        ],
        const SizedBox(height: 6),
        for (final c in _list(data['checks']))
          Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Text(
                '${switch (_s(c['status'])) { 'ok' => '✓', 'fail' => '✗', _ => '!' }} ${_s(c['item'])}'
                '${c['got'] != null ? ': ${c['got']}' : ''}${c['need'] != null ? ' (chahiye ${c['need']})' : ''} ${_s(c['note'])}',
                style: TextStyle(fontSize: 12.5, color: _stColor(_s(c['status'])))),
          ),
        const SizedBox(height: 4),
        const Text('Andaaza hai, final nahi: rule book aur authority se pakka kijiye.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// archassist_transmittal: drawings to a client / authority / consultant; issued ONLY by her tap here. Also in calls.
class ArchTransmittalCard extends StatefulWidget {
  const ArchTransmittalCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ArchTransmittalCard> createState() => _ArchTransmittalCardState();
}

class _ArchTransmittalCardState extends State<ArchTransmittalCard> {
  bool _busy = false;
  late Map<String, dynamic> _t = _m(widget.data['transmittal']);

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/archassist/transmittals/${_s(_t['id'])}/decide', body: {'yes': yes, 'hash': _s(_t['hash'])}));
      if (mounted) {
        setState(() => _t = {..._t, 'status': yes ? (_m(r['transmittal']).isNotEmpty ? _s(_m(r['transmittal'])['status']) : 'issued') : 'rejected'});
        _snack(context, _s(r['say']));
        if (yes) await _openLinks(context, r);
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
    final t = _t;
    final st = _s(t['status']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.outbox_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(t['number'])} → ${_s(t['to_name'])} (${_s(t['to_label'])})', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'issued' => 'issue', 'stale' => 'purana', 'rejected' => 'nahi', _ => st }, fg: _stColor(st)),
        ]),
        Text(_s(t['purpose_label']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final i in _list(t['items'])) Text('• ${_s(i['sheet'])} rev ${_s(i['rev'])} ${_s(i['title'])}', style: const TextStyle(fontSize: 12.5)),
        for (final w in _strs(t['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (_s(t['note']).isNotEmpty) Text(_s(t['note']), style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, issue karo', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'stale') const Text('Sheet ki revision badal gayi: naya transmittal banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        const Text('Issue = transmittal PDF + message draft; bhejna aap khud.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// archassist_submission: the submission checklist; "submit karo" ONLY on her tap. Also in calls.
class ArchSubmissionCard extends StatefulWidget {
  const ArchSubmissionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ArchSubmissionCard> createState() => _ArchSubmissionCardState();
}

class _ArchSubmissionCardState extends State<ArchSubmissionCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['submission']);

  Future<void> _post(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', path, body: body));
      if (mounted) {
        if (_s(r['id']).isNotEmpty) setState(() => _x = r);
        _snack(context, _s(r['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _update() async {
    final f = await _form(context, 'Portal ka haal', const [
      ('status', 'submitted / query / granted / refused'),
      ('ref_no', 'Inward / application / permission no.'),
      ('valid_to', 'Valid till (granted ho to)'),
    ], ok: 'Save', initial: {'status': 'submitted'});
    if (f == null) return;
    await _post('/api/archassist/submissions/${_s(_x['id'])}/update', f);
  }

  @override
  Widget build(BuildContext context) {
    final x = _x;
    final st = _s(x['status']);
    final blockers = _strs(x['blockers']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.fact_check_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · ${_s(x['stage_label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st == 'waiting' ? 'aapki haan?' : st, fg: _stColor(st)),
        ]),
        Text('${_s(x['project'])} · ${_s(x['authority'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final b in blockers) Text('✗ $b', style: const TextStyle(fontSize: 12.5, color: C.bad)),
        for (final w in _strs(x['warnings'])) Text('! $w', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        if (_s(x['ref']).isNotEmpty) Text('No: ${_s(x['ref'])}', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting' && blockers.isEmpty)
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: 'Haan, submit karna hai',
                    height: 42,
                    onTap: _busy ? null : () => _post('/api/archassist/submissions/${_s(x['id'])}/decide', {'yes': true, 'hash': _s(x['hash'])}))),
            const SizedBox(width: 8),
            GlassButton(
                label: 'Nahi',
                height: 42,
                onTap: _busy ? null : () => _post('/api/archassist/submissions/${_s(x['id'])}/decide', {'yes': false, 'hash': _s(x['hash'])})),
          ]),
        if (st == 'waiting' && blockers.isNotEmpty) const Text('Pehle rukawat hataiye, phir naya card banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        if (['approved', 'submitted', 'query'].contains(st))
          GlassButton(label: 'Portal ka haal batao', icon: Icons.update_rounded, height: 42, onTap: _busy ? null : _update),
        const Text('Portal login, fee aur OTP aap khud; Hoola sirf taiyaari karta hai.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// archassist_invoice: fee invoice; numbered ONLY on her tap (fingerprint once a phone key is active). Also in calls.
class ArchInvoiceCard extends StatefulWidget {
  const ArchInvoiceCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<ArchInvoiceCard> createState() => _ArchInvoiceCardState();
}

class _ArchInvoiceCardState extends State<ArchInvoiceCard> {
  bool _busy = false;
  late Map<String, dynamic> _i = _m(widget.data['invoice']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/archassist/invoices/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Invoice ki haan' : _s(show['title']),
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
    final id = _s(_i['id']);
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_i['hash'])};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/archassist/invoices/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/archassist/invoices/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        if (_m(m['invoice']).isNotEmpty) setState(() => _i = _m(m['invoice']));
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

  Future<void> _paid() async {
    final f = await _form(context, 'Paise aaye', const [('amount', 'Kitne aaye (bank / UPI)'), ('tds', 'TDS kata (ho to)'), ('ref', 'UTR (ho to)')]);
    if (f == null) return;
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', '/api/archassist/invoices/${_s(_i['id'])}/paid',
          body: {'amount': _n(f['amount']), 'tds': _n(f['tds']), 'ref': f['ref'] ?? ''}));
      if (mounted) {
        if (_s(m['id']).isNotEmpty) setState(() => _i = m);
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
    final i = _i;
    final st = _s(i['status']);
    final tax = _m(i['tax']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.receipt_long_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(i['number']).isEmpty ? 'Invoice' : _s(i['number'])} · ${_s(i['amount_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st == 'waiting' ? 'aapki haan?' : st, fg: _stColor(st)),
        ]),
        Text(_s(i['label']), style: const TextStyle(fontSize: 12.5)),
        if (_s(i['client']).isNotEmpty) Text('Client: ${_s(i['client'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        Text('Fee ${_s(i['amount'])} · ${_s(tax['note'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if ((i['tds'] ?? 0) != 0) Text('Client ~${_s(i['tds'])} TDS kaatega · ${_s(tax['tds_note'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, invoice banao', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'issued') GlassButton(label: 'Paise aaye', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : _paid),
        const Text('Hoola paise nahi leta; client aapko seedha deta hai.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// archassist_alert / archassist_day: reminders and the morning note. Calls: no.
class ArchNoteCard extends StatelessWidget {
  const ArchNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Glass(
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.architecture_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.4))),
          IconButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArchassistScreen(app: app))),
              icon: const Icon(Icons.open_in_new_rounded, size: 18)),
        ]),
      );
}
