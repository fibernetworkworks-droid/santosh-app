import 'package:flutter/material.dart';

import '../state.dart';
import 'attach.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';
import 'hoola_cards.dart' show openHoolaThread;

/// v0.160 Hoola Dosti: once she switches it on, her avatar chats with friends' avatars by itself about WORK (its work
/// diary, what it learned, skills). A document a friend asks for goes only on her tap; a friend's skill is learned only on
/// her yes; personal things are never talked about.

String _s(dynamic v) => v == null ? '' : '$v';
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
Map<String, dynamic> _m(dynamic x) => x is Map ? Map<String, dynamic>.from(x) : <String, dynamic>{};
List<Map<String, dynamic>> _l(dynamic x) =>
    List<Map<String, dynamic>>.from((x as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

Future<T?> _guard<T>(BuildContext context, Future<T> Function() fn) async {
  try {
    return await fn();
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

const _catWord = {'web': 'Web', 'technical': 'Technical', 'business': 'Business', 'creative': 'Creative', 'other': 'More tasks'};
const _catColor = {'web': C.teal, 'technical': C.violet, 'business': C.accent, 'creative': C.accent2, 'other': C.chip};
const _catIcon = {
  'web': Icons.public_rounded,
  'technical': Icons.code_rounded,
  'business': Icons.storefront_rounded,
  'creative': Icons.movie_creation_rounded,
  'other': Icons.work_outline_rounded,
};

/// Uploads one file she picks (as her own chat file) and returns its file_id.
Future<String?> _pickFile(BuildContext context, Santosh app) async {
  final files = await pickAttachments(context, max: 1);
  if (files.isEmpty || app.conversationId == null) return null;
  final r = await _guard(context, () => app.api!.chatFile(app.conversationId!, files.first.name, files.first.bytes));
  return r == null ? null : _s(r['file_id']);
}

// ------------------------------------------------------------------------------------------------ chat card
class DostiCard extends StatefulWidget {
  const DostiCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<DostiCard> createState() => _DostiCardState();
}

class _DostiCardState extends State<DostiCard> {
  bool _busy = false;
  String _done = '';
  Map<String, dynamic> get v => widget.v;
  Santosh get app => widget.app;

  Future<void> _run(Future<Map<String, dynamic>> Function() fn, String ok) async {
    setState(() => _busy = true);
    final r = await _guard(context, fn);
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r != null) _done = _s(r['say']).isNotEmpty ? _s(r['say']) : ok;
    });
    app.hoolaTick++;
  }

  @override
  Widget build(BuildContext context) {
    final card = _s(v['card']);
    final who = _s(v['with']);
    final tid = _s(v['thread_id']);
    final head = {
          'doc_ask': 'Document requested',
          'skill': 'Friend\'s skill',
          'paused': 'Friend conversation paused',
          'msg': 'Message from a friend\'s avatar',
          'info': 'Friends',
          'live': 'Friends',
        }[card] ??
        'Friends';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(card == 'doc_ask' ? Icons.description_rounded : card == 'skill' ? Icons.school_rounded : Icons.forum_rounded,
              color: C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text('$head · $who', style: const TextStyle(fontWeight: FontWeight.w800), maxLines: 2)),
        ]),
        const SizedBox(height: 6),
        if (_s(v['say']).isNotEmpty) Text(_s(v['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
        if (card == 'doc_ask') ..._doc(context),
        if (card == 'skill') ..._skill(context),
        if (card == 'paused')
          Align(
            alignment: Alignment.centerRight,
            child: Wrap(spacing: 8, children: [
              TextButton(onPressed: () => openHoolaThread(context, app, tid), child: const Text('View conversation')),
              GlassButton(
                  label: 'Turn on',
                  icon: Icons.play_arrow_rounded,
                  onTap: _busy || _done.isNotEmpty ? null : () => _run(() => app.api!.dostiThread(tid, 'resume'), 'Turned on')),
            ]),
          ),
        if (card == 'msg')
          Align(
            alignment: Alignment.centerRight,
            child: Wrap(spacing: 8, children: [
              TextButton(onPressed: () => openHoolaThread(context, app, tid), child: const Text('Reply')),
              if (v['dosti_on'] != true)
                TextButton(
                    onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DostiScreen(app: app))),
                    child: const Text('Open Friends')),
            ]),
          ),
        if (_done.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 6), child: Text('✓ $_done', style: const TextStyle(color: C.ok, fontSize: 12.5))),
      ]),
    );
  }

  List<Widget> _doc(BuildContext context) {
    final ask = _m(v['ask']);
    final sug = _l(ask['suggestions']);
    final id = _s(ask['id']);
    final closed = _done.isNotEmpty || _s(ask['status']) != 'waiting';
    return [
      if (_s(ask['why']).isNotEmpty)
        Text('Why: ${_s(ask['why'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 6),
      const Text('Nothing goes without your approval. Never documents like Aadhaar / PAN / passport.',
          style: TextStyle(color: C.faint, fontSize: 11.5)),
      const SizedBox(height: 6),
      for (final f in sug)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(children: [
            const Icon(Icons.insert_drive_file_rounded, size: 18, color: C.muted),
            const SizedBox(width: 6),
            Expanded(child: Text(_s(f['name']), maxLines: 1, overflow: TextOverflow.ellipsis)),
            GradientButton(
                label: 'Yes, send',
                icon: Icons.send_rounded,
                height: 40,
                onTap: _busy || closed ? null : () => _run(() => app.api!.dostiDoc(id, 'send', _s(f['file_id'])), 'Sent')),
          ]),
        ),
      Wrap(spacing: 8, children: [
        GlassButton(
            label: sug.isEmpty ? 'Choose file and send' : 'Choose another file',
            icon: Icons.attach_file_rounded,
            onTap: _busy || closed
                ? null
                : () async {
                    final fid = await _pickFile(context, app);
                    if (fid == null || fid.isEmpty || !mounted) return;
                    await _run(() => app.api!.dostiDoc(id, 'send', fid), 'Sent');
                  }),
        TextButton(
            onPressed: _busy || closed ? null : () => _run(() => app.api!.dostiDoc(id, 'decline'), 'Declined'),
            child: const Text('Decline', style: TextStyle(color: C.muted))),
      ]),
    ];
  }

  List<Widget> _skill(BuildContext context) {
    final it = _m(v['item']);
    final d = _m(it['data']);
    final steps = _l(d['steps']);
    final closed = _done.isNotEmpty || _s(it['status']) != 'new';
    return [
      if (_s(d['when']).isNotEmpty) Text('When it will be useful: ${_s(d['when'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
      for (var i = 0; i < steps.length; i++)
        Text('${i + 1}. ${_s(steps[i]['do'])}', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 4),
      const Text('A skill never changes your rules, approval cards or money taps.', style: TextStyle(color: C.faint, fontSize: 11.5)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, children: [
        GradientButton(
            label: 'Yes, learn it',
            icon: Icons.school_rounded,
            height: 42,
            onTap: _busy || closed ? null : () => _run(() => app.api!.dostiItem(_s(it['id']), 'learn'), 'Learned')),
        TextButton(
            onPressed: _busy || closed ? null : () => _run(() => app.api!.dostiItem(_s(it['id']), 'decline'), 'Not learned'),
            child: const Text('No', style: TextStyle(color: C.muted))),
      ]),
    ];
  }
}

