/// Profile > School office (Shiksha suite Phase 3, Daftar Sahayak): Hazri (tap the absent children, save, guardian
/// alerts card) · Marks (Hoola's marks wait UNSIGNED for the teacher's sign-off) · Timetable · Report card.
/// Guardians get alerts / report cards ONLY by her tap on the card, as drafts she sends herself.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

class DaftarScreen extends StatefulWidget {
  const DaftarScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DaftarScreen> createState() => _DaftarScreenState();
}

class _DaftarScreenState extends State<DaftarScreen> {
  int _tab = 0;
  bool _busy = false;
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _classes = const [];
  String _class = '';
  List<Map<String, dynamic>> _roster = const [];
  final Set<String> _absent = {};
  List<Map<String, dynamic>> _unsigned = const [];
  final Set<String> _pick = {};
  Map<String, dynamic>? _tt;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<dynamic> _api(String method, String path, {Object? body, Map<String, String>? query}) =>
      widget.app.api!.call(method, path, body: body, query: query, timeout: const Duration(minutes: 2));

  Future<void> _load() async {
    try {
      final d = _map(await _api('GET', '/api/daftar'));
      final c = _map(await _api('GET', '/api/shiksha/classes'));
      final u = _map(await _api('GET', '/api/daftar/unsigned'));
      final t = _map(await _api('GET', '/api/daftar/timetables'));
      if (!mounted) return;
      setState(() {
        _d = d;
        _classes = _list(c['classes']);
        _unsigned = _list(u['marks']);
        final tts = _list(t['timetables']);
        _tt = tts.isEmpty ? null : tts.first;
        if (_class.isEmpty && _classes.isNotEmpty) _class = _s(_classes.first['name']);
      });
      await _loadRoster();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _loadRoster() async {
    if (_class.isEmpty) return;
    final l = _map(await _api('GET', '/api/shiksha/learners', query: {'class_ref': _class}));
    if (mounted) setState(() => _roster = _list(l['learners']));
  }

  Future<Map<String, dynamic>?> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = _map(await f());
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e'.replaceFirst('Exception: ', ''));
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _classPicker() => Wrap(spacing: 6, children: [
        for (final c in _classes)
          ChoiceChip(
              label: Text(_s(c['name'])),
              selected: _class == _s(c['name']),
              onSelected: (_) {
                setState(() {
                  _class = _s(c['name']);
                  _absent.clear();
                });
                _loadRoster();
              }),
      ]);

  Widget _hazri() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _classPicker(),
        const SizedBox(height: 8),
        const Text('Tap the absent children; everyone else will be counted present.', style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        for (final l in _roster)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: _absent.contains(_s(l['number'])),
            onChanged: l['usable'] == true ? (v) => setState(() => v == true ? _absent.add(_s(l['number'])) : _absent.remove(_s(l['number']))) : null,
            title: Text('${_s(l['roll']).isEmpty ? '' : '${_s(l['roll'])}. '}${_s(l['name'])}'),
            subtitle: l['usable'] == true ? null : const Text('Guardian consent pending', style: TextStyle(color: C.warn, fontSize: 11.5)),
          ),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(
              child: GradientButton(
                  label: 'Save attendance',
                  height: 44,
                  onTap: _busy || _class.isEmpty
                      ? null
                      : () => _run(() => _api('POST', '/api/daftar/attendance', body: {'class': _class, 'absent': _absent.toList()})))),
          const SizedBox(width: 8),
          GlassButton(
              label: 'Guardian alerts (card)',
              onTap: _busy || _class.isEmpty ? null : () => _run(() => _api('POST', '/api/daftar/attendance/alerts', body: {'class': _class}))),
        ]),
      ]);

  Widget _marks() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_unsigned.length} marks are waiting for the teacher\'s sign-off. Select the correct ones and sign off.',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        for (final m in _unsigned)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: _pick.contains(_s(m['id'])),
            onChanged: (v) => setState(() => v == true ? _pick.add(_s(m['id'])) : _pick.remove(_s(m['id']))),
            title: Text('${_s(m['name'])} · ${_s(m['assessment'])}'),
            subtitle: Text('${_s(m['subject'])}: ${_s(m['marks'])}/${_s(m['max'])} · ${_s(m['by'])}', style: const TextStyle(fontSize: 12)),
          ),
        if (_unsigned.isNotEmpty)
          GradientButton(
              label: 'Sign off selected marks',
              height: 44,
              onTap: _busy || _pick.isEmpty
                  ? null
                  : () async {
                      await _run(() => _api('POST', '/api/shiksha/marks/sign', body: {'ids': _pick.toList()}));
                      if (mounted) setState(() => _pick.clear());
                    }),
      ]);

  Widget _timetable() {
    final tt = _tt;
    if (tt == null) {
      return const Text('No timetable yet. Tell me in chat: "Make a timetable for 9-A and 10-A: Maths Mrs Rao 6 periods..."',
          style: TextStyle(color: C.muted));
    }
    final grid = _map(tt['grid']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('${_s(tt['number'])} (${_s(tt['status'])})', style: const TextStyle(fontWeight: FontWeight.w800)),
      for (final c in grid.entries) ...[
        Caption(c.key),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 12,
            columns: [
              const DataColumn(label: Text('Din')),
              for (var p = 0; p < ((_map(c.value).values.isEmpty ? const [] : _map(c.value).values.first as List).length); p++)
                DataColumn(label: Text('${p + 1}')),
            ],
            rows: [
              for (final d in _map(c.value).entries)
                DataRow(cells: [
                  DataCell(Text(d.key)),
                  for (final cell in (d.value as List)) DataCell(Text(_s(cell).split(' / ').first, style: const TextStyle(fontSize: 12))),
                ]),
            ],
          ),
        ),
      ],
    ]);
  }

  Widget _report() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _classPicker(),
        const SizedBox(height: 6),
        const Text('Only signed-off marks go into the report card.', style: TextStyle(color: C.muted, fontSize: 12.5)),
        for (final l in _roster.where((x) => x['usable'] == true))
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_s(l['name'])),
            trailing: Wrap(spacing: 4, children: [
              TextButton(onPressed: _busy ? null : () => _run(() => _api('POST', '/api/daftar/report/${l['number']}/file', body: const {})), child: const Text('Word')),
              TextButton(onPressed: _busy ? null : () => _run(() => _api('POST', '/api/daftar/report/${l['number']}/share', body: const {})), child: const Text('Guardian')),
            ]),
          ),
      ]);

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('School office')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              if (_s(_d?['say']).isNotEmpty) Glass(child: Text(_s(_d?['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
              const SizedBox(height: 10),
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Attendance'), (1, 'Marks'), (2, 'Timetable'), (3, 'Report card')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_hazri(), _marks(), _timetable(), _report()][_tab],
              const SizedBox(height: 14),
              const Text('Hoola\'s marks are suggestions: they are final only after the teacher\'s sign-off. Anything to a guardian goes only with your tap.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// Absence alerts / a report card for guardians: ONLY her tap here prepares the drafts she sends herself.
class DaftarShareCard extends StatefulWidget {
  const DaftarShareCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<DaftarShareCard> createState() => _DaftarShareCardState();
}

class _DaftarShareCardState extends State<DaftarShareCard> {
  Map<String, dynamic>? _done;
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    final sh = _map(widget.data['share']);
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/daftar/shares/${sh['id']}/decide', body: {'yes': yes, 'hash': sh['hash']}));
      if (mounted) setState(() => _done = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _open(String url) async {
    final r = await Native.openExternal(url: url);
    if (r.isNotEmpty && r != 'ok' && mounted) _snack(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final src = _done ?? widget.data;
    final sh = _map(src['share']);
    final p = _map(_map(widget.data['share'])['payload']);
    final res = _map(sh['result']).isNotEmpty ? _map(sh['result']) : src;
    final waiting = _s(sh['status']) == 'waiting';
    final absent = _s(_map(widget.data['share'])['kind']) == 'absent';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          Icon(absent ? Icons.event_busy_rounded : Icons.assignment_rounded, size: 18, color: C.accent),
          const SizedBox(width: 6),
          Expanded(
              child: Text(absent ? '${_s(p['class'])}: ${(p['people'] as List? ?? const []).length} absent · ${_s(p['day'])}' : 'Report card: ${_s(p['name'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(sh['status']).toUpperCase(), fg: waiting ? C.warn : (_s(sh['status']) == 'shared' ? C.ok : C.muted)),
        ]),
        if (_s(src['say']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(src['say']), style: const TextStyle(fontSize: 12.5, color: C.muted))),
        const SizedBox(height: 8),
        if (waiting)
          Row(children: [
            Expanded(child: GradientButton(label: 'Yes, make the drafts', height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Declined', onTap: _busy ? null : () => _decide(false)),
          ]),
        for (final d in _list(res['drafts']))
          TextButton.icon(onPressed: () => _open(_s(d['link'])), icon: const Icon(Icons.chat_rounded, size: 18), label: Text('WhatsApp draft to ${_s(d['to'])}')),
        for (final e in _map(res['links']).entries)
          TextButton.icon(onPressed: () => _open(_s(e.value)), icon: const Icon(Icons.chat_rounded, size: 18), label: const Text('WhatsApp draft (attach the file yourself)')),
      ]),
    );
  }
}
