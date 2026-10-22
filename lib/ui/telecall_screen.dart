/// Profile > Telecaller (v0.99): Hoola prepares the calls, a PERSON makes them.
/// Aaj (who to call now, each with WHY; Call opens the phone's own dialer; coming back opens "kya hua?"), Log (quick
/// outcome chips, her words or a voice note, next call time, WhatsApp draft she sends), Log list (leads, import a sheet),
/// Report (today / week, best hours, objections, sources), Niyam (business, pitch, hours, goal, registered line, rules).
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import '../voice_recorder.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _quick = [
  ('no_answer', 'Uthaya nahi', Icons.phone_missed_rounded),
  ('busy', 'Busy', Icons.phone_locked_rounded),
  ('switched_off', 'Switch off', Icons.phone_disabled_rounded),
  ('interested', 'Interested', Icons.thumb_up_alt_rounded),
  ('callback', 'Baad mein', Icons.schedule_rounded),
  ('converted', 'Ho gaya', Icons.verified_rounded),
  ('promised_pay', 'Paise ka vaada', Icons.currency_rupee_rounded),
  ('not_interested', 'Interest nahi', Icons.thumb_down_alt_rounded),
  ('wrong_number', 'Galat number', Icons.block_rounded),
  ('dnd', 'Call mat karna', Icons.do_not_disturb_on_rounded),
];
const _whenChips = ['2 ghante', 'aaj shaam', 'kal subah', 'kal shaam', 'parso', 'agle hafte'];
const _purposes = {
  'sales': 'Nayi enquiry',
  'followup': 'Follow-up',
  'renewal': 'Renewal',
  'dues': 'Bakaya',
  'appointment': 'Appointment',
  'feedback': 'Feedback',
  'service': 'Service',
  'reactivate': 'Purane graahak',
};
const _sources = {
  'enquiry': 'Enquiry',
  'website': 'Website',
  'walk_in': 'Walk-in',
  'missed_call': 'Missed call',
  'whatsapp': 'WhatsApp',
  'referral': 'Referral',
  'customer': 'Purana graahak',
  'ads_form': 'Ads form',
  'bought': 'Kharidi list',
};

Color _stageCol(String s) => switch (s) {
      'interested' => C.ok,
      'callback' => C.accent,
      'converted' => C.teal,
      'lost' || 'dnd' || 'wrong' => C.faint,
      _ => C.accentSoft,
    };

class TelecallScreen extends StatefulWidget {
  const TelecallScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<TelecallScreen> createState() => _TelecallScreenState();
}

