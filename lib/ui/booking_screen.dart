import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../state.dart';
import 'glass.dart';

/// v0.113 Services and bookings: the quote's free slots, then the job card (on the way, extra work approved line by
/// line, proof photos, the bill made by code, warranty, reschedule). Every booking, extra-work "haan" and new time is
/// HER tap here; the avatar can only show the card.

String _s(dynamic v) => v == null ? '' : '$v';
double _d(dynamic v) => v is num ? v.toDouble() : (double.tryParse('$v') ?? 0);
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Map<String, dynamic> _m(dynamic x) => x is Map ? Map<String, dynamic>.from(x) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic x) =>
    List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

String _inr(dynamic v) {
  final x = _d(v);
  final whole = x.abs().floor();
  final paise = ((x.abs() - whole) * 100).round();
  var s = '$whole';
  if (s.length > 3) {
    final last = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final parts = <String>[];
    while (rest.length > 2) {
      parts.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) parts.insert(0, rest);
    s = '${parts.join(',')},$last';
  }
  return '${x < 0 ? '-' : ''}₹$s${paise > 0 ? '.${paise.toString().padLeft(2, '0')}' : ''}';
}

/// A slot (UTC iso) in her words: "aaj 4:00 pm", "kal 10:00 am", "25/10 11:00 am".
String slotSay(dynamic iso) {
  final t = DateTime.tryParse(_s(iso));
  if (t == null) return '';
  final l = t.toLocal();
  final now = DateTime.now();
  final d0 = DateTime(now.year, now.month, now.day);
  final d1 = DateTime(l.year, l.month, l.day);
  final diff = d1.difference(d0).inDays;
  final day = diff == 0 ? 'aaj' : (diff == 1 ? 'kal' : '${l.day}/${l.month}');
  final h = l.hour % 12 == 0 ? 12 : l.hour % 12;
  return '$day $h:${l.minute.toString().padLeft(2, '0')} ${l.hour < 12 ? 'am' : 'pm'}';
}

Future<String?> _askText(BuildContext context, String title, String hint, {String initial = '', bool number = false}) async {
  final c = TextEditingController(text: initial);
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: TextField(
          controller: c,
          minLines: 1,
          maxLines: number ? 1 : 4,
          keyboardType: number ? TextInputType.number : TextInputType.text,
          decoration: InputDecoration(hintText: hint)),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Theek hai')),
      ],
    ),
  );
  final t = c.text.trim();
  c.dispose();
  return ok == true ? t : null;
}

/// The job card part of a service deal (inside DealCard).
class JobPanel extends StatefulWidget {
  const JobPanel({super.key, required this.v, required this.app, required this.onFresh});
  final Map<String, dynamic> v;
  final Santosh app;
  final void Function(Map<String, dynamic>) onFresh;
  @override
  State<JobPanel> createState() => _JobPanelState();
}

class _JobPanelState extends State<JobPanel> {
  bool _busy = false;
  final Map<String, bool> _answers = {};

  Map<String, dynamic> get v => widget.v;
  Map<String, dynamic> get job => _m(v['job']);

