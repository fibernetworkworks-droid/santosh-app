/// Profile > Patrakar Sahayak: Hoola as a journalist's coworker (reporters, local news portals, YouTube news channels, stringers).
/// Aaj (deadlines, replies late, grievances due, election silence, cards waiting) · Stories (pitch -> draft -> fact check ->
/// ready -> published) · Source (masked refs S-001; identity only on her own screen) · Shikayat (IT Rules 2021, 15 days) · Niyam.
/// Publishing, right-of-reply letters, pitches, corrections and grievance answers run only after HER tap on the card. The server
/// refuses to publish while a hard red flag stays (victim / child identity, source identity, a quote nobody said, election
/// silence, embargo, blanks).
library;

import 'dart:async';

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

const _bigFields = {'text', 'notes', 'body', 'pitch', 'transcript', 'answer', 'response', 'rules', 'questions', 'allegations'};

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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: _bigFields.contains(k) ? 5 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

List<String> _lines(String? v) => (v ?? '').split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

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

Widget _draftButtons(BuildContext context, Map<String, dynamic> d) {
  final wa = _s(d['wa']), mail = _s(d['mailto']), text = _s(d['text']);
  if (wa.isEmpty && mail.isEmpty && text.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
    if (mail.isNotEmpty) GlassButton(label: 'Email draft', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (text.isNotEmpty)
      GlassButton(label: 'Copy', icon: Icons.copy_rounded, height: 40, onTap: () {
        Clipboard.setData(ClipboardData(text: text));
        _snack(context, 'Copied.');
      }),
  ]);
}

Widget _flags(Map<String, dynamic> chk) {
  final block = _list(chk['block']), warn = _list(chk['warn']);
  if (block.isEmpty && warn.isEmpty) {
    return chk.isEmpty ? const SizedBox.shrink() : const Text('No red flags.', style: TextStyle(color: C.ok));
  }
  String line(Map<String, dynamic> x) => '${_s(x['say'])}${_s(x['detail']).isEmpty ? '' : ' (${_s(x['detail'])})'}';
  return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    for (final b in block)
      Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('⛔ ${line(b)}', style: const TextStyle(color: C.bad, fontSize: 12.5))),
    for (final w in warn)
      Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('⚠ ${line(w)}', style: const TextStyle(color: C.warn, fontSize: 12))),
  ]);
}

const _statusLabel = {
  'pitch': 'Pitch', 'reporting': 'Reporting', 'draft': 'Draft', 'factcheck': 'Fact check', 'ready': 'Ready',
  'waiting': 'Waiting for your yes', 'published': 'Published', 'killed': 'Killed',
};

class PatrakarScreen extends StatefulWidget {
  const PatrakarScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PatrakarScreen> createState() => _PatrakarScreenState();
}

