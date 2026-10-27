/// Profile > Phone Doctor (v0.90): "phone mein kya dikkat hai?" -> fixed.
/// The phone checks itself (battery heat / health, storage, RAM, network, SIM, DND, volumes, date-time...), Hoola names
/// what it sees, then one fix at a time with a "Kholo" button that opens the exact settings screen, "theek hua?" after
/// each, and when the steps run out: the repair shop / service centre near her, the operator, or official help (CEIR,
/// 1930). Steps that erase data wait for her clear haan. Hoola never bypasses a lock or changes an IMEI.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _icons = <String, IconData>{
  'slow': Icons.hourglass_bottom_rounded,
  'battery_drain': Icons.battery_alert_rounded,
  'heating': Icons.local_fire_department_rounded,
  'not_charging': Icons.power_off_rounded,
  'no_network': Icons.signal_cellular_off_rounded,
  'mobile_data': Icons.mobiledata_off_rounded,
  'wifi': Icons.wifi_off_rounded,
  'calls_not_ringing': Icons.notifications_off_rounded,
  'sound_mic': Icons.volume_off_rounded,
  'notifications_late': Icons.schedule_rounded,
  'app_crash': Icons.apps_outage_rounded,
  'storage_full': Icons.sd_card_alert_rounded,
  'touch': Icons.touch_app_rounded,
  'screen_broken': Icons.broken_image_rounded,
  'water': Icons.water_drop_rounded,
  'wont_turn_on': Icons.power_settings_new_rounded,
  'otp_not_coming': Icons.sms_failed_rounded,
  'bluetooth': Icons.bluetooth_disabled_rounded,
  'camera': Icons.no_photography_rounded,
  'lost_stolen': Icons.phonelink_erase_rounded,
  'forgot_lock': Icons.lock_reset_rounded,
  'hacked_fraud': Icons.gpp_bad_rounded,
  'gps': Icons.location_off_rounded,
  'other': Icons.help_outline_rounded,
};

Color _lvl(String l) => switch (l) { 'bad' => C.bad, 'warn' => C.warn, _ => C.muted };

Color _stCol(String s) => switch (s) { 'resolved' => C.ok, 'escalated' => C.warn, 'closed' => C.faint, _ => C.accentSoft };

class PhoneDocScreen extends StatefulWidget {
  const PhoneDocScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PhoneDocScreen> createState() => _PhoneDocScreenState();
}

