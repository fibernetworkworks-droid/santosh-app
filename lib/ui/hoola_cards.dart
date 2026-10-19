import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

Widget _avatarDot(String label, {Color color = C.violet}) => CircleAvatar(
      radius: 18,
      backgroundColor: color.withOpacity(.35),
      child: Text(label.isEmpty ? 'H' : label.substring(0, 1).toUpperCase(),
          style: const TextStyle(fontWeight: FontWeight.w800, color: C.ink)),
    );

Widget _badges(Map<String, dynamic> v) => Wrap(spacing: 6, children: [
      if (v['verified'] == true || v['person_verified'] == true)
        const Text('✅ verified', style: TextStyle(color: C.ok, fontSize: 11.5, fontWeight: FontWeight.w700)),
      if (v['business'] == true) const Text('🏢 business', style: TextStyle(color: C.teal, fontSize: 11.5, fontWeight: FontWeight.w700)),
      if (v['vip'] == true) const Text('⭐ VIP', style: TextStyle(color: C.accent, fontSize: 11.5, fontWeight: FontWeight.w700)),
      if (v['key_warning'] == true)
        const Text('⚠️ pehchaan badli', style: TextStyle(color: C.bad, fontSize: 11.5, fontWeight: FontWeight.w700)),
    ]);

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

String _size(dynamic n) {
  final b = (n is num) ? n.toDouble() : 0.0;
  if (b <= 0) return '';
  if (b < 1024 * 1024) return '${(b / 1024).toStringAsFixed(0)} KB';
  return '${(b / 1024 / 1024).toStringAsFixed(1)} MB';
}

