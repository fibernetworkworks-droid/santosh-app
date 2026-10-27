/// Profile > Legal researcher: Hoola finds statutes / judgments from sources it actually READS (India Code, Supreme Court /
/// High Courts / eCourts, gazette, regulators; Indian Kanoon's official API with her key; her own files) and writes a memo where
/// every point has [n] + the exact quote. Not found = "nahi mila"; an invented section / case = "[citation chahiye]".
/// Tabs: Matter · Saved · Purana -> naya kanoon · Niyam. A memo goes outside ONLY by her tap on the share card.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _disclaimer = 'Draft research / jaankari, legal advice nahi. Har citation us source se hai jo Hoola ne padha; vakil se pakka karwaiye.';

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields, {String ok = 'Aage'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], minLines: 1, maxLines: k == 'question' || k == 'text' ? 4 : 1, decoration: InputDecoration(labelText: label)),
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

Future<void> _open(BuildContext context, String url) async {
  if (url.isEmpty) return;
  final r = await Native.openExternal(url: url);
  if (r.isNotEmpty && r != 'ok' && context.mounted) _snack(context, r);
}

class LegalresScreen extends StatefulWidget {
  const LegalresScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<LegalresScreen> createState() => _LegalresScreenState();
}

class _LegalresScreenState extends State<LegalresScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _saved = const [];
  List<Map<String, dynamic>> _rows = const [];
  int _tab = 0;
  bool _busy = false;
  final _mapText = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _mapText.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = _map(await widget.app.api!.call('GET', '/api/legalres'));
      final a = _map(await widget.app.api!.call('GET', '/api/legalres/authorities'));
      if (mounted) setState(() {
        _d = d;
        _saved = _list(a['authorities']);
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _ask() async {
    final f = await _form(context, 'Kanoon ka sawaal', const [
      ('question', 'Sawaal (jaise: IPC 420 ab kya hai, cheating kab banta hai?)'),
      ('client', 'Kiska matter (aapke liye label, optional)'),
      ('url', 'Koi official link padhna ho (optional)'),
    ], ok: 'Research karo');
    if (f == null || _s(f['question']).isEmpty) return;
    final r = await _run(() => widget.app.api!.call('POST', '/api/legalres/research',
        body: {'question': f['question'], if (f['client'] != null) 'client': f['client'], if (f['url'] != null) 'urls': [f['url']]},
        timeout: const Duration(minutes: 3)));
    final m = _map(r?['matter']);
    if (m['number'] != null && mounted) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => LegalresMatterPage(app: widget.app, ref: _s(m['number']))));
      _load();
    }
  }

  Widget _matters() {
    final d = _d ?? const {};
    final ms = _list(d['matters']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      GradientButton(label: 'Naya sawaal', icon: Icons.search_rounded, height: 48, onTap: _busy ? null : _ask),
      const SizedBox(height: 10),
      if (ms.isEmpty) const Text('Abhi koi matter nahi.', style: TextStyle(color: C.muted)),
      for (final m in ms)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () async {
              await Navigator.of(context).push(MaterialPageRoute(builder: (_) => LegalresMatterPage(app: widget.app, ref: _s(m['number']))));
              _load();
            },
            child: Glass(
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${_s(m['number'])} · ${_s(m['title'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    if (_s(m['client']).isNotEmpty) Text(_s(m['client']), style: const TextStyle(color: C.muted, fontSize: 12)),
                    if (m['last'] != null)
                      Text(_s(_map(m['last'])['short']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
                  ]),
                ),
                Pill(_s(m['status']) == 'closed' ? 'BAND' : 'KHULA', fg: _s(m['status']) == 'closed' ? C.muted : C.ok),
              ]),
            ),
          ),
        ),
    ]);
  }

  Widget _savedTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Caption('Saved authorities (act / judgment)'),
        if (_saved.isEmpty) const Text('Matter ke source par "Save" dabaiye.', style: TextStyle(color: C.muted)),
        for (final a in _saved)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(a['title']), style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('${_s(a['matter'])} · ${_s(a['kind'])}${a['official'] == true ? ' · official' : ''}', style: const TextStyle(color: C.muted, fontSize: 12)),
                if (_s(a['note']).isNotEmpty) Text(_s(a['note']), style: const TextStyle(fontSize: 12.5)),
                if (_s(a['excerpt']).isNotEmpty) Text('"${_s(a['excerpt'])}"', maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
                if (_s(a['url']).isNotEmpty) TextButton(onPressed: () => _open(context, _s(a['url'])), child: const Text('Source kholo')),
              ]),
            ),
          ),
      ]);

  Future<void> _lookup() async {
    final t = _mapText.text.trim();
    try {
      final r = _map(await widget.app.api!.call('GET', '/api/legalres/mapping', query: t.isEmpty ? {'act': 'IPC'} : {'text': t}));
      if (mounted) setState(() => _rows = _list(r['rows']));
      if (mounted && _list(r['rows']).isEmpty) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _mappingTab() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('IPC -> BNS, CrPC -> BNSS, Evidence Act -> BSA (1 July 2024 se). "andaaza" wali row India Code par pakka kijiye.',
            style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        TextField(controller: _mapText, decoration: const InputDecoration(labelText: 'Jaise: IPC 420, CrPC 438, Evidence 65B (khaali = poori IPC list)')),
        const SizedBox(height: 8),
        GlassButton(label: 'Dekho', icon: Icons.swap_horiz_rounded, onTap: _lookup),
        const SizedBox(height: 8),
        LegalresMappingTable(rows: _rows),
      ]);

  Widget _niyam() {
    final st = _map(_d?['settings']);
    final joined = st['ik_joined'] == true;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Indian Kanoon (official paid API)', style: TextStyle(fontWeight: FontWeight.w800)),
          Text(joined ? 'Judi: ${_s(st['ik_label'])}${st['ik_ok'] == true ? ' · chal rahi hai' : ''}' : 'Nahi judi (judgments sirf official sites / aapke links se)',
              style: const TextStyle(fontSize: 12.5)),
          Text('Aaj ka kharcha: Rs ${_s(st['ik_today_rs'])} / Rs ${_s(st['ik_day_rs'])} (search 0.50, document 0.20 aapke prepaid balance se)',
              style: const TextStyle(color: C.muted, fontSize: 12)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(
                label: joined ? 'Key badlo' : 'Key jodo',
                icon: Icons.key_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final c = TextEditingController();
                        final ok = await showDialog<bool>(
                          context: context,
                          builder: (d) => AlertDialog(
                            title: const Text('Indian Kanoon API token'),
                            content: Column(mainAxisSize: MainAxisSize.min, children: [
                              TextField(controller: c, obscureText: true, decoration: const InputDecoration(labelText: 'Token (api.indiankanoon.org)')),
                              const SizedBox(height: 6),
                              const Text('Sirf yahan daaliye, chat mein kabhi nahi. Server par sealed rehta hai.', style: TextStyle(fontSize: 12)),
                            ]),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
                              TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Jodo')),
                            ],
                          ),
                        );
                        if (ok == true && c.text.trim().isNotEmpty) {
                          await _run(() => widget.app.api!.call('PUT', '/api/legalres/key', body: {'token': c.text.trim()}));
                        }
                        c.dispose();
                      }),
            if (joined) GlassButton(label: 'Key hatao', icon: Icons.link_off_rounded, onTap: _busy ? null : () => _run(() => widget.app.api!.call('DELETE', '/api/legalres/key'))),
            GlassButton(
                label: 'Roz ki limit',
                icon: Icons.currency_rupee_rounded,
                onTap: _busy
                    ? null
                    : () async {
                        final f = await _form(context, 'Indian Kanoon roz ki limit (Rs)', const [('ik_day_rs', 'Rupaye')]);
                        final v = double.tryParse(_s(f?['ik_day_rs']));
                        if (v != null) await _run(() => widget.app.api!.call('PUT', '/api/legalres/settings', body: {'ik_day_rs': v}));
                      }),
          ]),
        ]),
      ),
      const SizedBox(height: 8),
      Glass(
        child: Column(children: [
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Official sites dhoondho (India Code, courts, gov.in)'),
              value: st['use_web'] != false,
              onChanged: _busy ? null : (v) => _run(() => widget.app.api!.call('PUT', '/api/legalres/settings', body: {'use_web': v}))),
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Meri files (Gyaan) bhi dekho'),
              value: st['use_files'] != false,
              onChanged: _busy ? null : (v) => _run(() => widget.app.api!.call('PUT', '/api/legalres/settings', body: {'use_files': v}))),
        ]),
      ),
      const SizedBox(height: 8),
      for (final n in (_d?['never'] as List? ?? const [])) Text('• ${_s(n)}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Legal researcher')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Matter'), (1, 'Saved'), (2, 'Purana -> naya'), (3, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_matters(), _savedTab(), _mappingTab(), _niyam()][_tab],
              const SizedBox(height: 14),
              const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// Old -> new criminal law rows with their own pakka / andaaza label.
