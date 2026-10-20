/// Hoola Employee v0.59: the business WhatsApp inbox (official Cloud API), appointments and dues.
/// Chats (Hoola answers; the owner can take over) · Appointments · Baaki (who owes what). Rules live on the server.
library;

import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';

List<Map<String, dynamic>> _rows(Object? o) =>
    List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

String _t(String? iso, {bool date = false}) {
  final t = iso == null ? null : DateTime.tryParse(iso)?.toLocal();
  if (t == null) return '';
  final n = DateTime.now();
  final hm = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  final same = t.year == n.year && t.month == n.month && t.day == n.day;
  return (same && !date) ? hm : '${t.day}/${t.month} $hm';
}

void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

/// The Inbox tab inside the Employee screen.
class EmployeeInboxTab extends StatefulWidget {
  const EmployeeInboxTab({super.key, required this.app});
  final Santosh app;
  @override
  State<EmployeeInboxTab> createState() => _EmployeeInboxTabState();
}

class _EmployeeInboxTabState extends State<EmployeeInboxTab> {
  String _view = 'chats';
  Map<String, dynamic>? _o;
  String? _err;
  int _tick = -1;
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    widget.app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    widget.app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (widget.app.employeeTick != _tick && _view == 'chats') _load();
  }

  Future<void> _load() async {
    _tick = widget.app.employeeTick;
    try {
      final o = await _api.employeeInbox();
      if (mounted) setState(() {
        _o = o;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final sum = Map<String, dynamic>.from((_o?['summary'] as Map?) ?? const {});
    final dues = Map<String, dynamic>.from((sum['dues'] as Map?) ?? const {});
    final today = _rows(sum['today']);
    final noNumber = _o != null && _rows(sum['channels']).isEmpty;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
        child: SegmentedButton<String>(
          showSelectedIcon: false,
          segments: [
            ButtonSegment(value: 'chats', label: Text('Chats${(sum['unread'] as num? ?? 0) > 0 ? ' · ${sum['unread']}' : ''}')),
            ButtonSegment(value: 'appts', label: Text('Appointment${today.isNotEmpty ? ' · ${today.length}' : ''}')),
            ButtonSegment(value: 'dues', label: Text('Baaki${(dues['open'] as num? ?? 0) > 0 ? ' · ${dues['open']}' : ''}')),
          ],
          selected: {_view},
          onSelectionChanged: (v) => setState(() => _view = v.first),
        ),
      ),
      Expanded(
        child: _view == 'appts'
            ? _ApptsView(api: _api)
            : _view == 'dues'
                ? _DuesView(api: _api)
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 32), children: [
                      if (_err != null) Padding(padding: const EdgeInsets.all(8), child: Text(_err!, style: const TextStyle(color: C.bad))),
                      if (_o == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
                      if (noNumber)
                        const Glass(
                          child: Text(
                              'Business ka WhatsApp number abhi juda nahi hai. "Naukri" tab mein WhatsApp Business (Cloud API) ka '
                              'phone number ID daaliye. Sirf Meta ka official API: personal WhatsApp kabhi nahi.',
                              style: TextStyle(color: C.chip, height: 1.35)),
                        ),
                      for (final c in _rows(_o?['contacts'])) _ChatRow(c: c, onTap: () => _open(c)),
                      if (_o != null && _rows(_o?['contacts']).isEmpty && !noNumber)
                        const Padding(
                            padding: EdgeInsets.all(30),
                            child: Center(child: Text('Graahakon ke message yahan dikhenge.', style: TextStyle(color: C.muted)))),
                    ]),
                  ),
      ),
    ]);
  }

  Future<void> _open(Map<String, dynamic> c) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => BizThreadScreen(app: widget.app, contactId: c['id'] as String)));
    _load();
  }
}

