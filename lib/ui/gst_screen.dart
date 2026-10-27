/// Profile > GST Sahayak (v0.93): Hoola does a GST practitioner's work for every client.
/// Aaj (due soon, late with late fee, notices), Clients (add with GSTIN; per client: sales / purchase register and
/// GSTR-2B upload, 2B milaan with IMS decisions, GSTR-1 / 3B / CMP-08), Returns (summary, checks, her Haan, file through
/// the Computer Operator, ARN), Notices. The portal password and OTP are never kept; tax is paid by the taxpayer.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

String rs(dynamic v) {
  final n = (v is num) ? v.toDouble() : double.tryParse('$v') ?? 0;
  final neg = n < 0;
  final whole = n.abs().round();
  var s = '$whole';
  if (s.length > 3) {
    var head = s.substring(0, s.length - 3);
    final tail = s.substring(s.length - 3);
    final parts = <String>[];
    while (head.length > 2) {
      parts.insert(0, head.substring(head.length - 2));
      head = head.substring(0, head.length - 2);
    }
    if (head.isNotEmpty) parts.insert(0, head);
    s = '${parts.join(',')},$tail';
  }
  return '${neg ? '-' : ''}₹$s';
}

List<String> _periods() {
  final now = DateTime.now();
  return [
    for (var i = 1; i <= 12; i++)
      () {
        final d = DateTime(now.year, now.month - i, 1);
        return '${d.year}-${d.month.toString().padLeft(2, '0')}';
      }()
  ];
}

String _nicePeriod(String p) {
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  final parts = p.split('-');
  if (parts.length != 2) return p;
  final i = int.tryParse(parts[1]) ?? 1;
  return '${m[(i - 1).clamp(0, 11)]} ${parts[0]}';
}

Color _stCol(String s) => switch (s) {
      'filed' => C.ok,
      'ready' => C.accent,
      'approved' || 'filing' => C.teal,
      'rejected' => C.faint,
      _ => C.muted,
    };

mixin _GstLive<T extends StatefulWidget> on State<T> {
  Santosh get app;
  int _tick = -1;
  Future<void> reload();
  void _onApp() {
    if (app.gstTick != _tick) {
      _tick = app.gstTick;
      reload();
    }
  }

  void startLive() {
    _tick = app.gstTick;
    app.addListener(_onApp);
    reload();
  }

  void stopLive() => app.removeListener(_onApp);
}

