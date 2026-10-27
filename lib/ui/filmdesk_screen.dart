/// Profile > Film desk: Hoola as an AI film producer's coworker on top of Video Studio.
/// Aaj (what's moving, cards waiting) · Filmein (logline -> script -> scenes -> cast -> shots -> studio storyboard -> free
/// preview -> budget per shot -> paid shots on the STUDIO's own price card -> rights -> release checklist) · Ijazat (consent
/// register: real people's face / voice only with a recorded proof) · Niyam.
/// Messages to outside people and marking a film released run only after HER tap here; money for AI shots only on the studio
/// card. Hoola never posts, uploads, files with CBFC or pays.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
List<String> _strs(dynamic l) => ((l as List?) ?? const []).map((e) => '$e').toList();
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());
List<String> _csv(String? v) => (v ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

const _bigFields = {'text', 'logline', 'notes', 'prompt', 'dialogue', 'terms', 'rules', 'description'};

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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: _bigFields.contains(k) ? 5 : 1),
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
    final r = await app.api!.call(method, path, body: body, timeout: const Duration(seconds: 180));
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

const _statusLabel = {
  'idea': 'Idea', 'script': 'Script', 'breakdown': 'Scenes', 'shots': 'Shots', 'storyboard': 'Storyboard',
  'production': 'Shots ban rahe', 'post': 'Jod rahe', 'release_ready': 'Release taiyaar', 'released': 'Release',
};
const _consentLabel = {'none': 'ijazat nahi', 'recorded': 'ijazat darj', 'withdrawn': 'ijazat wapas'};

class FilmdeskScreen extends StatefulWidget {
  const FilmdeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<FilmdeskScreen> createState() => _FilmdeskScreenState();
}

