/// Profile > Site Sahayak: Hoola as the construction site supervisor.
/// Aaj (morning note, cards waiting for her, cube tests due) · Sites (site page: plan vs done, hazri, material, safety, quality,
/// snags, DPR) · Niyam (hours, her trade rates, cube limits from her QA plan, rules). Indent / purchase, anything to the client and
/// any stop-work order happen only on HER tap here (fingerprint for an indent with an amount once a phone key is set up).
library;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

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

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Continue', Map<String, String> initial = const {}}) async {
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
                maxLines: const {'text', 'items', 'reason', 'tomorrow', 'note', 'rows'}.contains(k) ? 3 : 1),
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

/// "cement 100 bag; ret 2 brass" -> [{item, qty, unit}]
List<Map<String, dynamic>> _items(String text) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split(RegExp(r'[\n;,]'))) {
    final line = raw.trim();
    if (line.isEmpty) continue;
    final m = RegExp(r'^(.*?)\s+(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*$').firstMatch(line);
    if (m == null) continue;
    out.add({'item': m.group(1)!.trim(), 'qty': num.parse(m.group(2)!), 'unit': m.group(3) ?? ''});
  }
  return out;
}

/// "Ramesh beldar 12 8; Ramesh mistri 2 10" -> [{contractor, trade, count, hours}]
List<Map<String, dynamic>> _gangs(String text) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split(RegExp(r'[\n;]'))) {
    final p = raw.trim().split(RegExp(r'\s+'));
    if (p.length < 3) continue;
    final count = int.tryParse(p[2]);
    if (count == null) continue;
    out.add({'contractor': p[0], 'trade': p[1], 'count': count, if (p.length > 3 && num.tryParse(p[3]) != null) 'hours': num.parse(p[3])});
  }
  return out;
}

class SitesupScreen extends StatefulWidget {
  const SitesupScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SitesupScreen> createState() => _SitesupScreenState();
}

