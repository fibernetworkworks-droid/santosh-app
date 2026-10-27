// v0.147 Hoola Postgres: her own PostgreSQL database (what a Postgres MCP server gives an agent).
// The connection string is typed ONLY here (hidden), sealed on the server and never shown again.
// Reads run READ ONLY; every change is a PgWriteCard that runs only when she taps Haan.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';

class PgWriteCard extends StatefulWidget {
  const PgWriteCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  State<PgWriteCard> createState() => _PgWriteCardState();
}

class _PgWriteCardState extends State<PgWriteCard> {
  bool _busy = false;
  Map<String, dynamic>? _now;

  Future<void> _decide(bool yes) async {
    final api = widget.app.api;
    if (api == null || _busy) return;
    if (yes && ((widget.v['danger'] as List?)?.isNotEmpty ?? false)) {
      final ok = await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(
                title: const Text('Pakka chalaun?'),
                content: Text(((widget.v['danger'] as List?) ?? const []).join('\n')),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
                  FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, chalao')),
                ],
              ));
      if (ok != true) return;
    }
    setState(() => _busy = true);
    try {
      final r = await api.call('POST', '/api/pgdb/writes/${widget.v['id']}/decide', body: {'yes': yes, 'hash': widget.v['hash']});
      if (r is Map) setState(() => _now = Map<String, dynamic>.from(r));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Nahi ho paya: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = {...widget.v, ...?_now};
    final st = '${v['status'] ?? 'pending'}';
    final danger = ((v['danger'] as List?) ?? const []).map((e) => '$e').toList();
    final color = st == 'done' ? C.ok : st == 'failed' ? C.bad : st == 'pending' ? C.accent : C.faint;
    return Glass(flat: true,
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.storage_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(
              child: Text('Database badlav ${v['number'] ?? ''} · ${v['database'] ?? ''}',
                  style: const TextStyle(fontWeight: FontWeight.w700))),
          Pill(st == 'pending' ? 'haan chahiye' : st == 'done' ? 'ho gaya' : st == 'failed' ? 'nahi hua' : st == 'rejected' ? 'mana' : st,
              fg: color),
        ]),
        if ('${v['reason'] ?? ''}'.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('${v['reason']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ],
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
          constraints: const BoxConstraints(maxHeight: 220),
          child: SingleChildScrollView(
              child: SelectableText('${v['sql'] ?? ''}', style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5))),
        ),
        for (final d in danger)
          Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.warning_amber_rounded, color: C.warn, size: 16),
                const SizedBox(width: 6),
                Expanded(child: Text(d, style: const TextStyle(color: C.warn, fontSize: 12.5))),
              ])),
        const SizedBox(height: 8),
        Text('${v['say'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if (st == 'pending') ...[
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 10),
            Expanded(
                child: GradientButton(
                    label: _busy ? 'Chal raha hai…' : 'Haan, chalao', icon: Icons.check_rounded, height: 48,
                    onTap: _busy ? null : () => _decide(true))),
          ]),
          const SizedBox(height: 6),
          const Text('Saare statements ek transaction mein: sab chalenge ya kuch nahi.',
              style: TextStyle(color: C.faint, fontSize: 11.5)),
        ],
      ]),
    );
  }
}

class PostgresScreen extends StatefulWidget {
  const PostgresScreen({super.key, required this.app});
  final Santosh app;

  @override
  State<PostgresScreen> createState() => _PostgresScreenState();
}

