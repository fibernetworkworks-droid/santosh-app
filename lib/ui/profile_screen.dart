import 'package:flutter/material.dart';

import '../state.dart';
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
