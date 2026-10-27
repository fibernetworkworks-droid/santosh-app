/// Profile > Mobile dukaan (v0.88): Hoola as a mobile recharge + repair shop's coworker.
/// Aaj (due today, late, parts, bills waiting for her, not collected, recharges ending), Repair (job cards with camera
/// photos, status, parts, the bill that waits for her Haan, ready draft, delivery, slip), Recharge (log what she recharged,
/// commission, reminder drafts), Warranty (by IMEI / phone / job), Niyam (prices, warranty days, GST, terms).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
double? _num(String t) => double.tryParse(t.trim().replaceAll(',', '').replaceAll('₹', '').trim());
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
String _iso(DateTime d) => '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

const _accessories = {
  'sim': 'SIM',
  'memory_card': 'Memory card',
  'cover': 'Cover',
  'charger': 'Charger',
  'cable': 'Cable',
  'earphone': 'Earphone',
  'box': 'Dabba',
  'back_cover': 'Back cover',
};
const _flow = ['diagnosing', 'waiting_customer', 'waiting_part', 'repairing', 'ready'];
const _word = {
  'received': 'Jama',
  'diagnosing': 'Jaanch',
  'waiting_customer': 'Graahak ki haan',
  'waiting_part': 'Part baaki',
  'repairing': 'Repair',
  'ready': 'Taiyaar',
  'delivered': 'De diya',
  'returned': 'Bina repair wapas',
  'cancelled': 'Cancel',
};

Color _col(String s) => switch (s) {
      'ready' => C.ok,
      'delivered' => C.teal,
      'returned' || 'cancelled' => C.faint,
      'waiting_part' || 'waiting_customer' => C.warn,
      _ => C.accentSoft,
    };

mixin _ShopLive<T extends StatefulWidget> on State<T> {
  Santosh get app;
  int _tick = -1;
  Future<void> reload();
  void _onApp() {
    if (app.mshopTick != _tick) {
      _tick = app.mshopTick;
      reload();
    }
  }

  void startLive() {
    _tick = app.mshopTick;
    app.addListener(_onApp);
    reload();
  }

  void stopLive() => app.removeListener(_onApp);
}

class MShopScreen extends StatelessWidget {
  const MShopScreen({super.key, required this.app});
  final Santosh app;

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 5,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: const Text('Mobile dukaan sahayak'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Aaj'),
              Tab(text: 'Repair'),
              Tab(text: 'Recharge'),
              Tab(text: 'Warranty'),
              Tab(text: 'Niyam'),
            ]),
          ),
          floatingActionButton: FloatingActionButton.extended(
            backgroundColor: C.accent,
            foregroundColor: C.onAccent,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Naya repair', style: TextStyle(fontWeight: FontWeight.w800)),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MShopNewJobPage(app: app))),
          ),
          body: Aurora(
            child: TabBarView(children: [
              _TodayTab(app: app),
              _JobsTab(app: app),
              _RechargeTab(app: app),
              _WarrantyTab(app: app),
              _RulesTab(app: app),
            ]),
          ),
        ),
      );
}

class MShopJobTile extends StatelessWidget {
  const MShopJobTile({super.key, required this.j, required this.app});
  final Map<String, dynamic> j;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final st = _s(j['status']);
    final cust = Map<String, dynamic>.from((j['customer'] as Map?) ?? const {});
    final late = j['late'] == true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MShopJobPage(app: app, id: _s(j['id'])))),
        child: Glass(
          border: late ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(_s(j['number']), style: const TextStyle(color: C.faint, fontWeight: FontWeight.w800, fontSize: 12)),
              const SizedBox(width: 8),
              Expanded(child: Text(_s(cust['name']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
              Pill(_word[st] ?? st, fg: _col(st), bg: _col(st).withOpacity(.16)),
            ]),
            const SizedBox(height: 3),
            Text('${_s(j['device'])} · ${_list(j['faults']).map((f) => f['label']).join(', ')}',
                maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.chip)),
            const SizedBox(height: 3),
            Row(children: [
              Icon(late ? Icons.warning_amber_rounded : Icons.event_rounded, size: 15, color: late ? C.bad : C.muted),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                    st == 'delivered'
                        ? 'Diya ${_s(j['delivered_on'])}${_s(j['warranty_nice']).isNotEmpty ? ' · warranty ${j['warranty_nice']}' : ''}'
                        : (late ? 'Der: ${_s(j['promised_nice'])}' : 'Wapsi ${_s(j['promised_nice'])}'),
                    style: TextStyle(color: late ? C.bad : C.muted, fontSize: 12.5)),
              ),
              if (_s((j['bill'] as Map?)?['status']) == 'pending') const Text('Bill: aapki haan', style: TextStyle(color: C.accent, fontSize: 12)),
              if ((j['waiting_days'] ?? 0) is num && (j['waiting_days'] ?? 0) >= 3)
                Text('  ${j['waiting_days']} din se taiyaar', style: const TextStyle(color: C.warn, fontSize: 12)),
            ]),
          ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- Aaj
