import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

/// Santosh Agent Army: 36,336 open-source AI agents worldwide, by field, tier and kind.
class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  final _q = TextEditingController();
  Timer? _debounce;
  List<Map<String, dynamic>> _fields = [];
  List<Map<String, dynamic>> _items = [];
  int _total = 0;
  String _field = '';
  String _kind = '';
  bool _proven = true;   // Tier A + B only
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _q.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    try {
      final st = await widget.app.api!.agentsFields();
      _fields = List<Map<String, dynamic>>.from((st['fields'] as List?) ?? const []);
      _total = (st['total'] as num?)?.toInt() ?? 0;
    } catch (e) {
      _error = '$e';
    }
    await _search();
  }

  Future<void> _search() async {
    setState(() => _loading = true);
    try {
      final q = _q.text.trim();
      final j = await widget.app.api!.agentsDirectory(
          q: q, field: _field, kind: _kind, tier: _proven ? 'A,B' : (q.isEmpty && _field.isEmpty && _kind.isEmpty ? 'A,B,C,D' : ''));
      _items = List<Map<String, dynamic>>.from((j['agents'] as List?) ?? const []);
      _total = (j['total'] as num?)?.toInt() ?? _total;
      _error = null;
    } catch (e) {
      _error = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  void _typed(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 380), _search);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: C.bgTop, title: Text('Agent Army · ${_fmt(_total)}')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 6),
          child: TextField(
            controller: _q,
            onChanged: _typed,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _search(),
            decoration: InputDecoration(
              hintText: 'Kaunsa agent chahiye? e.g. call centre, GST, coding, legal',
              prefixIcon: const Icon(Icons.search_rounded),
              filled: true,
              fillColor: C.panel,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            ),
          ),
        ),
        SizedBox(
          height: 42,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            _chip(_proven ? '✓ Sirf proven (A/B)' : 'Sab tiers', _proven, () {
              setState(() => _proven = !_proven);
              _search();
            }),
            for (final k in const ['Agent / app', 'Framework / SDK', 'Plugin / tool / connector'])
              _chip(k, _kind == k, () {
                setState(() => _kind = _kind == k ? '' : k);
                _search();
              }),
          ]),
        ),
        SizedBox(
          height: 42,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            _chip('Sab fields', _field.isEmpty, () {
              setState(() => _field = '');
              _search();
            }),
            for (final f in _fields)
              _chip('${f['field']} · ${_fmt((f['agents'] as num?)?.toInt() ?? 0)}', _field == f['field'], () {
                setState(() => _field = _field == f['field'] ? '' : f['field'] as String);
                _search();
              }),
          ]),
        ),
        if (_loading) const LinearProgressIndicator(minHeight: 2, color: C.accent),
        Expanded(
          child: _error != null && _items.isEmpty
              ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!, style: const TextStyle(color: C.bad))))
              : _items.isEmpty && !_loading
                  ? const Center(child: Text('Kuch nahi mila. Doosre shabd ya "Sab tiers" try kijiye.', style: TextStyle(color: C.muted)))
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                      itemCount: _items.length + 1,
                      itemBuilder: (context, i) {
                        if (i == _items.length) {
                          return const Padding(
                            padding: EdgeInsets.only(top: 6),
                            child: Text('Score popularity/recency ka signal hai, benchmark nahi. Production se pehle sandbox mein test kijiye.',
                                style: TextStyle(color: C.faint, fontSize: 11.5)),
                          );
                        }
                        return _card(_items[i]);
                      },
                    ),
        ),
      ]),
    );
  }

  Widget _chip(String label, bool on, VoidCallback tap) => Padding(
        padding: const EdgeInsets.only(right: 6, top: 4, bottom: 4),
        child: ChoiceChip(label: Text(label, style: const TextStyle(fontSize: 12)), selected: on, onSelected: (_) => tap()),
      );

  Widget _card(Map<String, dynamic> a) {
    final tier = a['tier'] as String? ?? '';
    final tierColor = tier.startsWith('A') ? C.ok : (tier.startsWith('B') ? C.teal : C.muted);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: InkWell(
          onTap: () => _details(a),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(a['name'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: display(15.5))),
              Pill(tier.split(' ').first, fg: tierColor),
              const SizedBox(width: 6),
              Pill('${a['score'] ?? ''}', fg: C.chip),
            ]),
            const SizedBox(height: 4),
            Text('${a['field']} · ${a['kind']}', style: const TextStyle(color: C.faint, fontSize: 12)),
            const SizedBox(height: 6),
            Text(a['does'] as String? ?? '', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, height: 1.35)),
            if (a['caution'] != null || a['licence_note'] != null || a['blocked'] == true) ...[
              const SizedBox(height: 6),
              Wrap(spacing: 6, runSpacing: 4, children: [
                if (a['blocked'] == true) const Pill('Hoola use nahi karega', fg: C.bad),
                if (a['caution'] != null) const Pill('⚠ Sandbox mein chalaiye', fg: C.warn),
                if (a['licence_note'] != null && !(a['licence_note'] as String).startsWith('Licence not listed')) const Pill('Licence dhyan', fg: C.warn),
              ]),
            ],
          ]),
        ),
      ),
    );
  }

  Future<void> _details(Map<String, dynamic> brief) async {
    Map<String, dynamic> a = brief;
    try {
      a = await widget.app.api!.agentItem('${brief['ref']}');
    } catch (_) {}
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF151A24),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: .7,
        maxChildSize: .95,
        builder: (ctx, sc) => ListView(controller: sc, padding: const EdgeInsets.fromLTRB(20, 18, 20, 24), children: [
          Text(a['name'] as String? ?? '', style: display(22)),
          const SizedBox(height: 4),
          Text('${a['tier']} · score ${a['score']} · ${a['kind']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 12),
          Text(a['does'] as String? ?? '', style: const TextStyle(fontSize: 14.5, height: 1.4)),
          const SizedBox(height: 14),
          _row('Field', '${a['field']}${a['also_fits'] != null ? ' · also ${a['also_fits']}' : ''}'),
          if (a['language'] != null && '${a['language']}'.isNotEmpty) _row('Language', '${a['language']}'),
          if (a['github_stars'] != null) _row('GitHub stars', '${a['github_stars']}'),
          if (a['npm_downloads_month'] != null) _row('npm downloads / month', _fmt((a['npm_downloads_month'] as num).toInt())),
          if (a['days_trending'] != null) _row('Days on GitHub trending', '${a['days_trending']}'),
          if (a['last_release'] != null) _row('Last release', '${a['last_release']}'),
          if (a['licence'] != null) _row('Licence', '${a['licence']}'),
          if (a['in_curated_lists'] != null) _row('In curated lists', '${a['in_curated_lists']}'),
          if (a['found_in'] != null) _row('Found in', '${a['found_in']}'),
          if (a['packages'] != null) _row('Packages', '${a['packages']}'),
          const SizedBox(height: 10),
          _box('Hoola ke saath kaise', a['how_to_use'] as String? ?? '', C.teal),
          if (a['licence_note'] != null) _box('Licence', a['licence_note'] as String, C.warn),
          if (a['caution'] != null) _box('Savdhaan', a['caution'] as String, C.bad),
          const SizedBox(height: 12),
          if ((a['link'] as String? ?? '').startsWith('http'))
            FilledButton.icon(
              onPressed: () => launchUrl(Uri.parse(a['link'] as String), mode: LaunchMode.externalApplication),
              icon: const Icon(Icons.open_in_new_rounded),
              label: const Text('Project page kholiye'),
            ),
        ]),
      ),
    );
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 150, child: Text(k, style: const TextStyle(color: C.faint, fontSize: 12.5))),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 13))),
        ]),
      );

  Widget _box(String title, String text, Color c) => Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withOpacity(.12), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
          const SizedBox(height: 4),
          Text(text, style: const TextStyle(fontSize: 13, height: 1.35)),
        ]),
      );
}

String _fmt(int n) {
  final s = n.toString();
  if (s.length <= 3) return s;
  final last3 = s.substring(s.length - 3);
  var head = s.substring(0, s.length - 3);
  final parts = <String>[];
  while (head.length > 2) {
    parts.insert(0, head.substring(head.length - 2));
    head = head.substring(0, head.length - 2);
  }
  if (head.isNotEmpty) parts.insert(0, head);
  return '${parts.join(',')},$last3';
}