class _ChatRow extends StatelessWidget {
  const _ChatRow({required this.c, required this.onTap});
  final Map<String, dynamic> c;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final unread = (c['unread'] as num? ?? 0).toInt();
    final name = '${c['name']}';
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 6),
      onTap: onTap,
      leading: CircleAvatar(
          backgroundColor: c['human'] == true ? C.accent2 : C.violet,
          child: Text(name.isEmpty ? '?' : name.characters.first.toUpperCase(),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
      title: Row(children: [
        Expanded(child: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700))),
        Text(_t(c['last_at'] as String?), style: const TextStyle(color: C.faint, fontSize: 11.5)),
      ]),
      subtitle: Row(children: [
        if (c['human'] == true) const Padding(padding: EdgeInsets.only(right: 6), child: Pill('AAP', fg: C.accent2)),
        if (c['opted_out'] == true) const Padding(padding: EdgeInsets.only(right: 6), child: Pill('STOP', fg: C.bad)),
        Expanded(child: Text('${c['last_text']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5))),
        if (unread > 0)
          Container(
            margin: const EdgeInsets.only(left: 6),
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(color: C.ok, borderRadius: BorderRadius.circular(99)),
            child: Text('$unread', style: const TextStyle(color: C.onAccent, fontSize: 11, fontWeight: FontWeight.w800)),
          ),
      ]),
    );
  }
}

/// One customer's WhatsApp chat: Hoola's and the owner's replies, take over / give back, their appointments and dues.
class BizThreadScreen extends StatefulWidget {
  const BizThreadScreen({super.key, required this.app, required this.contactId});
  final Santosh app;
  final String contactId;
  @override
  State<BizThreadScreen> createState() => _BizThreadScreenState();
}

class _BizThreadScreenState extends State<BizThreadScreen> {
  Map<String, dynamic>? _o;
  String? _err;
  bool _busy = false;
  int _tick = -1;
  final _box = TextEditingController();
  final _scroll = ScrollController();
  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    widget.app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    widget.app.removeListener(_onApp);
    _box.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _onApp() {
    if (widget.app.employeeTick != _tick) _load();
  }

  Future<void> _load() async {
    _tick = widget.app.employeeTick;
    try {
      final o = await _api.employeeThread(widget.contactId);
      if (!mounted) return;
      setState(() {
        _o = o;
        _err = null;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _send() async {
    final text = _box.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() => _busy = true);
    try {
      await _api.employeeSendTo(widget.contactId, text);
      _box.clear();
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _human(bool on) async {
    try {
      await _api.employeeHuman(widget.contactId, on);
      if (!on) {
        await _api.employeeAnswerNow(widget.contactId);
      }
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = Map<String, dynamic>.from((_o?['contact'] as Map?) ?? const {});
    final msgs = _rows(_o?['messages']);
    final human = c['human'] == true;
    final open = c['window_open'] == true;
    final name = widget.app.aName;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${c['name'] ?? ''}', style: const TextStyle(fontSize: 16)),
          Text(human ? 'Aap jawab de rahi hain' : '$name jawab de raha hai',
              style: TextStyle(fontSize: 11.5, color: human ? C.accent2 : C.ok)),
        ]),
        actions: [
          if (_o != null)
            TextButton(
              onPressed: () => _human(!human),
              child: Text(human ? '$name ko do' : 'Main sambhalungi'),
            ),
        ],
      ),
      body: Aurora(
        child: Column(children: [
          if (_err != null) Padding(padding: const EdgeInsets.all(8), child: Text(_err!, style: const TextStyle(color: C.bad))),
          if (_rows(_o?['appointments']).isNotEmpty || _rows(_o?['dues']).isNotEmpty)
            SizedBox(
              height: 40,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
                for (final a in _rows(_o?['appointments']))
                  Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: Chip(
                          avatar: const Icon(Icons.event_rounded, size: 16),
                          label: Text('${_t(a['start'] as String?, date: true)} · ${a['status']}', style: const TextStyle(fontSize: 12)))),
                for (final d in _rows(_o?['dues']))
                  Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: Chip(
                          avatar: const Icon(Icons.currency_rupee_rounded, size: 16),
                          label: Text('${d['amount_text']} · ${d['status']}', style: const TextStyle(fontSize: 12)))),
              ]),
            ),
          Expanded(
            child: _o == null
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                    itemCount: msgs.length,
                    itemBuilder: (_, i) => _Bubble(m: msgs[i], avatar: name),
                  ),
          ),
          if (!open && _o != null)
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 0, 16, 6),
              child: Text('24 ghante se graahak ka message nahi aaya: WhatsApp ke niyam se ab sirf approved template ja sakta hai.',
                  style: TextStyle(color: C.warn, fontSize: 12)),
            ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _box,
                    enabled: open && c['opted_out'] != true,
                    minLines: 1,
                    maxLines: 4,
                    textCapitalization: TextCapitalization.sentences,
                    decoration: InputDecoration(
                      hintText: human ? 'Apna jawab likhiye' : 'Aap likhengi to $name ruk jayega',
                      filled: true,
                      fillColor: const Color(0x14FFFFFF),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(20), borderSide: BorderSide.none),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                IconButton.filled(
                  onPressed: _busy || !open ? null : _send,
                  icon: const Icon(Icons.send_rounded),
                  style: IconButton.styleFrom(backgroundColor: C.accent, foregroundColor: C.onAccent),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.m, required this.avatar});
  final Map<String, dynamic> m;
  final String avatar;
  @override
  Widget build(BuildContext context) {
    final mine = m['direction'] == 'out';
    final by = m['by'] as String? ?? '';
    final who = !mine ? '' : (by == 'hoola' ? avatar : by == 'owner' ? 'Aap' : by.startsWith('staff') ? 'Team' : 'System');
    final st = m['status'] as String? ?? '';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * .78),
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.fromLTRB(11, 7, 11, 6),
        decoration: BoxDecoration(
          color: mine ? (by == 'hoola' ? const Color(0x337C5CFF) : const Color(0x33C055F5)) : const Color(0x17FFFFFF),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(14),
            topRight: const Radius.circular(14),
            bottomLeft: Radius.circular(mine ? 14 : 4),
            bottomRight: Radius.circular(mine ? 4 : 14),
          ),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (who.isNotEmpty) Text(who, style: const TextStyle(fontSize: 11, color: C.accentSoft, fontWeight: FontWeight.w700)),
          SelectableText('${m['text']}', style: const TextStyle(fontSize: 14, height: 1.3)),
          const SizedBox(height: 2),
          Text(
              '${_t(m['at'] as String?)}${mine && st.isNotEmpty ? ' · ${{'sent': 'gaya', 'delivered': 'pahuncha', 'read': 'padha', 'failed': 'nahi gaya', 'held': 'ruka'}[st] ?? st}' : ''}',
              style: TextStyle(fontSize: 10.5, color: st == 'failed' || st == 'held' ? C.bad : C.faint)),
        ]),
      ),
    );
  }
}