class _TelecallScreenState extends State<TelecallScreen> with WidgetsBindingObserver {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  int _tick = -1;
  Map<String, dynamic>? _pending; // the call she just placed: ask "kya hua?" when she comes back

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _tick = app.teleTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.teleTick != _tick) {
      _tick = app.teleTick;
      _load();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed && _pending != null && mounted) {
      final p = _pending!;
      _pending = null;
      Future.delayed(const Duration(milliseconds: 400), () {
        if (mounted) showTeleLog(context, app, lead: Map<String, dynamic>.from(p['lead'] as Map), callId: _s(p['call_id']), onDone: _load);
      });
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.teleAll();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _call(Map<String, dynamic> lead) async {
    try {
      final r = await app.api!.teleStart(_s(lead['id']));
      if (_s(r['warn']).isNotEmpty && mounted) {
        final go = await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(
            title: const Text('Dhyan dijiye'),
            content: Text(_s(r['warn'])),
            actions: [
              TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
              FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Phir bhi call')),
            ],
          ),
        );
        if (go != true) return;
      }
      _pending = r;
      await Native.openExternal(url: _s(r['tel']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: Text('${app.aName} · Telecaller'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Aaj'),
              Tab(text: 'Log'),
              Tab(text: 'Report'),
              Tab(text: 'Niyam'),
            ]),
          ),
          floatingActionButton: FloatingActionButton.extended(
            backgroundColor: C.accent,
            foregroundColor: C.onAccent,
            icon: const Icon(Icons.person_add_alt_1_rounded),
            label: const Text('Naya naam', style: TextStyle(fontWeight: FontWeight.w800)),
            onPressed: () => _addLead(context),
          ),
          body: Aurora(
            child: _d == null
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(children: [
                    _today(),
                    _LeadsTab(app: app, onCall: _call, onChanged: _load),
                    _ReportTab(app: app, today: Map<String, dynamic>.from(_d!['report'] as Map)),
                    _RulesTab(app: app, st: Map<String, dynamic>.from(_d!['settings'] as Map), onChanged: _load),
                  ]),
          ),
        ),
      );

  Widget _today() {
    final l = Map<String, dynamic>.from(_d!['list'] as Map);
    final now = _list(l['now']);
    final later = _list(l['later']);
    final blocked = _list(l['blocked']);
    final done = (l['done_today'] as num?) ?? 0;
    final goal = (l['goal'] as num?) ?? 40;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('Aaj $done / $goal call', style: display(18))),
              Pill('${now.length} abhi', fg: C.accent),
            ]),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(value: goal > 0 ? (done / goal).clamp(0.0, 1.0).toDouble() : 0, minHeight: 8, color: C.ok),
            ),
            if (_s(l['tip']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_s(l['tip']), style: const TextStyle(color: C.accent2))),
            const SizedBox(height: 6),
            Text('Call aap khud karti hain: Call dabane par phone ka dialer khulega. Wapas aane par ${app.aName} poochhega kya hua.',
                style: const TextStyle(color: C.faint, fontSize: 12)),
          ]),
        ),
        if (now.isEmpty)
          const Padding(padding: EdgeInsets.all(20), child: Text('Abhi kisi ko call karna baaki nahi. Naya naam jodiye ya sheet daaliye.', style: TextStyle(color: C.muted))),
        for (final x in now) Padding(padding: const EdgeInsets.only(top: 10), child: TeleLeadTile(lead: x, app: app, onCall: () => _call(x), onChanged: _load)),
        if (later.isNotEmpty) Padding(padding: const EdgeInsets.fromLTRB(4, 18, 4, 6), child: Text('Baad mein (${later.length})', style: display(15))),
        for (final x in later.take(25))
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.schedule_rounded, color: C.muted),
            title: Text(_s(x['name'])),
            subtitle: Text('${_s(x['at']).isNotEmpty ? x['at'] : _s(x['wait'])} · ${x['why']}', maxLines: 2, overflow: TextOverflow.ellipsis),
            onTap: () => openTeleLead(context, app, _s(x['id'])),
          ),
        if (blocked.isNotEmpty) ...[
          Padding(padding: const EdgeInsets.fromLTRB(4, 18, 4, 6), child: Text('Roke gaye (${blocked.length})', style: display(15))),
          Text(_s(blocked.first['risk']), style: const TextStyle(color: C.faint, fontSize: 12)),
          for (final x in blocked.take(15))
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.gpp_maybe_rounded, color: C.faint),
              title: Text(_s(x['name'])),
              subtitle: Text('${x['source']} · ${x['phone_masked']}'),
              onTap: () => openTeleLead(context, app, _s(x['id'])),
            ),
        ],
      ]),
    );
  }

  Future<void> _addLead(BuildContext context) async {
    final name = TextEditingController();
    final phone = TextEditingController();
    final need = TextEditingController();
    String source = 'enquiry';
    String purpose = 'sales';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Naya naam'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam')),
              TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Mobile')),
              TextField(controller: need, decoration: const InputDecoration(labelText: 'Kya chahiye / kis baare mein')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 4, children: [
                for (final e in _sources.entries) ChoiceChip(label: Text(e.value), selected: source == e.key, onSelected: (_) => set(() => source = e.key)),
              ]),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 4, children: [
                for (final e in _purposes.entries) ChoiceChip(label: Text(e.value), selected: purpose == e.key, onSelected: (_) => set(() => purpose = e.key)),
              ]),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    try {
      final r = await app.api!.teleAdd({'name': name.text.trim(), 'phone': phone.text.trim(), 'need': need.text.trim(), 'source': source, 'purpose': purpose});
      if (context.mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    _load();
  }
}