class GstScreen extends StatelessWidget {
  const GstScreen({super.key, required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: const Text('GST sahayak'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Aaj'),
              Tab(text: 'Clients'),
              Tab(text: 'Returns'),
              Tab(text: 'Notice'),
            ]),
          ),
          body: Aurora(
            child: TabBarView(children: [
              _TodayTab(app: app),
              _ClientsTab(app: app),
              _ReturnsTab(app: app),
              _NoticesTab(app: app),
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------- Aaj
class _TodayTab extends StatefulWidget {
  const _TodayTab({required this.app});
  final Santosh app;
  @override
  State<_TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends State<_TodayTab> with _GstLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  String? _err;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final d = await app.api!.gstToday();
      if (mounted) setState(() {
        _d = d;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Widget _row(Map<String, dynamic> x, bool late) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Press(
          onTap: _s(x['client_id']).isEmpty
              ? null
              : () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => GstClientPage(app: app, id: _s(x['client_id']), period: _s(x['period'])))),
          child: Glass(
            border: late ? C.bad : null,
            child: Row(children: [
              Icon(late ? Icons.warning_amber_rounded : Icons.event_rounded, color: late ? C.bad : C.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${_s(x['client'])} · ${_s(x['label'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text(
                      [
                        if (_s(x['period_nice']).isNotEmpty) _s(x['period_nice']),
                        late ? '${-(x['days'] as num? ?? 0)} din late' : 'Due ${_s(x['due_nice'])}',
                        if (late && x['late_fee'] != null) 'late fee ${rs(x['late_fee'])}',
                        if (_s(x['status']).isNotEmpty) _s(x['status']),
                      ].join(' · '),
                      style: TextStyle(color: late ? C.bad : C.muted, fontSize: 12.5)),
                ]),
              ),
            ]),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final d = _d;
    if (d == null) {
      return Center(child: _err != null ? Text(_err!, style: const TextStyle(color: C.muted)) : const CircularProgressIndicator());
    }
    final late = _list(d['late']), due = _list(d['due']);
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        Glass(child: Text(_s(d['text']), style: const TextStyle(fontSize: 15, height: 1.35))),
        const SizedBox(height: 12),
        if ((d['clients'] ?? 0) == 0)
          const Glass(
              child: Text('Pehla client jodiye: Clients > "Naya client" (GSTIN se). Ya Hoola se boliye: '
                  '"Sharma Traders, GSTIN 27..., monthly client jodo".', style: TextStyle(color: C.muted))),
        if (late.isNotEmpty) ...[Text('Late', style: display(15)), const SizedBox(height: 8), for (final x in late) _row(x, true)],
        if (due.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('Aane wale', style: display(15)),
          const SizedBox(height: 8),
          for (final x in due) _row(x, false)
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- Clients
class _ClientsTab extends StatefulWidget {
  const _ClientsTab({required this.app});
  final Santosh app;
  @override
  State<_ClientsTab> createState() => _ClientsTabState();
}

class _ClientsTabState extends State<_ClientsTab> with _GstLive {
  @override
  Santosh get app => widget.app;
  List<Map<String, dynamic>> _c = [];

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final c = await app.api!.gstClients();
      if (mounted) setState(() => _c = c);
    } catch (_) {}
  }

  Future<void> _add() async {
    final name = TextEditingController(), g = TextEditingController(), aato = TextEditingController(),
        user = TextEditingController(), cn = TextEditingController(), ph = TextEditingController();
    var scheme = 'monthly';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => Padding(
          padding: EdgeInsets.fromLTRB(12, 12, 12, 12 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Glass(
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Naya client', style: display(17)),
                TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (firm)')),
                TextField(
                    controller: g,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(labelText: 'GSTIN (15 akshar)')),
                TextField(
                    controller: aato,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Pichhle saal ka turnover (₹)')),
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: [
                  for (final s in const ['monthly', 'qrmp', 'composition'])
                    ChoiceChip(label: Text(s), selected: scheme == s, onSelected: (_) => setS(() => scheme = s)),
                ]),
                TextField(
                    controller: user,
                    decoration: const InputDecoration(labelText: 'Portal username (password nahi)', helperText: 'Password Hoola kabhi nahi rakhta')),
                TextField(controller: cn, decoration: const InputDecoration(labelText: 'Contact naam')),
                TextField(controller: ph, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Contact phone')),
                const SizedBox(height: 12),
                GradientButton(label: 'Save', icon: Icons.check_rounded, onTap: () => Navigator.pop(ctx, true)),
              ]),
            ),
          ),
        ),
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.gstSaveClient({
        'name': name.text.trim(),
        'gstin': g.text.trim(),
        'aato': double.tryParse(aato.text.replaceAll(',', '').trim()),
        'scheme': scheme,
        'portal_user': user.text.trim(),
        'contact_name': cn.text.trim(),
        'contact_phone': ph.text.trim(),
      });
      if (mounted) _snack(context, _s(r['say']));
      reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        GradientButton(label: 'Naya client', icon: Icons.person_add_alt_1_rounded, onTap: _add),
        const SizedBox(height: 12),
        for (final c in _c)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstClientPage(app: app, id: _s(c['id'])))),
              child: Glass(
                child: Row(children: [
                  const Icon(Icons.business_rounded, color: C.accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(c['name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                      Text('${_s(c['gstin'])} · ${_s(c['state_name'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                  Pill(_s(c['scheme'])),
                ]),
              ),
            ),
          ),
      ]);
}

class GstClientPage extends StatefulWidget {
  const GstClientPage({super.key, required this.app, required this.id, this.period = ''});
  final Santosh app;
  final String id;
  final String period;
  @override
  State<GstClientPage> createState() => _GstClientPageState();
}

class _GstClientPageState extends State<GstClientPage> with _GstLive {
  @override
  Santosh get app => widget.app;
  late String _period = widget.period.isNotEmpty ? widget.period : _periods().first;
  Map<String, dynamic>? _client;
  List<Map<String, dynamic>> _bills = [];
  List<Map<String, dynamic>> _rets = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final cs = await app.api!.gstClients();
      final c = cs.firstWhere((x) => x['id'] == widget.id, orElse: () => <String, dynamic>{});
      final b = await app.api!.gstBills(widget.id, period: _period);
      final r = await app.api!.gstReturns(client: widget.id);
      if (mounted) setState(() {
        _client = c;
        _bills = b;
        _rets = r;
      });
    } catch (_) {}
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f, {bool openReturn = false}) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted) _snack(context, _s(r['say']));
      final ret = r['return'];
      if (openReturn && ret is Map && mounted) {
        await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstReturnPage(app: app, id: _s(ret['id']))));
      }
      reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _upload(String what) async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom,
        allowedExtensions: const ['csv', 'xlsx', 'xls', 'json']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    await _run(() => what == '2b'
        ? app.api!.gstImport2b(widget.id, _period, f.name, f.bytes!)
        : app.api!.gstImport(widget.id, what, _period, f.name, f.bytes!));
  }

  Future<void> _draft() async {
    try {
      final r = await app.api!.gstDraft(widget.id, _period);
      if (!mounted) return;
      await showDialog(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Client ko message'),
          content: SelectableText(_s(r['draft'])),
          actions: [
            TextButton(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: _s(r['draft'])));
                  Navigator.pop(d);
                },
                child: const Text('Copy')),
          ],
        ),
      );
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _client ?? const {};
    final scheme = _s(c['scheme']);
    final out = _bills.where((b) => b['direction'] == 'out').toList();
    final inn = _bills.where((b) => b['direction'] == 'in').toList();
    final bad = _bills.where((b) => (b['problems'] as List?)?.isNotEmpty == true).length;
    final quarterEnd = ['03', '06', '09', '12'].contains(_period.split('-').last);
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(c['name']).isEmpty ? 'Client' : _s(c['name']))),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_s(c['gstin'])} · ${_s(c['state_name'])} · $scheme', style: const TextStyle(color: C.muted)),
              const SizedBox(height: 8),
              DropdownButton<String>(
                value: _period,
                isExpanded: true,
                items: [for (final p in _periods()) DropdownMenuItem(value: p, child: Text(_nicePeriod(p)))],
                onChanged: (v) {
                  if (v == null) return;
                  setState(() => _period = v);
                  reload();
                },
              ),
              Text('Sale ${out.length} · Kharid ${inn.length}${bad > 0 ? ' · $bad bill mein galti' : ''}',
                  style: TextStyle(color: bad > 0 ? C.warn : C.chip)),
            ]),
          ),
          const SizedBox(height: 12),
          Text('1. Bill', style: display(15)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: 'Sale register', icon: Icons.upload_file_rounded, onTap: _busy ? null : () => _upload('out')),
            GlassButton(label: 'Kharid register', icon: Icons.upload_file_rounded, onTap: _busy ? null : () => _upload('in')),
            GlassButton(label: 'Client se bill mango', icon: Icons.chat_rounded, onTap: _draft),
          ]),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Bill ki photo / PDF chat mein Hoola ko bhejiye: woh padhkar yahan daal dega.',
                style: TextStyle(color: C.faint, fontSize: 12)),
          ),
          if (scheme != 'composition') ...[
            const SizedBox(height: 14),
            Text('2. GSTR-2B aur milaan', style: display(15)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 8, children: [
              GlassButton(label: '2B upload', icon: Icons.download_rounded, onTap: _busy ? null : () => _upload('2b')),
              GlassButton(
                  label: 'Milaan dekho',
                  icon: Icons.compare_arrows_rounded,
                  onTap: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => GstReconPage(app: app, client: widget.id, period: _period)))),
            ]),
          ],
          const SizedBox(height: 14),
          Text('3. Return', style: display(15)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (scheme != 'composition')
              GradientButton(
                  label: scheme == 'qrmp' && !quarterEnd ? 'IFF banao' : 'GSTR-1 banao',
                  icon: Icons.description_rounded,
                  onTap: _busy ? null : () => _run(() => app.api!.gstPrepare(widget.id, _period, 'gstr1'), openReturn: true)),
            if (scheme == 'monthly' || (scheme == 'qrmp' && quarterEnd))
              GradientButton(
                  label: 'GSTR-3B banao',
                  icon: Icons.calculate_rounded,
                  onTap: _busy ? null : () => _run(() => app.api!.gstPrepare(widget.id, _period, 'gstr3b'), openReturn: true)),
            if (scheme == 'composition' && quarterEnd)
              GradientButton(
                  label: 'CMP-08 banao',
                  icon: Icons.calculate_rounded,
                  onTap: _busy ? null : () => _run(() => app.api!.gstPrepare(widget.id, _period, 'cmp08'), openReturn: true)),
          ]),
          const SizedBox(height: 14),
          for (final r in _rets.take(12))
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Press(
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstReturnPage(app: app, id: _s(r['id'])))),
                child: Glass(
                  child: Row(children: [
                    Expanded(child: Text('${_s(r['label'])} · ${_s(r['period_nice'])}', style: const TextStyle(fontWeight: FontWeight.w700))),
                    Pill(_s(r['status_label']), fg: _stCol(_s(r['status'])), bg: _stCol(_s(r['status'])).withOpacity(.16)),
                  ]),
                ),
              ),
            ),
          if (_bills.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('Bill (${_nicePeriod(_period)})', style: display(15)),
            const SizedBox(height: 6),
            for (final b in _bills.take(200))
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Glass(
                  padding: const EdgeInsets.all(10),
                  border: (b['problems'] as List?)?.isNotEmpty == true ? C.warn : null,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Icon(b['direction'] == 'out' ? Icons.north_east_rounded : Icons.south_west_rounded, size: 16, color: C.muted),
                      const SizedBox(width: 6),
                      Expanded(
                          child: Text('${_s(b['number'])} · ${_s(b['party_name']).isEmpty ? (_s(b['party_gstin']).isEmpty ? 'B2C' : _s(b['party_gstin'])) : _s(b['party_name'])}',
                              style: const TextStyle(fontWeight: FontWeight.w700))),
                      Text(rs((b['igst'] ?? 0) + (b['cgst'] ?? 0) + (b['sgst'] ?? 0)), style: const TextStyle(color: C.chip)),
                    ]),
                    for (final p in ((b['problems'] as List?) ?? const []).take(3))
                      Text('• $p', style: const TextStyle(color: C.warn, fontSize: 12)),
                  ]),
                ),
              ),
          ],
        ]),
      ),
    );
  }
}

