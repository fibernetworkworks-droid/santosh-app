/// Profile > Graphic Sahayak: Hoola as a freelance graphic designer's / studio's client desk.
/// Aaj (late / due / feedback / proofs waiting / unpaid, cards) · Kaam (jobs -> GraphicJobPage: brief, price lines, rounds,
/// proofs from the brand engine in the client's kit or her own design file with print checks, client feedback, fonts /
/// pictures licences, trade-mark search help, quote / proof / extra round / handover / print order / invoice cards)
/// · Clients (their brand kits + logo) · Printer (vendor specs) · Niyam (studio, GST, rounds, advance, copyright).
/// Everything that goes out waits for HER tap; a discount needs her fingerprint once a phone key is set up.
library;

import 'package:file_picker/file_picker.dart';
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
String _rs(dynamic v) => v == null ? '[price?]' : '₹${(v is num ? v : num.tryParse('$v') ?? 0).toStringAsFixed(0)}';

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Next', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label),
                maxLines: (k == 'text' || k == 'brief' || k == 'facts' || k == 'terms' || k == 'lines' || k == 'evidence') ? 4 : 1),
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

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']), mail = _s(draft['mail']), upi = _s(draft['upi']);
  if (wa.isEmpty && sms.isEmpty && mail.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (mail.isNotEmpty) GlassButton(label: 'Email', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (upi.isNotEmpty) const Pill('UPI link of your UPI ID'),
  ]);
}

Widget _img(Santosh app, String path, {double height = 160}) {
  if (path.isEmpty) return const SizedBox.shrink();
  return ClipRRect(
    borderRadius: BorderRadius.circular(14),
    child: Image.network(app.api!.absolute(path), headers: app.api!.authHeaders, height: height, fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => SizedBox(height: height, child: const Center(child: Icon(Icons.image_not_supported_rounded)))),
  );
}

List<Map<String, dynamic>> _parseLines(String text) {
  final out = <Map<String, dynamic>>[];
  for (final raw in text.split('\n')) {
    final t = raw.trim();
    if (t.isEmpty) continue;
    final m = RegExp(r'^(.+?)\s*[-:@]\s*(?:rs\.?|₹)?\s*([\d,.]+)\s*$', caseSensitive: false).firstMatch(t);
    out.add(m == null ? {'name': t} : {'name': m.group(1), 'rate': _n(m.group(2))});
  }
  return out;
}

class GraphicScreen extends StatefulWidget {
  const GraphicScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<GraphicScreen> createState() => _GraphicScreenState();
}