  Future<void> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.netDealAct(_s(v['id']), action, body);
      final d = r['deal'];
      if (d is Map) widget.onFresh(Map<String, dynamic>.from(d));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _photo(ImageSource src) async {
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 75, maxWidth: 1600);
      if (x == null || !mounted) return;
      final stage = await showModalBottomSheet<String>(
        context: context,
        builder: (ctx) => SafeArea(
          child: Wrap(children: [
            for (final e in const {'before': 'Kaam se pehle', 'after': 'Kaam ke baad', 'intake': 'Jaise mila', 'proof': 'Saboot / bill'}.entries)
              ListTile(title: Text(e.value), onTap: () => Navigator.of(ctx).pop(e.key)),
          ]),
        ),
      );
      if (stage == null) return;
      setState(() => _busy = true);
      final bytes = await x.readAsBytes();
      final r = await widget.app.api!.netDealPhoto(_s(v['id']), x.name.isEmpty ? 'photo.jpg' : x.name, bytes, stage: stage);
      final d = r['deal'];
      if (d is Map) widget.onFresh(Map<String, dynamic>.from(d));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _estimate() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Extra kaam (graahak ki haan chahiye)'),
        content: TextField(
            controller: c,
            minLines: 2,
            maxLines: 6,
            decoration: const InputDecoration(hintText: 'Har line: kaam daam [GST%]\nCartridge 350 18')),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
        ],
      ),
    );
    final lines = <Map<String, dynamic>>[];
    for (final raw in c.text.split('\n')) {
      final m = RegExp(r'^(.*?)\s+(\d+(?:\.\d+)?)(?:\s+(\d+(?:\.\d+)?))?\s*$').firstMatch(raw.trim());
      if (m != null) {
        lines.add({'item': m.group(1)!.trim(), 'price': double.parse(m.group(2)!), 'gst_pct': double.tryParse(m.group(3) ?? '0') ?? 0});
      }
    }
    c.dispose();
    if (ok == true && lines.isNotEmpty) _act('estimate', {'lines': lines});
  }

  Future<void> _done() async {
    final sum = TextEditingController();
    final wd = TextEditingController(text: _s(_m(_m(v['quote'])['service'])['warranty_days']));
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kaam poora?'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: sum, decoration: const InputDecoration(labelText: 'Kya kiya (graahak ko dikhega)')),
          TextField(controller: wd, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Warranty (din)')),
          const SizedBox(height: 8),
          const Text('Bill code banayega: quote + jin extra kaam par haan aayi. Aur kuch nahi judta.',
              style: TextStyle(color: C.faint, fontSize: 12)),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Poora, bill bhejo')),
        ],
      ),
    );
    final body = {'summary': sum.text.trim(), 'warranty_days': int.tryParse(wd.text.trim())};
    sum.dispose();
    wd.dispose();
    if (ok == true) _act('done', body);
  }

  Widget _photos() {
    final ps = _l(job['photos']);
    if (ps.isEmpty) return const SizedBox.shrink();
    return SizedBox(
      height: 86,
      child: ListView(scrollDirection: Axis.horizontal, children: [
        for (final p in ps)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Column(children: [
              GestureDetector(
                onTap: () => showDialog(
                    context: context,
                    builder: (_) => Dialog(
                        child: Image.network(widget.app.api!.absolute(_s(p['url'])), headers: widget.app.api!.authHeaders))),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: Image.network(widget.app.api!.absolute(_s(p['url'])),
                      headers: widget.app.api!.authHeaders,
                      width: 64,
                      height: 64,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const SizedBox(width: 64, height: 64, child: Icon(Icons.broken_image_rounded))),
                ),
              ),
              Text({'before': 'pehle', 'after': 'baad', 'intake': 'mila', 'proof': 'saboot'}[_s(p['stage'])] ?? _s(p['stage']),
                  style: const TextStyle(fontSize: 10.5, color: C.muted)),
            ]),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final buyer = _s(v['role']) == 'buyer';
    final acts = List<String>.from((v['actions'] as List?) ?? const []);
    final extras = _l(job['extras']);
    final pending = extras.where((x) => _s(x['status']) == 'pending').toList();
    final bill = _m(job['bill']);
    final w = _m(job['warranty']);
    final offer = _m(job['offer']);
    final claim = _m(job['claim']);
    final rows = <Widget>[];
    if (_s(job['slot_say']).isNotEmpty) {
      rows.add(Row(children: [
        const Icon(Icons.event_available_rounded, size: 18, color: C.teal),
        const SizedBox(width: 6),
        Expanded(
            child: Text('${_s(job['slot_say'])}${_s(v['number']).isEmpty ? '' : ' · ${_s(v['number'])}'}',
                style: const TextStyle(fontWeight: FontWeight.w700))),
      ]));
    }
    if (!buyer && _s(job['address']).isNotEmpty) rows.add(Text('Pata: ${_s(job['address'])}', style: const TextStyle(fontSize: 12.5)));
    if (_s(job['eta']).isNotEmpty) rows.add(Text('Pahunchenge: ${slotSay(job['eta'])}', style: const TextStyle(color: C.teal, fontSize: 12.5)));
    if (extras.isNotEmpty) {
      rows.add(const Padding(
          padding: EdgeInsets.only(top: 6), child: Text('Extra kaam', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13))));
      for (final x in extras) {
        final st = _s(x['status']);
        rows.add(Row(children: [
          Expanded(
              child: Text('${_s(x['item'])} · ${_inr(_d(x['amount']) + _d(x['gst']))}${_s(x['note']).isEmpty ? '' : ' (${_s(x['note'])})'}',
                  style: const TextStyle(fontSize: 12.5))),
          if (buyer && st == 'pending' && acts.contains('approve'))
            Wrap(spacing: 4, children: [
              ChoiceChip(
                  label: const Text('Haan'),
                  selected: _answers[_s(x['id'])] == true,
                  onSelected: (_) => setState(() => _answers[_s(x['id'])] = true)),
              ChoiceChip(
                  label: const Text('Na'),
                  selected: _answers[_s(x['id'])] == false,
                  onSelected: (_) => setState(() => _answers[_s(x['id'])] = false)),
            ])
          else
            Pill({'pending': 'jawab baaki', 'yes': 'haan', 'no': 'na'}[st] ?? st,
                fg: st == 'yes' ? C.ok : (st == 'no' ? C.muted : C.warn)),
        ]));
      }
      if (buyer && pending.isNotEmpty && acts.contains('approve')) {
        final all = pending.every((x) => _answers.containsKey(_s(x['id'])));
        rows.add(Padding(
          padding: const EdgeInsets.only(top: 6),
          child: GradientButton(
              label: 'Jawab bhejo',
              icon: Icons.check_rounded,
              height: 46,
              onTap: _busy || !all
                  ? null
                  : () => _act('approve', {
                        'ids_yes': [for (final x in pending) if (_answers[_s(x['id'])] == true) _s(x['id'])],
                        'ids_no': [for (final x in pending) if (_answers[_s(x['id'])] == false) _s(x['id'])],
                      })),
        ));
      }
    }
    if (_l(job['photos']).isNotEmpty) {
      rows.add(const SizedBox(height: 6));
      rows.add(_photos());
    }
    if (bill.isNotEmpty) {
      rows.add(const Padding(
          padding: EdgeInsets.only(top: 6), child: Text('Bill', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13))));
      for (final l in _l(bill['lines'])) {
        rows.add(Row(children: [
          Expanded(child: Text('${_s(l['item'])}${l['waived'] == true ? ' (adjust)' : ''}', style: const TextStyle(fontSize: 12.5))),
          Text(_inr(_d(l['amount']) + _d(l['gst'])), style: const TextStyle(fontSize: 12.5)),
        ]));
      }
      rows.add(Row(children: [
        const Expanded(child: Text('Kul', style: TextStyle(fontWeight: FontWeight.w800))),
        Text(_inr(bill['total']), style: const TextStyle(fontWeight: FontWeight.w900, color: C.accent)),
      ]));
    }
    if (_s(job['summary']).isNotEmpty) rows.add(Text(_s(job['summary']), style: const TextStyle(fontSize: 12.5, color: C.muted)));
    if (_d(w['days']) > 0) {
      rows.add(Text('Warranty ${_s(w['days'])} din · ${_s(w['until'])} tak${_s(w['covers']).isEmpty ? '' : ' · ${_s(w['covers'])}'}',
          style: const TextStyle(color: C.ok, fontSize: 12.5)));
    }
    if (claim['open'] == true) rows.add(Text('Warranty shikayat: ${_s(claim['note'])}', style: const TextStyle(color: C.warn, fontSize: 12.5)));
    if (_s(job['revisit_say']).isNotEmpty) {
      rows.add(Text('Muft revisit: ${_s(job['revisit_say'])}', style: const TextStyle(color: C.teal, fontSize: 12.5)));
    }
    if (buyer && acts.contains('pick_slot')) {
      rows.add(const Padding(padding: EdgeInsets.only(top: 6), child: Text('Naya samay chuniye', style: TextStyle(fontWeight: FontWeight.w700))));
      rows.add(Wrap(spacing: 6, runSpacing: 6, children: [
        for (final s in List<String>.from((offer['slots'] as List?) ?? const []))
          ActionChip(label: Text(slotSay(s)), onPressed: _busy ? null : () => _act('pick_slot', {'slot': s})),
      ]));
    }
    final btn = <Widget>[];
    if (!buyer) {
      if (acts.contains('on_the_way')) {
        btn.add(GlassButton(
            label: 'Raste mein',
            icon: Icons.two_wheeler_rounded,
            onTap: _busy
                ? null
                : () async {
                    final r = await _askText(context, 'Kitni der mein pahunchenge?', 'minute (jaise 30)', number: true);
                    if (r != null) _act('on_the_way', {'eta_minutes': int.tryParse(r)});
                  }));
      }
      if (acts.contains('arrived')) btn.add(GlassButton(label: 'Pahunch gaye', icon: Icons.place_rounded, onTap: _busy ? null : () => _act('arrived')));
      if (acts.contains('estimate')) btn.add(GlassButton(label: 'Extra kaam', icon: Icons.build_rounded, onTap: _busy ? null : _estimate));
      if (acts.contains('photo')) {
        btn.add(GlassButton(label: 'Photo', icon: Icons.photo_camera_rounded, onTap: _busy ? null : () => _photo(ImageSource.camera)));
        btn.add(GlassButton(label: 'Gallery', icon: Icons.photo_library_rounded, onTap: _busy ? null : () => _photo(ImageSource.gallery)));
      }
      if (acts.contains('done')) btn.add(GradientButton(label: 'Kaam poora', icon: Icons.task_alt_rounded, height: 46, onTap: _busy ? null : _done));
      if (acts.contains('offer_slots')) {
        btn.add(GlassButton(label: 'Naya samay do', icon: Icons.schedule_rounded, onTap: _busy ? null : () => _act('offer_slots', {'purpose': 'resched'})));
      }
      if (acts.contains('warranty_slots')) {
        btn.add(GlassButton(
            label: 'Warranty visit ke samay', icon: Icons.schedule_rounded, onTap: _busy ? null : () => _act('offer_slots', {'purpose': 'warranty'})));
      }
      if (acts.contains('warranty_done')) {
        btn.add(GlassButton(
            label: 'Warranty kaam ho gaya',
            icon: Icons.verified_rounded,
            onTap: _busy
                ? null
                : () async {
                    final r = await _askText(context, 'Kya kiya?', 'Washer badla');
                    if (r != null) _act('warranty_done', {'summary': r});
                  }));
      }
    } else {
      if (acts.contains('resched')) {
        btn.add(GlassButton(
            label: 'Samay badlo',
            icon: Icons.schedule_rounded,
            onTap: _busy
                ? null
                : () async {
                    final r = await _askText(context, 'Samay badalna hai?', 'Kab theek rahega');
                    if (r != null) _act('resched', {'note': r});
                  }));
      }
      if (acts.contains('warranty')) {
        btn.add(GlassButton(
            label: 'Warranty shikayat',
            icon: Icons.report_rounded,
            onTap: _busy
                ? null
                : () async {
                    final r = await _askText(context, 'Kya dikkat phir aayi?', 'Do line mein');
                    if (r != null) _act('warranty', {'note': r});
                  }));
      }
    }
    if (rows.isEmpty && btn.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        ...rows,
        if (btn.isNotEmpty) ...[const SizedBox(height: 10), Wrap(spacing: 8, runSpacing: 8, children: btn)],
      ]),
    );
  }
}

