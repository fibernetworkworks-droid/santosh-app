import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_approve.dart';
import 'studio_kit.dart';

/// v0.159 Screen 11 (part 1) · Awaaz: the video's voice (hear both), music (a real Google Lyria track per mood, or her
/// own song), how loud it plays, and the spoken lines / narration of each shot.
class AudioTab extends StatefulWidget {
  const AudioTab({super.key, required this.app, required this.v, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> v;
  final Future<void> Function() onChanged;
  @override
  State<AudioTab> createState() => _AudioTabState();
}

class _AudioTabState extends State<AudioTab> {
  bool _busy = false;
  double? _vol;

  Santosh get app => widget.app;
  String get name => '${widget.v['project']}';

  Future<void> _run(Future<dynamic> Function() f, {String ok = ''}) async {
    setState(() => _busy = true);
    try {
      await f();
      if (mounted && ok.isNotEmpty) studioSnack(context, ok);
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    await widget.onChanged();
  }

  Future<void> _mood(String mood) async {
    if (widget.v['lyria'] == true) {
      final ok = await approveSimple(context, app,
          title: 'Music: ${moodLabel[mood] ?? mood}',
          sub: '$name · Google Lyria',
          rows: [PriceRow(Icons.music_note_rounded, SC.violet, 'One original track', 'For this video, without lyrics', 7)],
          inr: 7,
          month: sMap(widget.v['month']),
          ask: () => app.api!.studioMusicMood(name, mood));
      if (ok && mounted) studioSnack(context, 'Making the music (about 30 sec)');
      await widget.onChanged();
      return;
    }
    await _run(() => app.api!.studioMusicMood(name, mood), ok: 'Added free music');
  }

  Future<void> _ownSong() async {
    final r = await FilePicker.platform.pickFiles(type: FileType.audio, withData: false);
    final path = r?.files.single.path;
    if (path == null) return;
    await _run(() async {
      final bytes = await File(path).readAsBytes();
      final f = await app.api!.chatFile(app.conversationId ?? '', r!.files.single.name, bytes);
      await app.api!.studioMusicMood(name, 'own', fileId: '${f['file_id']}');
    }, ok: 'Your song is added (use only a song you have the rights to)');
  }

  Future<void> _narrate(Map<String, dynamic> s) async {
    final t = TextEditingController(text: '${s['vo_text'] ?? ''}');
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: SC.card,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(ctx).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Shot ${'${s['id']}'.toUpperCase()} narration', style: sora(18)),
          const SizedBox(height: 6),
          Text('It will be spoken in the video\'s voice (free). A ${s['duration']} sec shot fits about ${sInt(s['duration']) * 2} words.',
              style: body(12.5, color: C.faint)),
          const SizedBox(height: 12),
          TextField(controller: t, minLines: 2, maxLines: 5, autofocus: true, style: body(14.5, w: FontWeight.w500),
              decoration: InputDecoration(filled: true, fillColor: SC.field,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none))),
          const SizedBox(height: 14),
          SButton(label: 'Bolwao · free', icon: Icons.record_voice_over_rounded, onTap: () => Navigator.pop(ctx, true)),
        ]),
      ),
    );
    if (ok == true && t.text.trim().isNotEmpty) {
      await _run(() => app.api!.studioVoiceover(name, '${s['id']}', t.text.trim()), ok: 'Narration added');
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final pr = sMap(v['prefs']);
    final mi = sMap(v['music_info']);
    final cur = '${mi['mood'] ?? ''}'.isNotEmpty ? '${mi['mood']}' : '';
    final shots = sList(v['shots']);
    final lines = shots.where((s) => '${s['dialogue'] ?? ''}'.isNotEmpty || '${s['vo_url'] ?? ''}'.isNotEmpty).toList();
    final voice = '${pr['voice_kind'] ?? ''}'.isNotEmpty ? '${pr['voice_kind']}' : (app.aFemale ? 'female' : 'male');
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (_busy) const Padding(padding: EdgeInsets.only(bottom: 10), child: LinearProgressIndicator(color: C.accent, minHeight: 2)),
        const SHead('Video ki awaaz'),
        Row(children: [
          for (final e in const {'male': 'Male · deep', 'female': 'Female · sweet'}.entries) ...[
            Expanded(
              child: Press(
                onTap: () => _run(() => app.api!.studioSettings(name, {'voice': e.key}), ok: 'Voice changed (new lines will use it)'),
                child: Container(
                  height: 60,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: BoxDecoration(
                    color: voice == e.key ? C.accent.withOpacity(.08) : SC.card,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: voice == e.key ? C.accent : SC.line2, width: voice == e.key ? 1.5 : 1),
                  ),
                  child: Row(children: [
                    SoundButton(app: app, url: '', size: 36, light: voice == e.key,
                        load: () async => '${(await app.api!.studioVoiceSample(e.key, '${v['language']}'))['url']}'),
                    const SizedBox(width: 10),
                    Expanded(child: Text(e.value, style: body(12.5, w: FontWeight.w800))),
                  ]),
                ),
              ),
            ),
            if (e.key == 'male') const SizedBox(width: 10),
          ],
        ]),
        const SizedBox(height: 22),
        SHead('Music', trailing: v['lyria'] == true ? 'Google Lyria · ₹7' : 'free'),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          childAspectRatio: 2.4,
          children: [
            for (final m in moodLabel.entries)
              Press(
                onTap: _busy ? null : () => _mood(m.key),
                child: Container(
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: cur == m.key ? C.accent.withOpacity(.10) : SC.card,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: cur == m.key ? C.accent : SC.line2, width: cur == m.key ? 1.5 : 1),
                  ),
                  child: Text(m.value, style: body(12.5, w: cur == m.key ? FontWeight.w800 : FontWeight.w700,
                      color: cur == m.key ? C.accentSoft : C.chip)),
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Press(
          onTap: _busy ? null : _ownSong,
          child: Container(
            height: 44,
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white24)),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              const Icon(Icons.library_music_rounded, size: 18, color: C.chip),
              const SizedBox(width: 8),
              Text(cur == 'own song' ? 'Your song is set · change' : 'Add your own song', style: body(13, w: FontWeight.w700, color: C.chip)),
            ]),
          ),
        ),
        if (mi.isNotEmpty) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(16)),
            child: Column(children: [
              Row(children: [
                SoundButton(app: app, url: '${mi['url'] ?? ''}', size: 44, light: true),
                const SizedBox(width: 12),
                Expanded(child: _wave()),
              ]),
              const SizedBox(height: 6),
              Row(children: [
                const Icon(Icons.volume_down_rounded, size: 18, color: C.faint),
                Expanded(
                  child: Slider(
                    value: (_vol ?? (mi['volume'] as num? ?? 0.25).toDouble()).clamp(0.05, 1.0).toDouble(),
                    min: 0.05,
                    max: 1,
                    activeColor: C.accent,
                    onChanged: (x) => setState(() => _vol = x),
                    onChangeEnd: (x) => _run(() => app.api!.studioSettings(name, {'music_volume': x})),
                  ),
                ),
                const Icon(Icons.volume_up_rounded, size: 18, color: C.faint),
              ]),
              Text('When someone speaks, the music lowers by itself.', style: body(11.5, color: C.faint)),
            ]),
          ),
        ],
        const SizedBox(height: 22),
        const SHead('Speech and narration'),
        if (lines.isEmpty)
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white24)),
            child: Text('No shot has a spoken line. Add narration to a shot below.', style: body(12.5, color: C.muted)),
          ),
        for (final s in lines) ...[
          Container(
            padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(14)),
            child: Row(children: [
              SizedBox(width: 28, child: Text('${s['id']}'.toUpperCase(), style: body(12, w: FontWeight.w800, color: C.faint))),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${s['dialogue'] ?? ''}'.isNotEmpty ? '${s['dialogue']}' : '${s['vo_text']}', maxLines: 2,
                      overflow: TextOverflow.ellipsis, style: body(13, w: FontWeight.w600)),
                  if (s['lipsync'] == true) Text('LIP SYNC', style: body(10, w: FontWeight.w800, color: C.accentSoft)),
                  if ('${s['vo_url'] ?? ''}'.isNotEmpty) Text('NARRATION', style: body(10, w: FontWeight.w800, color: SC.violet)),
                ]),
              ),
              SoundButton(
                app: app,
                url: '${s['dialogue'] ?? ''}'.isNotEmpty ? '${s['line_url'] ?? ''}' : '${s['vo_url'] ?? ''}',
                load: '${s['dialogue'] ?? ''}'.isNotEmpty
                    ? () async => '${(await app.api!.studioLine(name, '${s['id']}'))['url']}'
                    : null,
              ),
            ]),
          ),
          const SizedBox(height: 8),
        ],
        const SizedBox(height: 4),
        SButton(label: 'Add narration to a shot', icon: Icons.record_voice_over_rounded, primary: false, height: 46,
            onTap: shots.isEmpty || _busy
                ? null
                : () async {
                    final id = await pickOne<String>(context, 'On which shot?', {
                      for (final s in shots)
                        '${s['id']}': '${'${s['id']}'.toUpperCase()} · ${'${s['prompt']}'.length > 40 ? '${'${s['prompt']}'.substring(0, 40)}…' : s['prompt']}',
                    });
                    if (id != null) await _narrate(shots.firstWhere((s) => '${s['id']}' == id));
                  }),
      ]),
    );
  }

  Widget _wave() => SizedBox(
        height: 34,
        child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          for (var i = 0; i < 26; i++)
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 1.5),
                height: 6.0 + ((i * 37) % 23),
                decoration: BoxDecoration(color: C.violet.withOpacity(i < 9 ? 1 : .45), borderRadius: BorderRadius.circular(2)),
              ),
            ),
        ]),
      );
}