/// What the receiving avatar found out before handing anything over: summary and the safety check.
Widget _checked(Map<String, dynamic> v) {
  final scan = v['scan'] is Map ? Map<String, dynamic>.from(v['scan'] as Map) : const <String, dynamic>{};
  final verdict = scan['verdict'] as String? ?? '';
  final notes = List<String>.from((scan['notes'] as List? ?? const []).map((e) => '$e'));
  final col = switch (verdict) { 'danger' => C.bad, 'caution' => C.warn, 'clear' => C.ok, _ => C.faint };
  final lines = <Widget>[
    if ((v['name'] ?? '') != '')
      Text('📎 ${v['name']}  ${_size(v['size'])}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
    if ((v['subject'] ?? '') != '')
      Text('✉️ ${v['subject']}${(v['from_name'] ?? '') != '' ? ' · ${v['from_name']}' : ''}',
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
    if ((v['url'] ?? '') != '') Text('🔗 ${v['url']}', style: const TextStyle(fontSize: 12.5, color: C.chip)),
    if ((v['place'] ?? '') != '') Text('📍 ${v['place']}', style: const TextStyle(fontSize: 13)),
    if ((v['summary'] ?? '') != '') Text(v['summary'] as String, style: const TextStyle(fontSize: 13, color: C.ink)),
    if (verdict.isNotEmpty)
      Text(
          '${verdict == 'clear' ? '✅ Jaanch saaf' : verdict == 'caution' ? '⚠️ Dhyaan se' : verdict == 'danger' ? '⛔ Khatarnak' : 'Jaanch poori nahi hui'}'
          '${notes.isNotEmpty ? ': ${notes.join('; ')}' : ''}',
          style: TextStyle(color: col, fontSize: 12.5, fontWeight: FontWeight.w600)),
  ];
  if (lines.isEmpty) return const SizedBox.shrink();
  return Padding(padding: const EdgeInsets.only(top: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: lines));
}

/// Buttons for what was handed over (pay in the UPI app, open the link / map, call the contact).
Widget _effectButtons(Map<String, dynamic>? e) {
  if (e == null) return const SizedBox.shrink();
  final where = e['where'] as String? ?? '';
  final (String label, IconData icon, String url) = switch (where) {
    'pay' => ('UPI app mein pay kijiye', Icons.currency_rupee_rounded, e['pay_link'] as String? ?? ''),
    'link' => ('Link kholiye', Icons.open_in_new_rounded, e['url'] as String? ?? ''),
    'map' => ('Map mein dekhiye', Icons.map_rounded, e['url'] as String? ?? ''),
    'contact' => ('Call kijiye', Icons.call_rounded, 'tel:${e['phone'] ?? ''}'),
    _ => ('', Icons.circle, ''),
  };
  if (label.isEmpty || url.isEmpty) return const SizedBox.shrink();
  return Padding(
    padding: const EdgeInsets.only(top: 6),
    child: Align(
      alignment: Alignment.centerLeft,
      child: TextButton.icon(onPressed: () => _open(url), icon: Icon(icon, size: 18), label: Text(label)),
    ),
  );
}

String _statusText(String s) => switch (s) {
      'accepted' => 'Haan kaha ✓',
      'declined' => 'Mana kiya',
      'snoozed' => 'Baad mein yaad dilayenge',
      'handled' => 'Hoola ne sambhal liya',
      'auto' => 'Niyam se seedha liya',
      'blocked' => 'Roka gaya',
      _ => s,
    };

/// Another avatar knocks: who, what they want, and the owner's choice (Haan / Mana / Baad mein).
class HoolaKnockCard extends StatefulWidget {
  const HoolaKnockCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaKnockCard> createState() => _HoolaKnockCardState();
}

class _HoolaKnockCardState extends State<HoolaKnockCard> {
  int? _slot;
  bool _busy = false;
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _do(String action, {int? minutes}) async {
    setState(() => _busy = true);
    final err = await widget.app.hoolaDecide(widget.v['id'] as String, action,
        slot: _slot ?? (widget.v['kind'] == 'meeting' ? 0 : null), minutes: minutes, note: _note.text.trim());
    if (!mounted) return;
    setState(() => _busy = false);
    if (err != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
  }

  Future<void> _later() async {
    final m = await showModalBottomSheet<int>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final e in const {60: '1 ghante baad', 180: '3 ghante baad', 720: 'Shaam ko (12 ghante)', 1440: 'Kal'}.entries)
            ListTile(title: Text(e.value), onTap: () => Navigator.of(ctx).pop(e.key)),
        ]),
      ),
    );
    if (m != null) await _do('later', minutes: m);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final body = Map<String, dynamic>.from(v['body'] as Map? ?? const {});
    final status = v['status'] as String? ?? 'pending';
    final open = status == 'pending' || status == 'snoozed';
    final slots = List<String>.from((v['slot_labels'] as List? ?? const []).map((e) => '$e'));
    final text = ((body['translated'] as String?) ?? (body['text'] as String? ?? '')).trim();
    final title = (body['title'] as String? ?? '').trim();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            _avatarDot(v['from'] as String? ?? ''),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(v['from'] as String? ?? 'Hoola', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                Text(v['what'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                _badges(v),
              ]),
            ),
            const Icon(Icons.door_front_door_rounded, color: C.accent),
          ]),
          if (title.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700))),
          if (text.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: Text('“$text”', style: const TextStyle(fontSize: 13.5)),
            ),
          _checked(v),
          if (body['amount'] != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('₹${body['amount']} maang rahe hain · paise sirf aapke UPI app mein aapke tap se',
                  style: const TextStyle(color: C.warn, fontSize: 12.5)),
            ),
          if (slots.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 6, children: [
              for (var i = 0; i < slots.length; i++)
                ChoiceChip(
                  label: Text(slots[i]),
                  selected: (_slot ?? 0) == i,
                  showCheckmark: false,
                  selectedColor: C.accent,
                  labelStyle: TextStyle(color: (_slot ?? 0) == i ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                  onSelected: open ? (_) => setState(() => _slot = i) : null,
                ),
            ]),
          ],
          if (open) ...[
            TextField(
              controller: _note,
              decoration: const InputDecoration(isDense: true, hintText: 'Jawab mein kuch kehna hai? (optional)'),
            ),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: GradientButton(label: 'Haan', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : () => _do('accept'))),
              const SizedBox(width: 8),
              TextButton(onPressed: _busy ? null : () => _do('decline'), child: const Text('Mana', style: TextStyle(color: C.bad))),
              TextButton(onPressed: _busy ? null : _later, child: const Text('Baad mein')),
            ]),
            if (const {'message', 'ask', 'meeting', 'task', 'reminder', 'voice_note'}.contains(v['kind']))
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: _busy ? null : () => _do('handle'),
                  icon: const Icon(Icons.smart_toy_rounded, size: 18, color: C.teal),
                  label: Text('${widget.app.aName}, tum sambhalo', style: const TextStyle(color: C.teal)),
                ),
              ),
          ] else ...[
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_statusText(status), style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700)),
            ),
            _effectButtons(v['effect'] is Map ? Map<String, dynamic>.from(v['effect'] as Map) : null),
          ],
        ]),
      ),
    );
  }
}