// ------------------------------------------------------------------ appointments
class _ApptsView extends StatefulWidget {
  const _ApptsView({required this.api});
  final Api api;
  @override
  State<_ApptsView> createState() => _ApptsViewState();
}

class _ApptsViewState extends State<_ApptsView> {
  List<Map<String, dynamic>>? _rows;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.api.employeeAppointments();
      if (mounted) setState(() => _rows = r);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _add() async {
    List<String> slots;
    try {
      slots = await widget.api.employeeSlots(days: 7);
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return;
    }
    if (!mounted) return;
    final name = TextEditingController();
    final phone = TextEditingController();
    final note = TextEditingController();
    String? pick = slots.isNotEmpty ? slots.first : null;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: const Text('Naya appointment'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (slots.isEmpty) const Text('Agle 7 din mein koi khaali samay nahi (Naukri tab mein samay dekhiye).'),
              if (slots.isNotEmpty)
                DropdownButton<String>(
                  value: pick,
                  isExpanded: true,
                  dropdownColor: C.bgBottom,
                  items: [for (final s in slots) DropdownMenuItem(value: s, child: Text(s))],
                  onChanged: (v) => set(() => pick = v),
                ),
              TextField(controller: name, textCapitalization: TextCapitalization.words, decoration: const InputDecoration(labelText: 'Naam')),
              TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone')),
              TextField(controller: note, decoration: const InputDecoration(labelText: 'Kis liye')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
            TextButton(onPressed: pick == null ? null : () => Navigator.pop(ctx, true), child: const Text('Book karo')),
          ],
        ),
      ),
    );
    if (ok != true || pick == null) return;
    try {
      await widget.api.employeeBook(pick!, name.text.trim(), phone.text.trim(), note.text.trim());
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _status(Map<String, dynamic> a, String st) async {
    try {
      await widget.api.employeeApptStatus(a['id'] as String, st);
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 32), children: [
        GlassButton(label: 'Appointment jodiye', icon: Icons.event_available_rounded, onTap: _add),
        const SizedBox(height: 8),
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        if (rows == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
        if (rows != null && rows.isEmpty)
          const Padding(padding: EdgeInsets.all(30), child: Center(child: Text('Aage koi appointment nahi.', style: TextStyle(color: C.muted)))),
        for (final a in rows ?? const <Map<String, dynamic>>[])
          ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 6),
            leading: Icon(
                a['status'] == 'done'
                    ? Icons.check_circle_rounded
                    : a['status'] == 'cancelled'
                        ? Icons.cancel_rounded
                        : a['status'] == 'no_show'
                            ? Icons.person_off_rounded
                            : Icons.event_rounded,
                color: a['status'] == 'booked' ? C.accent : C.muted),
            title: Text('${_t(a['start'] as String?, date: true)} · ${a['name'] == '' ? 'Bina naam' : a['name']}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(
                [if ('${a['note']}'.isNotEmpty) '${a['note']}', if ('${a['phone']}'.isNotEmpty) '+${a['phone']}', '${a['minutes']} min']
                    .join(' · '),
                style: const TextStyle(fontSize: 12)),
            trailing: PopupMenuButton<String>(
              color: C.bgBottom,
              onSelected: (v) => _status(a, v),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'done', child: Text('Ho gaya')),
                PopupMenuItem(value: 'no_show', child: Text('Nahi aaye')),
                PopupMenuItem(value: 'cancelled', child: Text('Cancel')),
                PopupMenuItem(value: 'booked', child: Text('Phir se booked')),
              ],
            ),
          ),
      ]),
    );
  }
}