class _PatrakarScreenState extends State<PatrakarScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  String _filter = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/patrakar'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    return r;
  }

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => PatrakarStoryPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Widget _storyTile(Map<String, dynamic> x) {
    final title = _s(x['headline']).isEmpty ? _s(x['slug']) : _s(x['headline']);
    final sub = [_s(x['beat']), _s(x['deadline']).isEmpty ? '' : 'deadline ${_s(x['deadline'])}'].where((e) => e.isNotEmpty).join(' · ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _open(_s(x['number'])),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.article_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(x['number'])} · $title', style: const TextStyle(fontWeight: FontWeight.w700), maxLines: 2, overflow: TextOverflow.ellipsis),
                if (sub.isNotEmpty) Text(sub, style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
            ),
            Pill(_statusLabel[_s(x['status'])] ?? _s(x['status'])),
          ]),
        ),
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
        Padding(padding: const EdgeInsets.only(bottom: 10), child: PatrakarCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_list(day['due']).isNotEmpty) ...[const Caption('DEADLINE'), for (final x in _list(day['due'])) _storyTile(x)],
      if (_list(day['ready']).isNotEmpty) ...[const Caption('READY TO PUBLISH'), for (final x in _list(day['ready'])) _storyTile(x)],
      if (_list(day['replies_late']).isNotEmpty) ...[
        const Caption('REPLY DEADLINE PASSED'),
        for (final r in _list(day['replies_late']))
          ListTile(
            title: Text('${_s(r['number'])} · ${_s(r['party'])}'),
            subtitle: Text('Deadline ${_s(r['deadline'])}'),
            trailing: TextButton(onPressed: () => _run('POST', '/api/patrakar/replies/${_s(r['id'])}/none'), child: const Text('No reply received')),
          ),
      ],
      if (_strs(day['elections']).isNotEmpty) ...[const Caption('ELECTION'), for (final e in _strs(day['elections'])) Text('• $e')],
      const SizedBox(height: 12),
      GradientButton(label: 'New story', icon: Icons.add_rounded, onTap: _newStory),
    ]);
  }

  Future<void> _newStory() async {
    final f = await _form(context, 'New story', const [
      ('pitch', 'What the story is about (pitch)'),
      ('slug', 'Slug (short name)'),
      ('beat', 'Beat (crime, civic, politics...)'),
      ('deadline', 'Deadline (YYYY-MM-DD)'),
      ('area', 'Area / constituency'),
      ('notes', 'Reporting notes'),
      ('protect', 'Names never to publish (victims / children), comma separated'),
    ]);
    if (f == null) return;
    final body = <String, dynamic>{...f};
    final p = f['protect'];
    if (p != null) body['protect'] = p.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    final r = await _run('POST', '/api/patrakar/stories', body);
    final num = _s(_m(r?['story'])['number']);
    if (num.isNotEmpty) _open(num);
  }

  Widget _stories() {
    final all = _list(_d?['stories']);
    final shown = _filter.isEmpty ? all : all.where((x) => _s(x['status']) == _filter).toList();
    return ListView(padding: const EdgeInsets.all(16), children: [
      Wrap(spacing: 6, runSpacing: 6, children: [
        ChoiceChip(label: const Text('All'), selected: _filter.isEmpty, onSelected: (_) => setState(() => _filter = '')),
        for (final e in _statusLabel.entries)
          ChoiceChip(label: Text(e.value), selected: _filter == e.key, onSelected: (_) => setState(() => _filter = e.key)),
      ]),
      const SizedBox(height: 10),
      for (final x in shown) _storyTile(x),
      if (shown.isEmpty) const Text('No stories.', style: TextStyle(color: C.muted)),
      const SizedBox(height: 10),
      GradientButton(label: 'New story', icon: Icons.add_rounded, onTap: _newStory),
    ]);
  }

  Future<void> _reveal(String ref) async {
    final r = await _call(context, widget.app, 'POST', '/api/patrakar/sources/$ref/reveal');
    if (r == null || !mounted) return;
    final id = _m(r['identity']);
    var open = true;
    final timer = Timer(const Duration(seconds: 20), () {
      if (open && mounted) Navigator.of(context, rootNavigator: true).pop();
    });
    await showDialog<void>(
      context: context,
      builder: (d) {
        return AlertDialog(
          title: Text('$ref (only for you, 20 sec)'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final k in const ['name', 'phone', 'contact', 'notes'])
              if (_s(id[k]).isNotEmpty) Text('$k: ${_s(id[k])}'),
            if (id.isEmpty) const Text('The identity has been removed.'),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Close'))],
        );
      },
    );
    open = false;
    timer.cancel();
  }

  Widget _sources() {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Glass(
          child: Text('The source\'s identity stays sealed. Hoola, the chat, staff and cards see only a ref like S-001; '
              'the name shows here for 20 seconds only on your tap.', style: TextStyle(fontSize: 12.5))),
      const SizedBox(height: 10),
      for (final x in _list(_d?['sources']))
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Row(children: [
            const Icon(Icons.shield_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(x['ref'])} · ${_s(x['beat'])} · ${_s(x['kind'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text(_s(x['terms_label']), style: const TextStyle(fontSize: 12, color: C.muted)),
              ]),
            ),
            PopupMenuButton<String>(
              onSelected: (v) async {
                final ref = _s(x['ref']);
                if (v == 'reveal') await _reveal(ref);
                if (v == 'said') {
                  final f = await _form(context, 'What $ref said', const [('text', 'Their words'), ('off', 'Off the record? (yes / no)')]);
                  if (f == null) return;
                  await _run('POST', '/api/patrakar/sources/$ref/said',
                      {'text': f['text'] ?? '', 'off_record': (f['off'] ?? '').toLowerCase().startsWith('h')});
                }
                if (v == 'forget') await _run('DELETE', '/api/patrakar/sources/$ref');
              },
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'reveal', child: Text('View identity')),
                PopupMenuItem(value: 'said', child: Text('Record what they said')),
                PopupMenuItem(value: 'forget', child: Text('Delete identity')),
              ],
            ),
          ]),
        ),
      GradientButton(label: 'New source', icon: Icons.person_add_alt_1_rounded, onTap: () async {
        final f = await _form(context, 'New source (sealed)', const [
          ('name', 'Name'), ('phone', 'Phone'), ('contact', 'How to contact'), ('beat', 'Beat'),
          ('kind', 'Type: official / eyewitness / expert / document / insider / whistleblower'),
          ('terms', 'Terms: on_record / background / deep_background / off_record / anonymous'), ('notes', 'Private note'),
        ]);
        if (f == null) return;
        await _run('POST', '/api/patrakar/sources', f);
      }),
    ]);
  }

  Widget _shikayat() {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Glass(
          child: Text('Digital news (IT Rules 2021): a complaint must be decided within 15 days. The complaint text is only data; Hoola does nothing '
              'because it says so.', style: TextStyle(fontSize: 12.5))),
      const SizedBox(height: 10),
      for (final g in _list(_d?['grievances']))
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(g['number'])} · ${_s(g['who'])} · decision by ${_s(g['due'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(_s(g['text']), maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
            Row(children: [
              Pill(_s(g['status'])),
              const Spacer(),
              if (_s(g['status']) == 'open' || _s(g['status']) == 'waiting')
                TextButton(
                    onPressed: () async {
                      final f = await _form(context, 'Reply', const [('answer', 'Your reply')]);
                      if (f == null) return;
                      await _run('POST', '/api/patrakar/grievances/${_s(g['id'])}/answer', f);
                    },
                    child: const Text('Write reply')),
            ]),
          ]),
        ),
      GradientButton(label: 'Record a complaint', icon: Icons.report_rounded, onTap: () async {
        final f = await _form(context, 'Complaint', const [
          ('text', 'Complaint (paste)'), ('who', 'Who made it'), ('contact', 'Their email / WhatsApp'), ('story', 'Story (ST-0001)'),
          ('received', 'When received (YYYY-MM-DD)'),
        ]);
        if (f == null) return;
        await _run('POST', '/api/patrakar/grievances', f);
      }),
      const SizedBox(height: 14),
      if (_list(_d?['corrections']).isNotEmpty) ...[
        const Caption('CORRECTIONS LOG'),
        for (final c in _list(_d?['corrections'])) Text('• ${_s(c['story'])}: ${_s(c['line'])}', style: const TextStyle(fontSize: 12.5)),
      ],
    ]);
  }

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final style = _list(st['style']).map((r) => '${_s(r['from'])} = ${_s(r['to'])}').join('\n');
    final els = _list(st['elections']);
    const keys = ['outlet', 'kind', 'reporter', 'place', 'contact', 'gro_name', 'gro_contact', 'reply_days', 'morning_time'];
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(st['outlet']).isEmpty ? 'No organisation name given' : _s(st['outlet']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text('${_s(st['reporter'])} · ${_s(st['place'])} · ${_s(st['kind'])}', style: const TextStyle(color: C.muted)),
          Text('Grievance officer: ${_s(st['gro_name']).isEmpty ? '-' : _s(st['gro_name'])} ${_s(st['gro_contact'])}',
              style: const TextStyle(fontSize: 12.5)),
          Text('${_s(st['reply_days'])} days to reply', style: const TextStyle(fontSize: 12.5)),
          for (final n in _strs(st['notes'])) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Organisation / byline', icon: Icons.badge_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Organisation', const [
            ('outlet', 'Portal / channel / newspaper'), ('kind', 'portal / youtube / stringer / print / freelance'), ('reporter', 'Byline name'),
            ('place', 'Dateline (city)'), ('contact', 'Contact (on letters)'), ('gro_name', 'Grievance officer'),
            ('gro_contact', 'Grievance officer contact'), ('reply_days', 'Days to reply (1-14)'), ('morning_time', 'Morning note (HH:MM)'),
          ], initial: {for (final k in keys) k: _s(st[k])});
          if (f == null) return;
          final body = <String, dynamic>{...f};
          final rd = f['reply_days'];
          if (rd != null) body['reply_days'] = int.tryParse(rd) ?? 2;
          await _run('PUT', '/api/patrakar/settings', body);
        }),
        GlassButton(label: 'Style sheet', icon: Icons.spellcheck_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Style (each line: wrong = right)', const [('text', 'thief = the accused')], initial: {'text': style});
          if (f == null) return;
          final rows = <Map<String, String>>[];
          for (final l in _lines(f['text'])) {
            final kv = l.split('=');
            if (kv.length == 2) rows.add({'from': kv[0].trim(), 'to': kv[1].trim()});
          }
          await _run('PUT', '/api/patrakar/settings', {'style': rows});
        }),
        GlassButton(label: 'Banned words', icon: Icons.block_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Never write (comma separated)', const [('text', 'words')],
              initial: {'text': _strs(st['avoid']).join(', ')});
          if (f == null) return;
          await _run('PUT', '/api/patrakar/settings', {'avoid': f['text'] ?? ''});
        }),
        GlassButton(label: 'Election date', icon: Icons.how_to_vote_rounded, height: 40, onTap: () async {
          final f = await _form(context, 'Voting (RP Act s.126: 48 hours of silence)', const [
            ('area', 'Area / constituency'), ('start', 'Voting starts (YYYY-MM-DD HH:MM)'), ('end', 'Voting ends (YYYY-MM-DD HH:MM)'),
          ]);
          final end = f?['end'];
          if (f == null || end == null) return;
          final list = [
            ...els,
            {
              'area': f['area'] ?? '',
              'phases': [
                {'start': f['start'] ?? '', 'end': end}
              ]
            }
          ];
          await _run('PUT', '/api/patrakar/settings', {'elections': list});
        }),
      ]),
      if (els.isNotEmpty) ...[
        const SizedBox(height: 10),
        const Caption('ELECTION'),
        for (final e in els)
          Text('• ${_s(e['area'])}: ${_list(e['phases']).map((p) => '${_s(p['start'])} - ${_s(p['end'])}').join(', ')}'),
      ],
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Today', 'Stories', 'Source', 'Complaints', 'Rules'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Journalist Assistant'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _stories, _sources, _shikayat, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