class _TodayTab extends StatefulWidget {
  const _TodayTab({required this.app});
  final Santosh app;
  @override
  State<_TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends State<_TodayTab> with _ShopLive {
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
      final d = await app.api!.mshopToday();
      if (mounted) setState(() {
        _d = d;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Widget _sec(String t, List<Map<String, dynamic>> rows, Color c) => rows.isEmpty
      ? const SizedBox.shrink()
      : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(padding: const EdgeInsets.fromLTRB(4, 12, 4, 8), child: Text('$t (${rows.length})', style: TextStyle(color: c, fontWeight: FontWeight.w800))),
          for (final j in rows) MShopJobTile(j: j, app: app),
        ]);

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (d == null && _err == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
        if (d != null) ...[
          MShopDayCard(v: d, app: app, inScreen: true),
          _sec('Der ho gayi', _list(d['late']), C.bad),
          _sec('Aaj wapas dena hai', _list(d['due_today']), C.accent),
          _sec('Part ka intezaar', _list(d['waiting_part']), C.warn),
          _sec('Taiyaar, le nahi gaye', _list(d['unclaimed']), C.warn),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- Repair list
class _JobsTab extends StatefulWidget {
  const _JobsTab({required this.app});
  final Santosh app;
  @override
  State<_JobsTab> createState() => _JobsTabState();
}

class _JobsTabState extends State<_JobsTab> with _ShopLive {
  @override
  Santosh get app => widget.app;
  String _status = 'open';
  final _q = TextEditingController();
  List<Map<String, dynamic>>? _rows;

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
      final r = await app.api!.mshopJobs(status: _status, q: _q.text.trim());
      if (mounted) setState(() => _rows = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    const filters = {'open': 'Chalu', 'ready': 'Taiyaar', 'delivered': 'Diye gaye', 'all': 'Sab'};
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        TextField(
          controller: _q,
          decoration: const InputDecoration(hintText: 'Naam, phone, model ya IMEI', prefixIcon: Icon(Icons.search_rounded)),
          onSubmitted: (_) => reload(),
        ),
        const SizedBox(height: 8),
        Wrap(spacing: 8, children: [
          for (final f in filters.entries)
            ChoiceChip(
              label: Text(f.value),
              selected: _status == f.key,
              onSelected: (_) {
                setState(() {
                  _status = f.key;
                  _rows = null;
                });
                reload();
              },
            ),
        ]),
        const SizedBox(height: 10),
        if (_rows == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
        if (_rows != null && _rows!.isEmpty)
          const Padding(padding: EdgeInsets.all(30), child: Center(child: Text('Koi job nahi.', style: TextStyle(color: C.muted)))),
        for (final j in _rows ?? const <Map<String, dynamic>>[]) MShopJobTile(j: j, app: app),
      ]),
    );
  }
}

// ---------------------------------------------------------------- one job
class MShopJobPage extends StatefulWidget {
  const MShopJobPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<MShopJobPage> createState() => _MShopJobPageState();
}

class _MShopJobPageState extends State<MShopJobPage> with _ShopLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _j;
  bool _busy = false;
  Api get _api => app.api!;
  String get _conv => app.conversationId ?? '';

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
      final j = await _api.mshopJob(widget.id);
      if (mounted) setState(() => _j = j);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _photo(String kind, ImageSource src) async {
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 72, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      await _run(() => _api.mshopPhoto(widget.id, x.name.isEmpty ? 'phone.jpg' : x.name, bytes, kind: kind));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, String>?> _form(String title, List<(String, String, bool)> fields) async {
    final ctl = {for (final f in fields) f.$1: TextEditingController()};
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final f in fields)
              TextField(
                controller: ctl[f.$1],
                keyboardType: f.$3 ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
                decoration: InputDecoration(labelText: f.$2),
              ),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Theek')),
        ],
      ),
    );
    if (ok != true) return null;
    return {for (final e in ctl.entries) e.key: e.value.text.trim()};
  }

  Future<void> _slip() async {
    setState(() => _busy = true);
    try {
      final r = await _api.mshopAct(widget.id, 'slip', {'conversation_id': _conv});
      final f = Map<String, dynamic>.from((r['file'] as Map?) ?? const {});
      final url = _api.absolute(_s(f['url']));
      if (url.isNotEmpty) await Native.openExternal(url: url);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _sheet(Widget child) => showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => Padding(padding: EdgeInsets.fromLTRB(12, 12, 12, 12 + MediaQuery.of(context).viewInsets.bottom), child: child),
      );

  @override
  Widget build(BuildContext context) {
    final j = _j;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(j == null ? 'Repair' : 'Job ${_s(j['number'])}')),
      body: Aurora(child: j == null ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(onRefresh: reload, child: _body(j))),
    );
  }

  Widget _body(Map<String, dynamic> j) {
    final st = _s(j['status']);
    final cust = Map<String, dynamic>.from((j['customer'] as Map?) ?? const {});
    final closed = const {'delivered', 'returned', 'cancelled'}.contains(st);
    final bill = Map<String, dynamic>.from((j['bill'] as Map?) ?? const {});
    final photos = _list(j['photos']);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(cust['name']), style: display(19))),
            Pill(_word[st] ?? st, fg: _col(st), bg: _col(st).withOpacity(.16)),
          ]),
          if (_s(cust['phone']).isNotEmpty) Text(_s(cust['phone']), style: const TextStyle(color: C.muted)),
          const SizedBox(height: 6),
          Text(_s(j['device']), style: const TextStyle(fontWeight: FontWeight.w800)),
          if (_s(j['imei']).isNotEmpty)
            Text('IMEI ${j['imei']}${j['imei_ok'] == false ? '  (check digit galat)' : ''}',
                style: TextStyle(color: j['imei_ok'] == false ? C.warn : C.muted, fontSize: 12.5)),
          const SizedBox(height: 6),
          Text(_s(j['problem']), style: const TextStyle(color: C.chip)),
          Text(_list(j['faults']).map((f) => f['label']).join(' · '), style: const TextStyle(color: C.accentSoft, fontSize: 12.5)),
          if ((j['accessories'] as List?)?.isNotEmpty == true)
            Text('Saath mein: ${(j['accessories'] as List).map((a) => _accessories[a] ?? a).join(', ')}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(j['condition']).isNotEmpty) Text('Haalat: ${j['condition']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(j['proof']).isNotEmpty) Text('Saboot: ${j['proof']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 6),
          Text('Liya ${_s(j['received_on'])} · wapsi ${_s(j['promised_nice'])}${_s(j['estimate']).isNotEmpty ? ' · andaza ${j['estimate']}' : ''}',
              style: TextStyle(color: j['late'] == true ? C.bad : C.chip, fontSize: 13)),
          Text('Mila ${_s(j['paid'])}${_s(j['total']).isNotEmpty ? ' · bill ${j['total']} · baaki ${j['balance']}' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          if (_s(j['warranty_nice']).isNotEmpty) Text('Warranty ${j['warranty_nice']} tak', style: const TextStyle(color: C.ok)),
          if (_s(j['warranty_of']).isNotEmpty) const Text('Warranty claim (pichhla repair)', style: TextStyle(color: C.warn)),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Photo (${photos.length})', style: const TextStyle(fontWeight: FontWeight.w800))),
            IconButton(tooltip: 'Gallery se', onPressed: _busy ? null : () => _photo(closed ? 'out' : 'in', ImageSource.gallery),
                icon: const Icon(Icons.photo_library_rounded, color: C.muted)),
          ]),
          if (photos.isEmpty) const Text('Phone ki aage, peeche aur screen ki photo lijiye: warranty mein kaam aati hai.', style: TextStyle(color: C.muted, fontSize: 12.5)),
          if (photos.isNotEmpty)
            SizedBox(
              height: 96,
              child: ListView(scrollDirection: Axis.horizontal, children: [
                for (final p in photos)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: Stack(children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Image.network(_api.absolute(_s(p['url'])), headers: _api.authHeaders, width: 96, height: 96, fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(width: 96, height: 96, color: C.panel, child: const Icon(Icons.broken_image_rounded))),
                      ),
                      Positioned(
                        left: 4,
                        bottom: 4,
                        child: Pill(p['kind'] == 'out' ? 'Dete' : (p['kind'] == 'part' ? 'Part' : 'Aate'), fg: C.ink, bg: const Color(0x99000000)),
                      ),
                    ]),
                  ),
              ]),
            ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: 'Aate waqt', icon: Icons.photo_camera_rounded, onTap: _busy ? null : () => _photo('in', ImageSource.camera))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Dete waqt', icon: Icons.photo_camera_back_rounded, onTap: _busy ? null : () => _photo('out', ImageSource.camera))),
          ]),
        ]),
      ),
      if (bill.isNotEmpty) ...[
        const SizedBox(height: 12),
        MShopBillCard(key: ValueKey('jb${j['id']}${bill['status']}${bill['total']}'), v: {
          'job_id': j['id'], 'number': j['number'], 'customer': cust['name'], 'device': j['device'], 'paid': j['paid'], ...bill,
        }, app: app),
      ],
      if (!closed) ...[
        const Padding(padding: EdgeInsets.fromLTRB(4, 14, 4, 8), child: Text('Kaam kahan tak?', style: TextStyle(fontWeight: FontWeight.w800))),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final s in _flow)
            ChoiceChip(
              label: Text(_word[s]!),
              selected: st == s,
              onSelected: _busy || st == s ? null : (_) => _run(() => _api.mshopAct(widget.id, 'status', {'status': s, 'conversation_id': _conv})),
            ),
        ]),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(
              label: 'Part / labour',
              icon: Icons.build_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form('Part / labour', [
                        ('name', 'Part (display combo, battery...)', false),
                        ('price', 'Graahak se ₹', true),
                        ('cost', 'Aapko pada ₹', true),
                        ('warranty_days', 'Part ki warranty (din)', true),
                        ('labour', 'Labour ₹ (agar alag)', true),
                      ]);
                      if (f == null) return;
                      _run(() => _api.mshopAct(widget.id, 'part', {
                            'name': f['name'],
                            if (_num(f['price']!) != null) 'price': _num(f['price']!),
                            if (_num(f['cost']!) != null) 'cost': _num(f['cost']!),
                            if (int.tryParse(f['warranty_days']!) != null) 'warranty_days': int.parse(f['warranty_days']!),
                            if (_num(f['labour']!) != null) 'labour': _num(f['labour']!),
                          }));
                    }),
          GlassButton(label: 'Bill banao', icon: Icons.receipt_long_rounded, onTap: _busy ? null : () => _run(() => _api.mshopAct(widget.id, 'bill', {'conversation_id': _conv}))),
          GlassButton(
              label: 'Andaze ka message',
              icon: Icons.chat_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      try {
                        final r = await _api.mshopAct(widget.id, 'estimate_message');
                        if (_s(r['wa_link']).isNotEmpty) {
                          await Native.openExternal(url: _s(r['wa_link']));
                        } else {
                          await Clipboard.setData(ClipboardData(text: _s(r['text'])));
                          if (mounted) _snack(context, 'Copy ho gaya');
                        }
                      } catch (e) {
                        if (mounted) _snack(context, '$e');
                      }
                    }),
          GlassButton(label: 'Graahak ne haan kahi', icon: Icons.thumb_up_alt_rounded,
              onTap: _busy ? null : () => _run(() => _api.mshopAct(widget.id, 'customer_ok'))),
          GlassButton(
              label: 'Paise mile',
              icon: Icons.currency_rupee_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final f = await _form('Kitne paise mile?', [('amount', '₹', true)]);
                      final a = f == null ? null : _num(f['amount']!);
                      if (a != null && a > 0) _run(() => _api.mshopAct(widget.id, 'pay', {'amount': a, 'how': 'app'}));
                    }),
          if (st == 'ready' && bill['status'] == 'approved')
            GlassButton(
                label: '"Taiyaar hai" message',
                icon: Icons.send_rounded,
                onTap: () async {
                  try {
                    final card = await _api.mshopAct(widget.id, 'ready', {'conversation_id': _conv});
                    if (mounted) await _sheet(MShopReadyCard(v: card, app: app));
                  } catch (e) {
                    if (mounted) _snack(context, '$e');
                  }
                }),
          GlassButton(
              label: 'Tareekh badlo',
              icon: Icons.event_repeat_rounded,
              onTap: _busy
                  ? null
                  : () async {
                      final now = DateTime.now();
                      final d = await showDatePicker(context: context, initialDate: now.add(const Duration(days: 1)),
                          firstDate: DateTime(now.year, now.month, now.day), lastDate: now.add(const Duration(days: 120)));
                      if (d != null) _run(() => _api.mshopAct(widget.id, 'update', {'promised_on': _iso(d), 'force': true}));
                    }),
          GlassButton(label: 'Slip (PDF)', icon: Icons.picture_as_pdf_rounded, onTap: _busy ? null : _slip),
          GlassButton(label: 'Bina repair wapas', icon: Icons.undo_rounded, color: C.warn,
              onTap: _busy ? null : () => _run(() => _api.mshopAct(widget.id, 'status', {'status': 'returned'}))),
        ]),
        const SizedBox(height: 12),
        GradientButton(
            label: 'De diya',
            icon: Icons.check_circle_rounded,
            height: 48,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form('Dete waqt kitne mile?', [('amount', '₹ (baaki ${_s(j['balance'])})', true)]);
                    if (f == null) return;
                    final a = _num(f['amount']!);
                    _run(() => _api.mshopAct(widget.id, 'deliver', {if (a != null && a > 0) 'amount': a, 'conversation_id': _conv}));
                  }),
      ] else
        Padding(padding: const EdgeInsets.only(top: 12), child: GlassButton(label: 'Slip (PDF)', icon: Icons.picture_as_pdf_rounded, onTap: _busy ? null : _slip)),
      const SizedBox(height: 18),
      const Text('Hisaab (log)', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final l in _list(j['log']).reversed)
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text('${_s(l['at']).replaceFirst('T', ' ').split('+').first}  ${_s(l['what'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ),
    ]);
  }
}

