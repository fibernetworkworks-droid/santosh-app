import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';
import 'hoola_cards.dart';
import 'hoola_media.dart';
import 'attach.dart';
import 'hoola_business_screen.dart';
import 'deal_screen.dart';
import 'dosti_screen.dart';
import 'hoola_samaj_screen.dart';

const _relations = {'family': 'Family', 'team': 'Team', 'business': 'Business', 'friend': 'Dost'};

/// Hoola Network: my Hoola ID + QR, connections and requests, what other avatars sent, and avatar-to-avatar talks.
class HoolaNetScreen extends StatefulWidget {
  const HoolaNetScreen({super.key, required this.app, this.initialTab = 0});
  final Santosh app;
  final int initialTab;
  @override
  State<HoolaNetScreen> createState() => _HoolaNetScreenState();
}

class _HoolaNetScreenState extends State<HoolaNetScreen> {
  Map<String, dynamic> _me = {};
  Map<String, dynamic>? _invite;
  List<Map<String, dynamic>> _links = [];
  List<Map<String, dynamic>> _inbox = [];
  List<Map<String, dynamic>> _threads = [];
  List<Map<String, dynamic>> _groups = [];
  bool _loading = true;
  String? _err;
  int _seen = 0;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _seen = app.hoolaTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.hoolaTick != _seen) {
      _seen = app.hoolaTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([app.api!.netMe(), app.api!.netConnections(), app.api!.netInbox(), app.api!.netThreads(),
        app.api!.netGroups().catchError((_) => <Map<String, dynamic>>[])]);
      if (!mounted) return;
      setState(() {
        _me = r[0] as Map<String, dynamic>;
        _links = r[1] as List<Map<String, dynamic>>;
        _inbox = List<Map<String, dynamic>>.from(((r[2] as Map)['waiting'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
        _threads = r[3] as List<Map<String, dynamic>>;
        _groups = r[4] as List<Map<String, dynamic>>;
        _loading = false;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loading = false; });
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  // ---------------------------------------------------------------- Mera ID
  Future<void> _makeInvite() async {
    try {
      final r = await app.api!.netInvite();
      if (mounted) setState(() => _invite = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _editHandle() async {
    final c = TextEditingController(text: _me['handle'] as String? ?? '');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Change Hoola ID'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: c, decoration: const InputDecoration(prefixText: '@', hintText: 'meghana.fnw')),
          const SizedBox(height: 8),
          const Text('Small English letters, numbers, . or _. Changeable any time in the first week; after that, once a year.',
              style: TextStyle(fontSize: 12, color: C.muted)),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.netSetMe(handle: c.text.trim());
      if (mounted) setState(() => _me = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _discover(bool on) async {
    String? phone;
    if (on) {
      final c = TextEditingController();
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Allow finding me by number'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: c, keyboardType: TextInputType.phone, decoration: const InputDecoration(hintText: 'Your mobile number')),
            const SizedBox(height: 8),
            const Text('Your number is kept hidden (hashed). Only people who know your number can find your Hoola; '
                'they still need your yes to connect.', style: TextStyle(fontSize: 12, color: C.muted)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Turn on')),
          ],
        ),
      );
      if (ok != true) return;
      phone = c.text.trim();
    }
    try {
      final r = await app.api!.netSetMe(discoverable: on, phone: phone);
      if (mounted) setState(() => _me = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Widget _meTab() {
    final inv = _invite;
    final qr = inv?['qr_png_b64'] as String? ?? '';
    return ListView(padding: const EdgeInsets.all(16), children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_me['label'] as String? ?? '', style: display(22)),
          const SizedBox(height: 4),
          Row(children: [
            Text(_me['handle_display'] as String? ?? '', style: const TextStyle(color: C.accent, fontWeight: FontWeight.w700, fontSize: 16)),
            IconButton(icon: const Icon(Icons.edit_rounded, size: 18, color: C.muted), onPressed: _editHandle),
            IconButton(
              icon: const Icon(Icons.copy_rounded, size: 18, color: C.muted),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: _me['handle_display'] as String? ?? ''));
                _snack('Hoola ID copied');
              },
            ),
          ]),
          Text('${_me['connections'] ?? 0} connected · ${_me['requests'] ?? 0} requests · ${_me['inbox'] ?? 0} waiting',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      ),
      const SizedBox(height: 14),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Connect by QR / link', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Show the QR to the other person or send them the link. It works once, for 7 days. You must say yes before connecting.',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          const SizedBox(height: 10),
          if (qr.isNotEmpty)
            Center(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: Image.memory(base64Decode(qr), width: 220, height: 220, gaplessPlayback: true),
              ),
            ),
          if (inv != null) ...[
            const SizedBox(height: 8),
            SelectableText(inv['url'] as String? ?? '', style: const TextStyle(fontSize: 12.5, color: C.chip)),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: 'Connect with my Hoola: ${inv['url']}'));
                  _snack('Link copied, send it on WhatsApp / SMS');
                },
                icon: const Icon(Icons.share_rounded, size: 18),
                label: const Text('Link copy'),
              ),
            ),
          ],
          GradientButton(label: inv == null ? 'QR banaiye' : 'New QR', icon: Icons.qr_code_2_rounded, height: 46, onTap: _makeInvite),
        ]),
      ),
      const SizedBox(height: 14),
      Glass(
        child: SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Let people find me by mobile number'),
          subtitle: const Text('If turned off, people can connect only with a Hoola ID / QR', style: TextStyle(fontSize: 12)),
          value: _me['discoverable'] == true,
          onChanged: _discover,
        ),
      ),
    ]);
  }

  // ---------------------------------------------------------------- Jude log
  Future<void> _addDialog() async {
    final to = TextEditingController();
    final note = TextEditingController();
    var rel = 'friend';
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Connect to someone\'s Hoola'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: to, decoration: const InputDecoration(labelText: 'Hoola ID (@kunal.raj, on another server @kunal@server.in) or mobile number')),
              const SizedBox(height: 10),
              Wrap(spacing: 6, children: [
                for (final e in _relations.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: rel == e.key,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: rel == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                    onSelected: (_) => set(() => rel = e.key),
                  ),
              ]),
              TextField(controller: note, decoration: const InputDecoration(labelText: 'A short note (optional)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Send request')),
          ],
        ),
      ),
    );
    if (ok != true || to.text.trim().isEmpty) return;
    try {
      final r = await app.api!.netConnect(to: to.text.trim(), relation: rel, note: note.text.trim());
      _snack(r['status'] == 'active' ? 'Connected ✓' : 'Request sent. Waiting for their yes.');
      _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _linkSheet(Map<String, dynamic> l) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) {
        Future<void> patch(Map<String, dynamic> b) async {
          try {
            final r = await app.api!.netUpdateLink(l['id'] as String, b);
            set(() => l.addAll(r));
            _load();
          } catch (e) {
            _snack(e.toString());
          }
        }

        Future<void> act(String a) async {
          Navigator.of(ctx).pop();
          final err = await app.hoolaAnswer(l['id'] as String, a);
          if (err != null) _snack(err);
          _load();
        }

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(l['label'] as String? ?? '', style: display(20)),
              Text('@${l['handle'] ?? ''}', style: const TextStyle(color: C.muted)),
              if (l['safety_code'] != null) ...[
                const SizedBox(height: 10),
                const Text('Safety code (must be the same on both phones)', style: TextStyle(color: C.muted, fontSize: 12.5)),
                Text(l['safety_code'] as String, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 2)),
              ],
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Code matches (verified)'),
                value: l['verified'] == true,
                onChanged: (v) => patch({'verified': v}),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('VIP (always reach me)'),
                value: l['vip'] == true,
                onChanged: (v) => patch({'vip': v}),
              ),
              Wrap(spacing: 6, children: [
                for (final e in _relations.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: l['relation'] == e.key,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: l['relation'] == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                    onSelected: (_) => patch({'relation': e.key}),
                  ),
              ]),
              const SizedBox(height: 10),
              Row(children: [
                TextButton(onPressed: () => act('remove'), child: const Text('Hataiye')),
                const Spacer(),
                TextButton(onPressed: () => act(l['status'] == 'blocked' ? 'unblock' : 'block'),
                    child: Text(l['status'] == 'blocked' ? 'Unblock' : 'Block', style: const TextStyle(color: C.bad))),
              ]),
            ]),
          ),
        );
      }),
    );
  }

  Widget _linksTab() {
    final incoming = _links.where((l) => l['status'] == 'incoming').toList();
    final active = _links.where((l) => l['status'] == 'active').toList();
    final waiting = _links.where((l) => l['status'] == 'requested').toList();
    final other = _links.where((l) => l['status'] == 'blocked' || l['status'] == 'declined').toList();
    Widget tile(Map<String, dynamic> l, String sub) => ListTile(
          contentPadding: EdgeInsets.zero,
          leading: CircleAvatar(
            backgroundColor: C.panel,
            child: Text((l['owner_name'] as String? ?? 'H').isEmpty ? 'H' : (l['owner_name'] as String).substring(0, 1).toUpperCase()),
          ),
          title: Text(l['label'] as String? ?? ''),
          subtitle: Text(sub, style: const TextStyle(fontSize: 12)),
          trailing: Wrap(spacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
            if (l['status'] == 'active')
              IconButton(
                tooltip: 'Talk',
                visualDensity: VisualDensity.compact,
                onPressed: () => _startChat(l),
                icon: const Icon(Icons.chat_bubble_rounded, color: C.accent, size: 20),
              ),
            if (l['vip'] == true) const Icon(Icons.star_rounded, color: C.accent, size: 18),
            if (l['verified'] == true) const Icon(Icons.verified_rounded, color: C.ok, size: 18),
            if (l['key_warning'] == true) const Icon(Icons.warning_rounded, color: C.bad, size: 18),
          ]),
          onTap: () => _linkSheet(l),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Connect someone', icon: Icons.person_add_alt_1_rounded, height: 46, onTap: _addDialog),
      const SizedBox(height: 12),
      for (final l in incoming) HoolaConnectCard(v: l, app: app),
      if (active.isNotEmpty) const Text('Connected', style: TextStyle(fontWeight: FontWeight.w700)),
      for (final l in active) tile(l, '@${l['handle']} · ${_relations[l['relation']] ?? ''}'),
      if (waiting.isNotEmpty) const Padding(padding: EdgeInsets.only(top: 12), child: Text('Waiting for your yes', style: TextStyle(fontWeight: FontWeight.w700))),
      for (final l in waiting) tile(l, '@${l['handle']} · request sent'),
      if (other.isNotEmpty) const Padding(padding: EdgeInsets.only(top: 12), child: Text('Band', style: TextStyle(fontWeight: FontWeight.w700))),
      for (final l in other) tile(l, l['status'] == 'blocked' ? 'Block' : 'Mana kiya'),
      if (_links.isEmpty)
        const Padding(
          padding: EdgeInsets.all(20),
          child: Text('Nobody is connected yet. Show your QR or enter someone\'s Hoola ID to connect.', style: TextStyle(color: C.muted)),
        ),
    ]);
  }

  /// Open the chat with a connected person (their latest conversation, or a new one with a first message).
  Future<void> _startChat(Map<String, dynamic> l) async {
    final had = _threads.where((t) => t['peer'] == l['peer']).toList();
    if (had.isNotEmpty) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaThreadScreen(app: app, threadId: had.first['id'] as String)));
      await _load();
      return;
    }
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${l['label'] ?? ''} se baat'),
        content: TextField(controller: c, minLines: 2, maxLines: 5, decoration: InputDecoration(hintText: 'What should ${app.aName} say to their Hoola?')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Send')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    try {
      final r = await app.api!.netSend('@${l['handle']}', 'message', {'text': c.text.trim()});
      if (!mounted) return;
      final tid = r['thread_id'] as String? ?? '';
      if (tid.isNotEmpty) await Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaThreadScreen(app: app, threadId: tid)));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  // ---------------------------------------------------------------- Inbox + Baatein
  Widget _inboxTab() => ListView(padding: const EdgeInsets.all(16), children: [
        if (_inbox.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('No requests waiting. Whatever other Hoolas send will come here, according to your rules.', style: TextStyle(color: C.muted)),
          ),
        for (final m in _inbox) HoolaKnockCard(key: ValueKey(m['id']), v: m, app: app),
      ]);

  Widget _threadsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        if (_threads.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('No conversations yet. Say in the chat: "Ask Kunal\'s Hoola if he is free tomorrow".', style: TextStyle(color: C.muted)),
          ),
        for (final t in _threads)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Stack(clipBehavior: Clip.none, children: [
              CircleAvatar(
                backgroundColor: C.violet.withOpacity(.35),
                child: Text(((t['peer_avatar'] as String?) ?? 'H').isEmpty ? 'H' : (t['peer_avatar'] as String).substring(0, 1).toUpperCase(),
                    style: const TextStyle(fontWeight: FontWeight.w800, color: C.ink)),
              ),
              if (t['mode'] == 'handle')
                const Positioned(right: -4, bottom: -4, child: Icon(Icons.smart_toy_rounded, size: 16, color: C.teal)),
            ]),
            title: Text(
                (t['peer_avatar'] as String? ?? '').isNotEmpty
                    ? '${t['peer_avatar']}${(t['peer_owner'] as String? ?? '').isNotEmpty ? '  ·  ${t['peer_owner']}' : ''}'
                    : t['with'] as String? ?? '',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(
                '${t['last_dir'] == 'out' ? 'Aapka ${t['my_avatar'] ?? app.aName}: ' : ''}'
                '${t['last_kind'] == 'file' ? '📎 ' : ''}${(t['last'] as String? ?? '').isNotEmpty ? t['last'] : (t['subject'] ?? '')}',
                maxLines: 2,
                overflow: TextOverflow.ellipsis),
            trailing: Text(t['status'] == 'open' ? '' : '${t['status']}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaThreadScreen(app: app, threadId: t['id'] as String))),
          ),
      ]);

  Future<void> _newGroup() async {
    final name = TextEditingController();
    final active = _links.where((l) => l['status'] == 'active').toList();
    final picked = <String>{};
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('New group'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Name (e.g. FNW Field, Home)')),
              const SizedBox(height: 10),
              const Text('Whom to invite (connected people)', style: TextStyle(color: C.muted, fontSize: 12.5)),
              for (final l in active)
                CheckboxListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: picked.contains(l['peer']),
                  title: Text(l['label'] as String? ?? ''),
                  onChanged: (v) => set(() => v == true ? picked.add(l['peer'] as String) : picked.remove(l['peer'])),
                ),
              if (active.isEmpty) const Text('Connect some people first.', style: TextStyle(color: C.faint)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Banaiye')),
          ],
        ),
      ),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    try {
      final r = await app.api!.netGroupCreate(name.text.trim(), picked.toList());
      _snack('Group created; invited ${(r['invited'] as List? ?? const []).length} people');
      _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Widget _groupsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'New group', icon: Icons.group_add_rounded, height: 46, onTap: _newGroup),
        const SizedBox(height: 12),
        for (final g in _groups)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Text(g['emoji'] as String? ?? '👥', style: const TextStyle(fontSize: 26)),
            title: Text(g['name'] as String? ?? ''),
            subtitle: Text(g['status'] == 'invited' ? 'You have an invite' : '${g['count']} log · ${g['role'] == 'admin' ? 'aap admin' : g['hub']}'),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaGroupScreen(app: app, gid: g['gid'] as String))),
          ),
        if (_groups.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('The Hoolas of a team, family or partners in one group: everyone\'s avatars talk, share work and learn.',
                style: TextStyle(color: C.muted)),
          ),
      ]);

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 6,
        initialIndex: widget.initialTab,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Hoola Network'),
            backgroundColor: Colors.transparent,
            actions: [
              IconButton(
                tooltip: 'Dosti',
                icon: const Icon(Icons.diversity_3_rounded),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DostiScreen(app: app))),
              ),
              IconButton(
                tooltip: 'Buy and sell',
                icon: const Icon(Icons.shopping_bag_rounded),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DealsScreen(app: app))),
              ),
              IconButton(
                tooltip: 'Business',
                icon: const Icon(Icons.storefront_rounded),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaBusinessScreen(app: app))),
              ),
            ],
            bottom: TabBar(isScrollable: true, tabs: [
              const Tab(text: 'My ID'),
              Tab(text: 'Connected people${(_me['requests'] ?? 0) > 0 ? ' (${_me['requests']})' : ''}'),
              Tab(text: 'Inbox${_inbox.isNotEmpty ? ' (${_inbox.length})' : ''}'),
              const Tab(text: 'Conversations'),
              const Tab(text: 'Groups'),
              const Tab(text: 'Community'),
            ]),
          ),
          body: Aurora(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _err != null
                    ? Center(child: Padding(padding: const EdgeInsets.all(20), child: Text(_err!, style: const TextStyle(color: C.bad))))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: TabBarView(children: [_meTab(), _linksTab(), _inboxTab(), _threadsTab(), _groupsTab(), SamajListView(app: app)]),
                      ),
          ),
        ),
      );
}

