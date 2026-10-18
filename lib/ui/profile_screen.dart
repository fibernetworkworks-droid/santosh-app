import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'bazar_screen.dart';
import 'glass.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, required this.app, required this.onReset});
  final Santosh app;
  final VoidCallback onReset;
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _name = TextEditingController();
  final _city = TextEditingController();
  String? _briefing;
  List<Map<String, dynamic>> _facts = [];
  bool _loading = true;

  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    widget.app.addListener(_maybeLoad);
    _maybeLoad();
  }

  @override
  void dispose() {
    widget.app.removeListener(_maybeLoad);
    super.dispose();
  }

  void _maybeLoad() {
    if (!_loaded && widget.app.connected && widget.app.api != null) {
      _loaded = true;
      _load();
    }
  }

  Future<void> _load() async {
    final api = widget.app.api;
    if (api == null) return;
    try {
      final p = await api.profile();
      _name.text = p['name'] as String? ?? '';
      _city.text = p['city'] as String? ?? '';
      _briefing = p['briefing_time'] as String?;
      _facts = await api.memory();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save() async {
    try {
      await widget.app.api!.saveProfile({
        'name': _name.text.trim(),
        'city': _city.text.trim(),
        'language': languages[widget.app.language],
        'briefing_time': _briefing ?? 'off',
        'conversation_id': widget.app.conversationId,
      });
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Save ho gaya')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save nahi hua: $e')));
    }
  }

  Future<void> _pickBriefing() async {
    final parts = (_briefing ?? '07:30').split(':');
    final t = await showTimePicker(context: context, initialTime: TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1])));
    if (t != null) setState(() => _briefing = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}');
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    if (_loading) {
      return Center(child: Text(app.connected ? 'Load ho raha hai…' : 'Server se connect ho raha hai…', style: const TextStyle(color: C.muted)));
    }
    return ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
      Text('Profile', style: display(28)),
      const SizedBox(height: 14),
      ListenableBuilder(listenable: app, builder: (context, _) => _BackgroundCard(app: app)),
      const SizedBox(height: 18),
      ListenableBuilder(listenable: app, builder: (context, _) => app.account != null ? _AccountCard(app: app) : const SizedBox.shrink()),
      if (app.account != null) const SizedBox(height: 18),
      Glass(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.storefront_rounded, color: C.accent),
          title: const Text('Santosh Bazar · 159 apps', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Bill, kirana, UPI, cab, Swiggy/Zomato · kharch ki seema'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => BazarScreen(app: app))),
        ),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(children: [
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'Naam')),
          TextField(controller: _city, decoration: const InputDecoration(labelText: 'Shehar (mausam ke liye)')),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Roz subah ki briefing'),
            subtitle: Text(_briefing == null ? 'Band' : 'Har din $_briefing baje: mausam, reminders, lists'),
            value: _briefing != null,
            onChanged: (on) => on ? _pickBriefing() : setState(() => _briefing = null),
          ),
          if (_briefing != null) Align(alignment: Alignment.centerLeft, child: TextButton(onPressed: _pickBriefing, child: const Text('Samay badlein'))),
          const SizedBox(height: 6),
          GradientButton(label: 'Save', height: 48, onTap: _save),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Bhasha aur awaaz', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final e in languages.entries)
              ChoiceChip(
                label: Text(e.value),
                selected: app.language == e.key,
                showCheckmark: false,
                selectedColor: C.accent,
                labelStyle: TextStyle(color: app.language == e.key ? Colors.white : C.chip, fontWeight: FontWeight.w600),
                onSelected: (_) async {
                  await app.saveSettings(lang: e.key);
                  setState(() {});
                },
              ),
          ]),
          if (app.realtimeVoice && app.voices.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text('Santosh ki awaaz (Baat tab)', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final v in app.voices)
                ChoiceChip(
                  label: Text('${v['id']} · ${v['style']}'),
                  selected: app.voiceName == v['id'],
                  showCheckmark: false,
                  selectedColor: C.accent,
                  labelStyle: TextStyle(color: app.voiceName == v['id'] ? Colors.white : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
                  onSelected: (_) async {
                    await app.setVoice(v['id'] as String);
                    setState(() {});
                  },
                ),
            ]),
          ],
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Bolkar poochhun to Santosh bolkar jawab de'),
            value: app.speakReplies,
            onChanged: (v) async {
              await app.saveSettings(speak: v);
              setState(() {});
            },
          ),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Santosh ko yaad hai', style: TextStyle(fontWeight: FontWeight.w700)),
          if (_facts.isEmpty) const Padding(padding: EdgeInsets.only(top: 6), child: Text('Abhi kuch nahi. Boliye: "Yaad rakhna, mummy ka birthday 5 June hai".', style: TextStyle(color: C.muted))),
          for (final f in _facts)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(f['text'] as String? ?? ''),
              trailing: IconButton(
                tooltip: 'Bhool jao',
                icon: const Icon(Icons.delete_outline, color: C.muted),
                onPressed: () async {
                  await app.api!.forget((f['id'] as num).toInt());
                  _facts = await app.api!.memory();
                  setState(() {});
                },
              ),
            ),
        ]),
      ),
      const SizedBox(height: 18),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Server', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(app.serverUrl, style: const TextStyle(color: C.muted)),
          Text(app.dryRun ? 'WhatsApp: test mode' : 'WhatsApp: live', style: const TextStyle(color: C.muted)),
          TextButton(onPressed: widget.onReset, child: const Text('Server badlein')),
        ]),
      ),
    ]);
  }
}