class LegalresMappingTable extends StatelessWidget {
  const LegalresMappingTable({super.key, required this.rows});
  final List<Map<String, dynamic>> rows;
  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      for (final r in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(
              width: 150,
              child: Text('${_s(r['old_act'])} ${_s(r['old'])} → ${_s(r['new_act'])} ${_s(r['new']).isEmpty ? '-' : _s(r['new'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
            ),
            Expanded(child: Text(_s(r['subject']), style: const TextStyle(fontSize: 12.5))),
            const SizedBox(width: 6),
            Pill(r['sure'] == true ? 'PAKKA' : 'ANDAAZA', fg: r['sure'] == true ? C.ok : C.warn),
          ]),
        ),
    ]);
  }
}

/// Points with [n] + the exact quote, then the sources that were really read.
class LegalresMemoView extends StatelessWidget {
  const LegalresMemoView({super.key, required this.memo, this.onSave});
  final Map<String, dynamic> memo;
  final void Function(int n)? onSave;
  @override
  Widget build(BuildContext context) {
    final found = _s(memo['status']) == 'found';
    final srcs = _list(memo['sources']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Pill(found ? 'SOURCE SE' : 'NAHI MILA', fg: found ? C.ok : C.warn),
        const SizedBox(width: 6),
        if (memo['v'] != null) Text('v${_s(memo['v'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
      ]),
      const SizedBox(height: 6),
      Text(_s(memo['short']), style: const TextStyle(fontWeight: FontWeight.w700, height: 1.35)),
      for (final (i, p) in _list(memo['points']).indexed) ...[
        const SizedBox(height: 8),
        Text('${i + 1}. ${_s(p['text'])} ${(p['sources'] as List? ?? const []).map((n) => '[$n]').join(' ')}', style: const TextStyle(fontSize: 13)),
        Container(
          margin: const EdgeInsets.only(top: 4),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(10)),
          child: Text('[${_s(p['quote_from'])}] "${_s(p['quote'])}"', style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: C.muted)),
        ),
      ],
      if (_list(memo['mapping']).isNotEmpty) ...[
        const SizedBox(height: 10),
        const Caption('Purana -> naya kanoon'),
        LegalresMappingTable(rows: _list(memo['mapping'])),
      ],
      for (final g in (memo['gaps'] as List? ?? const [])) Text('• Nahi mila: ${_s(g)}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      for (final f in (memo['flags'] as List? ?? const [])) Text('• Hataya: ${_s(f)}', style: const TextStyle(fontSize: 12, color: C.bad)),
      if (srcs.isNotEmpty) ...[
        const SizedBox(height: 10),
        const Caption('Sources (jo sach mein padhe)'),
        for (final x in srcs)
          Row(children: [
            Expanded(
              child: Text('[${_s(x['n'])}] ${_s(x['title'])}${x['official'] == true ? ' · official' : _s(x['via']) == 'ikanoon' ? ' · Indian Kanoon' : _s(x['via']) == 'gyaan' ? ' · aapki file' : ''}',
                  style: const TextStyle(fontSize: 12.5)),
            ),
            if (_s(x['url']).isNotEmpty) IconButton(icon: const Icon(Icons.open_in_new_rounded, size: 18), onPressed: () => _open(context, _s(x['url']))),
            if (onSave != null) IconButton(icon: const Icon(Icons.bookmark_add_rounded, size: 18), tooltip: 'Save', onPressed: () => onSave!(int.tryParse(_s(x['n'])) ?? 0)),
          ]),
      ],
      if (_s(memo['attribution']).isNotEmpty) Text(_s(memo['attribution']), style: const TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }
}

