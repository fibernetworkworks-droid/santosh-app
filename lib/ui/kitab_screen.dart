/// Profile > Kitab Sahayak: Hoola as an author's / freelance editor's / small publisher's coworker (Hindi, Marathi, English).
/// Aaj (deadlines, follow-ups, legal deposit, cards waiting) · Kitaabein (books -> chapters, tracked suggestions, style sheet,
/// permissions, ISBN + checklist, submissions, royalty, files, client invoice / delivery) · Niyam (her name, role, rate, GST, UPI).
/// Edit passes only SUGGEST: her chapter text changes only when she ticks suggestions and taps "Maano" (or taps an accept card).
/// Pitches, permission letters, invoices and client delivery go out only after HER tap; Hoola sends nothing and moves no money.
library;

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

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

const _bigFields = {'text', 'blurb', 'letter', 'synopsis', 'guidelines', 'notes', 'rules', 'hook', 'bio'};

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
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: _bigFields.contains(k) ? 6 : 1),
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
  final wa = _s(draft['wa']), mail = _s(draft['mailto']);
  if (wa.isEmpty && mail.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 8, runSpacing: 6, children: [
    if (mail.isNotEmpty) GlassButton(label: 'Email draft', icon: Icons.mail_rounded, height: 40, onTap: () => Native.openExternal(url: mail)),
    if (wa.isNotEmpty) GlassButton(label: 'WhatsApp draft', icon: Icons.chat_rounded, height: 40, onTap: () => Native.openExternal(url: wa)),
  ]);
}

const _passLabel = {'proof': 'Proofread', 'copy': 'Copy edit', 'line': 'Line edit', 'developmental': 'Developmental'};
const _statusLabel = {
  'drafting': 'Writing', 'editing': 'Editing', 'submission': 'Submitted', 'production': 'Printing', 'published': 'Printed', 'done': 'Complete'
};

class KitabScreen extends StatefulWidget {
  const KitabScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<KitabScreen> createState() => _KitabScreenState();
}

