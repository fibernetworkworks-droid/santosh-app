import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_kit.dart';

/// v0.159 Screens 2 + 3 · "Naya AI video" in two calm steps: the idea (name, what it is about, photos, length, shape,
/// language, voice), then the look and the quality with rough prices. Nothing is paid here: the storyboard is free.
class NewVideoScreen extends StatefulWidget {
  const NewVideoScreen({super.key, required this.app, this.idea = '', this.seconds = 30, this.style = 'cinematic',
      this.aspect = '9:16', this.language = 'Hindi'});
  final Santosh app;
  final String idea;
  final int seconds;
  final String style;
  final String aspect;
  final String language;
  @override
  State<NewVideoScreen> createState() => _NewVideoScreenState();
}

class _Photo {
  _Photo(this.file, this.bytes);
  final XFile file;
  final Uint8List bytes;
  final name = TextEditingController();
  String kind = 'person';
  bool consent = false;
}

class _NewVideoScreenState extends State<NewVideoScreen> {
  int _step = 0;
  final _name = TextEditingController();
  late final _brief = TextEditingController(text: widget.idea);
  final _photos = <_Photo>[];
  late int _secs = widget.seconds;
  late String _aspect = widget.aspect;
  late String _lang = widget.language;
  late String _style = widget.style;
  late String _voice = widget.app.aFemale ? 'female' : 'male';
  String _quality = 'final';
  bool _captions = true;
  String _capStyle = 'bold';
  bool _music = true;
  String _mood = 'calm';
  XFile? _logo;
  bool _busy = false;
  bool _improving = false;
  String _stage = '';
  final SpeechToText _stt = SpeechToText();
  bool _listening = false;

  Santosh get app => widget.app;

  // rough rupees per second of video (the real price comes on the card)
  static const _perSec = {'preview': 0.0, 'draft': 3.8, 'final': 8.5, 'premium': 48.5};

  @override
  void dispose() {
    _name.dispose();
    _brief.dispose();
    _stt.stop();
    super.dispose();
  }