class _FilmdeskScreenState extends State<FilmdeskScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/filmdesk'));
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
      .push(MaterialPageRoute(builder: (_) => FilmdeskProjectPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _projectTile(Map<String, dynamic> p) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        child: InkWell(
          onTap: () => _open(_s(p['number'])),
          child: Row(children: [
            const Icon(Icons.movie_creation_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(p['number'])} · ${_s(p['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${_s(p['format_label'])} · ${_s(p['scenes_n'])} scenes · ${_s(p['shots_n'])} shots · ${_s(p['seconds'])} s',
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
              if (_strs(p['target_labels']).isNotEmpty)
                Text(_strs(p['target_labels']).join(', '), style: const TextStyle(fontSize: 11.5, color: C.faint)),
            ])),
            Pill(_statusLabel[_s(p['status'])] ?? _s(p['status'])),
          ]),
        ),
      );

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('AAPKI HAAN KA INTEZAAR'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: FilmdeskCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final x in _strs(day['consent_ending'])) Text('• $x', style: const TextStyle(fontSize: 12.5)),
      for (final x in _strs(day['rights_ending'])) Text('• $x', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 8),
      const Text('AI shots ka kharcha sirf Video Studio ke card par aapki haan se hota hai. Hoola kahin post / upload nahi karta.',
          style: TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  Future<void> _newFilm() async {
    final f = await _form(context, 'Nayi film', const [
      ('title', 'Naam'),
      ('logline', 'Ek-do line ki kahani (logline)'),
      ('format', 'Kaisi: short / reel / ad / music_video / web_episode / feature / documentary'),
      ('language', 'Bhasha (Hindi / Marathi / English / Hinglish)'),
      ('targets', 'Kahan dikhegi: youtube, instagram, ott, festival, theatrical, tv'),
      ('budget_inr', 'AI shots ka budget ₹ (optional)'),
    ], ok: 'Banao');
    if (f == null) return;
    final r = await _run('POST', '/api/filmdesk/projects', {
      ...f,
      'targets': _csv(f['targets']),
      if (f['budget_inr'] != null) 'budget_inr': _n(f['budget_inr']),
    });
    final ref = _s(_m(r?['project'])['number']);
    if (ref.isNotEmpty) _open(ref);
  }

  Widget _films() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Nayi film', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newFilm),
        const SizedBox(height: 12),
        for (final p in _list(_d?['projects'])) _projectTile(p),
      ]);

  Future<void> _addPerson() async {
    final f = await _form(context, 'Register mein naam', const [
      ('name', 'Naam'),
      ('role', 'Role: actor / voice / subject / crew / writer / singer'),
      ('phone', 'Mobile (optional)'),
      ('minor', 'Nabalig? (haan / nahi)'),
    ], ok: 'Jodo');
    if (f == null) return;
    await _run('POST', '/api/filmdesk/people', {
      'name': f['name'],
      'role': f['role'] ?? 'actor',
      if (f['phone'] != null) 'phone': f['phone'],
      'minor': (f['minor'] ?? '').toLowerCase().startsWith('h'),
    });
  }

  Future<void> _recordConsent(Map<String, dynamic> p) async {
    final f = await _form(context, 'Ijazat darj: ${_s(p['name'])}', const [
      ('how', 'Kaise li: signed_form / video / audio / email / written'),
      ('uses', 'Kis kaam ki: ai_likeness, ai_voice, real_footage, real_voice, name, promo'),
      ('until', 'Kab tak (DD-MM-YYYY, optional)'),
      ('guardian', 'Nabalig ho to guardian ka naam'),
    ], ok: 'Saboot chuno');
    if (f == null) return;
    final pick = await FilePicker.platform.pickFiles(withData: true);
    final file = (pick == null || pick.files.isEmpty) ? null : pick.files.first;
    if (file == null || file.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/filmdesk/people/${_s(p['number'])}/consent/upload', file.name, file.bytes!,
          fields: {for (final e in f.entries) e.key: e.value}, timeout: const Duration(seconds: 180), tries: 1);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _ijazat() => ListView(padding: const EdgeInsets.all(16), children: [
        const Glass(
            child: Text(
                'Asli insaan ka chehra ya awaaz AI se tabhi banega jab unki ijazat ka saboot (sign kiya form / video / audio) yahan darj ho. '
                'Jaane-maane log (neta / actor / khiladi) kabhi nahi. Ijazat kabhi bhi wapas ho sakti hai.',
                style: TextStyle(fontSize: 12.5))),
        const SizedBox(height: 10),
        GradientButton(label: 'Naam jodo', icon: Icons.person_add_alt_rounded, height: 44, onTap: _busy ? null : _addPerson),
        const SizedBox(height: 12),
        for (final p in _list(_d?['people'])) _personTile(p),
      ]);

  Widget _personTile(Map<String, dynamic> p) {
    final c = _m(p['consent']);
    final status = _s(c['status']);
    final until = _s(c['until']);
    return Glass(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${_s(p['number'])} · ${_s(p['name'])} · ${_s(p['role'])}',
              style: const TextStyle(fontWeight: FontWeight.w700))),
          Pill(_consentLabel[status] ?? status, fg: status == 'recorded' ? C.ok : C.warn),
        ]),
        if (p['public_figure'] == true)
          const Text('Jaane-maane vyakti: AI chehra / awaaz nahi.', style: TextStyle(fontSize: 12, color: C.bad)),
        if (_strs(c['uses']).isNotEmpty)
          Text('${_strs(c['uses']).join(', ')}${until.isEmpty ? '' : ' · $until tak'}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (p['forgotten'] != true)
          Wrap(spacing: 8, runSpacing: 6, children: [
            if (p['public_figure'] != true)
              GlassButton(label: 'Ijazat darj', icon: Icons.verified_user_rounded, height: 38,
                  onTap: _busy ? null : () => _recordConsent(p)),
            if (status == 'recorded')
              GlassButton(label: 'Wapas li', icon: Icons.block_rounded, height: 38,
                  onTap: _busy ? null : () => _run('POST', '/api/filmdesk/people/${_s(p['number'])}/withdraw', {})),
            GlassButton(label: 'Hatao (DPDP)', icon: Icons.delete_outline_rounded, height: 38,
                onTap: _busy ? null : () => _run('DELETE', '/api/filmdesk/people/${_s(p['number'])}')),
          ]),
      ]),
    );
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Banner: ${_s(st['banner'])}'),
        Text('Producer: ${_s(st['producer'])}'),
        Text('Bhasha: ${_s(st['language'])}'),
        Text('Mahine ki AI shots seema: ${st['month_budget_inr'] == null ? '-' : '₹${_s(st['month_budget_inr'])}'}'),
        Text('Subah ka note: ${_s(st['morning_time'])}'),
      ])),
      const SizedBox(height: 10),
      GradientButton(label: 'Badlo', icon: Icons.edit_rounded, height: 44, onTap: _busy ? null : () async {
        final f = await _form(context, 'Film desk ke niyam', const [
          ('banner', 'Production / banner ka naam'),
          ('producer', 'Producer'),
          ('email', 'Email'),
          ('phone', 'Mobile'),
          ('language', 'Bhasha'),
          ('month_budget_inr', 'Mahine ki AI shots seema ₹'),
          ('morning_time', 'Subah ka note (HH:MM)'),
          ('rules', 'Apne niyam'),
        ], initial: {for (final e in st.entries) if (e.value != null) e.key: '${e.value}'}, ok: 'Save');
        if (f == null) return;
        await _run('PUT', '/api/filmdesk/settings', {
          ...f,
          if (f['month_budget_inr'] != null) 'month_budget_inr': _n(f['month_budget_inr']),
        });
      }),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Filmein', 'Ijazat', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Film desk'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _films, _ijazat, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class FilmdeskProjectPage extends StatefulWidget {
  const FilmdeskProjectPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<FilmdeskProjectPage> createState() => _FilmdeskProjectPageState();
}