Future<void> openTeleLead(BuildContext context, Santosh app, String id) =>
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => TeleLeadPage(app: app, id: id)));

/// One person on the call list: why today, Call (her phone's dialer), Script, quick log.
class TeleLeadTile extends StatelessWidget {
  const TeleLeadTile({super.key, required this.lead, required this.app, required this.onCall, required this.onChanged});
  final Map<String, dynamic> lead;
  final Santosh app;
  final VoidCallback onCall;
  final Future<void> Function() onChanged;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Press(
                onTap: () => openTeleLead(context, app, _s(lead['id'])),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(lead['name']), style: display(15.5)),
                  Text([_s(lead['purpose_label']), if (_s(lead['need']).isNotEmpty) _s(lead['need']), _s(lead['phone_masked'])].join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
              ),
            ),
            if (_s(lead['interest']).isNotEmpty) Pill(_s(lead['interest']), fg: lead['interest'] == 'hot' ? C.bad : C.accent),
          ]),
          const SizedBox(height: 6),
          Text('Kyun: ${lead['why']}', style: const TextStyle(color: C.chip, fontSize: 13)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GradientButton(label: 'Call', icon: Icons.call_rounded, height: 44, onTap: onCall)),
            const SizedBox(width: 8),
            GlassButton(label: 'Script', height: 44, onTap: () => showTeleScript(context, app, lead)),
            const SizedBox(width: 8),
            GlassButton(label: 'Log', height: 44, onTap: () => showTeleLog(context, app, lead: lead, onDone: onChanged)),
          ]),
        ]),
      );
}

Future<void> showTeleScript(BuildContext context, Santosh app, Map<String, dynamic> lead) async {
  await showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: C.bgBottom,
    builder: (c) => DraggableScrollableSheet(
      expand: false,
      initialChildSize: .75,
      maxChildSize: .95,
      builder: (c, sc) => FutureBuilder<Map<String, dynamic>>(
        future: app.api!.teleScript(_s(lead['id'])),
        builder: (c, snap) {
          if (snap.hasError) return Center(child: Padding(padding: const EdgeInsets.all(20), child: Text('${snap.error}')));
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final s = Map<String, dynamic>.from(snap.data!['script'] as Map);
          Widget part(String label, String text) => text.isEmpty
              ? const SizedBox.shrink()
              : Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(label, style: const TextStyle(color: C.muted, fontSize: 12)),
                    const SizedBox(height: 2),
                    Text(text, style: const TextStyle(fontSize: 16, height: 1.4)),
                  ]),
                );
          return ListView(controller: sc, padding: const EdgeInsets.fromLTRB(20, 16, 20, 30), children: [
            Text('${lead['name']} ke liye', style: display(18)),
            const SizedBox(height: 12),
            if (_s(s['warning']).isNotEmpty) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_s(s['warning']), style: const TextStyle(color: C.bad))),
            part('1. Shuruaat', _s(s['opener'])),
            part('2. Ijazat', _s(s['permission'])),
            part('3. Poochhiye', ((s['questions'] as List?) ?? const []).join('\n')),
            part('4. Fayda', _s(s['value'])),
            if (((s['objections'] as List?) ?? const []).isNotEmpty) ...[
              const Text('Agar woh kahein', style: TextStyle(color: C.muted, fontSize: 12)),
              for (final o in _list(s['objections']))
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('"${o['if']}" → ${o['say']}', style: const TextStyle(height: 1.35)),
                ),
              const SizedBox(height: 12),
            ],
            part('5. Agla kadam', _s(s['next_step'])),
            part('6. Ant', _s(s['close'])),
            for (final n in ((s['notes'] as List?) ?? const [])) Text('• $n', style: const TextStyle(color: C.faint, fontSize: 12.5)),
          ]);
        },
      ),
    ),
  );
}

/// After the call: what happened (one tap or her words / voice note), when to call again, WhatsApp draft.
Future<void> showTeleLog(BuildContext context, Santosh app, {required Map<String, dynamic> lead, String callId = '', Future<void> Function()? onDone}) async {
  await showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: C.bgBottom,
    builder: (c) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(c).viewInsets.bottom),
      child: _LogSheet(app: app, lead: lead, callId: callId),
    ),
  );
  await onDone?.call();
}