/// One avatar-to-avatar conversation as a real chat: both avatars by name, photos / videos / PDFs, what the avatar
/// saw, reply ideas, attach, "banwao" (the avatar makes a PDF / picture) and "tum sambhalo" for the whole talk.
class HoolaThreadScreen extends StatefulWidget {
  const HoolaThreadScreen({super.key, required this.app, required this.threadId});
  final Santosh app;
  final String threadId;
  @override
  State<HoolaThreadScreen> createState() => _HoolaThreadScreenState();
}

class _HoolaThreadScreenState extends State<HoolaThreadScreen> {
  Map<String, dynamic> _t = {};
  final _text = TextEditingController();
  bool _busy = false;
  bool _loading = true;
  String? _sending;            // name of a file going out right now
  int _tick = -1;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _tick = app.hoolaTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _text.dispose();
    super.dispose();
  }

  /// Something happened on the Hoola Network (reply, knock, what the avatar saw): refresh this chat.
  void _onApp() {
    if (app.hoolaTick == _tick) return;
    _tick = app.hoolaTick;
    Future<void>.delayed(const Duration(milliseconds: 250), _load);
  }

  void _snack(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.netThread(widget.threadId);
      if (mounted) setState(() { _t = r; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
      _snack(e.toString());
    }
  }

  Future<void> _send() async {
    final t = _text.text.trim();
    if (t.isEmpty) return;
    setState(() => _busy = true);
    try {
      if (_t['kind'] == 'dosti') {          // v0.160 her word in a Dosti chat: the avatar's chat goes on, streak resets
        await app.api!.dostiAct('talk', {'thread_id': widget.threadId, 'text': t});
      } else {
        await app.api!.netReply(widget.threadId, t);
      }
      _text.clear();
      await _load();
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _attach(FileType type) async {
    final picked = await pickAttachmentsOfType(context, type);
    if (picked.isEmpty) return;
    final f = picked.first;
    final caption = _text.text.trim();
    setState(() => _sending = f.name);
    try {
      final r = await app.api!.netUpload(f.name, f.bytes, threadId: widget.threadId, text: caption);
      _text.clear();
      if (r['status'] == 'declined' || r['status'] == 'refused') _snack('Their Hoola did not accept it: ${r['reason'] ?? ''}');
      await _load();
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() => _sending = null);
    }
  }

  Future<void> _attachMenu() async {
    final pick = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.photo_rounded, color: C.accent), title: const Text('Photo'), onTap: () => Navigator.pop(ctx, 'image')),
          ListTile(leading: const Icon(Icons.videocam_rounded, color: C.accent), title: const Text('Video'), onTap: () => Navigator.pop(ctx, 'video')),
          ListTile(leading: const Icon(Icons.audiotrack_rounded, color: C.accent), title: const Text('Audio'), onTap: () => Navigator.pop(ctx, 'audio')),
          ListTile(leading: const Icon(Icons.attach_file_rounded, color: C.accent), title: const Text('PDF / document / any file'), onTap: () => Navigator.pop(ctx, 'any')),
          const Divider(height: 1),
          ListTile(
              leading: const Icon(Icons.auto_awesome_rounded, color: C.teal),
              title: Text('${app.aName} se banwaiye'),
              subtitle: const Text('PDF (quotation, note, agenda) or picture'),
              onTap: () => Navigator.pop(ctx, 'make')),
        ]),
      ),
    );
    switch (pick) {
      case 'image':
        await _attach(FileType.image);
      case 'video':
        await _attach(FileType.video);
      case 'audio':
        await _attach(FileType.audio);
      case 'any':
        await _attach(FileType.any);
      case 'make':
        await _make();
    }
  }

  Future<void> _make() async {
    String kind = 'pdf';
    final title = TextEditingController();
    final content = TextEditingController(text: _text.text.trim());
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text('${app.aName} will make it'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(spacing: 8, children: [
                for (final e in const {'pdf': '📄 Document (PDF)', 'image': '🖼️ Picture'}.entries)
                  ChoiceChip(
                    label: Text(e.value),
                    selected: kind == e.key,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: kind == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
                    onSelected: (_) => set(() => kind = e.key),
                  ),
              ]),
              TextField(controller: title, decoration: const InputDecoration(hintText: 'Title (jaise: FNW Quotation)')),
              TextField(
                controller: content,
                minLines: 3,
                maxLines: 8,
                decoration: InputDecoration(
                    hintText: kind == 'pdf' ? 'What should it say? (rates, points, note…)' : 'What should the picture show? (e.g. Diwali greeting, FNW name)'),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Make')),
          ],
        ),
      ),
    );
    if (ok != true || content.text.trim().isEmpty) return;
    setState(() => _sending = kind == 'pdf' ? 'Making the document…' : 'Making the picture…');
    Map<String, dynamic>? f;
    try {
      f = await app.api!.netMake(kind, title.text.trim(), content.text.trim());
    } catch (e) {
      _snack(e.toString());
    }
    if (mounted) setState(() => _sending = null);
    if (f == null || !mounted) return;
    final made = f;
    final send = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Send this?'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          HoolaMediaTile(body: {'local': made}, app: app, maxWidth: 280),
          const SizedBox(height: 6),
          Text('${_t['peer_avatar'] ?? _t['with'] ?? ''} will receive it.', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Do not send')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Send')),
        ],
      ),
    );
    if (send != true) return;
    try {
      await app.api!.netSend(_t['peer'] as String, 'file', {'file_id': made['file_id'], 'text': title.text.trim()}, threadId: widget.threadId);
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _toggleHandle() async {
    final on = _t['mode'] == 'handle';
    String goal = '';
    if (!on) {
      final c = TextEditingController(text: _text.text.trim());
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text('${app.aName}, you handle it'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${app.aName} will talk by itself within your rules (up to 6 turns), and will call you if it gets stuck. '
                'It never gives money, files or private information on its own.', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            TextField(controller: c, minLines: 2, maxLines: 4, decoration: const InputDecoration(hintText: 'Goal: e.g. "fix a meeting tomorrow at 5"')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Start')),
          ],
        ),
      );
      if (ok != true) return;
      goal = c.text.trim();
    }
    try {
      final r = await app.api!.netHandle(widget.threadId, on ? 'stop' : 'start', goal: goal);
      if (mounted) setState(() => _t = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _decide(Map<String, dynamic> m, String action) async {
    final err = await app.hoolaDecide(m['id'] as String, action, slot: m['kind'] == 'meeting' ? 0 : null);
    if (err != null) _snack(err);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final msgs = List<Map<String, dynamic>>.from((_t['messages'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final peer = (_t['peer_avatar'] as String? ?? '').trim();
    final owner = (_t['peer_owner'] as String? ?? '').trim();
    final title = peer.isNotEmpty ? peer : (_t['with'] as String? ?? 'Conversations');
    final handling = _t['mode'] == 'handle';
    final lastIn = msgs.lastWhere((m) => m['direction'] == 'in', orElse: () => const <String, dynamic>{});
    final showIdeas = msgs.isNotEmpty && msgs.last['direction'] == 'in' && !handling;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        titleSpacing: 0,
        title: Row(children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: C.violet.withOpacity(.35),
            child: Text(title.isEmpty ? 'H' : title.substring(0, 1).toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w800, color: C.ink)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Flexible(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: display(17))),
                if (_t['verified'] == true) const Padding(padding: EdgeInsets.only(left: 4), child: Icon(Icons.verified_rounded, size: 16, color: C.ok)),
              ]),
              Text(
                [if (owner.isNotEmpty) '$owner ka avatar', if ((_t['handle'] ?? '') != '') '@${_t['handle']}'].join(' · '),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: C.muted, fontSize: 11.5),
              ),
            ]),
          ),
        ]),
        actions: [
          IconButton(
            tooltip: handling ? 'Stop handling it automatically' : '${app.aName}, you handle it',
            onPressed: _toggleHandle,
            icon: Icon(Icons.smart_toy_rounded, color: handling ? C.teal : C.muted),
          ),
        ],
      ),
      body: Aurora(
        child: Column(children: [
          if (handling)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
              color: const Color(0x222DD4BF),
              child: Row(children: [
                const Icon(Icons.smart_toy_rounded, size: 18, color: C.teal),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('${app.aName} is talking by itself · Goal: ${_t['goal'] ?? ''}',
                      style: const TextStyle(color: C.teal, fontSize: 12.5)),
                ),
                TextButton(onPressed: _toggleHandle, child: const Text('Rokiye')),
              ]),
            ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : msgs.isEmpty
                    ? Center(child: Text('No messages yet. Tell ${app.aName} what to say.', style: const TextStyle(color: C.muted)))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.builder(
                          reverse: true,
                          padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
                          itemCount: msgs.length,
                          itemBuilder: (_, i) {
                            final m = msgs[msgs.length - 1 - i];
                            final prev = msgs.length - 2 - i >= 0 ? msgs[msgs.length - 2 - i] : null;
                            return _Bubble(
                              key: ValueKey(m['id']),
                              m: m,
                              app: app,
                              showName: prev == null || prev['direction'] != m['direction'],
                              onDecide: (a) => _decide(m, a),
                            );
                          },
                        ),
                      ),
          ),
          if (_sending != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
              child: Row(children: [
                const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                const SizedBox(width: 8),
                Expanded(child: Text(_sending!, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5))),
              ]),
            ),
          if (showIdeas)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 2),
              child: HoolaInsight(v: lastIn, showGist: false, onPick: (t) => setState(() {
                _text.text = t;
                _text.selection = TextSelection.collapsed(offset: t.length);
              })),
            ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(6, 4, 10, 10),
              child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                IconButton(
                  tooltip: 'Send a photo, video or PDF',
                  onPressed: _sending != null ? null : _attachMenu,
                  icon: const Icon(Icons.add_circle_rounded, color: C.accent, size: 28),
                ),
                Expanded(
                  child: TextField(
                    controller: _text,
                    minLines: 1,
                    maxLines: 5,
                    textCapitalization: TextCapitalization.sentences,
                    decoration: InputDecoration(hintText: 'What should ${app.aName} say to ${title.isEmpty ? 'their Hoola' : title}…'),
                  ),
                ),
                IconButton(onPressed: _busy ? null : _send, icon: const Icon(Icons.send_rounded, color: C.accent)),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

