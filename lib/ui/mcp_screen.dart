import 'dart:async';

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'mcp_tools.dart';
import 'plugin_widgets.dart';
import 'postgres_screen.dart';

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
  Map<String, Map<String, dynamic>> _known = {}; // pack_id -> what the avatar knows (status, tools)
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
      _loadKnown();
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    }
  }

  /// Asks the server what the avatar can do with each server (this talks to the servers, so it comes a bit later).
  Future<void> _loadKnown() async {
    try {
      final k = await app.api!.mcpAvatar();
      if (mounted) setState(() => _known = {for (final x in k) x['pack_id'] as String: x});
    } catch (_) {}
  }

  Widget _knows(Map<String, dynamic> m) {
    final k = _known[m['pack_id']];
    if (k == null) return const SizedBox.shrink();
    final tools = List<String>.from((k['tools'] as List? ?? const []).map((e) => '$e'));
    final st = k['status'] as String? ?? '';
    final String line;
    final Color col;
    if (st == 'ready' && tools.isNotEmpty) {
      line = '${app.aName} jaanta hai · ${tools.length} tools: ${tools.take(4).join(', ')}${tools.length > 4 ? '…' : ''}';
      col = C.ok;
    } else if (st == 'ready') {
      line = '${app.aName} jaanta hai, par server ne koi tool nahi bataya';
      col = C.warn;
    } else if (st == 'slow' || st == 'error') {
      line = 'Server abhi jawab nahi de raha${(k['error'] as String? ?? '').isNotEmpty ? ': ${k['error']}' : ''}';
      col = C.warn;
    } else {
      line = 'Jodna poora kijiye, phir ${app.aName} iske tools use karega';
      col = C.faint;
    }
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text(app.g(line), maxLines: 2, overflow: TextOverflow.ellipsis, style: TextStyle(color: col, fontSize: 11.5)),
    );
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
      _snack('${c['name']} Hoola mein pehle se hai: ${c['native']}');
      return;
    }
    if ((c['options'] as Map?)?['kind'] == 'github') {
      await _connectGithub(c);
      return;
    }
    if ((c['options'] as Map?)?['kind'] == 'supabase') {
      await _connectSupabase(c);
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
            if (c['id'] == '21st-magic')
              const Padding(padding: EdgeInsets.only(top: 6),
                  child: Text('21st.dev/mcp par sign in karke API key banaiye (purani Magic key ab nahi chalti). Hoola sirf code banata hai, aapki site khud nahi badalta.',
                      style: TextStyle(color: C.faint, fontSize: 11.5))),
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
        _snack(r['status'] == 'ready' ? '${c['name']} jud gaya. Ab Hoola se kahiye.' : 'Key sahi nahi lagi');
      }
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// v0.142 GitHub's official MCP server: her fine-grained token (or the Developer Sahayak one), read-only switch,
  /// which toolsets Hoola sees. Lockdown is always on and every write waits for her tap (server side).
  Future<void> _connectGithub(Map<String, dynamic> c) async {
    final opts = Map<String, dynamic>.from(c['options'] as Map? ?? {});
    final all = [for (final t in (opts['toolsets'] as List? ?? [])) t.toString()];
    final st = Map<String, dynamic>.from(c['settings'] as Map? ?? {});
    final picked = <String>{
      for (final t in ((st['toolsets'] ?? opts['default_toolsets']) as List? ?? [])) t.toString()
    };
    bool readonly = st['readonly'] == true;
    final canReuse = c['can_reuse'] == true;
    bool reuse = canReuse;
    final t = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setD) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('GitHub jodiye'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(c['how_to_connect'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          if (canReuse)
            SwitchListTile(contentPadding: EdgeInsets.zero, value: reuse, onChanged: (v) => setD(() => reuse = v),
                title: const Text('Developer Sahayak wala token use karo', style: TextStyle(fontSize: 13.5))),
          if (!reuse)
            TextField(controller: t, obscureText: true,
                decoration: const InputDecoration(labelText: 'Fine-grained token (github_pat_…)')),
          SwitchListTile(contentPadding: EdgeInsets.zero, value: readonly, onChanged: (v) => setD(() => readonly = v),
              title: const Text('Sirf padhna (read-only)', style: TextStyle(fontSize: 13.5)),
              subtitle: const Text('Hoola kuch likh / badal nahi payega', style: TextStyle(color: C.faint, fontSize: 11.5))),
          const SizedBox(height: 6),
          const Text('Hoola kya dekh sake:', style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 4),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final ts in all)
              FilterChip(label: Text(ts, style: const TextStyle(fontSize: 12)), selected: ts == 'context' || picked.contains(ts),
                  onSelected: ts == 'context' ? null : (v) => setD(() => v ? picked.add(ts) : picked.remove(ts))),
          ]),
          const SizedBox(height: 8),
          const Text('Lockdown hamesha on (public repo mein bahar walon ka likha Hoola nahi padhta). Har likhne wala kaam '
              '(issue, PR, merge, push) aapke tap ke baad hi.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          if ((c['docs'] as String? ?? '').isNotEmpty)
            TextButton(onPressed: () => Native.openExternal(url: c['docs'] as String), child: const Text('Token kaise banaye?')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne dein')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Jodiye')),
        ],
      )),
    );
    if (ok != true) return;
    final key = reuse ? '' : t.text.trim();
    if (!reuse && key.isEmpty && c['status'] != 'ready') {
      _snack('Token daaliye');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await app.api!.mcpConnectFeatured(c['id'] as String, key: key, readonly: readonly,
          toolsets: picked.where((x) => x != 'context').toList());
      await _loadMine();
      final note = (r['note'] as String? ?? '');
      _snack(r['status'] == 'ready' ? 'GitHub jud gaya. ${note.isNotEmpty ? note : 'Ab Hoola se kahiye.'}' : 'Token sahi nahi laga');
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// v0.145 Supabase's official MCP server: one-tap sign-in (or a sbp_ token), ONE project, read-only on by default, feature
  /// groups. Writes always wait for her tap (server side).
  Future<void> _connectSupabase(Map<String, dynamic> c) async {
    final opts = Map<String, dynamic>.from(c['options'] as Map? ?? {});
    final all = [for (final t in (opts['features'] as List? ?? [])) t.toString()];
    final st = Map<String, dynamic>.from(c['settings'] as Map? ?? {});
    final picked = <String>{
      for (final t in ((st['features'] ?? opts['default_features']) as List? ?? [])) t.toString()
    };
    bool readonly = st.isEmpty ? true : st['readonly'] == true;
    bool useToken = false;
    final proj = TextEditingController(text: (st['project'] ?? '').toString());
    final tok = TextEditingController();
    const names = {
      'database': 'Tables + SQL', 'debugging': 'Logs + advisors', 'development': 'Project URL / types', 'docs': 'Docs',
      'functions': 'Edge Functions', 'account': 'Saare projects', 'branching': 'Branches', 'storage': 'Storage',
    };
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setD) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Supabase jodiye'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(c['how_to_connect'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          TextField(controller: proj, decoration: const InputDecoration(
              labelText: 'Project ref (behtar: sirf ek project)', hintText: '20 chhote akshar, Project Settings > General')),
          SwitchListTile(contentPadding: EdgeInsets.zero, value: readonly, onChanged: (v) => setD(() => readonly = v),
              title: const Text('Sirf padhna (read-only)', style: TextStyle(fontSize: 13.5)),
              subtitle: const Text('SQL read-only user se chalega. Production par on rakhiye.', style: TextStyle(color: C.faint, fontSize: 11.5))),
          SwitchListTile(contentPadding: EdgeInsets.zero, value: useToken, onChanged: (v) => setD(() => useToken = v),
              title: const Text('Sign-in ki jagah token (sbp_...)', style: TextStyle(fontSize: 13.5))),
          if (useToken)
            TextField(controller: tok, obscureText: true, decoration: const InputDecoration(labelText: 'Personal access token')),
          const SizedBox(height: 6),
          const Text('Hoola kya dekh sake:', style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 4),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final f in all)
              FilterChip(label: Text(names[f] ?? f, style: const TextStyle(fontSize: 12)), selected: picked.contains(f),
                  onSelected: (v) => setD(() => v ? picked.add(f) : picked.remove(f))),
          ]),
          const SizedBox(height: 8),
          const Text('Migration, SQL badlaav, Edge Function deploy, naya project: har baar aapke tap ke baad hi. '
              'Table ka data Hoola ke liye sirf data hai, hukum nahi.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          if ((c['docs'] as String? ?? '').isNotEmpty)
            TextButton(onPressed: () => Native.openExternal(url: c['docs'] as String), child: const Text('Supabase docs')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Rehne dein')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Jodiye')),
        ],
      )),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.mcpConnectFeatured(c['id'] as String, key: useToken ? tok.text.trim() : '',
          readonly: readonly, toolsets: picked.toList(), project: proj.text.trim());
      await _loadMine();
      if (r['status'] == 'needs_link') {
        final err = await app.linkApp(r['pack_id'] as String);
        if (err != null) _snack(err);
      } else {
        final note = (r['note'] as String? ?? '');
        _snack(r['status'] == 'ready' ? 'Supabase jud gaya. ${note.isNotEmpty ? note : 'Ab Hoola se kahiye.'}' : 'Token sahi nahi laga');
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
      const SizedBox(height: 12),
      PluginGrid(children: [for (final (i, c) in shown.indexed) Stagger(index: i % 8, child: _featuredCard(c))]),
    ]);
  }

  Widget _featuredAction(Map<String, dynamic> c) {
    final st = c['status'] as String? ?? '';
    if (st == 'ready') return const PluginAction(kind: ActionKind.linked, label: 'Juda hai');
    if (st == 'needs_link') {
      return PluginAction(kind: ActionKind.attention, label: 'Sign in', onTap: () async {
        final err = await app.linkApp(c['pack_id'] as String);
        if (err != null) _snack(err);
      });
    }
    if (st == 'needs_key') return PluginAction(kind: ActionKind.attention, label: 'Key daaliye', onTap: () => _connectFeatured(c));
    if (c['auth'] == 'oauth_partner') return const PluginAction(kind: ActionKind.soon, label: 'Jald aa raha');
    if (c['native'] != null) {
      return PluginAction(kind: ActionKind.builtin, label: 'Hoola mein hai', onTap: () => _snack('${c['name']} Hoola mein pehle se hai: ${c['native']}'));
    }
    return PluginAction(kind: ActionKind.add, label: _busy ? 'Jod raha hoon…' : 'Jodiye', onTap: _busy ? null : () => _connectFeatured(c));
  }

  Widget _featuredCard(Map<String, dynamic> c) => PluginCard(
        name: c['name'] as String? ?? '',
        does: c['does'] as String? ?? '',
        logo: c['logo'] as String?,
        category: 'MCP ${c['category'] ?? ''}',
        badge: c['india'] == true ? 'INDIA' : null,
        badgeColor: C.accentSoft,
        action: _featuredAction(c),
      );

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
          const Text('API key sirf tab, jab server maange. Hoola ise encrypt karke rakhta hai; chat mein kabhi na bhejein.',
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
        _snack(r['status'] == 'ready' ? '${r['name']} jud gaya. Ab Hoola se kahiye.' : 'Key sahi nahi lagi, dobara daaliye');
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
          BrandLogo(name: m['name'] as String? ?? '', path: m['logo'] as String?, category: 'MCP', size: 42),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m['name'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(m['url'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11.5)),
              if (m['caution'] == true) const Text('Paise/code wala server: har kaam par aapka tap', style: TextStyle(color: C.warn, fontSize: 11.5)),
              _knows(m),
            ]),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 104,
            child: switch (st) {
              'needs_link' => PluginAction(kind: ActionKind.attention, label: 'Link', height: 34, onTap: () async {
                  final err = await app.linkApp(m['pack_id'] as String);
                  if (err != null) _snack(err);
                }),
              'needs_key' => PluginAction(kind: ActionKind.attention, label: 'Key', height: 34, onTap: () => _keyDialog(m)),
              _ => const PluginAction(kind: ActionKind.linked, label: 'Juda hai', height: 34),
            },
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded, color: C.muted),
            onSelected: (v) async {
              if (v == 'key') _keyDialog(m);
              if (v == 'tools') {
                await showMcpTools(context, app, m);
                _loadMine();
              }
              if (v == 'remove') {
                await app.api!.mcpRemove(m['pack_id'] as String);
                _loadMine();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'tools', child: Text('Tools: chalu / band, pehle poochho')),
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
            BrandLogo(name: e['name'] as String? ?? '', path: e['logo'] as String?, category: e['field'] as String? ?? 'MCP', size: 40),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(e['name'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
                Text(e['ref'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: C.faint, fontSize: 11.5)),
              ]),
            ),
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
            Expanded(child: GlassButton(label: 'GitHub', icon: Icons.open_in_new_rounded, height: 38,
                onTap: () => Native.openExternal(url: (e['github'] ?? e['link']) as String? ?? ''))),
            const SizedBox(width: 8),
            Expanded(child: e['connect'] == 'not_allowed'
                ? PluginAction(kind: ActionKind.soon, label: 'Allowed nahi', onTap: () => _snack(e['how_to_connect'] as String? ?? ''))
                : PluginAction(kind: ActionKind.add, label: 'Jodiye', onTap: () => _addDialog(entry: e))),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    BrandLogo.base = app.api?.baseUrl ?? app.serverUrl;
    final fields = (_stats?['fields'] as Map?)?.cast<String, dynamic>();
    return Scaffold(
      appBar: AppBar(title: const Text('MCP servers'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
          Text('${_stats?['total'] ?? 50762} servers ki directory · jo chahiye jodiye, Hoola unse kaam karega',
              style: const TextStyle(color: C.muted, fontSize: 13)),
          const SizedBox(height: 12),
          GradientButton(label: _busy ? 'Jod raha hoon…' : 'Pata daal kar jodiye', icon: Icons.add_rounded, height: 48,
              onTap: _busy ? null : () => _addDialog()),
          if (_err != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
          const SizedBox(height: 12),
          Glass(
            padding: const EdgeInsets.all(4),
            child: ListTile(
              leading: const Icon(Icons.storage_rounded, color: C.accent),
              title: const Text('Postgres (apna database)', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Kisi bhi PostgreSQL ko jodiye: tables, read-only query, explain, sehat; badlav aapki haan se',
                  style: TextStyle(color: C.muted, fontSize: 12)),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PostgresScreen(app: app))),
            ),
          ),
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