class _LogSheet extends StatefulWidget {
  const _LogSheet({required this.app, required this.lead, required this.callId});
  final Santosh app;
  final Map<String, dynamic> lead;
  final String callId;
  @override
  State<_LogSheet> createState() => _LogSheetState();
}

class _LogSheetState extends State<_LogSheet> {
  final _notes = TextEditingController();
  final _when = TextEditingController();
  final _rec = VoiceRecorder();
  String _out = '';
  bool _busy = false;
  String? _voice;
  Timer? _t;
  Map<String, dynamic>? _done;

  @override
  void dispose() {
    _t?.cancel();
    if (_rec.recording) _rec.stop();
    super.dispose();
  }

  Future<void> _mic() async {
    if (_rec.recording) {
      _t?.cancel();
      final wav = await _rec.stop();
      setState(() => _busy = true);
      try {
        final f = await widget.app.api!.chatFile(widget.app.conversationId ?? '', 'call_note.wav', wav);
        _voice = _s(f['file_id']);
      } catch (e) {
        if (mounted) _snack(context, '$e');
      }
      if (mounted) setState(() => _busy = false);
      return;
    }
    final err = await _rec.start();
    if (err != null) {
      if (mounted) _snack(context, err);
      return;
    }
    _t = Timer.periodic(const Duration(milliseconds: 250), (_) => mounted ? setState(() {}) : null);
    setState(() {});
  }

  Future<void> _save() async {
    if (_out.isEmpty && _notes.text.trim().isEmpty && _voice == null) {
      _snack(context, 'Kya hua? Ek button dabaiye ya boliye / likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final body = {
        'outcome': _out,
        'notes': _notes.text.trim(),
        if (_voice != null && _notes.text.trim().isEmpty) 'file_id': _voice,
        'next_when': _when.text.trim(),
        'conversation_id': widget.app.conversationId ?? '',
      };
      final r = widget.callId.isNotEmpty ? await widget.app.api!.teleLogCall(widget.callId, body) : await widget.app.api!.teleLogLead(_s(widget.lead['id']), body);
      if (mounted) setState(() => _done = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final done = _done;
    if (done != null) {
      final wa = Map<String, dynamic>.from((done['whatsapp'] as Map?) ?? const {});
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Likh liya', style: display(18)),
            const SizedBox(height: 8),
            Text(_s(done['say']), style: const TextStyle(height: 1.4)),
            if (_s(wa['text']).isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(_s(wa['text']), style: const TextStyle(color: C.muted, fontSize: 13)),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: GradientButton(label: 'WhatsApp par bhejo', icon: Icons.send_rounded, height: 44, onTap: () => Native.openExternal(url: _s(wa['wa_link'])))),
                const SizedBox(width: 8),
                GlassButton(label: 'SMS', height: 44, onTap: () => Native.openExternal(url: _s(wa['sms_link']))),
              ]),
            ],
            const SizedBox(height: 10),
            Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () => Navigator.pop(context), child: const Text('Theek'))),
          ]),
        ),
      );
    }
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${widget.lead['name']}: kya hua?', style: display(18)),
          const SizedBox(height: 10),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final q in _quick)
              ChoiceChip(
                avatar: Icon(q.$3, size: 16),
                label: Text(q.$2),
                selected: _out == q.$1,
                onSelected: (_) => setState(() => _out = _out == q.$1 ? '' : q.$1),
              ),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
              child: TextField(controller: _notes, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'Kya baat hui (jaise boli waise likhiye)')),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: _busy ? null : _mic,
              style: IconButton.styleFrom(backgroundColor: _rec.recording ? C.bad : C.accent),
              icon: Icon(_rec.recording ? Icons.stop_rounded : Icons.mic_rounded, color: C.onAccent),
            ),
          ]),
          if (_rec.recording) Text('Bol rahi hain... ${_rec.length.inSeconds}s', style: const TextStyle(color: C.bad, fontSize: 12)),
          if (_voice != null && !_rec.recording) const Text('Awaaz mili', style: TextStyle(color: C.ok, fontSize: 12)),
          const SizedBox(height: 10),
          TextField(controller: _when, decoration: const InputDecoration(labelText: 'Agli call kab (jaise kal 4 baje)')),
          Wrap(spacing: 6, children: [
            for (final w in _whenChips) ActionChip(label: Text(w), onPressed: () => setState(() => _when.text = w)),
          ]),
          const SizedBox(height: 14),
          GradientButton(label: _busy ? 'Likh rahi hoon...' : 'Save', icon: Icons.check_rounded, onTap: _busy ? null : _save),
        ]),
      ),
    );
  }
}