class _PostgresScreenState extends State<PostgresScreen> {
  Map<String, dynamic>? _home;
  String? _err;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _say(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    setState(() => _loading = true);
    try {
      final r = await api.call('GET', '/api/pgdb');
      if (mounted) {
        setState(() {
          _home = Map<String, dynamic>.from(r as Map);
          _err = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _add() async {
    final name = TextEditingController();
    final dsn = TextEditingController();
    bool hide = true;
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => StatefulBuilder(
            builder: (c, set) => AlertDialog(
                  title: const Text('Postgres database jodiye'),
                  content: SingleChildScrollView(
                    child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                      TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (jaise Dukaan DB)')),
                      const SizedBox(height: 8),
                      TextField(
                        controller: dsn,
                        obscureText: hide,
                        autocorrect: false,
                        enableSuggestions: false,
                        decoration: InputDecoration(
                            labelText: 'Connection string',
                            hintText: 'postgresql://user:password@host:5432/db',
                            suffixIcon: IconButton(
                                icon: Icon(hide ? Icons.visibility_rounded : Icons.visibility_off_rounded),
                                onPressed: () => set(() => hide = !hide))),
                      ),
                      const SizedBox(height: 10),
                      const Text(
                          'Neon, Supabase, AWS RDS, DigitalOcean ya apne server ka. Sirf yahan daaliye, chat mein kabhi nahi. '
                          'Server par band (encrypt) rehta hai, wapas kabhi nahi dikhta. Sirf public host + SSL.\n\n'
                          'Sabse surakshit: database mein ek read-only user banaiye (sirf SELECT). Badlav tab bhi aapki haan '
                          'se hi chalenge.',
                          style: TextStyle(fontSize: 12, color: C.muted)),
                    ]),
                  ),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
                    FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo aur jaancho')),
                  ],
                )));
    final s = dsn.text.trim();
    dsn.clear();
    if (ok != true || s.isEmpty) return;
    try {
      final r = await widget.app.api!.call('POST', '/api/pgdb/conns', body: {'name': name.text.trim(), 'dsn': s});
      final m = Map<String, dynamic>.from(r as Map);
      _say('${m['say'] ?? 'Jud gaya'}');
      for (final n in ((m['notes'] as List?) ?? const [])) {
        _say('$n');
      }
      _load();
    } catch (e) {
      _say('Nahi juda: $e');
    }
  }

  Future<void> _remove(Map<String, dynamic> c) async {
    final ok = await showDialog<bool>(
        context: context,
        builder: (x) => AlertDialog(
              title: Text('${c['name']} hatayein?'),
              content: const Text('Hoola ke paas iska password nahi rahega. Database ko kuch nahi hoga.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(x, false), child: const Text('Nahi')),
                FilledButton(onPressed: () => Navigator.pop(x, true), child: const Text('Hatao')),
              ],
            ));
    if (ok != true) return;
    try {
      await widget.app.api!.call('DELETE', '/api/pgdb/conns/${c['id']}');
      _load();
    } catch (e) {
      _say('$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final dbs = ((_home?['databases'] as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    final writes = ((_home?['writes'] as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    final rules = ((_home?['rules'] as List?) ?? const []).map((e) => '$e').toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Postgres database')),
      floatingActionButton:
          FloatingActionButton.extended(onPressed: _add, icon: const Icon(Icons.add_rounded), label: const Text('Database jodo')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${widget.app.aName} aapka database padhta hai',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 6),
              const Text(
                  'Chat ya call mein poochhiye: "kal kitne order aaye?", "kaunse graahak 30 din se nahi aaye?", "app dheema kyun '
                  'hai?". Hoola tables dekhkar sahi query chalata hai, explain / health se dheemapan dhoondhta hai.',
                  style: TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              for (final r in rules)
                Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Row(children: [
                      const Icon(Icons.lock_rounded, size: 14, color: C.ok),
                      const SizedBox(width: 6),
                      Expanded(child: Text(r, style: const TextStyle(fontSize: 12, color: C.chip))),
                    ])),
            ]),
          ),
          const SizedBox(height: 12),
          if (_loading && _home == null) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
          if (_err != null && _home == null) Text(_err!, style: const TextStyle(color: C.bad)),
          if (_home != null && dbs.isEmpty)
            const Padding(
                padding: EdgeInsets.all(20),
                child: Text('Abhi koi database nahi juda. "Database jodo" dabaiye.', style: TextStyle(color: C.faint))),
          for (final c in dbs)
            Glass(
              margin: const EdgeInsets.only(bottom: 10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Icon(Icons.storage_rounded, color: c['status'] == 'ok' ? C.ok : C.bad),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${c['name']}', style: const TextStyle(fontWeight: FontWeight.w700))),
                  PopupMenuButton<String>(
                    onSelected: (k) async {
                      if (k == 'test') {
                        try {
                          final r = await widget.app.api!.call('POST', '/api/pgdb/conns/${c['id']}/test');
                          _say('Jud raha hai: ${(r as Map)['version'] ?? ''}');
                        } catch (e) {
                          _say('$e');
                        }
                        _load();
                      } else if (k == 'tables') {
                        Navigator.of(context).push(MaterialPageRoute(builder: (_) => _PgTablesPage(app: widget.app, conn: c)));
                      } else if (k == 'health') {
                        Navigator.of(context).push(MaterialPageRoute(builder: (_) => _PgHealthPage(app: widget.app, conn: c)));
                      } else if (k == 'remove') {
                        _remove(c);
                      }
                    },
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: 'tables', child: Text('Tables dekho')),
                      PopupMenuItem(value: 'health', child: Text('Sehat jaancho')),
                      PopupMenuItem(value: 'test', child: Text('Connection jaancho')),
                      PopupMenuItem(value: 'remove', child: Text('Hatao')),
                    ],
                  ),
                ]),
                Text('${c['label']}', style: const TextStyle(color: C.muted, fontSize: 12)),
                const SizedBox(height: 4),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  Pill('PostgreSQL ${'${c['server_version'] ?? ''}'.split(' ').first}'),
                  Pill('SSL ${c['sslmode']}'),
                  if (c['is_super'] == true) const Pill('superuser: read-only user behtar', fg: C.warn),
                  if (c['can_write'] == false) const Pill('sirf padh sakta hai', fg: C.ok),
                ]),
                if ('${c['last_error'] ?? ''}'.isNotEmpty)
                  Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text('${c['last_error']}', style: const TextStyle(color: C.bad, fontSize: 12))),
              ]),
            ),
          if (writes.isNotEmpty) ...[
            const SizedBox(height: 6),
            const Caption('BADLAV KE CARD'),
            for (final w in writes) PgWriteCard(key: ValueKey('pgw${w['id']}${w['status']}'), v: w, app: widget.app),
          ],
        ]),
      ),
    );
  }
}

