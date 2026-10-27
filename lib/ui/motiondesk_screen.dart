/// Profile > Motion designer desk: Hoola as a motion designer's studio coworker, on top of Hoola Motion / 3D Studio / Brand / photo.
/// Aaj (deadlines, review ready, unpaid bills, licences ending, cards waiting) · Kaam (job tickets -> MotiondeskJobPage: brief,
/// deliverables with platform specs, storyboard, client's yes, renders, timecoded client notes, revision rounds, final, invoices)
/// · Clients (their own brand kit: colours, fonts with licences, logo) · Licence (fonts / music / stock register) · Niyam.
/// The storyboard to the client, final delivery, invoices, paid extra rounds and client messages run only after HER tap
/// (money cards with her fingerprint once a phone key is set up). Hoola never sends anything and never takes or pays money.
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
            TextField(
                controller: c[k],
                decoration: InputDecoration(labelText: label),
                maxLines: (k == 'brief' || k == 'text' || k == 'terms' || k == 'notes') ? 4 : 1),
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

Widget _draftButtons(Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), sms = _s(draft['sms']), mail = _s(draft['mail']), upi = _s(draft['upi']);
  if (wa.isEmpty && sms.isEmpty && mail.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (sms.isNotEmpty) GlassButton(label: 'SMS draft', icon: Icons.sms_rounded, height: 40, onTap: () => Native.openExternal(url: sms)),
    if (mail.isNotEmpty) GlassButton(label: 'Email draft', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (upi.isNotEmpty) const Pill('UPI link aapke UPI ID ka'),
  ]);
}

const _platforms = [
  ('insta_reel', 'Insta Reel'),
  ('insta_post', 'Insta feed 4:5'),
  ('insta_story', 'Story'),
  ('yt_short', 'YT Short'),
  ('youtube', 'YouTube 16:9'),
  ('fb_reel', 'FB Reel'),
  ('whatsapp_status', 'WA Status'),
  ('square', 'Square'),
  ('linkedin', 'LinkedIn'),
  ('tv_ooh', 'TV / LED'),
];

class MotiondeskScreen extends StatefulWidget {
  const MotiondeskScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<MotiondeskScreen> createState() => _MotiondeskScreenState();
}