class _PhoneDocScreenState extends State<PhoneDocScreen> {
  final _text = TextEditingController();
  List<Map<String, dynamic>> _issues = [];
  List<Map<String, dynamic>> _cases = [];
  Map<String, dynamic> _check = {};
  bool _checking = false, _busy = false;
  String _forWhom = '';
  int _tick = -1;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _tick = app.phonedocTick;
    app.addListener(_onApp);
    _load();
    _runCheck();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _text.dispose();
    super.dispose();
  }

  void _onApp() {
    if (app.phonedocTick != _tick) {
      _tick = app.phonedocTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final i = _issues.isEmpty ? await app.api!.phonedocIssues() : _issues;
      final c = await app.api!.phonedocCases();
      if (mounted) setState(() {
        _issues = i;
        _cases = c;
      });
    } catch (_) {}
  }

  Future<void> _runCheck() async {
    setState(() => _checking = true);
    final r = await app.sendPhoneCheck();
    if (mounted) setState(() {
      _check = r;
      _checking = false;
    });
  }

  Future<void> _start({String issue = ''}) async {
    final t = _text.text.trim();
    if (t.isEmpty && issue.isEmpty) {
      _snack(context, 'Dikkat chuniye ya apne shabdon mein likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final own = _forWhom.trim().isEmpty;
      final snap = own ? await Native.phoneCheck() : <String, dynamic>{};
      final r = await app.api!.phonedocStart({
        'text': t,
        'issue': issue,
        'for_whom': _forWhom.trim(),
        if (snap.isNotEmpty) 'snapshot': snap,
      });
      if (!mounted) return;
      if (r['started'] == false) {
        _snack(context, _s(r['say']));
      } else {
        _text.clear();
        final id = _s((r['case'] as Map?)?['id']);
        await Navigator.of(context).push(MaterialPageRoute(builder: (_) => PhoneDocCasePage(app: app, id: id)));
        _load();
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _checkCard() {
    final snap = Map<String, dynamic>.from((_check['snapshot'] as Map?) ?? const {});
    final f = _list(_check['findings']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.health_and_safety_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Phone ki jaanch', style: display(16))),
          if (_checking)
            const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
          else
            IconButton(onPressed: _runCheck, icon: const Icon(Icons.refresh_rounded, color: C.muted), tooltip: 'Phir jaancho'),
        ]),
        if (snap.isEmpty && !_checking)
          const Text('Jaanch nahi ho payi (yeh sirf Android phone par chalti hai).', style: TextStyle(color: C.muted)),
        if (snap.isNotEmpty) ...[
          Wrap(spacing: 6, runSpacing: 6, children: [
            if (snap['battery_pct'] != null) Pill('Battery ${snap['battery_pct']}%'),
            if (snap['battery_temp_c'] is num) Pill('${(snap['battery_temp_c'] as num).round()}°C'),
            if (snap['storage_used_pct'] is num) Pill('Storage ${(snap['storage_used_pct'] as num).round()}%'),
            if (_s(snap['operator']).isNotEmpty) Pill('${snap['operator']} ${snap['signal_level'] ?? '-'}/4'),
            if (_s(snap['on']).isNotEmpty) Pill('Net: ${snap['on']}'),
          ]),
          const SizedBox(height: 8),
          if (f.isEmpty) const Text('Sab theek dikh raha hai.', style: TextStyle(color: C.ok)),
          for (final x in f.take(6))
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.circle, size: 9, color: _lvl(_s(x['level']))),
                const SizedBox(width: 8),
                Expanded(child: Text(_s(x['text']), style: const TextStyle(color: C.chip, fontSize: 13))),
              ]),
            ),
        ],
      ]),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Phone Doctor')),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            _checkCard(),
            const SizedBox(height: 14),
            Glass(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Kya dikkat hai?', style: display(16)),
                const SizedBox(height: 8),
                TextField(
                  controller: _text,
                  minLines: 1,
                  maxLines: 3,
                  decoration: const InputDecoration(hintText: 'Jaise: phone bahut garam hota hai, OTP nahi aata...'),
                ),
                const SizedBox(height: 8),
                TextField(
                  onChanged: (v) => _forWhom = v,
                  decoration: const InputDecoration(hintText: 'Kiska phone? (khaali = mera hi)', isDense: true),
                ),
                const SizedBox(height: 10),
                GradientButton(label: _busy ? 'Ruko...' : 'Ilaaj shuru karo', icon: Icons.build_rounded, onTap: _busy ? null : _start),
                const SizedBox(height: 12),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final i in _issues)
                    ActionChip(
                      avatar: Icon(_icons[_s(i['id'])] ?? Icons.help_outline_rounded, size: 18, color: C.accent),
                      label: Text(_s(i['label'])),
                      onPressed: _busy ? null : () => _start(issue: _s(i['id'])),
                    ),
                ]),
              ]),
            ),
            if (_cases.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('Pichhle case', style: display(15)),
              const SizedBox(height: 8),
              for (final c in _cases)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Press(
                    onTap: () async {
                      await Navigator.of(context)
                          .push(MaterialPageRoute(builder: (_) => PhoneDocCasePage(app: app, id: _s(c['id']))));
                      _load();
                    },
                    child: Glass(
                      child: Row(children: [
                        Icon(_icons[_s(c['issue'])] ?? Icons.help_outline_rounded, color: C.accent),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(_s(c['label']), style: const TextStyle(fontWeight: FontWeight.w800)),
                            Text(
                                [if (_s(c['for_whom']).isNotEmpty) _s(c['for_whom']), if (_s(c['device']).isNotEmpty) _s(c['device'])]
                                    .join(' · '),
                                style: const TextStyle(color: C.muted, fontSize: 12.5)),
                          ]),
                        ),
                        Pill(_s(c['status_label']), fg: _stCol(_s(c['status'])), bg: _stCol(_s(c['status'])).withOpacity(.16)),
                      ]),
                    ),
                  ),
                ),
            ],
          ]),
        ),
      );
}

class PhoneDocCasePage extends StatelessWidget {
  const PhoneDocCasePage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Phone ka ilaaj')),
        body: Aurora(
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [PhoneDocCaseView(app: app, id: id)]),
        ),
      );
}

/// Chat card for a Phone Doctor case (event `phonedoc_case`).
class PhoneDocCard extends StatelessWidget {
  const PhoneDocCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => PhoneDocCaseView(app: app, id: _s(v['case']), compact: true);
}

class PhoneDocCaseView extends StatefulWidget {
  const PhoneDocCaseView({super.key, required this.app, required this.id, this.compact = false});
  final Santosh app;
  final String id;
  final bool compact;
  @override
  State<PhoneDocCaseView> createState() => _PhoneDocCaseViewState();
}