class TeleLeadPage extends StatefulWidget {
  const TeleLeadPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<TeleLeadPage> createState() => _TeleLeadPageState();
}

class _TeleLeadPageState extends State<TeleLeadPage> {
  Map<String, dynamic>? _l;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final l = await widget.app.api!.teleLead(widget.id);
      if (mounted) setState(() => _l = l);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(Future<Map<String, dynamic>> Function() f) async {
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final l = _l;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(l == null ? '' : _s(l['name']))),
      body: Aurora(
        child: l == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
                Wrap(spacing: 8, runSpacing: 6, children: [
                  Pill(_s(l['stage']), fg: _stageCol(_s(l['stage']))),
                  Pill(_s(l['purpose_label'])),
                  Pill('Source: ${l['source']}'),
                  if (_s(l['interest']).isNotEmpty) Pill(_s(l['interest']), fg: C.accent),
                  if (_s(l['amount']).isNotEmpty) Pill(_s(l['amount']), fg: C.accent2),
                ]),
                const SizedBox(height: 10),
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${l['phone']} · ${l['calls']} call, ${l['connects']} baat', style: const TextStyle(color: C.muted)),
                    if (_s(l['need']).isNotEmpty) Text('Zaroorat: ${l['need']}'),
                    if (_s(l['next_nice']).isNotEmpty) Text('Agli call: ${l['next_nice']} (${l['next_reason']})', style: const TextStyle(color: C.accent)),
                    if (_s(l['notes']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(l['notes']), style: const TextStyle(color: C.faint, fontSize: 12.5))),
                  ]),
                ),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  if (l['callable'] == true)
                    GlassButton(
                      label: 'Script',
                      icon: Icons.article_rounded,
                      height: 42,
                      onTap: () => showTeleScript(context, widget.app, l),
                    ),
                  GlassButton(label: 'Log likho', icon: Icons.edit_note_rounded, height: 42, onTap: () => showTeleLog(context, widget.app, lead: l, onDone: _load)),
                  GlassButton(
                    label: 'Agli call',
                    icon: Icons.schedule_rounded,
                    height: 42,
                    onTap: () async {
                      final c = TextEditingController();
                      final ok = await showDialog<bool>(
                        context: context,
                        builder: (d) => AlertDialog(
                          title: const Text('Kab call karna hai?'),
                          content: TextField(controller: c, decoration: const InputDecoration(labelText: 'kal 4 baje / Friday shaam')),
                          actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Theek'))],
                        ),
                      );
                      if (ok == true && c.text.trim().isNotEmpty) await _do(() => widget.app.api!.teleUpdate(widget.id, {'next_when': c.text.trim()}));
                    },
                  ),
                  if (l['stage'] != 'dnd') GlassButton(label: 'Call mat karna', icon: Icons.do_not_disturb_on_rounded, height: 42, onTap: () => _do(() => widget.app.api!.teleDnd(widget.id))),
                  GlassButton(
                    label: 'Mita do',
                    icon: Icons.delete_outline_rounded,
                    height: 42,
                    onTap: () async {
                      final ok = await showDialog<bool>(
                        context: context,
                        builder: (d) => AlertDialog(
                          title: const Text('Saara record mitaye?'),
                          content: const Text('Naam, number, notes aur call history hamesha ke liye mit jayegi.'),
                          actions: [
                            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                            FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Mitao')),
                          ],
                        ),
                      );
                      if (ok != true) return;
                      try {
                        await widget.app.api!.teleForget(widget.id);
                        if (context.mounted) Navigator.pop(context);
                      } catch (e) {
                        if (context.mounted) _snack(context, '$e');
                      }
                    },
                  ),
                ]),
                const SizedBox(height: 14),
                Text('Calls', style: display(15)),
                for (final h in _list(l['history']))
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('${h['at']} · ${h['outcome_label']}${(h['seconds'] ?? 0) > 0 ? ' · ${((h['seconds'] as num) / 60).toStringAsFixed(1)} min' : ''}'),
                    subtitle: Text([_s(h['summary']), if (_s(h['next_nice']).isNotEmpty) 'Agli: ${h['next_nice']}'].where((x) => x.isNotEmpty).join('\n')),
                  ),
              ]),
      ),
    );
  }
}