/// One message: the avatar's name on top, words, photo / video / PDF, what was seen, and Haan / Mana if it waits.
class _Bubble extends StatelessWidget {
  const _Bubble({super.key, required this.m, required this.app, required this.showName, required this.onDecide});
  final Map<String, dynamic> m;
  final Santosh app;
  final bool showName;
  final ValueChanged<String> onDecide;

  static const _kindText = {
    'dosti_msg': '🤝 friendship', 'doc_ask': '📄 document request', 'ask': '❓ question', 'meeting': '📅 meeting', 'task': '✅ task', 'reminder': '⏰ reminder', 'voice_note': '🎙️ voice note',
    'email': '✉️ email', 'link': '🔗 link', 'presentation': '📊 presentation', 'payment_request': '₹ payment request',
    'contact_card': '👤 contact', 'location': '📍 place', 'meeting_ok': '📅 meeting confirmed', 'meeting_no': '📅 meeting declined',
  };

  String _status(String s) => switch (s) {
        'pending' => 'waiting for your decision',
        'snoozed' => 'later',
        'declined' => 'mana kiya',
        'blocked' => 'blocked',
        'refused' => 'their Hoola did not accept it',
        'accepted' => 'said yes ✓',
        'handled' => 'Hoola ne sambhala',
        _ => '',
      };

