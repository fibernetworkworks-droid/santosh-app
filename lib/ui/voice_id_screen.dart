import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../state.dart';
import '../voice_recorder.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

const _modes = {
  'off': ('Off', 'Hoola does not recognise anyone by voice'),
  'on': ('On', 'Household members are recognised; an unknown voice is treated as the owner'),
  'strict': ('Strict', 'Mail, money, files and PC only by your confirmed voice'),
};

/// Profile > Awaaz Pehchaan: Hoola knows who is talking (you, Maa, Papa...) and keeps your private work locked to
/// your own voice. Each person enrols by reading a short script in their own voice (their own permission).
class VoiceIdScreen extends StatefulWidget {
  const VoiceIdScreen({super.key, required this.app});
  final Santosh app;

  @override
  State<VoiceIdScreen> createState() => _VoiceIdScreenState();
}

class _VoiceIdScreenState extends State<VoiceIdScreen> {
  Map<String, dynamic>? _o;
  String? _err;
  bool _busy = false;

  Api get _api => widget.app.api!;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = await _api.voiceId();
      if (mounted) setState(() {
        _o = o;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  void _say(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  List<Map<String, dynamic>> get _members =>
      List<Map<String, dynamic>>.from(((_o?['members'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  Future<void> _setMode(String m) async {
    setState(() => _busy = true);
    try {
      await _api.voiceIdMode(m);
      await _load();
    } catch (e) {
      _say('$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _add({required bool self}) async {
    if (widget.app.voiceCall.inCall) {
      _say('A call is in progress. End the call first, then add a voice.');
      return;
    }
    final Map<String, dynamic>? spec =
        self ? <String, dynamic>{'name': '', 'relation': 'self', 'gender': null, 'level': 'owner'} : await _askPerson();
    if (spec == null || !mounted) return;
    if (self) {
      final name = await _askName('Your name');
      if (name == null || !mounted) return;
      spec['name'] = name;
      spec['gender'] = await _askGender();
      if (spec['gender'] == null || !mounted) return;
    }
    Map<String, dynamic> script;
    try {
      script = await _api.voiceIdEnrol(spec['name'] as String, spec['relation'] as String,
          gender: spec['gender'] as String?, level: spec['level'] as String?);
    } catch (e) {
      _say('$e');
      return;
    }
    if (!mounted) return;
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(
        builder: (_) => _EnrolPage(api: _api, script: script, name: spec['name'] as String, self: self)));
    if (ok == true) await _load();
  }

  Future<String?> _askName(String title) async {
    final c = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text(title),
        content: TextField(controller: c, autofocus: true, textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(hintText: 'Name')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Leave it')),
          TextButton(onPressed: () => Navigator.pop(ctx, c.text.trim().isEmpty ? null : c.text.trim()), child: const Text('Next')),
        ],
      ),
    );
  }

  Future<String?> _askGender() => showDialog<String>(
        context: context,
        builder: (ctx) => SimpleDialog(
          backgroundColor: C.bgBottom,
          title: const Text('How will they read the script?'),
          children: [
            SimpleDialogOption(onPressed: () => Navigator.pop(ctx, 'm'), child: const Text('"I give my permission"')),
            SimpleDialogOption(onPressed: () => Navigator.pop(ctx, 'f'), child: const Text('"I give my permission"')),
          ],
        ),
      );

  Future<Map<String, dynamic>?> _askPerson() async {
    final rels = List<Map<String, dynamic>>.from(((_o?['relations'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .where((r) => r['id'] != 'self'));
    final name = TextEditingController();
    String rel = rels.isNotEmpty ? rels.first['id'] as String : 'maa';
    String? gender;
    String level = 'family';
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) {
          final fixed = rels.firstWhere((r) => r['id'] == rel, orElse: () => const {})['gender'] as String?;
          return AlertDialog(
            backgroundColor: C.bgBottom,
            title: const Text('Household members'),
            content: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                TextField(controller: name, textCapitalization: TextCapitalization.words,
                    decoration: const InputDecoration(labelText: 'Name (for example Asha)')),
                const SizedBox(height: 12),
                const Text('Relation', style: TextStyle(color: C.muted, fontSize: 12.5)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final r in rels)
                    ChoiceChip(
                      label: Text(r['label'] as String),
                      selected: rel == r['id'],
                      showCheckmark: false,
                      selectedColor: C.accent,
                      labelStyle: TextStyle(color: rel == r['id'] ? C.onAccent : C.chip, fontSize: 12.5),
                      onSelected: (_) => set(() => rel = r['id'] as String),
                    ),
                ]),
                if (fixed == null) ...[
                  const SizedBox(height: 12),
                  Wrap(spacing: 6, children: [
                    for (final g in const [('m', 'Male'), ('f', 'Female')])
                      ChoiceChip(
                        label: Text(g.$2),
                        selected: gender == g.$1,
                        showCheckmark: false,
                        selectedColor: C.accent,
                        labelStyle: TextStyle(color: gender == g.$1 ? C.onAccent : C.chip, fontSize: 12.5),
                        onSelected: (_) => set(() => gender = g.$1),
                      ),
                  ]),
                ],
                const SizedBox(height: 12),
                const Text('What they can do', style: TextStyle(color: C.muted, fontSize: 12.5)),
                RadioListTile<String>(
                  contentPadding: EdgeInsets.zero, dense: true, value: 'family', groupValue: level,
                  title: const Text('Household tasks'), subtitle: const Text('Reminder, alarm, music, TV, AC, search'),
                  onChanged: (v) => set(() => level = v!),
                ),
                RadioListTile<String>(
                  contentPadding: EdgeInsets.zero, dense: true, value: 'trusted', groupValue: level,
                  title: const Text('Trusted'), subtitle: const Text('Also reading Calendar, files and mail; not money, sending mail or PC'),
                  onChanged: (v) => set(() => level = v!),
                ),
              ]),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Leave it')),
              TextButton(
                onPressed: () {
                  if (name.text.trim().isEmpty || (fixed == null && gender == null)) return;
                  Navigator.pop(ctx, {'name': name.text.trim(), 'relation': rel, 'gender': fixed ?? gender, 'level': level});
                },
                child: const Text('Next'),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _remove(Map<String, dynamic> m) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.bgBottom,
        title: Text('${m['name']} — remove the voice?'),
        content: const Text('Hoola will delete their voice recognition at once.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('No')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Remove', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _api.voiceIdDelete(m['id'] as String);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  Future<void> _level(Map<String, dynamic> m, String level) async {
    try {
      await _api.voiceIdUpdate(m['id'] as String, level: level);
      await _load();
    } catch (e) {
      _say('$e');
    }
  }

  Widget _member(Map<String, dynamic> m) {
    final owner = m['owner'] == true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
        child: Row(children: [
          Icon(owner ? Icons.verified_user_rounded : Icons.person_rounded, color: owner ? C.ok : C.accentSoft),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(owner ? 'You (owner) · everything' : '${m['relation_label']} · ${m['level'] == 'trusted' ? 'trusted' : 'household tasks'}',
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ])),
          if (!owner)
            PopupMenuButton<String>(
              icon: const Icon(Icons.tune_rounded, color: C.muted),
              color: C.bgBottom,
              onSelected: (v) => _level(m, v),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'family', child: Text('Household tasks')),
                PopupMenuItem(value: 'trusted', child: Text('Trusted')),
              ],
            ),
          IconButton(icon: const Icon(Icons.delete_outline_rounded, color: C.faint), onPressed: () => _remove(m)),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final o = _o;
    final mode = o?['mode'] as String? ?? 'on';
    final ownerIn = o?['owner_enrolled'] == true;
    return DeskPage(
      title: 'Voice Recognition',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (o == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (o != null) ...[
              Glass(
                child: Text(
                  'In a call, ${widget.app.aName} will recognise by voice who is speaking: you, Mom, Dad or someone else. '
                  'Household members can get their own tasks done, but your mail, money, files, PC and Hoola Network only by your voice.\n\n'
                  'Each person reads a short script and gives their own permission. The recording is not saved, only the voice '
                  'recognition (encrypted). A voice is not a password: money always moves only with your tap.',
                  style: const TextStyle(color: C.chip, fontSize: 13.5, height: 1.35),
                ),
              ),
              const SizedBox(height: 14),
              if (o['available'] != true)
                const Glass(child: Text('Voice Recognition is not on the server yet (setup_voiceid.sh has to be run on the server).',
                    style: TextStyle(color: C.warn))),
              if (o['available'] == true) ...[
                const Text('Lock', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final e in _modes.entries)
                    ChoiceChip(
                      label: Text(e.value.$1),
                      selected: mode == e.key,
                      showCheckmark: false,
                      selectedColor: C.accent,
                      labelStyle: TextStyle(color: mode == e.key ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
                      onSelected: _busy ? null : (_) => _setMode(e.key),
                    ),
                ]),
                const SizedBox(height: 6),
                Text(_modes[mode]?.$2 ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
                const SizedBox(height: 16),
                for (final m in _members) _member(m),
                if (!ownerIn) ...[
                  GradientButton(label: 'First add your voice', icon: Icons.mic_rounded, height: 50, onTap: () => _add(self: true)),
                  const SizedBox(height: 10),
                ],
                GlassButton(label: 'Add a household member', icon: Icons.group_add_rounded, height: 48,
                    onTap: ownerIn ? () => _add(self: false) : null),
              ],
            ],
          ]),
        ),
    );
  }
}

/// The person reads the script aloud; the recording is checked and turned into a voice fingerprint.
class _EnrolPage extends StatefulWidget {
  const _EnrolPage({required this.api, required this.script, required this.name, required this.self});
  final Api api;
  final Map<String, dynamic> script;
  final String name;
  final bool self;

  @override
  State<_EnrolPage> createState() => _EnrolPageState();
}

class _EnrolPageState extends State<_EnrolPage> {
  final _rec = VoiceRecorder();
  Timer? _tick;
  bool _sending = false;
  String? _msg;
  bool _done = false;

  static const _min = Duration(seconds: 15);

  @override
  void dispose() {
    _tick?.cancel();
    if (_rec.recording) _rec.stop();
    super.dispose();
  }

  Future<void> _start() async {
    final err = await _rec.start();
    if (err != null) {
      setState(() => _msg = err);
      return;
    }
    setState(() => _msg = null);
    _tick = Timer.periodic(const Duration(milliseconds: 100), (_) {
      if (mounted) setState(() {});
      if (_rec.length > const Duration(seconds: 60)) _stop();
    });
  }

  Future<void> _stop() async {
    _tick?.cancel();
    final long = _rec.length;
    final wav = await _rec.stop();
    if (long < _min) {
      setState(() => _msg = 'A little more: read the whole script calmly (at least 15 seconds).');
      return;
    }
    setState(() {
      _sending = true;
      _msg = 'Checking…';
    });
    try {
      final m = await widget.api.voiceIdUpload(widget.script['enrol_id'] as String, wav);
      setState(() {
        _done = true;
        _msg = '${m['name']} \'s voice is added. Now Hoola will recognise them in calls.';
      });
    } catch (e) {
      setState(() => _msg = e is ApiException ? e.message : '$e');
    }
    if (mounted) setState(() => _sending = false);
  }

  @override
  Widget build(BuildContext context) {
    final secs = _rec.length.inMilliseconds / 1000;
    return DeskPage(
      title: widget.self ? 'Your voice' : '${widget.name}\'s voice',
      body: () => ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
          Text(widget.self ? 'Read this script yourself, in your normal voice:' : '${widget.name} should read this script themselves (with their own permission):',
              style: const TextStyle(color: C.muted)),
          const SizedBox(height: 10),
          Glass(child: Text(widget.script['script'] as String? ?? '', style: const TextStyle(fontSize: 18, height: 1.45))),
          const SizedBox(height: 10),
          const Text('A quiet place, phone an arm\'s length from your mouth. Be sure to read the code line.',
              style: TextStyle(color: C.faint, fontSize: 12.5)),
          const SizedBox(height: 18),
          if (_rec.recording) ...[
            LinearProgressIndicator(value: _rec.level, minHeight: 8, color: C.ok, backgroundColor: C.panel),
            const SizedBox(height: 8),
            Text('${secs.toStringAsFixed(0)} sec${secs < 15 ? ' (at least 15)' : ''}', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            GradientButton(label: 'Done', icon: Icons.stop_rounded, onTap: _stop),
          ] else if (!_done)
            GradientButton(label: _sending ? 'Checking…' : 'Start speaking', icon: Icons.mic_rounded,
                onTap: _sending ? null : _start),
          if (_msg != null) ...[
            const SizedBox(height: 14),
            Text(_msg!, textAlign: TextAlign.center, style: TextStyle(color: _done ? C.ok : C.chip, fontWeight: FontWeight.w600)),
          ],
          if (_done) ...[
            const SizedBox(height: 16),
            GlassButton(label: 'OK', icon: Icons.check_rounded, onTap: () => Navigator.pop(context, true)),
          ],
        ]),
    );
  }
}
