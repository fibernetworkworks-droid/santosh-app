/// Profile > Auditor's assistant (v0.96): Hoola does an audit's leg-work; the CA judges and signs.
/// Audits list -> one audit: upload TB (this year / last year) and day book, materiality with its reason, "Jaanch
/// chalao" (analytics, journal-entry tests, cash / TDS rules, Benford, going concern), findings to close one by one,
/// sample, confirmations (sent only after her Haan), client query list, rep letter, working papers.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';
import 'gst_screen.dart' show rs;

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Color _lvl(String l) => switch (l) { 'bad' => C.bad, 'warn' => C.warn, _ => C.muted };

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  List<Map<String, dynamic>> _e = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final e = await widget.app.api!.audEngagements();
      if (mounted) setState(() => _e = e);
    } catch (_) {}
  }

  Future<void> _new() async {
    final client = TextEditingController();
    final now = DateTime.now();
    final fy = TextEditingController(text: '${now.month >= 4 ? now.year - 1 : now.year - 2}-${(now.month >= 4 ? now.year : now.year - 1) % 100}');
    var kind = 'tax';
    var entity = 'firm';
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, setS) => AlertDialog(
          title: const Text('Naya audit'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: client, decoration: const InputDecoration(labelText: 'Client')),
              TextField(controller: fy, decoration: const InputDecoration(labelText: 'Saal (2025-26)')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final k in const ['tax', 'statutory', 'internal', 'stock'])
                  ChoiceChip(label: Text(k), selected: kind == k, onSelected: (_) => setS(() => kind = k)),
              ]),
              Wrap(spacing: 6, children: [
                for (final k in const ['firm', 'private', 'public', 'individual'])
                  ChoiceChip(label: Text(k), selected: entity == k, onSelected: (_) => setS(() => entity = k)),
              ]),
            ]),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Shuru'))],
        ),
      ),
    );
    if (ok != true) return;
    try {
      final r = await widget.app.api!.audNew({'client': client.text.trim(), 'fy': fy.text.trim(), 'kind': kind, 'entity': entity});
      if (!mounted) return;
      _snack(context, _s(r['say']));
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => AuditPage(app: widget.app, id: _s((r['engagement'] as Map)['id']))));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text("Auditor's assistant")),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              GradientButton(label: 'Naya audit', icon: Icons.fact_check_rounded, onTap: _new),
              const SizedBox(height: 12),
              for (final e in _e)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Press(
                    onTap: () async {
                      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => AuditPage(app: widget.app, id: _s(e['id']))));
                      _load();
                    },
                    child: Glass(
                      child: Row(children: [
                        const Icon(Icons.fact_check_rounded, color: C.accent),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(_s(e['client']), style: const TextStyle(fontWeight: FontWeight.w800)),
                            Text('${_s(e['kind_label'])} · FY ${_s(e['fy'])} · ${_s(e['status'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                          ]),
                        ),
                        Pill('${(e['findings'] as Map?)?['open'] ?? 0} khule'),
                      ]),
                    ),
                  ),
                ),
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text('Hoola jaanch aur kaagaz taiyaar karta hai. Audit ki raay, sign aur UDIN CA ke.',
                    style: TextStyle(color: C.faint, fontSize: 11.5)),
              ),
            ]),
          ),
        ),
      );
}

class AuditPage extends StatefulWidget {
  const AuditPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<AuditPage> createState() => _AuditPageState();
}