class GstReconPage extends StatefulWidget {
  const GstReconPage({super.key, required this.app, required this.client, required this.period});
  final Santosh app;
  final String client, period;
  @override
  State<GstReconPage> createState() => _GstReconPageState();
}

class _GstReconPageState extends State<GstReconPage> {
  Map<String, dynamic>? _r;
  String? _err;
  final Map<String, String> _dec = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.gstReconcile(widget.client, widget.period);
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _save({bool apply = false}) async {
    try {
      if (_dec.isNotEmpty) {
        await widget.app.api!.gstIms({'client': widget.client, 'period': widget.period, 'decisions': _dec});
      }
      if (apply) {
        final r = await widget.app.api!.gstIms(
            {'client': widget.client, 'period': widget.period, 'apply': true, 'conversation_id': widget.app.conversationId ?? ''});
        if (mounted) _snack(context, _s(r['say']));
      } else if (mounted) {
        _snack(context, 'Faisla save');
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _sec(String title, String key, Color col, {bool ims = false}) {
    final rows = _list(_r?[key]);
    if (rows.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$title (${rows.length})', style: TextStyle(color: col, fontWeight: FontWeight.w800)),
        for (final x in rows.take(150))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${_s(x['supplier'])} · ${_s(x['number'])} · ${rs(x['tax'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                if (_s(x['note']).isNotEmpty) Text(_s(x['note']), style: const TextStyle(color: C.muted, fontSize: 12)),
                if (ims && _s(x['id']).isNotEmpty)
                  Wrap(spacing: 6, children: [
                    for (final a in const ['accept', 'pending', 'reject'])
                      ChoiceChip(
                        label: Text(a == 'accept' ? 'Accept' : a == 'pending' ? 'Pending' : 'Reject'),
                        selected: (_dec[_s(x['id'])] ?? _s(x['ims'])) == a,
                        onSelected: (_) => setState(() => _dec[_s(x['id'])] = a),
                      ),
                    if (_s(x['suggest']).isNotEmpty) Text('Hoola: ${_s(x['suggest'])}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
                  ]),
              ]),
            ),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: Text('2B milaan · ${_nicePeriod(widget.period)}')),
        body: Aurora(
          child: _r == null
              ? Center(child: _err != null ? Padding(padding: const EdgeInsets.all(20), child: Text(_err!)) : const CircularProgressIndicator())
              : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  Glass(child: Text(_s(_r!['say']), style: const TextStyle(height: 1.35))),
                  const SizedBox(height: 6),
                  Text(_s(_r!['ims_note']), style: const TextStyle(color: C.faint, fontSize: 12)),
                  _sec('Farak wale', 'mismatch', C.warn, ims: true),
                  _sec('Sirf 2B mein', 'only_2b', C.warn, ims: true),
                  _sec('Sirf books mein (supplier ne nahi dala)', 'only_books', C.bad),
                  _sec('Mil gaye', 'matched', C.ok, ims: true),
                  _sec('ITC nahi milega', 'ineligible', C.faint),
                  _sec('Reverse charge', 'rcm', C.muted),
                  const SizedBox(height: 16),
                  GlassButton(label: 'Faisla save', icon: Icons.save_rounded, onTap: () => _save()),
                  const SizedBox(height: 8),
                  GradientButton(label: 'Portal par IMS lagao', icon: Icons.computer_rounded, onTap: () => _save(apply: true)),
                ]),
        ),
      );
}

// ---------------------------------------------------------------- Returns
class _ReturnsTab extends StatefulWidget {
  const _ReturnsTab({required this.app});
  final Santosh app;
  @override
  State<_ReturnsTab> createState() => _ReturnsTabState();
}

class _ReturnsTabState extends State<_ReturnsTab> with _GstLive {
  @override
  Santosh get app => widget.app;
  List<Map<String, dynamic>> _r = [];

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final r = await app.api!.gstReturns();
      if (mounted) setState(() => _r = r);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        if (_r.isEmpty) const Glass(child: Text('Abhi koi return nahi. Client kholkar "GSTR-1 banao" dabaiye.', style: TextStyle(color: C.muted))),
        for (final r in _r)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstReturnPage(app: app, id: _s(r['id'])))),
              child: Glass(
                border: r['status'] == 'ready' ? C.accent : null,
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(r['client'])} · ${_s(r['label'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text('${_s(r['period_nice'])}${_s(r['arn']).isNotEmpty ? ' · ARN ${_s(r['arn'])}' : ''}',
                          style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                  Pill(_s(r['status_label']), fg: _stCol(_s(r['status'])), bg: _stCol(_s(r['status'])).withOpacity(.16)),
                ]),
              ),
            ),
          ),
      ]);
}