/// Someone's Hoola wants to connect.
class HoolaConnectCard extends StatefulWidget {
  const HoolaConnectCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaConnectCard> createState() => _HoolaConnectCardState();
}

class _HoolaConnectCardState extends State<HoolaConnectCard> {
  String? _rel;
  bool _busy = false;

  Future<void> _do(String action) async {
    setState(() => _busy = true);
    final err = await widget.app.hoolaAnswer(widget.v['id'] as String, action, relation: _rel ?? '');
    if (!mounted) return;
    setState(() => _busy = false);
    if (err != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = v['status'] as String? ?? '';
    final rel = _rel ?? (v['relation'] as String? ?? 'friend');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            _avatarDot(v['label'] as String? ?? ''),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(v['label'] as String? ?? 'Hoola', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                Text('@${v['handle'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                _badges(v),
              ]),
            ),
            const Icon(Icons.handshake_rounded, color: C.teal),
          ]),
          if ((v['note'] as String? ?? '').isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 8), child: Text('“${v['note']}”', style: const TextStyle(fontSize: 13.5))),
          if (status == 'incoming') ...[
            const SizedBox(height: 8),
            const Text('Aapke liye yeh kaun hain?', style: TextStyle(color: C.muted, fontSize: 12.5)),
            Wrap(spacing: 6, children: [
              for (final e in const {'family': 'Parivar', 'team': 'Team', 'business': 'Business', 'friend': 'Dost'}.entries)
                ChoiceChip(
                  label: Text(e.value),
                  selected: rel == e.key,
                  showCheckmark: false,
                  selectedColor: C.accent,
                  labelStyle: TextStyle(color: rel == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                  onSelected: (_) => setState(() => _rel = e.key),
                ),
            ]),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: GradientButton(label: 'Jodiye', icon: Icons.check_rounded, height: 42, onTap: _busy ? null : () => _do('accept'))),
              const SizedBox(width: 8),
              TextButton(onPressed: _busy ? null : () => _do('decline'), child: const Text('Mana')),
              TextButton(onPressed: _busy ? null : () => _do('block'), child: const Text('Block', style: TextStyle(color: C.bad))),
            ]),
          ] else
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                  status == 'active'
                      ? 'Jud gaye ✓ ${v['safety_code'] != null ? '· safety code ${v['safety_code']}' : ''}'
                      : status == 'blocked'
                          ? 'Block kiya'
                          : status == 'declined'
                              ? 'Mana kiya'
                              : 'Request bheji',
                  style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700)),
            ),
        ]),
      ),
    );
  }
}