class _FilmdeskProjectPageState extends State<FilmdeskProjectPage> {
  Map<String, dynamic>? _p;
  Map<String, dynamic>? _budget;
  bool _busy = false;
  String get _base => '/api/filmdesk/projects/${widget.ref}';

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

  Future<void> _loadBudget() async {
    final r = await _call(context, widget.app, 'GET', '$_base/budget');
    if (r != null && mounted) setState(() => _budget = r);
  }

  Widget _section(String title, List<Widget> children) => Glass(
        margin: const EdgeInsets.only(bottom: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 6),
          ...children,
        ]),
      );

  Widget _scriptBox() {
    final p = _p!;
    final script = _s(p['script']);
    final br = _m(p['breakdown']);
    return _section('Script', [
      if (script.isEmpty) const Text('Abhi script nahi.', style: TextStyle(color: C.muted)),
      if (script.isNotEmpty)
        Text(script.length > 700 ? '${script.substring(0, 700)}…' : script, style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
      if (br.isNotEmpty)
        Text('${_s(br['scenes'])} scenes · ~${_s(br['seconds'])} s · raat ke ${_s(br['night'])}',
            style: const TextStyle(fontSize: 12.5, color: C.muted)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Hoola likhe', icon: Icons.auto_awesome_rounded, height: 38, onTap: _busy ? null : () async {
          final f = await _form(context, 'Script ke liye aapki baatein', const [('notes', 'Kirdaar, mood, ant... (sirf aapki baatein)')]);
          if (f == null) return;
          await _run('POST', '$_base/script', {'notes': f['notes'] ?? ''});
        }),
        GlassButton(label: 'Apni script', icon: Icons.edit_note_rounded, height: 38, onTap: _busy ? null : () async {
          final f = await _form(context, 'Script (INT. JAGAH - DIN, NAAM: line)', const [('text', 'Script')],
              initial: {'text': script}, ok: 'Save');
          if (f == null) return;
          await _run('PUT', '$_base/script', {'text': f['text'] ?? ''});
        }),
      ]),
    ]);
  }

  Widget _castBox() {
    final cast = _m(_p!['cast']);
    return _section('Cast (kirdaar)', [
      if (cast.isEmpty) const Text('Script ke baad kirdaar yahan aayenge.', style: TextStyle(color: C.muted)),
      for (final e in cast.entries)
        Row(children: [
          Expanded(child: Text(
              '${e.key}: ${_s(_m(e.value)['kind']) == 'real' ? 'asli ${_s(_m(e.value)['person'])}' : 'AI kirdaar'}'
              '${_s(_m(e.value)['description']).isEmpty ? '' : ' · ${_s(_m(e.value)['description'])}'}',
              style: const TextStyle(fontSize: 12.5))),
          IconButton(icon: const Icon(Icons.edit_rounded, size: 18), onPressed: _busy ? null : () async {
            final f = await _form(context, 'Kirdaar: ${e.key}', const [
              ('person', 'Asli insaan ho to register number (P-001)'),
              ('description', 'AI kirdaar ho to roop (umar, kapde, chehra)'),
            ]);
            if (f == null) return;
            await _run('POST', '$_base/cast', {'character': e.key, ...f});
          }),
        ]),
    ]);
  }

  Future<void> _editShot(Map<String, dynamic> s, String action) async {
    final id = _s(s['id']);
    if (action == 'del') {
      await _run('DELETE', '$_base/shots/$id');
      return;
    }
    final f = await _form(context, 'Shot $id', const [
      ('prompt', 'Kya dikhe aur kya ho'),
      ('duration', 'Seconds (4-10)'),
      ('dialogue', 'Dialogue'),
    ], initial: {'prompt': _s(s['prompt']), 'duration': _s(s['duration']), 'dialogue': _s(s['dialogue'])}, ok: 'Save');
    if (f == null) return;
    await _run('PATCH', '$_base/shots/$id', {
      ...f,
      if (f['duration'] != null) 'duration': _n(f['duration'])?.toInt(),
    });
  }

  Widget _shotsBox() {
    final shots = _list(_p!['shots']);
    return _section('Shots (${shots.length})', [
      for (final s in shots)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(s['id'])} · ${_s(s['camera'])} · ${_s(s['duration'])} s', style: const TextStyle(fontSize: 12, color: C.muted)),
              Text(_s(s['prompt']), style: const TextStyle(fontSize: 12.5)),
              if (_s(s['dialogue']).isNotEmpty) Text('${_s(s['speaker'])}: “${_s(s['dialogue'])}”', style: const TextStyle(fontSize: 12)),
            ])),
            PopupMenuButton<String>(
              onSelected: (v) => _editShot(s, v),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'edit', child: Text('Badlo')),
                PopupMenuItem(value: 'del', child: Text('Hatao')),
              ],
            ),
          ]),
        ),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Shot list banao', icon: Icons.view_list_rounded, height: 38,
            onTap: _busy ? null : () => _run('POST', '$_base/shots', {})),
        GlassButton(label: 'Studio mein storyboard', icon: Icons.movie_filter_rounded, height: 38,
            onTap: _busy ? null : () => _run('POST', '$_base/storyboard')),
        GlassButton(label: 'Free preview', icon: Icons.play_circle_rounded, height: 38,
            onTap: _busy ? null : () => _run('POST', '$_base/preview')),
      ]),
    ]);
  }

  Widget _budgetBox() {
    final b = _budget;
    final tot = _m(b?['total']);
    return _section('Budget (studio ka andaaza)', [
      if (b == null) const Text('Storyboard ke baad har shot ka daam yahan dikhega.', style: TextStyle(color: C.muted)),
      if (b != null) ...[
        Text('Draft ~₹${_s(_m(tot['draft'])['inr'])} · Final ~₹${_s(_m(tot['final'])['inr'])} · ab tak ₹${_s(b['spent_inr'])}',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        if (b['film_budget_inr'] != null)
          Text('Film ka budget ₹${_s(b['film_budget_inr'])} · bacha ₹${_s(b['film_left_inr'])}', style: const TextStyle(fontSize: 12.5)),
        Text('Is mahine ₹${_s(b['month_spent_inr'])} / ₹${_s(b['month_limit_inr'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (_s(b['stale']).isNotEmpty) Text(_s(b['stale']), style: const TextStyle(fontSize: 12, color: C.warn)),
        for (final r in _list(b['shots']))
          Text('${_s(r['shot'])} · ${_s(r['seconds'])} s · draft ₹${_s(_m(r['draft'])['inr'])} · final ₹${_s(_m(r['final'])['inr'])}',
              style: const TextStyle(fontSize: 12)),
        Text(_s(b['note']), style: const TextStyle(fontSize: 11, color: C.faint)),
      ],
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Daam dekho', icon: Icons.calculate_rounded, height: 38, onTap: _busy ? null : _loadBudget),
        GlassButton(label: 'Draft shots maango', icon: Icons.currency_rupee_rounded, height: 38,
            onTap: _busy ? null : () => _run('POST', '$_base/spend', {'quality': 'draft'})),
        GlassButton(label: 'Final shots maango', icon: Icons.hd_rounded, height: 38,
            onTap: _busy ? null : () => _run('POST', '$_base/spend', {'quality': 'final'})),
        GlassButton(label: 'Video jodo', icon: Icons.merge_rounded, height: 38,
            onTap: _busy ? null : () => _run('POST', '$_base/assemble', {})),
      ]),
      const Text('Kharcha sirf Video Studio ke card par aapki haan se.', style: TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  Future<void> _addRight() async {
    final f = await _form(context, 'Gaana / awaaz / stock / font', const [
      ('kind', 'Kya: music / song / voice / stock / font / lyrics / footage'),
      ('title', 'Naam'),
      ('owner', 'Malik (label / artist)'),
      ('licence', 'own / commissioned / licensed / royalty_free / ai_generated / public_domain'),
      ('sync', 'Video ke saath (sync) ijazat? haan / nahi'),
      ('platforms', 'Kahan ke liye: youtube, ott, theatrical... ya all'),
      ('until', 'Kab tak (DD-MM-YYYY)'),
    ], ok: 'Jodo');
    if (f == null) return;
    await _run('POST', '$_base/rights', {
      ...f,
      'sync': (f['sync'] ?? '').toLowerCase().startsWith('h'),
      'platforms': (f['platforms'] ?? '').trim().toLowerCase() == 'all' ? 'all' : _csv(f['platforms']),
    });
  }

  Widget _rightsBox() {
    final rights = _list(_p!['rights']);
    return _section('Music / haq', [
      for (final r in rights)
        Text('${_s(r['number'])} · ${_s(r['title'])} (${_s(r['kind'])}) · ${_s(r['licence'])}${r['sync'] == true ? ' · sync' : ''}'
            '${r['has_proof'] == true ? ' · saboot' : ''}${_s(r['until']).isEmpty ? '' : ' · ${_s(r['until'])} tak'}',
            style: const TextStyle(fontSize: 12.5)),
      GlassButton(label: 'Haq jodo', icon: Icons.library_music_rounded, height: 38, onTap: _busy ? null : _addRight),
    ]);
  }

  Widget _checkRow(Map<String, dynamic> it) => Row(children: [
        Icon(it['ok'] == true ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
            size: 18, color: it['ok'] == true ? C.ok : C.warn),
        const SizedBox(width: 6),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(it['label']), style: const TextStyle(fontSize: 12.5)),
          if (_s(it['why_not']).isNotEmpty) Text(_s(it['why_not']), style: const TextStyle(fontSize: 11, color: C.faint)),
        ])),
        if (it['auto'] != true)
          TextButton(onPressed: _busy ? null : () => _run('POST', '$_base/tick', {'key': it['key'], 'done': it['ok'] != true}),
              child: Text(it['ok'] == true ? 'Undo' : 'Ho gaya')),
      ]);

  Widget _releaseBox() {
    final rel = _m(_p!['release']);
    final disc = _m(rel['disclosure']);
    return _section('Release', [
      for (final it in _list(rel['items'])) _checkRow(it),
      if (_s(disc['description_line']).isNotEmpty) ...[
        const SizedBox(height: 6),
        const Caption('AI DISCLOSURE (description mein)'),
        SelectableText(_s(disc['description_line']), style: const TextStyle(fontSize: 12.5)),
        for (final x in _strs(disc['steps'])) Text('• $x', style: const TextStyle(fontSize: 11.5, color: C.muted)),
      ],
      if (_s(rel['cbfc_note']).isNotEmpty) Text(_s(rel['cbfc_note']), style: const TextStyle(fontSize: 11, color: C.faint)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'OTT rating', icon: Icons.shield_rounded, height: 38, onTap: _busy ? null : () async {
          final f = await _form(context, 'OTT rating', const [('rating', 'U / UA7 / UA13 / UA16 / A'), ('descriptors', 'Content descriptors')]);
          if (f == null) return;
          await _run('PUT', '$_base/rating', f);
        }),
        GlassButton(label: 'CBFC', icon: Icons.verified_rounded, height: 38, onTap: _busy ? null : () async {
          final f = await _form(context, 'CBFC certificate', const [
            ('category', 'U / UA7 / UA13 / UA16 / A / S'),
            ('number', 'Certificate number'),
            ('date', 'Tareekh (DD-MM-YYYY)'),
          ]);
          if (f == null) return;
          await _run('PUT', '$_base/cbfc', f);
        }),
        GlassButton(label: 'Kisi ko message', icon: Icons.chat_rounded, height: 38, onTap: _busy ? null : () async {
          final f = await _form(context, 'Message (card banega, aap bhejengi)', const [
            ('msg_kind', 'consent_request / rights_request / festival / distributor / custom'),
            ('person', 'Register number (P-001) ya khaali'),
            ('phone', 'Ya mobile'),
            ('text', 'Text (custom ke liye)'),
            ('terms', 'Ijazat maangte waqt shartein / fees'),
          ], ok: 'Card banao');
          if (f == null) return;
          await _run('POST', '$_base/message', f);
        }),
        GradientButton(label: 'Release ke liye card', icon: Icons.rocket_launch_rounded, height: 42,
            onTap: _busy ? null : () => _run('POST', '$_base/release-request', {})),
      ]),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(p == null ? widget.ref : '${_s(p['number'])} · ${_s(p['title'])}'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: p == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                Glass(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(p['logline']), style: const TextStyle(fontSize: 13.5)),
                    const SizedBox(height: 4),
                    Text('${_s(p['format_label'])} · ${_s(p['language'])} · ${_s(p['aspect'])} · ${_strs(p['target_labels']).join(', ')}',
                        style: const TextStyle(fontSize: 12, color: C.muted)),
                    Pill(_statusLabel[_s(p['status'])] ?? _s(p['status'])),
                  ]),
                ),
                _scriptBox(),
                _castBox(),
                _shotsBox(),
                _budgetBox(),
                _rightsBox(),
                _releaseBox(),
              ]),
            ),
    );
  }
}

