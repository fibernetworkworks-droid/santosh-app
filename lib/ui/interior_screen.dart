/// Profile > Interior Sahayak: Hoola as the interior designer's coworker.
/// Aaj (installation today, late work, stages due, open snags, cards waiting) · Projects (brief per room, site measurement,
/// moodboard, BOQ with blanks, quotation, payment stages, vendor orders, schedule, snags, handover) · Rate card (HER rates only)
/// · Vendors · Niyam (firm, title, GST, design fee, stages, warranty words, terms).
/// The quote to the client, any vendor order (fingerprint once a phone key is set up), a change order that changes the price and
/// any payment request run only after HER tap. Hoola never invents a rate / size / brand price and never sends a message itself.
library;

import 'package:file_picker/file_picker.dart';
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
String _rs(dynamic v) => v == null ? '[daam?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'notes' || k == 'lines' || k == 'terms' ? 3 : 1),
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

/// A draft message she sends herself (WhatsApp / SMS).
Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']);
  if (wa.isEmpty && sms.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
  ]);
}

/// "WD1 56" / "Wardrobe 56 sqft @1650" / "FC1 naap" lines -> BOQ lines.
List<Map<String, dynamic>> _parseLines(String text, String room) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split('\n')) {
    final line = raw.trim();
    if (line.isEmpty) continue;
    final rate = RegExp(r'@\s*(\d+(?:\.\d+)?)').firstMatch(line);
    final qty = RegExp(r'(?<![@\d.])(\d+(?:\.\d+)?)\s*(sqft|rft|nos|point|sqm|set)?', caseSensitive: false).firstMatch(line.replaceAll(rate?.group(0) ?? '\u0000', ''));
    final word = line.split(RegExp(r'\s+')).first;
    final isCode = RegExp(r'^[A-Z]{1,4}\d{1,3}$').hasMatch(word);
    final name = line.split(RegExp(r'\d|@')).first.trim();
    out.add({
      'room': room,
      if (isCode) 'code': word else 'name': name.isEmpty ? line : name,
      if (qty != null && !line.toLowerCase().contains('naap')) 'qty': num.parse(qty.group(1)!),
      if (qty?.group(2) != null) 'unit': qty!.group(2)!.toLowerCase(),
      if (rate != null) 'rate': num.parse(rate.group(1)!),
    });
  }
  return out;
}

class InteriorScreen extends StatefulWidget {
  const InteriorScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<InteriorScreen> createState() => _InteriorScreenState();
}