/// What another avatar said back (or something taken in by the owner's rules), with a reply box.
class HoolaMsgCard extends StatelessWidget {
  const HoolaMsgCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  Future<void> _reply(BuildContext context) async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${v['from'] ?? 'Hoola'} ko jawab'),
        content: TextField(controller: c, minLines: 2, maxLines: 6, decoration: const InputDecoration(hintText: 'Kya kehna hai?')),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Bhejo')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    try {
      await app.api!.netReply(v['thread_id'] as String, c.text.trim());
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Jawab bhej diya')));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final effect = v['effect'] is Map ? Map<String, dynamic>.from(v['effect'] as Map) : (v['event'] is Map ? Map<String, dynamic>.from(v['event'] as Map) : null);
    final canReply = (v['thread_id'] as String? ?? '').isNotEmpty && v['kind'] != 'key_warning';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            _avatarDot(v['from'] as String? ?? ''),
            const SizedBox(width: 10),
            Expanded(child: Text(v['from'] as String? ?? 'Hoola', style: const TextStyle(fontWeight: FontWeight.w700))),
            if (v['fyi'] == true) const Text('jaankari', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
          const SizedBox(height: 6),
          Text(v['text'] as String? ?? '', style: const TextStyle(fontSize: 13.5)),
          if (effect != null && (effect['where'] == 'calendar' || effect['where'] == 'reminder'))
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(effect['where'] == 'calendar' ? '📅 Calendar mein jod diya' : '⏰ Reminder laga diya',
                  style: const TextStyle(color: C.teal, fontSize: 12.5)),
            ),
          _effectButtons(effect),
          if (canReply)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(onPressed: () => _reply(context), icon: const Icon(Icons.reply_rounded, size: 18), label: const Text('Jawab')),
            ),
        ]),
      ),
    );
  }
}


/// Invited to a Mandali (group), or a group event.
class HoolaGroupCard extends StatefulWidget {
  const HoolaGroupCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaGroupCard> createState() => _HoolaGroupCardState();
}

class _HoolaGroupCardState extends State<HoolaGroupCard> {
  String? _done;

  Future<void> _answer(String a) async {
    try {
      await widget.app.api!.netGroupAct(widget.v['gid'] as String, 'answer_invite', answer: a);
      if (mounted) setState(() => _done = a == 'accept' ? 'Group mein aa gaye ✓' : 'Mana kiya');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final invite = v['event'] == 'invite' && v['status'] == 'invited';
    final text = switch (v['event']) {
      'invite' => '${v['from'] ?? ''} ne aapko group mein bulaya hai',
      'group_join' => '${v['from'] ?? ''} group mein aa gaye',
      'group_leave' => '${v['from'] ?? ''} ne group chhoda',
      'removed' => 'Aapko group se hata diya gaya',
      _ => '',
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text(v['emoji'] as String? ?? '👥', style: const TextStyle(fontSize: 24)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(v['name'] as String? ?? 'Mandali', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                Text(text, style: const TextStyle(color: C.muted, fontSize: 12.5)),
              ]),
            ),
          ]),
          if (invite && _done == null) ...[
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: GradientButton(label: 'Judiye', icon: Icons.group_add_rounded, height: 42, onTap: () => _answer('accept'))),
              const SizedBox(width: 8),
              TextButton(onPressed: () => _answer('decline'), child: const Text('Mana')),
            ]),
          ],
          if (_done != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_done!, style: const TextStyle(color: C.ok))),
        ]),
      ),
    );
  }
}

/// A post in a Mandali that the owner's avatar decided to show (mention, task for the owner, or 'all').
class HoolaGroupPostCard extends StatefulWidget {
  const HoolaGroupPostCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaGroupPostCard> createState() => _HoolaGroupPostCardState();
}

class _HoolaGroupPostCardState extends State<HoolaGroupPostCard> {
  String? _status;