class _KitabScreenState extends State<KitabScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/kitab'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  void _open(String ref) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => KitabBookPage(app: widget.app, ref: ref)))
      .then((_) => _load());

  Future<void> _newBook() async {
    final f = await _form(context, 'New book', const [
      ('title', 'Naam (title)'), ('author', 'Lekhak'), ('lang', 'Language: hi | mr | en'), ('kind', 'fiction | nonfiction | poetry | academic | children | translation'),
      ('genre', 'Genre'), ('deadline', 'Deadline (YYYY-MM-DD)'), ('client', 'Client name (if you are editing someone else\'s book)'),
    ]);
    if (f == null || !mounted) return;
    final body = <String, dynamic>{...f};
    final client = body.remove('client');
    if (client != null) {
      body['mine'] = false;
      body['client'] = {'name': client};
    }
    final r = await _call(context, widget.app, 'POST', '/api/kitab/books', body);
    await _load();
    final num = _s(_m(r?['book'])['number']);
    if (num.isNotEmpty) _open(num);
  }

  Widget _bookTile(Map<String, dynamic> b) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Glass(
          child: InkWell(
            onTap: () => _open(_s(b['number'])),
            child: Row(children: [
              const Icon(Icons.menu_book_rounded, color: C.accent),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(b['number'])} · ${_s(b['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('${_s(b['chapters'])} chapter · ${_s(b['words'])} shabd · ${_statusLabel[_s(b['status'])] ?? _s(b['status'])}'
                    '${b['mine'] == false ? ' · client' : ''}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
                if ((b['open_suggestions'] ?? 0) != 0)
                  Text('${_s(b['open_suggestions'])} suggestions waiting for your review', style: const TextStyle(fontSize: 12, color: C.accent)),
              ])),
              const Icon(Icons.chevron_right_rounded, color: C.faint),
            ]),
          ),
        ),
      );

  Widget _aaj() {
    final day = _m(_d?['day']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Text(_s(day['say']), style: const TextStyle(fontSize: 14))),
      const SizedBox(height: 12),
      if (_list(_d?['cards']).isNotEmpty) const Caption('WAITING FOR YOUR YES'),
      for (final c in _list(_d?['cards']))
        Padding(padding: const EdgeInsets.only(bottom: 10), child: KitabCardCard(app: widget.app, data: {'card': c}, onDone: _load)),
      if (_strs(day['due']).isNotEmpty) ...[const Caption('DATES'), for (final x in _strs(day['due'])) Text('• $x')],
      if (_strs(day['follow']).isNotEmpty) ...[const SizedBox(height: 8), const Caption('FOLLOW-UP'), for (final x in _strs(day['follow'])) Text('• $x')],
      const SizedBox(height: 16),
      GradientButton(label: 'New book', icon: Icons.add_rounded, onTap: _newBook),
    ]);
  }

  Widget _kitaabein() => ListView(padding: const EdgeInsets.all(16), children: [
        for (final b in _list(_d?['books'])) _bookTile(b),
        if (_list(_d?['books']).isEmpty) const Text('No books yet.', style: TextStyle(color: C.muted)),
        const SizedBox(height: 8),
        GlassButton(label: 'New book', icon: Icons.add_rounded, onTap: _newBook),
      ]);

  Widget _niyam() {
    final st = _m(_d?['settings']);
    final rate = _m(st['rate']);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_s(st['name'])} · ${_s(st['role'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('Rate: ${rate.isEmpty ? 'not set' : '${_s(rate['amount'])} per ${_s(rate['per'])}'}', style: const TextStyle(color: C.muted)),
        Text('GSTIN: ${_s(st['gstin']).isEmpty ? 'none' : _s(st['gstin'])} · UPI: ${_s(st['upi_id'])}', style: const TextStyle(color: C.muted)),
        Text('Follow-up: after ${_s(st['follow_days'])} days · morning note at ${_s(st['morning_time'])}', style: const TextStyle(color: C.muted)),
      ])),
      const SizedBox(height: 10),
      GlassButton(label: 'Badlo', icon: Icons.edit_rounded, onTap: () async {
        final f = await _form(context, 'Niyam', const [
          ('name', 'Your name / pen name'), ('role', 'author | editor | publisher'), ('lang', 'Language: hi | mr | en'),
          ('rate_per', 'Rate per: word | page | hour | flat'), ('rate_amount', 'Rate (Rs)'), ('gstin', 'GSTIN (ho to)'),
          ('sac', 'SAC (from your CA)'), ('upi_id', 'UPI ID'), ('email', 'Email'), ('phone', 'Phone'), ('follow_days', 'Follow up after how many days'),
          ('morning_time', 'Morning note (HH:MM)'), ('rules', 'Your rules'),
        ], initial: {
          'name': _s(st['name']), 'role': _s(st['role']), 'lang': _s(st['lang']), 'rate_per': _s(rate['per']),
          'rate_amount': _s(rate['amount']), 'gstin': _s(st['gstin']), 'sac': _s(st['sac']), 'upi_id': _s(st['upi_id']),
          'email': _s(st['email']), 'phone': _s(st['phone']), 'follow_days': _s(st['follow_days']),
          'morning_time': _s(st['morning_time']), 'rules': _s(st['rules']),
        });
        if (f == null || !mounted) return;
        final body = <String, dynamic>{...f};
        final per = body.remove('rate_per'), amt = body.remove('rate_amount');
        if (amt != null) body['rate'] = {'per': per ?? 'word', 'amount': _n(amt)};
        if (body['follow_days'] != null) body['follow_days'] = int.tryParse(body['follow_days']) ?? 90;
        await _call(context, widget.app, 'PUT', '/api/kitab/settings', body);
        await _load();
      }),
      const SizedBox(height: 14),
      for (final x in _strs(st['notes'])) Padding(padding: const EdgeInsets.only(bottom: 6),
          child: Text(x, style: const TextStyle(fontSize: 12, color: C.faint))),
      const Caption('SOURCES (WITH DATES)'),
      for (final s in (_d?['sources'] as List? ?? const []))
        if (s is List && s.length >= 3)
          Padding(padding: const EdgeInsets.only(bottom: 6),
              child: Text('• ${s[0]} (${s[2]})', style: const TextStyle(fontSize: 11.5, color: C.faint))),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['Aaj', 'Kitaabein', 'Niyam'];
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Kitab Sahayak'),
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
              : RefreshIndicator(onRefresh: _load, child: [_aaj, _kitaabein, _niyam][_tab]()),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- one book
class KitabBookPage extends StatefulWidget {
  const KitabBookPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<KitabBookPage> createState() => _KitabBookPageState();
}