class GstReturnPage extends StatelessWidget {
  const GstReturnPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Return')),
        body: Aurora(child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [GstReturnView(app: app, id: id)])),
      );
}

/// Chat card for a return waiting for her Haan (event `gst_return`).
class GstReturnCard extends StatelessWidget {
  const GstReturnCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => GstReturnView(app: app, id: _s(v['return_id']), compact: true);
}

class GstDayCard extends StatelessWidget {
  const GstDayCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.receipt_long_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text('GST: ${_s(v['text'])}', style: const TextStyle(height: 1.3))),
          ]),
        ),
      );
}

class GstReturnView extends StatefulWidget {
  const GstReturnView({super.key, required this.app, required this.id, this.compact = false});
  final Santosh app;
  final String id;
  final bool compact;
  @override
  State<GstReturnView> createState() => _GstReturnViewState();
}

class _GstReturnViewState extends State<GstReturnView> with _GstLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _r;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    if (widget.id.isEmpty) return;
    try {
      final r = await app.api!.gstReturn(widget.id);
      if (mounted) setState(() => _r = r);
    } catch (_) {}
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.gstReturnAct(widget.id, action, {...body, 'conversation_id': app.conversationId ?? ''});
      if (r['return'] is Map && mounted) setState(() => _r = Map<String, dynamic>.from(r['return'] as Map));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      if (action == 'tax_message' && mounted) {
        await Clipboard.setData(ClipboardData(text: _s(r['draft'])));
        if (mounted) _snack(context, 'Client ka message copy ho gaya');
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _arn() async {
    final t = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('ARN'),
        content: TextField(controller: t, textCapitalization: TextCapitalization.characters, decoration: const InputDecoration(hintText: 'AA27...')),
        actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
      ),
    );
    if (ok == true) await _act('filed', {'arn': t.text.trim()});
  }

  Widget _kv(String k, String v, {Color? c}) => Padding(
        padding: const EdgeInsets.only(top: 3),
        child: Row(children: [
          Expanded(child: Text(k, style: const TextStyle(color: C.muted, fontSize: 13))),
          Text(v, style: TextStyle(fontWeight: FontWeight.w700, color: c ?? C.ink)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final r = _r;
    if (r == null) {
      return const Glass(child: Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator(strokeWidth: 2))));
    }
    final st = _s(r['status']);
    final s = Map<String, dynamic>.from((r['summary'] as Map?) ?? const {});
    final t = Map<String, dynamic>.from((r['tables'] as Map?) ?? const {});
    final checks = List<String>.from(((r['checks'] as List?) ?? const []).map((e) => '$e'));
    final kind = _s(r['kind']);
    return Glass(
      border: st == 'ready' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.receipt_long_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(r['client'])} · ${_s(s['label']).isNotEmpty ? _s(s['label']) : _s(r['label'])} · ${_s(r['period_nice'])}', style: display(15))),
          Pill(_s(r['status_label']), fg: _stCol(st), bg: _stCol(st).withOpacity(.16)),
        ]),
        if (_s(r['due']).isNotEmpty) Text('Due ${_s(r['due'])}${_s(r['arn']).isNotEmpty ? ' · ARN ${_s(r['arn'])}' : ''}',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        if (kind == 'gstr1') ...[
          _kv('B2B bill', '${s['b2b_invoices'] ?? 0} (${s['b2b_parties'] ?? 0} party)'),
          _kv('B2C bade (B2CL)', '${s['b2cl_invoices'] ?? 0}'),
          _kv('B2C chhote (lines)', '${s['b2cs_rows'] ?? 0}'),
          _kv('Credit / debit notes', '${s['notes'] ?? 0}'),
          _kv('Taxable', rs(s['txval'] ?? 0)),
          _kv('Kul tax', rs(s['tax'] ?? 0), c: C.accent),
        ],
        if (kind == 'gstr3b') ...[
          _kv('Tax (3.1)', rs(s['liability'] ?? 0)),
          _kv('ITC (4C, sirf 2B wala)', rs(s['itc'] ?? 0), c: C.ok),
          if (!widget.compact) ...[
            _kv('4B(1) blocked 17(5)', rs(((t['4B1'] as Map?)?.values ?? const []).fold<num>(0, (a, b) => a + (b as num)))),
            _kv('4B(2) Rule 37 / other', rs(((t['4B2'] as Map?)?.values ?? const []).fold<num>(0, (a, b) => a + (b as num)))),
            _kv('RCM (3.1(d)) cash mein', rs(((t['3.1d'] as Map?)?['igst'] ?? 0) + ((t['3.1d'] as Map?)?['cgst'] ?? 0) + ((t['3.1d'] as Map?)?['sgst'] ?? 0))),
          ],
          if ((s['late_days'] ?? 0) > 0) _kv('Byaaj + late fee', '${rs(s['interest'] ?? 0)} + ${rs(s['late_fee'] ?? 0)}', c: C.bad),
          _kv('Cash mein bharna', rs(s['pay_total'] ?? 0), c: C.accent),
        ],
        if (kind == 'cmp08') ...[
          _kv('Turnover', rs(s['turnover'] ?? 0)),
          _kv('Tax (${s['rate'] ?? 1}%)', rs(s['tax'] ?? 0), c: C.accent),
        ],
        for (final c in checks.take(widget.compact ? 3 : 20))
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.info_outline_rounded, size: 15, color: C.warn),
              const SizedBox(width: 6),
              Expanded(child: Text(c, style: const TextStyle(color: C.chip, fontSize: 12.5))),
            ]),
          ),
        const SizedBox(height: 10),
        if (st == 'ready' || st == 'rejected')
          Row(children: [
            Expanded(child: GlassButton(label: 'Haan, theek hai', icon: Icons.check_rounded, color: C.ok, onTap: _busy ? null : () => _act('decide', {'approve': true}))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, color: C.bad, onTap: _busy ? null : () => _act('decide', {'approve': false}))),
          ]),
        if (st == 'approved')
          GradientButton(label: 'Portal par file ke liye taiyaar karo', icon: Icons.computer_rounded, onTap: _busy ? null : () => _act('file')),
        if (st == 'filing' || st == 'approved')
          TextButton.icon(onPressed: _busy ? null : _arn, icon: const Icon(Icons.verified_rounded, size: 18), label: const Text('File ho gaya: ARN daalo')),
        if (!widget.compact)
          Wrap(spacing: 8, children: [
            if (kind == 'gstr1' && r['has_json'] == true)
              TextButton.icon(onPressed: _busy ? null : () => _act('json'), icon: const Icon(Icons.file_download_rounded, size: 18), label: const Text('JSON + Excel')),
            if (kind != 'gstr1')
              TextButton.icon(onPressed: _busy ? null : () => _act('tax_message'), icon: const Icon(Icons.chat_rounded, size: 18), label: const Text('Client ko tax batao')),
          ]),
        if (widget.compact)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GstReturnPage(app: app, id: widget.id))),
                child: const Text('Poora dekho')),
          ),
        const Text('Final submit EVC OTP / DSC se aur tax ka challan client khud karega. Hoola paise nahi bharta.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Notices
class _NoticesTab extends StatefulWidget {
  const _NoticesTab({required this.app});
  final Santosh app;
  @override
  State<_NoticesTab> createState() => _NoticesTabState();
}

class _NoticesTabState extends State<_NoticesTab> with _GstLive {
  @override
  Santosh get app => widget.app;
  List<Map<String, dynamic>> _n = [];

  @override
  void initState() {
    super.initState();
    startLive();
  }

  @override
  void dispose() {
    stopLive();
    super.dispose();
  }

  @override
  Future<void> reload() async {
    try {
      final n = await app.api!.gstNotices(status: '');
      if (mounted) setState(() => _n = n);
    } catch (_) {}
  }

  Future<void> _draft(Map<String, dynamic> n) async {
    try {
      final r = await app.api!.gstNoticeAct(_s(n['id']), 'draft');
      if (!mounted) return;
      await showDialog(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('${_s(n['form'])} jawab (${_s(r['reply_form'])})'),
          content: SingleChildScrollView(child: SelectableText(_s(r['draft']))),
          actions: [
            TextButton(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: _s(r['draft'])));
                  Navigator.pop(d);
                },
                child: const Text('Copy')),
          ],
        ),
      );
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 40), children: [
        const Glass(
            child: Text('Notice aaya? PDF / photo chat mein Hoola ko bhejiye: woh client, form aur aakhri tareekh note karke jawab ka draft banayega.',
                style: TextStyle(color: C.muted))),
        const SizedBox(height: 10),
        for (final n in _n)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              border: n['status'] == 'open' ? C.warn : null,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${_s(n['client'])} · ${_s(n['form'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
                  Pill(_s(n['status'])),
                ]),
                Text(_s(n['what']), style: const TextStyle(color: C.chip, fontSize: 13)),
                Text('Jawab: ${_s(n['reply_form'])} · aakhri din ${_s(n['due_on'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                Wrap(spacing: 8, children: [
                  TextButton(onPressed: () => _draft(n), child: const Text('Jawab ka draft')),
                  if (n['status'] == 'open')
                    TextButton(
                        onPressed: () async {
                          await app.api!.gstNoticeAct(_s(n['id']), 'status', {'status': 'replied'});
                          reload();
                        },
                        child: const Text('Jawab de diya')),
                ]),
              ]),
            ),
          ),
      ]);
}