  Future<void> _task(String a) async {
    try {
      final r = await widget.app.api!.netGroupTask(widget.v['id'] as String, a);
      if (mounted) setState(() => _status = r['status'] as String?);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _file() async {
    try {
      await widget.app.api!.netGroupFile(widget.v['id'] as String);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('File phone par aa gayi')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final body = Map<String, dynamic>.from(v['body'] as Map? ?? const {});
    final task = v['kind'] == 'task';
    final status = _status ?? v['task_status'] as String? ?? '';
    final text = (body['text'] ?? v['text'] ?? '') as String;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.groups_rounded, color: C.violet, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text('${v['group'] ?? ''} · ${v['author'] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
            ),
            if (v['mention'] == true) const Text('@aap', style: TextStyle(color: C.accent, fontSize: 11.5, fontWeight: FontWeight.w700)),
          ]),
          if (task) Padding(padding: const EdgeInsets.only(top: 6), child: Text('🧰 ${body['title'] ?? 'Kaam'}${(body['due'] ?? '') != '' ? ' · ${body['due']}' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w700))),
          if (text.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(text, style: const TextStyle(fontSize: 13.5))),
          if ((body['name'] ?? '') != '') _checked({...body}),
          if ((body['name'] ?? '') != '' && body['qid'] != null)
            Align(alignment: Alignment.centerLeft, child: TextButton.icon(onPressed: _file, icon: const Icon(Icons.download_rounded, size: 18), label: const Text('File lijiye'))),
          if (task && v['for_me'] == true)
            status == 'open' || status.isEmpty
                ? Row(children: [
                    TextButton(onPressed: () => _task('accepted'), child: const Text('Le liya')),
                    TextButton(onPressed: () => _task('done'), child: const Text('Ho gaya')),
                    TextButton(onPressed: () => _task('declined'), child: const Text('Mana', style: TextStyle(color: C.bad))),
                  ])
                : status == 'accepted'
                    ? Row(children: [
                        const Text('Aapne liya', style: TextStyle(color: C.ok)),
                        const Spacer(),
                        TextButton(onPressed: () => _task('done'), child: const Text('Ho gaya')),
                      ])
                    : Text(status == 'done' ? 'Poora ✓' : status, style: const TextStyle(color: C.ok)),
        ]),
      ),
    );
  }
}


/// The avatar learned something and asks before sharing a privacy-filtered version with the owner's Samaj.
class HoolaLessonCard extends StatefulWidget {
  const HoolaLessonCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaLessonCard> createState() => _HoolaLessonCardState();
}

class _HoolaLessonCardState extends State<HoolaLessonCard> {
  String? _done;

  Future<void> _act(String a) async {
    try {
      await widget.app.api!.netLessonAct(widget.v['id'] as String, a);
      if (mounted) setState(() => _done = a == 'share' ? 'Samaj ke saath share kiya ✓' : 'Share nahi kiya');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final removed = List<String>.from((v['share_removed'] as List? ?? const []).map((e) => '$e'));
    final comms = List<Map<String, dynamic>>.from((v['communities'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.lightbulb_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${widget.app.aName} ne seekha', style: const TextStyle(fontWeight: FontWeight.w700))),
          ]),
          const SizedBox(height: 6),
          Text(v['text'] as String? ?? '', style: const TextStyle(fontSize: 13.5)),
          if ((v['share_text'] ?? '') != '') ...[
            const SizedBox(height: 8),
            const Text('Samaj ko yeh jayega (bina personal jaankari):', style: TextStyle(color: C.muted, fontSize: 12.5)),
            Container(
              margin: const EdgeInsets.only(top: 4),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: Text(v['share_text'] as String, style: const TextStyle(fontSize: 13)),
            ),
            if (removed.isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text('Hataya: ${removed.join(', ')}', style: const TextStyle(color: C.teal, fontSize: 12))),
            if (comms.isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text('Kahan: ${comms.map((c) => c['name']).join(', ')}', style: const TextStyle(color: C.faint, fontSize: 12))),
          ],
          if (_done == null && v['share_status'] == 'proposed')
            Row(children: [
              TextButton(onPressed: () => _act('share'), child: const Text('Share karo')),
              TextButton(onPressed: () => _act('dont_share'), child: const Text('Nahi')),
            ]),
          if (_done != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_done!, style: const TextStyle(color: C.ok))),
        ]),
      ),
    );
  }
}

