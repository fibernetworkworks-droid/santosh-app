/// Profile > Podcast Sahayak: Hoola as the podcast producer.
/// Aaj (recordings, releases missing, publish dates, cards waiting) · Episode (pipeline: idea -> booked -> recorded -> ready ->
/// live; episode page with run sheet, audio + loudness, transcript, show notes / chapters, music, sponsor reads, checks, publish)
/// · Guest (bookings, release / ijazat) · Sponsor (deals, reads, invoice, paise mile) · Music (licence register) · Numbers (her
/// pasted exports) · Niyam (show, artwork, feed, release wording).
/// Publishing, any message to a guest / sponsor and any invoice run only after HER tap on the card (server checks the hash).
library;

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
num? _n(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());

String _hms(dynamic sec) {
  final s = (sec is num ? sec : num.tryParse('$sec') ?? 0).round();
  final h = s ~/ 3600, m = (s % 3600) ~/ 60, x = s % 60;
  String two(int v) => v.toString().padLeft(2, '0');
  return h > 0 ? '${two(h)}:${two(m)}:${two(x)}' : '${two(m)}:${two(x)}';
}

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  const long = {'text', 'bio', 'script', 'summary', 'chapters', 'description', 'release_terms', 'points', 'notes', 'topics'};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: long.contains(k) ? 5 : 1),
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
    final r = await app.api!.call(method, path, body: body, timeout: const Duration(minutes: 5));
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Future<Map<String, dynamic>?> _upload(BuildContext context, Santosh app, String path, List<String> ext,
    {Map<String, String> fields = const {}}) async {
  final pick = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ext, withData: true);
  final f = pick?.files.firstOrNull;
  if (f == null || f.bytes == null) return null;
  try {
    final r = await app.api!.uploadFile(path, f.name, f.bytes!, fields: fields, timeout: const Duration(minutes: 10), tries: 1);
    if (context.mounted) _snack(context, _s(r['say']));
    return r;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Widget _draftButtons(BuildContext context, Map<String, dynamic> draft) {
  final wa = _s(draft['wa']), mail = _s(draft['mail']), upi = _s(draft['upi']), text = _s(draft['text']);
  if (wa.isEmpty && mail.isEmpty && text.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (mail.isNotEmpty) GlassButton(label: 'Email', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (text.isNotEmpty)
      GlassButton(label: 'Copy', icon: Icons.copy_rounded, height: 40, onTap: () {
        Clipboard.setData(ClipboardData(text: text));
        _snack(context, 'Copy ho gaya');
      }),
    if (upi.isNotEmpty) const Pill('UPI link aapke UPI ID ka'),
  ]);
}

const _stLabel = {'idea': 'Idea', 'booked': 'Recording tay', 'recorded': 'Record hua', 'ready': 'Taiyaar', 'published': 'Live'};

class PodcastScreen extends StatefulWidget {
  const PodcastScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PodcastScreen> createState() => _PodcastScreenState();
}

class _PodcastScreenState extends State<PodcastScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _stats;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/podcast'));
      final st = _m(await widget.app.api!.call('GET', '/api/podcast/stats'));
      if (mounted) setState(() {
        _d = d;
        _stats = st;
      });
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
      .push(MaterialPageRoute(builder: (_) => PodcastEpisodePage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _aaj() {
    final day = _m(_d?['day']);
    final feed = _m(_d?['feed']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 10),
      if (feed['on'] == true)
        Glass(child: Row(children: [
          const Icon(Icons.rss_feed_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(feed['url']), style: const TextStyle(fontSize: 12.5))),
          IconButton(icon: const Icon(Icons.copy_rounded), onPressed: () {
            Clipboard.setData(ClipboardData(text: _s(feed['url'])));
            _snack(context, 'Feed link copy');
          }),
        ])),
      const SizedBox(height: 10),
      if (_list(_d?['cards']).isNotEmpty) const Caption('AAPKI HAAN KA INTEZAAR'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: PodcastCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_list(day['recordings']).isNotEmpty) ...[
        const Caption('RECORDING'),
        for (final r in _list(day['recordings']))
          Glass(margin: const EdgeInsets.only(bottom: 8), child: InkWell(onTap: () => _open(_s(r['number'])),
              child: Text('${_s(r['number'])} · ${_s(r['title'])} · ${_s(r['at'])}${r['run_sheet'] == true ? '' : ' · run sheet baaki'}'))),
      ],
      if (_strs(day['release_missing']).isNotEmpty) ...[const Caption('RELEASE BAAKI'), for (final x in _strs(day['release_missing'])) Text('• $x')],
    ]);
  }

  Widget _epTile(Map<String, dynamic> e) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        child: InkWell(
          onTap: () => _open(_s(e['number'])),
          child: Row(children: [
            Icon(e['status'] == 'published' ? Icons.podcasts_rounded : Icons.mic_rounded,
                color: e['status'] == 'published' ? C.ok : C.accent),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(e['number'])} · ${_s(e['title'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text([
                if (_s(e['record_at']).isNotEmpty) 'Rec ${_s(e['record_at'])}',
                if (e['duration'] != null) _hms(e['duration']),
                for (final g in _list(e['guests'])) '${_s(g['name'])}${g['release_ok'] == true ? '' : ' (release?)'}',
              ].join(' · '), style: const TextStyle(fontSize: 12.5, color: C.muted)),
            ])),
            Pill(_stLabel[_s(e['status'])] ?? _s(e['status'])),
          ]),
        ),
      );

  Widget _episodes() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya episode', icon: Icons.add_rounded, height: 46, onTap: _busy ? null : () async {
          final f = await _form(context, 'Naya episode', const [
            ('title', 'Title / vishay'),
            ('topics', 'Topics (comma se)'),
            ('guests', 'Guest (G-001 ya naam)'),
            ('record_at', 'Recording (YYYY-MM-DD HH:MM)'),
            ('publish_on', 'Publish tareekh (YYYY-MM-DD)'),
          ]);
          if (f == null) return;
          final r = await _run('POST', '/api/podcast/episodes', {
            ...f,
            if (f['topics'] != null) 'topics': f['topics']!.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
            if (f['guests'] != null) 'guests': [f['guests']],
          });
          final n = _s(_m(r?['episode'])['number']);
          if (n.isNotEmpty && mounted) _open(n);
        }),
        const SizedBox(height: 12),
        for (final e in _list(_d?['episodes'])) _epTile(e),
      ]);

  Widget _guests() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya guest', icon: Icons.person_add_rounded, height: 46, onTap: _busy ? null : () async {
          final f = await _form(context, 'Guest', const [('name', 'Naam'), ('phone', 'Mobile'), ('email', 'Email'),
            ('bio', 'Unka parichay (unke apne shabd)'), ('topics', 'Kis baare mein')]);
          if (f == null) return;
          await _run('POST', '/api/podcast/guests', {...f, if (f['topics'] != null) 'topics': f['topics']!.split(',')});
        }),
        const SizedBox(height: 12),
        for (final g in _list(_d?['guests']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(g['number'])} · ${_s(g['name'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                Pill('release: ${_s(_m(g['release'])['status'])}', fg: g['release_ok'] == true ? C.ok : C.warn),
              ]),
              Text('${_s(g['status'])} · ${_s(g['phone'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 6, children: [
                GlassButton(label: 'Nyota', height: 38, onTap: _busy ? null : () async {
                  final f = await _form(context, 'Nyota', const [('episode', 'Episode (EP-001)'), ('text', 'Apna message (khaali = Hoola ka draft)')]);
                  if (f == null) return;
                  await _run('POST', '/api/podcast/guests/${_s(g['id'])}/invite', f);
                }),
                GlassButton(label: 'Release maango', height: 38, onTap: _busy ? null : () async {
                  final f = await _form(context, 'Release / ijazat', const [('episode', 'Episode (EP-001)'), ('fee', 'Fees tay hui? (khaali = kuch nahi likhenge)')]);
                  if (f == null) return;
                  await _run('POST', '/api/podcast/guests/${_s(g['id'])}/release_request', f);
                }),
                GlassButton(label: 'Haan mili', height: 38, onTap: _busy ? null : () => _releaseGot(g)),
                if (g['release_ok'] == true)
                  GlassButton(label: 'Ijazat wapas', height: 38, color: C.bad, onTap: () async {
                    final f = await _form(context, 'Ijazat wapas li?', const [('note', 'Kya kaha')]);
                    if (f == null) return;
                    await _run('POST', '/api/podcast/guests/${_s(g['id'])}/revoke', f);
                  }),
                GlassButton(label: 'Details hatao', height: 38, onTap: () => _run('POST', '/api/podcast/guests/${_s(g['id'])}/forget')),
              ]),
            ]),
          ),
      ]);

  Future<void> _releaseGot(Map<String, dynamic> g) async {
    final how = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(leading: const Icon(Icons.description_rounded), title: const Text('Sign ki hui file'), onTap: () => Navigator.pop(c, 'file')),
        ListTile(leading: const Icon(Icons.chat_rounded), title: const Text('Unka likha jawab (I agree)'), onTap: () => Navigator.pop(c, 'text')),
        ListTile(leading: const Icon(Icons.mic_rounded), title: const Text('Recording mein boli (samay batayiye)'), onTap: () => Navigator.pop(c, 'audio')),
      ])),
    );
    if (how == null || !mounted) return;
    final path = '/api/podcast/guests/${_s(g['id'])}/release';
    if (how == 'file') {
      await _upload(context, widget.app, path, const ['pdf', 'jpg', 'jpeg', 'png'], fields: {'how': 'file'});
      await _load();
      return;
    }
    final f = await _form(context, 'Ijazat', how == 'text'
        ? const [('text', 'Guest ka jawab yahan chipkaiye')]
        : const [('episode', 'Episode (EP-001)'), ('at', 'Samay (jaise 00:04:10)')]);
    if (f == null || !mounted) return;
    try {
      final r = await widget.app.api!.uploadFile(path, 'none.txt', const [], fields: {'how': how, ...f}, tries: 1);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
  }

  Widget _sponsors() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Naya sponsor', icon: Icons.handshake_rounded, height: 46, onTap: _busy ? null : () async {
          final f = await _form(context, 'Sponsor', const [('brand', 'Brand'), ('contact', 'Contact'), ('phone', 'Mobile'),
            ('email', 'Email'), ('gstin', 'Brand ka GSTIN'), ('amount', 'Tay fees (GST se pehle)'), ('deliverables', 'Kya dena hai (2 mid-roll ...)')]);
          if (f == null) return;
          await _run('POST', '/api/podcast/sponsors', {...f, if (f['amount'] != null) 'amount': _n(f['amount'])});
        }),
        const SizedBox(height: 12),
        for (final p in _list(_d?['sponsors']))
          Glass(
            margin: const EdgeInsets.only(bottom: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${_s(p['number'])} · ${_s(p['brand'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                Pill(_s(p['status'])),
              ]),
              Text('Fees ${_s(p['amount_text'])} · mile ₹${_s(p['paid'])} · ${_s(p['deliverables'])}',
                  style: const TextStyle(fontSize: 12.5, color: C.muted)),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 6, children: [
                GlassButton(label: 'Invoice', icon: Icons.receipt_long_rounded, height: 38,
                    onTap: _busy ? null : () => _run('POST', '/api/podcast/sponsors/${_s(p['id'])}/invoice', {})),
                GlassButton(label: 'Script bhejo', height: 38, onTap: _busy ? null : () async {
                  final f = await _form(context, 'Brand ko', const [('episode', 'Episode (EP-001) - us ke reads'), ('text', 'Ya apna message')]);
                  if (f == null) return;
                  await _run('POST', '/api/podcast/sponsors/${_s(p['id'])}/message', f);
                }),
                GlassButton(label: 'Paise mile', icon: Icons.currency_rupee_rounded, height: 38, onTap: _busy ? null : () async {
                  final f = await _form(context, 'Paise mile', const [('amount', 'Rakam'), ('ref', 'UTR ke aakhri ank'), ('tds', 'TDS kata (agar)')]);
                  if (f == null) return;
                  await _run('POST', '/api/podcast/sponsors/${_s(p['id'])}/paid',
                      {...f, 'amount': _n(f['amount']), if (f['tds'] != null) 'tds': _n(f['tds'])});
                }),
              ]),
            ]),
          ),
      ]);

  Widget _music() => ListView(padding: const EdgeInsets.all(16), children: [
        const Glass(child: Text('Har gaana / dhun / sound ka licence yahan. Licence saaf nahi = episode publish nahi hoga. Film / album ke '
            'gaane ke liye label / IPRS / PPL ka likhit licence chahiye; "royalty-free" har jagah free nahi.', style: TextStyle(fontSize: 12.5))),
        const SizedBox(height: 10),
        GradientButton(label: 'Track jodo', icon: Icons.music_note_rounded, height: 46, onTap: _busy ? null : () async {
          final f = await _form(context, 'Music / sound', const [('title', 'Naam'), ('artist', 'Kalakar'), ('source', 'Kahan se'),
            ('licence', 'own / commissioned / cc0 / cc_by / royalty_free / paid / unknown'), ('attribution', 'Credit line (CC BY)'),
            ('proof', 'Licence / receipt ka zikr'), ('valid_until', 'Kab tak (YYYY-MM-DD)')]);
          if (f == null) return;
          await _run('POST', '/api/podcast/music', f);
        }),
        const SizedBox(height: 12),
        for (final m in _list(_d?['music']))
          Glass(margin: const EdgeInsets.only(bottom: 8), child: Row(children: [
            Icon(m['cleared'] == true ? Icons.verified_rounded : Icons.block_rounded, color: m['cleared'] == true ? C.ok : C.bad),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(m['number'])} · ${_s(m['title'])} · ${_s(m['licence_label'])}'
                '${_s(m['valid_until']).isEmpty ? '' : ' · ${_s(m['valid_until'])} tak'}')),
          ])),
      ]);

  Widget _numbers() => ListView(padding: const EdgeInsets.all(16), children: [
        const Glass(child: Text('Spotify for Creators, Apple Podcasts Connect ya YouTube Studio se export (CSV / Excel) dijiye ya chipkaiye. '
            'Hoola sirf aapki file ke number dikhata hai.', style: TextStyle(fontSize: 12.5))),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'File chuno', icon: Icons.upload_file_rounded, height: 42, onTap: () async {
            await _upload(context, widget.app, '/api/podcast/stats/file', const ['csv', 'xlsx', 'txt']);
            await _load();
          }),
          GlassButton(label: 'Chipkao', icon: Icons.content_paste_rounded, height: 42, onTap: () async {
            final f = await _form(context, 'Export ka text', const [('text', 'CSV text'), ('platform', 'spotify / apple / youtube')]);
            if (f == null) return;
            await _run('POST', '/api/podcast/stats', f);
          }),
        ]),
        const SizedBox(height: 10),
        Glass(child: Text(_s(_stats?['say']))),
        for (final e in _list(_stats?['episodes']))
          Glass(margin: const EdgeInsets.only(top: 8), child: Text(
              '${_s(e['number'])} ${_s(e['title'])}\n${_s(e['plays'])} plays · ${_s(e['listeners'])} listeners'
              '${e['consumption'] == null ? '' : ' · ${_s(e['consumption'])}% suna'}',
              style: const TextStyle(fontSize: 12.5))),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final feed = _m(_d?['feed']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text('${_s(st['show']).isEmpty ? 'Show ka naam nahi' : _s(st['show'])} · host ${_s(st['host'])} · ${_s(st['category'])} · '
          '${st['explicit'] == true ? 'explicit' : 'clean'} · ${_s(st['language'])}')),
      const SizedBox(height: 10),
      GlassButton(label: 'Show badlo', icon: Icons.edit_rounded, height: 44, onTap: () async {
        final f = await _form(context, 'Show', const [('show', 'Show ka naam'), ('host', 'Host'), ('author', 'Author / company'),
          ('description', 'Show ke baare mein'), ('language', 'Bhasha (hi / mr / en)'), ('category', 'Apple category (Business, Education ...)'),
          ('owner_email', 'Owner email (feed mein dikhega)'), ('website', 'Website'), ('upi_id', 'UPI ID'), ('gstin', 'GSTIN'),
          ('business', 'Business ka naam (invoice)'), ('release_terms', 'Apni release wording (khaali = Hoola ki shuruaati)')],
            initial: {for (final k in ['show', 'host', 'author', 'description', 'language', 'category', 'owner_email', 'website',
              'upi_id', 'gstin', 'business', 'release_terms']) k: _s(st[k])});
        if (f == null) return;
        await _run('PUT', '/api/podcast/settings', f);
      }),
      const SizedBox(height: 8),
      GlassButton(label: 'Artwork (1400-3000 px square)', icon: Icons.image_rounded, height: 44, onTap: () async {
        await _upload(context, widget.app, '/api/podcast/artwork', const ['jpg', 'jpeg', 'png']);
        await _load();
      }),
      if (_strs(_m(st['artwork'])['problems']).isNotEmpty) Text(_strs(_m(st['artwork'])['problems']).join(' '), style: const TextStyle(color: C.warn)),
      const SizedBox(height: 8),
      SwitchListTile(
        title: const Text('Hoola RSS feed'),
        subtitle: Text(feed['on'] == true ? _s(feed['url']) : 'Band (apne hosting par publish pack daaliye)'),
        value: feed['on'] == true,
        onChanged: _busy ? null : (v) => _run('POST', '/api/podcast/feed', {'on': v}),
      ),
      if (feed['on'] == true)
        TextButton(onPressed: () => _run('POST', '/api/podcast/feed', {'on': true, 'new_token': true}), child: const Text('Naya feed link (purana band)')),
      Text(_s(st['note']), style: const TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Episode', 'Guest', 'Sponsor', 'Music', 'Numbers', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Podcast Sahayak'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _episodes, _guests, _sponsors, _music, _numbers, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class PodcastEpisodePage extends StatefulWidget {
  const PodcastEpisodePage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<PodcastEpisodePage> createState() => _PodcastEpisodePageState();
}

class _PodcastEpisodePageState extends State<PodcastEpisodePage> {
  Map<String, dynamic>? _e;
  Map<String, dynamic> _cross = {};
  bool _busy = false;
  String get _base => '/api/podcast/episodes/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final e = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() => _e = e);
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

  @override
  Widget build(BuildContext context) {
    final e = _e;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(e == null ? widget.ref : '${_s(e['number'])} · ${_s(e['title'])}')),
      body: e == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(16), children: _body(e))),
    );
  }

  List<Widget> _body(Map<String, dynamic> e) {
    final ck = _m(e['checks']);
    final nt = _m(e['notes']);
    final lo = _m(e['loudness']);
    final au = _m(e['audio']);
    final live = e['status'] == 'published';
    return [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [Expanded(child: Text(_stLabel[_s(e['status'])] ?? _s(e['status']), style: const TextStyle(fontWeight: FontWeight.w800))),
          if (_s(e['record_at']).isNotEmpty) Pill('Rec ${_s(e['record_at'])}')]),
        for (final g in _list(e['guests'])) Text('Guest: ${_s(g['name'])} · release ${_s(_m(g['release'])['status'])}'),
      ])),
      const SizedBox(height: 10),
      if (_strs(ck['blockers']).isNotEmpty) ...[
        const Caption('PUBLISH SE PEHLE'),
        for (final b in _strs(ck['blockers'])) Text('✗ $b', style: const TextStyle(color: C.bad, fontSize: 12.5)),
      ],
      for (final w in _strs(ck['warnings'])) Text('• $w', style: const TextStyle(color: C.warn, fontSize: 12.5)),
      const SizedBox(height: 12),
      const Caption('RUN SHEET'),
      for (final r in _list(e['run_sheet']))
        Text('${_s(r['at'])} (${_s(r['mins'])} min) ${_s(r['what'])}${_strs(r['notes']).isEmpty ? '' : '\n   ${_strs(r['notes']).join('\n   ')}'}',
            style: const TextStyle(fontSize: 12.5)),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Run sheet banao', height: 38, onTap: _busy || live ? null : () => _run('POST', '$_base/run_sheet', {})),
        GlassButton(label: 'Topics / samay', height: 38, onTap: _busy || live ? null : () async {
          final f = await _form(context, 'Episode', const [('topics', 'Topics (comma se)'), ('record_at', 'Recording (YYYY-MM-DD HH:MM)'),
            ('publish_on', 'Publish (YYYY-MM-DD)')]);
          if (f == null) return;
          await _run('POST', '/api/podcast/episodes', {'episode': widget.ref, ...f,
            if (f['topics'] != null) 'topics': f['topics']!.split(',')});
        }),
      ]),
      const SizedBox(height: 12),
      const Caption('AUDIO'),
      if (au.isNotEmpty) Text('${_s(au['name'])} · ${_hms(au['duration'])}${au['normalized'] == true ? ' · barabar ki hui copy' : ''}'),
      if (lo.isNotEmpty)
        Text('Loudness ${_s(lo['lufs'])} LUFS · peak ${_s(lo['true_peak'])} dBTP ${lo['ok'] == true ? '✓' : '(Apple: -16 ±1, peak ≤ -1)'}',
            style: TextStyle(fontSize: 12.5, color: lo['ok'] == true ? C.ok : C.warn)),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Audio do', icon: Icons.upload_rounded, height: 38, onTap: _busy || live ? null : () async {
          setState(() => _busy = true);
          await _upload(context, widget.app, '$_base/audio', const ['mp3', 'm4a', 'wav', 'flac', 'aac', 'ogg', 'mp4']);
          await _load();
          if (mounted) setState(() => _busy = false);
        }),
        if (au.isNotEmpty && lo['ok'] != true)
          GlassButton(label: 'Awaaz barabar karo', height: 38, onTap: _busy || live ? null : () => _run('POST', '$_base/normalize', {})),
      ]),
      const SizedBox(height: 12),
      const Caption('TRANSCRIPT'),
      Text(e['has_transcript'] == true ? 'Hai (${_s(e['transcript_source'])})' : 'Abhi nahi', style: const TextStyle(fontSize: 12.5)),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Audio se banao', height: 38, onTap: _busy || au.isEmpty ? null : () => _run('POST', '$_base/transcribe', {})),
        GlassButton(label: 'SRT / VTT file', height: 38, onTap: _busy ? null : () async {
          await _upload(context, widget.app, '$_base/captions', const ['srt', 'vtt', 'txt']);
          await _load();
        }),
        if (e['has_transcript'] == true)
          GlassButton(label: 'Bolne wale', height: 38, onTap: () async {
            final f = await _form(context, 'Naam', const [('S1', 'S1 kaun?'), ('S2', 'S2 kaun?'), ('S3', 'S3 kaun?')]);
            if (f == null) return;
            await _run('POST', '$_base/speakers', {'names': f});
          }),
      ]),
      const SizedBox(height: 12),
      const Caption('SHOW NOTES'),
      if (nt.isNotEmpty) ...[
        Text(_s(nt['summary'])),
        for (final p in _strs(nt['points'])) Text('• $p', style: const TextStyle(fontSize: 12.5)),
        if (_list(nt['chapters']).isNotEmpty) ...[
          const SizedBox(height: 6),
          for (final c in _list(nt['chapters'])) Text('${_hms(c['start'])} ${_s(c['title'])}', style: const TextStyle(fontSize: 12.5)),
        ],
        for (final q in _list(nt['quotes'])) Text('“${_s(q['text'])}” (${_hms(q['start'])})', style: const TextStyle(fontSize: 12, color: C.muted)),
        for (final d in _strs(nt['dropped'])) Text('Hataya: $d', style: const TextStyle(fontSize: 11.5, color: C.faint)),
      ],
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Notes banao', height: 38, onTap: _busy || e['has_transcript'] != true || live ? null : () => _run('POST', '$_base/notes', {})),
        if (nt.isNotEmpty)
          GlassButton(label: 'Khud badlo', height: 38, onTap: live ? null : () async {
            final f = await _form(context, 'Show notes', const [('summary', 'Summary'), ('points', 'Points (ek line ek)'),
              ('chapters', 'Chapters (00:00 Title, har line)')], initial: {
              'summary': _s(nt['summary']),
              'points': _strs(nt['points']).join('\n'),
              'chapters': _list(nt['chapters']).map((c) => '${_hms(c['start'])} ${_s(c['title'])}').join('\n'),
            });
            if (f == null) return;
            await _run('PUT', '$_base/notes', {...f, if (f['points'] != null) 'points': f['points']!.split('\n')});
          }),
      ]),
      const SizedBox(height: 12),
      const Caption('MUSIC AUR SPONSOR'),
      for (final m in _list(e['music'])) Text('${m['cleared'] == true ? '✓' : '✗'} ${_s(m['title'])} · ${_s(m['licence_label'])}'),
      for (final r in _list(e['reads']))
        Text('${_m(r['disclosure'])['ok'] == true ? '✓' : '✗'} ${_s(r['sponsor'])} (${_s(r['slot'])}-roll): ${_s(r['script'])}',
            style: const TextStyle(fontSize: 12.5)),
      Wrap(spacing: 8, runSpacing: 6, children: [
        GlassButton(label: 'Music jodo', height: 38, onTap: live ? null : () async {
          final f = await _form(context, 'Music', const [('music', 'M-001 / naam')]);
          if (f == null) return;
          await _run('POST', '$_base/music', f);
        }),
        GlassButton(label: 'Sponsor read', height: 38, onTap: live ? null : () async {
          final f = await _form(context, 'Sponsor read (#Ad shuru + aakhir Hoola lagata hai)', const [('sponsor', 'S-001 / brand'),
            ('slot', 'pre / mid / post'), ('script', 'Script')]);
          if (f == null) return;
          await _run('POST', '$_base/reads', f);
        }),
      ]),
      const SizedBox(height: 16),
      if (!live)
        GradientButton(label: 'Publish ka card banao', icon: Icons.podcasts_rounded, height: 48,
            onTap: _busy || _strs(ck['blockers']).isNotEmpty ? null : () => _run('POST', '$_base/publish_request', {'where': 'feed'}))
      else ...[
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: 'Cross-post drafts', height: 40, onTap: () async {
            final r = _m(await widget.app.api!.call('GET', '$_base/crosspost'));
            if (mounted) setState(() => _cross = _m(r['drafts']));
          }),
          GlassButton(label: 'Link darj karo', height: 40, onTap: () async {
            final f = await _form(context, 'Kahan daala?', const [('platform', 'spotify / apple / youtube'), ('url', 'https:// link')]);
            if (f == null) return;
            await _run('POST', '$_base/posted', f);
          }),
          GlassButton(label: 'Feed se hatao', height: 40, color: C.bad, onTap: () async {
            final f = await _form(context, 'Kyun hatana hai?', const [('reason', 'Wajah')]);
            if (f == null) return;
            await _run('POST', '$_base/unpublish', f);
          }),
        ]),
        for (final k in _cross.keys)
          Glass(margin: const EdgeInsets.only(top: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [Expanded(child: Text(k.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w800))),
              IconButton(icon: const Icon(Icons.copy_rounded), onPressed: () {
                Clipboard.setData(ClipboardData(text: _s(_cross[k])));
                _snack(context, 'Copy');
              })]),
            Text(_s(_cross[k]), style: const TextStyle(fontSize: 12.5)),
          ])),
      ],
    ];
  }
}