class _PgTablesPage extends StatefulWidget {
  const _PgTablesPage({required this.app, required this.conn});
  final Santosh app;
  final Map<String, dynamic> conn;

  @override
  State<_PgTablesPage> createState() => _PgTablesPageState();
}

class _PgTablesPageState extends State<_PgTablesPage> {
  Map<String, dynamic>? _d;
  String _schema = 'public';
  String? _err;
  final _sql = TextEditingController();
  Map<String, dynamic>? _res;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _sql.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.call('GET', '/api/pgdb/conns/${widget.conn['id']}/schema', query: {'schema': _schema});
      if (mounted) {
        setState(() {
          _d = Map<String, dynamic>.from(r as Map);
          _err = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _run() async {
    if (_busy || _sql.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!
          .call('POST', '/api/pgdb/conns/${widget.conn['id']}/query', body: {'sql': _sql.text.trim(), 'limit': 50});
      if (mounted) setState(() => _res = Map<String, dynamic>.from(r as Map));
    } catch (e) {
      if (mounted) setState(() => _res = {'error': '$e'});
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final schemas = ((_d?['schemas'] as List?) ?? const []).whereType<Map>().toList();
    final tables = ((_d?['tables'] as List?) ?? const []).whereType<Map>().toList();
    final cols = ((_res?['columns'] as List?) ?? const []).map((e) => '$e').toList();
    final rows = ((_res?['rows'] as List?) ?? const []).whereType<List>().toList();
    return Scaffold(
      appBar: AppBar(title: Text('${widget.conn['name']}')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (schemas.length > 1)
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final s in schemas)
              ChoiceChip(
                label: Text('${s['schema']} (${s['tables']})'),
                selected: _schema == '${s['schema']}',
                onSelected: (_) {
                  setState(() => _schema = '${s['schema']}');
                  _load();
                },
              ),
          ]),
        const SizedBox(height: 8),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Padhne wala query (SELECT)', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            TextField(
                controller: _sql,
                minLines: 2,
                maxLines: 6,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
                decoration: const InputDecoration(hintText: 'select * from orders order by id desc limit 20')),
            const SizedBox(height: 8),
            GradientButton(label: _busy ? 'Chal raha hai…' : 'Chalao (sirf padhna)', icon: Icons.play_arrow_rounded, height: 44,
                onTap: _busy ? null : _run),
            if (_res?['error'] != null)
              Padding(padding: const EdgeInsets.only(top: 8), child: Text('${_res!['error']}', style: const TextStyle(color: C.bad))),
            if (cols.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text('${_res!['row_count']} rows · ${_res!['ms']} ms${_res!['more'] == true ? ' · aur bhi hain' : ''}',
                  style: const TextStyle(color: C.faint, fontSize: 12)),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columns: [for (final c in cols) DataColumn(label: Text(c))],
                  rows: [
                    for (final r in rows)
                      DataRow(cells: [for (var i = 0; i < cols.length; i++) DataCell(Text(i < r.length ? '${r[i] ?? '—'}' : ''))])
                  ],
                ),
              ),
            ],
          ]),
        ),
        const SizedBox(height: 12),
        const Caption('TABLES'),
        for (final t in tables)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(t['kind'] == 'table' ? Icons.table_chart_rounded : Icons.visibility_rounded, color: C.accent),
            title: Text('${t['name']}'),
            subtitle: Text('${t['kind']} · ~${t['approx_rows']} rows · ${t['size']}', style: const TextStyle(color: C.muted)),
            onTap: () => setState(() => _sql.text = 'select * from "$_schema"."${t['name']}" limit 20'),
            onLongPress: () {
              Clipboard.setData(ClipboardData(text: '${t['name']}'));
            },
          ),
      ]),
    );
  }
}