class _GraphicScreenState extends State<GraphicScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/graphic'));
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
      .push(MaterialPageRoute(builder: (_) => GraphicJobPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _jobTile(Map<String, dynamic> j) {
    final r = _m(j['rounds']);
    return Glass(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => _open(_s(j['number'])),
        child: Row(children: [
          const Icon(Icons.brush_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(j['number'])} · ${_s(j['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text('${_s(j['client'])} · ${_s(j['kind_label'])}${_s(j['due']).isEmpty ? '' : ' · due ${_s(j['due'])}'}',
                style: const TextStyle(fontSize: 12, color: C.muted)),
            Text('Round ${_s(r['used'])}/${(r['included'] ?? 0) + (r['extra'] ?? 0) + (r['waived'] ?? 0)}'
                '${r['pending_feedback'] == true ? ' · feedback received' : ''}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ])),
          Pill(_s(j['status_label'])),
        ]),
      ),
    );
  }

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('WAITING FOR YOUR YES'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: GraphicCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('late', 'LATE'), ('today', 'DUE TODAY'), ('soon', 'DUE SOON'), ('feedback', 'FEEDBACK RECEIVED'),
        ('waiting_client', 'WAITING FOR CLIENT\'S REPLY'), ('unpaid', 'PAYMENT DUE')])
        if (_list(day[k]).isNotEmpty) ...[Caption(label), for (final j in _list(day[k])) _jobTile(j), const SizedBox(height: 8)],
    ]);
  }

  Future<void> _newJob() async {
    final cl = _list(_d?['clients']);
    if (cl.isEmpty) {
      _snack(context, 'First add a client (Clients tab).');
      return;
    }
    final f = await _form(context, 'New job', const [
      ('client', 'Client (name or C-001)'), ('title', 'Job name'), ('kind', 'Kind: logo / social / poster / visiting_card ...'),
      ('brief', 'Brief (in the client\'s words)'), ('facts', 'What to write on the design (only the truth)'), ('due', 'Due date (YYYY-MM-DD)'),
      ('lines', 'Price: in one line "job - 3000"'), ('rounds', 'Revision rounds'), ('extra_round_price', 'Extra round price'),
    ], initial: {'client': _s(cl.first['number'])});
    if (f == null || f['client'] == null) return;
    final body = <String, dynamic>{
      'client': f['client'],
      if (f['title'] != null) 'title': f['title'],
      if (f['kind'] != null) 'kind': f['kind'],
      if (f['brief'] != null) 'brief': f['brief'],
      if (f['facts'] != null) 'facts': f['facts'],
      if (f['due'] != null) 'due': f['due'],
      if (f['lines'] != null) 'lines': _parseLines(f['lines']!),
      if (_n(f['rounds']) != null) 'rounds': _n(f['rounds']),
      if (_n(f['extra_round_price']) != null) 'extra_round_price': _n(f['extra_round_price']),
    };
    final r = await _run('POST', '/api/graphic/jobs', body);
    final jobNo = _s(_m(r?['job'])['number']);
    if (jobNo.isNotEmpty) _open(jobNo);
  }

  Widget _kaam() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New job', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newJob),
        const SizedBox(height: 12),
        for (final j in _list(_d?['jobs'])) _jobTile(j),
        if (_list(_d?['jobs']).isEmpty) const Text('No open jobs yet.', style: TextStyle(color: C.muted)),
      ]);

  Future<void> _clientForm([Map<String, dynamic>? c]) async {
    final f = await _form(context, c == null ? 'New client' : 'Change client', const [
      ('name', 'Name'), ('business', 'Business / brand'), ('phone', 'Phone'), ('email', 'Email'), ('kind', 'business / individual'),
      ('gstin', 'GSTIN'), ('state', 'State (MH / 27)'), ('tagline', 'Tagline'), ('primary', 'Main colour (#hex or red / blue)'),
      ('accent', 'Second colour'), ('tds_pct', 'How much TDS the client will deduct (%)'),
    ], initial: c == null ? const {} : {for (final k in ['name', 'business', 'phone', 'email', 'kind', 'gstin', 'state', 'tagline']) k: _s(c[k])});
    if (f == null) return;
    final body = <String, dynamic>{
      for (final k in ['name', 'business', 'phone', 'email', 'kind', 'gstin', 'state', 'tagline']) if (f[k] != null) k: f[k],
      if (f['primary'] != null || f['accent'] != null)
        'colors': {if (f['primary'] != null) 'primary': f['primary'], if (f['accent'] != null) 'accent': f['accent']},
      if (_n(f['tds_pct']) != null) 'tds_pct': _n(f['tds_pct']),
    };
    if (c == null) {
      await _run('POST', '/api/graphic/clients', body);
    } else {
      await _run('PATCH', '/api/graphic/clients/${_s(c['number'])}', body);
    }
  }

  Future<void> _logo(Map<String, dynamic> c) async {
    final pick = await FilePicker.platform.pickFiles(type: FileType.image, withData: true);
    final file = pick?.files.firstOrNull;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/graphic/clients/${_s(c['number'])}/logo', file.name, file.bytes!);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _clients() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New client', icon: Icons.person_add_rounded, height: 46, onTap: _busy ? null : () => _clientForm()),
        const SizedBox(height: 12),
        for (final c in _list(_d?['clients']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: Row(children: [
              Icon(c['logo'] == true ? Icons.verified_rounded : Icons.storefront_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(c['number'])} · ${_s(c['name'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${_s(c['business'])}${c['forgotten'] == true ? ' · (removed)' : ''}', style: const TextStyle(fontSize: 12, color: C.muted)),
              ])),
              PopupMenuButton<String>(
                onSelected: (v) async {
                  if (v == 'edit') await _clientForm(c);
                  if (v == 'logo') await _logo(c);
                  if (v == 'forget') await _run('POST', '/api/graphic/clients/${_s(c['number'])}/forget');
                },
                itemBuilder: (_) => const [
                  PopupMenuItem(value: 'edit', child: Text('Change / brand kit')),
                  PopupMenuItem(value: 'logo', child: Text('Add logo')),
                  PopupMenuItem(value: 'forget', child: Text('Delete details (DPDP)')),
                ],
              ),
            ]),
          ),
      ]);

  Future<void> _vendorForm() async {
    final f = await _form(context, 'Printer', const [
      ('name', 'Name'), ('phone', 'Phone'), ('does', 'What they print'), ('color', 'Colour: cmyk / rgb'), ('dpi', 'DPI'),
      ('bleed', 'Bleed mm'), ('safe', 'Safe margin mm'), ('format', 'File: pdf / jpg'),
    ], initial: const {'color': 'cmyk', 'dpi': '300', 'bleed': '3', 'safe': '4', 'format': 'pdf'});
    if (f == null || f['name'] == null) return;
    await _run('POST', '/api/graphic/vendors', {
      'name': f['name'], 'phone': f['phone'] ?? '', 'does': f['does'] ?? '',
      'spec': {'color': f['color'] ?? 'cmyk', 'dpi': _n(f['dpi']), 'bleed': _n(f['bleed']), 'safe': _n(f['safe']), 'format': f['format'] ?? 'pdf'},
    });
  }

  Widget _printers() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Add printer', icon: Icons.print_rounded, height: 46, onTap: _busy ? null : _vendorForm),
        const SizedBox(height: 12),
        for (final v in _list(_d?['vendors']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(v['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${_s(v['phone'])} · ${_s(v['does'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
              Text(_m(v['spec']).entries.map((e) => '${e.key} ${e.value}').join(' · '), style: const TextStyle(fontSize: 11.5, color: C.faint)),
            ]),
          ),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['studio']).isEmpty ? 'No studio name' : _s(st['studio']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('Designer: ${_s(st['designer'])} · GSTIN ${_s(st['gstin']).isEmpty ? 'none' : st['gstin']} · SAC ${_s(st['sac'])}'),
        Text('Rounds ${_s(st['rounds'])} · extra round ${_rs(st['extra_round'])} · advance ${_s(st['advance_pct'])}%'),
        Text('UPI: ${_s(st['upi_id'])} · Files after payment: ${st['handover_after_pay'] == true ? 'yes' : 'no'}'),
        Text('Written copyright assignment: ${st['assign_copyright'] == true ? 'yes' : 'no'}', style: const TextStyle(fontSize: 12, color: C.muted)),
      ])),
      const SizedBox(height: 10),
      GlassButton(
        label: 'Change rules',
        icon: Icons.tune_rounded,
        onTap: () async {
          final f = await _form(context, 'Studio rules', const [
            ('studio', 'Studio'), ('designer', 'Your name (for copyright)'), ('gstin', 'GSTIN'), ('state', 'State'),
            ('upi_id', 'UPI ID'), ('phone', 'Phone'), ('email', 'Email'), ('rounds', 'Revision rounds (default)'),
            ('extra_round', 'Extra round price'), ('advance_pct', 'Advance %'), ('udyam', 'Udyam number (MSME)'), ('terms', 'Terms'),
          ], initial: {for (final k in ['studio', 'designer', 'gstin', 'state', 'upi_id', 'phone', 'email', 'udyam', 'terms']) k: _s(st[k]),
            'rounds': _s(st['rounds']), 'advance_pct': _s(st['advance_pct']), 'extra_round': _s(st['extra_round'])});
          if (f == null) return;
          await _run('PUT', '/api/graphic/settings', {
            for (final k in ['studio', 'designer', 'gstin', 'state', 'upi_id', 'phone', 'email', 'udyam', 'terms']) if (f[k] != null) k: f[k],
            if (_n(f['rounds']) != null) 'rounds': _n(f['rounds']),
            if (_n(f['advance_pct']) != null) 'advance_pct': _n(f['advance_pct']),
            if (f['extra_round'] != null) 'extra_round': _n(f['extra_round']),
          });
        },
      ),
      const SizedBox(height: 12),
      const Text('Fonts: you may give Google Fonts (OFL) as files; Adobe Fonts / bought fonts go to the client in PDF / outline, not as files. '
          '"Personal use only" fonts are not allowed in client work. You do the logo trademark search on IP India yourself.',
          style: TextStyle(fontSize: 12, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Today', 'Job', 'Clients', 'Printer', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Graphic designer'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _kaam, _clients, _printers, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

/// One job: brief, money, rounds, versions with proofs + checks, assets, trade-mark, card buttons.
class GraphicJobPage extends StatefulWidget {
  const GraphicJobPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<GraphicJobPage> createState() => _GraphicJobPageState();
}

class _GraphicJobPageState extends State<GraphicJobPage> {
  Map<String, dynamic>? _j;
  bool _busy = false;
  String get _base => '/api/graphic/jobs/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final j = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _j = j);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _act(String what, [Map<String, dynamic>? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '$_base/$what', body ?? const {});
    await _load();
    if (mounted) setState(() => _busy = false);
    if (r != null && _m(r['card']).isNotEmpty && mounted) {
      await showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: C.bgBottom,
          builder: (_) => Padding(padding: const EdgeInsets.all(16),
              child: SingleChildScrollView(child: GraphicCardCard(app: widget.app, data: {'card': r['card']}, onDone: _load))));
    }
    return r;
  }

  Future<void> _upload() async {
    final pick = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff'],
        withData: true);
    final file = pick?.files.firstOrNull;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('$_base/upload', file.name, file.bytes!);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _version(Map<String, dynamic> v) {
    final proofs = _m(v['proofs']);
    final checks = _list(v['checks']);
    return Glass(
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('v${_s(v['n'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(width: 8),
          Pill(_s(v['source']) == 'upload' ? 'your file' : 'Hoola engine'),
          const SizedBox(width: 6),
          Pill('round ${_s(v['round'])}'),
          const Spacer(),
          Pill(_s(v['status']), fg: _s(v['status']) == 'client_ok' ? C.ok : C.chip),
        ]),
        const SizedBox(height: 8),
        if (proofs.isNotEmpty)
          SizedBox(
            height: 170,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final p in proofs.values) Padding(padding: const EdgeInsets.only(right: 8), child: _img(widget.app, _s(p))),
            ]),
          ),
        for (final c in checks)
          Text('${_s(c['level']) == 'block' ? '⛔' : _s(c['level']) == 'warn' ? '⚠️' : 'ℹ️'} ${_s(c['text'])}',
              style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 6, children: [
          if (_s(v['status']) != 'old')
            GlassButton(label: 'Send to client', icon: Icons.send_rounded, height: 38,
                onTap: _busy ? null : () => _act('proof', {'version': v['n']})),
          if (_s(v['status']) == 'sent')
            GlassButton(label: 'Client said yes', icon: Icons.thumb_up_rounded, height: 38, onTap: _busy ? null : () async {
              final f = await _form(context, 'Client\'s yes', const [('evidence', 'Their message / talk')]);
              if (f?['evidence'] != null) await _act('client_ok', {'version': v['n'], 'evidence': f!['evidence']});
            }),
          if (_s(v['status']) == 'sent')
            GlassButton(label: 'Client\'s changes', icon: Icons.edit_note_rounded, height: 38, onTap: _busy ? null : () async {
              final f = await _form(context, 'What the client said', const [('text', 'Their words')]);
              if (f?['text'] != null) await _act('feedback', {'version': v['n'], 'text': f!['text']});
            }),
        ]),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final j = _j;
    if (j == null) {
      return Scaffold(backgroundColor: C.bgTop, appBar: AppBar(title: Text(widget.ref)), body: const Center(child: CircularProgressIndicator()));
    }
    final q = _m(j['quote']);
    final r = _m(j['rounds']);
    final tm = _m(j['tm']);
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${_s(j['number'])} · ${_s(j['title'])}'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(j['client'])} · ${_s(j['kind_label'])} · ${_s(j['status_label'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
            if (_s(j['due']).isNotEmpty) Text('Due: ${_s(j['due'])}'),
            if (_s(j['brief']).isNotEmpty) Text('Brief: ${_s(j['brief'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
            if (_s(j['facts']).isNotEmpty) Text('On design: ${_s(j['facts'])}', style: const TextStyle(fontSize: 12.5)),
            const SizedBox(height: 6),
            Text('Revision: ${_s(r['used'])} used ·${_s(r['left'])} left (quote ${_s(r['included'])}, extra ${_s(r['extra'])})'
                '${r['pending_feedback'] == true ? ' · new feedback' : ''}'),
            const SizedBox(height: 6),
            for (final ln in _list(q['lines'])) Text('• ${_s(ln['name'])}: ${_rs(ln['amount'])}', style: const TextStyle(fontSize: 12.5)),
            Text('Total: ${_s(q['total_text'])} · advance ${_s(q['advance_text'])} · paid ${_rs(j['paid'])} · balance${_rs(j['balance'])}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            if (_strs(q['missing']).isNotEmpty) Text('Balance: ${_strs(q['missing']).join(', ')}', style: const TextStyle(color: C.warn)),
            if (_s(q['tds_note']).isNotEmpty) Text(_s(q['tds_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
          ])),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Price / rounds', icon: Icons.currency_rupee_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Price and rounds', const [
                ('lines', 'In one line "job - 3000"'), ('rounds', 'Revision rounds'), ('extra_round_price', 'Extra round price'),
                ('advance_pct', 'Advance %'), ('due', 'Due date')]);
              if (f == null) return;
              setState(() => _busy = true);
              await _call(context, widget.app, 'PATCH', _base, {
                if (f['lines'] != null) 'lines': _parseLines(f['lines']!),
                if (_n(f['rounds']) != null) 'rounds': _n(f['rounds']),
                if (f['extra_round_price'] != null) 'extra_round_price': _n(f['extra_round_price']),
                if (_n(f['advance_pct']) != null) 'advance_pct': _n(f['advance_pct']),
                if (f['due'] != null) 'due': f['due'],
              });
              await _load();
              if (mounted) setState(() => _busy = false);
            }),
            GlassButton(label: 'Quote card', icon: Icons.request_quote_rounded, height: 40, onTap: _busy ? null : () => _act('quote')),
            GlassButton(label: 'Client accepted the quote', icon: Icons.handshake_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Quote maana', const [('evidence', 'Their message')]);
              if (f?['evidence'] != null) await _act('accepted', {'evidence': f!['evidence']});
            }),
            GlassButton(label: 'Make proof', icon: Icons.auto_awesome_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Proof (Hoola engine, client\'s colours)', const [('instruction', 'Changes (blank = new)')]);
              if (f == null) return;
              await _act('render', {if (f['instruction'] != null) 'instruction': f['instruction']});
            }),
            GlassButton(label: 'Add your own file', icon: Icons.upload_file_rounded, height: 40, onTap: _busy ? null : _upload),
            GlassButton(label: 'Extra round card', icon: Icons.add_card_rounded, height: 40, onTap: _busy ? null : () => _act('extra')),
            GlassButton(label: 'Free this time', icon: Icons.redeem_rounded, height: 40, onTap: _busy ? null : () => _act('waive', {'reason': 'owner'})),
          ]),
          const SizedBox(height: 14),
          const Caption('VERSIONS / PROOF'),
          for (final v in _list(j['version_list']).reversed) _version(v),
          if (_list(j['version_list']).isEmpty) const Text('No proofs yet.', style: TextStyle(color: C.muted)),
          const SizedBox(height: 10),
          const Caption('FONT / PHOTO LICENCE'),
          for (final a in _list(j['assets']))
            Text('• ${_s(a['name'])}: ${_s(_m(a['verdict'])['say'])}', style: const TextStyle(fontSize: 12.5)),
          GlassButton(label: 'Add font / photo', icon: Icons.font_download_rounded, height: 38, onTap: _busy ? null : () async {
            final f = await _form(context, 'Asset', const [('name', 'Name'), ('kind', 'font / image / icon'), ('source', 'Where from (Google Fonts, Adobe, stock ...)'),
              ('licence', 'Licence (ofl / adobe_fonts / commercial / stock_paid / own / ai ...)'), ('licence_ref', 'Licence number')]);
            if (f?['name'] != null) await _act('asset', f);
          }),
          if (_s(j['kind']) == 'logo') ...[
            const SizedBox(height: 10),
            const Caption('TRADE-MARK SEARCH (IP INDIA)'),
            Text(tm.isEmpty ? 'Not done yet.' : 'Result: ${_s(tm['result'])} · class ${_strs(tm['classes']).join(', ')}',
                style: const TextStyle(fontSize: 12.5)),
            Wrap(spacing: 8, children: [
              GlassButton(label: 'How to do it', icon: Icons.search_rounded, height: 38, onTap: () async {
                final h = await _call(context, widget.app, 'GET', '$_base/tm_help');
                if (h == null || !mounted) return;
                await showDialog(context: context, builder: (d) => AlertDialog(
                  title: const Text('IP India public search'),
                  content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    for (final s in _strs(h['steps'])) Text('• $s'),
                    const SizedBox(height: 8),
                    Text(_s(h['note']), style: const TextStyle(fontSize: 12)),
                  ])),
                  actions: [
                    TextButton(onPressed: () => Native.openExternal(url: _strs(h['links']).first), child: const Text('Open site')),
                    TextButton(onPressed: () => Navigator.pop(d), child: const Text('OK')),
                  ],
                ));
              }),
              GlassButton(label: 'Write the result', icon: Icons.fact_check_rounded, height: 38, onTap: () async {
                final f = await _form(context, 'Search result', const [
                  ('result', 'nothing_similar / similar_found / registered_same'), ('classes', 'Class (for example 30, 35)'), ('notes', 'What was found')]);
                if (f?['result'] == null) return;
                await _act('tm', {'result': f!['result'], 'notes': f['notes'] ?? '',
                  'classes': (f['classes'] ?? '').split(RegExp(r'[,\s]+')).map((e) => int.tryParse(e)).whereType<int>().toList()});
              }),
            ]),
          ],
          const SizedBox(height: 14),
          const Caption('JOBS GOING OUT (YOUR YES)'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Final files card', icon: Icons.inventory_2_rounded, height: 40, onTap: _busy ? null : () => _act('handover')),
            GlassButton(label: 'Print order card', icon: Icons.print_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Print order', const [('vendor', 'Printer name'), ('qty', 'How many copies'), ('stock', 'Paper'), ('finish', 'Finish')]);
              if (f == null) return;
              if (f['qty'] != null || f['stock'] != null || f['finish'] != null) {
                await _call(context, widget.app, 'PATCH', _base, {'print_job': {'qty': f['qty'], 'stock': f['stock'], 'finish': f['finish']}});
              }
              await _act('vendor', {'vendor': f['vendor'] ?? ''});
            }),
            GlassButton(label: 'Advance invoice', icon: Icons.receipt_rounded, height: 40, onTap: _busy ? null : () => _act('invoice', {'what': 'advance'})),
            GlassButton(label: 'Final invoice', icon: Icons.receipt_long_rounded, height: 40, onTap: _busy ? null : () => _act('invoice', {'what': 'final'})),
            GlassButton(label: 'Discount', icon: Icons.percent_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Discount', const [('amount', 'Amount'), ('reason', 'Why')]);
              if (_n(f?['amount']) != null) await _act('discount', {'amount': _n(f!['amount']), 'reason': f['reason'] ?? ''});
            }),
            GlassButton(label: 'Message', icon: Icons.chat_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Message to client', const [('text', 'Message')]);
              if (f?['text'] != null) await _act('message', {'text': f!['text']});
            }),
            GlassButton(label: 'Money received', icon: Icons.payments_rounded, height: 40, onTap: _busy ? null : () async {
              final f = await _form(context, 'Money received', const [('amount', 'How many'), ('mode', 'upi / cash / bank'), ('ref', 'Last digits of UTR')]);
              if (_n(f?['amount']) != null) await _act('paid', {'amount': _n(f!['amount']), 'mode': f['mode'] ?? 'upi', 'ref': f['ref'] ?? ''});
            }),
            GlassButton(label: 'Complete', icon: Icons.done_all_rounded, height: 40, onTap: _busy ? null : () => _act('done')),
          ]),
          const SizedBox(height: 12),
          const Caption('LOG'),
          for (final l in _list(j['log']).reversed.take(12))
            Text('${_s(l['at']).substring(0, _s(l['at']).length >= 16 ? 16 : _s(l['at']).length)} · ${_s(l['what'])}',
                style: const TextStyle(fontSize: 11.5, color: C.faint)),
          const SizedBox(height: 30),
        ]),
      ),
    );
  }
}