class LegalresMatterPage extends StatefulWidget {
  const LegalresMatterPage({super.key, required this.app, required this.ref});
  final Santosh app;
  final String ref;
  @override
  State<LegalresMatterPage> createState() => _LegalresMatterPageState();
}

class _LegalresMatterPageState extends State<LegalresMatterPage> {
  Map<String, dynamic>? _m;
  bool _busy = false;
  bool _showLog = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _path => '/api/legalres/matters/${Uri.encodeComponent(widget.ref)}';

  Future<void> _load() async {
    try {
      final m = _map(await widget.app.api!.call('GET', _path));
      if (mounted) setState(() => _m = m);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _share() async {
    final f = await _form(context, 'Memo bhejna (aapki haan ka card)', const [
      ('to_name', 'Kisko (naam)'),
      ('to_contact', 'Mobile ya email'),
      ('via', 'whatsapp / email / file'),
    ]);
    if (f == null || _s(f['to_name']).isEmpty) return;
    final r = await _run(() => widget.app.api!.call('POST', '$_path/share', body: f));
    final sh = _map(r?['share']);
    if (sh['id'] != null && mounted) {
      await showDialog<void>(context: context, builder: (_) => AlertDialog(content: LegalresShareCard(app: widget.app, data: {'share': sh, 'say': r?['say']})));
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = _m;
    final memo = _map(m?['memo']);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(m == null ? widget.ref : '${_s(m['number'])} · ${_s(m['title'])}')),
      body: Aurora(
        child: m == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                if (memo.isNotEmpty)
                  Glass(child: LegalresMemoView(memo: memo, onSave: (n) => _run(() => widget.app.api!.call('POST', '$_path/sources/$n/save', body: {})))),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  GlassButton(
                      label: 'Aur poochho',
                      icon: Icons.search_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Isi matter mein sawaal', const [('question', 'Sawaal'), ('url', 'Official link (optional)')]);
                              if (f != null && _s(f['question']).isNotEmpty) {
                                await _run(() => widget.app.api!.call('POST', '/api/legalres/research',
                                    body: {'question': f['question'], 'matter': m['number'], if (f['url'] != null) 'urls': [f['url']]},
                                    timeout: const Duration(minutes: 3)));
                              }
                            }),
                  GlassButton(
                      label: 'Link padho',
                      icon: Icons.link_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Judgment / act ka link', const [('url', 'https://...')]);
                              if (f?['url'] != null) await _run(() => widget.app.api!.call('POST', '$_path/link', body: {'url': f!['url']}));
                            }),
                  GlassButton(
                      label: 'Note',
                      icon: Icons.edit_note_rounded,
                      onTap: _busy
                          ? null
                          : () async {
                              final f = await _form(context, 'Research log note', const [('text', 'Note')]);
                              if (f?['text'] != null) await _run(() => widget.app.api!.call('POST', '$_path/note', body: {'text': f!['text']}));
                            }),
                  if (memo.isNotEmpty) GlassButton(label: 'Word memo', icon: Icons.description_rounded, onTap: _busy ? null : () => _run(() => widget.app.api!.call('POST', '$_path/memo/file', body: {}))),
                  if (_s(memo['status']) == 'found') GlassButton(label: 'Bhejna hai', icon: Icons.send_rounded, onTap: _busy ? null : _share),
                  if (_s(m['status']) == 'open')
                    GlassButton(label: 'Band karo', icon: Icons.lock_rounded, onTap: _busy ? null : () => _run(() => widget.app.api!.call('PATCH', _path, body: {'status': 'closed'})))
                  else ...[
                    GlassButton(label: 'Phir kholo', icon: Icons.lock_open_rounded, onTap: _busy ? null : () => _run(() => widget.app.api!.call('PATCH', _path, body: {'status': 'open'}))),
                    GlassButton(
                        label: 'Sab mitao',
                        icon: Icons.delete_forever_rounded,
                        color: C.bad,
                        onTap: _busy
                            ? null
                            : () async {
                                final ok = await showDialog<bool>(
                                  context: context,
                                  builder: (d) => AlertDialog(
                                    content: const Text('Is matter ka sawaal, memo, sources aur log hamesha ke liye mit jaayenge.'),
                                    actions: [
                                      TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                                      TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, mitao')),
                                    ],
                                  ),
                                );
                                if (ok == true) {
                                  final r = await _run(() => widget.app.api!.call('POST', '$_path/forget'));
                                  if (r != null && context.mounted) Navigator.of(context).pop();
                                }
                              }),
                  ],
                ]),
                const SizedBox(height: 12),
                const Caption('Saare sources'),
                for (final x in _list(m['sources']))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Glass(
                      padding: const EdgeInsets.all(10),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('[${_s(x['n'])}] ${_s(x['title'])}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                        Text('${_s(x['kind'])} · ${x['official'] == true ? 'official' : _s(x['via'])}${x['saved'] == true ? ' · saved' : ''}',
                            style: const TextStyle(color: C.muted, fontSize: 11.5)),
                        if (_s(x['url']).isNotEmpty)
                          Row(children: [
                            TextButton(onPressed: () => _open(context, _s(x['url'])), child: const Text('Kholo')),
                            TextButton(
                                onPressed: () {
                                  Clipboard.setData(ClipboardData(text: _s(x['url'])));
                                  _snack(context, 'Link copy');
                                },
                                child: const Text('Link copy')),
                          ]),
                      ]),
                    ),
                  ),
                const SizedBox(height: 8),
                for (final sh in _list(m['shares']))
                  Text('${_s(sh['number'])}: ${_s(sh['to_name'])} · ${_s(sh['status'])}', style: const TextStyle(fontSize: 12.5)),
                TextButton(onPressed: () => setState(() => _showLog = !_showLog), child: Text(_showLog ? 'Log chhupao' : 'Research log (Rs ${_s(m['spent_rs'])})')),
                if (_showLog)
                  for (final l in _list(m['log']))
                    Text('${_s(l['at']).length >= 16 ? _s(l['at']).substring(0, 16).replaceFirst('T', ' ') : _s(l['at'])} · ${_s(l['kind'])}: ${_s(l['text'])}',
                        style: const TextStyle(fontSize: 11.5, color: C.muted)),
                const SizedBox(height: 12),
                const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11.5)),
              ]),
      ),
    );
  }
}