// ---------------------------------------------------------------- new job
class MShopNewJobPage extends StatefulWidget {
  const MShopNewJobPage({super.key, required this.app});
  final Santosh app;
  @override
  State<MShopNewJobPage> createState() => _MShopNewJobPageState();
}

class _MShopNewJobPageState extends State<MShopNewJobPage> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _brand = TextEditingController();
  final _model = TextEditingController();
  final _imei = TextEditingController();
  final _problem = TextEditingController();
  final _condition = TextEditingController();
  final _estimate = TextEditingController();
  final _advance = TextEditingController();
  final _proof = TextEditingController();
  final Set<String> _faults = {};
  final Set<String> _acc = {'sim'};
  List<Map<String, dynamic>> _allFaults = const [];
  String _promised = '';
  Map<String, dynamic>? _check;
  bool _busy = false;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    _api.mshopSettings().then((s) {
      if (mounted) setState(() => _allFaults = _list(s['faults']));
    }).catchError((_) {});
  }

  Map<String, dynamic> _body({bool force = false}) => {
        'name': _name.text.trim(),
        'phone': _phone.text.trim(),
        'brand': _brand.text.trim(),
        'model': _model.text.trim(),
        'imei': _imei.text.trim(),
        'problem': _problem.text.trim(),
        'faults': _faults.toList(),
        'accessories': _acc.toList(),
        'condition': _condition.text.trim(),
        'promised_on': _promised,
        if (_num(_estimate.text) != null) 'estimate': _num(_estimate.text),
        if (_num(_advance.text) != null) 'advance': _num(_advance.text),
        'proof': _proof.text.trim(),
        'force': force,
        'conversation_id': widget.app.conversationId ?? '',
      };

  Future<void> _doCheck() async {
    setState(() => _busy = true);
    try {
      final r = await _api.mshopCheck(_body());
      if (mounted) setState(() => _check = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _save({bool force = false}) async {
    if (_problem.text.trim().isEmpty) {
      _snack(context, 'Kya kharabi hai, likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await _api.mshopNewJob(_body(force: force));
      if (!mounted) return;
      if (r['saved'] == true) {
        _snack(context, _s(r['say']));
        final id = _s((r['job'] as Map?)?['id']);
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => MShopJobPage(app: widget.app, id: id)));
        return;
      }
      setState(() => _check = Map<String, dynamic>.from((r['check'] as Map?) ?? const {}));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final ck = _check;
    final probs = List<String>.from((ck?['problems'] as List?) ?? const []);
    final notes = List<String>.from((ck?['notes'] as List?) ?? const []);
    final legal = probs.any((p) => p.contains('kanoonan'));
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Naya repair')),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
          Glass(
            child: Column(children: [
              TextField(controller: _name, decoration: const InputDecoration(labelText: 'Graahak ka naam')),
              TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone')),
              Row(children: [
                Expanded(child: TextField(controller: _brand, decoration: const InputDecoration(labelText: 'Company (Redmi, Samsung...)'))),
                const SizedBox(width: 8),
                Expanded(child: TextField(controller: _model, decoration: const InputDecoration(labelText: 'Model'))),
              ]),
              TextField(controller: _imei, keyboardType: TextInputType.number, maxLength: 15,
                  decoration: const InputDecoration(labelText: 'IMEI (*#06# dabakar)', counterText: '')),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: _problem, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Kya kharabi hai (graahak ke shabdon mein)')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 4, children: [
                for (final f in _allFaults)
                  FilterChip(
                    label: Text(_s(f['label'])),
                    selected: _faults.contains(f['id']),
                    onSelected: (v) => setState(() => v ? _faults.add(_s(f['id'])) : _faults.remove(f['id'])),
                  ),
              ]),
              if (_faults.contains('unlock'))
                TextField(controller: _proof, decoration: const InputDecoration(labelText: 'Saboot ki phone inka hai (bill / dabba / ID dekha)')),
              const SizedBox(height: 8),
              const Text('Saath mein kya diya', style: TextStyle(color: C.muted)),
              Wrap(spacing: 6, children: [
                for (final a in _accessories.entries)
                  FilterChip(label: Text(a.value), selected: _acc.contains(a.key), onSelected: (v) => setState(() => v ? _acc.add(a.key) : _acc.remove(a.key))),
              ]),
              TextField(controller: _condition, decoration: const InputDecoration(labelText: 'Haalat (scratch, crack, dent)')),
              const Text('Phone ka password / pattern mat likhiye: Hoola use kabhi nahi rakhta.', style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
          const SizedBox(height: 12),
          Glass(
            child: Column(children: [
              GlassButton(
                label: _promised.isEmpty ? 'Wapsi ki tareekh (khaali = niyam se)' : 'Wapsi $_promised',
                icon: Icons.event_rounded,
                onTap: () async {
                  final now = DateTime.now();
                  final d = await showDatePicker(context: context, initialDate: now.add(const Duration(days: 1)),
                      firstDate: DateTime(now.year, now.month, now.day), lastDate: now.add(const Duration(days: 120)));
                  if (d != null) setState(() => _promised = _iso(d));
                },
              ),
              Row(children: [
                Expanded(child: TextField(controller: _estimate, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Andaza ₹'))),
                const SizedBox(width: 8),
                Expanded(child: TextField(controller: _advance, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Advance ₹'))),
              ]),
            ]),
          ),
          if (ck != null) ...[
            const SizedBox(height: 12),
            Glass(
              border: probs.isEmpty ? C.ok : (legal ? C.bad : C.warn),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(probs.isEmpty ? 'Niyam ke hisaab se theek' : 'Dhyaan dijiye',
                    style: TextStyle(fontWeight: FontWeight.w800, color: probs.isEmpty ? C.ok : (legal ? C.bad : C.warn))),
                for (final p in probs) Padding(padding: const EdgeInsets.only(top: 6), child: Text('• $p', style: const TextStyle(color: C.chip))),
                for (final n in notes) Padding(padding: const EdgeInsets.only(top: 6), child: Text('· $n', style: const TextStyle(color: C.muted, fontSize: 12.5))),
                if (_s(ck['estimate']).isNotEmpty) Text('Andaza: ${ck['estimate']}', style: const TextStyle(color: C.accent)),
                if (_s(ck['earliest_nice']).isNotEmpty)
                  Row(children: [
                    Expanded(child: Text('Sabse jaldi: ${ck['earliest_nice']}', style: const TextStyle(color: C.accent))),
                    TextButton(onPressed: () => setState(() => _promised = _s(ck['earliest'])), child: const Text('Yahi rakho')),
                  ]),
              ]),
            ),
          ],
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: GlassButton(label: 'Niyam se check', icon: Icons.rule_rounded, onTap: _busy ? null : _doCheck)),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Job save', height: 48, onTap: _busy ? null : () => _save())),
          ]),
          if (probs.isNotEmpty && !legal)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: GlassButton(label: 'Main maanti hoon, phir bhi save karo', color: C.warn, onTap: _busy ? null : () => _save(force: true)),
            ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- Recharge
class _RechargeTab extends StatefulWidget {
  const _RechargeTab({required this.app});
  final Santosh app;
  @override
  State<_RechargeTab> createState() => _RechargeTabState();
}

class _RechargeTabState extends State<_RechargeTab> with _ShopLive {
  @override
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  final _number = TextEditingController();
  final _amount = TextEditingController();
  final _validity = TextEditingController();
  final _name = TextEditingController();
  String _op = 'jio';
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
      final d = await app.api!.mshopRecharges();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _add() async {
    final a = _num(_amount.text);
    if (a == null || a <= 0 || _number.text.trim().length < 10) {
      _snack(context, 'Number aur rakam likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await app.api!.mshopAddRecharge({
        'number': _number.text.trim(),
        'amount': a,
        'operator': _op,
        if (int.tryParse(_validity.text.trim()) != null) 'validity_days': int.parse(_validity.text.trim()),
        'name': _name.text.trim(),
      });
      if (mounted) _snack(context, _s(r['say']));
      for (final c in [_number, _amount, _validity, _name]) {
        c.clear();
      }
      await reload();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final day = Map<String, dynamic>.from((d?['day'] as Map?) ?? const {});
    return RefreshIndicator(
      onRefresh: reload,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Recharge kiya? Likh lijiye', style: TextStyle(fontWeight: FontWeight.w800)),
            const Text('Recharge aap apne Jio POS Plus / Airtel Mitra / Vi app mein karti hain; Hoola khatam hone se pehle graahak ko yaad dilane ka draft banata hai.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
            TextField(controller: _number, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Mobile number')),
            Row(children: [
              Expanded(child: TextField(controller: _amount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: '₹ Rakam'))),
              const SizedBox(width: 8),
              Expanded(child: TextField(controller: _validity, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Validity (din)'))),
            ]),
            TextField(controller: _name, decoration: const InputDecoration(labelText: 'Naam (optional)')),
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: [
              for (final o in const {'jio': 'Jio', 'airtel': 'Airtel', 'vi': 'Vi', 'bsnl': 'BSNL'}.entries)
                ChoiceChip(label: Text(o.value), selected: _op == o.key, onSelected: (_) => setState(() => _op = o.key)),
            ]),
            const SizedBox(height: 10),
            GradientButton(label: 'Likh lo', height: 46, onTap: _busy ? null : _add),
          ]),
        ),
        if (d != null) ...[
          const SizedBox(height: 12),
          Glass(
            child: Text('Aaj: ${day['count'] ?? 0} recharge · ${_s(day['amount'])} · commission ${_s(day['commission'])}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
          if (_list(d['due']).isNotEmpty) ...[
            const Padding(padding: EdgeInsets.fromLTRB(4, 14, 4, 6), child: Text('Plan khatam hone wala: yaad dilaiye', style: TextStyle(fontWeight: FontWeight.w800, color: C.accent))),
            for (final r in _list(d['due']))
              Glass(
                margin: const EdgeInsets.only(bottom: 8),
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${_s(r['name']).isEmpty ? _s(r['number']) : r['name']} · ${_s(r['operator'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text('${_s(r['nice'])} ko khatam · pichhla ${_s(r['last_amount'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    ]),
                  ),
                  r['reminded'] == true
                      ? const Pill('Bheja', fg: C.ok)
                      : TextButton(
                          onPressed: () async {
                            await Native.openExternal(url: _s(r['wa_link']));
                            try {
                              await app.api!.mshopRechargeAct(_s(r['id']), 'reminded');
                            } catch (_) {}
                            await reload();
                          },
                          child: const Text('WhatsApp')),
                ]),
              ),
          ],
          const Padding(padding: EdgeInsets.fromLTRB(4, 14, 4, 6), child: Text('Haal ke recharge', style: TextStyle(fontWeight: FontWeight.w800))),
          for (final r in _list(d['recent']))
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('${_s(r['amount'])} · ${_s(r['operator'])} · ${_s(r['number'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${_s(r['day'])}${_s(r['expires_on']).isNotEmpty ? ' · khatam ${r['expires_on']}' : ''} · commission ${_s(r['commission'])}',
                  style: const TextStyle(fontSize: 12)),
              trailing: IconButton(
                icon: const Icon(Icons.remove_circle_outline_rounded, color: C.faint),
                onPressed: () async {
                  try {
                    await app.api!.mshopRechargeAct(_s(r['id']), 'void');
                    await reload();
                  } catch (e) {
                    if (context.mounted) _snack(context, '$e');
                  }
                },
              ),
            ),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------- Warranty
class _WarrantyTab extends StatefulWidget {
  const _WarrantyTab({required this.app});
  final Santosh app;
  @override
  State<_WarrantyTab> createState() => _WarrantyTabState();
}

class _WarrantyTabState extends State<_WarrantyTab> {
  final _q = TextEditingController();
  Map<String, dynamic>? _r;

  Future<void> _find() async {
    if (_q.text.trim().isEmpty) return;
    try {
      final r = await widget.app.api!.mshopWarranty(_q.text.trim());
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Row(children: [
          Expanded(
            child: TextField(controller: _q, decoration: const InputDecoration(hintText: 'IMEI, phone number ya job no.'), onSubmitted: (_) => _find()),
          ),
          IconButton(onPressed: _find, icon: const Icon(Icons.search_rounded, color: C.accent)),
        ]),
        const SizedBox(height: 6),
        const Text('Second-hand phone asli hai ya chori ka: "KYM <IMEI>" SMS 14422 par bhejiye (DoT / Sanchar Saathi).',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
        if (_r != null) ...[
          const SizedBox(height: 12),
          Glass(child: Text(_s(_r!['say']), style: const TextStyle(fontWeight: FontWeight.w700))),
          const SizedBox(height: 8),
          for (final j in _list(_r!['found'])) MShopJobTile(j: j, app: widget.app),
        ],
      ]);
}

// ---------------------------------------------------------------- Niyam
class _RulesTab extends StatefulWidget {
  const _RulesTab({required this.app});
  final Santosh app;
  @override
  State<_RulesTab> createState() => _RulesTabState();
}

class _RulesTabState extends State<_RulesTab> {
  Map<String, dynamic>? _st;
  final _shop = TextEditingController();
  final _gstin = TextEditingController();
  final _perDay = TextEditingController();
  final _unclaimed = TextEditingController();
  final _remind = TextEditingController();
  final _morning = TextEditingController();
  final _terms = TextEditingController();
  final _template = TextEditingController();
  final _rules = TextEditingController();
  final Map<String, TextEditingController> _price = {}, _warranty = {}, _days = {}, _comm = {};
  bool _gst = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  TextEditingController _c(Map<String, TextEditingController> m, String k, dynamic v) =>
      m.putIfAbsent(k, () => TextEditingController())..text = v == null ? '' : (v is num && v == v.roundToDouble() ? '${v.round()}' : '$v');

  Future<void> _load() async {
    try {
      final s = await widget.app.api!.mshopSettings();
      if (!mounted) return;
      final prices = Map<String, dynamic>.from((s['prices'] as Map?) ?? const {});
      final w = Map<String, dynamic>.from((s['warranty'] as Map?) ?? const {});
      final fd = Map<String, dynamic>.from((s['fix_days'] as Map?) ?? const {});
      final cm = Map<String, dynamic>.from((s['commission'] as Map?) ?? const {});
      setState(() {
        _st = s;
        _shop.text = _s(s['shop_name']);
        _gstin.text = _s(s['gstin']);
        _gst = s['gst_on'] == true;
        _perDay.text = _s(s['jobs_per_day']);
        _unclaimed.text = _s(s['unclaimed_days']);
        _remind.text = _s(s['remind_days']);
        _morning.text = _s(s['morning_time']);
        _terms.text = _s(s['terms']);
        _template.text = _s(s['ready_template']);
        _rules.text = List<String>.from((s['rules'] as List?) ?? const []).join('\n');
        for (final f in _list(s['faults'])) {
          final id = _s(f['id']);
          _c(_price, id, prices[id]);
          _c(_warranty, id, w[id]);
          _c(_days, id, fd[id]);
        }
        for (final o in _list(s['operators'])) {
          _c(_comm, _s(o['id']), cm[o['id']]);
        }
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.mshopSaveSettings({
        'shop_name': _shop.text.trim(),
        'gstin': _gstin.text.trim(),
        'gst_on': _gst,
        'jobs_per_day': int.tryParse(_perDay.text.trim()) ?? 0,
        'unclaimed_days': int.tryParse(_unclaimed.text.trim()) ?? 30,
        'remind_days': int.tryParse(_remind.text.trim()) ?? 2,
        'morning_time': _morning.text.trim(),
        'terms': _terms.text.trim(),
        'ready_template': _template.text.trim(),
        'rules': _rules.text.split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
        'prices': {for (final e in _price.entries) e.key: _num(e.value.text)},
        'warranty': {for (final e in _warranty.entries) if (int.tryParse(e.value.text.trim()) != null) e.key: int.parse(e.value.text.trim())},
        'fix_days': {for (final e in _days.entries) if (int.tryParse(e.value.text.trim()) != null) e.key: int.parse(e.value.text.trim())},
        'commission': {for (final e in _comm.entries) e.key: _num(e.value.text)},
      });
      if (mounted) _snack(context, 'Niyam save');
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _small(TextEditingController? c, String label) => SizedBox(
        width: 70,
        child: TextField(controller: c, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: label, isDense: true)),
      );

  @override
  Widget build(BuildContext context) {
    final s = _st;
    if (s == null) return const Center(child: CircularProgressIndicator());
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(controller: _shop, decoration: const InputDecoration(labelText: 'Dukaan ka naam')),
          TextField(controller: _gstin, textCapitalization: TextCapitalization.characters, decoration: const InputDecoration(labelText: 'GSTIN (agar hai)')),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: _gst,
            onChanged: (v) => setState(() => _gst = v),
            title: const Text('Repair bill par GST 18% (SAC 998716)'),
          ),
          Wrap(spacing: 12, children: [
            _small(_perDay, 'Job / din'),
            _small(_unclaimed, 'Na le jaane ke din'),
            _small(_remind, 'Recharge yaad (din pehle)'),
          ]),
          TextField(controller: _morning, decoration: const InputDecoration(labelText: 'Subah ki list kab (HH:MM)')),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Kaam: daam, warranty, kitne din', style: TextStyle(fontWeight: FontWeight.w800)),
          for (final f in _list(s['faults']))
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Row(children: [
                Expanded(child: Text(_s(f['label']), style: const TextStyle(fontSize: 13))),
                _small(_price[_s(f['id'])], '₹'),
                const SizedBox(width: 6),
                _small(_warranty[_s(f['id'])], 'Warranty'),
                const SizedBox(width: 6),
                _small(_days[_s(f['id'])], 'Din'),
              ]),
            ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Recharge commission %', style: TextStyle(fontWeight: FontWeight.w800)),
          Wrap(spacing: 10, children: [for (final o in _list(s['operators'])) _small(_comm[_s(o['id'])], _s(o['label']))]),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(children: [
          TextField(controller: _terms, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'Slip par shartein')),
          TextField(controller: _template, minLines: 2, maxLines: 5,
              decoration: const InputDecoration(labelText: '"Taiyaar hai" message', helperText: '{name} {device} {work} {amount} {balance_line} {shop} {number}')),
          TextField(controller: _rules, minLines: 2, maxLines: 6, decoration: const InputDecoration(labelText: 'Apne niyam (ek line mein ek)')),
        ]),
      ),
      const SizedBox(height: 14),
      GradientButton(label: 'Niyam save karo', height: 50, onTap: _busy ? null : _save),
    ]);
  }
}

// ---------------------------------------------------------------- chat cards
/// The bill Hoola prepared: nothing reaches the customer until she says Haan (she can change the amount).
class MShopBillCard extends StatefulWidget {
  const MShopBillCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<MShopBillCard> createState() => _MShopBillCardState();
}

class _MShopBillCardState extends State<MShopBillCard> {
  late final TextEditingController _t = TextEditingController(
      text: (widget.v['total_paise'] as num?) == null ? '' : '${((widget.v['total_paise'] as num) / 100).round()}');
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final total = _num(_t.text);
      final orig = ((widget.v['total_paise'] as num?) ?? 0) / 100;
      final r = await widget.app.api!.mshopAct(_s(widget.v['job_id']), 'decide', {
        'approve': yes,
        if (yes && total != null && total != orig) 'total': total,
        'conversation_id': widget.app.conversationId ?? '',
      });
      final job = Map<String, dynamic>.from((r['job'] as Map?) ?? const {});
      final bill = Map<String, dynamic>.from((job['bill'] as Map?) ?? const {});
      widget.v.addAll(bill);
      if (mounted) _snack(context, _s(r['say']));
      final ready = r['ready'];
      if (yes && ready is Map && mounted) {
        await showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (_) => Padding(
            padding: EdgeInsets.fromLTRB(12, 12, 12, 12 + MediaQuery.of(context).viewInsets.bottom),
            child: MShopReadyCard(v: Map<String, dynamic>.from(ready), app: widget.app),
          ),
        );
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final st = _s(v['status']);
    final pending = st == 'pending' || st == 'needs_price' || st == 'rejected';
    return Glass(
      border: pending ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.receipt_long_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Bill: ${_s(v['number'])} ${_s(v['customer'])}', style: display(15.5))),
          if (st == 'approved') Pill('Pakka ${_s(v['total'])}', fg: C.ok),
          if (st == 'rejected') const Pill('Mana', fg: C.faint),
        ]),
        Text(_s(v['device']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        for (final l in _list(v['lines']))
          Row(children: [
            Expanded(child: Text(_s(l['what']), style: const TextStyle(color: C.chip))),
            Text('₹${((l['paise'] as num) / 100).toStringAsFixed(0)}'),
          ]),
        if ((v['gst_paise'] ?? 0) is num && (v['gst_paise'] as num) > 0)
          Row(children: [Expanded(child: Text(_s(v['gst_note']), style: const TextStyle(color: C.chip))), Text('₹${((v['gst_paise'] as num) / 100).toStringAsFixed(0)}')]),
        for (final w in List<String>.from((v['why'] as List?) ?? const [])) Text(w, style: const TextStyle(color: C.faint, fontSize: 12)),
        if (_s(v['paid']).isNotEmpty) Text('Advance / mila: ${v['paid']}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if (pending) ...[
          const SizedBox(height: 8),
          SizedBox(width: 160, child: TextField(controller: _t, keyboardType: TextInputType.number, decoration: const InputDecoration(prefixText: '₹ ', labelText: 'Kul'))),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Haan, yahi lo', height: 48, onTap: _busy ? null : () => _decide(true))),
          ]),
          const SizedBox(height: 4),
          Text('${widget.app.aName} graahak ko daam tabhi batayega jab aap haan kahengi.', style: const TextStyle(color: C.faint, fontSize: 11.5)),
        ],
      ]),
    );
  }
}

/// 'Phone taiyaar hai' with the approved amount + her UPI link: a draft she sends herself.
class MShopReadyCard extends StatefulWidget {
  const MShopReadyCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<MShopReadyCard> createState() => _MShopReadyCardState();
}

class _MShopReadyCardState extends State<MShopReadyCard> {
  late final TextEditingController _t = TextEditingController(text: _s(widget.v['text']));
  String get _phone => _s(widget.v['phone']);

  Future<void> _open(String how) async {
    final upi = _s(widget.v['upi_link']);
    final body = _t.text.trim() + (how == 'whatsapp' && upi.isNotEmpty ? '\nUPI: $upi' : '');
    final url = how == 'sms' ? 'sms:+91$_phone?body=${Uri.encodeComponent(body)}' : 'https://wa.me/91$_phone?text=${Uri.encodeComponent(body)}';
    await Native.openExternal(url: url);
    if (mounted) setState(() => widget.v['status'] = 'opened');
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    return Glass(
      border: _s(v['status']) == 'draft' ? C.ok : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.phone_android_rounded, color: C.ok, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Taiyaar: ${_s(v['customer'])} (${_s(v['number'])})', style: display(15.5))),
          if (_s(v['status']) == 'opened') const Pill('WhatsApp khola', fg: C.teal),
        ]),
        Text('Kul ${_s(v['amount'])} · baaki ${_s(v['balance'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 8),
        TextField(controller: _t, minLines: 2, maxLines: 6, decoration: const InputDecoration(labelText: 'Message (badal sakti hain)')),
        const SizedBox(height: 10),
        if (_phone.length == 10)
          Row(children: [
            Expanded(child: GradientButton(label: 'WhatsApp par bhejo', icon: Icons.send_rounded, height: 46, onTap: () => _open('whatsapp'))),
            const SizedBox(width: 8),
            GlassButton(label: 'SMS', onTap: () => _open('sms')),
          ])
        else
          GlassButton(
              label: 'Message copy karo',
              icon: Icons.copy_rounded,
              onTap: () {
                Clipboard.setData(ClipboardData(text: _t.text.trim()));
                _snack(context, 'Copy ho gaya');
              }),
        if (_s(v['upi_link']).isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('UPI link ke liye Employee > Naukri mein apni UPI ID daaliye.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        Text('${widget.app.aName} khud nahi bhejta: aap dabayengi tabhi jayega.', style: const TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
    );
  }
}

/// The morning list in chat (also the top of the Aaj tab).
class MShopDayCard extends StatelessWidget {
  const MShopDayCard({super.key, required this.v, required this.app, this.inScreen = false});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool inScreen;
  @override
  Widget build(BuildContext context) {
    final late = v['late'] is List ? (v['late'] as List).length : (v['late'] ?? 0);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.phone_iphone_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Aaj ki mobile dukaan', style: display(16))),
          if (late is num && late > 0) Pill('$late der', fg: C.bad),
        ]),
        const SizedBox(height: 8),
        Text(_s(v['text']), style: const TextStyle(color: C.chip, height: 1.4)),
        if (!inScreen)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MShopScreen(app: app))),
              child: const Text('Dukaan kholo'),
            ),
          ),
      ]),
    );
  }
}