// ------------------------------------------------------------------ dues
class _DuesView extends StatefulWidget {
  const _DuesView({required this.api});
  final Api api;
  @override
  State<_DuesView> createState() => _DuesViewState();
}

class _DuesViewState extends State<_DuesView> {
  Map<String, dynamic>? _o;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = await widget.api.employeeDues();
      if (mounted) setState(() => _o = o);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _add() async {
    final name = TextEditingController();
    final phone = TextEditingController();
    final amount = TextEditingController();
    final date = TextEditingController();
    final note = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Baaki jodiye'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: name, textCapitalization: TextCapitalization.words, decoration: const InputDecoration(labelText: 'Naam')),
            TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'WhatsApp number')),
            TextField(controller: amount, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Rakam (₹)')),
            TextField(controller: date, decoration: const InputDecoration(labelText: 'Tareekh (2026-11-05)')),
            TextField(controller: note, decoration: const InputDecoration(labelText: 'Kis cheez ka')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodo')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.api.employeeAddDue({
        'name': name.text.trim(),
        'phone': phone.text.trim(),
        'amount': double.tryParse(amount.text.trim()) ?? 0,
        'due_date': date.text.trim(),
        'note': note.text.trim(),
      });
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _import() async {
    try {
      final res = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: const ['csv'], withData: true);
      final f = res?.files.single;
      if (f == null || f.bytes == null) return;
      final r = await widget.api.employeeImportDues(f.name, f.bytes!);
      if (mounted) _snack(context, '${r['added']} jode${(r['skipped_rows'] as List? ?? const []).isNotEmpty ? ', kuch line chhodi' : ''}');
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _status(Map<String, dynamic> d, String st) async {
    try {
      await widget.api.employeeDueStatus(d['id'] as String, st);
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final sum = Map<String, dynamic>.from((_o?['summary'] as Map?) ?? const {});
    final rows = _rows(_o?['dues']);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 32), children: [
        if (_o != null)
          Glass(
            child: Text(
                'Khule: ${sum['open']} · kul ${sum['total']}${(sum['late'] as num? ?? 0) > 0 ? '\nDer se: ${sum['late']} · ${sum['late_total']}' : ''}\n'
                'Graahak WhatsApp par poochhe to Hoola sirf unka baaki batata hai aur aapke UPI ID ka link deta hai. Paisa aaya, yeh aap batati hain.',
                style: const TextStyle(color: C.chip, height: 1.35)),
          ),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: GlassButton(label: 'Jodiye', icon: Icons.add_rounded, onTap: _add)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'CSV se', icon: Icons.upload_file_rounded, onTap: _import)),
        ]),
        const SizedBox(height: 6),
        const Text('CSV: name, phone, amount, due_date, note', style: TextStyle(color: C.faint, fontSize: 11.5)),
        if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
        for (final d in rows)
          ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 6),
            title: Text('${d['name'] == '' ? '+${d['phone']}' : d['name']} · ${d['amount_text']}', style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(
                [
                  {'open': 'Baaki', 'promised': 'Waada ${d['promised_on']}', 'paid': 'Mil gaya', 'disputed': 'Vivaad', 'written_off': 'Chhod diya'}[d['status']] ??
                      '${d['status']}',
                  if ('${d['due_date']}'.isNotEmpty) 'tareekh ${d['due_date']}',
                  if ('${d['note']}'.isNotEmpty) '${d['note']}',
                ].join(' · '),
                style: const TextStyle(fontSize: 12)),
            trailing: PopupMenuButton<String>(
              color: C.bgBottom,
              onSelected: (v) => _status(d, v),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'paid', child: Text('Paisa mil gaya')),
                PopupMenuItem(value: 'disputed', child: Text('Vivaad hai')),
                PopupMenuItem(value: 'written_off', child: Text('Chhod do')),
                PopupMenuItem(value: 'open', child: Text('Phir se baaki')),
              ],
            ),
          ),
      ]),
    );
  }
}