class _SitesupScreenState extends State<SitesupScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/sitesup'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void _openSite(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => SitesupSitePage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _addSite() async {
    final f = await _form(context, 'New site', const [
      ('name', 'Site name'),
      ('client', 'Client'),
      ('client_phone', 'Client mobile'),
      ('address', 'Address'),
      ('engineer', 'Engineer / consultant'),
      ('start', 'Start (DD-MM-YYYY)'),
      ('finish', 'End (DD-MM-YYYY)'),
      ('theka_project', 'Contractor job name, if linking to one'),
    ], ok: 'Add');
    if (f == null || (f['name'] ?? '').isEmpty || !mounted) return;
    final r = await _call(context, widget.app, 'POST', '/api/sitesup/sites', f);
    await _load();
    final id = _s(_m(r?['site'])['id']);
    if (id.isNotEmpty && mounted) _openSite(id);
  }

  Widget _aaj() {
    final d = _d!;
    final day = _m(d['day']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('On site today', style: TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        for (final p in _strs(day['parts'])) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• $p', style: const TextStyle(fontSize: 13))),
      ])),
      const SizedBox(height: 12),
      for (final i in _list(d['indents']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: SitesupIndentCard(app: widget.app, data: {'indent': i}, onDone: _load)),
      for (final w in _list(d['stops']).where((x) => const {'waiting', 'active'}.contains(_s(x['status']))))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: SitesupStopCard(app: widget.app, data: {'stop': w}, onDone: _load)),
      for (final r in _list(d['reports']).where((x) => const {'waiting', 'approved'}.contains(_s(x['status']))))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: SitesupReportCard(app: widget.app, data: {'report': r}, onDone: _load)),
      if (_list(d['cubes_due']).isNotEmpty) ...[
        const Caption('CUBE TEST'),
        for (final c in _list(d['cubes_due']))
          Text('${_s(c['pour'])} ${_s(c['element'])} · ${_s(c['age'])} din · ${_s(c['due'])}${(c['late_days'] ?? 0) > 0 ? ' (late)' : ''}',
              style: const TextStyle(fontSize: 13)),
      ],
      const SizedBox(height: 12),
      for (final r in _strs(d['rules'])) Text(r, style: const TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  Widget _sites() {
    final list = _list(_d!['sites']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      GradientButton(label: 'New site', icon: Icons.add_rounded, height: 46, onTap: _addSite),
      const SizedBox(height: 12),
      for (final s in list)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => _openSite(_s(s['id'])),
            child: Glass(
              border: _s(s['status']) == 'stopped' ? C.bad : null,
              child: Row(children: [
                const Icon(Icons.construction_rounded, color: C.accent),
                const SizedBox(width: 10),
                Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(s['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text([_s(s['client']), if (_m(s['theka']).isNotEmpty) 'Contract: ${_s(_m(s['theka'])['name'])}'].where((x) => x.isNotEmpty).join(' · '),
                      style: const TextStyle(fontSize: 12.5, color: C.muted)),
                ])),
                Pill(_s(s['status']), fg: _s(s['status']) == 'stopped' ? C.bad : C.ok),
              ]),
            ),
          ),
        ),
      if (list.isEmpty) const Text('No sites yet.', style: TextStyle(color: C.muted)),
    ]);
  }

  Widget _niyam() {
    final st = _m(_d!['settings']);
    final rates = _m(st['rates']);
    final cl = _m(st['cube_limits']);
    return ListView(padding: const EdgeInsets.all(14), children: [
      Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Firm: ${_s(st['firm'])}  ·  Supervisor: ${_s(st['supervisor'])}'),
        Text('Morning note ${_s(st['morning_time'])} · DPR reminder ${_s(st['dpr_time'])}'),
        Text('Day ${_s(st['day_hours'])} hours (then overtime, double rate) · week ${_s(st['week_hours'])} hours'),
        Text('Look-ahead ${_s(st['lookahead_days'])} days · ${_s(st['behind_pct'])}% behind plan = delay'),
        Text('Rate (only for checking contractor bills): ${rates.isEmpty ? 'none' : rates.entries.map((e) => '${e.key} ₹${e.value}').join(', ')}'),
        Text('Cube rules (QA plan): ${cl.isEmpty ? 'IS 456 Table 11 default' : cl.entries.map((e) => '${e.key} ${e.value}').join(', ')}'),
        for (final r in _strs(st['rules'])) Text('• $r', style: const TextStyle(fontSize: 12.5)),
      ])),
      const SizedBox(height: 10),
      GlassButton(
          label: 'Edit',
          icon: Icons.tune_rounded,
          height: 44,
          onTap: () async {
            final f = await _form(context, 'Site rules', const [
              ('firm', 'Firm'),
              ('supervisor', 'Supervisor'),
              ('morning_time', 'Morning note (HH:MM)'),
              ('dpr_time', 'DPR reminder (HH:MM)'),
              ('day_hours', 'Hours in a day'),
              ('lookahead_days', 'Look-ahead din'),
              ('mason', 'Mason rate / day (₹)'),
              ('helper', 'Beldar rate / din (₹)'),
              ('individual_minus', 'Cube: how much below fck one cube may fall'),
              ('mean_plus', 'Cube: how far the mean of 4 must be above fck'),
            ]);
            if (f == null || !mounted) return;
            final body = <String, dynamic>{
              for (final k in ['firm', 'supervisor', 'morning_time', 'dpr_time']) if (f[k] != null) k: f[k],
              if (f['day_hours'] != null) 'day_hours': _n(f['day_hours']),
              if (f['lookahead_days'] != null) 'lookahead_days': _n(f['lookahead_days']),
              if (f['mason'] != null || f['helper'] != null) 'rates': {if (f['mason'] != null) 'mason': _n(f['mason']), if (f['helper'] != null) 'helper': _n(f['helper'])},
              if (f['individual_minus'] != null || f['mean_plus'] != null)
                'cube_limits': {if (f['individual_minus'] != null) 'individual_minus': _n(f['individual_minus']), if (f['mean_plus'] != null) 'mean_plus': _n(f['mean_plus'])},
            };
            await _call(context, widget.app, 'PUT', '/api/sitesup/settings', body);
            await _load();
          }),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = const ['Today', 'Sites', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Site supervisor'), actions: [
        IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load),
      ]),
      body: _d == null
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Row(children: [
                  for (var i = 0; i < tabs.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
                    ),
                ]),
              ),
              Expanded(child: RefreshIndicator(onRefresh: _load, child: [_aaj, _sites, _niyam][_tab]())),
            ]),
    );
  }
}