class _MotiondeskScreenState extends State<MotiondeskScreen> {
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
      final d = _m(await widget.app.api!.call('GET', '/api/motiondesk'));
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
      .push(MaterialPageRoute(builder: (_) => MotiondeskJobPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _jobTile(Map<String, dynamic> j) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        child: InkWell(
          onTap: () => _open(_s(j['number'])),
          child: Row(children: [
            Icon(j['status'] == 'delivered' ? Icons.check_circle_rounded : Icons.movie_filter_rounded,
                color: j['status'] == 'delivered' ? C.ok : C.accent),
            const SizedBox(width: 10),
            Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(j['number'])} · ${_s(j['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text('${_s(j['client'])} · ${_s(j['engine'])} · deadline ${_s(j['deadline']).isEmpty ? '-' : _s(j['deadline'])} · ${_s(_m(j['rounds'])['say'])}',
                  style: const TextStyle(fontSize: 12, color: C.muted)),
            ])),
            Pill(_s(j['status_label'])),
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
        Padding(padding: const EdgeInsets.only(bottom: 10), child: MotiondeskCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      for (final (k, label) in const [('late', 'DEADLINE NIKAL GAYI'), ('due', '2 DIN MEIN DEADLINE'), ('unpaid', 'PAISE BAAKI'), ('expiring', 'LICENCE KHATAM HONE WALE')])
        if (_strs(day[k]).isNotEmpty) ...[Caption(label), for (final x in _strs(day[k])) Text('• $x'), const SizedBox(height: 8)],
    ]);
  }

  Future<void> _newJob() async {
    final clients = _list(_d?['clients']);
    final f = await _form(context, 'Naya kaam', [
      ('client', 'Client (naam / C-number)${clients.isEmpty ? '' : ': ${clients.map((c) => _s(c['name'])).take(4).join(', ')}'}'),
      ('title', 'Kaam ka naam'),
      ('brief', 'Brief (client ke shabd: kya, kis ke liye, kahan chalega)'),
      ('engine', 'Engine: motion / blender3d / brand / photo'),
      ('kind', 'Motion type: explainer / logo / offer / recipe / custom'),
      ('deliverables', 'Platforms (comma se): insta_reel, youtube, square ...'),
      ('deadline', 'Deadline (DD-MM-YYYY)'),
      ('rate', 'Aapka daam (₹, khaali = baad mein)'),
    ], ok: 'Banao');
    if (f == null) return;
    final r = await _run('POST', '/api/motiondesk/jobs', {
      ...f,
      'deliverables': (f['deliverables'] ?? 'insta_reel').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
      'quote': [
        {'text': f['title'] ?? 'Motion video', 'qty': 1, 'rate': _n(f['rate'])}
      ],
    });
    final jn = _s(_m(r?['job'])['number']);
    if (jn.isNotEmpty) _open(jn);
  }

  Widget _kaam() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya kaam', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : _newJob),
        const SizedBox(height: 12),
        if (_list(_d?['templates']).isNotEmpty) ...[
          const Caption('MERE TEMPLATE'),
          Wrap(spacing: 8, runSpacing: 6, children: [
            for (final t in _list(_d?['templates']))
              ActionChip(
                  label: Text('${_s(t['name'])} (${_s(t['uses'])})'),
                  onPressed: _busy
                      ? null
                      : () async {
                          final f = await _form(context, 'Template se kaam', const [('client', 'Client'), ('brief', 'Naya brief (optional)')]);
                          if (f == null) return;
                          await _run('POST', '/api/motiondesk/jobs', {...f, 'template': _s(t['id'])});
                        }),
          ]),
          const SizedBox(height: 12),
        ],
        for (final j in _list(_d?['jobs'])) _jobTile(j),
      ]);

  Widget _clients() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(
            label: 'Naya client',
            icon: Icons.person_add_rounded,
            height: 46,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Client aur unka brand kit', const [
                      ('name', 'Naam'),
                      ('contact', 'Contact person'),
                      ('phone', 'Mobile'),
                      ('email', 'Email'),
                      ('gstin', 'GSTIN'),
                      ('primary', 'Main rang (#hex ya laal / neela ...)'),
                      ('accent', 'Accent rang'),
                      ('font', 'Font ka naam'),
                      ('font_source', 'Font kahan se: google_fonts / adobe_fonts / client / own'),
                      ('tone', 'Tone (jaise warm, premium)'),
                    ], ok: 'Save');
                    if (f == null) return;
                    await _run('POST', '/api/motiondesk/clients', {
                      ...f,
                      'kit': {
                        'colors': {if (f['primary'] != null) 'primary': f['primary'], if (f['accent'] != null) 'accent': f['accent']},
                        'fonts': [if (f['font'] != null) {'name': f['font'], 'source': f['font_source'] ?? ''}],
                        if (f['tone'] != null) 'tone': f['tone'],
                      },
                    });
                  }),
        const SizedBox(height: 12),
        for (final c in _list(_d?['clients']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(c['number'])} · ${_s(c['name'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                if (c['logo'] == true) const Pill('logo'),
              ]),
              Wrap(spacing: 6, children: [
                for (final e in _m(_m(c['kit'])['colors']).entries)
                  Container(
                      width: 22,
                      height: 22,
                      decoration: BoxDecoration(
                          color: Color(int.tryParse('FF${_s(e.value).replaceAll('#', '')}', radix: 16) ?? 0xFF888888),
                          borderRadius: BorderRadius.circular(6))),
              ]),
              for (final f in _list(_m(c['kit'])['fonts']))
                Text('Font: ${_s(f['name'])} · ${_s(f['licence'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
              if (c['forgotten'] != true)
                TextButton(
                    onPressed: _busy ? null : () => _run('POST', '/api/motiondesk/clients/${_s(c['id'])}/forget'),
                    child: const Text('Jaankari hatao (DPDP)')),
            ]),
          ),
      ]);

  Widget _licence() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(
            label: 'Font / music / stock jodo',
            icon: Icons.library_add_rounded,
            height: 46,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Licence register', const [
                      ('name', 'Naam'),
                      ('kind', 'Kya: font / music / sfx / stock_video / stock_image / template / 3d_model'),
                      ('source', 'Kahan se: google_fonts / adobe_fonts / envato / artlist / epidemic / pixabay / own / client'),
                      ('licence_ref', 'Licence ID / invoice no.'),
                      ('credit', 'Credit line (CC BY ho to)'),
                      ('valid_until', 'Licence kab tak (DD-MM-YYYY)'),
                    ], ok: 'Save');
                    if (f == null) return;
                    await _run('POST', '/api/motiondesk/assets', f);
                  }),
        const SizedBox(height: 12),
        for (final a in _list(_d?['assets']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(a['name'])} · ${_s(a['kind'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                Pill(_s(a['licence_label']), fg: a['licence'] == 'unknown' ? C.warn : C.chip),
              ]),
              Text(_s(a['say']), style: const TextStyle(fontSize: 12, color: C.muted)),
              if (_s(a['licence_ref']).isNotEmpty) Text('Ref: ${_s(a['licence_ref'])}', style: const TextStyle(fontSize: 12)),
              if (_s(a['valid_until']).isNotEmpty)
                Text('Kab tak: ${_s(a['valid_until'])}${a['expired'] == true ? ' (khatam)' : ''}', style: const TextStyle(fontSize: 12)),
            ]),
          ),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(st['studio']).isEmpty ? 'Studio ka naam nahi' : _s(st['studio']), style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('GSTIN ${_s(st['gstin']).isEmpty ? '-' : _s(st['gstin'])} · GST ${_s(st['gst_pct'])}% · SAC ${_s(st['sac'])}'),
        Text('UPI ${_s(st['upi_id']).isEmpty ? '-' : _s(st['upi_id'])} · Shamil round ${_s(st['rounds'])} · Extra round ${_rs(st['round_fee'])}'),
        Text('Advance ${_s(st['advance_pct'])}% · Bill ${_s(st['pay_days'])} din mein · Haq: ${_s(st['rights'])}'),
        const SizedBox(height: 8),
        GlassButton(
            label: 'Badlo',
            icon: Icons.edit_rounded,
            height: 40,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(
                        context,
                        'Studio niyam',
                        const [
                          ('studio', 'Studio ka naam'),
                          ('gstin', 'GSTIN'),
                          ('upi_id', 'UPI ID'),
                          ('gst_pct', 'GST %'),
                          ('sac', 'SAC'),
                          ('rounds', 'Shamil badlav round'),
                          ('round_fee', 'Extra round ka daam (₹)'),
                          ('advance_pct', 'Advance %'),
                          ('pay_days', 'Bill kitne din mein'),
                          ('rights', 'Haq: licence / assign'),
                          ('rights_years', 'Assign ho to kitne saal'),
                          ('rights_territory', 'Kis desh mein'),
                          ('terms', 'Shartein'),
                        ],
                        ok: 'Save',
                        initial: {for (final e in st.entries) if (e.value != null && e.value is! Map && e.value is! List) e.key: _s(e.value)});
                    if (f == null) return;
                    await _run('PUT', '/api/motiondesk/settings', f);
                  }),
      ])),
      const SizedBox(height: 10),
      for (final k in const ['gst_note', 'tds_note', 'copyright_note', 'ai_note', 'starter'])
        if (_s(st[k]).isNotEmpty) Padding(padding: const EdgeInsets.only(bottom: 8), child: Glass(child: Text(_s(st[k]), style: const TextStyle(fontSize: 12.5)))),
      const Caption('PLATFORM SPEC (STARTER)'),
      for (final p in _list(_d?['platforms']))
        Text('• ${_s(p['label'])}: ${_s(p['aspect'])} ${_s(p['px'])}, ${_s(p['fps'])} fps${p['max_s'] == null ? '' : ', ${_s(p['max_s'])} s tak'}',
            style: const TextStyle(fontSize: 12)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [_aaj, _kaam, _clients, _licence, _niyam];
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} · Motion designer'), actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _d == null ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(onRefresh: _load, child: tabs[_tab]()),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today_rounded), label: 'Aaj'),
          NavigationDestination(icon: Icon(Icons.movie_filter_rounded), label: 'Kaam'),
          NavigationDestination(icon: Icon(Icons.people_rounded), label: 'Clients'),
          NavigationDestination(icon: Icon(Icons.verified_user_rounded), label: 'Licence'),
          NavigationDestination(icon: Icon(Icons.tune_rounded), label: 'Niyam'),
        ],
      ),
    );
  }
}

