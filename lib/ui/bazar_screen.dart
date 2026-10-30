import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';
import 'mcp_screen.dart';
import 'plugin_widgets.dart';
import 'publicapis_screen.dart';
import 'shopping_screen.dart';
import 'reels_screen.dart';
import 'motion_screen.dart';
import 'scroll_screen.dart';
import 'top_plugins.dart';
import 'tv_screen.dart';

/// Santosh Bazar: every pack with live status, linked app accounts, spend limits and delivery details.
class BazarScreen extends StatefulWidget {
  const BazarScreen({super.key, required this.app, this.embedded = false});
  final Santosh app;
  final bool embedded; // shown as the Connect tab (no back bar)
  @override
  State<BazarScreen> createState() => _BazarScreenState();
}

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
    BrandLogo.failed.clear();          // pull-to-refresh retries logos that failed earlier
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

  String _grp = '';

  Widget _chip(String label, String value) {
    final on = _grp == value;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Press(
        onTap: () => setState(() => _grp = value),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: on ? C.accent : const Color(0x17FFFFFF),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: on ? C.accent : const Color(0x29FFFFFF)),
          ),
          child: Text(label, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: on ? C.onAccent : C.ink)),
        ),
      ),
    );
  }

  bool _inGroup(Map<String, dynamic> p) => switch (_grp) {
        '' => true,
        'does' => levelGroup(p) == 'does' && p['executor'] != 'upi',
        'open' => p['executor'] == 'handoff',
        'sms' => p['executor'] == 'reader',
        _ => p['executor'] == _grp,
      };

  Future<void> _unlink(Map<String, dynamic> a) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('${a['name']} hatayein?'),
        content: const Text('Hoola is account se order nahi kar payega jab tak aap dobara link na karein.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nahi')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hatao', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    await app.api!.bazarUnlink(a['pack_id'] as String);
    _load();
  }

  Future<void> _link(String packId) async {
    final err = await app.linkApp(packId);
    if (err != null && mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
  }

  // v0.277 IndiaMART (and any no-login app): connected for everyone, nothing to link or unlink
  Widget _appAction(Map<String, dynamic> a) => a['no_login'] == true
      ? PluginAction(kind: a['status'] == 'ready' ? ActionKind.linked : ActionKind.soon,
          label: a['status'] == 'ready' ? 'Connected' : 'Abhi band hai')
      : switch (a['status'] as String? ?? '') {
        'ready' => PluginAction(kind: ActionKind.linked, label: 'Juda hai', onTap: () => _unlink(a)),
        'needs_link' => PluginAction(kind: ActionKind.add, label: 'Jodiye', onTap: () => _link(a['pack_id'] as String)),
        _ => const PluginAction(kind: ActionKind.soon, label: 'Jald aa raha'),
      };

  Widget _appCard(Map<String, dynamic> a) => PluginCard(
        name: a['name'] as String? ?? '',
        does: (a['does'] as String?)?.isNotEmpty == true ? a['does'] as String : 'Order, cart aur tracking Hoola se',
        logo: a['logo'] as String?,
        category: a['no_login'] == true ? 'Business & SMB' : 'Food & Dining',
        executor: 'mcp',
        badge: a['status'] == 'ready' ? 'LIVE' : null,
        badgeColor: C.ok,
        action: _appAction(a),
        onTap: () => _openSheet({...a, 'executor': 'mcp', 'category': 'Apps'}),
      );

  Widget? _sheetAction(Map<String, dynamic> p) {
    final st = p['status'] as String? ?? '';
    final ex = p['executor'] as String? ?? '';
    if (ex == 'mcp' && st == 'needs_link') {
      return PluginAction(kind: ActionKind.add, label: 'Jodiye', height: 46, onTap: () {
        Navigator.of(context).pop();
        _link(p['pack_id'] as String);
      });
    }
    if (ex == 'shop' && st == 'no_shop_yet') {
      return PluginAction(kind: ActionKind.add, label: 'Dukaan jodiye', height: 46, onTap: () {
        Navigator.of(context).pop();
        _addShop(context);
      });
    }
    if (st == 'ready' || st == 'core') {
      return const PluginAction(kind: ActionKind.linked, label: 'Taiyaar hai · Hoola se kahiye', height: 46);
    }
    if (st == 'demo') return const PluginAction(kind: ActionKind.soon, label: 'Abhi demo: asli bill jald', height: 46);
    if (st == 'not_connected') return const PluginAction(kind: ActionKind.soon, label: 'Main tab mein account jodiye', height: 46);
    return null;
  }

  void _openSheet(Map<String, dynamic> p) => showPluginSheet(context, p, action: _sheetAction(p), onSay: (t) async {
        final ok = await app.send(t);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? 'Chat mein bhej diya: "$t"' : 'Bhej nahi paya, dobara try kijiye')));
        }
      });

  @override
  Widget build(BuildContext context) {
    BrandLogo.base = app.api?.baseUrl ?? app.serverUrl;
    final all = ((_cat?['packs'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final packs = all.where((p) {
      if (!_inGroup(p)) return false;
      if (_filter.isEmpty) return true;
      final f = _filter.toLowerCase();
      return '${p['name']} ${p['category']} ${p['kind']} ${p['does'] ?? ''}'.toLowerCase().contains(f);
    }).toList();
    final byCat = <String, List<Map<String, dynamic>>>{};
    for (final p in packs) {
      byCat.putIfAbsent(p['category'] as String, () => []).add(p);
    }
    final total = _cat?['total'] ?? all.length;
    final list = RefreshIndicator(
        color: C.accent,
        onRefresh: _load,
        child: ListView(padding: EdgeInsets.fromLTRB(16, widget.embedded ? 18 : 8, 16, 120), children: [
          if (widget.embedded) ...[
            Text('Connectors', style: display(28)),
            const SizedBox(height: 4),
            Text('$total plugins · jodiye, Hoola inse kaam poora karega', style: const TextStyle(color: C.muted, fontSize: 13.5)),
            const SizedBox(height: 16),
          ],
          if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
          Glass(
            radius: 18,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
            child: TextField(
              style: const TextStyle(color: C.ink, fontSize: 15),
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded, color: C.muted), hintText: 'Plugin dhoondhiye: bijli, kirana, Uber…',
                  border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),
              onChanged: (v) => setState(() => _filter = v.trim()),
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              // v0.303 SAAF CONNECT: only groups that still have working plugins (handoffs, demo bills, empty shops are hidden)
              _chip('Sab', ''), _chip('Hoola karega', 'does'), _chip('SMS padhega', 'sms'),
              _chip('UPI', 'upi'), _chip('Cab', 'ride'), _chip('Food apps', 'mcp'),
            ]),
          ),
          const SizedBox(height: 18),
          if (_filter.isEmpty && _grp.isEmpty) ...[
            if (_cat != null && ((_cat!['top'] as List?) ?? const []).isNotEmpty) ...[
              TopPlugins(
                sections: List<Map<String, dynamic>>.from((_cat!['top'] as List).map((e) => Map<String, dynamic>.from(e as Map))),
                onOpen: _openSheet,
              ),
              const SizedBox(height: 20),
            ],
            const Caption('APNE ACCOUNTS CONNECT KAREIN'),
            PluginGrid(children: [
              for (final (i, a) in _apps.where((a) => a['custom'] != true).indexed) Stagger(index: i, child: _appCard(a)),
            ]),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.live_tv_rounded, color: C.accent),
                title: Text('Hoola TV · free live channels', style: display(15.5)),
                subtitle: const Text('Doordarshan, Sansad TV, news, bhakti, music · phone pe ya TV pe'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TvScreen())),
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.slow_motion_video_rounded, color: C.accentSoft),
                title: Text('Hoola Reels · saved reels', style: display(15.5)),
                subtitle: const Text('Kisi bhi reel ko Share → Hoola: save, yaad, shopping, family, ye sach hai?'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SavedReelsScreen())),
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.insights_rounded, color: C.teal),
                title: Text('Scroll report · reel ki aadat', style: display(15.5)),
                subtitle: const Text('Kitni der reels, kab, kaunsi app, raat mein kitna · aap kya dekhte ho'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ScrollScreen())),
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.movie_creation_rounded, color: C.accent2),
                title: Text('Hoola Motion · reel banao', style: display(15.5)),
                subtitle: const Text('Dukaan ki reel, recipe, logo intro, Diwali offer: animated video, WhatsApp / Insta / YouTube ke liye'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MotionScreen())),
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.hub_rounded, color: C.teal),
                title: Text('Apps · 1,600+', style: display(15.5)),
                subtitle: const Text('Slack, Notion, Jira, HubSpot, Zoom, Tally… apne account se jodiye, koi naya account nahi'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => McpScreen(app: app)));
                  _load();
                },
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.api_rounded, color: C.ok),
                title: Text('Public APIs · 2,100+', style: display(15.5)),
                subtitle: const Text('Free APIs: mausam, IFSC, pincode, holidays, cricket, currency, news… Hoola khud use karta hai'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PublicApisScreen(app: app))),
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.shopping_bag_rounded, color: C.accent),
                title: Text('Hoola Shopping · orders', style: display(15.5)),
                subtitle: const Text('ONDC, brand stores, paas ki dukaan · Claude / ChatGPT se bhi jodiye'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShoppingScreen(app: app))),
              ),
            ),
            const SizedBox(height: 14),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Kharch ki seema (auto-approve)', style: display(16)),
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
                title: Text('Dukaan jodiye', style: display(15.5)),
                subtitle: const Text('Kirana, dairy, medical, tiffin… apni ya paas ki dukaan Hoola par laaiye'),
                trailing: const Icon(Icons.add_circle_rounded, color: C.accent),
                onTap: () => _addShop(context),
              ),
            ),
            const SizedBox(height: 18),
          ],
          Caption('SAB PLUGINS · ${packs.length}'),
          if (_cat == null && _err == null) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
          if (_cat != null && packs.isEmpty)
            const Padding(padding: EdgeInsets.all(20), child: Center(child: Text('Kuch nahi mila', style: TextStyle(color: C.muted)))),
          for (final e in byCat.entries)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Glass(
                padding: const EdgeInsets.fromLTRB(14, 2, 10, 2),
                child: ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  shape: const Border(),
                  collapsedShape: const Border(),
                  iconColor: C.accent,
                  collapsedIconColor: C.muted,
                  leading: Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(color: const Color(0x1FFFB15C), borderRadius: BorderRadius.circular(10)),
                    child: Icon(categoryIcon(e.key, e.value.first['executor'] as String? ?? ''), color: C.accentSoft, size: 19),
                  ),
                  title: Text(e.key, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
                  subtitle: Text('${e.value.length} plugins', style: const TextStyle(color: C.faint, fontSize: 11.5)),
                  initiallyExpanded: _filter.isNotEmpty || _grp.isNotEmpty,
                  children: [for (final p in e.value) PluginRow(p: p, onTap: () => _openSheet(p))],
                ),
              ),
            ),
          const SizedBox(height: 14),
          const Text('Kisi bhi plugin par tap kijiye: woh kya karta hai aur Hoola se kaise kahein.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      );
    if (widget.embedded) return list;
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(title: Text('Connectors · ${_cat?['total'] ?? ''} plugins')),
      body: Aurora(child: SafeArea(child: list)),
    );
  }
}
