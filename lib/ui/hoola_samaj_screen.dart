import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

/// "Mera avatar ne kya seekha": private lessons (forget any), what was shared, installed skills (switch off any).
class HoolaLearnedScreen extends StatefulWidget {
  const HoolaLearnedScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaLearnedScreen> createState() => _HoolaLearnedScreenState();
}

class _HoolaLearnedScreenState extends State<HoolaLearnedScreen> {
  List<Map<String, dynamic>> _lessons = [];
  List<Map<String, dynamic>> _skills = [];
  bool _loading = true;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  List<Map<String, dynamic>> _list(dynamic x) =>
      List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  Future<void> _load() async {
    try {
      final r = await app.api!.netLearned();
      if (mounted) setState(() { _lessons = _list(r['lessons']); _skills = _list(r['skills']); _loading = false; });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  Future<void> _do(Future<dynamic> Function() f) async {
    try {
      await f();
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('${app.aName} ne kya seekha'), backgroundColor: Colors.transparent),
        body: Aurora(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.all(16), children: [
                    Text(app.g('${app.aName} aapke kaam se seekhta hai: kya chala, kya nahi, sahi tareeka. Yeh sirf aapka hai; '
                        'Samaj ke saath share karne se pehle personal jaankari hata di jaati hai, aur aapke niyam ke hisaab se poocha jata hai.'),
                        style: const TextStyle(color: C.muted, fontSize: 13)),
                    const SizedBox(height: 12),
                    Text('Seekhi baatein (${_lessons.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
                    for (final l in _lessons)
                      Glass(
                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text(l['text'] as String? ?? '', style: const TextStyle(fontSize: 13.5)),
                              Text(
                                  '${(l['at'] as String? ?? '').split('T').first}'
                                  '${l['share_status'] == 'shared' ? ' · Samaj mein share ✓' : l['share_status'] == 'proposed' ? ' · share ka sawaal' : ''}',
                                  style: const TextStyle(color: C.faint, fontSize: 11.5)),
                            ]),
                          ),
                          IconButton(
                            tooltip: 'Bhool jao',
                            icon: const Icon(Icons.delete_outline_rounded, color: C.muted),
                            onPressed: () => _do(() => app.api!.netLessonAct(l['id'] as String, 'forget')),
                          ),
                        ]),
                      ),
                    if (_lessons.isEmpty)
                      const Padding(padding: EdgeInsets.all(12), child: Text('Abhi kuch nahi seekha.', style: TextStyle(color: C.faint))),
                    const SizedBox(height: 18),
                    Text('Lagi hui skills (${_skills.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
                    for (final k in _skills)
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(k['name'] as String? ?? ''),
                        subtitle: Text(k['status'] == 'recalled'
                            ? 'Samaj ne wapas le li'
                            : ((k['skill'] as Map?)?['when'] as String? ?? '')),
                        value: k['status'] == 'active',
                        onChanged: k['status'] == 'recalled'
                            ? null
                            : (v) => _do(() => app.api!.netSkillAct(k['id'] as String, v ? 'active' : 'off')),
                      ),
                    if (_skills.isEmpty)
                      const Padding(padding: EdgeInsets.all(12), child: Text('Koi skill nahi lagi. Samaj se laga sakte hain.', style: TextStyle(color: C.faint))),
                  ]),
                ),
        ),
      );
}


/// Samaj list + directory (used inside the Hoola Network screen).
class SamajListView extends StatefulWidget {
  const SamajListView({super.key, required this.app});
  final Santosh app;
  @override
  State<SamajListView> createState() => _SamajListViewState();
}

class _SamajListViewState extends State<SamajListView> {
  List<Map<String, dynamic>> _mine = [];
  List<Map<String, dynamic>> _dir = [];
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