/// Naukri tab: the business's WhatsApp number (official Cloud API).
class BizChannelCard extends StatefulWidget {
  const BizChannelCard({super.key, required this.api});
  final Api api;
  @override
  State<BizChannelCard> createState() => _BizChannelCardState();
}

class _BizChannelCardState extends State<BizChannelCard> {
  List<Map<String, dynamic>> _ch = const [];
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.api.employeeChannels();
      if (mounted) setState(() {
        _ch = _rows(r['channels']);
        _loaded = true;
      });
    } catch (_) {
      if (mounted) setState(() => _loaded = true);
    }
  }

  Future<void> _add() async {
    final id = TextEditingController();
    final numc = TextEditingController();
    final tok = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: const Text('Business WhatsApp number'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Meta WhatsApp Manager > Phone numbers se. Sirf official Cloud API.', style: TextStyle(color: C.muted, fontSize: 12.5)),
            TextField(controller: id, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Phone number ID')),
            TextField(controller: numc, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Number (91...)')),
            TextField(
                controller: tok,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Access token (zaroori nahi)', helperText: 'Server par encrypted rehta hai')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Jodo')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.api.employeeSetChannel(id.text.trim(), numc.text.trim(), tok.text.trim());
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('WhatsApp number', style: display(17)),
          const SizedBox(height: 4),
          const Text('Graahak is number par likhenge, Hoola naukri ke niyam se jawab dega. Webhook: /webhooks/whatsapp',
              style: TextStyle(color: C.muted, fontSize: 12.5)),
          if (!_loaded) const LinearProgressIndicator(),
          for (final c in _ch)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.chat_rounded, color: C.ok),
              title: Text(c['display_number'] == '' ? 'ID ${c['phone_number_id']}' : '+${c['display_number']}'),
              subtitle: Text('ID ${c['phone_number_id']}${c['own_token'] == true ? ' · apna token' : ''}', style: const TextStyle(fontSize: 12)),
              trailing: IconButton(
                icon: const Icon(Icons.link_off_rounded),
                onPressed: () async {
                  try {
                    await widget.api.employeeRemoveChannel(c['phone_number_id'] as String);
                    await _load();
                  } catch (e) {
                    if (context.mounted) _snack(context, '$e');
                  }
                },
              ),
            ),
          if (_loaded && _ch.isEmpty) TextButton.icon(onPressed: _add, icon: const Icon(Icons.add_rounded), label: const Text('Number jodiye')),
        ]),
      );
}

/// Chat card: a WhatsApp customer needs the owner (Hoola handed the chat over).
class BizHandoverCard extends StatelessWidget {
  const BizHandoverCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final c = Map<String, dynamic>.from((v['contact'] as Map?) ?? const {});
    return Glass(
      border: C.accent2.withOpacity(.5),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.support_agent_rounded, color: C.accent2, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('WhatsApp: ${c['name'] ?? ''} ko aapki zaroorat hai', style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        if ('${v['reason'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('${v['reason']}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
        const SizedBox(height: 8),
        GradientButton(
          label: 'Chat kholo',
          icon: Icons.chat_rounded,
          height: 44,
          onTap: c['id'] == null
              ? null
              : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BizThreadScreen(app: app, contactId: c['id'] as String))),
        ),
      ]),
    );
  }
}