/// Something from a Samaj the owner's avatar decided to show (alert, an answer to their question, a review / join
/// request for moderators, or a question it can answer from what it learned).
class HoolaSamajCard extends StatefulWidget {
  const HoolaSamajCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaSamajCard> createState() => _HoolaSamajCardState();
}

class _HoolaSamajCardState extends State<HoolaSamajCard> {
  String? _done;

  Future<void> _run(Future<dynamic> Function() f, String ok) async {
    try {
      await f();
      if (mounted) setState(() => _done = ok);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final api = widget.app.api!;
    final item = v['item'] is Map ? Map<String, dynamic>.from(v['item'] as Map) : <String, dynamic>{};
    final data = item['data'] is Map ? Map<String, dynamic>.from(item['data'] as Map) : <String, dynamic>{};
    final ev = v['event'] as String? ?? 'item';
    final kind = item['kind'] as String? ?? '';
    final icon = switch (kind) {
      'alert' => Icons.warning_amber_rounded,
      'answer' => Icons.question_answer_rounded,
      'question' => Icons.help_rounded,
      'skill' => Icons.extension_rounded,
      _ => Icons.public_rounded,
    };
    final head = switch (ev) {
      'review' => 'Skill manzoori ka intezaar',
      'report' => 'Report aayi',
      'join_request' => '${v['from'] ?? ''} judna chahte hain',
      'joined' => 'Samaj mein aa gaye',
      'can_answer' => 'Is sawaal ka jawab aapki seekh mein hai',
      'answered' => 'Maine jawab diya',
      _ => kind == 'alert' ? 'Chetavni' : kind == 'answer' && v['for_me'] == true ? 'Aapke sawaal ka jawab' : (item['author'] as String? ?? ''),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(icon, color: kind == 'alert' ? C.bad : C.teal, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text('${v['community'] ?? 'Samaj'} · $head',
                  maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
            ),
          ]),
          if ((item['title'] ?? '') != '') Padding(padding: const EdgeInsets.only(top: 6), child: Text(item['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700))),
          if ((item['text'] ?? v['text'] ?? '') != '')
            Padding(padding: const EdgeInsets.only(top: 4), child: Text((item['text'] ?? v['text']) as String, style: const TextStyle(fontSize: 13.5))),
          if (kind == 'alert' && (data['value'] ?? '') != '')
            Padding(padding: const EdgeInsets.only(top: 4), child: SelectableText('${data['type']}: ${data['value']}', style: const TextStyle(color: C.bad, fontSize: 12))),
          if (ev == 'can_answer') ...[
            Container(
              margin: const EdgeInsets.only(top: 6),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: Text('Draft: ${v['draft'] ?? ''}', style: const TextStyle(fontSize: 13)),
            ),
            if (_done == null)
              TextButton(
                onPressed: () => _run(() => api.netSamajPost(v['cid'] as String, 'answer', {'parent': item['item_id'], 'text': v['draft']}), 'Jawab bhej diya ✓'),
                child: const Text('Haan, jawab bhejo'),
              ),
          ],
          if (ev == 'review' && _done == null)
            TextButton(
              onPressed: () => _run(() => api.netSamajItem(item['item_id'] as String, {'action': 'moderate', 'mod_action': 'approve'}), 'Manzoor ✓'),
              child: const Text('Manzoor karo'),
            ),
          if (ev == 'join_request' && _done == null)
            TextButton(
              onPressed: () => _run(() => api.netSamajAct(v['cid'] as String, {'action': 'moderate_member', 'mod_action': 'approve_member', 'who': v['address']}), 'Jod liya ✓'),
              child: const Text('Aane do'),
            ),
          if (ev == 'item' && kind == 'skill' && _done == null)
            TextButton(onPressed: () => _run(() => api.netSamajItem(item['item_id'] as String, {'action': 'install'}), 'Skill lag gayi ✓'),
                child: const Text('Skill install karo')),
          if (ev == 'item' && (kind == 'answer' || kind == 'card') && _done == null)
            Row(children: [
              TextButton(onPressed: () => _run(() => api.netSamajItem(item['item_id'] as String, {'action': 'rate', 'helpful': true}), 'Dhanyavaad ✓'),
                  child: const Text('👍 Kaam ka')),
              TextButton(onPressed: () => _run(() => api.netSamajItem(item['item_id'] as String, {'action': 'report'}), 'Report kiya'),
                  child: const Text('Report', style: TextStyle(color: C.bad))),
            ]),
          if (_done != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_done!, style: const TextStyle(color: C.ok))),
        ]),
      ),
    );
  }
}