  List<Map<String, dynamic>> _list(dynamic x) =>
      List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  Future<void> _load() async {
    try {
      final r = await app.api!.netSamaj(q: _q.text.trim());
      if (mounted) setState(() { _mine = _list(r['mine']); _dir = _list(r['directory']); });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _create() async {
    final name = TextEditingController();
    final topic = TextEditingController();
    var approval = false;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Naya Samaj'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (jaise Maharashtra ISPs)')),
            TextField(controller: topic, decoration: const InputDecoration(labelText: 'Vishay / area')),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Judne ke liye manzoori chahiye'),
              value: approval,
              onChanged: (v) => set(() => approval = v),
            ),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Banaiye')),
          ],
        ),
      ),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    try {
      await app.api!.netSamajCreate({'name': name.text.trim(), 'topic': topic.text.trim(), 'visibility': approval ? 'approval' : 'open'});
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Row(children: [
            Expanded(child: GradientButton(label: 'Naya Samaj', icon: Icons.add_rounded, height: 44, onTap: _create)),
            const SizedBox(width: 8),
            Expanded(
              child: TextButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaLearnedScreen(app: app))),
                icon: const Icon(Icons.lightbulb_rounded, color: C.accent),
                label: const Text('Seekha'),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          if (_mine.isNotEmpty) const Text('Mere Samaj', style: TextStyle(fontWeight: FontWeight.w700)),
          for (final c in _mine)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Text(c['emoji'] as String? ?? '🌐', style: const TextStyle(fontSize: 24)),
              title: Text(c['name'] as String? ?? ''),
              subtitle: Text(c['status'] == 'pending' ? 'Manzoori ka intezaar' : '${c['topic'] ?? ''} · ${c['role']}'),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => HoolaSamajScreen(app: app, cid: c['cid'] as String))),
            ),
          const SizedBox(height: 12),
          TextField(
            controller: _q,
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), hintText: 'Samaj dhoondhiye (ISP, kirana, Akola…)'),
            onSubmitted: (_) => _load(),
          ),
          for (final c in _dir.where((d) => d['joined'] != true))
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Text(c['emoji'] as String? ?? '🌐', style: const TextStyle(fontSize: 24)),
              title: Text(c['name'] as String? ?? ''),
              subtitle: Text('${c['members']} avatars · ${c['topic'] ?? ''}${c['visibility'] == 'approval' ? ' · manzoori se' : ''}'),
              trailing: TextButton(
                onPressed: () async {
                  try {
                    await app.api!.netSamajJoin(c['cid'] as String);
                    await _load();
                  } catch (e) {
                    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                },
                child: const Text('Judiye'),
              ),
            ),
        ]),
      );
}

/// One Samaj: questions, cards, skills and alerts, with a box to ask / share / warn.
class HoolaSamajScreen extends StatefulWidget {
  const HoolaSamajScreen({super.key, required this.app, required this.cid});
  final Santosh app;
  final String cid;
  @override
  State<HoolaSamajScreen> createState() => _HoolaSamajScreenState();
}