class _PgHealthPage extends StatefulWidget {
  const _PgHealthPage({required this.app, required this.conn});
  final Santosh app;
  final Map<String, dynamic> conn;

  @override
  State<_PgHealthPage> createState() => _PgHealthPageState();
}

class _PgHealthPageState extends State<_PgHealthPage> {
  Map<String, dynamic>? _h;
  String? _err;

  @override
  void initState() {
    super.initState();
    () async {
      try {
        final r = await widget.app.api!.call('GET', '/api/pgdb/conns/${widget.conn['id']}/health');
        if (mounted) setState(() => _h = Map<String, dynamic>.from(r as Map));
      } catch (e) {
        if (mounted) setState(() => _err = '$e');
      }
    }();
  }

  @override
  Widget build(BuildContext context) {
    final checks = Map<String, dynamic>.from((_h?['checks'] as Map?) ?? const {});
    final tips = ((_h?['tips'] as List?) ?? const []).map((e) => '$e').toList();
    final conn = Map<String, dynamic>.from((checks['connections'] as Map?) ?? const {});
    return Scaffold(
      appBar: AppBar(title: Text('${widget.conn['name']} · sehat')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (_h == null && _err == null) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
        if (_h != null) ...[
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_h!['score']}/100', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: C.accent)),
              Text('Size ${checks['size'] ?? '—'} · connections ${conn['used'] ?? '—'}/${conn['max'] ?? '—'} · '
                  'cache hit ${checks['cache_hit_pct'] ?? '—'}%', style: const TextStyle(color: C.muted)),
            ]),
          ),
          const SizedBox(height: 12),
          if (tips.isEmpty) const Text('Sab theek dikh raha hai.', style: TextStyle(color: C.ok)),
          for (final t in tips)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.tips_and_updates_rounded, color: C.warn, size: 18),
                const SizedBox(width: 8),
                Expanded(child: Text(t)),
              ]),
            ),
          const SizedBox(height: 8),
          const Text('Theek karwana ho to chat mein boliye: Hoola badlav ka card banayega, chalega aapki haan se.',
              style: TextStyle(color: C.faint, fontSize: 12)),
        ],
      ]),
    );
  }
}