Future<String?> _ask(BuildContext context, String title, String hint) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: TextField(controller: c, minLines: 1, maxLines: 4, decoration: InputDecoration(hintText: hint)),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('OK')),
      ],
    ),
  );
  return ok == true ? c.text.trim() : null;
}

/// A job that came to the owner along a chain (take / pass on / done / send back), or news about one they started.
class HoolaChainCard extends StatefulWidget {
  const HoolaChainCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaChainCard> createState() => _HoolaChainCardState();
}

class _HoolaChainCardState extends State<HoolaChainCard> {
  String? _done;

  Future<void> _act(String a) async {
    String to = '';
    String note = '';
    if (a == 'pass') {
      final t = await _ask(context, 'Kise dena hai?', '@hoola.id ya naam');
      if (t == null || t.isEmpty) return;
      to = t;
    }
    if (a == 'done' || a == 'decline') {
      if (!mounted) return;
      final n = await _ask(context, a == 'done' ? 'Kya kiya?' : 'Kyon wapas?', 'Chhota note');
      if (n == null) return;
      note = n;
    }
    try {
      final r = await widget.app.api!.netChainAct(widget.v['chain_id'] as String, a, to: to, note: note);
      if (mounted) setState(() => _done = {'accepted': 'Aapne le liya', 'passed': 'Aage diya: ${r['to'] ?? ''}', 'done': 'Ho gaya ✓', 'declined': 'Wapas bheja'}[r['status']] ?? '${r['status']}');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final withMe = v['event'] == 'with_me' || v['event'] == 'back';
    final steps = List<Map<String, dynamic>>.from((v['steps'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.link_rounded, color: C.violet),
            const SizedBox(width: 8),
            Expanded(
              child: Text(withMe ? '${v['from'] ?? ''} ne kaam bheja' : (v['text'] as String? ?? 'Kaam ki khabar'),
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
            ),
            if ((v['ref'] ?? '') != '') Text(v['ref'] as String, style: const TextStyle(color: C.accent, fontSize: 12)),
          ]),
          const SizedBox(height: 4),
          Text(v['goal'] as String? ?? '', style: const TextStyle(fontSize: 13.5)),
          for (final st in steps)
            Text('• ${st['who']}: ${st['action']}${(st['note'] ?? '') != '' ? ' · ${st['note']}' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 12)),
          if (withMe && _done == null)
            Wrap(spacing: 2, children: [
              TextButton(onPressed: () => _act('accept'), child: const Text('Le liya')),
              TextButton(onPressed: () => _act('pass'), child: const Text('Aage bhejo')),
              TextButton(onPressed: () => _act('done'), child: const Text('Ho gaya')),
              TextButton(onPressed: () => _act('decline'), child: const Text('Wapas', style: TextStyle(color: C.bad))),
            ]),
          if (_done != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_done!, style: const TextStyle(color: C.ok))),
        ]),
      ),
    );
  }
}