  @override
  Widget build(BuildContext context) {
    final out = m['direction'] == 'out';
    final b = Map<String, dynamic>.from(m['body'] as Map? ?? const {});
    final name = (m['avatar'] as String? ?? '').trim().isNotEmpty ? m['avatar'] as String : (out ? app.aName : (m['from'] as String? ?? ''));
    final byAvatar = m['by_avatar'] == true || b['by_avatar'] == true || b['made_by_avatar'] == true;
    final text = ((b['translated'] as String?) ?? (b['text'] as String? ?? '')).trim();
    final status = m['status'] as String? ?? '';
    final pending = !out && (status == 'pending' || status == 'snoozed');
    final hasMedia = (b['name'] ?? b['preview'] ?? b['local']) != null && const {'file', 'presentation', 'voice_note'}.contains(m['kind']);
    final at = DateTime.tryParse(m['at'] as String? ?? '')?.toLocal();
    final time = at == null ? '' : '${at.hour.toString().padLeft(2, '0')}:${at.minute.toString().padLeft(2, '0')}';
    final lines = <String>[
      if ((b['title'] ?? '') != '' && m['kind'] != 'file') '${b['title']}',
      if (text.isNotEmpty) text,
      if ((b['note'] ?? '') != '' && b['note'] != text) '${b['note']}',
      if ((b['url'] ?? '') != '') '🔗 ${b['url']}',
      if ((b['place'] ?? '') != '') '📍 ${b['place']}',
      if (b['amount'] != null) '₹${b['amount']} ${b['upi_note'] ?? ''}',
      // v0.160 Dosti: work experience / skills / a document asked for, shown inside the bubble
      for (final e in (b['experiences'] as List? ?? const []))
        if (e is Map) '🧠 ${e['title'] ?? ''}${(e['learned'] ?? '') != '' ? '\n   seekha: ${e['learned']}' : ''}',
      for (final k in (b['skills'] as List? ?? const []))
        if (k is Map) '🎓 skill: ${k['name'] ?? ''}',
      if (b['doc'] is Map && ((b['doc'] as Map)['what'] ?? '') != '') '📄 asked for: ${(b['doc'] as Map)['what']}',
    ];
    final st = _status(status);
    return Padding(
      padding: EdgeInsets.only(top: showName ? 10 : 3),
      child: Column(crossAxisAlignment: out ? CrossAxisAlignment.end : CrossAxisAlignment.start, children: [
        if (showName)
          Padding(
            padding: const EdgeInsets.only(left: 6, right: 6, bottom: 3),
            child: Text(out ? 'Your $name' : name,
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: out ? C.accentSoft : C.teal)),
          ),
        Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * .8),
          padding: const EdgeInsets.fromLTRB(11, 8, 11, 6),
          decoration: BoxDecoration(
            color: out ? const Color(0x33FFB15C) : C.panel,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: Radius.circular(out ? 16 : 4),
              bottomRight: Radius.circular(out ? 4 : 16),
            ),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            if (_kindText[m['kind']] != null)
              Text(_kindText[m['kind']]!, style: const TextStyle(color: C.faint, fontSize: 10.5, fontWeight: FontWeight.w600)),
            if (hasMedia) HoolaMediaTile(body: b, app: app, locked: pending, maxWidth: 250),
            if (lines.isNotEmpty) Padding(padding: EdgeInsets.only(top: hasMedia ? 6 : 0), child: Text(lines.join('\n'), style: const TextStyle(fontSize: 14, height: 1.3))),
            if (!out) HoolaSeen(app: app, v: {'seen': b['seen'], 'summary': b['summary']}),
            if (!out && b['scan'] is Map && (b['scan'] as Map)['verdict'] == 'danger')
              const Padding(padding: EdgeInsets.only(top: 4), child: Text('⛔ Looked dangerous on checking', style: TextStyle(color: C.bad, fontSize: 12))),
            if (pending)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Wrap(spacing: 6, children: [
                  FilledButton.tonal(onPressed: () => onDecide('accept'), child: const Text('Yes')),
                  TextButton(onPressed: () => onDecide('decline'), child: const Text('Mana', style: TextStyle(color: C.bad))),
                  if (const {'message', 'ask', 'meeting', 'task', 'reminder', 'voice_note'}.contains(m['kind']))
                    TextButton(onPressed: () => onDecide('handle'), child: Text('${app.aName}, handle it', style: const TextStyle(color: C.teal))),
                ]),
              ),
            const SizedBox(height: 2),
            Row(mainAxisSize: MainAxisSize.min, children: [
              if (byAvatar) const Padding(padding: EdgeInsets.only(right: 4), child: Icon(Icons.smart_toy_rounded, size: 12, color: C.teal)),
              if (st.isNotEmpty && !pending) Text('$st · ', style: const TextStyle(color: C.faint, fontSize: 10.5)),
              Text(time, style: const TextStyle(color: C.faint, fontSize: 10.5)),
            ]),
          ]),
        ),
      ]),
    );
  }
}