/// One site: plan vs done, hazri, material, safety, quality, snags, DPR.
class SitesupSitePage extends StatefulWidget {
  const SitesupSitePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<SitesupSitePage> createState() => _SitesupSitePageState();
}

class _SitesupSitePageState extends State<SitesupSitePage> {
  Map<String, dynamic>? _v;
  bool _busy = false;
  String get _p => '/api/sitesup/sites/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', _p));
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _do(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _progress([Map<String, dynamic>? a]) async {
    final f = await _form(context, a == null ? 'Today\'s work' : _s(a['name']), const [
      ('activity', 'Activity (name / code)'),
      ('qty', 'How much done (as measured)'),
      ('note', 'Where / note'),
      ('delay', 'Stopped / slow, then the reason'),
    ], initial: {'activity': a == null ? '' : _s(a['code'])}, ok: 'Write');
    if (f == null) return;
    await _do('POST', '$_p/progress', {...f, if (f['qty'] != null) 'qty': _n(f['qty'])});
  }

  Future<void> _plan() async {
    final f = await _form(context, 'Activity plan', const [
      ('name', 'Activity (e.g. RCC slab 1st floor)'),
      ('unit', 'Unit (cum / sqm / rmt / nos)'),
      ('qty', 'Total quantity'),
      ('start', 'Start (DD-MM-YYYY)'),
      ('finish', 'End (DD-MM-YYYY)'),
      ('contractor', 'Contractor'),
    ], ok: 'Add');
    if (f == null) return;
    await _do('POST', '$_p/plan', {
      'items': [
        {...f, if (f['qty'] != null) 'qty': _n(f['qty'])}
      ]
    });
  }

  Future<void> _hazri() async {
    final f = await _form(context, 'Attendance', const [
      ('rows', 'One per line: contractor work log hours\n(Ramesh beldar 12 8)'),
      ('day', 'Date (empty = today)'),
    ], ok: 'Write');
    if (f == null) return;
    final rows = _gangs(f['rows'] ?? '');
    if (rows.isEmpty) {
      if (mounted) _snack(context, 'Could not understand the line: "Ramesh beldar 12 8"');
      return;
    }
    await _do('POST', '$_p/attendance', {'rows': rows, if (f['day'] != null) 'day': f['day']});
  }

  Future<void> _material(String kind) async {
    final f = await _form(context, kind == 'in' ? 'Material received' : 'Material used', [
      ('item', 'Material (cement / sand / steel...)'),
      ('qty', 'Quantity'),
      ('unit', 'Unit (bag / brass / t / nos)'),
      if (kind == 'in') ('supplier', 'Supplier'),
      if (kind == 'in') ('challan', 'Challan no'),
      if (kind == 'in') ('vehicle', 'Vehicle no.'),
    ], ok: 'Write');
    if (f == null) return;
    await _do('POST', '$_p/material', {...f, 'kind': kind, if (f['qty'] != null) 'qty': _n(f['qty'])});
  }

  Future<void> _indent() async {
    final f = await _form(context, 'Indent (card for your approval)', const [
      ('items', 'One per line: material qty unit (cement 100 bag)'),
      ('need_by', 'Needed by'),
      ('supplier', 'Supplier'),
      ('supplier_phone', 'Supplier mobile'),
      ('amount', 'Amount (from the quote, if known)'),
      ('reason', 'What it is for'),
    ], ok: 'Make card');
    if (f == null) return;
    await _do('POST', '$_p/indents', {...f, 'items': _items(f['items'] ?? ''), if (f['amount'] != null) 'amount': _n(f['amount'])});
  }

  Future<void> _checklist() async {
    final kinds = _m((await widget.app.api!.call('GET', '/api/sitesup'))['checklists']);
    if (!mounted) return;
    final kind = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => ListView(children: [
        for (final e in kinds.entries) ListTile(title: Text(_s(_m(e.value)['label'])), onTap: () => Navigator.pop(c, e.key)),
      ]),
    );
    if (kind == null || !mounted) return;
    final items = _list(_m(kinds[kind])['items']);
    final answers = <String, bool?>{for (final i in items) _s(i['id']): null};
    final area = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: Text(_s(_m(kinds[kind])['label'])),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: area, decoration: const InputDecoration(labelText: 'Place (e.g. 2nd floor slab edge)')),
              for (final i in items) ...[
                const SizedBox(height: 8),
                Text('${_s(i['q'])}${i['critical'] == true ? ' ⚠' : ''}', style: const TextStyle(fontSize: 13)),
                Wrap(spacing: 6, children: [
                  ChoiceChip(label: const Text('Yes'), selected: answers[_s(i['id'])] == true, onSelected: (_) => set(() => answers[_s(i['id'])] = true)),
                  ChoiceChip(label: const Text('No'), selected: answers[_s(i['id'])] == false, onSelected: (_) => set(() => answers[_s(i['id'])] = false)),
                ]),
              ],
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    await _do('POST', '$_p/checklist', {
      'kind': kind,
      'area': area.text.trim(),
      'answers': {for (final e in answers.entries) if (e.value != null) e.key: e.value},
    });
  }

  Future<void> _incident() async {
    final f = await _form(context, 'Incident / near-miss', const [
      ('text', 'What happened, where'),
      ('kind', 'near_miss / first_aid / injury / death / dangerous'),
      ('at', 'When (YYYY-MM-DD HH:MM, empty = now)'),
      ('people', 'How many people'),
      ('names', 'Name / contractor'),
      ('action', 'What was done (first aid / hospital)'),
    ], ok: 'In the register');
    if (f == null) return;
    final r = await _do('POST', '$_p/incident', {...f, if (f['people'] != null) 'people': _n(f['people'])});
    final form = _s(r?['form_xi']);
    if (form.isNotEmpty && mounted) {
      await showDialog<void>(
          context: context,
          builder: (d) => AlertDialog(
              title: const Text('Draft of Form XI'),
              content: SingleChildScrollView(child: SelectableText(form)),
              actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK'))]));
    }
  }

  Future<void> _pour() async {
    final f = await _form(context, 'Pour card', const [
      ('element', 'Part (1st floor slab / column C3...)'),
      ('grade', 'Grade (M20 / M25)'),
      ('volume', 'Concrete (cum)'),
      ('cement', 'Cement (OPC 53 / PPC)'),
      ('source', 'RMC plant / site mix'),
      ('slump', 'Slump (mm)'),
    ], ok: 'Save');
    if (f == null) return;
    await _do('POST', '$_p/pours', {...f, if (f['volume'] != null) 'volume': _n(f['volume'])});
  }

  Future<void> _cube(Map<String, dynamic> p) async {
    final f = await _form(context, '${_s(p['number'])} cube result', const [
      ('age', 'Din (7 / 28 / 56)'),
      ('sample', 'Sample no (1, 2...)'),
      ('results', 'N/mm2, comma separated (18.2, 17.9, 18.6)'),
      ('lab', 'Lab'),
    ], ok: 'Check');
    if (f == null) return;
    final res = (f['results'] ?? '').split(RegExp(r'[,\s]+')).map((x) => num.tryParse(x)).whereType<num>().toList();
    await _do('POST', '/api/sitesup/pours/${_s(p['id'])}/cubes',
        {'age': _n(f['age']) ?? 28, 'sample': _n(f['sample']) ?? 1, 'results': res, 'lab': f['lab'] ?? ''});
  }

  Future<void> _snag() async {
    final f = await _form(context, 'Snag (defect)', const [('text', 'What is lacking'), ('location', 'Where'), ('contractor', 'Whose contractor')], ok: 'Add');
    if (f == null) return;
    await _do('POST', '$_p/snags', f);
  }

  Future<void> _photo(String ref, String stage) async {
    final src = await showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (c) => Wrap(children: [
        ListTile(leading: const Icon(Icons.photo_camera_rounded), title: const Text('Camera'), onTap: () => Navigator.pop(c, ImageSource.camera)),
        ListTile(leading: const Icon(Icons.photo_library_rounded), title: const Text('Gallery'), onTap: () => Navigator.pop(c, ImageSource.gallery)),
      ]),
    );
    if (src == null) return;
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 80, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      setState(() => _busy = true);
      final r = await widget.app.api!.uploadFile('$_p/photo', x.name.isEmpty ? 'photo.jpg' : x.name, bytes, fields: {'ref': ref, 'stage': stage});
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _dpr() async {
    final f = await _form(context, 'Today\'s DPR', const [
      ('weather', 'Weather'),
      ('tomorrow', 'Tomorrow\'s work'),
      ('remarks', 'Anything else'),
    ], ok: 'Make (it goes only after your approval)');
    if (f == null) return;
    final r = await _do('POST', '$_p/dpr', f);
    final rep = _m(r?['report']);
    if (rep.isNotEmpty && mounted) {
      await showModalBottomSheet<void>(
          context: context,
          backgroundColor: C.bgBottom,
          isScrollControlled: true,
          builder: (_) => Padding(
              padding: const EdgeInsets.all(16),
              child: SingleChildScrollView(child: SitesupReportCard(app: widget.app, data: {'report': rep}, onDone: _load))));
    }
  }

  Widget _sec(String title, List<Widget> children, {List<Widget> actions = const []}) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            ...children,
            if (actions.isNotEmpty) ...[const SizedBox(height: 8), Wrap(spacing: 8, runSpacing: 8, children: actions)],
          ]),
        ),
      );

  Color _stateColor(String st) => switch (st) { 'late' => C.bad, 'behind' => C.warn, 'done' => C.ok, 'on_track' => C.ok, _ => C.chip };

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(v == null ? 'Site' : _s(v['name']))),
      body: v == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(14), children: [
                if (_busy) const LinearProgressIndicator(),
                if (_m(v['stop']).isNotEmpty) SitesupStopCard(app: widget.app, data: {'stop': _m(v['stop'])}, onDone: _load),
                Text([_s(v['client']), _s(v['address']), if (_m(v['theka']).isNotEmpty) 'Contract: ${_s(_m(v['theka'])['name'])}']
                    .where((x) => x.isNotEmpty)
                    .join(' · '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
                const SizedBox(height: 10),
                _sec('Work: plan vs done', [
                  for (final a in _list(v['activities']))
                    InkWell(
                      onTap: () => _progress(a),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(children: [
                          Expanded(
                              child: Text('${_s(a['code'])} ${_s(a['name'])}${_strs(a['reasons']).isNotEmpty ? '\n  reason: ${_strs(a['reasons']).first}' : ''}',
                                  style: const TextStyle(fontSize: 13))),
                          Pill('${_s(a['done_pct'])}%${a['planned_pct'] != null ? ' / ${_s(a['planned_pct'])}%' : ''}', fg: _stateColor(_s(a['state']))),
                        ]),
                      ),
                    ),
                ], actions: [
                  GlassButton(label: 'Today\'s work', height: 38, onTap: () => _progress()),
                  GlassButton(label: 'Add activity', height: 38, onTap: _plan),
                  if (_s(v['theka_project_id']).isNotEmpty) GlassButton(label: 'BOQ se', height: 38, onTap: () => _do('POST', '$_p/plan', {'from_boq': true})),
                ]),
                _sec('Attendance (${_s(_m(v['labour_today'])['total'])} people today)', [
                  for (final c in _list(_m(v['labour_today'])['contractors']))
                    Text('${_s(c['contractor'])}: ${_list(c['trades']).map((t) => '${t['label']} ${t['people']}').join(', ')}'
                        '${(c['ot_hours'] ?? 0) > 0 ? ' · OT ${c['ot_hours']} hours' : ''}', style: const TextStyle(fontSize: 13)),
                ], actions: [
                  GlassButton(label: 'Mark attendance', height: 38, onTap: _hazri),
                  GlassButton(label: 'Register Excel', height: 38, onTap: () => _do('POST', '$_p/register_file', {})),
                ]),
                _sec('Material at site', [
                  for (final b in _list(v['material']))
                    Text('${_s(b['item'])}: ${_s(b['balance'])} ${_s(b['unit'])} (received ${_s(b['received'])}, used ${_s(b['used'])})',
                        style: TextStyle(fontSize: 13, color: (b['balance'] ?? 0) <= 0 ? C.bad : C.ink)),
                ], actions: [
                  GlassButton(label: 'Arrived', height: 38, onTap: () => _material('in')),
                  GlassButton(label: 'Used', height: 38, onTap: () => _material('used')),
                  GlassButton(label: 'Indent', height: 38, onTap: _indent),
                ]),
                _sec('Safety', [
                  for (final x in _list(v['safety']).take(8))
                    Text(
                        switch (_s(x['type'])) {
                          'incident' => '⚠ ${_s(x['number'])} ${_s(x['label'])}${_s(x['reported']).isEmpty && _s(x['due_at']).isNotEmpty ? ' · notice pending' : ''}',
                          'check' => '☑ ${_s(x['label'])} ${_s(x['score'])}%',
                          _ => '🗣 ${_s(x['topic'])} · ${_s(x['people'])} log',
                        },
                        style: const TextStyle(fontSize: 13)),
                ], actions: [
                  GlassButton(
                      label: 'Toolbox talk',
                      height: 38,
                      onTap: () async {
                        final f = await _form(context, 'Toolbox talk', const [('topic', 'Topic (empty = today\'s)'), ('people', 'How many people')]);
                        if (f == null) return;
                        await _do('POST', '$_p/toolbox', {...f, 'people': _n(f['people'])});
                      }),
                  GlassButton(label: 'Checklist', height: 38, onTap: _checklist),
                  GlassButton(label: 'Incident', height: 38, color: C.bad, onTap: _incident),
                  GlassButton(
                      label: 'Stop the work?',
                      height: 38,
                      onTap: () async {
                        final f = await _form(context, 'Stop-work card', const [('area', 'Where'), ('reason', 'Why')]);
                        if (f == null) return;
                        await _do('POST', '$_p/stops', f);
                      }),
                ]),
                _sec('Quality', [
                  for (final p in _list(v['pours']).take(8))
                    InkWell(
                      onTap: () => _cube(p),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Text(
                            '${_s(p['number'])} ${_s(p['element'])} ${_s(p['grade'])} ${_s(p['volume'])} cum · curing until ${_s(p['curing_until'])}\n'
                            '${_list(p['cubes']).where((c) => _s(c['verdict']).isNotEmpty).map((c) => '${c['age']}d S${c['sample']}: ${c['verdict']}').join(', ')}',
                            style: const TextStyle(fontSize: 13)),
                      ),
                    ),
                  for (final n in _list(v['snags']).where((x) => _s(x['status']) != 'verified').take(10))
                    Row(children: [
                      Expanded(child: Text('${_s(n['number'])} ${_s(n['location'])}: ${_s(n['text'])}', style: const TextStyle(fontSize: 13))),
                      IconButton(icon: const Icon(Icons.add_a_photo_rounded, size: 18), onPressed: () => _photo(_s(n['id']), 'snag')),
                      if (_s(n['status']) == 'open')
                        TextButton(onPressed: () => _photo(_s(n['id']), 'fixed'), child: const Text('Fixed (photo)'))
                      else
                        TextButton(onPressed: () => _do('POST', '/api/sitesup/snags/${_s(n['id'])}/status', {'status': 'verified'}), child: const Text('Seen')),
                    ]),
                ], actions: [
                  GlassButton(label: 'Pour card', height: 38, onTap: _pour),
                  GlassButton(label: 'Snag', height: 38, onTap: _snag),
                  GlassButton(label: 'Site photo', height: 38, onTap: () => _photo('', 'progress')),
                ]),
                _sec('Report to client', [
                  for (final r in _list(v['reports']).take(6))
                    Text('${_s(r['number'])} ${_s(r['day'])} · ${_s(r['status'])}', style: const TextStyle(fontSize: 13)),
                  const Text('Nothing goes to the client without your approval.', style: TextStyle(fontSize: 11.5, color: C.faint)),
                ], actions: [
                  GradientButton(label: 'Today\'s DPR', height: 42, onTap: _dpr),
                  GlassButton(
                      label: 'Message to client',
                      height: 42,
                      onTap: () async {
                        final f = await _form(context, 'Message for the client', const [('text', 'Message')], ok: 'Make card');
                        if (f == null) return;
                        await _do('POST', '$_p/message', f);
                      }),
                ]),
              ]),
            ),
    );
  }
}