class _AuditPageState extends State<AuditPage> {
  Map<String, dynamic>? _e;
  List<Map<String, dynamic>> _f = [];
  bool _busy = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final e = await app.api!.audGet(widget.id);
      final f = await app.api!.audFindings(widget.id);
      if (mounted) setState(() {
        _e = e;
        _f = f;
      });
    } catch (_) {}
  }

  Future<void> _upload(String what) async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'xlsx']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.audUpload(widget.id, what, f.name, f.bytes!);
      if (mounted) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _act(String a, [Map<String, dynamic> body = const {}, bool copy = false]) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.audAct(widget.id, a, {...body, 'conversation_id': app.conversationId ?? ''});
      if (copy && _s(r['draft']).isNotEmpty) {
        await Clipboard.setData(ClipboardData(text: _s(r['draft'])));
      }
      if (mounted) _snack(context, _s(r['say']).isEmpty ? 'Ho gaya' : _s(r['say']) + (copy ? ' (copy ho gaya)' : ''));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<bool> _confirm(String q) async =>
      await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          content: Text(q),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan')),
          ],
        ),
      ) ==
      true;

  Future<void> _close(Map<String, dynamic> f) async {
    final note = TextEditingController();
    var remember = false;
    final status = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => Padding(
          padding: EdgeInsets.fromLTRB(12, 12, 12, 12 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Glass(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(f['text']), style: const TextStyle(height: 1.3)),
              TextField(controller: note, decoration: const InputDecoration(labelText: 'Aapka note / client ka jawab')),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: remember,
                onChanged: (v) => setS(() => remember = v ?? false),
                title: const Text('Is client ke liye yeh baat agli baar mat uthana'),
              ),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final st in const [('explained', 'Samjha diya'), ('adjusted', 'Entry theek ki'), ('reported', 'Report mein'), ('asked', 'Poochha')])
                  GlassButton(label: st.$2, onTap: () => Navigator.pop(ctx, st.$1)),
              ]),
            ]),
          ),
        ),
      ),
    );
    if (status == null) return;
    try {
      await app.api!.audClose(_s(f['id']), {'status': status, 'note': note.text.trim(), 'remember': remember});
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final e = _e;
    final m = Map<String, dynamic>.from((e?['materiality'] as Map?) ?? const {});
    final facts = Map<String, dynamic>.from((e?['facts'] as Map?) ?? const {});
    final ta = facts['tax_audit'] as Map?;
    final caro = facts['caro'] as Map?;
    final open = _f.where((f) => f['status'] == 'open' || f['status'] == 'asked').toList();
    final closed = _f.where((f) => !(f['status'] == 'open' || f['status'] == 'asked')).toList();
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(e?['client']).isEmpty ? 'Audit' : _s(e?['client']))),
      body: Aurora(
        child: e == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(e['kind_label'])} · FY ${_s(e['fy'])}', style: display(15)),
                      const SizedBox(height: 8),
                      Wrap(spacing: 8, runSpacing: 8, children: [
                        GlassButton(label: e['has_tb'] == true ? 'TB ✓' : 'Is saal ka TB', icon: Icons.upload_file_rounded, onTap: _busy ? null : () => _upload('tb')),
                        GlassButton(label: e['has_prev'] == true ? 'Pichhla TB ✓' : 'Pichhle saal ka TB', icon: Icons.history_rounded, onTap: _busy ? null : () => _upload('tb_prev')),
                        GlassButton(label: (e['entries'] ?? 0) > 0 ? 'Day book ✓ (${e['entries']})' : 'Day book', icon: Icons.menu_book_rounded, onTap: _busy ? null : () => _upload('daybook')),
                      ]),
                    ]),
                  ),
                  if (m.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Glass(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Materiality (SA 320)', style: display(15)),
                        Text('${rs(m['overall'])} = ${m['pct']}% ${_s(m['benchmark_label'])} (${rs(m['base'])})', style: const TextStyle(fontWeight: FontWeight.w700)),
                        Text('Performance ${rs(m['performance'])} · chhota farak ${rs(m['trivial'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                        Text('Kyun: ${_s(m['why'])}', style: const TextStyle(color: C.faint, fontSize: 12)),
                      ]),
                    ),
                  ],
                  if (ta != null || caro != null) ...[
                    const SizedBox(height: 10),
                    Glass(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        if (ta != null)
                          Text('Tax audit: ${ta['required'] == true ? 'zaroori' : 'zaroori nahi'} · ${_s(ta['form'])} · due ${_s(ta['due'])} ${_s(ta['note'])}',
                              style: const TextStyle(fontSize: 13)),
                        if (caro != null) Text('CARO 2020: ${caro['applies'] == true ? 'lagu' : 'lagu nahi'} (${_s(caro['why'])})', style: const TextStyle(fontSize: 13)),
                      ]),
                    ),
                  ],
                  const SizedBox(height: 10),
                  GradientButton(
                      label: _busy ? 'Jaanch chal rahi...' : 'Jaanch chalao',
                      icon: Icons.manage_search_rounded,
                      onTap: _busy || e['has_tb'] != true ? null : () => _act('run')),
                  const SizedBox(height: 10),
                  if (open.isNotEmpty) Text('Dekhni hain (${open.length})', style: display(15)),
                  for (final f in open)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Press(
                        onTap: () => _close(f),
                        child: Glass(
                          padding: const EdgeInsets.all(10),
                          border: f['level'] == 'bad' ? C.bad : null,
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Icon(Icons.circle, size: 10, color: _lvl(_s(f['level']))),
                            const SizedBox(width: 8),
                            Expanded(child: Text(_s(f['text']), style: const TextStyle(fontSize: 13, height: 1.3))),
                            if (f['status'] == 'asked') const Pill('poochha'),
                          ]),
                        ),
                      ),
                    ),
                  if (closed.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text('${closed.length} band ho chuki', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ),
                  const SizedBox(height: 12),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    GlassButton(label: 'Sample (MUS)', icon: Icons.casino_rounded, onTap: _busy ? null : () => _act('sample', {'method': 'mus'})),
                    GlassButton(label: 'Confirmation draft', icon: Icons.mark_email_read_rounded, onTap: _busy ? null : () => _act('confirmations')),
                    GlassButton(
                        label: 'Confirmation bhejne do',
                        icon: Icons.send_rounded,
                        onTap: _busy
                            ? null
                            : () async {
                                if (await _confirm('Balance confirmation letters bahar bhejne ki haan?')) _act('approve_confirmations', {'approve': true});
                              }),
                    GlassButton(label: 'Client ke sawaal', icon: Icons.help_center_rounded, onTap: _busy ? null : () => _act('queries', const {}, true)),
                    GlassButton(
                        label: 'Sawaal bhej diye',
                        icon: Icons.done_all_rounded,
                        onTap: _busy
                            ? null
                            : () async {
                                if (await _confirm('Client ko sawaal bhej diye?')) _act('asked');
                              }),
                    GlassButton(label: 'Rep letter (SA 580)', icon: Icons.description_rounded, onTap: _busy ? null : () => _act('rep_letter', const {}, true)),
                    GlassButton(label: 'Working papers', icon: Icons.folder_zip_rounded, onTap: _busy ? null : () => _act('workpapers')),
                  ]),
                  const SizedBox(height: 10),
                  const Text('Raay, sign, UDIN aur Form 3CD / 26 filing CA ke. Letters aur sawaal aapki haan ke baad hi bahar jaate hain.',
                      style: TextStyle(color: C.faint, fontSize: 11.5)),
                ]),
              ),
      ),
    );
  }
}

/// Chat card after a test run (event `audit_update`).
class AuditCard extends StatelessWidget {
  const AuditCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AuditPage(app: app, id: _s(v['engagement'])))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.manage_search_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text('Audit jaanch poori: ${v['findings'] ?? 0} baatein dekhni hain', style: const TextStyle(fontWeight: FontWeight.w700))),
            const Icon(Icons.chevron_right_rounded, color: C.muted),
          ]),
        ),
      );
}