class _LeadsTab extends StatefulWidget {
  const _LeadsTab({required this.app, required this.onCall, required this.onChanged});
  final Santosh app;
  final Future<void> Function(Map<String, dynamic>) onCall;
  final Future<void> Function() onChanged;
  @override
  State<_LeadsTab> createState() => _LeadsTabState();
}

class _LeadsTabState extends State<_LeadsTab> {
  List<Map<String, dynamic>> _rows = [];
  String _q = '';
  String _stage = 'open';
  Timer? _deb;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _deb?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.teleLeads(q: _q, stage: _stage);
      if (mounted) setState(() => _rows = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _import() async {
    final files = await pickAttachments(context, max: 1);
    if (files.isEmpty) return;
    String source = '';
    if (!mounted) return;
    source = await showDialog<String>(
          context: context,
          builder: (c) => SimpleDialog(title: const Text('Yeh log kahan se aaye?'), children: [
            for (final e in _sources.entries) SimpleDialogOption(onPressed: () => Navigator.pop(c, e.key), child: Text(e.value)),
          ]),
        ) ??
        '';
    setState(() => _busy = true);
    try {
      final f = await widget.app.api!.chatFile(widget.app.conversationId ?? '', files.first.name, files.first.bytes);
      final r = await widget.app.api!.teleImport({'file_id': f['file_id'], 'source': source});
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
    await widget.onChanged();
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
          GlassButton(label: _busy ? 'Padh rahi hoon...' : 'Excel / CSV sheet daalo', icon: Icons.upload_file_rounded, onTap: _busy ? null : _import),
          const SizedBox(height: 8),
          TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), labelText: 'Naam / number / zaroorat'),
            onChanged: (v) {
              _q = v;
              _deb?.cancel();
              _deb = Timer(const Duration(milliseconds: 350), _load);
            },
          ),
          const SizedBox(height: 6),
          Wrap(spacing: 6, children: [
            for (final s in const [('open', 'Chalu'), ('interested', 'Interested'), ('callback', 'Callback'), ('converted', 'Ho gaya'), ('lost', 'Mana'), ('dnd', 'DND')])
              ChoiceChip(
                label: Text(s.$2),
                selected: _stage == s.$1,
                onSelected: (_) {
                  setState(() => _stage = s.$1);
                  _load();
                },
              ),
          ]),
          for (final l in _rows)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(_s(l['name'])),
              subtitle: Text([_s(l['purpose_label']), if (_s(l['last_outcome_label']).isNotEmpty) _s(l['last_outcome_label']), if (_s(l['next_nice']).isNotEmpty) 'agli ${l['next_nice']}'].join(' · ')),
              trailing: l['callable'] == true
                  ? IconButton(icon: const Icon(Icons.call_rounded, color: C.ok), onPressed: () => widget.onCall(l))
                  : Pill(_s(l['stage']), fg: _stageCol(_s(l['stage']))),
              onTap: () => openTeleLead(context, widget.app, _s(l['id'])).then((_) => _load()),
            ),
        ]),
      );
}

class _ReportTab extends StatefulWidget {
  const _ReportTab({required this.app, required this.today});
  final Santosh app;
  final Map<String, dynamic> today;
  @override
  State<_ReportTab> createState() => _ReportTabState();
}

