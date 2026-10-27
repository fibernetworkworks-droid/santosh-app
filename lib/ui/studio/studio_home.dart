import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_approve.dart';
import 'studio_kit.dart';
import 'studio_new.dart';
import 'studio_project.dart';

/// v0.159 Screen 1 · Studio home: one box to start (type or speak the idea), one-tap starters, her projects with a
/// poster, where each one stands and the next step with its price. The month's spend sits in a small ring.
class StudioScreen extends StatefulWidget {
  const StudioScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<StudioScreen> createState() => _StudioScreenState();
}

class Starter {
  const Starter(this.title, this.sub, this.tone, this.icon, this.idea, this.seconds, this.style, this.aspect);
  final String title;
  final String sub;
  final Color tone;
  final IconData icon;
  final String idea;
  final int seconds;
  final String style;
  final String aspect;
}

const starters = [
  Starter('Diwali offer reel', '20 sec · dukaan', Color(0xFF3A1D0E), Icons.local_fire_department_rounded,
      'Meri dukaan ki Diwali offer reel: diye, rangoli, khush graahak, ant mein offer aur dukaan ka naam.', 20, 'ad', '9:16'),
  Starter('Product ad', '15 sec · photo se', Color(0xFF10283A), Icons.inventory_2_rounded,
      'Mere product ka 15 second ka ad: product chamakti roshni mein ghoomta hai, istemaal hota dikhe, ant mein naam.', 15, 'ad', '9:16'),
  Starter('Shaadi invite', '30 sec · Hindi', Color(0xFF3B1230), Icons.favorite_rounded,
      'Shaadi ka video invite: phoolon se saja mandap, dulha dulhan ke naam, tareekh aur jagah, pyaar bhara sandesh.', 30, 'indian_wedding', '9:16'),
  Starter('Good morning', '10 sec · chai', Color(0xFF2F2A10), Icons.wb_sunny_rounded,
      'Good morning greeting: subah ki dhoop, garam chai ka cup, pakshi, ek pyaari si shubhkamna.', 10, 'reel', '9:16'),
];

