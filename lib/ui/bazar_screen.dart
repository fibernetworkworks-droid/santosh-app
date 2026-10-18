import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// Santosh Bazar: all 159 packs with live status, linked app accounts, spend limits and delivery details.
class BazarScreen extends StatefulWidget {
  const BazarScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<BazarScreen> createState() => _BazarScreenState();
}

const _statusText = {
  'ready': 'Ready',
  'demo': 'Demo',
  'no_shop_yet': 'Dukaan jud rahi hai',
  'needs_link': 'Link karein',
  'not_configured': 'Jald aa raha',
  'core': 'Santosh mein',
  'unavailable': 'Abhi band',
};

class _BazarScreenState extends State<BazarScreen> {
  Map<String, dynamic>? _cat;
  List<Map<String, dynamic>> _apps = [];
  Map<String, dynamic>? _settings;
  String? _err;
  String _filter = '';
  int _seenTick = -1;
  final _order = TextEditingController();
  final _day = TextEditingController();
  final _pin = TextEditingController();
  final _addr = TextEditingController();
  final _phone = TextEditingController();

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.bazarLinkedTick != _seenTick) {
      _seenTick = app.bazarLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    _seenTick = app.bazarLinkedTick;
    try {
      final r = await Future.wait([app.api!.bazarCatalog(), app.api!.bazarApps(), app.api!.bazarSettings()]);
      if (!mounted) return;
      setState(() {
        _cat = r[0] as Map<String, dynamic>;
        _apps = r[1] as List<Map<String, dynamic>>;
        _settings = r[2] as Map<String, dynamic>;
        _order.text = _num(_settings!['cap_per_order_rupees']);
        _day.text = _num(_settings!['cap_per_day_rupees']);
        _pin.text = _settings!['pincode'] as String? ?? '';
        _addr.text = _settings!['address'] as String? ?? '';
        _phone.text = _settings!['phone'] as String? ?? '';
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    }
  }

  String _num(dynamic v) {
    final d = (v as num?)?.toDouble() ?? 0;
    return d == d.roundToDouble() ? d.toInt().toString() : d.toString();
  }

  Future<void> _save() async {
    try {
      await app.api!.saveBazarSettings({
        'cap_per_order_rupees': double.tryParse(_order.text.trim()) ?? 0,
        'cap_per_day_rupees': double.tryParse(_day.text.trim()) ?? 0,
        'pincode': _pin.text.trim(),
        'address': _addr.text.trim(),
        'phone': _phone.text.trim(),
      });
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Save ho gaya')));
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  /// Lines like "Atta, 53, kg" or "Haircut 150" -> items.
  List<Map<String, dynamic>> _parseItems(String text) {
    final out = <Map<String, dynamic>>[];
    for (final raw in text.split('\n')) {
      final line = raw.trim();
      if (line.isEmpty) continue;
      final m = RegExp(r'^(.+?)[,\s]+(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(?:[,/\s]+\s*(kg|g|l|ml|pc|pack|dozen|visit|month|session))?\s*$', caseSensitive: false)
          .firstMatch(line);
      if (m == null) continue;
      final name = m.group(1)!.trim().replaceAll(RegExp(r'[,\-]+$'), '').trim();
      out.add({'name': name, 'price_rupees': double.parse(m.group(2)!), 'unit': (m.group(3) ?? 'pc').toLowerCase(),
        'aliases': [name.toLowerCase().split(' ').first]});
    }
    return out;
  }

  Future<void> _addShop(BuildContext context) async {
    final shopPacks = ((_cat?['packs'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map))
        .where((p) => p['executor'] == 'shop').toList();
    if (shopPacks.isEmpty) return;
    String tpl = shopPacks.firstWhere((p) => p['pack_id'] == 'kirana-store', orElse: () => shopPacks.first)['pack_id'] as String;
    final name = TextEditingController();
    final phone = TextEditingController();
    final upi = TextEditingController();
    final city = TextEditingController();
    final pins = TextEditingController(text: _settings?['pincode'] as String? ?? '');
    final aliases = TextEditingController();
    final slots = TextEditingController(text: 'Aaj shaam 6-7, Kal subah 9-10');
    final items = TextEditingController(text: 'Atta, 53, kg\nTel, 145, l\nSakhar, 46, kg');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setD) => AlertDialog(
        title: const Text('Dukaan jodiye'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            DropdownButtonFormField<String>(
              value: tpl,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Dukaan ka prakaar'),
              items: [for (final p in shopPacks) DropdownMenuItem(value: p['pack_id'] as String, child: Text(p['name'] as String))],
              onChanged: (v) => setD(() => tpl = v ?? tpl),
            ),
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Dukaan ka naam')),
            TextField(controller: aliases, decoration: const InputDecoration(labelText: 'Log kaise bulate hain (jaise: Ramesh bhau)')),
            TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Maalik ka mobile')),
            TextField(controller: upi, decoration: const InputDecoration(labelText: 'Dukaan ka UPI ID (paise yahin jayenge)')),
            TextField(controller: city, decoration: const InputDecoration(labelText: 'Shehar')),
            TextField(controller: pins, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Pincode (comma se)')),
            TextField(controller: slots, decoration: const InputDecoration(labelText: 'Delivery samay (comma se)')),
            TextField(controller: items, minLines: 3, maxLines: 10,
                decoration: const InputDecoration(labelText: 'Saamaan: naam, daam, unit (har line ek)')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodiye')),
        ],
      )),
    );
    if (ok != true) return;
    List<String> csv(String t) => t.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    try {
      final shop = await app.api!.bazarCreateShop({
        'template_id': tpl, 'name': name.text.trim(), 'owner_phone': phone.text.trim(), 'upi_id': upi.text.trim(),
        'city': city.text.trim(), 'pincodes': csv(pins.text), 'aliases': csv(aliases.text), 'slots': csv(slots.text),
      });
      final list = _parseItems(items.text);
      if (list.isNotEmpty) await app.api!.bazarShopItems(shop['id'] as String, list);
      if (!context.mounted) return;
      await showDialog(context: context, builder: (ctx) => AlertDialog(
        title: Text('${shop['name']} jud gayi ✓'),
        content: SelectableText('${list.length} saamaan add hue.\n\nDukaan ka merchant token (dukaan wale ko dijiye, sirf ek baar dikhega):\n\n${shop['merchant_token']}'),
        actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Theek hai'))],
      ));
      _load();
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Color _color(String st) => switch (st) {
        'ready' || 'core' => C.ok,
        'demo' || 'needs_link' => C.warn,
        _ => C.muted,
      };

  @override
  Widget build(BuildContext context) {
    final packs = ((_cat?['packs'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).where((p) {
      if (_filter.isEmpty) return true;
      final f = _filter.toLowerCase();
      return '${p['name']} ${p['category']} ${p['kind']}'.toLowerCase().contains(f);
    }).toList();
    final byCat = <String, List<Map<String, dynamic>>>{};
    for (final p in packs) {
      byCat.putIfAbsent(p['category'] as String, () => []).add(p);
    }
    return Scaffold(
      appBar: AppBar(title: Text('Santosh Bazar · ${_cat?['total'] ?? 159} apps')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
          if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Apps jodiye', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 4),
              const Text('Ek baar login, phir Santosh aapke account se order karega. Har order se pehle aapse poochega.',
                  style: TextStyle(color: C.muted, fontSize: 12.5)),
              const SizedBox(height: 8),
              for (final a in _apps)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(a['name'] as String? ?? ''),
                  subtitle: Text(_statusText[a['status']] ?? a['status'] as String? ?? '', style: TextStyle(color: _color(a['status'] as String? ?? ''))),
                  trailing: switch (a['status']) {
                    'needs_link' => FilledButton(
                        onPressed: () async {
                          final err = await app.linkApp(a['pack_id'] as String);
                          if (err != null && context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
                        },
                        child: const Text('Link')),
                    'ready' => TextButton(
                        onPressed: () async {
                          await app.api!.bazarUnlink(a['pack_id'] as String);
                          _load();
                        },
                        child: const Text('Hatao')),
                    _ => null,
                  },
                ),
            ]),
          ),
          const SizedBox(height: 14),
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Kharch ki seema (auto-approve)', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 4),
              const Text('0 = har kharch par aapka tap. Seema ke andar sirf pehle approve kiye hue dukaan/biller ka order apne aap hoga. '
                  'Kisi insaan ko paise hamesha aapke tap aur UPI PIN se hi jayenge.', style: TextStyle(color: C.muted, fontSize: 12.5)),
              Row(children: [
                Expanded(child: TextField(controller: _order, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Ek order ₹ (max 5000)'))),
                const SizedBox(width: 10),
                Expanded(child: TextField(controller: _day, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Ek din ₹'))),
              ]),
              TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Mobile number (dukaan ke bill ke liye)')),
              TextField(controller: _pin, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Pincode (paas ki dukaan)')),
              TextField(controller: _addr, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Delivery address')),
              const SizedBox(height: 10),
              GradientButton(label: 'Save', height: 46, onTap: _save),
            ]),
          ),
          const SizedBox(height: 14),
          Glass(
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.add_business_rounded, color: C.accent),
              title: const Text('Dukaan jodiye', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Kirana, dairy, medical, tiffin… apni ya paas ki dukaan Santosh par laaiye'),
              onTap: () => _addShop(context),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), labelText: 'Dhoondhiye: bijli, kirana, phonepe, uber…'),
            onChanged: (v) => setState(() => _filter = v.trim()),
          ),
          const SizedBox(height: 8),
          if (_cat == null && _err == null) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
          for (final e in byCat.entries)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Glass(
                child: ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: Text('${e.key} · ${e.value.length}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  initiallyExpanded: _filter.isNotEmpty,
                  children: [
                    for (final p in e.value)
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(p['name'] as String? ?? ''),
                        subtitle: Text(p['kind'] as String? ?? '', style: const TextStyle(fontSize: 12)),
                        trailing: Pill(_statusText[p['status']] ?? '', fg: _color(p['status'] as String? ?? '')),
                      ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 14),
          const Text('Chat mein boliye: "MSEDCL ka bill bhar do", "Ramesh ke dukaan se 5 kilo atta", "Priya ko 500 bhejo PhonePe se", '
              '"Station ke liye Uber". Demo = test bill, asli paise nahi.', style: TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      ),
    );
  }
}