class _ReportTabState extends State<_ReportTab> {
  int _days = 1;
  Map<String, dynamic>? _r;

  @override
  void initState() {
    super.initState();
    _r = widget.today;
  }

  Future<void> _load(int d) async {
    setState(() => _days = d);
    try {
      final r = await widget.app.api!.teleReport(d);
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _r ?? const {};
    Widget stat(String label, String v, Color c) => Expanded(
          child: Glass(
            padding: const EdgeInsets.all(10),
            child: Column(children: [Text(v, style: display(20).copyWith(color: c)), Text(label, style: const TextStyle(color: C.muted, fontSize: 11.5))]),
          ),
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Wrap(spacing: 6, children: [
        for (final d in const [(1, 'Aaj'), (7, '7 din'), (30, '30 din')]) ChoiceChip(label: Text(d.$2), selected: _days == d.$1, onSelected: (_) => _load(d.$1)),
      ]),
      const SizedBox(height: 10),
      Row(children: [
        stat('Call', '${r['calls'] ?? 0}', C.chip),
        const SizedBox(width: 8),
        stat('Baat hui', '${r['connect_pct'] ?? 0}%', C.ok),
        const SizedBox(width: 8),
        stat('Min baat', '${r['talk_min'] ?? 0}', C.accent2),
      ]),
      const SizedBox(height: 8),
      Row(children: [
        stat('Interested', '${r['interested'] ?? 0}', C.accent),
        const SizedBox(width: 8),
        stat('Ho gaya', '${r['converted'] ?? 0}', C.teal),
        const SizedBox(width: 8),
        stat('Log baaki', '${r['unlogged'] ?? 0}', C.bad),
      ]),
      const SizedBox(height: 12),
      if (_list(r['missed_followups']).isNotEmpty) ...[
        Text('Chhoot gaye follow-up', style: display(15)),
        for (final m in _list(r['missed_followups']))
          ListTile(contentPadding: EdgeInsets.zero, title: Text(_s(m['name'])), subtitle: Text('${m['next_nice']} · ${m['next_reason']}'), onTap: () => openTeleLead(context, widget.app, _s(m['id']))),
      ],
      if (_list(r['best_hours']).isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Aapke records mein sabse achha samay', style: display(15)),
        for (final h in _list(r['best_hours'])) Text('${h['hour']}:00 baje · ${h['connect_pct']}% uthaate hain (${h['calls']} call)'),
      ],
      if (_list(r['objections']).isNotEmpty) ...[
        const SizedBox(height: 12),
        Text('Log kya kehte hain', style: display(15)),
        for (final o in _list(r['objections']))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('"${o['objection']}" · ${o['times']} baar · ${o['won_pct']}% phir bhi aage badhe${_s(o['worked']).isNotEmpty ? '\n  Kaam aaya: ${o['worked']}' : ''}'),
          ),
      ],
      if (_list(r['sources']).isNotEmpty) ...[
        const SizedBox(height: 12),
        Text('Kahan se aaye log', style: display(15)),
        for (final s in _list(r['sources'])) Text('${s['source']}: ${s['leads']} log, ${s['converted']} ho gaye (${s['pct']}%)'),
      ],
      if ((r['stale'] ?? 0) > 0) Padding(padding: const EdgeInsets.only(top: 12), child: Text('${r['stale']} purane band records: mita dene chahiye (DPDP).', style: const TextStyle(color: C.faint))),
    ]);
  }
}