Future<Map<String, dynamic>> _fingerprint(Santosh app, String path) async {
  final ch = _m(await app.api!.call('POST', path));
  final show = _m(ch['show']);
  final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Indent approval' : _s(show['title']),
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

/// sitesup_indent: a material indent / purchase waiting for HER tap. Also in calls.
class SitesupIndentCard extends StatefulWidget {
  const SitesupIndentCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SitesupIndentCard> createState() => _SitesupIndentCardState();
}

class _SitesupIndentCardState extends State<SitesupIndentCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['indent']);

  Future<void> _decide(bool yes) async {
    final id = _s(_x['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not', const [('reason', 'Reason')]);
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_x['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/sitesup/indents/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _fingerprint(widget.app, '/api/sitesup/indents/$id/challenge');
        r = await widget.app.api!.call('POST', '/api/sitesup/indents/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() => _x = _m(m['indent']).isEmpty ? _x : _m(m['indent']));
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
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.inventory_2_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · ${_s(x['site'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'accepted', 'ordered' => 'order sent', 'received' => 'arrived', 'rejected' => 'no', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' ? C.bad : C.ok)),
        ]),
        for (final i in _list(x['items'])) Text('• ${_s(i['item'])} ${_s(i['qty'])} ${_s(i['unit'])}', style: const TextStyle(fontSize: 13)),
        Text('Amount: ${_s(x['amount_text'])}${_s(x['need_by']).isNotEmpty ? ' · needed by ${_s(x['need_by'])}' : ''}', style: const TextStyle(fontSize: 12.5)),
        if (_s(x['supplier']).isNotEmpty) Text('Supplier: ${_s(x['supplier'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        for (final c in _strs(x['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, order it', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved')
          Wrap(spacing: 8, children: [
            if (_s(x['wa']).isNotEmpty) GlassButton(label: 'WhatsApp the supplier', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: _s(x['wa']))),
            GlassButton(
                label: 'Order sent',
                height: 40,
                onTap: () async {
                  final m = await _call(context, widget.app, 'POST', '/api/sitesup/indents/${_s(x['id'])}/ordered');
                  if (m != null && mounted) setState(() => _x = _m(m['indent']).isEmpty ? _x : _m(m['indent']));
                  widget.onDone?.call();
                }),
          ]),
        const Text('Hoola never places an order or payment itself.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// sitesup_stop: a stop-work order waiting for HER tap (and lifting it). Also in calls.
class SitesupStopCard extends StatefulWidget {
  const SitesupStopCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SitesupStopCard> createState() => _SitesupStopCardState();
}

class _SitesupStopCardState extends State<SitesupStopCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['stop']);

  Future<void> _go(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    final m = await _call(context, widget.app, 'POST', path, body);
    if (m != null && mounted) {
      setState(() => _x = _m(m['stop']).isEmpty ? _x : _m(m['stop']));
      final notice = _s(m['notice']);
      if (notice.isNotEmpty) {
        await showDialog<void>(
            context: context,
            builder: (d) => AlertDialog(title: const Text('Notice to contractor'), content: SelectableText(notice), actions: [
                  TextButton(onPressed: () => Native.openExternal(url: 'https://wa.me/?text=${Uri.encodeComponent(notice)}'), child: const Text('WhatsApp')),
                  TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK')),
                ]));
      }
    }
    widget.onDone?.call();
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final x = _x;
    final st = _s(x['status']);
    return Glass(
      border: st == 'waiting' || st == 'active' ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.front_hand_rounded, color: C.bad),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · Stop work: ${_s(x['area'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'active' => 'in force', 'lifted' => 'lifted', 'rejected' => 'not stopped', _ => st },
              fg: st == 'lifted' || st == 'rejected' ? C.ok : C.bad),
        ]),
        Text(_s(x['site']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        Text(_s(x['reason']), style: const TextStyle(fontSize: 13)),
        if (st == 'waiting') const Text('If there is danger to life, move people away first.', style: TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, stop the work', height: 42, onTap: _busy ? null : () => _go('/api/sitesup/stops/${_s(x['id'])}/decide', {'yes': true, 'hash': _s(x['hash'])}))),
            const SizedBox(width: 8),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _go('/api/sitesup/stops/${_s(x['id'])}/decide', {'yes': false, 'hash': _s(x['hash'])})),
          ]),
        if (st == 'active')
          GlassButton(
              label: 'Fixed, restart work',
              height: 42,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form(context, 'What was fixed', const [('note', 'e.g. guard rail fitted, checklist 100%')]);
                      if (f == null) return;
                      await _go('/api/sitesup/stops/${_s(x['id'])}/lift', {'note': f['note'] ?? ''});
                    }),
      ]),
    );
  }
}