class _InteriorScreenState extends State<InteriorScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/interior'));
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

  void _open(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => InteriorProjectPage(app: widget.app, id: id)))
      .then((_) => _load());

  Future<void> _newProject() async {
    final f = await _form(context, 'Naya project', const [
      ('name', 'Project ka naam (jaise Patil 2BHK)'),
      ('client', 'Client ka naam'),
      ('phone', 'Client ka phone'),
      ('site', 'Site ka pata'),
      ('city', 'Shahar'),
      ('pin', 'PIN code'),
      ('client_state', 'State code (GST, jaise 27)'),
      ('home', '2BHK / office / shop'),
      ('budget', 'Client ka budget (unke shabd)'),
      ('style', 'Style (modern / japandi / traditional ...)'),
      ('target_handover', 'Handover tareekh (DD-MM-YYYY)'),
    ]);
    if (f == null) return;
    final r = await _run('POST', '/api/interior/projects', {...f, if (f['budget'] != null) 'budget': _n(f['budget'])});
    final id = _s(_m(r?['project'])['id']);
    if (id.isNotEmpty && mounted) _open(id);
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    final w = _m(day['waiting']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(w['quotes']).isNotEmpty) const Caption('QUOTE: AAPKI HAAN'),
      for (final q in _list(w['quotes'])) Padding(padding: const EdgeInsets.only(bottom: 10),
          child: InteriorQuoteCard(app: widget.app, data: {'quote': q}, onDone: _load)),
      if (_list(w['orders']).isNotEmpty) const Caption('VENDOR ORDER: AAPKI HAAN'),
      for (final o in _list(w['orders'])) Padding(padding: const EdgeInsets.only(bottom: 10),
          child: InteriorOrderCard(app: widget.app, data: {'order': o}, onDone: _load)),
      if (_list(w['changes']).isNotEmpty) const Caption('BADLAV: AAPKI HAAN'),
      for (final c in _list(w['changes'])) Padding(padding: const EdgeInsets.only(bottom: 10),
          child: InteriorChangeCard(app: widget.app, data: {'change': c}, onDone: _load)),
      if (_list(w['payments']).isNotEmpty) const Caption('PAISE MAANGNA: AAPKI HAAN'),
      for (final p in _list(w['payments'])) Padding(padding: const EdgeInsets.only(bottom: 10),
          child: InteriorPaymentCard(app: widget.app, data: {'stage': p}, onDone: _load)),
      if (_strs(day['starting']).isNotEmpty) ...[const Caption('AAJ / KAL SHURU'), for (final x in _strs(day['starting'])) Text('• $x')],
      if (_strs(day['late']).isNotEmpty) ...[const SizedBox(height: 8), const Caption('DER SE'),
        for (final x in _strs(day['late'])) Text('• $x', style: const TextStyle(color: C.warn))],
    ]);
  }

  Widget _projects() {
    final ps = _list(_d?['projects']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Naya project', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newProject),
      const SizedBox(height: 12),
      if (ps.isEmpty) const Text('Abhi koi project nahi.', style: TextStyle(color: C.muted)),
      for (final p in ps)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Press(
            onTap: () => _open(_s(p['id'])),
            child: Glass(child: Row(children: [
              const Icon(Icons.chair_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(p['number'])} · ${_s(p['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text([_s(p['client']), _s(p['style_label']), if (_s(p['budget_text']).isNotEmpty) 'budget ${_s(p['budget_text'])}']
                    .where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(fontSize: 12.5, color: C.muted)),
              ])),
              Pill(_s(p['status_label'])),
            ])),
          ),
        ),
    ]);
  }

  Future<void> _addRate() async {
    final f = await _form(context, 'Rate card line (aapka rate)', const [
      ('name', 'Kaam / item (jaise Wardrobe BWP ply + laminate)'),
      ('rate', 'Aapka rate per unit (GST se pehle)'),
      ('unit', 'Unit: sqft / rft / nos / point / sqm / lumpsum'),
      ('code', 'Code (jaise WD1, chahein to)'),
      ('spec', 'Material / brand / finish (aapke shabd)'),
      ('gst_pct', 'GST % (khaali = aapka default)'),
    ]);
    if (f == null) return;
    await _run('POST', '/api/interior/rates', {...f, 'rate': _n(f['rate']), if (f['gst_pct'] != null) 'gst_pct': _n(f['gst_pct'])});
  }

  Future<void> _importRates() async {
    final pick = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['csv', 'xlsx'], withData: true);
    final file = pick?.files.firstOrNull;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/interior/rates/import', file.name, file.bytes!);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _rates() {
    final rs = _list(_d?['rates']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: GradientButton(label: 'Rate jodo', icon: Icons.add_rounded, height: 44, onTap: _busy ? null : _addRate)),
        const SizedBox(width: 8),
        GlassButton(label: 'Sheet', icon: Icons.upload_file_rounded, height: 44, onTap: _busy ? null : _importRates),
      ]),
      const SizedBox(height: 6),
      const Text('Sirf aapke rate. Jo rate yahan nahi, BOQ mein khaali rahega; Hoola daam nahi gadhta.',
          style: TextStyle(fontSize: 12, color: C.faint)),
      const SizedBox(height: 10),
      for (final r in rs)
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(r['code']).isEmpty ? '' : '${_s(r['code'])} · '}${_s(r['name'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${_s(r['kind_label'])} · ${_s(r['rate_text'])} / ${_s(r['unit'])}${_s(r['spec']).isEmpty ? '' : ' · ${_s(r['spec'])}'}',
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ])),
            IconButton(icon: const Icon(Icons.delete_outline_rounded, color: C.faint),
                onPressed: _busy ? null : () => _run('DELETE', '/api/interior/rates/${_s(r['id'])}')),
          ]),
        ),
    ]);
  }

  Widget _vendors() {
    final vs = _list(_d?['vendors']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Vendor jodo', icon: Icons.person_add_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Vendor / karigar', const [
          ('name', 'Naam'), ('trade', 'Kaam: carpenter / modular / electrician / painter / ceiling / flooring / fabricator / supplier'),
          ('phone', 'Phone'), ('notes', 'Note'),
        ]);
        if (f != null) await _run('POST', '/api/interior/vendors', f);
      }),
      const SizedBox(height: 10),
      for (final v in vs)
        Glass(margin: const EdgeInsets.only(bottom: 8), child: Row(children: [
          const Icon(Icons.handyman_rounded, color: C.teal),
          const SizedBox(width: 10),
          Expanded(child: Text('${_s(v['name'])} · ${_s(v['trade'])}\n${_s(v['phone'])}')),
        ])),
    ]);
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final stages = _list(st['stages']);
    final w = _m(st['warranty']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['firm']).isEmpty ? 'Firm ka naam nahi' : _s(st['firm']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('${_s(st['title'])}${_s(st['gstin']).isEmpty ? '' : ' · GSTIN ${_s(st['gstin'])}'}', style: const TextStyle(color: C.muted)),
        Text('Design fee: ${_s(st['fee_mode'])} ${_s(st['fee_value'])} · GST kaam ${_s(st['gst_works'])}% · design ${_s(st['gst_design'])}%',
            style: const TextStyle(fontSize: 12.5)),
        Text('UPI: ${_s(st['upi_id']).isEmpty ? '(Employee profile se)' : _s(st['upi_id'])}', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        GlassButton(label: 'Badlo', icon: Icons.edit_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Niyam', const [
            ('firm', 'Firm'), ('title', 'Title (Interior Designer)'), ('coa_reg', 'CoA no (sirf architect ho to)'), ('gstin', 'GSTIN'),
            ('address', 'Pata'), ('phone', 'Phone'), ('email', 'Email'), ('upi_id', 'UPI ID'),
            ('fee_mode', 'Design fee: none / percent / sqft / flat'), ('fee_value', 'Fee ka number'),
            ('gst_works', 'GST % kaam (CA se pakka)'), ('gst_design', 'GST % design fee'), ('validity_days', 'Quote kitne din valid'),
            ('terms', 'Terms'), ('morning_time', 'Subah ka note (HH:MM)'),
          ], initial: {for (final k in ['firm', 'title', 'coa_reg', 'gstin', 'address', 'phone', 'email', 'upi_id', 'fee_mode', 'terms', 'morning_time'])
            k: _s(st[k])});
          if (f == null) return;
          await _run('PUT', '/api/interior/settings', {
            ...f,
            for (final k in ['fee_value', 'gst_works', 'gst_design', 'validity_days']) if (f[k] != null) k: _n(f[k]),
          });
        }),
      ])),
      const SizedBox(height: 12),
      Caption(st['stages_starter'] == true ? 'PAYMENT STAGES (STARTER - AAPKE NIYAM SE BADLIYE)' : 'PAYMENT STAGES'),
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final s in stages) Text('• ${_s(s['label'])}: ${_s(s['pct'])}%'),
        const SizedBox(height: 8),
        GlassButton(label: 'Stages badlo', icon: Icons.tune_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Har line: naam = %', const [('lines', 'Booking = 10\nProduction = 50\nInstallation = 35\nHandover = 5')]);
          if (f == null) return;
          final out = <Map<String, dynamic>>[];
          for (final l in (f['lines'] ?? '').split('\n')) {
            final p = l.split('=');
            if (p.length == 2) out.add({'label': p[0].trim(), 'pct': _n(p[1])});
          }
          await _run('PUT', '/api/interior/settings', {'stages': out});
        }),
      ])),
      const SizedBox(height: 12),
      const Caption('WARRANTY (AAPKE SHABD, HANDOVER SHEET MEIN)'),
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (final e in w.entries) Text('• ${e.key}: ${_s(e.value)}'),
        if (w.isEmpty) const Text('Abhi kuch nahi likha.', style: TextStyle(color: C.muted)),
        const SizedBox(height: 8),
        GlassButton(label: 'Warranty likho', icon: Icons.verified_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Kaam ki warranty', const [('kind', 'Kaam (kitchen / wardrobe / false ceiling ...)'), ('text', 'Warranty aapke shabdon mein')]);
          if (f == null || f['kind'] == null) return;
          await _run('PUT', '/api/interior/settings', {'warranty': {f['kind']!: f['text'] ?? ''}});
        }),
      ])),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Projects', 'Rate card', 'Vendors', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Interior Sahayak'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: Column(children: [
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < tabs.length; i++)
              Padding(padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(label: Text(tabs[i]), selected: _tab == i, onSelected: (_) => setState(() => _tab = i))),
          ]),
        ),
        Expanded(
          child: _d == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _projects, _rates, _vendors, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class InteriorProjectPage extends StatefulWidget {
  const InteriorProjectPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<InteriorProjectPage> createState() => _InteriorProjectPageState();
}

class _InteriorProjectPageState extends State<InteriorProjectPage> {
  Map<String, dynamic>? _p;
  bool _busy = false;
  String get _base => '/api/interior/projects/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final p = _m(await widget.app.api!.call('GET', _base));
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

  Future<void> _brief() async {
    final f = await _form(context, 'Client ka brief', const [
      ('room', 'Kamra (khaali = poora ghar)'), ('room_type', 'Kamra kis kaam ka (bedroom / kitchen ...)'), ('style', 'Style'),
      ('budget', 'Budget (client ke shabd)'), ('must', 'Zaroor chahiye (comma se)'), ('avoid', 'Nahi chahiye (comma se)'), ('notes', 'Note'),
    ]);
    if (f == null) return;
    await _run('POST', '$_base/brief', {...f, if (f['budget'] != null) 'budget': _n(f['budget'])});
  }

  Future<void> _measure([String room = '']) async {
    final f = await _form(context, 'Site ka naap', const [
      ('room', 'Kamra'), ('l', 'Lambai (12, 12\'6", 3.6 m)'), ('w', 'Chaudai'), ('h', 'Unchai'),
      ('door', 'Darwaza: chaudai x unchai x ginti (3x7x1)'), ('window', 'Khidki: chaudai x unchai x ginti (5x4x2)'), ('by', 'Kisne naapa'),
    ], initial: {'room': room});
    if (f == null) return;
    List<Map<String, dynamic>> ops = [];
    for (final k in ['door', 'window']) {
      final v = f[k];
      if (v == null) continue;
      final p = v.toLowerCase().split('x').map((e) => e.trim()).toList();
      if (p.length >= 2) ops.add({'kind': k, 'w': p[0], 'h': p[1], 'count': p.length > 2 ? _n(p[2]) ?? 1 : 1});
    }
    await _run('POST', '$_base/measure', {'room': f['room'] ?? room, 'l': f['l'], 'w': f['w'], 'h': f['h'], 'by': f['by'] ?? '',
      if (ops.isNotEmpty) 'openings': ops});
  }

  Future<void> _concept(String room) async {
    final f = await _form(context, 'Moodboard', const [('style', 'Style (khaali = brief wala)'), ('words', 'Aur kuch (rang, mood)'),
      ('pictures', 'AI tasveerein 0-3 (AI se bana label ke saath)')], initial: {'pictures': '1'});
    if (f == null) return;
    final r = await _run('POST', '$_base/concept', {'room': room, ...f, 'pictures': int.tryParse(f['pictures'] ?? '0') ?? 0});
    if (r != null && mounted) {
      showModalBottomSheet(context: context, backgroundColor: C.bgBottom, isScrollControlled: true,
          builder: (_) => Padding(padding: const EdgeInsets.all(16), child: InteriorConceptCard(app: widget.app, data: {'concept': r['concept']})));
    }
  }

  Future<void> _boq() async {
    final rooms = _list(_p?['rooms']);
    final f = await _form(context, 'BOQ lines', [
      ('room', 'Kamra (${rooms.map((r) => _s(r['name'])).join(' / ')})'),
      ('lines', 'Har line: CODE qty, ya "Naam qty unit @rate".\n"FC1 naap" = naap se qty'),
    ]);
    if (f == null) return;
    final lines = _parseLines(f['lines'] ?? '', f['room'] ?? '');
    if (lines.isEmpty) return;
    await _run('POST', '$_base/boq', {'lines': lines});
  }

  Future<void> _snag() async {
    final f = await _form(context, 'Snag (kharabi)', const [('what', 'Kya kharabi'), ('room', 'Kamra'), ('vendor', 'Kiska kaam')]);
    if (f == null || f['what'] == null) return;
    XFile? x;
    try {
      x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 75, maxWidth: 1600);
    } catch (_) {}
    setState(() => _busy = true);
    try {
      if (x != null) {
        final bytes = await x.readAsBytes();
        final r = await widget.app.api!.uploadFile('$_base/snags', x.name.isEmpty ? 'snag.jpg' : x.name, bytes,
            fields: {'what': f['what']!, 'room': f['room'] ?? '', 'vendor': f['vendor'] ?? ''});
        if (mounted) _snack(context, _s(r['say']));
      } else {
        // the multipart route needs a form; without a photo send the fields only
        final r = await widget.app.api!.uploadFile('$_base/snags', 'none.txt', const [],
            fields: {'what': f['what']!, 'room': f['room'] ?? '', 'vendor': f['vendor'] ?? ''});
        if (mounted) _snack(context, _s(r['say']));
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _snagFixPhoto(String id) async {
    final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 75, maxWidth: 1600);
    if (x == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/interior/snags/$id/photo', x.name.isEmpty ? 'fixed.jpg' : x.name, await x.readAsBytes(),
          fields: {'stage': 'fixed'});
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _order() async {
    final vs = _list(_m(await widget.app.api!.call('GET', '/api/interior/vendors'))['vendors']);
    if (!mounted) return;
    final f = await _form(context, 'Vendor order', [
      ('vendor', 'Vendor (${vs.map((v) => _s(v['name'])).take(5).join(' / ')})'),
      ('lines', 'Har line: BOQ line id ya naam, qty, VENDOR ka rate\n(jaise "Lab12 @1500")'),
      ('amount', 'Ya kul rakam (vendor ka quote)'),
      ('start', 'Shuru (DD-MM-YYYY)'), ('finish', 'Khatam'), ('notes', 'Note'),
    ]);
    if (f == null) return;
    final lines = <Map<String, dynamic>>[];
    for (final raw in (f['lines'] ?? '').split('\n')) {
      final l = raw.trim();
      if (l.isEmpty) continue;
      final rate = RegExp(r'@\s*(\d+(?:\.\d+)?)').firstMatch(l);
      final id = l.split(RegExp(r'\s+')).first;
      final qty = RegExp(r'\s(\d+(?:\.\d+)?)(?:\s|$)').firstMatch(' $l ');
      lines.add({if (id.startsWith('L')) 'line': id else 'name': l.split('@').first.trim(), if (rate != null) 'rate': num.parse(rate.group(1)!),
        if (qty != null && !id.startsWith('L')) 'qty': num.parse(qty.group(1)!)});
    }
    await _run('POST', '$_base/orders', {'vendor': f['vendor'] ?? '', 'lines': lines, if (f['amount'] != null) 'amount': _n(f['amount']),
      'start': f['start'] ?? '', 'finish': f['finish'] ?? '', 'notes': f['notes'] ?? ''});
  }

  Future<void> _change() async {
    final f = await _form(context, 'Change order', const [('what', 'Badlav kya hai'), ('lines', 'Naye item: "Naam qty unit @rate" ya CODE qty'),
      ('remove', 'Hatane wali BOQ line ids (comma se)'), ('room', 'Kamra')]);
    if (f == null || f['what'] == null) return;
    await _run('POST', '$_base/changes', {'what': f['what'], 'add': _parseLines(f['lines'] ?? '', f['room'] ?? ''),
      'remove': (f['remove'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList()});
  }

  Future<void> _task() async {
    final f = await _form(context, 'Schedule mein kaam', const [('what', 'Kaam'), ('kind', 'Type (ceiling / electrical / wardrobe ...)'),
      ('room', 'Kamra'), ('vendor', 'Vendor'), ('start', 'Shuru (DD-MM-YYYY)'), ('end', 'Khatam')]);
    if (f == null) return;
    await _run('POST', '$_base/tasks', f);
  }

  Widget _section(String title, List<Widget> children, {Widget? action}) => Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Expanded(child: Caption(title)), if (action != null) action]),
          ...children,
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final p = _p;
    if (p == null) {
      return const Scaffold(backgroundColor: C.bgTop, body: Center(child: CircularProgressIndicator()));
    }
    final rooms = _list(p['rooms']);
    final boq = _list(p['boq']);
    final quotes = _list(p['quotes']);
    final stages = _list(p['stages']);
    final orders = _list(p['orders']);
    final sch = _m(p['schedule']);
    final snags = _list(p['snags']);
    final brief = _m(p['brief']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${_s(p['number'])} · ${_s(p['name'])}')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(p['client'])} · ${_s(p['phone'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
            Text('${_s(p['site'])} ${_s(p['city'])} ${_s(p['pin'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            Text('${_s(p['status_label'])} · ${_s(p['style_label'])}${p['contract_total'] == null ? '' : ' · kul ${_rs(p['contract_total'])}'}'
                '${_s(p['target_handover']).isEmpty ? '' : ' · handover ${_s(p['target_handover'])}'}', style: const TextStyle(fontSize: 12.5)),
            if (_strs(brief['must']).isNotEmpty) Text('Chahiye: ${_strs(brief['must']).join(', ')}', style: const TextStyle(fontSize: 12.5)),
          ])),
          _section('KAMRE + NAAP', [
            for (final r in rooms)
              Glass(margin: const EdgeInsets.only(bottom: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(r['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                Builder(builder: (_) {
                  final a = _m(r['areas']);
                  if (a.isEmpty) return const Text('Naap abhi nahi', style: TextStyle(color: C.warn, fontSize: 12.5));
                  return Text('Floor ${_s(a['floor_sqft'])} · deewar ${_s(a['wall_sqft'])} · skirting ${_s(a['skirting_rft'])} rft'
                      '${_strs(a['missing']).isEmpty ? '' : ' · baaki: ${_strs(a['missing']).join(', ')}'}', style: const TextStyle(fontSize: 12.5));
                }),
                if (_strs(r['must']).isNotEmpty) Text('Chahiye: ${_strs(r['must']).join(', ')}', style: const TextStyle(fontSize: 12)),
                Wrap(spacing: 8, children: [
                  TextButton(onPressed: _busy ? null : () => _measure(_s(r['name'])), child: const Text('Naap')),
                  TextButton(onPressed: _busy ? null : () => _concept(_s(r['name'])), child: const Text('Moodboard')),
                  TextButton(onPressed: _busy ? null : () => _run('POST', '$_base/render3d', {'room': _s(r['name'])}), child: const Text('3D')),
                ]),
              ])),
          ], action: Row(mainAxisSize: MainAxisSize.min, children: [
            IconButton(icon: const Icon(Icons.edit_note_rounded), tooltip: 'Brief', onPressed: _busy ? null : _brief),
            IconButton(icon: const Icon(Icons.straighten_rounded), tooltip: 'Naap', onPressed: _busy ? null : () => _measure()),
            IconButton(icon: const Icon(Icons.table_view_rounded), tooltip: 'Naap sheet', onPressed: _busy ? null : () => _run('POST', '$_base/measure_sheet')),
          ])),
          _section('BOQ (aapke rate)', [
            for (final c in boq)
              Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(
                  '${_s(c['id'])} · ${_s(c['room'])} · ${_s(c['name'])}: ${c['qty'] ?? '[qty?]'} ${_s(c['unit'])} x ${c['rate'] == null ? '[rate?]' : _rs(c['rate'])}'
                  ' = ${c['amount'] == null ? '—' : _rs(c['amount'])}${_s(c['co']).isEmpty ? '' : ' (${_s(c['co'])})'}',
                  style: TextStyle(fontSize: 12.5, color: _strs(c['blanks']).isEmpty ? C.ink : C.warn))),
            if (boq.isEmpty) const Text('Abhi khaali.', style: TextStyle(color: C.muted)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 6, children: [
              if (_s(p['contract_quote']).isEmpty)
                GlassButton(label: 'Lines jodo', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _boq)
              else
                GlassButton(label: 'Change order', icon: Icons.swap_horiz_rounded, height: 40, onTap: _busy ? null : _change),
              GlassButton(label: 'Excel', icon: Icons.grid_on_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/boq_file')),
              if (_s(p['contract_quote']).isEmpty)
                GradientButton(label: 'Quote banao', icon: Icons.request_quote_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/quote')),
            ]),
          ]),
          if (quotes.isNotEmpty)
            _section('QUOTATION', [
              for (final q in quotes.reversed.take(3))
                Padding(padding: const EdgeInsets.only(bottom: 8), child: InteriorQuoteCard(app: widget.app, data: {'quote': q}, onDone: _load)),
            ]),
          if (stages.isNotEmpty)
            _section('PAYMENT STAGES', [
              for (final s in stages)
                Padding(padding: const EdgeInsets.only(bottom: 8), child: InteriorPaymentCard(app: widget.app, data: {'stage': s}, onDone: _load)),
            ]),
          _section('VENDOR ORDERS', [
            for (final o in orders)
              Padding(padding: const EdgeInsets.only(bottom: 8), child: InteriorOrderCard(app: widget.app, data: {'order': o}, onDone: _load)),
          ], action: IconButton(icon: const Icon(Icons.add_shopping_cart_rounded), onPressed: _busy ? null : _order)),
          _section('SCHEDULE', [
            for (final t in _list(sch['tasks']))
              Row(children: [
                Expanded(child: Text('${_s(t['start'])} → ${_s(t['end'])} · ${_s(t['room'])} ${_s(t['what'])}${_s(t['vendor']).isEmpty ? '' : ' (${_s(t['vendor'])})'}',
                    style: const TextStyle(fontSize: 12.5))),
                PopupMenuButton<String>(
                  initialValue: _s(t['status']),
                  onSelected: (v) => _run('PATCH', '/api/interior/tasks/${_s(t['id'])}', {'status': v}),
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'started', child: Text('Shuru')),
                    PopupMenuItem(value: 'done', child: Text('Poora')),
                    PopupMenuItem(value: 'delayed', child: Text('Der')),
                    PopupMenuItem(value: 'cancelled', child: Text('Radd')),
                  ],
                  child: Pill(_s(t['status'])),
                ),
              ]),
            for (final x in _strs(sch['problems'])) Text('⚠ $x', style: const TextStyle(fontSize: 12, color: C.warn)),
          ], action: IconButton(icon: const Icon(Icons.event_rounded), onPressed: _busy ? null : _task)),
          _section('SNAGS', [
            for (final sn in snags)
              Glass(margin: const EdgeInsets.only(bottom: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('#${_s(sn['number'])} ${_s(sn['room'])}: ${_s(sn['what'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                if (_list(sn['photos']).isNotEmpty)
                  SizedBox(height: 72, child: ListView(scrollDirection: Axis.horizontal, children: [
                    for (final ph in _list(sn['photos']))
                      Padding(padding: const EdgeInsets.only(right: 6), child: ClipRRect(borderRadius: BorderRadius.circular(8),
                          child: Image.network(widget.app.api!.absolute('/api/interior/snags/${_s(sn['id'])}/photos/${_s(ph['id'])}'),
                              headers: widget.app.api!.authHeaders, width: 72, height: 72, fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const SizedBox(width: 72, child: Icon(Icons.broken_image_rounded))))),
                  ])),
                Wrap(spacing: 8, children: [
                  Pill(_s(sn['status'])),
                  TextButton(onPressed: _busy ? null : () => _snagFixPhoto(_s(sn['id'])), child: const Text('Theek ki photo')),
                  if (_s(sn['status']) != 'fixed') TextButton(onPressed: _busy ? null : () => _run('PATCH', '/api/interior/snags/${_s(sn['id'])}', {'status': 'fixed'}),
                      child: const Text('Theek hua')),
                  if (_s(sn['status']) != 'closed') TextButton(onPressed: _busy ? null : () => _run('PATCH', '/api/interior/snags/${_s(sn['id'])}', {'status': 'closed'}),
                      child: const Text('Band karo')),
                ]),
              ])),
          ], action: IconButton(icon: const Icon(Icons.add_a_photo_rounded), onPressed: _busy ? null : _snag)),
          const SizedBox(height: 16),
          if (_s(p['status']) != 'done')
            GradientButton(label: 'Handover + warranty sheet', icon: Icons.key_rounded, height: 46, onTap: _busy ? null : () async {
              final r = await _run('POST', '$_base/handover', {});
              if (r == null && mounted) {
                final f = await _form(context, 'Snag khule hain. Phir bhi?', const [('reason', 'Wajah (likhi jayegi)')], ok: 'Phir bhi handover');
                if (f != null && f['reason'] != null) await _run('POST', '$_base/handover', {'force': true, 'reason': f['reason']});
              }
            })
          else if (p['forgotten'] != true)
            GlassButton(label: 'Client ki details mitao (DPDP)', icon: Icons.privacy_tip_rounded, height: 44,
                onTap: _busy ? null : () => _run('POST', '$_base/forget')),
          const SizedBox(height: 30),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// interior_quote: the quotation going to the client waits for HER tap. Also in calls.
