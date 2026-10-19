import 'dart:async';

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// MCP servers: the user's connected servers plus the built-in directory of ~50,700 MCP servers worldwide.
class McpScreen extends StatefulWidget {
  const McpScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<McpScreen> createState() => _McpScreenState();
}

const _fields = ['Developer Tools', 'Finance & Fintech', 'Productivity', 'Communication', 'Databases', 'Search & Data Extraction',
  'Knowledge & Memory', 'Browser Automation', 'Marketing', 'Cloud Platforms', 'Travel & Transportation', 'Location Services',
  'Social Media', 'Security'];

class _McpScreenState extends State<McpScreen> {
  List<Map<String, dynamic>> _mine = [];
  List<Map<String, dynamic>> _found = [];
  Map<String, dynamic>? _stats;
  String _q = '';
  String _field = '';
  String? _err;
  bool _busy = false;
  Timer? _deb;
  int _seenTick = -1;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _loadMine();
    _search();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _deb?.cancel();
    super.dispose();
  }

  void _onApp() {
    if (app.bazarLinkedTick != _seenTick) {
      _seenTick = app.bazarLinkedTick;
      _loadMine();
    }
  }

  List<Map<String, dynamic>> _featured = [];
  String _fcat = '';

  Future<void> _loadMine() async {
    _seenTick = app.bazarLinkedTick;
    try {
      final r = await Future.wait([app.api!.mcpList(), app.api!.mcpFeatured()]);
      if (mounted) {
        setState(() {
          _mine = r[0];
          _featured = r[1];
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    }
  }

  Future<void> _search() async {
    try {
      final r = await app.api!.mcpDirectory(q: _q, field: _field);
      if (!mounted) return;
      setState(() {
        if (r['servers'] != null) {
          _found = (r['servers'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        } else {
          _stats = r;
          _found = [];
        }
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    }
  }

  Future<void> _connectFeatured(Map<String, dynamic> c) async {
    final auth = c['auth'] as String? ?? '';
    String url = '', key = '';
    if (auth == 'oauth_partner') {
      _snack(c['how_to_connect'] as String? ?? '');
      return;
    }
    if (c['native'] != null) {
      _snack('${c['name']} Santosh mein pehle se hai: ${c['native']}');
      return;
    }
    if (auth == 'api_key' || auth == 'per_user_url') {
      final t = TextEditingController();
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text('${c['name']} jodiye'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(c['how_to_connect'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if ((c['url_hint'] as String? ?? '').isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 6),
                  child: Text('Aisa dikhta hai: ${c['url_hint']}', style: const TextStyle(color: C.faint, fontSize: 11.5))),
            if (c['id'] == 'razorpay')
              const Padding(padding: EdgeInsets.only(top: 6),
                  child: Text('Format: key_id:key_secret (Razorpay Dashboard > API Keys)', style: TextStyle(color: C.faint, fontSize: 11.5))),
            TextField(controller: t, obscureText: auth == 'api_key',
                decoration: InputDecoration(labelText: auth == 'api_key' ? 'API key' : 'Aapka MCP address (https://…)')),
            if ((c['docs'] as String? ?? '').isNotEmpty)
              TextButton(onPressed: () => Native.openExternal(url: c['docs'] as String), child: const Text('Kahan milega? (docs)')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne dein')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Jodiye')),
          ],
        ),
      );
      if (ok != true || t.text.trim().isEmpty) return;
      if (auth == 'api_key') {
        key = t.text.trim();
      } else {
        url = t.text.trim();
      }
    }
    setState(() => _busy = true);
    try {
      final r = await app.api!.mcpConnectFeatured(c['id'] as String, url: url, key: key);
      await _loadMine();
      if (r['status'] == 'needs_link') {
        final err = await app.linkApp(r['pack_id'] as String);
        if (err != null) _snack(err);
      } else {
        _snack(r['status'] == 'ready' ? '${c['name']} jud gaya. Ab Santosh se kahiye.' : 'Key sahi nahi lagi');
      }
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _featuredGrid() {
    final cats = <String>{for (final c in _featured) c['category'] as String};
    final shown = _featured.where((c) => _fcat.isEmpty || c['category'] == _fcat).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          for (final cat in ['', ...cats])
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(label: Text(cat.isEmpty ? 'Sab' : cat), selected: _fcat == cat, showCheckmark: false,
                  onSelected: (_) => setState(() => _fcat = cat)),
            ),
        ]),
      ),
      const SizedBox(height: 10),
      GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1.35,
        children: [
          for (final c in shown)
            Glass(
              radius: 18,
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Row(children: [
                  Expanded(child: Text(c['name'] as String, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14))),
                  if (c['india'] == true) const Pill('India', fg: C.accentSoft),
                ]),
                const SizedBox(height: 2),
                Text(c['does'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: C.faint, fontSize: 11.5, height: 1.3)),
                const Spacer(),
                switch (c['status'] as String? ?? '') {
                  'ready' => const GlassButton(label: 'Juda hai', color: C.ok, height: 34, onTap: null),
                  'needs_link' => GlassButton(label: 'Sign in', color: C.accentSoft, height: 34, onTap: () async {
                      final err = await app.linkApp(c['pack_id'] as String);
                      if (err != null) _snack(err);
                    }),
                  _ => GlassButton(
                      label: c['auth'] == 'oauth_partner' ? 'Jald aa raha' : (c['native'] != null ? 'Santosh mein hai' : 'Jodiye'),
                      color: c['auth'] == 'oauth_partner' ? C.faint : C.accentSoft,
                      height: 34,
                      onTap: _busy ? null : () => _connectFeatured(c)),
                },
              ]),
            ),
        ],
      ),
    ]);
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _addDialog({Map<String, dynamic>? entry}) async {
    final url = TextEditingController();
    final name = TextEditingController(text: entry?['name'] as String? ?? '');
    final key = TextEditingController();
    final header = TextEditingController(text: 'Authorization');
    final local = entry?['connect'] == 'local';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(18, 18, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(entry == null ? 'MCP server jodiye' : 'Jodiye: ${entry['name']}', style: display(19)),
          const SizedBox(height: 6),
          Text(
              local
                  ? 'Yeh server computer par chalta hai. Pehle use apne PC/server par HTTP mode mein chalaiye, phir uska https pata yahan daaliye.'
                  : 'Server ka MCP pata (https://…/mcp) daaliye. GitHub page par milta hai.',
              style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
          if (entry?['caution'] != null) ...[
            const SizedBox(height: 8),
            Text('⚠ ${entry!['caution']}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
          ],
          TextField(controller: url, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'MCP address (https://…)')),
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (optional)')),
          const SizedBox(height: 6),
          const Text('API key sirf tab, jab server maange. Santosh ise encrypt karke rakhta hai; chat mein kabhi na bhejein.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          TextField(controller: key, obscureText: true, decoration: const InputDecoration(labelText: 'API key (optional)')),
          TextField(controller: header, decoration: const InputDecoration(labelText: 'Key header (Authorization / X-API-Key)')),
          const SizedBox(height: 14),
          Row(children: [
            if (entry?['github'] != null && (entry!['github'] as String).isNotEmpty)
              Expanded(child: GlassButton(label: 'GitHub', height: 46, onTap: () => Native.openExternal(url: entry['github'] as String))),
            if (entry?['github'] != null) const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Jodiye', height: 46, onTap: () => Navigator.of(ctx).pop(true))),
          ]),
        ]),
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.mcpAdd(url.text.trim(),
          name: name.text.trim(), ref: entry?['ref'] as String? ?? '', key: key.text.trim(),
          header: key.text.trim().isEmpty ? '' : header.text.trim());
      await _loadMine();
      if (r['status'] == 'needs_link') {
        final err = await app.linkApp(r['pack_id'] as String);
        if (err != null) _snack(err);
      } else {
        _snack(r['status'] == 'ready' ? '${r['name']} jud gaya. Ab Santosh se kahiye.' : 'Key sahi nahi lagi, dobara daaliye');
      }
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _keyDialog(Map<String, dynamic> m) async {
    final key = TextEditingController();
    final header = TextEditingController(text: 'Authorization');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('${m['name']} ki API key'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: key, obscureText: true, decoration: const InputDecoration(labelText: 'API key')),
          TextField(controller: header, decoration: const InputDecoration(labelText: 'Header')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne dein')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || key.text.trim().isEmpty) return;
    try {
      final r = await app.api!.mcpKey(m['pack_id'] as String, key.text.trim(), header: header.text.trim());
      _snack(r['status'] == 'ready' ? 'Key save ho gayi' : 'Key save hui, server abhi bhi sign-in maang raha hai');
      _loadMine();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Widget _mineCard(Map<String, dynamic> m) {
    final st = m['status'] as String? ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        radius: 20,
        padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
        child: Row(children: [
          Icon(Icons.hub_rounded, color: st == 'ready' ? C.ok : C.accentSoft),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m['name'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(m['url'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11.5)),
              if (m['caution'] == true) const Text('Paise/code wala server: har kaam par aapka tap', style: TextStyle(color: C.warn, fontSize: 11.5)),
            ]),
          ),
          switch (st) {
            'needs_link' => TextButton(onPressed: () async {
                final err = await app.linkApp(m['pack_id'] as String);
                if (err != null) _snack(err);
              }, child: const Text('Link')),
            'needs_key' => TextButton(onPressed: () => _keyDialog(m), child: const Text('Key daaliye')),
            _ => const Padding(padding: EdgeInsets.symmetric(horizontal: 8), child: Pill('Juda hai', fg: C.ok)),
          },
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded, color: C.muted),
            onSelected: (v) async {
              if (v == 'key') _keyDialog(m);
              if (v == 'remove') {
                await app.api!.mcpRemove(m['pack_id'] as String);
                _loadMine();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'key', child: Text('API key badlein')),
              PopupMenuItem(value: 'remove', child: Text('Hata dein')),
            ],
          ),
        ]),
      ),
    );
  }

  Widget _entryCard(Map<String, dynamic> e) {
    final remote = e['connect'] == 'remote';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        radius: 18,
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(e['ref'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5))),
            if (e['official'] == true) const Pill('Official', fg: C.ok),
          ]),
          const SizedBox(height: 4),
          Text(e['does'] as String? ?? '', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            Pill(e['field'] as String? ?? ''),
            Pill(remote ? 'Online service' : 'Computer par chalta', fg: remote ? C.teal : C.faint),
            if (e['source'] != null) Pill(e['source'] as String),
            if (e['downloads_per_month'] != null) Pill('${e['downloads_per_month']}/mahina downloads'),
            if (e['caution'] != null) const Pill('Savdhani', fg: C.warn),
          ]),
          if (e['install'] != null) ...[
            const SizedBox(height: 6),
            SelectableText(e['install'] as String, style: const TextStyle(fontFamily: 'monospace', fontSize: 11.5, color: C.chip)),
          ],
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: GlassButton(label: 'GitHub', height: 38, onTap: () => Native.openExternal(url: (e['github'] ?? e['link']) as String? ?? ''))),
            const SizedBox(width: 8),
            Expanded(child: e['connect'] == 'not_allowed'
                ? GlassButton(label: 'Allowed nahi', color: C.faint, height: 38, onTap: () => _snack(e['how_to_connect'] as String? ?? ''))
                : GlassButton(label: 'Jodiye', color: C.accentSoft, height: 38, onTap: () => _addDialog(entry: e))),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final fields = (_stats?['fields'] as Map?)?.cast<String, dynamic>();
    return Scaffold(
      appBar: AppBar(title: const Text('MCP servers'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
          Text('${_stats?['total'] ?? 50762} servers ki directory · jo chahiye jodiye, Santosh unse kaam karega',
              style: const TextStyle(color: C.muted, fontSize: 13)),
          const SizedBox(height: 12),
          GradientButton(label: _busy ? 'Jod raha hoon…' : 'Pata daal kar jodiye', icon: Icons.add_rounded, height: 48,
              onTap: _busy ? null : () => _addDialog()),
          if (_err != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
          if (_featured.isNotEmpty) ...[
            const SizedBox(height: 18),
            Caption('POPULAR APPS · ${_featured.length}'),
            _featuredGrid(),
          ],
          if (_mine.isNotEmpty) ...[
            const SizedBox(height: 18),
            const Caption('AAPKE SERVERS'),
            for (final m in _mine) _mineCard(m),
          ],
          const SizedBox(height: 18),
          const Caption('DIRECTORY'),
          Glass(
            radius: 18,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
            child: TextField(
              style: const TextStyle(color: C.ink, fontSize: 15),
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded, color: C.muted), hintText: 'GitHub, Notion, Zerodha, Tally, Postgres…',
                  border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),
              onChanged: (v) {
                _q = v.trim();
                _deb?.cancel();
                _deb = Timer(const Duration(milliseconds: 350), _search);
              },
            ),
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              for (final f in _fields)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(fields?[f] != null ? '$f · ${fields![f]}' : f),
                    selected: _field == f,
                    showCheckmark: false,
                    onSelected: (on) {
                      setState(() => _field = on ? f : '');
                      _search();
                    },
                  ),
                ),
            ]),
          ),
          const SizedBox(height: 12),
          if (_found.isEmpty && (_q.isNotEmpty || _field.isNotEmpty))
            const Padding(padding: EdgeInsets.all(20), child: Center(child: Text('Kuch nahi mila', style: TextStyle(color: C.muted)))),
          if (_found.isEmpty && _q.isEmpty && _field.isEmpty)
            const Padding(padding: EdgeInsets.all(12), child: Text('Upar dhoondhiye ya koi category chuniye.', style: TextStyle(color: C.faint))),
          for (final e in _found) _entryCard(e),
        ]),
      ),
    );
  }
}