  Future<void> _mic() async {
    if (_listening) {
      await _stt.stop();
      setState(() => _listening = false);
      return;
    }
    final ok = await _stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted) setState(() => _listening = false);
    });
    if (!ok) {
      if (mounted) studioSnack(context, 'Microphone ki permission chahiye.');
      return;
    }
    final before = _brief.text.trim();
    setState(() => _listening = true);
    await _stt.listen(
      localeId: app.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 60),
      pauseFor: const Duration(seconds: 4),
      partialResults: true,
      onResult: (r) => setState(() => _brief.text = before.isEmpty ? r.recognizedWords : '$before ${r.recognizedWords}'),
    );
  }

  Future<void> _improve() async {
    if (_brief.text.trim().length < 4) {
      studioSnack(context, 'Pehle thoda sa likhiye.');
      return;
    }
    setState(() => _improving = true);
    try {
      final r = await app.api!.studioImprove(_brief.text.trim(), _lang, _secs);
      if (mounted) setState(() => _brief.text = '${r['brief']}');
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _improving = false);
  }

  Future<void> _addPhoto() async {
    if (_photos.length >= 4) {
      studioSnack(context, '4 photo tak');
      return;
    }
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 90, maxWidth: 2000);
    if (x == null) return;
    final b = await x.readAsBytes();
    if (!mounted) return;
    final p = _Photo(x, b);
    final ok = await _photoSheet(p);
    if (ok == true && mounted) setState(() => _photos.add(p));
  }

  Future<bool?> _photoSheet(_Photo p) => showModalBottomSheet<bool>(
        context: context,
        isScrollControlled: true,
        backgroundColor: SC.card,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, set) => Padding(
            padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + MediaQuery.of(ctx).viewInsets.bottom),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                ClipRRect(borderRadius: BorderRadius.circular(12),
                    child: Image.memory(p.bytes, width: 64, height: 64, fit: BoxFit.cover)),
                const SizedBox(width: 12),
                Expanded(child: Text('Yeh photo kiski hai?', style: sora(17))),
              ]),
              const SizedBox(height: 14),
              Wrap(spacing: 8, children: [
                for (final k in const {'person': 'Insaan', 'product': 'Product / logo', 'place': 'Jagah'}.entries)
                  SChip(label: k.value, on: p.kind == k.key, onTap: () => set(() => p.kind = k.key)),
              ]),
              const SizedBox(height: 12),
              TextField(
                controller: p.name,
                onChanged: (_) => set(() {}),
                style: body(15),
                decoration: InputDecoration(
                  labelText: p.kind == 'person' ? 'Naam (jaise Meera)' : p.kind == 'product' ? 'Naam (jaise Chai packet)' : 'Naam (jaise Nadi kinara)',
                  filled: true,
                  fillColor: SC.field,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                ),
              ),
              if (p.kind == 'person')
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: p.consent,
                  activeColor: C.accent,
                  onChanged: (v) => set(() => p.consent = v == true),
                  title: Text('Is insaan ne video ke liye ijazat di hai', style: body(13.5)),
                ),
              const SizedBox(height: 12),
              SButton(
                label: 'Jodo',
                onTap: p.name.text.trim().isEmpty || (p.kind == 'person' && !p.consent) ? null : () => Navigator.pop(ctx, true),
              ),
            ]),
          ),
        ),
      );

  void _next() {
    if (_name.text.trim().length < 2) {
      studioSnack(context, 'Video ka naam likhiye');
      return;
    }
    if (_brief.text.trim().length < 8) {
      studioSnack(context, 'Video kis baare mein hai, thoda likhiye');
      return;
    }
    setState(() => _step = 1);
  }

  Future<void> _create() async {
    setState(() {
      _busy = true;
      _stage = 'Project ban raha hai…';
    });
    final name = _name.text.trim();
    try {
      final v = await app.api!.studioNew({
        'name': name, 'brief': '', 'aspect': _aspect, 'style': _style, 'language': _lang, 'seconds': _secs, 'voice': _voice,
        'captions': _captions, 'caption_style': _capStyle, 'music': _music ? _mood : '', 'quality': _quality,
      });
      final project = '${v['project']}';
      final conv = app.conversationId ?? '';
      for (final p in _photos) {
        if (mounted) setState(() => _stage = '${p.name.text.trim()} ki photo jod raha hoon…');
        final f = await app.api!.chatFile(conv, p.file.name.isEmpty ? 'photo.jpg' : p.file.name, p.bytes);
        await app.api!.studioCharacter(project, {
          'name': p.name.text.trim(), 'description': '', 'file_ids': ['${f['file_id']}'], 'consent': p.kind != 'person' || p.consent,
          'voice': _voice, 'kind': p.kind,
        });
      }
      if (_logo != null) {
        if (mounted) setState(() => _stage = 'Logo jod raha hoon…');
        final f = await app.api!.chatFile(conv, _logo!.name.isEmpty ? 'logo.png' : _logo!.name, await _logo!.readAsBytes());
        await app.api!.studioLogo(project, '${f['file_id']}', 'top-right');
      }
      if (mounted) setState(() => _stage = 'Storyboard shuru…');
      await app.api!.studioPlan(project, _brief.text.trim(), _secs);
      if (mounted) Navigator.pop(context, project);
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => PopScope(
        canPop: _step == 0,
        onPopInvoked: (did) {
          if (!did && _step == 1) setState(() => _step = 0);
        },
        child: Scaffold(
          backgroundColor: SC.bg,
          body: SafeArea(
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 8, 16, 6),
                child: Row(children: [
                  IconButton(
                    onPressed: () => _step == 1 ? setState(() => _step = 0) : Navigator.maybePop(context),
                    icon: Icon(_step == 1 ? Icons.chevron_left_rounded : Icons.close_rounded, size: _step == 1 ? 30 : 24),
                  ),
                  Expanded(child: Text(_step == 0 ? 'Naya AI video' : 'Look aur quality', style: sora(18))),
                  Text('Kadam ${_step + 1} / 2', style: body(12, w: FontWeight.w700, color: C.faint)),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                child: Row(children: [
                  Expanded(child: Container(height: 3, decoration: BoxDecoration(color: C.accent, borderRadius: BorderRadius.circular(2)))),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Container(height: 3, decoration: BoxDecoration(
                        color: _step == 1 ? C.accent : Colors.white12, borderRadius: BorderRadius.circular(2))),
                  ),
                ]),
              ),
              Expanded(child: _step == 0 ? _idea() : _look()),
              SBottomBar(
                note: _step == 1 ? (_busy ? _stage : 'Storyboard free hai. Paisa tabhi lagega jab aap daam ke card par haan karenge.') : null,
                child: _step == 0
                    ? SButton(label: 'Aage: look chuniye', icon: Icons.arrow_forward_rounded, onTap: _next)
                    : SButton(label: 'Storyboard banao · free', icon: Icons.auto_awesome_rounded, busy: _busy, onTap: _create),
              ),
            ]),
          ),
        ),
      );

  InputDecoration _box(String hint) => InputDecoration(
        hintText: hint,
        hintStyle: body(14, w: FontWeight.w500, color: C.faint),
        filled: true,
        fillColor: SC.card,
        contentPadding: const EdgeInsets.all(14),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: SC.line2)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.accent)),
      );

  Widget _idea() => ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 24), children: [
        const SLabel('Naam'),
        TextField(controller: _name, style: body(15), decoration: _box('Jaise: Gautam Buddha')),
        const SizedBox(height: 22),
        SLabel('Video kis baare mein hai?', trailing: '${_brief.text.length} / 2000'),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(18), border: Border.all(color: C.accent)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            TextField(
              controller: _brief,
              minLines: 4,
              maxLines: 9,
              maxLength: 2000,
              onChanged: (_) => setState(() {}),
              style: body(14.5, w: FontWeight.w500, height: 1.5),
              decoration: InputDecoration.collapsed(
                hintText: 'Kya dikhana hai, kisko, kya bolna hai, kya offer / sandesh. Jitna detail, utna achha.',
                hintStyle: body(14, w: FontWeight.w500, color: C.faint, height: 1.5),
              ).copyWith(counterText: ''),
            ),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              SChip(label: _listening ? 'Sun raha hoon…' : 'Bolkar likhein', icon: _listening ? Icons.stop_rounded : Icons.mic_rounded,
                  on: _listening, onTap: _mic),
              SChip(label: _improving ? 'Likh raha hoon…' : 'Hoola se behtar karwao', icon: Icons.auto_awesome_rounded, on: false,
                  onTap: _improving ? null : _improve),
            ]),
          ]),
        ),
        const SizedBox(height: 22),
        const SLabel('Photo (insaan, product, jagah)', trailing: 'har shot mein wahi chehra'),
        Wrap(spacing: 10, runSpacing: 10, children: [
          for (final p in _photos)
            Stack(children: [
              ClipRRect(borderRadius: BorderRadius.circular(16),
                  child: Image.memory(p.bytes, width: 76, height: 76, fit: BoxFit.cover)),
              Positioned(left: 6, bottom: 6, child: Tag(p.name.text.trim(), fg: C.ink, bg: const Color(0xBF0B0A1A), size: 10)),
              Positioned(
                right: 2,
                top: 2,
                child: GestureDetector(
                  onTap: () => setState(() => _photos.remove(p)),
                  child: const CircleAvatar(radius: 11, backgroundColor: Color(0xCC0B0A1A), child: Icon(Icons.close_rounded, size: 14, color: C.ink)),
                ),
              ),
            ]),
          _dashed(Icons.add_rounded, 'Photo', _addPhoto),
        ]),
        const SizedBox(height: 22),
        const SLabel('Lambai'),
        SSegment<int>(items: const {15: '15s', 30: '30s', 60: '1m', 120: '2m', 300: '5m'}, value: _secs,
            onChanged: (v) => setState(() => _secs = v)),
        const SizedBox(height: 8),
        Text('Lagbhag ${(_secs / 5).ceil()} shots · HD mein ~${rupees(_secs * (_perSec['final'] ?? 8.5))} · free preview pehle',
            style: body(11.5, color: C.faint)),
        const SizedBox(height: 22),
        const SLabel('Shape'),
        Row(children: [
          _shape('9:16', '9:16 Reel', 24, 40),
          const SizedBox(width: 10),
          _shape('16:9', '16:9 YouTube', 44, 26),
          const SizedBox(width: 10),
          _shape('1:1', '1:1 Post', 32, 32),
        ]),
        const SizedBox(height: 22),
        const SLabel('Bhasha (bolna + captions)'),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final l in langs) SChip(label: l[1], on: _lang == l[0], onTap: () => setState(() => _lang = l[0])),
        ]),
        const SizedBox(height: 22),
        const SLabel('Awaaz'),
        Row(children: [
          Expanded(child: _voiceTile('male', '${app.aFemale ? 'Purush' : app.aName}', 'purush · gambhir')),
          const SizedBox(width: 10),
          Expanded(child: _voiceTile('female', '${app.aFemale ? app.aName : 'Mahila'}', 'madhur · shaant')),
        ]),
      ]);

  Widget _dashed(IconData icon, String label, VoidCallback onTap) => Press(
        onTap: onTap,
        child: Container(
          width: 76,
          height: 76,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white24, width: 1.5)),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(icon, color: C.muted, size: 20),
            const SizedBox(height: 4),
            Text(label, style: body(11, w: FontWeight.w700, color: C.muted)),
          ]),
        ),
      );

  Widget _shape(String a, String label, double w, double h) {
    final on = _aspect == a;
    return Expanded(
      child: Press(
        onTap: () => setState(() => _aspect = a),
        child: Container(
          height: 104,
          decoration: BoxDecoration(
            color: on ? C.accent.withOpacity(.08) : SC.card,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: on ? C.accent : SC.line2, width: on ? 1.5 : 1),
          ),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Container(width: w, height: h, decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(5), border: Border.all(color: on ? C.accent : C.muted, width: 2))),
            const SizedBox(height: 8),
            Text(label, style: body(12.5, w: FontWeight.w700, color: on ? C.ink : C.chip)),
          ]),
        ),
      ),
    );
  }

  Widget _voiceTile(String voice, String title, String sub) {
    final on = _voice == voice;
    return Press(
      onTap: () => setState(() => _voice = voice),
      child: Container(
        height: 64,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(
          color: on ? C.accent.withOpacity(.08) : SC.card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: on ? C.accent : SC.line2, width: on ? 1.5 : 1),
        ),
        child: Row(children: [
          SoundButton(app: app, url: '', size: 38, light: on,
              load: () async => '${(await app.api!.studioVoiceSample(voice, _lang))['url']}'),
          const SizedBox(width: 10),
          Expanded(
            child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: body(13, w: FontWeight.w800)),
              Text(sub, maxLines: 1, style: body(11, color: C.faint)),
            ]),
          ),
        ]),
      ),
    );
  }

  // ---- step 2 ----
  static const _looks = {
    'reel': [Color(0xFF3B1230), Icons.phone_android_rounded],
    'cinematic': [Color(0xFF2A1A0C), Icons.movie_rounded],
    'ad': [Color(0xFF10283A), Icons.campaign_rounded],
    'indian_wedding': [Color(0xFF3A0E1A), Icons.favorite_rounded],
    'documentary': [Color(0xFF1A2A1A), Icons.landscape_rounded],
    'animation_3d': [Color(0xFF1B2350), Icons.emoji_emotions_rounded],
    'anime': [Color(0xFF2B1650), Icons.auto_awesome_rounded],
    'news': [Color(0xFF1C1C2C), Icons.newspaper_rounded],
  };

  Widget _look() => ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 24), children: [
        const SLabel('Look'),
        GridView.count(
          crossAxisCount: 4,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 8,
          childAspectRatio: .62,
          children: [
            for (final e in _looks.entries)
              Press(
                onTap: () => setState(() => _style = e.key),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: e.value[0] as Color,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: _style == e.key ? C.accent : Colors.transparent, width: 2),
                      ),
                      child: Icon(e.value[1] as IconData, color: _style == e.key ? C.accentSoft : Colors.white54, size: 28),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(styleLabel[e.key] ?? e.key, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: body(11.5, w: _style == e.key ? FontWeight.w800 : FontWeight.w700, color: _style == e.key ? C.accentSoft : C.chip)),
                ]),
              ),
          ],
        ),
        const SizedBox(height: 22),
        SLabel('Quality ($_secs sec ke liye)', trailing: 'baad mein badal sakte hain'),
        for (final q in const ['preview', 'draft', 'final', 'premium']) ...[_qTile(q), const SizedBox(height: 8)],
        const SizedBox(height: 14),
        Container(
          decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(16), border: Border.all(color: SC.line)),
          child: Column(children: [
            _switch('Captions', _captions ? '${langShown(_lang)} · ${const {'bold': 'bade akshar', 'words': 'shabd-shabd', 'plain': 'saada'}[_capStyle]}' : 'band',
                _captions, (v) => setState(() => _captions = v), onTap: () async {
              final s = await pickOne<String>(context, 'Captions ka andaaz',
                  const {'bold': 'Bade akshar (neeche)', 'words': 'Shabd-shabd (2-3 shabd)', 'plain': 'Saada (patti par)'}, current: _capStyle);
              if (s != null) setState(() => _capStyle = s);
            }),
            const Divider(height: 1, color: Color(0x0FFFFFFF)),
            _switch('Asli music (Google Lyria)', _music ? '${moodLabel[_mood]} · ~₹7' : 'bina music', _music, (v) => setState(() => _music = v),
                onTap: () async {
              final m = await pickOne<String>(context, 'Music ka mood', moodLabel, current: _mood);
              if (m != null) setState(() => _mood = m);
            }),
            const Divider(height: 1, color: Color(0x0FFFFFFF)),
            _switch('Logo', _logo == null ? 'apni dukaan / brand ka logo' : 'upar daayein kone mein', _logo != null, (v) async {
              if (!v) {
                setState(() => _logo = null);
                return;
              }
              final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 95, maxWidth: 1200);
              if (x != null && mounted) setState(() => _logo = x);
            }),
          ]),
        ),
      ]);

  Widget _qTile(String q) {
    final on = _quality == q;
    final price = q == 'preview' ? 'Free' : '~${rupees(_secs * (_perSec[q] ?? 0))}';
    return Press(
      onTap: q == 'preview' ? () => studioSnack(context, 'Preview har project mein free hai; asli video ke liye quality chuniye.')
          : () => setState(() => _quality = q),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: on ? C.accent.withOpacity(.08) : SC.card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: on ? C.accent : SC.line2, width: on ? 1.5 : 1),
        ),
        child: Row(children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: on ? C.accent : C.faint, width: on ? 6 : 2)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(qualityLabel[q] ?? q, style: body(14, w: FontWeight.w800)),
                if (q == 'final') ...[const SizedBox(width: 6), const Tag('SUJHAV', fg: C.onAccent, bg: C.accent, size: 9.5)],
              ]),
              Text(qualityWhat[q] ?? '', style: body(11.5, color: C.faint)),
            ]),
          ),
          Text(price, style: body(14, w: FontWeight.w800, color: q == 'preview' ? C.ok : C.ink)),
        ]),
      ),
    );
  }

  Widget _switch(String title, String sub, bool on, ValueChanged<bool> set, {VoidCallback? onTap}) => InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: body(13.5, w: FontWeight.w700)),
                Text(sub, style: body(11.5, color: onTap != null && on ? C.accentSoft : C.faint)),
              ]),
            ),
            Switch(value: on, onChanged: set, activeColor: C.onAccent, activeTrackColor: C.accent),
          ]),
        ),
      );
}