class MotiondeskJobPage extends StatefulWidget {
  const MotiondeskJobPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<MotiondeskJobPage> createState() => _MotiondeskJobPageState();
}

class _MotiondeskJobPageState extends State<MotiondeskJobPage> {
  Map<String, dynamic>? _j;
  bool _busy = false;
  Map<String, dynamic>? _card;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final j = _m(await widget.app.api!.call('GET', '/api/motiondesk/jobs/${widget.ref}'));
      if (mounted) setState(() => _j = j);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _act(String what, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/motiondesk/jobs/${widget.ref}/$what', body);
    if (r != null && _m(r['card']).isNotEmpty) _card = r;
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _btn(String label, IconData icon, String what, [Map<String, dynamic> body = const {}]) =>
      GlassButton(label: label, icon: icon, height: 40, onTap: _busy ? null : () => _act(what, body));

  @override
  Widget build(BuildContext context) {
    final j = _j;
    if (j == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final rounds = _m(j['rounds']);
    return Scaffold(
      appBar: AppBar(title: Text('${_s(j['number'])} · ${_s(j['title'])}')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(j['client'])} · ${_s(j['status_label'])} · ${_s(j['engine'])} ${_s(j['kind'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text('Deadline ${_s(j['deadline']).isEmpty ? '-' : _s(j['deadline'])} · Quote ${_s(j['quote_total_text'])}'),
            Text(_s(rounds['say']), style: const TextStyle(fontSize: 12.5)),
            if (_s(j['brief']).isNotEmpty) Text('Brief: ${_s(j['brief'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
          ])),
          const SizedBox(height: 10),
          const Caption('DELIVERABLES'),
          for (final d in _list(j['deliverables'])) ...[
            Text('• ${_s(d['label'])}: ${_s(d['aspect'])} ${_s(d['px'])}, ${_s(d['fps'])} fps', style: const TextStyle(fontSize: 12.5)),
            for (final w in _strs(d['warnings'])) Text('   ⚠ $w', style: const TextStyle(fontSize: 11.5, color: C.warn)),
          ],
          Wrap(spacing: 6, runSpacing: 4, children: [
            for (final (k, label) in _platforms)
              FilterChip(
                  label: Text(label),
                  selected: _list(j['deliverables']).any((d) => d['platform'] == k),
                  onSelected: _busy
                      ? null
                      : (on) {
                          final cur = _list(j['deliverables']).map((d) => _s(d['platform'])).toList();
                          on ? cur.add(k) : cur.remove(k);
                          _act('update', {'deliverables': cur});
                        }),
          ]),
          const SizedBox(height: 12),
          Caption('STORYBOARD v${_s(j['sb_version'])} · ${_s(j['seconds'])} sec${j['storyboard_approved'] == true ? ' · client ne maana' : ''}'),
          for (final f in _list(j['frames']))
            Glass(
                margin: const EdgeInsets.only(bottom: 6),
                child: Text('${_s(f['n'])}. [${_s(f['seconds'])}s] ${_s(f['visual'])}\n“${_s(f['text'])}” ${_s(f['motion'])} ${_s(f['audio'])}',
                    style: const TextStyle(fontSize: 12.5))),
          Wrap(spacing: 8, runSpacing: 6, children: [
            _btn('Storyboard banao', Icons.view_carousel_rounded, 'storyboard'),
            if (_list(j['frames']).isNotEmpty) _btn('Client ko bhejne ka card', Icons.send_rounded, 'storyboard_send'),
            if (_list(j['frames']).isNotEmpty && j['storyboard_approved'] != true)
              GlassButton(
                  label: 'Client ne maana',
                  icon: Icons.thumb_up_rounded,
                  height: 40,
                  onTap: _busy
                      ? null
                      : () async {
                          final f = await _form(context, 'Client ki haan', const [('by', 'Kisne, kaise (jaise: Mr Sharma, WhatsApp)')]);
                          if (f != null) _act('client_ok', f);
                        }),
          ]),
          const SizedBox(height: 12),
          const Caption('RENDERS'),
          for (final r in _list(j['renders']))
            ListTile(
              dense: true,
              leading: Icon(r['status'] == 'done' ? Icons.play_circle_rounded : (r['status'] == 'failed' ? Icons.error_rounded : Icons.hourglass_top_rounded)),
              title: Text('v${_s(r['v'])} · ${_s(r['aspect'])} · ${_s(r['platform'])}'),
              subtitle: Text(_s(r['status']) + (_s(r['error']).isEmpty ? '' : ' · ${_s(r['error'])}')),
              onTap: _s(r['url']).isEmpty ? null : () => Native.openExternal(url: widget.app.api!.absolute(_s(r['url']))),
            ),
          Wrap(spacing: 8, runSpacing: 6, children: [
            _btn('Render', Icons.movie_creation_rounded, 'render'),
            GlassButton(
                label: 'Client ke notes',
                icon: Icons.comment_rounded,
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Client ke notes (har line: 0:12 kya badalna)', const [('text', 'Notes'), ('by', 'Kisne')]);
                        if (f != null) _act('feedback', f);
                      }),
            _btn('Badlav render', Icons.autorenew_rounded, 'revise'),
            if (rounds['left'] == 0) _btn('Extra round card', Icons.add_card_rounded, 'extra_round'),
          ]),
          for (final n in _list(j['feedback']))
            Text('${n['done'] == true ? '✓' : '•'} ${n['tc'] == null ? '--:--' : _s(n['tc'])}s ${_s(n['text'])}', style: const TextStyle(fontSize: 12)),
          const SizedBox(height: 12),
          const Caption('LICENCE / ASSETS'),
          for (final a in _list(j['assets'])) Text('• ${_s(a['name'])}: ${_s(a['licence_label'])}', style: const TextStyle(fontSize: 12)),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 6, children: [
            _btn('Final delivery card', Icons.inventory_2_rounded, 'final'),
            _btn('Advance bill card', Icons.request_quote_rounded, 'invoice', {'bill': 'advance'}),
            _btn('Final bill card', Icons.receipt_long_rounded, 'invoice', {'bill': 'final'}),
            GlassButton(
                label: 'Client ko message',
                icon: Icons.chat_rounded,
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Message', const [('text', 'Message')]);
                        if (f != null) _act('message', f);
                      }),
            GlassButton(
                label: 'Template save',
                icon: Icons.bookmark_add_rounded,
                height: 40,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Template ka naam', const [('name', 'Naam')]);
                        if (f != null) _act('template', f);
                      }),
          ]),
          if (_card != null) ...[
            const SizedBox(height: 10),
            MotiondeskCardCard(app: widget.app, data: _card!, onDone: _load),
          ],
          const SizedBox(height: 12),
          const Caption('BILL'),
          for (final i in _list(j['invoices']))
            ListTile(
              dense: true,
              title: Text('${_s(i['number'])} · ${_s(i['kind'])} · ${_s(i['total_text'])}'),
              subtitle: Text('Mila ${_rs(i['paid'])} · ${_s(i['status'])} · due ${_s(i['due'])}'),
              trailing: i['status'] == 'paid'
                  ? const Icon(Icons.check_rounded, color: C.ok)
                  : TextButton(
                      onPressed: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Paise mile', const [('amount', 'Kitne (₹)'), ('ref', 'UTR / ref (aakhri ank)')]);
                              if (f == null) return;
                              if (!context.mounted) return;
                              await _call(context, widget.app, 'POST', '/api/motiondesk/invoices/${_s(i['id'])}/paid',
                                  {'amount': _n(f['amount']), 'ref': f['ref'] ?? ''});
                              await _load();
                            },
                      child: const Text('Paise mile')),
            ),
        ]),
      ),
    );
  }
}