class _KitabBookPageState extends State<KitabBookPage> {
  Map<String, dynamic>? _b;
  Map<String, dynamic>? _perms;
  Map<String, dynamic>? _roy;
  List<Map<String, dynamic>> _subs = [];
  Map<String, dynamic>? _card;
  bool _busy = false;
  String get _base => '/api/kitab/books/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = _m(await widget.app.api!.call('GET', _base));
      final p = _m(await widget.app.api!.call('GET', '$_base/permissions'));
      final s = _m(await widget.app.api!.call('GET', '$_base/submissions'));
      final r = _m(await widget.app.api!.call('GET', '$_base/royalties'));
      if (mounted) setState(() {
        _b = b;
        _perms = p;
        _subs = _list(s['submissions']);
        _roy = r;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    if (r != null && _m(r['card']).isNotEmpty) _card = _m(r['card']);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  Future<void> _import() async {
    final f = await _form(context, 'Add the manuscript', const [('text', 'Full text (chapters are made from Chapter / अध्याय headings)')]);
    if (f == null || f['text'] == null) return;
    await _run('POST', '$_base/import', {'text': f['text']});
  }

  Future<void> _export(String what) async {
    final r = await _run('POST', '$_base/export', {'what': what});
    if (r != null && mounted) _snack(context, '${_s(r['say'])} The file is in the chat.');
  }

  Widget _section(String title, List<Widget> children) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Caption(title), ...children])),
      );

  @override
  Widget build(BuildContext context) {
    final b = _b;
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(b == null ? 'Book' : '${_s(b['number'])} · ${_s(b['title'])}')),
      body: b == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                if (_card != null) Padding(padding: const EdgeInsets.only(bottom: 12),
                    child: KitabCardCard(app: widget.app, data: {'card': _card}, onDone: _load)),
                Text('${_s(b['words'])} shabd · ${_s(b['lang'])} · ${_statusLabel[_s(b['status'])] ?? _s(b['status'])}'
                    '${_s(b['deadline']).isEmpty ? '' : ' · deadline ${_s(b['deadline'])}'}', style: const TextStyle(color: C.muted)),
                const SizedBox(height: 10),
                _section('CHAPTER', [
                  for (final c in _list(b['chapter_list']))
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${_s(c['n'])}. ${_s(c['title'])}'),
                      subtitle: Text('${_s(c['words'])} shabd · ${_s(c['status'])}'),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => Navigator.of(context)
                          .push(MaterialPageRoute(builder: (_) => KitabChapterPage(app: widget.app, id: _s(c['id']))))
                          .then((_) => _load()),
                    ),
                  Wrap(spacing: 8, runSpacing: 6, children: [
                    GlassButton(label: 'Add the manuscript', icon: Icons.upload_file_rounded, height: 40, onTap: _busy ? null : _import),
                    GlassButton(label: 'New chapter', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : () async {
                      final f = await _form(context, 'New chapter', const [('title', 'Naam'), ('text', 'Text')]);
                      if (f != null) await _run('POST', '$_base/chapters', f);
                    }),
                  ]),
                ]),
                _section('STYLE SHEET', [
                  for (final x in _list(_m(b['style'])['characters'])) Text('• ${_s(x['name'])} ${_s(x['note'])}'),
                  for (final e in _m(_m(b['style'])['spellings']).entries) Text('• ${e.key} -> ${e.value}', style: const TextStyle(fontSize: 12.5)),
                  Wrap(spacing: 8, runSpacing: 6, children: [
                    GlassButton(label: 'Add name', height: 40, onTap: () async {
                      final f = await _form(context, 'Paatra / naam', const [('name', 'Name (correct spelling)'), ('note', 'Note')]);
                      if (f != null) await _run('PUT', '$_base/style', {'characters': [f]});
                    }),
                    GlassButton(label: 'Fix the spelling', height: 40, onTap: () async {
                      final f = await _form(context, 'Which spelling is right?', const [('choose', 'The correct word (the rest will be changed to match)')]);
                      if (f != null) await _run('PUT', '$_base/style', f);
                    }),
                    GlassButton(label: 'Full stop: । / .', height: 40, onTap: () async {
                      final f = await _form(context, 'Full stop', const [('full_stop', 'danda (।) or period (.)')]);
                      if (f != null) await _run('PUT', '$_base/style', {'conventions': {'full_stop': f['full_stop']}});
                    }),
                  ]),
                ]),
                _section('PERMISSION (OTHERS\' WORDS)', [
                  Text(_s(_perms?['say']), style: const TextStyle(fontSize: 12.5)),
                  for (final p in _list(_perms?['permissions']))
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${_s(p['number'])} · ${_s(p['kind'])} · "${_s(p['excerpt'])}..."', style: const TextStyle(fontSize: 13)),
                      subtitle: Text('${_s(p['status'])} · ${_s(p['holder'])}'),
                      trailing: PopupMenuButton<String>(
                        onSelected: (v) async {
                          if (v == 'edit') {
                            final f = await _form(context, _s(p['number']), const [
                              ('source', 'Kiski rachna'), ('holder', 'Who holds the rights'), ('contact', 'Email / contact'),
                              ('death_year', 'Year of the author\'s death (for public domain)'), ('credit', 'Credit line'),
                              ('status', 'needed | asked | granted | refused | fair_dealing | public_domain | own | removed'),
                            ], initial: {'source': _s(p['source']), 'holder': _s(p['holder']), 'contact': _s(p['contact']),
                              'credit': _s(p['credit']), 'status': _s(p['status'])});
                            if (f == null) return;
                            final body = <String, dynamic>{...f, 'permission': p['number']};
                            if (body['death_year'] != null) body['death_year'] = int.tryParse(body['death_year']);
                            await _run('POST', '$_base/permissions', body);
                          } else {
                            await _run('POST', '$_base/permissions/${_s(p['number'])}/request');
                          }
                        },
                        itemBuilder: (_) => const [
                          PopupMenuItem(value: 'edit', child: Text('Write / change')),
                          PopupMenuItem(value: 'ask', child: Text('Permission letter')),
                        ],
                      ),
                    ),
                  GlassButton(label: 'Search the manuscript', icon: Icons.search_rounded, height: 40,
                      onTap: _busy ? null : () => _run('POST', '$_base/permissions/scan')),
                ]),
                _section('ISBN AUR CHECKLIST', [
                  for (final e in _m(b['isbns']).entries) Text('${e.key}: ${e.value}'),
                  for (final it in _list(b['checklist']))
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      dense: true,
                      value: _s(it['status']) == 'done',
                      title: Text(_s(it['label']), style: const TextStyle(fontSize: 12.5)),
                      subtitle: Text([_s(it['due']).isEmpty ? '' : 'by: ${_s(it['due'])}', _s(it['note']), _s(it['ref'])]
                          .where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(fontSize: 11)),
                      onChanged: (v) => _run('POST', '$_base/checklist', {'item': it['key'], 'status': v == true ? 'done' : 'todo'}),
                    ),
                  Wrap(spacing: 8, runSpacing: 6, children: [
                    GlassButton(label: 'Add ISBN', height: 40, onTap: () async {
                      final f = await _form(context, 'ISBN (isbn.gov.in se)', const [('format', 'paperback | hardback | ebook | audiobook'), ('isbn', 'ISBN')]);
                      if (f != null) await _run('POST', '$_base/isbn', f);
                    }),
                    GlassButton(label: 'Verso page', height: 40, onTap: () async {
                      final r = await _call(context, widget.app, 'GET', '$_base/verso');
                      if (r == null || !mounted) return;
                      showDialog(context: context, builder: (d) => AlertDialog(
                            title: const Text('Copyright / verso page'),
                            content: SingleChildScrollView(child: SelectableText(_strs(r['lines']).join('\n\n'))),
                            actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Theek'))]));
                    }),
                  ]),
                ]),
                _section('PUBLISHER / AGENT', [
                  for (final x in _subs)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${_s(x['number'])} · ${_s(x['to'])}${x['exclusive'] == true ? ' (exclusive)' : ''}'),
                      subtitle: Text('${_s(x['status'])}${_s(x['follow_on']).isEmpty ? '' : ' · follow-up ${_s(x['follow_on'])}'}'),
                      trailing: _s(x['status']) == 'draft'
                          ? TextButton(onPressed: _busy ? null : () async {
                              final r = await _run('POST', '$_base/submissions/${_s(x['number'])}/pitch', {});
                              if (r != null && _s(r['status']) == 'blanks' && mounted) {
                                final p = _m(r['pitch']);
                                final f = await _form(context, 'Pitch (fill the [blank])', const [('subject', 'Subject'), ('letter', 'Letter'), ('synopsis', 'Synopsis')],
                                    initial: {'subject': _s(p['subject']), 'letter': _s(p['letter']), 'synopsis': _s(p['synopsis'])}, ok: 'Save');
                                if (f != null) await _run('POST', '$_base/submissions/${_s(x['number'])}/pitch', f);
                              }
                            }, child: const Text('Pitch'))
                          : null,
                    ),
                  GlassButton(label: 'New place', icon: Icons.send_rounded, height: 40, onTap: () async {
                    final f = await _form(context, 'Where to send', const [
                      ('to', 'Publisher / agent'), ('email', 'Email'), ('guidelines', 'Their guidelines (paste)'), ('exclusive', 'Do they ask for exclusive? yes / no'),
                    ]);
                    if (f == null) return;
                    final body = <String, dynamic>{...f, 'exclusive': (f['exclusive'] ?? '').toLowerCase().startsWith('h')};
                    await _run('POST', '$_base/submissions', body);
                  }),
                ]),
                _section('ROYALTY', [
                  Text(_s(_roy?['say'])),
                  for (final r in _list(_roy?['statements']))
                    Text('${_s(r['period'])} ${_s(r['format'])}: ${_s(r['units'])} copies · due ${_s(r['expected'])} · statement ${_s(r['stated'])}'
                        '${r['diff'] != null && (r['diff'] as num).abs() >= 1 ? ' · farq ${_s(r['diff'])}' : ''}', style: const TextStyle(fontSize: 12.5)),
                  GlassButton(label: 'Add statement', height: 40, onTap: () async {
                    final f = await _form(context, 'Royalty statement', const [
                      ('period', 'Avadhi (Apr-Sep 2026)'), ('period_end', 'Ant tareekh (YYYY-MM-DD)'), ('format', 'paperback | ebook ...'),
                      ('units', 'Copies sold'), ('returns', 'Returned'), ('price', 'MRP'), ('stated', 'Royalty in the statement'), ('tds', 'TDS deducted'),
                    ]);
                    if (f == null) return;
                    final body = <String, dynamic>{...f};
                    for (final k in ['units', 'returns', 'price', 'stated', 'tds']) {
                      if (body[k] != null) body[k] = _n(body[k]);
                    }
                    await _run('POST', '$_base/statements', body);
                  }),
                ]),
                if (b['mine'] == false)
                  _section('CLIENT', [
                    Text(_s(_m(b['client'])['name'])),
                    Wrap(spacing: 8, runSpacing: 6, children: [
                      GlassButton(label: 'Invoice card', icon: Icons.receipt_long_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/invoice', {})),
                      GlassButton(label: 'Send the edited file', icon: Icons.outbox_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '$_base/deliver')),
                    ]),
                  ]),
                _section('FILES', [
                  Wrap(spacing: 8, runSpacing: 6, children: [
                    GlassButton(label: 'Word', height: 40, onTap: () => _export('docx')),
                    GlassButton(label: 'Word + Track Changes', height: 40, onTap: () => _export('tracked')),
                    GlassButton(label: 'PDF', height: 40, onTap: () => _export('pdf')),
                    GlassButton(label: 'Style sheet', height: 40, onTap: () => _export('style')),
                    GlassButton(label: 'Register (Excel)', height: 40, onTap: () => _export('register')),
                  ]),
                ]),
              ]),
            ),
    );
  }
}

