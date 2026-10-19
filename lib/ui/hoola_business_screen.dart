import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'hoola_cards.dart';

const _cats = {
  'isp': 'Internet / ISP', 'shop': 'Dukaan', 'pharmacy': 'Medical', 'clinic': 'Clinic', 'services': 'Services',
  'restaurant': 'Khana', 'education': 'Shiksha', 'other': 'Aur',
};

/// Businesses on Hoola: find one and complain / ask a quote / order through your avatar, and run your own business
/// counter (profile, price list, tickets, technicians, verified badge).
class HoolaBusinessScreen extends StatefulWidget {
  const HoolaBusinessScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaBusinessScreen> createState() => _HoolaBusinessScreenState();
}

class _HoolaBusinessScreenState extends State<HoolaBusinessScreen> {
  Map<String, dynamic>? _biz;
  List<Map<String, dynamic>> _tickets = [];
  List<Map<String, dynamic>> _mine = [];
  List<Map<String, dynamic>> _found = [];
  final _q = TextEditingController();

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  List<Map<String, dynamic>> _list(dynamic x) =>
      List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  Future<void> _load() async {
    try {
      final r = await app.api!.netBusiness();
      final f = await app.api!.netBusinesses(q: _q.text.trim());
      if (!mounted) return;
      setState(() {
        _biz = r['business'] is Map ? Map<String, dynamic>.from(r['business'] as Map) : null;
        _tickets = _list(r['tickets']);
        _mine = _list(r['my_tickets']);
        _found = f;
      });
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _contact(Map<String, dynamic> b, String kind) async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text({'complain': 'Shikayat', 'quote': 'Quote maangiye', 'order': 'Order'}[kind] ?? kind),
        content: TextField(controller: c, minLines: 2, maxLines: 6, decoration: const InputDecoration(hintText: 'Kya chahiye / kya problem hai?')),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    try {
      final r = await app.api!.netBusinessContact('@${b['handle']}', c.text.trim(), kind);
      _snack(kind == 'complain' ? 'Ticket ${r['ticket'] ?? ''} bana. ${r['eta'] ?? ''}' : 'Bhej diya; jawab chat mein aayega.');
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _setup() async {
    final b = _biz ?? {};
    final name = TextEditingController(text: b['name'] as String? ?? '');
    final area = TextEditingController(text: b['area'] as String? ?? '');
    final hours = TextEditingController(text: b['hours'] as String? ?? '');
    final about = TextEditingController(text: b['about'] as String? ?? '');
    final catalog = TextEditingController(text: (b['catalog'] as List? ?? const [])
        .map((e) => '${(e as Map)['item']} - ${e['price'] ?? ''}${(e['unit'] ?? '') != '' ? ' / ${e['unit']}' : ''}')
        .join('\n'));
    final webhook = TextEditingController();
    final secret = TextEditingController();
    var cat = b['category'] as String? ?? 'other';
    var public = b['public'] != false;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Mera business'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Business ka naam')),
              DropdownButton<String>(
                isExpanded: true,
                value: cat,
                items: [for (final e in _cats.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
                onChanged: (v) => set(() => cat = v ?? 'other'),
              ),
              TextField(controller: area, decoration: const InputDecoration(labelText: 'Area (jaise Akola, Pune)')),
              TextField(controller: hours, decoration: const InputDecoration(labelText: 'Samay (jaise Som-Shani 9 se 7)')),
              TextField(controller: about, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'Business ke baare mein')),
              TextField(controller: catalog, minLines: 3, maxLines: 10,
                  decoration: const InputDecoration(labelText: 'Price list (har line: cheez - daam / unit)')),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Public counter (koi bhi customer ka Hoola baat kar sake)'),
                value: public,
                onChanged: (v) => set(() => public = v),
              ),
              TextField(controller: webhook, decoration: const InputDecoration(labelText: 'Apna system webhook (optional, https://)')),
              TextField(controller: secret, decoration: const InputDecoration(labelText: 'Webhook secret (optional)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    final items = <Map<String, dynamic>>[];
    for (final line in catalog.text.split('\n')) {
      final m = RegExp(r'^(.+?)\s*[-:]\s*₹?\s*([\d.,]+)\s*(?:/\s*(.+))?$').firstMatch(line.trim());
      if (m != null) {
        items.add({'item': m.group(1)!.trim(), 'price': double.tryParse(m.group(2)!.replaceAll(',', '')), 'unit': (m.group(3) ?? '').trim()});
      }
    }
    try {
      await app.api!.netBusinessPut({
        'name': name.text.trim(), 'category': cat, 'area': area.text.trim(), 'hours': hours.text.trim(), 'about': about.text.trim(),
        'catalog': items, 'public': public,
        if (webhook.text.trim().isNotEmpty) 'webhook_url': webhook.text.trim(),
        if (secret.text.trim().isNotEmpty) 'webhook_secret': secret.text.trim(),
      });
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _verify() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Verified badge'),
        content: TextField(controller: c, textCapitalization: TextCapitalization.characters, decoration: const InputDecoration(labelText: 'GSTIN')),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.netBusinessVerify(c.text.trim());
      _snack(r['note'] as String? ?? 'Bhej diya');
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final b = _biz;
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Hoola Business'),
          backgroundColor: Colors.transparent,
          bottom: const TabBar(tabs: [Tab(text: 'Dhoondhiye'), Tab(text: 'Mera business')]),
        ),
        body: Aurora(
          child: TabBarView(children: [
            RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                TextField(
                  controller: _q,
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), hintText: 'ISP, medical, dukaan, area…'),
                  onSubmitted: (_) => _load(),
                ),
                const SizedBox(height: 8),
                for (final f in _found)
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      Row(children: [
                        Expanded(child: Text(f['name'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700))),
                        if (f['verified'] == true) const Text('🏢 verified', style: TextStyle(color: C.teal, fontSize: 12)),
                      ]),
                      Text('${_cats[f['category']] ?? ''} · ${f['area'] ?? ''} · @${f['handle']}', style: const TextStyle(color: C.muted, fontSize: 12)),
                      Wrap(spacing: 2, children: [
                        TextButton(onPressed: () => _contact(f, 'complain'), child: const Text('Shikayat')),
                        TextButton(onPressed: () => _contact(f, 'quote'), child: const Text('Quote')),
                        TextButton(onPressed: () => _contact(f, 'order'), child: const Text('Order')),
                      ]),
                    ]),
                  ),
                if (_mine.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  const Text('Meri shikayatein', style: TextStyle(fontWeight: FontWeight.w700)),
                  for (final t in _mine)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${t['number']} · ${t['business']}'),
                      subtitle: Text('${t['status']}${(t['note'] ?? '') != '' ? ' · ${t['note']}' : ''}'),
                    ),
                ],
              ]),
            ),
            RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                if (b == null) ...[
                  const Text('Apne business ka Hoola counter kholiye: customers ke Hoola shikayat, quote aur order seedha aapke Hoola se karenge; '
                      'shikayat par ticket number banta hai aur aapke apne system (jaise FNW Flow) ko bhi ja sakta hai.',
                      style: TextStyle(color: C.muted)),
                  const SizedBox(height: 12),
                  GradientButton(label: 'Business counter kholiye', icon: Icons.storefront_rounded, height: 48, onTap: _setup),
                ] else ...[
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(child: Text(b['name'] as String? ?? '', style: display(20))),
                        Text(b['verification'] == 'verified' ? '🏢 verified' : b['verification'] == 'requested' ? 'jaanch mein' : '',
                            style: const TextStyle(color: C.teal)),
                      ]),
                      Text('${_cats[b['category']] ?? ''} · ${b['area'] ?? ''} · ${b['hours'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                      Text('${(b['catalog'] as List? ?? const []).length} cheezein price list mein · ${b['public'] == true ? 'public' : 'band'}'
                          '${b['webhook'] == true ? ' · webhook jud gaya' : ''}', style: const TextStyle(color: C.faint, fontSize: 12)),
                      Row(children: [
                        TextButton(onPressed: _setup, child: const Text('Badliye')),
                        if (b['verification'] != 'verified' && b['verification'] != 'requested')
                          TextButton(onPressed: _verify, child: const Text('Verified badge maangiye')),
                      ]),
                    ]),
                  ),
                  const SizedBox(height: 12),
                  Text('Tickets (${_tickets.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
                  for (final t in _tickets) HoolaTicketCard(key: ValueKey(t['id']), v: t, app: app),
                ],
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