/// Chat / call card for `legalres_memo`.
class LegalresMemoCard extends StatelessWidget {
  const LegalresMemoCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final m = _map(data['matter']);
    final memo = _map(data['memo']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.gavel_rounded, size: 18, color: C.accent),
          const SizedBox(width: 6),
          Expanded(child: Text('Research memo ${_s(m['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        LegalresMemoView(memo: memo),
        const SizedBox(height: 6),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LegalresMatterPage(app: app, ref: _s(m['number'])))),
              child: const Text('Poora matter')),
        ),
        const Text(_disclaimer, style: TextStyle(color: C.faint, fontSize: 11)),
      ]),
    );
  }
}

/// Chat / call card for `legalres_share`: the memo goes outside ONLY on this tap (hash of the exact memo + recipient).
class LegalresShareCard extends StatefulWidget {
  const LegalresShareCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<LegalresShareCard> createState() => _LegalresShareCardState();
}

class _LegalresShareCardState extends State<LegalresShareCard> {
  Map<String, dynamic>? _done;
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    final sh = _map(widget.data['share']);
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/legalres/shares/${sh['id']}/decide', body: {'yes': yes, 'hash': sh['hash']}));
      if (mounted) setState(() => _done = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final src = _done ?? widget.data;
    final sh = _map(src['share']);
    final links = _map(src['links']);
    final waiting = _s(sh['status']) == 'waiting';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.outbox_rounded, size: 18, color: C.accent),
          const SizedBox(width: 6),
          Expanded(child: Text('${_s(sh['number'])}: memo v${_s(sh['memo_v'])} → ${_s(sh['to_name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(sh['status']).toUpperCase(), fg: waiting ? C.warn : (_s(sh['status']) == 'shared' ? C.ok : C.muted)),
        ]),
        if (_s(src['short']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(src['short']), maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5))),
        if (_s(src['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(src['say']), style: const TextStyle(fontSize: 12.5, color: C.muted))),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, taiyaar karo', height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Mana', onTap: _busy ? null : () => _decide(false)),
          ]),
        for (final e in links.entries)
          TextButton.icon(
              onPressed: () => _open(context, _s(e.value)),
              icon: Icon(e.key == 'email' ? Icons.mail_rounded : Icons.chat_rounded, size: 18),
              label: Text(e.key == 'email' ? 'Email draft kholo' : 'WhatsApp draft kholo (file khud lagaiye)')),
      ]),
    );
  }
}