class _StudioScreenState extends State<StudioScreen> {
  Map<String, dynamic> _home = const {};
  bool _loading = true;
  bool _busy = false;
  int _tick = -1;
  final _idea = TextEditingController();
  final SpeechToText _stt = SpeechToText();
  bool _listening = false;
  int _secs = 30;
  String _aspect = '9:16';
  String _style = 'cinematic';
  String _lang = 'Hindi';

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _idea.dispose();
    _stt.stop();
    super.dispose();
  }

  void _onApp() {
    if (app.studioTick != _tick) {
      _tick = app.studioTick;
      _load();
    }
  }

  Future<void> _load() async {
    if (app.api == null) return;
    try {
      final r = await app.api!.studioHome();
      if (mounted) setState(() => _home = r);
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
    if (mounted) setState(() => _loading = false);
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
    final before = _idea.text.trim();
    setState(() => _listening = true);
    await _stt.listen(
      localeId: app.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 60),
      pauseFor: const Duration(seconds: 4),
      partialResults: true,
      onResult: (r) => setState(() => _idea.text = before.isEmpty ? r.recognizedWords : '$before ${r.recognizedWords}'),
    );
  }

  String _nameFrom(String idea) {
    final w = idea.replaceAll(RegExp(r'[^\w\sऀ-෿]'), ' ').split(RegExp(r'\s+')).where((x) => x.isNotEmpty).take(5).join(' ');
    final n = w.length > 36 ? w.substring(0, 36) : w;
    return n.length < 2 ? 'Naya video' : n[0].toUpperCase() + n.substring(1);
  }

  Future<void> _quick() async {
    final idea = _idea.text.trim();
    if (idea.length < 8) {
      studioSnack(context, 'Thoda aur likhiye: kya dikhana hai, kisko, kya kehna hai.');
      return;
    }
    setState(() => _busy = true);
    try {
      var name = _nameFrom(idea);
      Map<String, dynamic>? v;
      for (var i = 0; i < 3 && v == null; i++) {
        try {
          v = await app.api!.studioNew({
            'name': name, 'brief': idea, 'aspect': _aspect, 'style': _style, 'language': _lang, 'seconds': _secs,
            'voice': app.aFemale ? 'female' : 'male', 'captions': true, 'caption_style': 'bold',
            'music': '', 'quality': 'final',
          });
        } catch (e) {
          if (!'$e'.contains('already exists')) rethrow;
          name = '${_nameFrom(idea)} ${i + 2}';
        }
      }
      _idea.clear();
      if (mounted && v != null) await _open('${v['project']}');
    } catch (e) {
      if (mounted) studioSnack(context, '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _open(String name) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => StudioProjectScreen(app: app, name: name)));
    _load();
  }

  Future<void> _full({Starter? s}) async {
    final name = await Navigator.of(context).push<String>(MaterialPageRoute(
        builder: (_) => NewVideoScreen(app: app, idea: s?.idea ?? _idea.text.trim(), seconds: s?.seconds ?? _secs,
            style: s?.style ?? _style, aspect: s?.aspect ?? _aspect, language: _lang)));
    if (name != null && mounted) {
      _idea.clear();
      await _open(name);
    }
  }

  Future<void> _hide(Map<String, dynamic> p) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: SC.card,
        title: Text('"${p['project']}" hatayein?', style: sora(17)),
        content: Text('List se hat jayega. Is mahine ka kharcha hisaab mein rahega.', style: body(13.5, color: C.muted)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hatao', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await app.api!.studioHide('${p['project']}');
      _load();
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final projects = sList(_home['projects']);
    final rate = (_home['usd_inr'] as num?)?.toDouble() ?? 85;
    final spent = ((_home['month_spent_usd'] as num?)?.toDouble() ?? 0) * rate;
    final limit = ((_home['month_limit_usd'] as num?)?.toDouble() ?? 0) * rate;
    final ready = List<String>.from(((_home['ready'] as List?) ?? const []).map((e) => '$e'));
    return Scaffold(
      backgroundColor: SC.bg,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.only(bottom: 28), children: [
            _header(spent, limit),
            _create(),
            const SizedBox(height: 26),
            Padding(padding: const EdgeInsets.symmetric(horizontal: 20), child: SHead('Ek tap mein shuru', trailing: 'idea ke saath khulega')),
            SizedBox(
              height: 214,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 20),
                itemCount: starters.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (_, i) => _starter(starters[i]),
              ),
            ),
            const SizedBox(height: 18),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                SHead('Aapke projects', trailing: projects.isEmpty ? null : '${projects.length}'),
                if (_loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
                if (!_loading && projects.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(20), border: Border.all(color: SC.line2)),
                    child: Text('Abhi koi video nahi. Upar idea likhiye ya ek starter chuniye: storyboard free banta hai.',
                        style: body(13.5, color: C.muted, height: 1.45)),
                  ),
                for (final p in projects) ...[
                  for (final a in sList(p['approvals'])) StudioApprovalCard(key: ValueKey('ap${a['id']}'), v: a, app: app),
                  ProjectTile(app: app, v: p, onTap: () => _open('${p['project']}'), onLong: () => _hide(p)),
                  const SizedBox(height: 10),
                ],
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), border: Border.all(color: SC.line2)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Har shot ke liye sabse achha model, apne aap', style: body(12, w: FontWeight.w700, color: C.chip)),
                    const SizedBox(height: 6),
                    Text(
                        'Kahani Wan 3.0 · Premium Seedance 2.5 · Product MiniMax H3 · Bolna Sync 3 lip sync · Tasveer Nano Banana Pro. '
                        'Har video par "AI-generated · Hoola" label.${ready.isEmpty ? '\nAbhi server par sirf free preview chalu hai (OPENROUTER_API_KEY lagaiye).' : ''}',
                        style: body(11.5, color: C.faint, height: 1.45)),
                  ]),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _header(double spent, double limit) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 8, 16, 10),
        child: Row(children: [
          IconButton(onPressed: () => Navigator.maybePop(context), icon: const Icon(Icons.chevron_left_rounded, size: 30)),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Video Studio', style: sora(22, w: FontWeight.w700)),
              Text('${app.aName} ka AI film set', style: body(12.5, color: C.faint)),
            ]),
          ),
          Press(
            onTap: () => studioSnack(context, 'Is mahine ${rupees(spent)} laga, seema ${rupees(limit)}.'),
            child: Container(
              padding: const EdgeInsets.fromLTRB(8, 6, 12, 6),
              decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(999), border: Border.all(color: SC.line)),
              child: Row(children: [
                SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(value: limit <= 0 ? 0 : (spent / limit).clamp(0, 1).toDouble(), strokeWidth: 4,
                      backgroundColor: Colors.white12, color: C.accent),
                ),
                const SizedBox(width: 8),
                Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(rupees(spent), style: body(13, w: FontWeight.w800)),
                  Text('/ ${rupees(limit)}', style: body(10.5, color: C.faint)),
                ]),
              ]),
            ),
          ),
        ]),
      );

  Widget _create() => Container(
        margin: const EdgeInsets.symmetric(horizontal: 16),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(24), border: Border.all(color: SC.line)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text('Kya video banana hai?', style: sora(17))),
            const Tag('Storyboard free', fg: C.ok, size: 11),
          ]),
          const SizedBox(height: 14),
          TextField(
            controller: _idea,
            minLines: 3,
            maxLines: 6,
            style: body(14.5, w: FontWeight.w500, height: 1.45),
            decoration: InputDecoration(
              hintText: 'Jaise: Gautam Buddha ki 30 sec ki cinematic reel, Marathi mein ek shaant sandesh ke saath…',
              hintStyle: body(14, w: FontWeight.w500, color: C.faint, height: 1.45),
              filled: true,
              fillColor: SC.field,
              contentPadding: const EdgeInsets.all(14),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: SC.line2)),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: C.accent)),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            SChip(label: _secs < 60 ? '$_secs sec' : '${_secs ~/ 60} min', icon: Icons.timer_outlined, on: false, onTap: () async {
              final v = await pickOne<int>(context, 'Lambai', const {15: '15 sec', 30: '30 sec', 60: '1 min', 120: '2 min', 300: '5 min'},
                  current: _secs);
              if (v != null) setState(() => _secs = v);
            }),
            SChip(label: _aspect, icon: Icons.crop_portrait_rounded, on: false, onTap: () async {
              final v = await pickOne<String>(context, 'Shape', const {'9:16': '9:16 Reel / Short', '16:9': '16:9 YouTube', '1:1': '1:1 Post'},
                  current: _aspect);
              if (v != null) setState(() => _aspect = v);
            }),
            SChip(label: styleLabel[_style] ?? _style, on: false, onTap: () async {
              final v = await pickOne<String>(context, 'Look', styleLabel, current: _style);
              if (v != null) setState(() => _style = v);
            }),
            SChip(label: langShown(_lang), on: false, onTap: () async {
              final v = await pickOne<String>(context, 'Bhasha', {for (final l in langs) l[0]: l[1]}, current: _lang);
              if (v != null) setState(() => _lang = v);
            }),
          ]),
          const SizedBox(height: 14),
          Row(children: [
            _square(_listening ? Icons.stop_rounded : Icons.mic_rounded, 'Bolkar bataiye', _mic, on: _listening),
            const SizedBox(width: 10),
            _square(Icons.add_photo_alternate_rounded, 'Photo ke saath', () => _full()),
            const SizedBox(width: 10),
            Expanded(child: SButton(label: 'Storyboard banao', icon: Icons.auto_awesome_rounded, busy: _busy, onTap: _quick)),
          ]),
          const SizedBox(height: 10),
          Center(
            child: TextButton(
              onPressed: () => _full(),
              child: Text('Poori settings ke saath shuru karein', style: body(12.5, color: C.muted)),
            ),
          ),
        ]),
      );

  Widget _square(IconData icon, String tip, VoidCallback onTap, {bool on = false}) => Tooltip(
        message: tip,
        child: Press(
          onTap: onTap,
          child: Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: on ? C.accent.withOpacity(.18) : SC.card2,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: on ? C.accent : SC.line2),
            ),
            child: Icon(icon, color: on ? C.accent : C.ink),
          ),
        ),
      );

  Widget _starter(Starter s) => Press(
        onTap: () => _full(s: s),
        child: SizedBox(
          width: 116,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 116,
              height: 156,
              decoration: BoxDecoration(color: s.tone, borderRadius: BorderRadius.circular(16)),
              child: Stack(children: [
                Positioned(
                  right: -14,
                  bottom: -14,
                  child: Icon(s.icon, size: 92, color: Colors.white.withOpacity(.10)),
                ),
                Center(child: Icon(s.icon, size: 40, color: C.accentSoft)),
              ]),
            ),
            const SizedBox(height: 8),
            Text(s.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: body(13, w: FontWeight.w700)),
            Text(s.sub, maxLines: 1, style: body(11.5, color: C.faint)),
          ]),
        ),
      );
}