/// DealsScreen > Booking: her bookings (both sides), a new booking, and (when she gives a service) hours + rate card.
class BookingTab extends StatefulWidget {
  const BookingTab({super.key, required this.app, required this.cardBuilder});
  final Santosh app;
  final Widget Function(Map<String, dynamic> deal, VoidCallback onChanged) cardBuilder;
  @override
  State<BookingTab> createState() => _BookingTabState();
}

class _BookingTabState extends State<BookingTab> {
  List<Map<String, dynamic>> _xs = [];
  Map<String, dynamic> _rules = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = await widget.app.api!.netBookings();
      Map<String, dynamic> r = {};
      try {
        r = await widget.app.api!.netServiceRules();
      } catch (_) {}
      if (!mounted) return;
      setState(() {
        _xs = b;
        _rules = r;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        _snack(context, '$e');
      }
    }
  }

  Future<void> _new() async {
    final to = TextEditingController();
    final what = TextEditingController();
    final when = TextEditingController();
    final area = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Booking / appointment'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: to, decoration: const InputDecoration(labelText: 'Kisse (plumber, clinic, garage...)')),
            TextField(controller: what, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Kya kaam', hintText: 'Nal neeche se tapak raha hai')),
            TextField(controller: when, decoration: const InputDecoration(labelText: 'Kab theek rahega', hintText: 'Kal subah')),
            TextField(controller: area, decoration: const InputDecoration(labelText: 'Ilaaka (pura pata booking par hi)', hintText: 'Kothrud')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Poochho')),
        ],
      ),
    );
    final body = {'to': to.text.trim(), 'what': what.text.trim(), 'when': when.text.trim(), 'area': area.text.trim()};
    for (final c in [to, what, when, area]) {
      c.dispose();
    }
    if (ok != true || _s(body['to']).isEmpty || _s(body['what']).isEmpty) return;
    try {
      final r = await widget.app.api!.netBook(body);
      if (mounted) _snack(context, _s(r['say']));
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _set(Map<String, dynamic> body) async {
    try {
      final r = await widget.app.api!.netServiceRulesPut(body);
      if (mounted) setState(() => _rules = {..._rules, ...r});
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _addService() async {
    final name = TextEditingController();
    final price = TextEditingController();
    final wd = TextEditingController(text: '30');
    var gst = 0.0;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Rate card mein kaam'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Kaam', hintText: 'Tap repair')),
            TextField(controller: price, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Daam (GST ke bina)')),
            TextField(controller: wd, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Warranty (din)')),
            Wrap(spacing: 6, children: [
              for (final g in const [0.0, 5.0, 18.0])
                ChoiceChip(label: Text('GST ${g.toInt()}%'), selected: gst == g, onSelected: (_) => set(() => gst = g)),
            ]),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne do')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
          ],
        ),
      ),
    );
    final item = {
      'name': name.text.trim(),
      'price': double.tryParse(price.text.trim()) ?? 0,
      'gst_pct': gst,
      'kind': 'service',
      'warranty_days': int.tryParse(wd.text.trim()),
    };
    for (final c in [name, price, wd]) {
      c.dispose();
    }
    if (ok != true || _s(item['name']).isEmpty) return;
    try {
      await widget.app.api!.netStockPut([item]);
      _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _settings() {
    final days = List<String>.from((_rules['days'] as List?) ?? const []);
    const dw = {'mon': 'Som', 'tue': 'Mangal', 'wed': 'Budh', 'thu': 'Guru', 'fri': 'Shukra', 'sat': 'Shani', 'sun': 'Ravi'};
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Meri seva (jab main kaam karti / karta hoon)', style: TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        Wrap(spacing: 4, runSpacing: 4, children: [
          for (final e in dw.entries)
            FilterChip(
                label: Text(e.value),
                selected: days.contains(e.key),
                onSelected: (x) => _set({'days': x ? [...days, e.key] : days.where((d) => d != e.key).toList()})),
        ]),
        Row(children: [
          TextButton(
              onPressed: () async {
                final r = await _askText(context, 'Kab se', 'HH:MM', initial: _s(_rules['open_at']));
                if (r != null) _set({'open_at': r});
              },
              child: Text('Khule: ${_s(_rules['open_at'])}')),
          TextButton(
              onPressed: () async {
                final r = await _askText(context, 'Kab tak', 'HH:MM', initial: _s(_rules['close_at']));
                if (r != null) _set({'close_at': r});
              },
              child: Text('Band: ${_s(_rules['close_at'])}')),
        ]),
        Text('Ek kaam: ${_s(_rules['slot_minutes'])} min · ek samay mein ${_s(_rules['capacity'])}', style: const TextStyle(fontSize: 12.5)),
        Wrap(spacing: 6, children: [
          for (final x in const [30, 60, 90, 120])
            ChoiceChip(label: Text('$x min'), selected: _d(_rules['slot_minutes']) == x, onSelected: (_) => _set({'slot_minutes': x})),
        ]),
        Wrap(spacing: 6, children: [
          for (final e in const {'their_place': 'Graahak ke ghar', 'my_place': 'Meri dukaan / clinic'}.entries)
            ChoiceChip(label: Text(e.value), selected: _s(_rules['at']) == e.key, onSelected: (_) => _set({'at': e.key})),
        ]),
        Row(children: [
          Expanded(child: Text('Visit charge: ${_inr(_rules['visit_fee'])}', style: const TextStyle(fontSize: 12.5))),
          TextButton(
              onPressed: () async {
                final r = await _askText(context, 'Visit charge (₹)', '200', number: true);
                if (r != null) _set({'visit_fee': double.tryParse(r) ?? 0});
              },
              child: const Text('Badlo')),
        ]),
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: const Text('Kaam hua to visit charge bill mein adjust'),
          value: _rules['visit_adjust'] != false,
          onChanged: (x) => _set({'visit_adjust': x}),
        ),
        const SizedBox(height: 6),
        const Text('Rate card', style: TextStyle(fontWeight: FontWeight.w700)),
        for (final x in _l(_rules['services']))
          Text('${_s(x['name'])} · ${_inr(x['price'])}${_d(x['gst_pct']) > 0 ? ' + GST ${_s(x['gst_pct'])}%' : ''}'
              '${x['warranty_days'] != null ? ' · warranty ${_s(x['warranty_days'])} din' : ''}',
              style: const TextStyle(fontSize: 12.5)),
        TextButton.icon(onPressed: _addService, icon: const Icon(Icons.add_rounded), label: const Text('Kaam jodo')),
        if ((_rules['free_slots'] as List?)?.isNotEmpty == true)
          Text('Agle khaali samay: ${(_rules['free_slots'] as List).take(4).map(slotSay).join(', ')}',
              style: const TextStyle(color: C.faint, fontSize: 12)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          GlassButton(label: 'Nayi booking / appointment', icon: Icons.event_rounded, onTap: _new),
          const SizedBox(height: 6),
          const Text('Sirf kaam, ilaaka aur samay jaata hai. Samay aap chunengi tabhi booking hoti hai, aur pata bhi tabhi.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          const SizedBox(height: 12),
          if (_loading) const Center(child: CircularProgressIndicator()),
          for (final d in _xs) Padding(padding: const EdgeInsets.only(bottom: 12), child: widget.cardBuilder(d, _load)),
          const SizedBox(height: 8),
          if (_rules.isNotEmpty) _settings(),
        ]),
      );
}