/// Chat / call card for `podcast_card` (publish, invite, release, sponsor, invoice, message): her tap decides (hash checked).
class PodcastCardCard extends StatefulWidget {
  const PodcastCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<PodcastCardCard> createState() => _PodcastCardCardState();
}

class _PodcastCardCardState extends State<PodcastCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

  Future<void> _decide(bool yes) async {
    String reason = '';
    if (!yes) {
      final f = await _form(context, 'Kyun nahi?', const [('reason', 'Wajah (optional)')], ok: 'Nahi');
      if (f == null) return;
      reason = f['reason'] ?? '';
    }
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '/api/podcast/cards/${_s(_c['id'])}/decide',
          body: {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason}, timeout: const Duration(minutes: 3)));
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
    final who = [sh['episode'], sh['title'], sh['name'], sh['brand']].where((x) => x != null && '$x'.isNotEmpty).join(' · ');
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'publish' => Icons.podcasts_rounded, 'invite' => Icons.mail_outline_rounded, 'release' => Icons.verified_user_rounded,
            'invoice' => Icons.receipt_long_rounded, 'sponsor' => Icons.handshake_rounded, _ => Icons.chat_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · $who', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'aapki haan?', 'approved' => 'haan', 'rejected' => 'nahi', 'stale' => 'purana', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        if (kind == 'publish') ...[
          Text(_s(sh['summary']), style: const TextStyle(fontSize: 12.5)),
          for (final g in _list(sh['guests'])) Text('Guest ${_s(g['name'])}: release ${_s(g['release'])}', style: const TextStyle(fontSize: 12)),
          for (final m in _list(sh['music'])) Text('Music ${_s(m['title'])}: ${_s(m['licence'])}', style: const TextStyle(fontSize: 12)),
          for (final r in _list(sh['reads'])) Text('#Ad ${_s(r['sponsor'])} (${_s(r['slot'])})', style: const TextStyle(fontSize: 12)),
          if (_strs(sh['ai_parts']).isNotEmpty) Text('AI label: ${_strs(sh['ai_parts']).join(', ')}', style: const TextStyle(fontSize: 12)),
          Text(sh['where'] == 'feed' ? 'Hoola RSS feed mein jayega (public)' : 'Publish pack aapki files mein (aap hosting par daaliye)',
              style: const TextStyle(fontSize: 12, color: C.muted)),
        ],
        if (kind == 'invoice') Text('${_s(sh['number'])} · ${_s(sh['total_text'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(sh['text']).isNotEmpty) Text(_s(sh['text']), style: const TextStyle(fontSize: 12.5), maxLines: 12, overflow: TextOverflow.ellipsis),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(child: GradientButton(label: kind == 'publish' ? 'Haan, publish karo' : 'Haan', height: 42,
                onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) _draftButtons(context, _draft),
      ]),
    );
  }
}

/// Chat card for `podcast_alert` / `podcast_day` (notes, no action needed).
class PodcastNoteCard extends StatelessWidget {
  const PodcastNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Row(children: [
          const Icon(Icons.podcasts_rounded, color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13.5))),
          IconButton(icon: const Icon(Icons.open_in_new_rounded), onPressed: () => Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => PodcastScreen(app: app)))),
        ]),
      );
}
