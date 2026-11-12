import 'dart:async';

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'mcp_tools.dart';
import 'plugin_widgets.dart';
import 'postgres_screen.dart';

/// MCP servers: the user's connected servers plus the built-in directory of ~63,700 MCP servers worldwide
/// (npm, PyPI, GitHub lists, mcp.so, mcpservers.org, Apify Store), each with a name, short description and HD logo.
class McpScreen extends StatefulWidget {
  const McpScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<McpScreen> createState() => _McpScreenState();
}

const _fields = ['Developer Tools', 'AI & Agents', 'Search & Web', 'Productivity', 'Finance & Payments', 'Databases',
  'Communication', 'Knowledge & Memory', 'Cloud & DevOps', 'Business & CRM', 'Design & Media', 'Marketing & SEO',
  'Browser Automation', 'Maps & Travel', 'Health & Science', 'Security', 'Files & Documents', 'Social Media',
  'Data & Analytics', 'E-commerce', 'Crypto & Web3', 'Gaming', 'Education & Research', 'IoT & Hardware'];

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
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _deb?.cancel();
    _cmpDeb?.cancel();
    super.dispose();
  }

  void _onApp() {
    if (app.bazarLinkedTick != _seenTick) {
      _seenTick = app.bazarLinkedTick;
      _loadMine();
    }
  }

  List<Map<String, dynamic>> _featured = [];
  List<Map<String, dynamic>> _cmp = [];       // v0.276 apps via Composio (empty when the server has no key)
  int _cmpTotal = 0;                          // v0.294 the live catalogue: search + category + 40 at a time
  int _cmpAll = 0;
  String _cmpQ = '';
  String _cmpCat = '';
  List<String> _cmpCats = [];
  bool _cmpBusy = false;
  bool _cmpLoaded = false;                    // v0.303 first answer arrived (spinner until then)
  Timer? _cmpDeb;
  Map<String, Map<String, dynamic>> _known = {}; // pack_id -> what the avatar knows (status, tools)
  String _fcat = '';

  Future<void> _loadMine() async {
    _seenTick = app.bazarLinkedTick;
    _loadComposio();                  // v0.303 the apps load on their own, even if the server list fails
    try {
      final mine = await app.api!.mcpList();
      if (mounted) setState(() => _mine = mine);
      _loadKnown();
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    }
  }

  Future<void> _loadComposio({bool more = false}) async {
    if (_cmpBusy) return;
    _cmpBusy = true;
    try {
      final r = await app.api!.composioApps(q: _cmpQ, category: _cmpCat, offset: more ? _cmp.length : 0);
      if (r['configured'] != true) {
        if (mounted) setState(() => _cmp = []);
        return;
      }
      final list = List<Map<String, dynamic>>.from((r['apps'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)));
      final cats = [for (final c in (r['categories'] as List? ?? [])) (c as List).first.toString()];
      if (mounted) {
        setState(() {
          _cmp = more ? [..._cmp, ...list] : list;
          _cmpTotal = (r['total'] as num?)?.toInt() ?? _cmp.length;
          _cmpAll = (r['all'] as num?)?.toInt() ?? _cmpTotal;
          if (cats.isNotEmpty) _cmpCats = cats;
        });
      }
    } catch (_) {
    } finally {
      _cmpBusy = false;
      if (mounted && !_cmpLoaded) setState(() => _cmpLoaded = true);
    }
  }

  Future<void> _composioConnect(Map<String, dynamic> a) async {
    try {
      final r = await app.api!.composioConnect(a['toolkit'] as String);
      final url = r['url'] as String? ?? '';
      if (url.isEmpty) {
        _snack(r['say'] as String? ?? '${a['name']} cannot be connected right now.');
        await _loadComposio();
        return;
      }
      final res = await Native.openExternal(url: url);
      if (res != 'ok') _snack(res);
      _snack('Sign in to your ${a['name']} account, then come back here.');
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  /// v0.296 key apps: she types HER key for that app here (never in chat); the server hands it to Composio.
  Future<void> _composioKey(Map<String, dynamic> a) async {
    Map<String, dynamic> r;
    try {
      r = await app.api!.composioConnect(a['toolkit'] as String);
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
      return;
    }
    if (r['status'] != 'needs_key') {
      _snack(r['say'] as String? ?? '');
      await _loadComposio();
      return;
    }
    final fields = List<Map<String, dynamic>>.from((r['fields'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)));
    final ctl = {for (final f in fields) f['name'] as String: TextEditingController()};
    if (!mounted) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('${a['name']} Connect'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Enter your ${a['name']} account key here. It is checked directly with ${a['name']} ; Hoola does not save it.',
                style: const TextStyle(fontSize: 13)),
            for (final f in fields)
              TextField(
                controller: ctl[f['name'] as String],
                obscureText: f['secret'] == true,
                autocorrect: false,
                enableSuggestions: false,
                decoration: InputDecoration(
                  labelText: '${f['label']}${f['required'] == true ? '' : ' (optional)'}',
                  helperText: (f['hint'] as String? ?? '').isEmpty ? null : f['hint'] as String,
                  helperMaxLines: 3,
                ),
              ),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Connect')),
        ],
      ),
    );
    final values = {for (final e in ctl.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
    for (final c in ctl.values) {
      c.dispose();
    }
    if (ok != true) return;
    try {
      final res = await app.api!.composioKey(a['toolkit'] as String, values);
      _snack(res['status'] == 'ready' ? '${a['name']} is connected. Now tell Hoola.' : '${a['name']} is connecting…');
      await _loadComposio();
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _composioRemove(Map<String, dynamic> a) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text('${a['name']} remove?'),
        content: Text('Hoola will stop working with your ${a['name']} account.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Remove')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await app.api!.composioRemove(a['toolkit'] as String);
      await _loadComposio();
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Widget _composioCard(Map<String, dynamic> a) {
    final st = a['status'] as String? ?? '';
    final tools = (a['tools'] as num?)?.toInt() ?? 0;
    final PluginAction action;
    if (st == 'ready') {
      action = const PluginAction(kind: ActionKind.linked, label: 'Connected');
    } else if (st == 'needs_key') {
      action = PluginAction(kind: ActionKind.attention, label: 'Enter key', onTap: () => _composioKey(a));
    } else if (st == 'needs_setup') {
      action = PluginAction(kind: ActionKind.soon, label: 'Setup pending',
          onTap: () => _snack('${a['name']}: Newtika has to set up this app in Composio once, then it will connect.'));
    } else {
      action = PluginAction(kind: ActionKind.add, label: 'Connect', onTap: () => _composioConnect(a));
    }
    return PluginCard(
      name: a['name'] as String? ?? '',
      does: a['does'] as String? ?? '',
      logo: a['logo'] as String?,       // v0.298 Hoola-served path: the app's own logo, cached on the server
      category: [if ((a['category'] as String? ?? '').isNotEmpty) a['category'], if (tools > 0) '$tools tools'].join(' · '),
      onTap: st == 'ready' ? () => _composioRemove(a) : null,
      action: action,
    );
  }

  Widget _composioSection() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Caption('APPS · ${_cmpAll > 0 ? _cmpAll : _cmp.length} · sign in with your own account, no new account'),
        Glass(
          radius: 18,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
          child: TextField(
            style: const TextStyle(color: C.ink, fontSize: 15),
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded, color: C.muted), hintText: 'Slack, Zoho, Tally, invoice, CRM…',
                border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),
            onChanged: (v) {
              _cmpQ = v.trim();
              _cmpDeb?.cancel();
              _cmpDeb = Timer(const Duration(milliseconds: 350), () => _loadComposio());
            },
          ),
        ),
        if (_cmpCats.isNotEmpty) ...[
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              for (final c in ['', ..._cmpCats])
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(label: Text(c.isEmpty ? 'All' : c), selected: _cmpCat == c, showCheckmark: false,
                      onSelected: (_) {
                        setState(() => _cmpCat = c);
                        _loadComposio();
                      }),
                ),
            ]),
          ),
        ],
        const SizedBox(height: 12),
        if (_cmp.isEmpty)
          const Padding(padding: EdgeInsets.all(12), child: Text('Nothing found', style: TextStyle(color: C.muted)))
        else
          PluginGrid(children: [for (final (i, a) in _cmp.indexed) Stagger(index: i % 8, child: _composioCard(a))]),
        if (_cmp.length < _cmpTotal)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Center(
              child: TextButton(onPressed: () => _loadComposio(more: true),
                  child: Text('Show more (${_cmpTotal - _cmp.length} more)')),
            ),
          ),
      ]);

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
      line = '${app.aName} knows · ${tools.length} tools: ${tools.take(4).join(', ')}${tools.length > 4 ? '…' : ''}';
      col = C.ok;
    } else if (st == 'ready') {
      line = '${app.aName} knows it, but the server did not list any tools';
      col = C.warn;
    } else if (st == 'slow' || st == 'error') {
      line = 'The server is not answering right now${(k['error'] as String? ?? '').isNotEmpty ? ': ${k['error']}' : ''}';
      col = C.warn;
    } else {
      line = 'Finish connecting, then ${app.aName} will use its tools';
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
      _snack('${c['name']} is already in Hoola: ${c['native']}');
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
          title: Text('${c['name']} Connect'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(c['how_to_connect'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            if ((c['url_hint'] as String? ?? '').isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 6),
                  child: Text('It looks like: ${c['url_hint']}', style: const TextStyle(color: C.faint, fontSize: 11.5))),
            if (c['id'] == '21st-magic')
              const Padding(padding: EdgeInsets.only(top: 6),
                  child: Text('Sign in at 21st.dev/mcp and make an API key (the old Magic key no longer works). Hoola only makes code; it does not change your site by itself.',
                      style: TextStyle(color: C.faint, fontSize: 11.5))),
            if (c['id'] == 'razorpay')
              const Padding(padding: EdgeInsets.only(top: 6),
                  child: Text('Format: key_id:key_secret (Razorpay Dashboard > API Keys)', style: TextStyle(color: C.faint, fontSize: 11.5))),
            TextField(controller: t, obscureText: auth == 'api_key',
                decoration: InputDecoration(labelText: auth == 'api_key' ? 'API key' : 'Your MCP address (https://…)')),
            if ((c['docs'] as String? ?? '').isNotEmpty)
              TextButton(onPressed: () => Native.openExternal(url: c['docs'] as String), child: const Text('Where to find it? (docs)')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Leave it')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Connect')),
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
        _snack(r['status'] == 'ready' ? '${c['name']} is connected. Now tell Hoola.' : 'The key does not look right');
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
        title: const Text('Connect GitHub'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(c['how_to_connect'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          if (canReuse)
            SwitchListTile(contentPadding: EdgeInsets.zero, value: reuse, onChanged: (v) => setD(() => reuse = v),
                title: const Text('Use the Developer Assistant token', style: TextStyle(fontSize: 13.5))),
          if (!reuse)
            TextField(controller: t, obscureText: true,
                decoration: const InputDecoration(labelText: 'Fine-grained token (github_pat_…)')),
          SwitchListTile(contentPadding: EdgeInsets.zero, value: readonly, onChanged: (v) => setD(() => readonly = v),
              title: const Text('Read only', style: TextStyle(fontSize: 13.5)),
              subtitle: const Text('Hoola will not be able to write or change anything', style: TextStyle(color: C.faint, fontSize: 11.5))),
          const SizedBox(height: 6),
          const Text('What Hoola may see:', style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 4),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final ts in all)
              FilterChip(label: Text(ts, style: const TextStyle(fontSize: 12)), selected: ts == 'context' || picked.contains(ts),
                  onSelected: ts == 'context' ? null : (v) => setD(() => v ? picked.add(ts) : picked.remove(ts))),
          ]),
          const SizedBox(height: 8),
          const Text('Lockdown is always on (in a public repo Hoola does not read what outsiders wrote). Every writing action '
              '(issue, PR, merge, push) happens only after your tap.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          if ((c['docs'] as String? ?? '').isNotEmpty)
            TextButton(onPressed: () => Native.openExternal(url: c['docs'] as String), child: const Text('How to make the token?')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Connect')),
        ],
      )),
    );
    if (ok != true) return;
    final key = reuse ? '' : t.text.trim();
    if (!reuse && key.isEmpty && c['status'] != 'ready') {
      _snack('Enter token');
      return;
    }
    setState(() => _busy = true);
    try {
      final r = await app.api!.mcpConnectFeatured(c['id'] as String, key: key, readonly: readonly,
          toolsets: picked.where((x) => x != 'context').toList());
      await _loadMine();
      final note = (r['note'] as String? ?? '');
      _snack(r['status'] == 'ready' ? 'GitHub is connected. ${note.isNotEmpty ? note : 'Now tell Hoola.'}' : 'The token does not look right');
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
      'functions': 'Edge Functions', 'account': 'All projects', 'branching': 'Branches', 'storage': 'Storage',
    };
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setD) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Connect Supabase'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(c['how_to_connect'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 8),
          TextField(controller: proj, decoration: const InputDecoration(
              labelText: 'Project ref (better: just one project)', hintText: '20 lowercase letters, Project Settings > General')),
          SwitchListTile(contentPadding: EdgeInsets.zero, value: readonly, onChanged: (v) => setD(() => readonly = v),
              title: const Text('Read only', style: TextStyle(fontSize: 13.5)),
              subtitle: const Text('SQL runs as a read-only user. Keep this on in production.', style: TextStyle(color: C.faint, fontSize: 11.5))),
          SwitchListTile(contentPadding: EdgeInsets.zero, value: useToken, onChanged: (v) => setD(() => useToken = v),
              title: const Text('Token instead of sign-in (sbp_...)', style: TextStyle(fontSize: 13.5))),
          if (useToken)
            TextField(controller: tok, obscureText: true, decoration: const InputDecoration(labelText: 'Personal access token')),
          const SizedBox(height: 6),
          const Text('What Hoola may see:', style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 4),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final f in all)
              FilterChip(label: Text(names[f] ?? f, style: const TextStyle(fontSize: 12)), selected: picked.contains(f),
                  onSelected: (v) => setD(() => v ? picked.add(f) : picked.remove(f))),
          ]),
          const SizedBox(height: 8),
          const Text('Migrations, SQL changes, Edge Function deploys, a new project: each time only after your tap. '
              'Table data is just data for Hoola, not instructions.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          if ((c['docs'] as String? ?? '').isNotEmpty)
            TextButton(onPressed: () => Native.openExternal(url: c['docs'] as String), child: const Text('Supabase docs')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Connect')),
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
        _snack(r['status'] == 'ready' ? 'Supabase is connected. ${note.isNotEmpty ? note : 'Now tell Hoola.'}' : 'The token does not look right');
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
              child: ChoiceChip(label: Text(cat.isEmpty ? 'All' : cat), selected: _fcat == cat, showCheckmark: false,
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
    if (st == 'ready') return const PluginAction(kind: ActionKind.linked, label: 'Connected');
    if (st == 'needs_link') {
      return PluginAction(kind: ActionKind.attention, label: 'Sign in', onTap: () async {
        final err = await app.linkApp(c['pack_id'] as String);
        if (err != null) _snack(err);
      });
    }
    if (st == 'needs_key') return PluginAction(kind: ActionKind.attention, label: 'Enter key', onTap: () => _connectFeatured(c));
    if (c['auth'] == 'oauth_partner') return const PluginAction(kind: ActionKind.soon, label: 'Coming soon');
    if (c['native'] != null) {
      return PluginAction(kind: ActionKind.builtin, label: 'In Hoola', onTap: () => _snack('${c['name']} is already in Hoola: ${c['native']}'));
    }
    return PluginAction(kind: ActionKind.add, label: _busy ? 'Connecting…' : 'Connect', onTap: _busy ? null : () => _connectFeatured(c));
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

  /// v0.154 one tap: the server checks it, starts it on Hoola's runner (or joins a hosted one) and lists its tools.
  Future<void> _oneTap(Map<String, dynamic> e, {Map<String, String> keys = const {}, bool accept = false}) async {
    final ref = e['ref'] as String? ?? '';
    setState(() => _busy = true);
    Map<String, dynamic> r;
    try {
      _snack(e['package'] != null ? '${e['name']} is being checked and started… the first time it can take a minute' : '${e['name']} connecting…');
      r = await app.api!.mcpOneTap(ref, keys: keys, acceptCaution: accept);
    } catch (err) {
      if (mounted) setState(() => _busy = false);
      _snack(err.toString().replaceFirst('Exception: ', ''));
      return;
    }
    if (mounted) setState(() => _busy = false);
    final st = r['status'] as String? ?? '';
    if (st == 'ready') {
      await _loadMine();
      _snack(r['say'] as String? ?? '${e['name']} is connected. Now tell Hoola.');
    } else if (st == 'needs_link') {
      await _loadMine();
      final err = await app.linkApp(r['pack_id'] as String);
      if (err != null) _snack(err);
    } else if (st == 'needs_keys') {
      final got = await _askKeys(e, (r['keys'] as List? ?? []).cast<Map>(), r['say'] as String? ?? '');
      if (got != null) await _oneTap(e, keys: {...keys, ...got}, accept: accept);
    } else if (st == 'caution') {
      final go = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('${e['name']}: caution'),
          content: Text([...(r['reasons'] as List? ?? []).map((x) => '• $x'), '',
            'Hoola will run it in a locked container and ask for your yes before every write or send action.'].join('\n')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Leave it')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Connect anyway')),
          ],
        ),
      );
      if (go == true) await _oneTap(e, keys: keys, accept: true);
    } else {
      _snack(r['say'] as String? ?? 'Could not connect');
    }
  }

  Future<Map<String, String>?> _askKeys(Map<String, dynamic> e, List<Map> need, String say) async {
    final ctrls = {for (final k in need) k['name'] as String: TextEditingController()};
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(18, 18, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${e['name']} keys', style: display(19)),
          const SizedBox(height: 6),
          Text(say.isNotEmpty ? say : 'This server needs these to run.', style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
          const SizedBox(height: 4),
          const Text('Hoola keeps them encrypted and gives them only to this server; never send them in chat.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          for (final k in need)
            TextField(
              controller: ctrls[k['name']],
              obscureText: k['kind'] == 'secret',
              decoration: InputDecoration(labelText: k['name'] as String),
            ),
          const SizedBox(height: 14),
          Row(children: [
            if ((e['github'] as String? ?? '').isNotEmpty)
              Expanded(child: GlassButton(label: 'Where to find it?', height: 46, onTap: () => Native.openExternal(url: e['github'] as String))),
            if ((e['github'] as String? ?? '').isNotEmpty) const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Connect', height: 46, onTap: () => Navigator.of(ctx).pop(true))),
          ]),
        ]),
      ),
    );
    if (ok != true) return null;
    final out = {for (final x in ctrls.entries) if (x.value.text.trim().isNotEmpty) x.key: x.value.text.trim()};
    return out.isEmpty ? null : out;
  }

  Future<void> _addDialog({Map<String, dynamic>? entry}) async {
    final url = TextEditingController(text: entry?['mcp_url'] as String? ?? '');
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
          Text(entry == null ? 'Connect an MCP server' : 'Connect: ${entry['name']}', style: display(19)),
          const SizedBox(height: 6),
          Text(
              entry?['source'] == 'Apify Store'
                  ? 'Apify actor: put your own Apify API token in the key field below (Apify Console > Settings > Integrations). Every run uses your Apify credit.'
                  : entry?['mcp_url'] != null
                      ? 'Its MCP address is already filled in. Just tap Connect (a key only if the server asks).'
                      : local
                          ? 'This server runs on a computer. First run it on your PC/server in HTTP mode, then enter its https address here.'
                          : 'Enter the server\'s MCP address (https://…/mcp). You can find it on the GitHub page.',
              style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
          if (entry?['caution'] != null) ...[
            const SizedBox(height: 8),
            Text('⚠ ${entry!['caution']}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
          ],
          TextField(controller: url, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'MCP address (https://…)')),
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Name (optional)')),
          const SizedBox(height: 6),
          const Text('An API key only if the server asks. Hoola keeps it encrypted; never send it in chat.',
              style: TextStyle(color: C.faint, fontSize: 12)),
          TextField(controller: key, obscureText: true, decoration: const InputDecoration(labelText: 'API key (optional)')),
          TextField(controller: header, decoration: const InputDecoration(labelText: 'Key header (Authorization / X-API-Key)')),
          const SizedBox(height: 14),
          Row(children: [
            if (entry?['github'] != null && (entry!['github'] as String).isNotEmpty)
              Expanded(child: GlassButton(label: 'GitHub', height: 46, onTap: () => Native.openExternal(url: entry['github'] as String))),
            if (entry?['github'] != null) const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Connect', height: 46, onTap: () => Navigator.of(ctx).pop(true))),
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
        _snack(r['status'] == 'ready' ? '${r['name']} is connected. Now tell Hoola.' : 'The key does not look right, enter it again');
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
        title: Text('${m['name']} API key'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: key, obscureText: true, decoration: const InputDecoration(labelText: 'API key')),
          TextField(controller: header, decoration: const InputDecoration(labelText: 'Header')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || key.text.trim().isEmpty) return;
    try {
      final r = await app.api!.mcpKey(m['pack_id'] as String, key.text.trim(), header: header.text.trim());
      _snack(r['status'] == 'ready' ? 'Key saved' : 'Key saved, but the server is still asking you to sign in');
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
              if (m['caution'] == true) const Text('Server with money/codes: your tap on every action', style: TextStyle(color: C.warn, fontSize: 11.5)),
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
              _ => const PluginAction(kind: ActionKind.linked, label: 'Connected', height: 34),
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
              PopupMenuItem(value: 'tools', child: Text('Tools: on / off, ask first')),
              PopupMenuItem(value: 'key', child: Text('Change API key')),
              PopupMenuItem(value: 'remove', child: Text('Remove')),
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
                Text(e['by'] != null ? 'by ${e['by']}' : (e['ref'] as String? ?? ''), maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: C.faint, fontSize: 11.5)),
              ]),
            ),
            if (e['official'] == true) const Pill('Official', fg: C.ok)
            else if (e['verified'] == true) const Pill('Verified', fg: C.teal),
          ]),
          const SizedBox(height: 4),
          Text(e['does'] as String? ?? '', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            Pill(e['field'] as String? ?? ''),
            Pill(remote ? 'Online service' : e['runs_on'] == 'hoola' ? 'Runs on the Hoola runner' : e['runs_on'] == 'pc' ? 'On your PC' : 'Runs on a computer',
                fg: remote || e['runs_on'] == 'hoola' ? C.teal : C.faint),
            if (e['source'] != null) Pill(e['source'] as String),
            if (e['downloads_per_month'] != null) Pill('${e['downloads_per_month']}/month downloads'),
            if (e['users_per_month'] != null) Pill('${e['users_per_month']} logs/month'),
            if (e['one_tap'] == true) const Pill('One tap', fg: C.ok),
            if (e['trusted'] == true) const Pill('Trusted', fg: C.teal),
            if (e['keys'] != null) Pill('Key: ${(e['keys'] as List).join(', ')}', fg: C.warn),
            if (e['caution'] != null) const Pill('Caution', fg: C.warn),
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
                ? PluginAction(kind: ActionKind.soon, label: 'Not allowed', onTap: () => _snack(e['how_to_connect'] as String? ?? ''))
                : e['runs_on'] == 'pc'
                    ? PluginAction(kind: ActionKind.soon, label: 'Runs on the PC', onTap: () => _snack(e['pc_note'] as String? ?? ''))
                    : e['one_tap'] == true
                        ? PluginAction(kind: ActionKind.add, label: 'Connect in one tap', onTap: () => _oneTap(e))
                        : PluginAction(kind: ActionKind.add, label: 'Connect', onTap: () => _addDialog(entry: e))),
          ]),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // v0.303 SAAF CONNECT (owner: "REMOVE ALL JUST KEEP COMPOSIO MCPS AND WORKING PLUG IN"): the Composio apps, the
    // servers she already joined and her own Postgres. The 63,700-server directory, the non-Composio popular list and
    // "add by address" are gone from the screen (Hoola can still add a server she names in chat).
    BrandLogo.base = app.api?.baseUrl ?? app.serverUrl;
    return Scaffold(
      appBar: AppBar(title: const Text('Apps'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _loadMine,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Connect your Slack, Notion, Jira, HubSpot, Zoom… accounts: Hoola will do your work in them.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            if (_err != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (_cmp.isNotEmpty || _cmpQ.isNotEmpty || _cmpCat.isNotEmpty) ...[
              const SizedBox(height: 14),
              _composioSection(),
            ] else if (!_cmpLoaded)
              const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()))
            else
              const Padding(padding: EdgeInsets.all(16), child: Text('Apps are not running on the server right now.', style: TextStyle(color: C.muted))),
            if (_mine.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Caption('YOUR CONNECTED SERVERS'),
              for (final m in _mine) _mineCard(m),
            ],
            const SizedBox(height: 18),
            Glass(
              padding: const EdgeInsets.all(4),
              child: ListTile(
                leading: const Icon(Icons.storage_rounded, color: C.accent),
                title: const Text('Postgres (your own database)', style: TextStyle(fontWeight: FontWeight.w700)),
                subtitle: const Text('Connect any PostgreSQL: tables, read-only queries, explain, health; changes only with your yes',
                    style: TextStyle(color: C.muted, fontSize: 12)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PostgresScreen(app: app))),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
