import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// The event Santosh added / changed / cancelled, or a "meeting in 10 minutes" nudge, shown in the chat.
class CalendarEventCard extends StatelessWidget {
  const CalendarEventCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'added';
    final (chip, fg) = switch (status) {
      'added' => ('CALENDAR MEIN', C.ok),
      'updated' => ('BADAL DIYA', C.ok),
      'cancelled' => ('CANCEL', C.muted),
      'declined' => ('MANA KIYA', C.muted),
      'accepted' => ('HAAN KAHA', C.ok),
      'tentative' => ('SHAYAD', C.warn),
      'soon' => ('JALDI SHURU', C.warn),
      _ => (status.toUpperCase(), C.chip),
    };
    final title = v['title'] as String? ?? '';
    final start = v['start'] as String? ?? '';
    final end = v['end'] as String? ?? '';
    final loc = v['location'] as String? ?? '';
    final meet = v['meet_link'] as String? ?? '';
    final link = v['link'] as String? ?? '';
    final people = (v['attendees'] as List? ?? const []).map((e) => (e as Map)['email']?.toString() ?? '').where((e) => e.isNotEmpty).toList();
    final gone = status == 'cancelled' || status == 'declined';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.event_rounded, color: C.teal, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(title, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5,
                decoration: gone ? TextDecoration.lineThrough : null))),
            Pill(chip, fg: fg),
          ]),
          const SizedBox(height: 6),
          if (start.isNotEmpty)
            Text(end.isNotEmpty && v['all_day'] != true ? '$start – ${end.split(', ').last}' : start,
                style: const TextStyle(color: C.chip, fontSize: 13.5)),
          if (loc.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 2), child: Text('📍 $loc', style: const TextStyle(color: C.muted, fontSize: 13))),
          if (people.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 2), child: Text('👥 ${people.join(', ')}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
          if (!gone && (meet.isNotEmpty || link.isNotEmpty)) ...[
            const SizedBox(height: 10),
            Row(children: [
              if (meet.isNotEmpty)
                Expanded(child: GradientButton(label: 'Meet join karein', icon: Icons.videocam_rounded, height: 42, onTap: () => _open(meet))),
              if (meet.isNotEmpty && link.isNotEmpty) const SizedBox(width: 8),
              if (link.isNotEmpty)
                Expanded(child: GlassButton(label: 'Calendar mein dekhein', icon: Icons.open_in_new_rounded, height: 42, onTap: () => _open(link))),
            ]),
          ],
        ]),
      ),
    );
  }
}