/// Where a project stands, for its poster card: status label, colour and the 4-step bar.
({String label, Color color, int steps}) projectStatus(Map<String, dynamic> v) {
  final shots = sList(v['shots']);
  final outs = sList(v['outputs']);
  final prog = sMap(v['progress']);
  final phase = '${v['phase'] ?? ''}';
  var steps = 0;
  if (shots.isNotEmpty) steps = 1;
  if (shots.isNotEmpty && shots.every((s) => '${s['keyframe']}'.isNotEmpty)) steps = 2;
  if (shots.isNotEmpty && shots.every((s) => s['picked'] != null && s['quality'] != 'preview')) steps = 3;
  if (outs.isNotEmpty && outs.last['preview'] != true) steps = 4;
  switch (phase) {
    case 'planning':
      return (label: 'Storyboard likh raha', color: C.accent, steps: steps);
    case 'painting':
      return (label: 'Tasveerein ban rahi', color: const Color(0xFF7FB2FF), steps: steps);
    case 'working':
      return (label: 'Ban raha ${prog['done'] ?? 0}/${prog['total'] ?? shots.length}', color: const Color(0xFF7FB2FF), steps: steps);
    case 'reviewing':
      return (label: 'AI jaanch', color: const Color(0xFF7FB2FF), steps: steps);
    case 'assembling':
      return (label: 'Jod raha hoon', color: const Color(0xFF7FB2FF), steps: steps);
    case 'ready':
      return (label: 'Taiyaar', color: C.ok, steps: steps);
    case 'empty':
      return (label: 'Khaali', color: C.faint, steps: steps);
  }
  return (label: 'Storyboard taiyaar', color: C.accent, steps: steps);
}

