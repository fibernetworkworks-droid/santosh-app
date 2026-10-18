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