/// filmdesk_card: a message to an outside person or the release pack, waiting for HER tap (hash must still match).
class FilmdeskCardCard extends StatefulWidget {
  const FilmdeskCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<FilmdeskCardCard> createState() => _FilmdeskCardCardState();
}

class _FilmdeskCardCardState extends State<FilmdeskCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<void> _decide(bool yes) async {
    final id = _s(_c['id']);
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyun nahi?', const [('reason', 'Wajah (optional)')], ok: 'Nahi');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/filmdesk/cards/$id/decide',
          body: {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason}, timeout: const Duration(seconds: 120)));
      if (mounted) {
        setState(() {
          if (_m(r['card']).isNotEmpty) _c = _m(r['card']);
          _draft = _m(r['draft']);
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
    final c = _c, sh = _m(c['show']);
    final st = _s(c['status']), kind = _s(c['kind']);
    final wa = _s(_draft['wa']), sms = _s(_draft['sms']), mail = _s(_draft['mail']);
    final forced = _strs(sh['forced']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(kind == 'release' ? Icons.rocket_launch_rounded : Icons.chat_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['project'])} ${_s(sh['title'])}',
              style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        if (kind == 'message') ...[
          if (_s(sh['to']).isNotEmpty || _s(sh['phone']).isNotEmpty)
            Text('Kisko: ${_s(sh['to'])} ${_s(sh['phone'])}', style: const TextStyle(fontSize: 12.5)),
          Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
          if (sh['blanks'] == true)
            const Text('[Khaali jagah] bhariye, phir card dobara banaiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        ],
        if (kind == 'release') ...[
          Text(_strs(sh['targets']).join(', '), style: const TextStyle(fontSize: 12.5)),
          for (final it in _list(sh['items']))
            Text('${it['ok'] == true ? '✓' : (forced.contains(_s(it['key'])) ? '⚠ chhoda' : '✗')} ${_s(it['label'])}',
                style: const TextStyle(fontSize: 12)),
          if (_s(sh['disclosure']).isNotEmpty) Text(_s(sh['disclosure']), style: const TextStyle(fontSize: 12, color: C.muted)),
        ],
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: 'Haan', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (wa.isNotEmpty || sms.isNotEmpty || mail.isNotEmpty)
          Wrap(spacing: 8, runSpacing: 6, children: [
            if (wa.isNotEmpty)
              GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
            if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
            if (mail.isNotEmpty)
              GlassButton(label: 'Mail draft', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
          ]),
        const Text('Hoola khud kuch nahi bhejta / post karta: message aur upload aap karti hain.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// filmdesk_alert / filmdesk_day: consent / licence ending, morning note.
class FilmdeskNoteCard extends StatelessWidget {
  const FilmdeskNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.movie_creation_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Film desk', style: TextStyle(fontWeight: FontWeight.w800)),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13)),
        ])),
        TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FilmdeskScreen(app: app))),
            child: const Text('Kholo')),
      ]),
    );
  }
}
