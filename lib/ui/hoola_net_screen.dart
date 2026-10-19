import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../state.dart';
import 'glass.dart';
import 'hoola_cards.dart';
import 'hoola_business_screen.dart';
import 'hoola_samaj_screen.dart';

const _relations = {'family': 'Parivar', 'team': 'Team', 'business': 'Business', 'friend': 'Dost'};

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
        title: const Text('Hoola ID badliye'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: c, decoration: const InputDecoration(prefixText: '@', hintText: 'meghana.fnw')),
          const SizedBox(height: 8),
          const Text('Chhote angrezi akshar, number, . ya _. Pehle hafte mein kabhi bhi; uske baad saal mein ek baar.',
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
          title: const Text('Number se dhoondhne dein'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: c, keyboardType: TextInputType.phone, decoration: const InputDecoration(hintText: 'Aapka mobile number')),
            const SizedBox(height: 8),
            const Text('Number chhupa (hashed) rakha jata hai. Jo aapka number jaante hain, wahi aapka Hoola dhoondh payenge; '
                'judne ke liye phir bhi aapki haan chahiye.', style: TextStyle(fontSize: 12, color: C.muted)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Chalu karein')),
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
                _snack('Hoola ID copy ho gaya');
              },
            ),
          ]),
          Text('${_me['connections'] ?? 0} jude · ${_me['requests'] ?? 0} requests · ${_me['inbox'] ?? 0} intezaar mein',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if ((_me['server'] ?? '') != '' && _me['server'] != 'local')
            Text('Doosre Hoola server se: ${_me['handle_display']}@${_me['server']}', style: const TextStyle(color: C.faint, fontSize: 12)),
        ]),
      ),
      const SizedBox(height: 14),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('QR / link se jodiye', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Saamne wale ko QR dikhaiye ya link bhejiye. Ek baar chalta hai, 7 din tak. Judne se pehle aapko haan kehna hoga.',
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
                  Clipboard.setData(ClipboardData(text: 'Mere Hoola se judiye: ${inv['url']}'));
                  _snack('Link copy ho gaya, WhatsApp / SMS par bhej dijiye');
                },
                icon: const Icon(Icons.share_rounded, size: 18),
                label: const Text('Link copy'),
              ),
            ),
          ],
          GradientButton(label: inv == null ? 'QR banaiye' : 'Naya QR', icon: Icons.qr_code_2_rounded, height: 46, onTap: _makeInvite),
        ]),
      ),
      const SizedBox(height: 14),
      Glass(
        child: SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Mobile number se mujhe dhoondh sakein'),
          subtitle: const Text('Band rakhenge to sirf Hoola ID / QR se', style: TextStyle(fontSize: 12)),
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
          title: const Text('Kisi ke Hoola se jodiye'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: to, decoration: const InputDecoration(labelText: 'Hoola ID (@kunal.raj, doosre server par @kunal@server.in) ya mobile number')),
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
              TextField(controller: note, decoration: const InputDecoration(labelText: 'Chhota sa note (optional)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Request bhejo')),
          ],
        ),
      ),
    );
    if (ok != true || to.text.trim().isEmpty) return;
    try {
      final r = await app.api!.netConnect(to: to.text.trim(), relation: rel, note: note.text.trim());
      _snack(r['status'] == 'active' ? 'Jud gaye ✓' : 'Request bhej di. Unki haan ka intezaar.');
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
                const Text('Safety code (dono phone par same hona chahiye)', style: TextStyle(color: C.muted, fontSize: 12.5)),
                Text(l['safety_code'] as String, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 2)),
              ],
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Code mil gaya (verified)'),
                value: l['verified'] == true,
                onChanged: (v) => patch({'verified': v}),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('VIP (hamesha pahunchein)'),
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
          trailing: Wrap(spacing: 4, children: [
            if (l['vip'] == true) const Icon(Icons.star_rounded, color: C.accent, size: 18),
            if (l['verified'] == true) const Icon(Icons.verified_rounded, color: C.ok, size: 18),
            if (l['key_warning'] == true) const Icon(Icons.warning_rounded, color: C.bad, size: 18),
          ]),
          onTap: () => _linkSheet(l),
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      GradientButton(label: 'Kisi ko jodiye', icon: Icons.person_add_alt_1_rounded, height: 46, onTap: _addDialog),
      const SizedBox(height: 12),
      for (final l in incoming) HoolaConnectCard(v: l, app: app),
      if (active.isNotEmpty) const Text('Jude hue', style: TextStyle(fontWeight: FontWeight.w700)),
      for (final l in active) tile(l, '@${l['handle']} · ${_relations[l['relation']] ?? ''}'),
      if (waiting.isNotEmpty) const Padding(padding: EdgeInsets.only(top: 12), child: Text('Haan ka intezaar', style: TextStyle(fontWeight: FontWeight.w700))),
      for (final l in waiting) tile(l, '@${l['handle']} · request bheji'),
      if (other.isNotEmpty) const Padding(padding: EdgeInsets.only(top: 12), child: Text('Band', style: TextStyle(fontWeight: FontWeight.w700))),
      for (final l in other) tile(l, l['status'] == 'blocked' ? 'Block' : 'Mana kiya'),
      if (_links.isEmpty)
        const Padding(
          padding: EdgeInsets.all(20),
          child: Text('Abhi koi nahi juda. Apna QR dikhaiye ya kisi ka Hoola ID daal kar jodiye.', style: TextStyle(color: C.muted)),
        ),
    ]);
  }

  // ---------------------------------------------------------------- Inbox + Baatein
  Widget _inboxTab() => ListView(padding: const EdgeInsets.all(16), children: [
        if (_inbox.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('Koi request intezaar mein nahi. Doosre Hoola jo bhi bhejenge, aapke niyam se yahan aayega.', style: TextStyle(color: C.muted)),
          ),
        for (final m in _inbox) HoolaKnockCard(key: ValueKey(m['id']), v: m, app: app),
      ]);

  Widget _threadsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        if (_threads.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('Abhi koi baat-cheet nahi. Chat mein boliye: "Kunal ke Hoola se poochho kal free hain?"', style: TextStyle(color: C.muted)),
          ),
        for (final t in _threads)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(t['mode'] == 'handle' ? Icons.smart_toy_rounded : Icons.forum_rounded, color: C.teal),
            title: Text(t['with'] as String? ?? ''),
            subtitle: Text('${t['last_dir'] == 'out' ? 'Aap: ' : ''}${t['last'] ?? t['subject'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis),
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
          title: const Text('Nayi Mandali'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (jaise FNW Field, Ghar)')),
              const SizedBox(height: 10),
              const Text('Kise bulana hai (jude hue log)', style: TextStyle(color: C.muted, fontSize: 12.5)),
              for (final l in active)
                CheckboxListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: picked.contains(l['peer']),
                  title: Text(l['label'] as String? ?? ''),
                  onChanged: (v) => set(() => v == true ? picked.add(l['peer'] as String) : picked.remove(l['peer'])),
                ),
              if (active.isEmpty) const Text('Pehle logon ko jodiye.', style: TextStyle(color: C.faint)),
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
      _snack('Mandali ban gayi; ${(r['invited'] as List? ?? const []).length} logon ko invite gaya');
      _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Widget _groupsTab() => ListView(padding: const EdgeInsets.all(16), children: [
        GradientButton(label: 'Nayi Mandali', icon: Icons.group_add_rounded, height: 46, onTap: _newGroup),
        const SizedBox(height: 12),
        for (final g in _groups)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Text(g['emoji'] as String? ?? '👥', style: const TextStyle(fontSize: 26)),
            title: Text(g['name'] as String? ?? ''),
            subtitle: Text(g['status'] == 'invited' ? 'Invite aaya hai' : '${g['count']} log · ${g['role'] == 'admin' ? 'aap admin' : g['hub']}'),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaGroupScreen(app: app, gid: g['gid'] as String))),
          ),
        if (_groups.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('Team, parivar ya partners ke Hoola ek group mein: sab ke avatar baat karte, kaam baant-te aur seekhte hain.',
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
                tooltip: 'Business',
                icon: const Icon(Icons.storefront_rounded),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaBusinessScreen(app: app))),
              ),
            ],
            bottom: TabBar(isScrollable: true, tabs: [
              const Tab(text: 'Mera ID'),
              Tab(text: 'Jude log${(_me['requests'] ?? 0) > 0 ? ' (${_me['requests']})' : ''}'),
              Tab(text: 'Inbox${_inbox.isNotEmpty ? ' (${_inbox.length})' : ''}'),
              const Tab(text: 'Baatein'),
              const Tab(text: 'Mandali'),
              const Tab(text: 'Samaj'),
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

/// One avatar-to-avatar conversation, and a box to send what the owner wants to say.
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

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.netThread(widget.threadId);
      if (mounted) setState(() => _t = r);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _send() async {
    final t = _text.text.trim();
    if (t.isEmpty) return;
    setState(() => _busy = true);
    try {
      await widget.app.api!.netReply(widget.threadId, t);
      _text.clear();
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final msgs = List<Map<String, dynamic>>.from((_t['messages'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Scaffold(
      appBar: AppBar(title: Text(_t['with'] as String? ?? 'Baat-cheet'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: Column(children: [
          if (_t['mode'] == 'handle')
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              color: const Color(0x222DD4BF),
              child: Text('${widget.app.aName} yeh baat aapke niyam ke andar khud sambhal raha hai. Lakshya: ${_t['goal'] ?? ''}',
                  style: const TextStyle(color: C.teal, fontSize: 12.5)),
            ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(16), children: [
                for (final m in msgs)
                  Align(
                    alignment: m['direction'] == 'out' ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 300),
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: m['direction'] == 'out' ? const Color(0x33FFB15C) : C.panel,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${m['kind']} · ${m['status']}', style: const TextStyle(color: C.faint, fontSize: 10.5)),
                        Text(_msgText(m), style: const TextStyle(fontSize: 13.5)),
                      ]),
                    ),
                  ),
              ]),
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 10),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _text,
                    minLines: 1,
                    maxLines: 4,
                    decoration: InputDecoration(hintText: '${widget.app.aName} se kahiye kya bolna hai…'),
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

  String _msgText(Map<String, dynamic> m) {
    final b = Map<String, dynamic>.from(m['body'] as Map? ?? const {});
    final parts = <String>[
      if ((b['title'] ?? '') != '') '${b['title']}',
      if ((b['text'] ?? '') != '') '${b['text']}',
      if ((b['note'] ?? '') != '') '${b['note']}',
      if ((b['name'] ?? '') != '') '📎 ${b['name']}',
      if ((b['url'] ?? '') != '') '🔗 ${b['url']}',
      if (b['amount'] != null) '₹${b['amount']}',
    ];
    return parts.isEmpty ? '(${m['kind']})' : parts.join('\n');
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
      _snack('Kaam kise dena hai? Member chuniye.');
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
        title: Text('${_g['emoji'] ?? '👥'} ${_g['name'] ?? 'Mandali'}'),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(icon: const Icon(Icons.summarize_rounded), tooltip: 'Kya hua', onPressed: _digest),
          PopupMenuButton<String>(
            onSelected: (v) => v.startsWith('mute:') ? _act('mute', mute: v.substring(5)) : _act(v),
            itemBuilder: (_) => [
              PopupMenuItem(value: 'mute:all', child: Text('Sab dikhao${_g['mute'] == 'all' ? ' ✓' : ''}')),
              PopupMenuItem(value: 'mute:mentions', child: Text('Sirf mera zikr / kaam${_g['mute'] == 'mentions' ? ' ✓' : ''}')),
              PopupMenuItem(value: 'mute:digest', child: Text('Sirf digest${_g['mute'] == 'digest' ? ' ✓' : ''}')),
              if (_g['role'] != 'admin') const PopupMenuItem(value: 'leave', child: Text('Group chhodiye')),
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
                if (posts.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('Abhi koi post nahi.', style: TextStyle(color: C.muted))),
              ]),
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
              child: Column(children: [
                Row(children: [
                  for (final k in const {'message': 'Baat', 'ask': 'Sawaal', 'task': 'Kaam do'}.entries)
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
                        hint: const Text('Kise?'),
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
                        decoration: InputDecoration(hintText: '${app.aName} group mein bhejega…')),
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