class _HoolaSamajScreenState extends State<HoolaSamajScreen> {
  Map<String, dynamic> _c = {};
  String _filter = '';
  String _kind = 'question';
  final _text = TextEditingController();
  final _value = TextEditingController();
  String _alertType = 'scam_number';

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _text.dispose();
    _value.dispose();
    super.dispose();
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<void> _load() async {
    try {
      final r = await app.api!.netSamajDetail(widget.cid, kind: _filter);
      if (mounted) setState(() => _c = r);
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _post() async {
    final t = _text.text.trim();
    final data = <String, dynamic>{'text': t};
    if (_kind == 'alert') {
      data['type'] = _alertType;
      data['value'] = _value.text.trim();
    }
    if (t.isEmpty && _kind != 'alert') return;
    try {
      final r = await app.api!.netSamajPost(widget.cid, _kind, data);
      _text.clear();
      _value.clear();
      _snack(r['status'] == 'waiting' ? 'Moderator ki manzoori ke baad sab dekhenge' : 'Bhej diya ✓');
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _item(Map<String, dynamic> i, Map<String, dynamic> body, String ok) async {
    try {
      await app.api!.netSamajItem(i['id'] as String, body);
      _snack(ok);
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _answer(Map<String, dynamic> q) async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Jawab'),
        content: TextField(controller: c, minLines: 2, maxLines: 6),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    try {
      await app.api!.netSamajPost(widget.cid, 'answer', {'parent': q['item_id'], 'text': c.text.trim()});
      await _load();
    } catch (e) {
      _snack(e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = List<Map<String, dynamic>>.from((_c['items'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final pending = List<Map<String, dynamic>>.from((_c['pending_members'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final mod = _c['role'] == 'owner' || _c['role'] == 'mod';
    return Scaffold(
      appBar: AppBar(
        title: Text('${_c['emoji'] ?? '🌐'} ${_c['name'] ?? 'Samaj'}'),
        backgroundColor: Colors.transparent,
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) async {
              try {
                await app.api!.netSamajAct(widget.cid, v == 'leave' ? {'action': 'leave'} : {'action': 'mute', 'mute': v});
                if (v == 'leave' && context.mounted) {
                  Navigator.of(context).pop();
                } else {
                  await _load();
                }
              } catch (e) {
                _snack(e.toString());
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(value: 'all', child: Text('Sab dikhao${_c['mute'] == 'all' ? ' ✓' : ''}')),
              PopupMenuItem(value: 'alerts', child: Text('Sirf chetavni + mere sawaal${_c['mute'] == 'alerts' ? ' ✓' : ''}')),
              PopupMenuItem(value: 'digest', child: Text('Kuch mat dikhao${_c['mute'] == 'digest' ? ' ✓' : ''}')),
              if (_c['role'] != 'owner') const PopupMenuItem(value: 'leave', child: Text('Samaj chhodiye')),
            ],
          ),
        ],
      ),
      body: Aurora(
        child: Column(children: [
          SizedBox(
            height: 44,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              for (final f in const {'': 'Sab', 'question': 'Sawaal', 'answer': 'Jawab', 'card': 'Jaankari', 'skill': 'Skills', 'alert': 'Chetavni'}.entries)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: ChoiceChip(
                    label: Text(f.value),
                    selected: _filter == f.key,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: _filter == f.key ? C.onAccent : C.chip, fontSize: 12.5),
                    onSelected: (_) {
                      setState(() => _filter = f.key);
                      _load();
                    },
                  ),
                ),
            ]),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(12), children: [
                if (mod)
                  for (final p in pending)
                    Glass(
                      child: Row(children: [
                        Expanded(child: Text('${p['label']} judna chahte hain')),
                        TextButton(
                          onPressed: () async {
                            try {
                              await app.api!.netSamajAct(widget.cid, {'action': 'moderate_member', 'mod_action': 'approve_member', 'who': p['address']});
                              await _load();
                            } catch (e) {
                              _snack(e.toString());
                            }
                          },
                          child: const Text('Aane do'),
                        ),
                      ]),
                    ),
                for (final i in items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Glass(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        Text('${_kindLabel(i['kind'] as String? ?? '')} · ${i['author'] ?? ''}${i['status'] != 'available' ? ' · ${i['status']}' : ''}',
                            style: const TextStyle(color: C.muted, fontSize: 12)),
                        if ((i['title'] ?? '') != '') Text(i['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                        Text(i['text'] as String? ?? '', style: const TextStyle(fontSize: 13.5)),
                        if (i['kind'] == 'alert')
                          SelectableText('${(i['data'] as Map?)?['type'] ?? ''}: ${(i['data'] as Map?)?['value'] ?? ''}',
                              style: const TextStyle(color: C.bad, fontSize: 12)),
                        if (i['kind'] == 'skill')
                          for (final st in ((i['data'] as Map?)?['skill'] as Map?)?['steps'] as List? ?? const [])
                            Text('• ${(st as Map)['tool']}: ${st['do']}', style: const TextStyle(fontSize: 12, color: C.chip)),
                        Wrap(spacing: 2, children: [
                          if (i['kind'] == 'question') TextButton(onPressed: () => _answer(i), child: const Text('Jawab do')),
                          if (i['kind'] == 'skill' && i['status'] == 'available')
                            TextButton(onPressed: () => _item(i, {'action': 'install'}, 'Skill lag gayi ✓'), child: const Text('Install')),
                          if (i['mine'] != true)
                            TextButton(onPressed: () => _item(i, {'action': 'rate', 'helpful': true}, 'Dhanyavaad'), child: Text('👍 ${i['helpful'] ?? 0}')),
                          if (i['mine'] != true)
                            TextButton(onPressed: () => _item(i, {'action': 'report'}, 'Report kiya'), child: const Text('Report', style: TextStyle(color: C.bad))),
                          if (mod && i['status'] == 'waiting')
                            TextButton(onPressed: () => _item(i, {'action': 'moderate', 'mod_action': 'approve'}, 'Manzoor'), child: const Text('Manzoor')),
                          if (mod && i['status'] == 'available' && i['kind'] == 'skill')
                            TextButton(onPressed: () => _item(i, {'action': 'moderate', 'mod_action': 'recall'}, 'Wapas li'), child: const Text('Recall')),
                          if (mod && i['status'] != 'removed')
                            TextButton(onPressed: () => _item(i, {'action': 'moderate', 'mod_action': 'remove'}, 'Hata diya'), child: const Text('Hataiye')),
                          if (mod && i['status'] == 'hidden')
                            TextButton(onPressed: () => _item(i, {'action': 'moderate', 'mod_action': 'restore'}, 'Wapas dikhaya'), child: const Text('Restore')),
                        ]),
                      ]),
                    ),
                  ),
                if (items.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('Abhi kuch nahi.', style: TextStyle(color: C.muted))),
              ]),
            ),
          ),
          if (_c['status'] == 'active')
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                child: Column(children: [
                  Row(children: [
                    for (final k in const {'question': 'Sawaal', 'card': 'Jaankari', 'alert': 'Chetavni'}.entries)
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
                    if (_kind == 'alert')
                      Expanded(
                        child: DropdownButton<String>(
                          isExpanded: true,
                          value: _alertType,
                          items: const [
                            DropdownMenuItem(value: 'scam_number', child: Text('Fraud number')),
                            DropdownMenuItem(value: 'fraud_link', child: Text('Fraud website')),
                            DropdownMenuItem(value: 'fraud_apk', child: Text('Fraud app (SHA-256)')),
                            DropdownMenuItem(value: 'outage', child: Text('Outage')),
                            DropdownMenuItem(value: 'other', child: Text('Aur kuch')),
                          ],
                          onChanged: (v) => setState(() => _alertType = v ?? 'other'),
                        ),
                      ),
                  ]),
                  if (_kind == 'alert' && _alertType != 'outage' && _alertType != 'other')
                    TextField(controller: _value, decoration: const InputDecoration(isDense: true, hintText: 'Number / website / SHA-256')),
                  Row(children: [
                    Expanded(
                      child: TextField(controller: _text, minLines: 1, maxLines: 4,
                          decoration: const InputDecoration(hintText: 'Personal jaankari apne aap hat jaati hai…')),
                    ),
                    IconButton(onPressed: _post, icon: const Icon(Icons.send_rounded, color: C.accent)),
                  ]),
                ]),
              ),
            ),
        ]),
      ),
    );
  }

  String _kindLabel(String k) => switch (k) {
        'question' => '❓ Sawaal',
        'answer' => '💬 Jawab',
        'card' => '📘 Jaankari',
        'skill' => '🧩 Skill',
        'alert' => '⚠️ Chetavni',
        _ => k,
      };
}