/// A new complaint ticket at the owner's business counter.
class HoolaTicketCard extends StatefulWidget {
  const HoolaTicketCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaTicketCard> createState() => _HoolaTicketCardState();
}

class _HoolaTicketCardState extends State<HoolaTicketCard> {
  String? _status;

  Future<void> _set(String status) async {
    final note = await _ask(context, 'Customer ko kya batayein?', 'Jaise: technician kal 11 baje aayega');
    if (note == null) return;
    try {
      final r = await widget.app.api!.netTicket(widget.v['number'] as String, status: status, note: note);
      if (mounted) setState(() => _status = r['status'] as String?);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _assign() async {
    final to = await _ask(context, 'Kise dena hai?', '@technician.id');
    if (to == null || to.isEmpty) return;
    try {
      await widget.app.api!.netTicket(widget.v['number'] as String, to: to);
      if (mounted) setState(() => _status = 'assigned');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = _status ?? v['status'] as String? ?? 'open';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.confirmation_number_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${v['number']} · ${v['customer'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700))),
            Text(status, style: const TextStyle(color: C.teal, fontSize: 12)),
          ]),
          const SizedBox(height: 4),
          Text(v['text'] as String? ?? '', style: const TextStyle(fontSize: 13.5)),
          if ((v['webhook'] ?? '') != '') Text('Aapke system ko bheja: ${v['webhook']}', style: const TextStyle(color: C.faint, fontSize: 11.5)),
          if (status != 'resolved' && status != 'closed')
            Wrap(spacing: 2, children: [
              TextButton(onPressed: _assign, child: const Text('Technician ko do')),
              TextButton(onPressed: () => _set('in_progress'), child: const Text('Kaam chalu')),
              TextButton(onPressed: () => _set('resolved'), child: const Text('Theek ho gaya')),
            ]),
        ]),
      ),
    );
  }
}


/// The owner's avatar wants to send something that needs the owner's own tap (a file, an email, a contact, a place,
/// a payment request, or a message with phone numbers / IDs in it).
class HoolaOutboxCard extends StatefulWidget {
  const HoolaOutboxCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<HoolaOutboxCard> createState() => _HoolaOutboxCardState();
}

class _HoolaOutboxCardState extends State<HoolaOutboxCard> {
  String? _done;

  Future<void> _act(String a) async {
    try {
      await widget.app.api!.netOutbox(widget.v['id'] as String, a);
      if (mounted) setState(() => _done = a == 'send' ? 'Bhej diya ✓' : 'Nahi bheja');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final body = Map<String, dynamic>.from(v['body'] as Map? ?? const {});
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.outbox_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text('${v['to'] ?? ''} ko bhejein?', style: const TextStyle(fontWeight: FontWeight.w700))),
          ]),
          Text('Aapka tap chahiye: ${v['reason'] ?? ''}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
          if ((v['text'] ?? '') != '')
            Container(
              margin: const EdgeInsets.only(top: 6),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: Text(v['text'] as String, style: const TextStyle(fontSize: 13)),
            ),
          if ((body['name'] ?? body['place'] ?? body['email_id'] ?? '') != '')
            Text('${body['name'] ?? body['place'] ?? 'email'}', style: const TextStyle(color: C.chip, fontSize: 12.5)),
          if (_done == null)
            Row(children: [
              Expanded(child: GradientButton(label: 'Bhejo', icon: Icons.send_rounded, height: 42, onTap: () => _act('send'))),
              const SizedBox(width: 8),
              TextButton(onPressed: () => _act('cancel'), child: const Text('Mat bhejo')),
            ])
          else
            Padding(padding: const EdgeInsets.only(top: 6), child: Text(_done!, style: const TextStyle(color: C.ok))),
        ]),
      ),
    );
  }
}