// ---------------------------------------------------------------- one chapter: her text + tracked suggestions
class KitabChapterPage extends StatefulWidget {
  const KitabChapterPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<KitabChapterPage> createState() => _KitabChapterPageState();
}

class _KitabChapterPageState extends State<KitabChapterPage> {
  Map<String, dynamic>? _c;
  final Set<String> _picked = {};
  bool _busy = false;
  String get _base => '/api/kitab/chapters/${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = _m(await widget.app.api!.call('GET', _base));
      if (mounted) setState(() {
        _c = c;
        _picked.removeWhere((id) => !_list(c['suggestions']).any((s) => _s(s['id']) == id));
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _decide(bool yes, {bool remember = false}) async {
    if (_picked.isEmpty) return;
    await _run('POST', '$_base/suggestions/decide',
        {'ids': _picked.toList(), 'yes': yes, 'hash': _s(_c?['hash']), 'remember': remember});
    _picked.clear();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    final sugs = _list(c?['suggestions']);
    final changes = sugs.where((s) => s['query'] != true).toList();
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(c == null ? 'Chapter' : '${_s(c['n'])}. ${_s(c['title'])}'), actions: [
        IconButton(icon: const Icon(Icons.edit_note_rounded), tooltip: 'Write it myself', onPressed: c == null ? null : () async {
          final f = await _form(context, 'Your text', const [('text', 'Text')], initial: {'text': _s(c['text'])}, ok: 'Save');
          if (f != null) await _run('PUT', _base, {'text': f['text'] ?? ''});
        }),
      ]),
      body: c == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                Text('${_s(c['words'])} shabd · ausat vakya ${_s(_m(c['stats'])['avg_sentence'])} shabd', style: const TextStyle(color: C.muted)),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 6, children: [
                  for (final e in _passLabel.entries)
                    GlassButton(label: e.value, height: 38, onTap: _busy ? null : () => _run('POST', '$_base/pass', {'pass': e.key})),
                  GlassButton(label: 'Translation', icon: Icons.translate_rounded, height: 38, onTap: _busy ? null : () async {
                    final f = await _form(context, 'In which language?', const [('to', 'Hindi / Marathi / English ...')]);
                    if (f != null) await _run('POST', '$_base/translate', f);
                  }),
                ]),
                const SizedBox(height: 10),
                if (_s(c['letter']).isNotEmpty)
                  Glass(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Caption("EDITOR\'S LETTER (OPINION ONLY, TEXT NOT CHANGED)"),
                    Text(_s(c['letter']), style: const TextStyle(fontSize: 13)),
                  ])),
                const SizedBox(height: 10),
                if (sugs.isNotEmpty) ...[
                  Caption('SUGGESTIONS (${sugs.length}) · YOUR TEXT CHANGES ONLY WHEN YOU ACCEPT'),
                  Row(children: [
                    TextButton(onPressed: () => setState(() => _picked
                      ..clear()
                      ..addAll(changes.map((s) => _s(s['id'])))), child: const Text('Choose all changes')),
                    TextButton(onPressed: () => setState(_picked.clear), child: const Text('None')),
                  ]),
                  for (final s in sugs)
                    Glass(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Checkbox(value: _picked.contains(_s(s['id'])), onChanged: (v) => setState(() {
                              if (v == true) {
                                _picked.add(_s(s['id']));
                              } else {
                                _picked.remove(_s(s['id']));
                              }
                            })),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${_s(s['number'])} · ${_passLabel[_s(s['pass'])] ?? _s(s['pass'])} · ${_s(s['kind'])}',
                              style: const TextStyle(fontSize: 11.5, color: C.faint)),
                          if (s['query'] == true)
                            Text('“${_s(s['from'])}”', style: const TextStyle(fontStyle: FontStyle.italic))
                          else
                            RichText(text: TextSpan(style: const TextStyle(color: C.ink, fontSize: 14), children: [
                              TextSpan(text: _s(s['from']).replaceAll(' ', '·'),
                                  style: const TextStyle(decoration: TextDecoration.lineThrough, color: C.bad)),
                              const TextSpan(text: '  →  '),
                              TextSpan(text: _s(s['to']).isEmpty ? '(remove)' : _s(s['to']).replaceAll(' ', '·'),
                                  style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700)),
                            ])),
                          Text(_s(s['why']), style: const TextStyle(fontSize: 12, color: C.muted)),
                        ])),
                      ]),
                    ),
                  Wrap(spacing: 8, runSpacing: 6, children: [
                    GradientButton(label: 'Accept chosen (${_picked.length})', height: 44, onTap: _busy || _picked.isEmpty ? null : () => _decide(true)),
                    GlassButton(label: 'Hatao', height: 44, onTap: _busy || _picked.isEmpty ? null : () => _decide(false)),
                    GlassButton(label: 'Remove + do not show again', height: 44,
                        onTap: _busy || _picked.isEmpty ? null : () => _decide(false, remember: true)),
                  ]),
                  const SizedBox(height: 12),
                ],
                const Caption('YOUR TEXT'),
                Glass(child: SelectableText(_s(c['text']), style: const TextStyle(fontSize: 14, height: 1.5))),
                const SizedBox(height: 10),
                for (final (i, v) in _list(c['versions']).indexed)
                  Text('Version ${i + 1}: ${_s(v['why'])} (${_s(v['words'])} shabd)', style: const TextStyle(fontSize: 11.5, color: C.faint)),
              ]),
            ),
    );
  }
}