/// One Mandali: members, posts (what every avatar shared), and a box to post / give a task.
class HoolaGroupScreen extends StatefulWidget {
  const HoolaGroupScreen({super.key, required this.app, required this.gid});
  final Santosh app;
  final String gid;
  @override
  State<HoolaGroupScreen> createState() => _HoolaGroupScreenState();
}

class _HoolaGroupScreenState extends State<HoolaGroupScreen> {
  Map<String, dynamic> _g = {};
  final _text = TextEditingController();
  String _kind = 'message';
  String? _assign;
  bool _busy = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<void> _load() async {
    try {
      final r = await app.api!.netGroup(widget.gid);
      if (mounted) setState(() => _g = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _post() async {
    final t = _text.text.trim();
    if (t.isEmpty) return;
    if (_kind == 'task' && _assign == null) {
      _snack('Who should get the task? Choose a member.');
      return;
    }
    setState(() => _busy = true);
    try {
      await app.api!.netGroupPost(widget.gid, {'kind': _kind, 'text': t, if (_kind == 'task') 'title': t.length > 60 ? t.substring(0, 60) : t,
        if (_kind == 'task') 'assign_to': _assign});
      _text.clear();
      await _load();
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _digest() async {
    try {
      final r = await app.api!.netGroupAct(widget.gid, 'digest');
      if (!mounted) return;
      showDialog(context: context, builder: (ctx) => AlertDialog(
          title: Text('${r['group']} · ${r['posts']} posts'), content: SingleChildScrollView(child: Text(r['summary'] as String? ?? ''))));
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _act(String action, {String mute = ''}) async {
    try {
      await app.api!.netGroupAct(widget.gid, action, mute: mute);
      if (action == 'leave' && mounted) {
        Navigator.of(context).pop();
        return;
      }
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final posts = List<Map<String, dynamic>>.from((_g['posts'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final members = List<Map<String, dynamic>>.from((_g['members'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Scaffold(
      appBar: AppBar(
        title: Text('${_g['emoji'] ?? '👥'} ${_g['name'] ?? 'Groups'}'),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(icon: const Icon(Icons.summarize_rounded), tooltip: 'What happened', onPressed: _digest),
          PopupMenuButton<String>(
            onSelected: (v) => v.startsWith('mute:') ? _act('mute', mute: v.substring(5)) : _act(v),
            itemBuilder: (_) => [
              PopupMenuItem(value: 'mute:all', child: Text('Show all${_g['mute'] == 'all' ? ' ✓' : ''}')),
              PopupMenuItem(value: 'mute:mentions', child: Text('Only my mentions / tasks${_g['mute'] == 'mentions' ? ' ✓' : ''}')),
              PopupMenuItem(value: 'mute:digest', child: Text('Digest only${_g['mute'] == 'digest' ? ' ✓' : ''}')),
              if (_g['role'] != 'admin') const PopupMenuItem(value: 'leave', child: Text('Leave group')),
            ],
          ),
        ],
      ),
      body: Aurora(
        child: Column(children: [
          SizedBox(
            height: 40,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              for (final m in members)
                Padding(padding: const EdgeInsets.only(right: 6), child: Chip(label: Text(m['label'] as String? ?? '', style: const TextStyle(fontSize: 12)))),
            ]),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(12), children: [
                for (final p in posts) HoolaGroupPostCard(key: ValueKey(p['id']), v: {...p, 'group': ''}, app: app),
                if (posts.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('No posts yet.', style: TextStyle(color: C.muted))),
              ]),
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
              child: Column(children: [
                Row(children: [
                  for (final k in const {'message': 'Baat', 'ask': 'Question', 'task': 'Kaam do'}.entries)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(k.value),
                        selected: _kind == k.key,
                        showCheckmark: false,
                        selectedColor: C.accent,
                        labelStyle: TextStyle(color: _kind == k.key ? C.onAccent : C.chip, fontSize: 12.5),
                        onSelected: (_) => setState(() => _kind = k.key),
                      ),
                    ),
                  if (_kind == 'task')
                    Expanded(
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: _assign,
                        hint: const Text('Who?'),
                        items: [
                          for (final m in members)
                            DropdownMenuItem(value: m['address'] as String, child: Text(m['label'] as String? ?? '', overflow: TextOverflow.ellipsis)),
                        ],
                        onChanged: (v) => setState(() => _assign = v),
                      ),
                    ),
                ]),
                Row(children: [
                  Expanded(
                    child: TextField(controller: _text, minLines: 1, maxLines: 4,
                        decoration: InputDecoration(hintText: '${app.aName} will send to the group…')),
                  ),
                  IconButton(onPressed: _busy ? null : _post, icon: const Icon(Icons.send_rounded, color: C.accent)),
                ]),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