/// Background mode: Santosh keeps working (notifications, alarms, calendar, automatic jobs) with the app closed.
class _BackgroundCard extends StatefulWidget {
  const _BackgroundCard({required this.app});
  final Santosh app;
  @override
  State<_BackgroundCard> createState() => _BackgroundCardState();
}

class _BackgroundCardState extends State<_BackgroundCard> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.app.refreshBackgroundInfo();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) widget.app.refreshBackgroundInfo(); // back from a settings screen
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final on = app.background;
    final st = app.backgroundStatus;
    final statusText = !on
        ? 'Band: app band hone par notifications aur phone ke kaam ruk jaate hain'
        : !app.backgroundRunning
            ? 'Shuru ho raha hai…'
            : st == 'connected'
                ? 'Chalu · Santosh duty par hai'
                : st.isEmpty
                    ? 'Chalu'
                    : 'Chalu · $st';
    Widget fix(String title, String sub, String button, Future<void> Function() onTap) => Container(
          margin: const EdgeInsets.only(top: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xE6FEF3C7), borderRadius: BorderRadius.circular(16)),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF7C2D12))),
                Text(sub, style: const TextStyle(fontSize: 12.5, color: Color(0xFF7C2D12))),
              ]),
            ),
            TextButton(onPressed: onTap, child: Text(button)),
          ]),
        );
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Background mein kaam', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(statusText, style: TextStyle(color: on && app.backgroundRunning ? C.ok : C.muted, fontSize: 12.5)),
          value: on,
          onChanged: (v) => app.setBackground(v),
        ),
        const Text('App band ho tab bhi: Santosh ke jawab notification mein, alarm aur timer bajenge, calendar mein entry, aur Santosh ke roz ke kaam chalte rahenge.',
            style: TextStyle(fontSize: 12.5, color: C.muted)),
        if (on && app.batteryOptimized)
          fix('Battery saver Santosh ko rok sakta hai', 'Santosh ko "Unrestricted / Don\'t optimize" par rakhiye', 'Theek karo', Native.askBattery),
        if (on && !app.hasCalendar)
          fix('Calendar permission', 'Taaki Santosh meetings seedha calendar mein save kare', 'Allow', () async {
            await Native.askCalendar();
            await Future.delayed(const Duration(seconds: 2));
            await app.refreshBackgroundInfo();
          }),
      ]),
    );
  }
}


/// Shows the signed-in Google account and connected services (product mode).
class _AccountCard extends StatelessWidget {
  const _AccountCard({required this.app});
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final acc = app.account!;
    final conns = List<Map<String, dynamic>>.from(acc['connections'] as List? ?? const []);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.account_circle_rounded, color: C.accent, size: 36),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${acc['name'] ?? ''}'.isEmpty ? 'Signed in' : '${acc['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              Text('${acc['email'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            ]),
          ),
        ]),
        const SizedBox(height: 10),
        for (final c in conns)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.check_circle_rounded, color: C.ok),
            title: Text('${c['provider'] == 'google' ? 'Google' : c['provider']}  ·  ${c['account'] ?? ''}'),
            subtitle: const Text('Gmail · Calendar · Drive · Docs · Sheets', style: TextStyle(fontSize: 11.5, color: C.muted)),
            trailing: TextButton(onPressed: () => app.disconnectProvider(c['provider'] as String), child: const Text('Hatao')),
          ),
      ]),
    );
  }
}