/// v0.159 Screen 11 (part 2) · Brand: captions on / off and their look, the logo and where it sits, the AI label.
class BrandTab extends StatefulWidget {
  const BrandTab({super.key, required this.app, required this.v, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> v;
  final Future<void> Function() onChanged;
  @override
  State<BrandTab> createState() => _BrandTabState();
}

class _BrandTabState extends State<BrandTab> {
  bool _busy = false;

  Santosh get app => widget.app;
  String get name => '${widget.v['project']}';

  Future<void> _set(Map<String, dynamic> m, {String ok = ''}) async {
    setState(() => _busy = true);
    try {
      await app.api!.studioSettings(name, m);
      if (mounted && ok.isNotEmpty) studioSnack(context, ok);
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    await widget.onChanged();
  }

  Future<void> _logo(String pos) async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 95, maxWidth: 1200);
    if (x == null) return;
    setState(() => _busy = true);
    try {
      final f = await app.api!.chatFile(app.conversationId ?? '', x.name.isEmpty ? 'logo.png' : x.name, await x.readAsBytes());
      await app.api!.studioLogo(name, '${f['file_id']}', pos);
      if (mounted) studioSnack(context, 'Logo added');
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
    await widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final pr = sMap(widget.v['prefs']);
    final logo = sMap(widget.v['logo_info']);
    final pos = '${logo['position'] ?? 'top-right'}';
    final style = '${pr['caption_style'] ?? 'bold'}';
    final on = pr['captions'] != false;
    const spots = ['top-left', 'top', 'top-right', 'left', 'center', 'right', 'bottom-left', 'bottom', 'bottom-right'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (_busy) const Padding(padding: EdgeInsets.only(bottom: 10), child: LinearProgressIndicator(color: C.accent, minHeight: 2)),
        Row(children: [
          Expanded(child: Text('Captions', style: sora(15.5))),
          Switch(value: on, activeColor: C.onAccent, activeTrackColor: C.accent, onChanged: (x) => _set({'captions': x})),
        ]),
        const SizedBox(height: 6),
        Opacity(
          opacity: on ? 1 : .4,
          child: Row(children: [
            for (final e in const {'bold': 'Large letters', 'words': 'Shabd-shabd', 'plain': 'Saada'}.entries) ...[
              Expanded(
                child: Press(
                  onTap: on ? () => _set({'caption_style': e.key}) : null,
                  child: Container(
                    height: 96,
                    padding: const EdgeInsets.only(bottom: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF2A1A0C),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: style == e.key ? C.accent : SC.line2, width: style == e.key ? 1.5 : 1),
                    ),
                    child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                      if (e.key == 'bold')
                        Text('मन शांत', style: body(14, w: FontWeight.w800, color: Colors.white)
                            .copyWith(shadows: const [Shadow(blurRadius: 3, color: Colors.black)]))
                      else if (e.key == 'words')
                        RichText(text: TextSpan(style: body(14, w: FontWeight.w800, color: Colors.white), children: const [
                          TextSpan(text: 'मन '),
                          TextSpan(text: 'शांत', style: TextStyle(color: Color(0xFFFFD27A))),
                        ]))
                      else
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(4)),
                          child: Text('मन शांत', style: body(11.5, color: Colors.white)),
                        ),
                      const SizedBox(height: 6),
                      Text(e.value, style: body(11, w: FontWeight.w700, color: style == e.key ? C.accentSoft : C.chip)),
                    ]),
                  ),
                ),
              ),
              if (e.key != 'plain') const SizedBox(width: 8),
            ],
          ]),
        ),
        const SizedBox(height: 24),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 84,
            height: 130,
            padding: const EdgeInsets.all(5),
            decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(12)),
            child: GridView.count(
              crossAxisCount: 3,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 4,
              crossAxisSpacing: 4,
              childAspectRatio: .62,
              children: [
                for (final sp in spots)
                  GestureDetector(
                    onTap: logo.isEmpty ? () => _logo(sp) : () => _set({'logo_position': sp}, ok: 'Logo position changed'),
                    child: Container(decoration: BoxDecoration(
                        color: logo.isNotEmpty && pos == sp ? C.accent : Colors.white10, borderRadius: BorderRadius.circular(4))),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('Logo', style: sora(15.5)),
              const SizedBox(height: 8),
              if (logo.isNotEmpty)
                Row(children: [
                  SizedBox(width: 44, height: 44, child: SImage(app: app, url: '${logo['url'] ?? ''}', radius: 10, fit: BoxFit.contain)),
                  const SizedBox(width: 10),
                  Expanded(child: Text('It will stay in the corner. Tap a box to change its position.',
                      style: body(11.5, color: C.faint, height: 1.4))),
                ]),
              const SizedBox(height: 8),
              SButton(label: logo.isEmpty ? 'Choose a logo photo' : 'Logo badlo', primary: false, height: 44,
                  onTap: _busy ? null : () => _logo(logo.isEmpty ? 'top-right' : pos)),
              const SizedBox(height: 10),
              Row(children: [
                const Icon(Icons.lock_rounded, size: 14, color: C.faint),
                const SizedBox(width: 6),
                Expanded(child: Text('The "AI-generated · Hoola" label is always there (as the law requires)', style: body(11.5, color: C.faint))),
              ]),
            ]),
          ),
        ]),
      ]),
    );
  }
}