class _PhoneDocCaseViewState extends State<PhoneDocCaseView> {
  Map<String, dynamic>? _c;
  String? _err;
  bool _busy = false;
  int _tick = -1;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _tick = app.phonedocTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.phonedocTick != _tick) {
      _tick = app.phonedocTick;
      _load();
    }
  }

  Future<void> _load() async {
    if (widget.id.isEmpty) return;
    try {
      final c = await app.api!.phonedocCase(widget.id);
      if (mounted) setState(() {
        _c = c;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _act(String action, [Map<String, dynamic> body = const {}]) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.phonedocAct(widget.id, action, body);
      final c = r['case'];
      if (c is Map && mounted) setState(() => _c = Map<String, dynamic>.from(c));
      if (mounted && _s(r['say']).isNotEmpty && action != 'step') _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _result(Map<String, dynamic> st, String result) async {
    if (result == 'fixed' && st['careful'] == true) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Pakka?'),
          content: const Text('Is step mein data / settings mit sakti hain. Backup ho gaya?'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Ruko')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, ho gaya')),
          ],
        ),
      );
      if (ok != true) return;
    }
    await _act('step', {'step_id': _s(st['id']), 'result': result});
    final c = _c;
    if (c != null && _s(c['status']) == 'open' && _s(c['for_whom']).isEmpty) {
      final cur = Map<String, dynamic>.from((c['current'] as Map?) ?? const {});
      if (_s(cur['setting']).isNotEmpty) await app.openPhoneScreen(_s(cur['setting']), package: _s(cur['pkg']));
    }
  }

  Future<void> _recheck() async {
    setState(() => _busy = true);
    final snap = await Native.phoneCheck();
    try {
      final r = await app.api!.phonedocAct(widget.id, 'recheck', {if (snap.isNotEmpty) 'snapshot': snap});
      if (r['case'] is Map && mounted) setState(() => _c = Map<String, dynamic>.from(r['case'] as Map));
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _stepCard(Map<String, dynamic> st, int n, int total, bool own) {
    final hasScreen = _s(st['setting']).isNotEmpty || _s(st['url']).isNotEmpty;
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: st['careful'] == true ? C.bad : C.accent.withOpacity(.5))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Pill('Step $n/$total', fg: C.accent, bg: C.accent.withOpacity(.14)),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(st['title']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
        ]),
        const SizedBox(height: 6),
        Text(_s(st['how']), style: const TextStyle(color: C.ink, height: 1.35)),
        if (st['matched'] == true)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Phone check mein yahi wajah dikhi.', style: TextStyle(color: C.warn, fontSize: 12.5)),
          ),
        if (st['careful'] == true)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Isme data mit sakta hai: pehle backup, phir aapki haan.', style: TextStyle(color: C.bad, fontSize: 12.5)),
          ),
        const SizedBox(height: 10),
        if (hasScreen && (own || _s(st['url']).isNotEmpty))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: GlassButton(
              label: _s(st['setting_label']).isNotEmpty ? 'Kholo: ${st['setting_label']}' : 'Kholo',
              icon: Icons.open_in_new_rounded,
              color: C.accent,
              onTap: () => app.openPhoneScreen(_s(st['setting']), package: _s(st['pkg']), url: _s(st['url'])),
            ),
          ),
        Row(children: [
          Expanded(
            child: GlassButton(
                label: 'Theek hua', icon: Icons.check_rounded, color: C.ok, onTap: _busy ? null : () => _result(st, 'fixed')),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: GlassButton(
                label: 'Nahi hua', icon: Icons.close_rounded, color: C.bad, onTap: _busy ? null : () => _result(st, 'not_fixed')),
          ),
        ]),
        Row(children: [
          TextButton(onPressed: _busy ? null : () => _result(st, 'skipped'), child: const Text('Chhodo, agla')),
          const Spacer(),
          if (own) TextButton.icon(onPressed: _busy ? null : _recheck, icon: const Icon(Icons.refresh_rounded, size: 18), label: const Text('Phone phir jaancho')),
        ]),
      ]),
    );
  }

  Widget _escalation(Map<String, dynamic> c) {
    final e = Map<String, dynamic>.from((c['escalation'] as Map?) ?? const {});
    final links = _list(e['links']);
    final notes = List<String>.from(((e['notes'] as List?) ?? const []).map((x) => '$x'));
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(16), border: Border.all(color: C.warn.withOpacity(.6))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(
            switch (_s(e['kind'])) {
              'official' => 'Sarkari / zaroori madad',
              'operator' => 'Operator se baat',
              _ => 'Dukaan / service centre',
            },
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        for (final n in notes)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('•  ', style: TextStyle(color: C.warn)),
              Expanded(child: Text(n, style: const TextStyle(color: C.chip, height: 1.3))),
            ]),
          ),
        if (n1930(notes))
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GlassButton(label: '1930 par call', icon: Icons.call_rounded, color: C.bad,
                onTap: () => Native.openExternal(url: 'tel:1930')),
          ),
        for (final l in links)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GlassButton(label: _s(l['label']), icon: Icons.open_in_new_rounded, color: C.accent,
                onTap: () => Native.openExternal(url: _s(l['url']))),
          ),
        if (_s(e['tell']).isNotEmpty) ...[
          const SizedBox(height: 10),
          const Text('Dukaan ko yeh bataiye:', style: TextStyle(color: C.muted, fontSize: 12.5)),
          Row(children: [
            Expanded(child: Text(_s(e['tell']), style: const TextStyle(color: C.ink))),
            IconButton(
              icon: const Icon(Icons.copy_rounded, size: 18, color: C.muted),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: _s(e['tell'])));
                _snack(context, 'Copy ho gaya');
              },
            ),
          ]),
        ],
        if (_s(e['kind']) == 'repair' && _s(c['for_whom']).isNotEmpty && _s(c['mshop_job']).isEmpty)
          TextButton.icon(
            onPressed: _busy ? null : () => _act('escalate', {'kind': 'repair', 'make_job': true}),
            icon: const Icon(Icons.add_task_rounded, size: 18),
            label: const Text('Meri dukaan mein repair job banao'),
          ),
      ]),
    );
  }

  bool n1930(List<String> notes) => notes.any((n) => n.contains('1930'));

  @override
  Widget build(BuildContext context) {
    final c = _c;
    if (c == null) {
      return Glass(
        child: _err != null
            ? Text(_err!, style: const TextStyle(color: C.muted))
            : const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator(strokeWidth: 2))),
      );
    }
    final st = _s(c['status']);
    final own = _s(c['for_whom']).isEmpty;
    final f = _list(c['findings']);
    final cur = c['current'] is Map ? Map<String, dynamic>.from(c['current'] as Map) : null;
    final done = _list(c['steps']).where((x) => x['result'] != null).toList();
    return Glass(
      border: st == 'open' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_icons[_s(c['issue'])] ?? Icons.healing_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Phone Doctor: ${_s(c['label'])}', style: display(15.5))),
          Pill(_s(c['status_label']), fg: _stCol(st), bg: _stCol(st).withOpacity(.16)),
        ]),
        if (_s(c['device']).isNotEmpty || !own)
          Text([if (!own) _s(c['for_whom']), _s(c['device'])].where((x) => x.isNotEmpty).join(' · '),
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
        for (final x in f.take(widget.compact ? 3 : 8))
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.circle, size: 9, color: _lvl(_s(x['level']))),
              const SizedBox(width: 8),
              Expanded(child: Text(_s(x['text']), style: const TextStyle(color: C.chip, fontSize: 13))),
            ]),
          ),
        if (st == 'open' && cur != null) _stepCard(cur, (c['step_no'] as num?)?.toInt() ?? 1, (c['total'] as num?)?.toInt() ?? 1, own),
        if (st == 'resolved')
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Row(children: [
              const Icon(Icons.verified_rounded, color: C.ok),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                    'Theek ho gaya${done.isNotEmpty ? ': ${_s(done.last['title'])}' : ''}. Yeh tareeka agli baar pehle aayega.',
                    style: const TextStyle(color: C.ok)),
              ),
            ]),
          ),
        if (st == 'escalated') _escalation(c),
        if (!widget.compact && done.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text('Kiya gaya', style: TextStyle(color: C.muted, fontWeight: FontWeight.w700)),
          for (final d in done)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(children: [
                Icon(
                    switch (_s(d['result'])) {
                      'fixed' => Icons.check_circle_rounded,
                      'skipped' => Icons.skip_next_rounded,
                      _ => Icons.cancel_rounded,
                    },
                    size: 16,
                    color: _s(d['result']) == 'fixed' ? C.ok : C.faint),
                const SizedBox(width: 6),
                Expanded(child: Text(_s(d['title']), style: const TextStyle(color: C.chip, fontSize: 13))),
              ]),
            ),
        ],
        if (!widget.compact && st == 'open')
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: _busy ? null : () => _act('escalate'),
              child: const Text('Seedha dukaan / madad dikhao'),
            ),
          ),
      ]),
    );
  }
}