String posterOf(Map<String, dynamic> v) {
  final outs = sList(v['outputs']);
  if (outs.isNotEmpty && '${outs.last['thumb'] ?? ''}'.isNotEmpty) return '${outs.last['thumb']}';
  for (final s in sList(v['shots'])) {
    if ('${s['keyframe'] ?? ''}'.isNotEmpty) return '${s['keyframe']}';
  }
  return '';
}

/// One project as a poster card (home list and chat).
class ProjectTile extends StatelessWidget {
  const ProjectTile({super.key, required this.app, required this.v, this.onTap, this.onLong});
  final Santosh app;
  final Map<String, dynamic> v;
  final VoidCallback? onTap;
  final VoidCallback? onLong;

  @override
  Widget build(BuildContext context) {
    final st = projectStatus(v);
    final shots = sList(v['shots']);
    final nxt = sMap(v['next']);
    final prog = sMap(v['progress']);
    final working = '${v['phase']}' == 'working';
    final poster = posterOf(v);
    final ready = '${v['phase']}' == 'ready';
    return GestureDetector(
      onLongPress: onLong,
      child: Press(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: SC.card, borderRadius: BorderRadius.circular(20), border: Border.all(color: SC.line)),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(
              width: 72,
              height: 112,
              child: Stack(fit: StackFit.expand, children: [
                SImage(app: app, url: poster, tone: toneOf('${v['project']}'), icon: Icons.movie_filter_rounded),
                if (ready)
                  Center(
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xB30B0A1A)),
                      child: const Icon(Icons.play_arrow_rounded, color: C.ink, size: 20),
                    ),
                  ),
                if (working)
                  Positioned(
                    left: 0,
                    right: 0,
                    bottom: 0,
                    child: ClipRRect(
                      borderRadius: const BorderRadius.vertical(bottom: Radius.circular(12)),
                      child: LinearProgressIndicator(value: sInt(prog['pct']) / 100, minHeight: 4, backgroundColor: Colors.white24, color: C.accent),
                    ),
                  ),
              ]),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${v['project']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: sora(15.5))),
                  const SizedBox(width: 6),
                  Tag(st.label, fg: st.color, size: 11),
                ]),
                const SizedBox(height: 5),
                Text('${v['aspect']} · ${styleLabel['${v['style']}'] ?? v['style']} · ${langShown('${v['language']}')}'
                    '${shots.isEmpty ? '' : ' · ${shots.length} shots · ${v['seconds'] ?? 0}s'}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: body(12, color: C.faint)),
                const SizedBox(height: 10),
                Row(children: [
                  for (var i = 0; i < 4; i++) ...[
                    Expanded(
                      child: Container(height: 4, decoration: BoxDecoration(
                          color: i < st.steps ? C.accent : Colors.white12, borderRadius: BorderRadius.circular(2))),
                    ),
                    if (i < 3) const SizedBox(width: 4),
                  ],
                ]),
                const SizedBox(height: 5),
                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  for (final t in const ['Storyboard', 'Tasveer', 'Video', 'Final']) Text(t, style: body(10, color: C.faint)),
                ]),
                const SizedBox(height: 8),
                Text(
                  working
                      ? 'Kharch ${rupees(prog['spent_inr'])} / ${rupees(prog['inr'])}'
                      : ready
                          ? 'Kharch ${rupees(v['spent_inr'])}'
                          : 'Agla kadam: ${nxt['label'] ?? ''}${sInt(nxt['inr']) > 0 ? ' · ${rupees(nxt['inr'])}' : ''}',
                  style: body(12.5, w: FontWeight.w700),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

/// The live project card in chat / calls (updated in place by `studio` events).
class StudioCard extends StatelessWidget {
  const StudioCard({super.key, required this.v, required this.app, this.margin = const EdgeInsets.symmetric(vertical: 6)});
  final Map<String, dynamic> v;
  final Santosh app;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => Padding(
          padding: margin,
          child: ProjectTile(
            app: app,
            v: v,
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => StudioProjectScreen(app: app, name: '${v['project']}'))),
          ),
        ),
      );
}