/// motiondesk_card: storyboard / final / invoice / extra_round / message waiting for HER tap.
class MotiondeskCardCard extends StatefulWidget {
  const MotiondeskCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<MotiondeskCardCard> createState() => _MotiondeskCardCardState();
}

class _MotiondeskCardCardState extends State<MotiondeskCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/motiondesk/cards/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Motion studio' : _s(show['title']),
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
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyun nahi?', const [('reason', 'Wajah (optional)')], ok: 'Nahi');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason};
      dynamic r;
      try {
        r = await widget.app.api!.call('POST', '/api/motiondesk/cards/$id/decide', body: body);
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = await widget.app.api!.call('POST', '/api/motiondesk/cards/$id/decide', body: {...body, 'proof': proof});
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
    final blocks = _strs(sh['blocks']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'storyboard' => Icons.view_carousel_rounded,
            'final' => Icons.inventory_2_rounded,
            'invoice' => Icons.receipt_long_rounded,
            'extra_round' => Icons.add_card_rounded,
            _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['job'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text('${_s(sh['client'])} · ${_s(sh['title'])}', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'storyboard') Text('v${_s(sh['version'])} · ${_list(sh['frames']).length} frame · ${_s(sh['seconds'])} sec', style: const TextStyle(fontSize: 12.5)),
        if (kind == 'invoice' || kind == 'extra_round') Text(_s(sh['amount_text']), style: const TextStyle(fontWeight: FontWeight.w700)),
        if (kind == 'invoice')
          for (final l in _list(sh['lines'])) Text('• ${_s(l['text'])} ${l['rate'] == null ? '' : _rs(l['rate'])}', style: const TextStyle(fontSize: 12)),
        if (kind == 'final') ...[
          for (final f in _list(sh['files'])) Text('• ${_s(f['platform'])} ${_s(f['aspect'])}', style: const TextStyle(fontSize: 12)),
          for (final l in _list(sh['licences']))
            Text('◦ ${_s(l['name'])}: ${_s(l['licence'])}${_s(l['client_needs']).isEmpty ? '' : ' (${_s(l['client_needs'])})'}',
                style: const TextStyle(fontSize: 11.5, color: C.muted)),
          Text(_s(sh['rights']), style: const TextStyle(fontSize: 11.5)),
          for (final w in _strs(sh['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 11.5, color: C.warn)),
        ],
        for (final b in blocks) Text('⛔ $b', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_s(sh['text']).isNotEmpty) Text('“${_s(sh['text'])}”', style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: money ? 'Haan (fingerprint)' : 'Haan', height: 42, onTap: (_busy || blocks.isNotEmpty) ? null : () => _decide(true)),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola khud kuch nahi bhejta, paise nahi leta / deta: message aap bhejti hain.', style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// motiondesk_update / motiondesk_alert / motiondesk_day: notes (render ready, deadline, unpaid bill, licence ending, morning note).
class MotiondeskNoteCard extends StatelessWidget {
  const MotiondeskNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final job = _s(data['job']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.movie_filter_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
          if (job.isNotEmpty)
            TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MotiondeskJobPage(app: app, ref: job))),
              child: Text('$job kholo'),
            ),
        ])),
      ]),
    );
  }
}