/// graphic_card: quote / proof / extra round / handover / print order / invoice / discount / message — HER tap only.
class GraphicCardCard extends StatefulWidget {
  const GraphicCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<GraphicCardCard> createState() => _GraphicCardCardState();
}

class _GraphicCardCardState extends State<GraphicCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/graphic/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Design' : _s(show['title']),
        [show['amount'], show['payee']].where((x) => x != null && '$x'.isNotEmpty).join(' · '));
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'Fingerprint was not given, so approval did not happen.',
        'key_invalidated' => 'A new fingerprint was added on this phone: go to Profile > Approve with fingerprint and connect the phone again.',
        _ => 'Approval by fingerprint did not work (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Why not?', const [('reason', 'Reason (optional)')], ok: 'No');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/graphic/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/graphic/cards/$id/decide', body: {...body, 'proof': proof});
      }
      final m = _m(r);
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
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
    final c = _c, sh = _m(c['show']);
    final st = _s(c['status']), kind = _s(c['kind']);
    final money = c['money'] == true;
    final amount = _s(sh['amount_text']).isNotEmpty ? _s(sh['amount_text']) : _s(sh['total_text']);
    final proofs = _m(sh['proofs']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'quote' => Icons.request_quote_rounded, 'proof' => Icons.image_rounded, 'extra' => Icons.add_card_rounded,
            'handover' => Icons.inventory_2_rounded, 'vendor' => Icons.print_rounded, 'invoice' => Icons.receipt_long_rounded,
            'discount' => Icons.percent_rounded, _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['job'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your yes?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'old', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['client'])} · ${_s(sh['title'])}', style: const TextStyle(fontSize: 12.5)),
        if (amount.isNotEmpty) Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
        if (kind == 'quote') ...[
          for (final ln in _list(sh['lines'])) Text('• ${_s(ln['name'])}: ${_rs(ln['amount'])}', style: const TextStyle(fontSize: 12)),
          Text('Advance ${_s(sh['advance_text'])} · ${_s(sh['rounds'])} revision round · valid ${_s(sh['valid_until'])}',
              style: const TextStyle(fontSize: 12)),
          Text(_s(sh['rights']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
        ],
        if (kind == 'proof') ...[
          Text('v${_s(sh['version'])} · round ${_s(sh['round'])} · ${_s(sh['rounds_left'])} rounds left', style: const TextStyle(fontSize: 12)),
          if (proofs.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: _img(widget.app, _s(proofs.values.first), height: 140)),
          for (final p in _strs(sh['print_problems'])) Text('🖨 $p', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        ],
        if (kind == 'extra') Text('Of the quote ${_s(sh['included'])} rounds done; next round${_s(sh['amount_text'])}', style: const TextStyle(fontSize: 12)),
        if (kind == 'handover') ...[
          for (final f in _list(sh['files'])) Text('• ${_s(f['name'])}: ${_s(f['what'])}', style: const TextStyle(fontSize: 12)),
          for (final a in _list(sh['assets'])) Text('🔤 ${_s(a['name'])}: ${_s(a['say'])}', style: const TextStyle(fontSize: 11.5)),
          if (_s(sh['assignment']).isNotEmpty) const Text('+ A written copyright assignment draft (s.19)', style: TextStyle(fontSize: 12)),
          if (sh['balance'] != null) Text('Pending: ${_s(sh['balance_text'])}', style: const TextStyle(fontSize: 12)),
        ],
        if (kind == 'vendor') ...[
          Text('Printer: ${_s(sh['vendor'])} · ${_s(_m(sh['print_job'])['qty'])} copies', style: const TextStyle(fontSize: 12)),
          Text('${_s(_m(sh['spec'])['label'])} · bleed ${_s(_m(sh['spec'])['bleed'])} mm · ${_s(_m(sh['spec'])['color'])}',
              style: const TextStyle(fontSize: 12)),
        ],
        if (kind == 'invoice') ...[
          Text('${_s(sh['what']) == 'advance' ? 'Advance' : 'Final'} invoice · UPI ${_s(sh['upi'])}', style: const TextStyle(fontSize: 12)),
          Text(_s(sh['tds_note']), style: const TextStyle(fontSize: 11.5, color: C.muted)),
        ],
        if (_s(sh['reason']).isNotEmpty) Text('Reason: ${_s(sh['reason'])}', style: const TextStyle(fontSize: 12)),
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Yes (fingerprint)' : 'Yes', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola sends nothing and neither takes nor gives money by itself: you send it.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// graphic_alert / graphic_day / graphic_job: notes (due tomorrow, late, proof unanswered, unpaid, morning note, proof made).
class GraphicNoteCard extends StatelessWidget {
  const GraphicNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final job = _s(data['job'] is Map ? _m(data['job'])['number'] : data['job']);
    final v = _m(data['version']);
    final proofs = _m(v['proofs']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.brush_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
        ]),
        if (proofs.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: _img(app, _s(proofs.values.first), height: 140)),
        if (job.isNotEmpty)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GraphicJobPage(app: app, ref: job))),
              child: Text('Open $job'),
            ),
          ),
      ]),
    );
  }
}