/// sitesup_report: DPR / message for the client, waiting for HER tap. Also in calls.
class SitesupReportCard extends StatefulWidget {
  const SitesupReportCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SitesupReportCard> createState() => _SitesupReportCardState();
}

class _SitesupReportCardState extends State<SitesupReportCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['report']);

  Future<void> _post(String path, [Object? body]) async {
    setState(() => _busy = true);
    final m = await _call(context, widget.app, 'POST', path, body);
    if (m != null && mounted) setState(() => _x = _m(m['report']).isEmpty ? _x : _m(m['report']));
    widget.onDone?.call();
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final x = _x;
    final st = _s(x['status']);
    final id = _s(x['id']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_s(x['kind']) == 'dpr' ? Icons.summarize_rounded : Icons.message_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['number'])} · ${_s(x['site'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your approval?', 'approved' => 'accepted', 'sent' => 'sent', 'rejected' => 'no', 'stale' => 'stale', _ => st },
              fg: st == 'waiting' ? C.accent : (st == 'rejected' || st == 'stale' ? C.faint : C.ok)),
        ]),
        const SizedBox(height: 4),
        Text(_s(x['text']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        if (_s(x['to_phone']).isEmpty) const Text('No client phone: add it in the site.', style: TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 8, children: [
            GradientButton(label: 'Yes, let it go', height: 42, onTap: _busy ? null : () => _post('/api/sitesup/reports/$id/decide', {'yes': true, 'hash': _s(x['hash'])})),
            GlassButton(
                label: 'Business WhatsApp se',
                height: 42,
                onTap: _busy ? null : () => _post('/api/sitesup/reports/$id/decide', {'yes': true, 'hash': _s(x['hash']), 'via': 'business'})),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _post('/api/sitesup/reports/$id/decide', {'yes': false, 'hash': _s(x['hash'])})),
          ]),
        if (st == 'approved')
          Wrap(spacing: 8, children: [
            if (_s(x['wa']).isNotEmpty) GlassButton(label: 'Open WhatsApp', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: _s(x['wa']))),
            GlassButton(label: 'I have sent it', height: 40, onTap: _busy ? null : () => _post('/api/sitesup/reports/$id/sent')),
          ]),
      ]),
    );
  }
}

/// sitesup_alert: cube test / curing / incident deadline / DPR reminder / delay. Also in calls.
class SitesupAlertCard extends StatelessWidget {
  const SitesupAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final k = _s(data['kind']);
    final icon = switch (k) {
      'incident' => Icons.health_and_safety_rounded,
      'cube' || 'curing' => Icons.science_rounded,
      'dpr' => Icons.summarize_rounded,
      _ => Icons.construction_rounded,
    };
    return Glass(
      border: k == 'incident' ? C.bad : C.warn,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: k == 'incident' ? C.bad : C.warn),
        const SizedBox(width: 10),
        Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5, height: 1.35))),
      ]),
    );
  }
}

/// sitesup_day: the morning site note. Not in calls.
class SitesupDayCard extends StatelessWidget {
  const SitesupDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.wb_sunny_rounded, color: C.accent),
            SizedBox(width: 8),
            Text('Today\'s site note', style: TextStyle(fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          for (final p in _strs(data['parts'])) Text('• $p', style: const TextStyle(fontSize: 13, height: 1.35)),
          if (_strs(data['parts']).isEmpty) Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          const SizedBox(height: 8),
          GlassButton(label: 'Open site', height: 38, onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SitesupScreen(app: app)))),
        ]),
      );
}