class PatrakarStoryPage extends StatefulWidget {
  const PatrakarStoryPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<PatrakarStoryPage> createState() => _PatrakarStoryPageState();
}

class _PatrakarStoryPageState extends State<PatrakarStoryPage> {
  Map<String, dynamic>? _v;
  Map<String, dynamic> _chk = {};
  bool _busy = false;
  final _head = TextEditingController();
  final _body = TextEditingController();

  String get _p => '/api/patrakar/stories/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _head.dispose();
    _body.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final v = _m(await widget.app.api!.call('GET', _p));
      if (!mounted) return;
      setState(() {
        _v = v;
        _chk = _m(v['checks']);
        _head.text = _s(v['headline']);
        _body.text = _s(v['body']);
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null && r['check'] != null) _chk = _m(r['check']);
        if (r != null && r['block'] != null) _chk = r;
      });
    }
    return r;
  }

  Widget _claimTile(Map<String, dynamic> c) {
    final st = _s(c['status']);
    final color = switch (st) { 'supported' || 'attributed' => C.ok, 'contradicted' => C.bad, 'cut' => C.faint, _ => C.warn };
    String ev(Map<String, dynamic> e) {
      final where = _s(e['url']).isNotEmpty ? _s(e['url']) : (_s(e['ref']).isNotEmpty ? _s(e['ref']) : _s(e['note']));
      final how = e['found'] == true ? ' · read, found' : (e['read'] == true ? ' · read, not found' : (e['read'] == false ? ' · did not open' : ''));
      return '↳ $where$how';
    }

    return Glass(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Pill(st, fg: color),
          const SizedBox(width: 6),
          Pill(_s(c['kind'])),
          const Spacer(),
          PopupMenuButton<String>(
            onSelected: (v) async {
              final id = _s(c['id']);
              if (v == 'url') {
                final f = await _form(context, 'Which page is it on? (Hoola will open it itself)', const [('url', 'https://...')]);
                if (f == null) return;
                await _run('POST', '/api/patrakar/claims/$id/check', f);
              } else if (v == 'search') {
                await _run('POST', '/api/patrakar/claims/$id/check', <String, dynamic>{});
              } else if (v == 'source') {
                final f = await _form(context, 'Which source confirmed it', const [('source', 'S-001')]);
                if (f == null) return;
                await _run('POST', '/api/patrakar/claims/$id/mark', {'status': 'supported', ...f});
              } else if (v == 'mine') {
                final f = await _form(context, 'How you confirmed it', const [('note', 'I saw it myself / document...')]);
                if (f == null) return;
                await _run('POST', '/api/patrakar/claims/$id/mark', {'status': 'supported', ...f});
              } else {
                await _run('POST', '/api/patrakar/claims/$id/mark', {'status': v});
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'url', child: Text('Check from a link')),
              PopupMenuItem(value: 'search', child: Text('Search the web')),
              PopupMenuItem(value: 'source', child: Text('Confirmed by the source')),
              PopupMenuItem(value: 'mine', child: Text('I confirmed it')),
              PopupMenuItem(value: 'attributed', child: Text('Allegation / attribution only')),
              PopupMenuItem(value: 'contradicted', child: Text('Turned out wrong')),
              PopupMenuItem(value: 'cut', child: Text('Removed from copy')),
            ],
          ),
        ]),
        Text(_s(c['text']), style: const TextStyle(fontSize: 13)),
        for (final e in _list(c['evidence'])) Text(ev(e), style: const TextStyle(fontSize: 11.5, color: C.muted)),
      ]),
    );
  }

  Future<void> _publish() async {
    String dest = 'copy', mode = 'draft';
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('Where to publish?'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(spacing: 6, children: [
              ChoiceChip(label: const Text('Copy (I\'ll post it)'), selected: dest == 'copy', onSelected: (_) => set(() => dest = 'copy')),
              ChoiceChip(label: const Text('WordPress'), selected: dest == 'wordpress', onSelected: (_) => set(() => dest = 'wordpress')),
            ]),
            if (dest == 'wordpress')
              Wrap(spacing: 6, children: [
                ChoiceChip(label: const Text('Draft'), selected: mode == 'draft', onSelected: (_) => set(() => mode = 'draft')),
                ChoiceChip(label: const Text('Publish directly'), selected: mode == 'publish', onSelected: (_) => set(() => mode = 'publish')),
              ]),
            const SizedBox(height: 6),
            const Text('A card will be made; publishing only with your yes.', style: TextStyle(fontSize: 12, color: C.muted)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Make card')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    await _run('POST', '$_p/publish', {'dest': dest, 'mode': mode});
  }

  Future<void> _styleSuggest() async {
    final r = await _call(context, widget.app, 'GET', '$_p/style');
    if (r == null || !mounted || _strs(r['changes']).isEmpty) return;
    final yes = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              title: const Text('Style change'),
              content: Text(_strs(r['changes']).join('\n')),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('No')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Apply')),
              ],
            ));
    if (yes == true) await _run('PATCH', _p, {'headline': _s(r['headline']), 'body': _s(r['body'])});
  }

  Widget _interviewTile(Map<String, dynamic> i) => Glass(
        margin: const EdgeInsets.only(bottom: 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_s(i['who'])} · ${_s(i['terms'])}${i['consent'] == true ? ' · consent' : ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
          Text(_s(i['transcript']), maxLines: 5, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
          for (final q in _strs(i['quotes'])) Text('“$q”', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
          TextButton(
              onPressed: () async {
                final f = await _form(context, 'Quote (exact words)', const [('text', 'Quote')]);
                if (f == null) return;
                await _run('POST', '/api/patrakar/interviews/${_s(i['id'])}/quote', f);
              },
              child: const Text('Choose a quote')),
        ]),
      );

  Widget _replyTile(Map<String, dynamic> r) => ListTile(
        title: Text('${_s(r['number'])} · ${_s(r['party'])} · ${_s(r['status'])}'),
        subtitle: Text(_s(r['response']).isNotEmpty ? _s(r['response']) : 'Deadline ${_s(r['deadline'])}', maxLines: 3),
        trailing: _s(r['status']) == 'sent'
            ? TextButton(
                onPressed: () async {
                  final f = await _form(context, 'Their reply', const [('response', 'Reply (paste)')]);
                  if (f == null) return;
                  await _run('POST', '/api/patrakar/replies/${_s(r['id'])}/answer', f);
                },
                child: const Text('Reply received'))
            : null,
      );

  @override
  Widget build(BuildContext context) {
    final v = _v;
    if (v == null) {
      return Scaffold(backgroundColor: C.bgTop, appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.ref)),
          body: const Center(child: CircularProgressIndicator()));
    }
    final pub = _m(v['published']);
    final protected = (v['protected_names'] is num) ? (v['protected_names'] as num).toInt() : 0;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.ref),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(spacing: 6, runSpacing: 6, children: [
              Pill(_statusLabel[_s(v['status'])] ?? _s(v['status'])),
              if (_s(v['deadline']).isNotEmpty) Pill('deadline ${_s(v['deadline'])}'),
              if (protected > 0) Pill('$protected names protected', fg: C.ok),
            ]),
            if (_s(v['pitch']).isNotEmpty) Text(_s(v['pitch']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
            if (_s(pub['url']).isNotEmpty)
              TextButton(onPressed: () => Native.openExternal(url: _s(pub['url'])), child: const Text('Open the published story')),
          ]),
        ),
        const SizedBox(height: 10),
        const Caption('COPY'),
        TextField(controller: _head, decoration: const InputDecoration(labelText: 'Headline')),
        TextField(controller: _body, decoration: const InputDecoration(labelText: 'Story'), maxLines: 12, minLines: 5),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Save', icon: Icons.save_rounded, height: 40,
              onTap: _busy ? null : () => _run('PATCH', _p, {'headline': _head.text, 'body': _body.text})),
          GlassButton(label: 'Let Hoola write a draft', icon: Icons.edit_note_rounded, height: 40, onTap: _busy ? null : () async {
            final f = await _form(context, 'What kind of draft?', const [('ask', 'For example: 300 words, straight news')]);
            if (f == null) return;
            await _run('POST', '$_p/write', f);
          }),
          GlassButton(label: 'Check', icon: Icons.fact_check_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_p/check')),
          GlassButton(label: 'Style', icon: Icons.spellcheck_rounded, height: 40, onTap: _styleSuggest),
        ]),
        const SizedBox(height: 8),
        _flags(_chk),
        const SizedBox(height: 14),
        Row(children: [
          const Expanded(child: Caption('FACT SHEET')),
          TextButton(onPressed: _busy ? null : () => _run('POST', '$_p/claims/extract'), child: const Text('Pull claims out of the copy')),
        ]),
        for (final c in _list(v['claims'])) _claimTile(c),
        const SizedBox(height: 10),
        Row(children: [
          const Expanded(child: Caption('INTERVIEW')),
          TextButton(
              onPressed: () async {
                final f = await _form(context, 'Interview', const [
                  ('transcript', 'Transcript (paste)'), ('file_id', 'Or audio file_id (sent in the chat)'), ('who', 'Who'),
                  ('source', 'Source ref (S-001, if confidential)'), ('consent', 'Permission to record received? (yes / no)'),
                ]);
                if (f == null) return;
                await _run('POST', '$_p/interviews', {...f, 'consent': (f['consent'] ?? '').toLowerCase().startsWith('h')});
              },
              child: const Text('Add')),
        ]),
        for (final i in _list(v['interviews'])) _interviewTile(i),
        const SizedBox(height: 10),
        const Caption('CHANCE TO REPLY (RIGHT OF REPLY)'),
        for (final r in _list(v['replies'])) _replyTile(r),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Ask for a reply', icon: Icons.question_answer_rounded, height: 40, onTap: () async {
            final f = await _form(context, 'Right of reply', const [
              ('party', 'To whom (the person accused)'), ('phone', 'WhatsApp'), ('email', 'Email'),
              ('allegations', 'Allegations (one per line)'), ('questions', 'Questions (one per line)'),
            ]);
            if (f == null) return;
            await _run('POST', '$_p/reply', {...f, 'allegations': _lines(f['allegations']), 'questions': _lines(f['questions'])});
          }),
          GlassButton(label: 'Send pitch', icon: Icons.send_rounded, height: 40, onTap: () async {
            final f = await _form(context, 'Pitch to editor',
                const [('to', 'Editor'), ('phone', 'WhatsApp'), ('email', 'Email'), ('text', 'Pitch (blank = Hoola writes it)')]);
            if (f == null) return;
            await _run('POST', '$_p/pitch', f);
          }),
          GradientButton(label: 'Card to publish', icon: Icons.publish_rounded, height: 44, onTap: _busy ? null : _publish),
          if (_s(v['status']) == 'published')
            GlassButton(label: 'Correction', icon: Icons.edit_rounded, height: 40, onTap: () async {
              final f = await _form(context, 'Correction', const [
                ('wrong', 'What was written before'), ('right', 'What is correct'),
                ('kind', 'correction / clarification / update / retraction / apology'), ('why', 'Reason'),
              ]);
              if (f == null) return;
              await _run('POST', '$_p/correction', f);
            }),
          if (pub.isNotEmpty && _s(v['status']) != 'published')
            GlassButton(label: 'Added', icon: Icons.done_all_rounded, height: 40, onTap: () async {
              final f = await _form(context, 'Where was it published? (link)', const [('url', 'https://...')]);
              if (f == null) return;
              await _run('POST', '$_p/published', f);
            }),
          GlassButton(label: 'Word + fact sheet', icon: Icons.description_rounded, height: 40, onTap: () => _run('POST', '$_p/files')),
        ]),
        const SizedBox(height: 10),
        const Text('Hoola publishes or sends nothing by itself; it never invents quotes, figures or names. Red flags are not legal advice.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// patrakar_card: publish / reply / pitch / correction / grievance card waiting for her tap.
class PatrakarCardCard extends StatefulWidget {
  const PatrakarCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<PatrakarCardCard> createState() => _PatrakarCardCardState();
}

class _PatrakarCardCardState extends State<PatrakarCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _res = _m(_c['result']);

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
      final m = _m(await widget.app.api!.call('POST', '/api/patrakar/cards/$id/decide',
          body: {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason}));
      if (mounted) {
        setState(() {
          if (_m(m['card']).isNotEmpty) _c = _m(m['card']);
          _res = {..._m(_c['result']), if (m['draft'] != null) 'draft': m['draft'], if (m['text'] != null) 'text': m['text']};
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
    final preview = switch (kind) {
      'publish' => '${_s(sh['headline'])}\n\n${_s(sh['body'])}',
      'reply' => _s(sh['letter']),
      'pitch' => _s(sh['text']),
      'correction' => _s(sh['line']),
      'grievance' => _s(sh['answer']),
      _ => '',
    };
    final draft = _m(_res['draft']);
    final text = _s(_res['text']);
    final ref = _s(sh['story']).isNotEmpty ? _s(sh['story']) : _s(sh['grievance']);
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'publish' => Icons.publish_rounded,
            'reply' => Icons.question_answer_rounded,
            'pitch' => Icons.send_rounded,
            'correction' => Icons.edit_rounded,
            _ => Icons.report_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · $ref', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your yes?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'old', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        if (kind == 'publish')
          Text('${_s(sh['dest'])} · ${_s(sh['mode'])} · ${_s(sh['words'])} words · ${_s(sh['byline'])}',
              style: const TextStyle(fontSize: 12, color: C.muted)),
        if (kind == 'reply') Text('${_s(sh['party'])} · reply by ${_s(sh['deadline'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 6),
        Text(preview, maxLines: 10, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: 'Yes', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (draft.isNotEmpty) _draftButtons(context, draft),
        if (draft.isEmpty && text.isNotEmpty) _draftButtons(context, {'text': text}),
        const Text('Hoola publishes or sends nothing by itself: you send the draft after your yes.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// patrakar_alert / patrakar_day / patrakar_story: notes (reply deadline passed, grievance due, embargo over, election silence,
/// morning note, story started).
class PatrakarNoteCard extends StatelessWidget {
  const PatrakarNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final sn = _s(_m(data['story'])['number']);
    final story = sn.isNotEmpty ? sn : _s(data['ref']);
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.newspaper_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
            if (story.startsWith('ST-'))
              TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PatrakarStoryPage(app: app, ref: story))),
                child: Text('Open $story'),
              ),
          ]),
        ),
      ]),
    );
  }
}