// ---------------------------------------------------------------- chat / call cards
/// kitab_card: accept batch / permission letter / pitch / invoice / client delivery. Only her tap decides.
class KitabCardCard extends StatefulWidget {
  const KitabCardCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<KitabCardCard> createState() => _KitabCardCardState();
}

class _KitabCardCardState extends State<KitabCardCard> {
  bool _busy = false;
  late Map<String, dynamic> _c = _m(widget.data['card']);
  late Map<String, dynamic> _draft = _m(_m(_c['result'])['draft']);

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
      final m = _m(await widget.app.api!.call('POST', '/api/kitab/cards/$id/decide', body: {'yes': yes, 'hash': _s(_c['hash']), 'reason': reason}));
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
    return Glass(
      border: st == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(switch (kind) {
            'accept' => Icons.spellcheck_rounded, 'permission' => Icons.gavel_rounded, 'submission' => Icons.send_rounded,
            'invoice' => Icons.receipt_long_rounded, _ => Icons.outbox_rounded,
          }, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(c['title'])} · ${_s(sh['book'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(switch (st) { 'waiting' => 'your yes?', 'approved' => 'yes', 'rejected' => 'no', 'stale' => 'old', _ => st },
              fg: st == 'waiting' ? C.accent : C.chip),
        ]),
        Text(_s(sh['title']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (kind == 'accept') ...[
          Text('Chapter ${_s(sh['chapter'])}: ${_s(sh['count'])} changes will be applied to your text', style: const TextStyle(fontSize: 13)),
          for (final it in _list(sh['items']).take(8))
            Text('• "${_s(it['from'])}" → "${_s(it['to'])}"  (${_s(it['why'])})', style: const TextStyle(fontSize: 12)),
        ],
        if (kind == 'permission') ...[
          Text('${_s(sh['number'])} · ${_s(sh['holder'])}', style: const TextStyle(fontSize: 13)),
          Text(_s(sh['letter']), maxLines: 6, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
        ],
        if (kind == 'submission') ...[
          Text('${_s(sh['to'])} · ${_s(sh['email'])}', style: const TextStyle(fontSize: 13)),
          Text(_s(sh['subject']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
          Text(_s(sh['letter']), maxLines: 8, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
          for (final w in _strs(sh['warnings'])) Text('⚠ $w', style: const TextStyle(fontSize: 12, color: C.warn)),
        ],
        if (kind == 'invoice') ...[
          Text('${_s(sh['client'])} · ${_s(sh['line'])}', style: const TextStyle(fontSize: 12.5)),
          Text(_s(sh['total_text']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text(_s(sh['tds_note']), style: const TextStyle(fontSize: 11, color: C.faint)),
        ],
        if (kind == 'deliver')
          Text('${_s(sh['client'])} · ${_s(sh['chapters'])} chapters · ${_s(sh['open_suggestions'])} suggestions in Track Changes',
              style: const TextStyle(fontSize: 12.5)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Wrap(spacing: 8, runSpacing: 6, children: [
            GradientButton(label: 'Yes', height: 42, onTap: _busy ? null : () => _decide(true)),
            GlassButton(label: 'No', height: 42, onTap: _busy ? null : () => _decide(false)),
          ]),
        if (_draft.isNotEmpty) ...[const SizedBox(height: 6), _draftButtons(_draft)],
        const Text('Hoola sends nothing by itself and does not pay or receive money: sending is in your hands.',
            style: TextStyle(fontSize: 11, color: C.faint)),
      ]),
    );
  }
}

/// kitab_alert / kitab_day / kitab_update: notes (follow-up, legal deposit, deadline, statement late, morning note, progress).
class KitabNoteCard extends StatelessWidget {
  const KitabNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    return Glass(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.menu_book_rounded, color: C.accent),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (_s(data['book']).isNotEmpty) Text(_s(data['book']), style: const TextStyle(fontWeight: FontWeight.w800)),
          Text(_s(data['say']), style: const TextStyle(fontSize: 13.5)),
        ])),
        IconButton(icon: const Icon(Icons.open_in_new_rounded, size: 18), onPressed: () =>
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => KitabScreen(app: app)))),
      ]),
    );
  }
}