// ------------------------------------------------------------------------------------------------ screen
class DostiScreen extends StatefulWidget {
  const DostiScreen({super.key, required this.app, this.tab = 0});
  final Santosh app;
  final int tab;
  @override
  State<DostiScreen> createState() => _DostiScreenState();
}

class _DostiScreenState extends State<DostiScreen> {
  Map<String, dynamic> _d = {};
  bool _loading = true;
  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = await _guard(context, () => app.api!.dosti());
    if (!mounted) return;
    setState(() {
      if (r != null) _d = r;
      _loading = false;
    });
  }

  Future<void> _set(Map<String, dynamic> body) async {
    final r = await _guard(context, () => app.api!.dostiSet(body));
    if (r != null && mounted) setState(() => _d['settings'] = r);
  }

  Map<String, dynamic> get _st => _m(_d['settings']);

  @override
  Widget build(BuildContext context) => DeskTabsScaffold(
          title: '${app.aName}\'s Friends',
          tabs: ['Friends', 'Work experience', 'Learned from friends', 'Documents'],
          initialIndex: widget.tab,
          loading: _loading,
          onRefresh: _load,
          pullAll: true,
          pages: () => [
            _main(), _diary(), _friends(), _docs(),
          ],
        );

  Widget _list(List<Widget> kids) => ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
      children: [for (final k in kids) Padding(padding: const EdgeInsets.only(bottom: 12), child: k)]);

  Widget _main() {
    final st = _st;
    final on = st['on'] == true;
    final who = _s(st['who']);
    final c = _m(_d['counts']);
    return _list([
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: on,
            onChanged: (x) => _set({'on': x}),
            title: const Text('Talk to friends\' avatars by itself', style: TextStyle(fontWeight: FontWeight.w800)),
            subtitle: Text(
                on
                    ? '${app.aName} will not ask you for every message; it will only talk about work.'
                    : 'Off: asks you before every message.',
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ),
          const Text('Which ones?', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, children: [
            for (final o in const [['trusted', 'Trusted'], ['connected', 'All linked people'], ['chosen', 'Selected']])
              ChoiceChip(label: Text(o[1]), selected: who == o[0], onSelected: (_) => _set({'who': o[0]})),
          ]),
          if (who == 'chosen') ...[
            const SizedBox(height: 8),
            TextFormField(
              initialValue: (st['chosen'] as List? ?? const []).join(', '),
              decoration: const InputDecoration(labelText: 'Name or @Hoola ID (comma separated)'),
              onFieldSubmitted: (x) => _set({'chosen': x.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList()}),
            ),
          ],
          const SizedBox(height: 6),
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: st['share_work'] != false,
              onChanged: (x) => _set({'share_work': x}),
              title: const Text('Share its work experience'),
              subtitle: const Text('Web / technical / big tasks, without personal information', style: TextStyle(color: C.faint, fontSize: 12))),
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: st['share_skills'] != false,
              onChanged: (x) => _set({'share_skills': x}),
              title: const Text('Share learned skills')),
          SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: st['share_videos'] == 'auto',
              onChanged: (x) => _set({'share_videos': x ? 'auto' : 'ask'}),
              title: const Text('Send skill videos without asking'),
              subtitle: const Text('Off = every video needs your tap', style: TextStyle(color: C.faint, fontSize: 12))),
          Row(children: [
            const Expanded(child: Text('Reply to one friend per day')),
            DropdownButton<int>(
              value: ((st['daily_max'] as num?) ?? 30).toInt().clamp(5, 100).toInt(),
              items: [for (final n in {5, 10, 20, 30, 50, 100, ((st['daily_max'] as num?) ?? 30).toInt().clamp(5, 100).toInt()})
                DropdownMenuItem(value: n, child: Text('$n'))],
              onChanged: (n) => n == null ? null : _set({'daily_max': n}),
            ),
          ]),
          const SizedBox(height: 4),
          const Text('Always: documents / files need your approval; a friend\'s skill needs your approval; never money, OTP, PIN, Aadhaar;'
              'never personal matters.', style: TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
      ),
      Glass(
        child: Wrap(spacing: 8, runSpacing: 6, children: [
          Pill('${c['experiences'] ?? 0} experiences', fg: C.accent),
          Pill('${c['web'] ?? 0} web', fg: C.teal),
          Pill('${c['technical'] ?? 0} technical', fg: C.violet),
          Pill('${c['complex'] ?? 0} big tasks', fg: C.accent2),
          if ((c['skills_waiting'] ?? 0) != 0) Pill('${c['skills_waiting']} skill waiting for your approval', fg: C.warn),
          if ((c['docs_waiting'] ?? 0) != 0) Pill('${c['docs_waiting']} document request', fg: C.warn),
        ]),
      ),
      Row(children: [
        Expanded(
            child: GradientButton(
                label: 'Talk to a friend',
                icon: Icons.forum_rounded,
                height: 46,
                onTap: () => _talkDialog())),
        const SizedBox(width: 8),
        GlassButton(
            label: 'Tell what was learned',
            icon: Icons.campaign_rounded,
            onTap: on
                ? () async {
                    final r = await _guard(context, () => app.api!.dostiAct('share_now', {}));
                    if (r != null && mounted) _snack(context, 'Told ${r['friends_told'] ?? 0} friends');
                  }
                : null),
      ]),
      const Text('Conversation', style: TextStyle(fontWeight: FontWeight.w800)),
      if (_l(_d['threads']).isEmpty) const Text('No conversations yet.', style: TextStyle(color: C.muted)),
      for (final t in _l(_d['threads']))
        Glass(
          padding: const EdgeInsets.all(12),
          child: InkWell(
            onTap: () => openHoolaThread(context, app, _s(t['thread_id'])),
            child: Row(children: [
              Icon(t['paused'] == true ? Icons.pause_circle_rounded : Icons.forum_rounded,
                  color: t['paused'] == true ? C.warn : (t['free'] == true ? C.ok : C.muted)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(t['with']), style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text(_s(t['last']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  if (t['paused'] == true && _s(t['pause_why']).isNotEmpty)
                    Text('Paused: ${_s(t['pause_why'])}', style: const TextStyle(color: C.warn, fontSize: 11.5)),
                ]),
              ),
              IconButton(
                  tooltip: t['paused'] == true ? 'Turn on' : 'Stop',
                  icon: Icon(t['paused'] == true ? Icons.play_arrow_rounded : Icons.pause_rounded),
                  onPressed: () async {
                    await _guard(context, () => app.api!.dostiThread(_s(t['thread_id']), t['paused'] == true ? 'resume' : 'pause'));
                    _load();
                  }),
            ]),
          ),
        ),
    ]);
  }

  Future<void> _talkDialog() async {
    final to = TextEditingController();
    final text = TextEditingController();
    var share = true;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Talk to a friend\'s avatar'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: to, decoration: const InputDecoration(labelText: 'Name or @Hoola ID')),
            TextField(controller: text, maxLines: 3, decoration: const InputDecoration(labelText: 'What to ask / tell')),
            CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: share,
                onChanged: (x) => set(() => share = x ?? false),
                title: const Text('Also send my new experience and skill')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Send')),
          ],
        ),
      ),
    );
    if (ok != true || to.text.trim().isEmpty) return;
    final r = await _guard(context, () => app.api!.dostiAct('talk', {'to': to.text.trim(), 'text': text.text.trim(), 'share': share}));
    if (r != null && mounted) {
      _snack(context, r['free_talk'] == true ? 'Sent; ${app.aName} will continue the conversation.' : 'Sent.');
      _load();
    }
  }

  Widget _diary() {
    final exps = _l(_d['experiences']);
    final skills = _l(_d['skills']);
    return _list([
      const Text('The work I did for you (personal work does not show here). I tell friends only the general form.',
          style: TextStyle(color: C.muted, fontSize: 12.5)),
      GlassButton(label: 'Add an experience yourself', icon: Icons.add_rounded, onTap: _addDialog),
      if (exps.isEmpty) const Text('The diary is empty: get some work done and it will appear here by itself.', style: TextStyle(color: C.muted)),
      for (final e in exps) _expTile(e),
      if (skills.isNotEmpty) const Text('My skills (I can give them to friends)', style: TextStyle(fontWeight: FontWeight.w800)),
      for (final k in skills)
        Glass(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(k['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
            for (var i = 0; i < _l(k['steps']).length; i++)
              Text('${i + 1}. ${_s(_l(k['steps'])[i]['do'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ]),
        ),
    ]);
  }

  Widget _expTile(Map<String, dynamic> e) {
    final cat = _s(e['category']);
    return Glass(
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_catIcon[cat] ?? Icons.work_outline_rounded, color: _catColor[cat] ?? C.chip, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(e['title']), style: const TextStyle(fontWeight: FontWeight.w700))),
        ]),
        const SizedBox(height: 4),
        Wrap(spacing: 6, runSpacing: 4, children: [
          Pill(_catWord[cat] ?? cat, fg: _catColor[cat] ?? C.chip),
          if (e['complex'] == true) const Pill('big task', fg: C.accent2),
          if (e['shared'] != true) const Pill('only for me', fg: C.muted),
          if ((e['told'] ?? 0) != 0) Pill('Told ${e['told']} friends', fg: C.teal),
        ]),
        if (_s(e['summary']).isNotEmpty) Text(_s(e['summary']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
        if (_s(e['learned']).isNotEmpty) Text('Learned: ${_s(e['learned'])}', style: const TextStyle(fontSize: 12.5)),
        Wrap(spacing: 4, children: [
          TextButton.icon(
              icon: const Icon(Icons.movie_creation_rounded, size: 18),
              label: Text(_s(e['video_id']).isEmpty ? 'Make skill video' : 'Send video to friends'),
              onPressed: () async {
                if (_s(e['video_id']).isEmpty) {
                  final r = await _guard(context, () => app.api!.dostiVideo(_s(e['id']), 'video'));
                  if (r != null && mounted) _snack(context, _s(r['say']));
                  _load();
                } else {
                  final to = await _askTo();
                  if (to == null) return;
                  final r = await _guard(context, () => app.api!.dostiVideo(_s(e['id']), 'send_video', to));
                  if (r != null && mounted) _snack(context, _s(r['say']).isEmpty ? 'Sent' : _s(r['say']));
                }
              }),
          TextButton(
              onPressed: () async {
                await _guard(context, () => app.api!.dostiDiary(_s(e['id']), {'shared': e['shared'] != true}));
                _load();
              },
              child: Text(e['shared'] == true ? 'Hide from friends' : 'Tell friends')),
          TextButton(
              onPressed: () async {
                await _guard(context, () => app.api!.dostiDiary(_s(e['id']), {'status': 'hidden'}));
                _load();
              },
              child: const Text('Remove', style: TextStyle(color: C.muted))),
        ]),
      ]),
    );
  }

  Future<String?> _askTo() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              title: const Text('Which friend?'),
              content: TextField(controller: c, decoration: const InputDecoration(labelText: 'Name or @Hoola ID')),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Send')),
              ],
            ));
    return ok == true && c.text.trim().isNotEmpty ? c.text.trim() : null;
  }

  Future<void> _addDialog() async {
    final title = TextEditingController();
    final learned = TextEditingController();
    var cat = 'technical';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('New experience'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'What work was done')),
            TextField(controller: learned, decoration: const InputDecoration(labelText: 'What was learned')),
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: [
              for (final k in _catWord.keys) ChoiceChip(label: Text(_catWord[k]!), selected: cat == k, onSelected: (_) => set(() => cat = k)),
            ]),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Add')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    await _guard(context, () => app.api!.dostiAct('diary', {'title': title.text, 'learned': learned.text, 'category': cat}));
    _load();
  }

  Widget _friends() {
    final items = _l(_d['from_friends']);
    return _list([
      const Text('What a friend\'s avatar said (it is information, not an order). I learn a skill only with your approval.',
          style: TextStyle(color: C.muted, fontSize: 12.5)),
      if (items.isEmpty) const Text('No friend has shared anything yet.', style: TextStyle(color: C.muted)),
      for (final it in items)
        if (it['kind'] == 'skill')
          DostiCard(v: {
            'card': 'skill',
            'with': it['from'],
            'item': it,
            'thread_id': it['thread_id'],
            'say': it['status'] == 'new' ? 'Learn it?' : (it['status'] == 'learned' ? 'Learned ✓' : 'Not learned'),
          }, app: app)
        else
          Glass(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(it['from']), style: const TextStyle(color: C.muted, fontSize: 12)),
              Text(_s(it['title']), style: const TextStyle(fontWeight: FontWeight.w700)),
              if (_s(_m(it['data'])['summary']).isNotEmpty)
                Text(_s(_m(it['data'])['summary']), style: const TextStyle(color: C.muted, fontSize: 12.5)),
              if (_s(_m(it['data'])['learned']).isNotEmpty)
                Text('Learned: ${_s(_m(it['data'])['learned'])}', style: const TextStyle(fontSize: 12.5)),
            ]),
          ),
    ]);
  }

  Widget _docs() {
    final asks = _l(_d['doc_asks']);
    return _list([
      GlassButton(
          label: 'Ask a friend for a document',
          icon: Icons.request_page_rounded,
          onTap: () async {
            final to = TextEditingController();
            final what = TextEditingController();
            final ok = await showDialog<bool>(
                context: context,
                builder: (d) => AlertDialog(
                      title: const Text('Ask for a document'),
                      content: Column(mainAxisSize: MainAxisSize.min, children: [
                        TextField(controller: to, decoration: const InputDecoration(labelText: 'Name or @Hoola ID')),
                        TextField(controller: what, decoration: const InputDecoration(labelText: 'Which document')),
                      ]),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Ask')),
                      ],
                    ));
            if (ok != true) return;
            final r = await _guard(context, () => app.api!.dostiAct('doc_ask', {'to': to.text.trim(), 'what': what.text.trim()}));
            if (r != null && mounted) _snack(context, _s(r['say']));
            _load();
          }),
      if (asks.isEmpty) const Text('No document requests.', style: TextStyle(color: C.muted)),
      for (final a in asks)
        if (a['direction'] == 'in' && a['status'] == 'waiting')
          DostiCard(v: {'card': 'doc_ask', 'with': a['with'], 'ask': a, 'thread_id': a['thread_id'], 'say': 'Asked for "${_s(a['what'])}"'}, app: app)
        else
          Glass(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Icon(a['direction'] == 'in' ? Icons.call_received_rounded : Icons.call_made_rounded, color: C.muted),
              const SizedBox(width: 8),
              Expanded(
                  child: Text('${a['direction'] == 'in' ? '${_s(a['with'])} asked' : 'asked ${_s(a['with'])}'}: ${_s(a['what'])}',
                      style: const TextStyle(fontSize: 13))),
              Pill({'waiting': 'waiting', 'sent': 'sent', 'declined': 'declined'}[_s(a['status'])] ?? _s(a['status']),
                  fg: a['status'] == 'sent' ? C.ok : C.muted),
            ]),
          ),
    ]);
  }
}