/// Profile > Calendar: connect Google Calendar, choose which calendars Santosh reads, where new events go,
/// and how early Santosh reminds you before a meeting.
class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  Map<String, dynamic> _st = {};
  bool _loaded = false;
  String? _err;
  int _seenTick = 0;

  Santosh get app => widget.app;
  List<Map<String, dynamic>> _list(String k) =>
      List<Map<String, dynamic>>.from((_st[k] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    _seenTick = app.calendarLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.calendarLinkedTick != _seenTick) {
      _seenTick = app.calendarLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.calendarState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = r['error'] as String?; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _do(Future<Map<String, dynamic>> Function() f) async {
    try {
      final r = await f();
      if (mounted) setState(() { _st = r; _err = r['error'] as String?; });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _link() async {
    try {
      await _open(await app.api!.calendarLinkUrl());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final accounts = _list('accounts');
    final cals = _list('calendars');
    final canLink = _st['can_link'] == true;
    final alert = ((_st['prefs'] as Map?)?['alert_minutes'] as num?)?.toInt() ?? 10;
    final reading = cals.where((c) => c['reading'] == true).map((c) => c['ref'] as String).toList();
    final onlyOld = accounts.isNotEmpty && accounts.every((a) => a['full'] != true);
    return Scaffold(
      appBar: AppBar(title: const Text('Calendar'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Hoola aapka Google Calendar dekhta hai, meeting banata hai (Google Meet link ke saath), samay badalta hai, '
                'khaali samay dhoondhta hai aur meeting se pehle yaad dilata hai. Doosre logon ko invite / badlav / cancel '
                'hamesha aapke tap ke baad hi.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Row(children: [
                  const Icon(Icons.event_available_rounded, color: C.teal),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(a['full'] == true ? 'Google Calendar' : 'Purana connection (app password): sirf dekhna, banana, hatana',
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (a['status'] == 'error') Text(a['error'] as String? ?? 'Login fail', style: const TextStyle(color: C.bad, fontSize: 12)),
                  ])),
                  if (a['removable'] == true)
                    IconButton(tooltip: 'Hataiye', icon: const Icon(Icons.close_rounded, color: C.muted),
                        onPressed: () => _do(() => app.api!.calendarRemove(a['key'] as String))),
                ])),
              ),
            if (_loaded && (accounts.isEmpty || onlyOld)) ...[
              GradientButton(label: 'Google Calendar jodiye', icon: Icons.event_rounded, height: 50, onTap: canLink ? _link : null),
              if (!canLink)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text('Is server par Google sign-in abhi chalu nahi hai (GOOGLE_OAUTH_CLIENT_ID / SECRET).',
                      style: TextStyle(color: C.faint, fontSize: 12)),
                ),
              const SizedBox(height: 14),
            ] else if (_loaded)
              Padding(padding: const EdgeInsets.only(bottom: 14),
                  child: GlassButton(label: 'Doosra Google account jodiye', icon: Icons.add_rounded, height: 44, onTap: canLink ? _link : null)),
            if (cals.isNotEmpty) ...[
              const Text('Hoola kaunse calendar dekhe', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Glass(child: Column(children: [
                for (final c in cals)
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(c['name'] as String? ?? ''),
                    subtitle: Text([
                      if (c['primary'] == true) 'main',
                      if (c['default'] == true) 'naye event yahan',
                      if (c['role'] == 'reader') 'sirf padhna',
                    ].join(' · '), style: const TextStyle(color: C.muted, fontSize: 12)),
                    value: c['reading'] == true,
                    onChanged: (on) {
                      final next = [...reading.where((r) => r != c['ref']), if (on) c['ref'] as String];
                      _do(() => app.api!.calendarPrefs(read: next));
                    },
                  ),
              ])),
              const SizedBox(height: 14),
              const Text('Naye event kis calendar mein', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final c in cals.where((c) => c['role'] != 'reader' && c['role'] != 'freeBusyReader'))
                  ChoiceChip(
                    label: Text(c['name'] as String? ?? ''),
                    selected: c['default'] == true,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: c['default'] == true ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                    onSelected: (_) => _do(() => app.api!.calendarPrefs(defaultCalendar: c['ref'] as String)),
                  ),
              ]),
              const SizedBox(height: 14),
            ],
            if (accounts.isNotEmpty) ...[
              const Text('Meeting se pehle yaad dilaye', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final m in const [0, 5, 10, 15, 30])
                  ChoiceChip(
                    label: Text(m == 0 ? 'Band' : '$m min'),
                    selected: alert == m,
                    showCheckmark: false,
                    selectedColor: C.accent,
                    labelStyle: TextStyle(color: alert == m ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
                    onSelected: (_) => _do(() => app.api!.calendarPrefs(alertMinutes: m)),
                  ),
              ]),
            ],
            const SizedBox(height: 18),
            const Text('Bolkar dekhiye', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"Kal mera schedule kya hai?"',
              '"Is hafte 1 ghante ka free slot batao"',
              '"Friday 4 baje Swati ke saath sales review, Meet link ke saath"',
              '"Dentist wali appointment 11 baje kar do"',
              '"Har Monday 10 baje team standup daal do"',
              '"BSNL meeting ka invite accept kar do"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
      ),
    );
  }
}