class InteriorQuoteCard extends StatefulWidget {
  const InteriorQuoteCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<InteriorQuoteCard> createState() => _InteriorQuoteCardState();
}

class _InteriorQuoteCardState extends State<InteriorQuoteCard> {
  bool _busy = false;
  late Map<String, dynamic> _q = _m(widget.data['quote']);
  Map<String, dynamic> _draft = {};

  Future<void> _post(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', path, body: body));
      if (mounted) {
        setState(() {
          if (_m(m['quote']).isNotEmpty) _q = _m(m['quote']);
          _draft = _m(m['draft']);
        });
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
    final q = _q, t = _m(q['totals']);
    final st = _s(q['status']);
    final id = _s(q['id']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.request_quote_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(q['number'])} · ${_s(q['client'])} · ${_s(q['total_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'draft' => 'draft', 'approved' => 'bhejne ko taiyaar', 'sent' => 'bheja',
            'accepted' => 'pakka', 'rejected' => 'nahi', _ => st }, fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('Kaam ${_rs(t['works'])}${(t['design_fee'] ?? 0) == 0 ? '' : ' + design fee ${_rs(t['design_fee'])}'} + GST ${_rs(t['tax'])}'
            '${t['intra'] == false ? ' (IGST)' : ' (CGST + SGST)'} · ${_s(q['valid_until'])} tak', style: const TextStyle(fontSize: 12.5)),
        for (final b in _strs(q['blanks'])) Text('⚠ $b', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (st == 'draft' && _strs(q['blanks']).isEmpty)
            GlassButton(label: 'Haan ke liye card', icon: Icons.send_rounded, height: 40,
                onTap: _busy ? null : () => _post('/api/interior/quotes/$id/request', {})),
          if (st == 'waiting') ...[
            GradientButton(label: 'Haan, client ko bhejo', height: 42,
                onTap: _busy ? null : () => _post('/api/interior/quotes/$id/decide', {'yes': true, 'hash': _s(q['hash'])})),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _post('/api/interior/quotes/$id/decide', {'yes': false, 'hash': _s(q['hash'])})),
          ],
          if (st == 'approved') GlassButton(label: 'Maine bhej diya', icon: Icons.check_rounded, height: 40,
              onTap: _busy ? null : () => _post('/api/interior/quotes/$id/mark', {'what': 'sent'})),
          if (st == 'approved' || st == 'sent') GlassButton(label: 'Client ne maana', icon: Icons.handshake_rounded, height: 40,
              onTap: _busy ? null : () => _post('/api/interior/quotes/$id/mark', {'what': 'accepted'})),
        ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Quote client ko sirf aapki haan se jaata hai; message aap khud bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// interior_order: a vendor work order waits for HER tap (+ fingerprint once a phone key is active). Also in calls.
class InteriorOrderCard extends StatefulWidget {
  const InteriorOrderCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<InteriorOrderCard> createState() => _InteriorOrderCardState();
}

class _InteriorOrderCardState extends State<InteriorOrderCard> {
  bool _busy = false;
  late Map<String, dynamic> _o = _m(widget.data['order']);
  Map<String, dynamic> _draft = {};

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/interior/orders/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Vendor order' : _s(show['title']),
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
    final id = _s(_o['id']);
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_o['hash'])};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/interior/orders/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/interior/orders/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['order']).isNotEmpty) _o = _m(m['order']);
          _draft = _m(m['draft']);
        });
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
    final o = _o;
    final st = _s(o['status']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.handyman_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(o['number'])} · ${_s(o['vendor'])} · ${_s(o['amount_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'maana', 'done' => 'poora', 'rejected' => 'nahi', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(o['project'])}${_s(o['start']).isEmpty ? '' : ' · ${_s(o['start'])} → ${_s(o['finish'])}'}', style: const TextStyle(fontSize: 12.5)),
        for (final l in _list(o['lines']))
          Text('• ${_s(l['name'])}: ${_s(l['qty'])} ${_s(l['unit'])} x ${_rs(l['rate'])}', style: const TextStyle(fontSize: 12)),
        for (final c in _strs(o['checks'])) Text('⚠ $c', style: const TextStyle(fontSize: 12.5, color: C.warn)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, order do', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (st == 'approved')
          GlassButton(label: 'Kaam poora', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () async {
            await _call(context, widget.app, 'POST', '/api/interior/orders/${_s(o['id'])}/done');
            widget.onDone?.call();
          }),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola khud paise nahi deta; vendor ko message aap bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// interior_change: a change order that changes the price waits for HER tap. Also in calls.
class InteriorChangeCard extends StatefulWidget {
  const InteriorChangeCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<InteriorChangeCard> createState() => _InteriorChangeCardState();
}

class _InteriorChangeCardState extends State<InteriorChangeCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['change']);
  Map<String, dynamic> _draft = {};

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', '/api/interior/changes/${_s(_c['id'])}/decide', body: {'yes': yes, 'hash': _s(_c['hash'])}));
      if (mounted) {
        setState(() {
          if (_m(m['change']).isNotEmpty) _c = _m(m['change']);
          _draft = _m(m['draft']);
        });
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
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.swap_horiz_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['number'])} · ${_s(c['project'])} · ${_s(c['delta_text'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(st == 'waiting' ? 'aapki haan?' : st, fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text(_s(c['what']), style: const TextStyle(fontSize: 13)),
        for (final a in _list(c['add'])) Text('+ ${_s(a['name'])}: ${_s(a['qty'])} ${_s(a['unit'])} x ${_rs(a['rate'])}', style: const TextStyle(fontSize: 12)),
        for (final r in _strs(c['remove'])) Text('− line $r', style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, badlav maano', height: 42, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
      ]),
    );
  }
}

/// interior_payment: a payment stage; asking the client for money waits for HER tap. Also in calls.
class InteriorPaymentCard extends StatefulWidget {
  const InteriorPaymentCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<InteriorPaymentCard> createState() => _InteriorPaymentCardState();
}

class _InteriorPaymentCardState extends State<InteriorPaymentCard> {
  bool _busy = false;
  late Map<String, dynamic> _x = _m(widget.data['stage']);
  Map<String, dynamic> _draft = {};

  Future<void> _post(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final m = _m(await widget.app.api!.call('POST', path, body: body));
      if (mounted) {
        setState(() {
          if (_m(m['stage']).isNotEmpty) _x = _m(m['stage']);
          _draft = _m(m['draft']);
        });
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
    final id = _s(x['id']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.payments_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(x['project'])} · ${_s(x['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'requested' => 'maanga', 'paid' => 'mila', 'planned' => 'baaki', _ => st },
              fg: st == 'paid' ? C.ok : (st == 'waiting' ? C.accent : C.chip)),
        ]),
        Text('${_s(x['amount_text'])}${x['pct'] == null ? '' : ' (${_s(x['pct'])}%)'}${_s(x['due_on']).isEmpty ? '' : ' · ${_s(x['due_on'])} tak'}'
            '${st == 'paid' ? ' · mila ${_rs(x['paid_amount'])} ${_s(x['paid_ref'])}' : ''}', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (st == 'planned' || st == 'requested')
            GlassButton(label: st == 'requested' ? 'Dobara maango' : 'Client se maango', icon: Icons.send_rounded, height: 40,
                onTap: _busy ? null : () => _post('/api/interior/stages/$id/request', {})),
          if (st == 'waiting') ...[
            GradientButton(label: 'Haan, maango', height: 42,
                onTap: _busy ? null : () => _post('/api/interior/stages/$id/decide', {'yes': true, 'hash': _s(x['hash'])})),
            GlassButton(label: 'Abhi nahi', height: 42, onTap: _busy ? null : () => _post('/api/interior/stages/$id/decide', {'yes': false, 'hash': _s(x['hash'])})),
          ],
          if (st != 'paid')
            GlassButton(label: 'Paise mile', icon: Icons.check_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Paise mile', const [('amount', 'Kitne mile'), ('ref', 'UTR / cheque no')], initial: {'amount': _s(x['amount'])});
              if (f != null) await _post('/api/interior/stages/$id/paid', {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''});
            }),
        ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola paise nahi leta; client apne UPI app se aapko dete hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// interior_concept: the moodboard (palette, her photos, AI pictures labelled). Calls: no.
class InteriorConceptCard extends StatelessWidget {
  const InteriorConceptCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  Color _hex(String h) {
    final v = int.tryParse(h.replaceAll('#', ''), radix: 16);
    return v == null ? C.panel : Color(0xFF000000 | v);
  }

  @override
  Widget build(BuildContext context) {
    final c = _m(data['concept']);
    final items = _list(c['items']);
    return Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      Text('${_s(c['project'])} · ${_s(c['room'])} · ${_s(c['style'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      Row(children: [for (final h in _strs(c['palette'])) Expanded(child: Container(height: 28, color: _hex(h)))]),
      Text(_s(c['palette_from']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
      Text('Material: ${_strs(c['materials']).join(', ')}', style: const TextStyle(fontSize: 12.5)),
      if (items.isNotEmpty) Text('${items.length} tasveer (${items.where((i) => i['ai'] == true).length} AI se bani)', style: const TextStyle(fontSize: 12.5)),
      for (final n in _strs(c['notes'])) Text('⚠ $n', style: const TextStyle(fontSize: 12, color: C.warn)),
      Text(_s(c['ai_note']), style: const TextStyle(fontSize: 11, color: C.faint)),
    ]));
  }
}

/// interior_alert / interior_day: plain notes. Calls: no.
class InteriorNoteCard extends StatelessWidget {
  const InteriorNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          const Icon(Icons.chair_rounded, color: C.teal),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
          IconButton(
              icon: const Icon(Icons.open_in_new_rounded, color: C.faint),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InteriorScreen(app: app)))),
        ]),
      );
}