class _RulesTab extends StatelessWidget {
  const _RulesTab({required this.app, required this.st, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> st;
  final Future<void> Function() onChanged;

  Future<void> _save(BuildContext context, Map<String, dynamic> body) async {
    try {
      await app.api!.teleSettings(body);
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
    await onChanged();
  }

  @override
  Widget build(BuildContext context) {
    Widget row(String key, String label, String value, {bool number = false, bool list = false, int lines = 1}) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(value.isEmpty ? '-' : value, maxLines: 3, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final c = TextEditingController(text: value);
            final ok = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(
                title: Text(label),
                content: TextField(controller: c, minLines: lines, maxLines: lines > 1 ? 8 : 1, keyboardType: number ? TextInputType.number : TextInputType.text),
                actions: [FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save'))],
              ),
            );
            if (ok != true || !context.mounted) return;
            final v = c.text.trim();
            await _save(context, {key: number ? int.tryParse(v) : (list ? v.split('\n').map((x) => x.trim()).where((x) => x.isNotEmpty).toList() : v)});
          },
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
      Glass(
        child: Column(children: [
          row('business', 'Business ka naam', _s(st['business'])),
          row('caller_name', 'Call karne wale ka naam', _s(st['caller_name'])),
          row('pitch', 'Hum kya dete hain (script ke liye)', _s(st['pitch']), lines: 4),
          row('start_hour', 'Call shuru (9 se pehle nahi)', _s(st['start_hour'])),
          row('end_hour', 'Call band (9 baje raat ke baad nahi)', _s(st['end_hour'])),
          row('daily_goal', 'Roz kitni call', '${st['daily_goal']}', number: true),
          row('max_attempts', 'Ek vyakti ko kitni baar try', '${st['max_attempts']}', number: true),
          row('morning_time', 'Subah ki list kab', _s(st['morning_time'])),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: st['registered'] == true,
            title: const Text('TRAI registered 140 line se call'),
            subtitle: const Text('Band = kharidi / cold list waale log roke jayenge'),
            onChanged: (v) => _save(context, {'registered': v}),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: st['record_calls'] == true,
            title: const Text('Main phone par call record karti hoon'),
            subtitle: const Text('Script mein "call record ho sakti hai" bolna jud jayega'),
            onChanged: (v) => _save(context, {'record_calls': v}),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Glass(
        child: Column(children: [
          row('rules', 'Mere niyam (har line ek)', ((st['rules'] as List?) ?? const []).join('\n'), list: true, lines: 5),
          row('dont_say', 'Yeh kabhi na bolein (har line ek)', ((st['dont_say'] as List?) ?? const []).join('\n'), list: true, lines: 5),
        ]),
      ),
      const SizedBox(height: 10),
      const Text('Hoola khud kabhi call nahi karta aur message nahi bhejta: dialer aur WhatsApp aapke tap se khulte hain.',
          style: TextStyle(color: C.faint, fontSize: 12)),
    ]);
  }
}

// ---------------------------------------------------------------- chat cards
class TeleDayCard extends StatelessWidget {
  const TeleDayCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.headset_mic_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('Aaj ki call list', style: display(16))),
            Pill('${v['count'] ?? 0} log', fg: C.accent),
          ]),
          const SizedBox(height: 8),
          Text(_s(v['text']), style: const TextStyle(color: C.chip, height: 1.4)),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelecallScreen(app: app))),
              child: const Text('Call list kholo'),
            ),
          ),
        ]),
      );
}

class TeleLoggedCard extends StatelessWidget {
  const TeleLoggedCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final lead = Map<String, dynamic>.from((v['lead'] as Map?) ?? const {});
    final call = Map<String, dynamic>.from((v['call'] as Map?) ?? const {});
    final wa = Map<String, dynamic>.from((v['whatsapp'] as Map?) ?? const {});
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.edit_note_rounded, color: C.ok, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${lead['name']}: ${call['outcome_label']}', style: display(15))),
        ]),
        if (_s(call['summary']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_s(call['summary']), style: const TextStyle(color: C.chip))),
        if (_s(lead['next_nice']).isNotEmpty) Text('Agli call: ${lead['next_nice']}', style: const TextStyle(color: C.accent, fontSize: 12.5)),
        if (_s(v['ask']).isNotEmpty) Text(_s(v['ask']), style: const TextStyle(color: C.accent2, fontSize: 12.5)),
        if (_s(wa['wa_link']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GlassButton(label: 'WhatsApp draft kholo', icon: Icons.send_rounded, height: 40, onTap: () => Native.openExternal(url: _s(wa['wa_link']))),
          ),
      ]),
    );
  }
}
