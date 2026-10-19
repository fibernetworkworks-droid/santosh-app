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
      'handled' => 'Hoola sambhal raha hai',
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
    final text = (body['text'] as String? ?? '').trim();
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
