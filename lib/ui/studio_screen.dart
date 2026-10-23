import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';
import 'video_editor.dart' show VideoPlayScreen;

/// v0.68 Hoola Video Studio: Hoola directs AI-made videos (storyboard -> free preview -> paid shots -> final video).
/// v0.157 best model per shot (Wan 3.0 / Seedance 2.5 / MiniMax H3 / Gemini Omni Flash / Sync 3 lip sync), each shot's
/// opening picture painted first (Nano Banana Pro), Hindi lines in Hoola's voice, lip-synced; the whole studio in the app.
/// Every paid step is a price card she taps; nothing is spent before it. The final video always carries the
/// "AI-generated" label, and nothing is posted anywhere by Hoola.

void _snack(BuildContext context, String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

List<Map<String, dynamic>> _list(Object? o) =>
    List<Map<String, dynamic>>.from(((o as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(Object? o) => o is Map ? Map<String, dynamic>.from(o) : <String, dynamic>{};

const _qualityLabel = {'preview': 'Free preview', 'draft': 'Draft (720p)', 'final': 'HD (1080p)', 'premium': 'Premium'};
const _kindLabel = {'scene': 'Scene', 'product': 'Product', 'talk': 'Bolna (lip sync)', 'dialogue': 'Baatcheet', 'link': 'Jodna'};
const _kindIcon = {
  'scene': Icons.movie_filter_rounded, 'product': Icons.shopping_bag_rounded, 'talk': Icons.record_voice_over_rounded,
  'dialogue': Icons.forum_rounded, 'link': Icons.swap_horiz_rounded,
};
const _modelName = {
  'or-wan-3': 'Wan 3.0', 'or-seedance-2.5': 'Seedance 2.5', 'or-minimax-h3': 'MiniMax H3', 'or-minimax-h3-max': 'MiniMax H3 Max',
  'gemini-omni-flash': 'Gemini Omni Flash', 'sync-3': 'Sync 3 lip sync', 'or-seedance-2-fast': 'Seedance 2.0 Fast',
  'or-seedance-2': 'Seedance 2.0', 'or-flux-3-video': 'FLUX 3 Video', 'nano-banana-pro': 'Nano Banana Pro',
  'offline-preview': 'Free preview', 'lyria-3.5': 'Google Lyria',
};
String _mn(Object? m) => _modelName['$m'] ?? '$m';

void _play(BuildContext context, Santosh app, String url, String title) {
  final u = app.api?.absolute(url);
  if (u != null) Navigator.of(context).push(MaterialPageRoute(builder: (_) => VideoPlayScreen(url: u, title: title)));
}

/// The price card: what will be made, what it costs (₹ and $), Haan / Mana.
class StudioApprovalCard extends StatefulWidget {
  const StudioApprovalCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<StudioApprovalCard> createState() => _StudioApprovalCardState();
}

class _StudioApprovalCardState extends State<StudioApprovalCard> {
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.studioDecide('${widget.v['id']}', yes);
      widget.v.addAll(r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  String _what(Map<String, dynamic> v) {
    switch ('${v['kind']}') {
      case 'character':
        return 'Character ki photo: ${v['name'] ?? ''}';
      case 'keyframes':
        return '${v['shots'] ?? 0} shots ki pehli tasveer (Nano Banana Pro)';
      case 'music':
        return 'Music: ${v['mood'] ?? ''} (Google Lyria)';
    }
    final extra = [
      if ((v['keyframes'] as num? ?? 0) > 0) '+ ${v['keyframes']} tasveer',
      if ((v['lipsync'] as num? ?? 0) > 0) '${v['lipsync']} lip sync',
    ];
    return '${v['shots'] ?? 0} shot · ${v['seconds'] ?? 0} sec · ${_qualityLabel['${v['quality']}'] ?? v['quality']}'
        '${extra.isEmpty ? '' : ' · ${extra.join(', ')}'}';
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? 'pending'}';
    final pending = status == 'pending';
    final usd = (v['usd'] as num?)?.toDouble() ?? 0;
    return Glass(
      margin: const EdgeInsets.symmetric(vertical: 6),
      border: pending ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.currency_rupee_rounded, color: C.warn),
          const SizedBox(width: 8),
          Expanded(child: Text('AI video ka kharcha · ${v['project'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700))),
          if (!pending)
            Pill(status == 'approved' ? 'Haan kaha' : status == 'rejected' ? 'Mana kiya' : status,
                fg: status == 'approved' ? C.ok : C.faint),
        ]),
        const SizedBox(height: 8),
        Text(_what(v), style: const TextStyle(color: C.muted)),
        const SizedBox(height: 6),
        Text('Lagbhag ₹${v['inr'] ?? ''}  (\$${usd.toStringAsFixed(2)})',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: C.ink)),
        if (v['month_left_usd'] != null)
          Text('Is mahine bacha: \$${(v['month_left_usd'] as num).toStringAsFixed(2)}', style: const TextStyle(color: C.faint, fontSize: 12)),
        if ((v['models'] as List?)?.isNotEmpty == true)
          Text('Model: ${(v['models'] as List).map(_mn).join(', ')}', style: const TextStyle(color: C.faint, fontSize: 12)),
        if ('${v['error'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 6), child: Text('${v['error']}', style: const TextStyle(color: C.bad, fontSize: 12.5))),
        if (pending) ...[
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 8),
            Expanded(child: GradientButton(height: 48, label: _busy ? '...' : 'Haan, banao', onTap: _busy ? null : () => _decide(true))),
          ]),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Asli kharcha jitna laga utna hi likha jayega (is se zyada kabhi nahi).', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        ],
      ]),
    );
  }
}

/// One project in chat, updated live: pictures, shots and their state, spend, the finished video.
class StudioCard extends StatelessWidget {
  const StudioCard({super.key, required this.v, required this.app, this.margin = const EdgeInsets.symmetric(vertical: 6)});
  final Map<String, dynamic> v;
  final Santosh app;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) => ListenableBuilder(listenable: app, builder: (context, _) => _card(context));

  Widget _card(BuildContext context) {
    final shots = _list(v['shots']);
    final outs = _list(v['outputs']);
    final last = outs.isEmpty ? null : outs.last;
    final working = v['working'] == true || v['planning'] == true;
    final pics = shots.where((s) => '${s['keyframe'] ?? ''}'.isNotEmpty).toList();
    return Glass(
      margin: margin,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.auto_awesome_motion_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['project'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
          Pill(v['planning'] == true ? 'Storyboard' : v['assembling'] == true ? 'Jod raha hoon' : working ? 'Ban raha hai' : last != null ? 'Taiyaar' : 'Storyboard',
              fg: working ? C.accent : last != null ? C.ok : C.chip),
        ]),
        const SizedBox(height: 4),
        Text('${v['aspect'] ?? ''} · ${v['style'] ?? ''} · ${v['language'] ?? ''} · ${shots.length} shots · ${v['seconds'] ?? 0}s · kharch ₹${v['spent_inr'] ?? 0}',
            style: const TextStyle(color: C.faint, fontSize: 12)),
        if (working) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator(color: C.accent, minHeight: 3)),
        if (pics.isNotEmpty) ...[
          const SizedBox(height: 8),
          SizedBox(
            height: 92,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final s in pics)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.network(app.api!.absolute('${s['keyframe']}'), height: 92, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(width: 52, color: C.panel)),
                  ),
                ),
            ]),
          ),
        ] else if (shots.isNotEmpty) ...[
          const SizedBox(height: 8),
          for (final s in shots.take(6))
            Text('${s['id']} · ${s['duration']}s · ${_kindLabel['${s['kind']}'] ?? ''} — ${s['prompt']}',
                maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.chip)),
        ],
        if (last != null) ...[
          const SizedBox(height: 8),
          _FinalVideo(app: app, project: '${v['project']}', last: last),
        ],
        const SizedBox(height: 8),
        GlassButton(label: 'Studio mein kholo', icon: Icons.open_in_new_rounded, height: 42, onTap: () {
          Navigator.of(context).push(MaterialPageRoute(builder: (_) => StudioProjectScreen(app: app, name: '${v['project']}')));
        }),
      ]),
    );
  }
}

class _FinalVideo extends StatelessWidget {
  const _FinalVideo({required this.app, required this.project, required this.last});
  final Santosh app;
  final String project;
  final Map<String, dynamic> last;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        GestureDetector(
          onTap: () => _play(context, app, '${last['url']}', project),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Stack(alignment: Alignment.center, children: [
              if ('${last['thumb'] ?? ''}'.isNotEmpty)
                Image.network(app.api!.absolute('${last['thumb']}'), height: 220, width: double.infinity, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(height: 120, color: C.panel))
              else
                Container(height: 120, width: double.infinity, color: C.panel),
              const CircleAvatar(radius: 24, backgroundColor: Color(0x99000000), child: Icon(Icons.play_arrow_rounded, color: Colors.white, size: 30)),
            ]),
          ),
        ),
        const SizedBox(height: 6),
        Text(last['preview'] == true
            ? 'Free preview (kahani aur timing). Pasand aaye to asli shots banwaiye.'
            : '${(last['seconds'] as num?)?.toStringAsFixed(0) ?? ''} sec · "AI-generated" label ke saath',
            style: const TextStyle(color: C.faint, fontSize: 12)),
        Row(children: [
          TextButton.icon(
            icon: const Icon(Icons.download_rounded, size: 18),
            label: const Text('Download'),
            onPressed: () async {
              final u = app.api?.absolute('${last['url']}');
              if (u != null) await launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication);
            },
          ),
          TextButton.icon(
            icon: const Icon(Icons.link_rounded, size: 18),
            label: const Text('Link'),
            onPressed: () {
              Clipboard.setData(ClipboardData(text: app.api?.absolute('${last['url']}') ?? ''));
              _snack(context, 'Link copy ho gaya');
            },
          ),
        ]),
      ]);
}

/// Profile > "<name> · Video Studio": projects, this month's spend, which AI models are switched on, "Naya video".
class StudioScreen extends StatefulWidget {
  const StudioScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<StudioScreen> createState() => _StudioScreenState();
}

class _StudioScreenState extends State<StudioScreen> {
  Map<String, dynamic> _home = const {};
  bool _loading = true;
  int _tick = -1;

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
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _loading = false);
  }

  void _ask(String text) {
    app.send(text);
    Navigator.of(context).popUntil((r) => r.isFirst);
    _snack(context, '${app.aName} ko bata diya; chat mein dekhiye');
  }

  Future<void> _new() async {
    final name = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (_) => _NewVideoSheet(app: app),
    );
    if (name != null && mounted) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => StudioProjectScreen(app: app, name: name)));
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final projects = _list(_home['projects']);
    final ready = List<String>.from(((_home['ready'] as List?) ?? const []).map((e) => '$e'));
    final spent = (_home['month_spent_usd'] as num?)?.toDouble() ?? 0;
    final limit = (_home['month_limit_usd'] as num?)?.toDouble() ?? 0;
    final rate = (_home['usd_inr'] as num?)?.toDouble() ?? 85;
    const ideas = [
      'Meri dukaan ki Diwali offer ki 20 sec ki reel banao, AI se',
      'Mere product ka 15 sec ka ad banao, photo main bhejti hoon',
      'Shaadi ka video invite banao, Hindi mein',
      'Good morning greeting video banao, chai aur dhoop wala',
    ];
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${app.aName} · Video Studio')),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: C.accent,
        foregroundColor: C.onAccent,
        onPressed: _new,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Naya video', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 100), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                'Bina shooting ke video. Har shot ke liye sabse achha AI model apne aap: kahani Wan 3.0, premium Seedance 2.5, '
                'product MiniMax H3, Hindi bolna Hoola ki awaaz + lip sync. Pehle har shot ki tasveer (Nano Banana Pro), phir video. '
                'Har kharche se pehle card par daam (₹) aur aapki haan. Video par "AI-generated" label hamesha.',
                style: const TextStyle(fontSize: 13, height: 1.4, color: C.muted),
              ),
              const SizedBox(height: 10),
              Text('Is mahine: ₹${(spent * rate).round()} / ₹${(limit * rate).round()}', style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(value: limit > 0 ? (spent / limit).clamp(0, 1) : 0, minHeight: 6,
                    backgroundColor: C.panel, color: C.accent),
              ),
              const SizedBox(height: 6),
              Text(ready.isEmpty ? 'AI models abhi server par chalu nahi (sirf free preview). OPENROUTER_API_KEY lagaiye.'
                  : 'Chalu: ${ready.join(', ')}', style: TextStyle(color: ready.isEmpty ? C.warn : C.faint, fontSize: 12)),
            ]),
          ),
          const SizedBox(height: 14),
          const Text('Chat se kahiye', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [for (final i in ideas) ActionChip(label: Text(i), onPressed: () => _ask(i))]),
          const SizedBox(height: 16),
          if (_loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
          if (!_loading && projects.isEmpty)
            const Text('Abhi koi project nahi. "Naya video" dabaiye ya chat mein boliye.', style: TextStyle(color: C.faint)),
          for (final p in projects) ...[
            for (final a in _list(p['approvals'])) StudioApprovalCard(key: ValueKey('ap${a['id']}'), v: a, app: app),
            StudioCard(key: ValueKey('pj${p['project']}${p['updated']}'), v: p, app: app),
          ],
        ]),
      ),
    );
  }
}

class _NewVideoSheet extends StatefulWidget {
  const _NewVideoSheet({required this.app});
  final Santosh app;
  @override
  State<_NewVideoSheet> createState() => _NewVideoSheetState();
}

class _NewVideoSheetState extends State<_NewVideoSheet> {
  final _name = TextEditingController();
  final _brief = TextEditingController();
  String _aspect = '9:16';
  String _style = 'reel';
  String _lang = 'Hindi';
  int _secs = 30;
  bool _busy = false;
  static const _styles = {
    'reel': 'Reel', 'cinematic': 'Cinematic', 'ad': 'Ad', 'indian_wedding': 'Shaadi', 'documentary': 'Documentary',
    'animation_3d': '3D cartoon', 'anime': 'Anime', 'news': 'News style',
  };
  static const _langs = ['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi'];

  Future<void> _go() async {
    if (_name.text.trim().length < 2 || _brief.text.trim().length < 8) {
      _snack(context, 'Naam aur video kis baare mein hai, dono likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      final v = await widget.app.api!.studioNew({
        'name': _name.text.trim(), 'brief': _brief.text.trim(), 'aspect': _aspect, 'style': _style, 'language': _lang,
        'seconds': _secs,
      });
      if (mounted) Navigator.pop(context, '${v['project']}');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _chips<T>(String title, Map<T, String> items, T cur, void Function(T) set) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 12),
          Caption(title),
          Wrap(spacing: 8, runSpacing: 6, children: [
            for (final e in items.entries) ChoiceChip(label: Text(e.value), selected: cur == e.key, onSelected: (_) => setState(() => set(e.key))),
          ]),
        ],
      );

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(18, 18, 18, 18 + MediaQuery.of(context).viewInsets.bottom),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Naya AI video', style: display(20)),
            const SizedBox(height: 10),
            TextField(controller: _name, decoration: const InputDecoration(labelText: 'Naam', hintText: 'Jaise: Diwali saree reel')),
            const SizedBox(height: 8),
            TextField(controller: _brief, minLines: 3, maxLines: 6,
                decoration: const InputDecoration(labelText: 'Video kis baare mein hai?',
                    hintText: 'Kya dikhana hai, kisko, kya bolna hai, kya offer / sandesh. Jitna detail, utna achha.')),
            _chips<int>('LAMBAI', const {15: '15 sec', 30: '30 sec', 60: '1 min', 120: '2 min', 300: '5 min'}, _secs, (v) => _secs = v),
            _chips<String>('SHAPE', const {'9:16': 'Reel / Short', '16:9': 'YouTube', '1:1': 'Square'}, _aspect, (v) => _aspect = v),
            _chips<String>('LOOK', _styles, _style, (v) => _style = v),
            const SizedBox(height: 12),
            const Caption('BHASHA (bolne aur captions ki)'),
            DropdownButton<String>(
              isExpanded: true,
              value: _lang,
              dropdownColor: C.bgBottom,
              items: [for (final l in _langs) DropdownMenuItem(value: l, child: Text(l))],
              onChanged: (v) => setState(() => _lang = v ?? 'Hindi'),
            ),
            const SizedBox(height: 16),
            GradientButton(label: _busy ? 'Bana raha hoon…' : 'Storyboard banao', icon: Icons.auto_awesome_rounded, onTap: _busy ? null : _go),
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Storyboard free hai. Tasveer aur video ke daam card par dikhenge, aapki haan ke baad hi banenge.',
                  textAlign: TextAlign.center, style: TextStyle(color: C.faint, fontSize: 11.5)),
            ),
          ]),
        ),
      );
}

/// One video project: storyboard with painted pictures, every shot's takes (play / pick / redo), quality, music, assemble.
class StudioProjectScreen extends StatefulWidget {
  const StudioProjectScreen({super.key, required this.app, required this.name});
  final Santosh app;
  final String name;
  @override
  State<StudioProjectScreen> createState() => _StudioProjectScreenState();
}

class _StudioProjectScreenState extends State<StudioProjectScreen> {
  Map<String, dynamic>? _v;
  String? _err;
  int _tick = -1;
  Timer? _poll;
  bool _busy = false;

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
    _poll?.cancel();
    super.dispose();
  }

  void _onApp() {
    if (app.studioTick != _tick) {
      _tick = app.studioTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final v = await app.api!.studioProject(widget.name);
      if (!mounted) return;
      setState(() {
        _v = v;
        _err = null;
      });
      _poll?.cancel();
      if (v['working'] == true || v['planning'] == true || v['assembling'] == true) _poll = Timer(const Duration(seconds: 5), _load);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f, {String ok = ''}) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted) _snack(context, '${r['say'] ?? (ok.isEmpty ? 'Ho gaya' : ok)}');
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    _load();
  }

  Future<void> _replan() async {
    final v = _v!;
    final brief = TextEditingController(text: '${v['brief'] ?? ''}');
    int secs = (v['seconds'] as num? ?? 30).clamp(15, 300).toInt();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => AlertDialog(
            title: const Text('Storyboard dobara likhein?'),
            content: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: brief, minLines: 3, maxLines: 6, decoration: const InputDecoration(labelText: 'Video kis baare mein')),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                for (final s in const [15, 30, 60, 120, 300])
                  ChoiceChip(label: Text(s < 60 ? '$s sec' : '${s ~/ 60} min'), selected: secs == s, onSelected: (_) => set(() => secs = s)),
              ]),
            ]),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Likho')),
            ],
          )),
    );
    if (ok == true) await _run(() => app.api!.studioPlan(widget.name, brief.text.trim(), secs));
  }

  Future<void> _character() async {
    final name = TextEditingController();
    final desc = TextEditingController();
    String voice = 'female';
    bool consent = false;
    final pick = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 90, maxWidth: 2000);
    if (pick == null || !mounted) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => AlertDialog(
            title: const Text('Character / product'),
            content: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(controller: name, decoration: const InputDecoration(labelText: 'Naam (jaise Meera, Saree)')),
                TextField(controller: desc, decoration: const InputDecoration(labelText: 'Kaisa dikhta hai (umar, kapde, rang)')),
                const SizedBox(height: 8),
                Wrap(spacing: 6, children: [
                  for (final v in const ['female', 'male'])
                    ChoiceChip(label: Text(v == 'female' ? 'Mahila awaaz' : 'Purush awaaz'), selected: voice == v,
                        onSelected: (_) => set(() => voice = v)),
                ]),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: consent,
                  onChanged: (v) => set(() => consent = v == true),
                  title: const Text('Is photo wale insaan ne ijazat di hai (ya yeh product / logo hai)', style: TextStyle(fontSize: 13)),
                ),
              ]),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
              FilledButton(onPressed: consent ? () => Navigator.pop(ctx, true) : null, child: const Text('Jodo')),
            ],
          )),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    await _run(() async {
      final conv = app.conversationId ?? '';
      final f = await app.api!.chatFile(conv, pick.name.isEmpty ? 'photo.jpg' : pick.name, await pick.readAsBytes());
      return app.api!.studioCharacter(widget.name, {
        'name': name.text.trim(), 'description': desc.text.trim(), 'file_ids': ['${f['file_id']}'], 'consent': true, 'voice': voice,
      });
    }, ok: 'Character jud gaya: har shot mein yahi chehra / product');
  }

  Future<void> _editShot(Map<String, dynamic> s) async {
    final prompt = TextEditingController(text: '${s['prompt'] ?? ''}');
    final line = TextEditingController(text: '${s['dialogue'] ?? ''}');
    final cap = TextEditingController(text: '${s['caption'] ?? ''}');
    String kind = '${s['kind'] ?? 'scene'}';
    int dur = (s['duration'] as num? ?? 5).toInt();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => AlertDialog(
            title: Text('Shot ${s['id']}'),
            content: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Wrap(spacing: 6, runSpacing: 4, children: [
                  for (final e in _kindLabel.entries)
                    ChoiceChip(label: Text(e.value), selected: kind == e.key, onSelected: (_) => set(() => kind = e.key)),
                ]),
                TextField(controller: prompt, minLines: 3, maxLines: 6, decoration: const InputDecoration(labelText: 'Kya dikhe')),
                TextField(controller: line, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Kya bole (optional)')),
                TextField(controller: cap, decoration: const InputDecoration(labelText: 'Caption (optional)')),
                Row(children: [
                  const Text('Lambai'),
                  Expanded(child: Slider(value: dur.clamp(2, 30).toDouble(), min: 2, max: 30, divisions: 28, label: '$dur s',
                      onChanged: (v) => set(() => dur = v.round()))),
                  Text('$dur s'),
                ]),
              ]),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
            ],
          )),
    );
    if (ok != true) return;
    await _run(() => app.api!.studioShot(widget.name, '${s['id']}', {
          'prompt': prompt.text.trim(), 'dialogue': line.text.trim(), 'caption': cap.text.trim(), 'duration': dur, 'kind': kind,
        }), ok: 'Shot badal gaya (nayi tasveer / take banwaiye)');
  }

  Future<void> _redo(Map<String, dynamic> s) async {
    final q = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: C.bgBottom,
      builder: (ctx) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(title: Text('Shot ${s['id']} dobara', style: const TextStyle(fontWeight: FontWeight.w700))),
        ListTile(leading: const Icon(Icons.image_rounded), title: const Text('Nayi pehli tasveer'), onTap: () => Navigator.pop(ctx, 'pic')),
        ListTile(leading: const Icon(Icons.play_circle_outline_rounded), title: const Text('Free preview'), onTap: () => Navigator.pop(ctx, 'preview')),
        ListTile(leading: const Icon(Icons.speed_rounded), title: const Text('Draft (720p)'), onTap: () => Navigator.pop(ctx, 'draft')),
        ListTile(leading: const Icon(Icons.hd_rounded), title: const Text('HD (1080p)'), onTap: () => Navigator.pop(ctx, 'final')),
        ListTile(leading: const Icon(Icons.diamond_rounded), title: const Text('Premium'), onTap: () => Navigator.pop(ctx, 'premium')),
        ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Shot badlo'), onTap: () => Navigator.pop(ctx, 'edit')),
      ])),
    );
    if (q == null) return;
    if (q == 'edit') return _editShot(s);
    if (q == 'pic') return _run(() => app.api!.studioKeyframes(widget.name, shots: ['${s['id']}']));
    await _run(() => app.api!.studioGenerate(widget.name, q, shots: ['${s['id']}']));
  }

  Widget _shot(Map<String, dynamic> s, String aspect) {
    final takes = _list(s['take_list']);
    final picked = s['picked'];
    final kf = '${s['keyframe'] ?? ''}';
    final portrait = aspect == '9:16' || aspect == '3:4';
    final state = '${s['state']}';
    return Glass(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          GestureDetector(
            onTap: () {
              final t = takes.where((x) => x['n'] == picked).toList();
              if (t.isNotEmpty) _play(context, app, '${t.first['url']}', 'Shot ${s['id']}');
            },
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: SizedBox(
                width: portrait ? 84 : 140,
                height: portrait ? 150 : 79,
                child: Stack(fit: StackFit.expand, children: [
                  kf.isNotEmpty
                      ? Image.network(app.api!.absolute(kf), fit: BoxFit.cover, errorBuilder: (_, __, ___) => const ColoredBox(color: C.panel))
                      : ColoredBox(color: C.panel, child: Icon(_kindIcon['${s['kind']}'] ?? Icons.movie_rounded, color: C.faint)),
                  if (takes.isNotEmpty) const Center(child: Icon(Icons.play_circle_fill_rounded, color: Colors.white70, size: 34)),
                ]),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('${s['id']}', style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(width: 6),
              Pill(_kindLabel['${s['kind']}'] ?? '${s['kind']}', fg: C.teal),
              const Spacer(),
              Text('${s['duration']}s', style: const TextStyle(color: C.faint, fontSize: 12)),
            ]),
            const SizedBox(height: 4),
            if ('${s['prompt'] ?? ''}'.isNotEmpty)
              Text('${s['prompt']}', maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.chip, height: 1.3)),
            if ('${s['dialogue'] ?? ''}'.isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text('🗣 "${s['dialogue']}"', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600))),
            if ('${s['caption'] ?? ''}'.isNotEmpty)
              Text('Caption: ${s['caption']}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
            if (state == 'working')
              Padding(padding: const EdgeInsets.only(top: 6), child: Row(children: [
                const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: C.accent)),
                const SizedBox(width: 8),
                Text('${s['stage'] ?? 'ban raha hai'}', style: const TextStyle(color: C.accent, fontSize: 12)),
              ])),
            if (s['error'] != null)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text('${s['error']}', maxLines: 3, style: const TextStyle(color: C.bad, fontSize: 11.5))),
          ])),
          IconButton(icon: const Icon(Icons.more_vert_rounded), onPressed: _busy ? null : () => _redo(s)),
        ]),
        if (takes.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final t in takes)
              InputChip(
                selected: t['n'] == picked,
                selectedColor: C.accent.withOpacity(.3),
                avatar: Icon(t['n'] == picked ? Icons.check_circle_rounded : Icons.play_arrow_rounded, size: 18),
                label: Text('#${t['n']} ${_qualityLabel['${t['quality']}']?.split(' ').first ?? ''}'
                    '${t['score'] != null ? ' · ${t['score']}/10' : ''}${t['lipsync'] == true ? ' · lip sync' : ''}'),
                onPressed: () => _play(context, app, '${t['url']}', 'Shot ${s['id']} · take ${t['n']} · ${_mn(t['model'])}'),
                onDeleted: t['n'] == picked ? null : () => _run(() => app.api!.studioPick(widget.name, '${s['id']}', (t['n'] as num).toInt()),
                    ok: 'Take ${t['n']} chuna'),
                deleteIcon: const Icon(Icons.done_rounded, size: 16),
                deleteButtonTooltipMessage: 'Yahi lo',
              ),
          ]),
          for (final t in takes.where((x) => x['n'] == picked && ((x['problems'] as List?)?.isNotEmpty ?? false)))
            Text('Jaanch: ${(t['problems'] as List).join(', ')}', style: const TextStyle(color: C.warn, fontSize: 11.5)),
        ],
      ]),
    );
  }

  Widget _tier(String q, Map<String, dynamic> est) {
    final e = _map(est[q]);
    final models = List<String>.from(((e['models'] as List?) ?? const []).map((x) => _mn(x)));
    return Expanded(
      child: Press(
        onTap: _busy ? null : () => _run(() => app.api!.studioGenerate(widget.name, q)),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: q == 'final' ? C.accent.withOpacity(.18) : C.panel,
            border: Border.all(color: q == 'final' ? C.accent : const Color(0x22FFFFFF)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_qualityLabel[q] ?? q, style: const TextStyle(fontWeight: FontWeight.w800)),
            Text(e.isEmpty ? '—' : '~₹${e['inr']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: C.accentSoft)),
            Text(models.take(3).join(', '), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 10.5)),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(widget.name), actions: [
        IconButton(tooltip: 'Storyboard dobara', icon: const Icon(Icons.auto_fix_high_rounded), onPressed: v == null || _busy ? null : _replan),
      ]),
      body: v == null
          ? Center(child: _err != null ? Padding(padding: const EdgeInsets.all(24), child: Text(_err!, style: const TextStyle(color: C.bad)))
              : const CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(14, 4, 14, 40), children: _body(v)),
            ),
    );
  }

  List<Widget> _body(Map<String, dynamic> v) {
    final shots = _list(v['shots']);
    final outs = _list(v['outputs']);
    final est = _map(v['estimates']);
    final chars = _list(v['character_list']);
    final aspect = '${v['aspect']}';
    final allPics = shots.isNotEmpty && shots.every((s) => '${s['keyframe'] ?? ''}'.isNotEmpty);
    final allTakes = shots.isNotEmpty && shots.every((s) => s['picked'] != null);
    return [
      Text('${v['brief'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 13, height: 1.35)),
      const SizedBox(height: 4),
      Text('$aspect · ${v['style']} · ${v['language']} · ${shots.length} shots · ${v['seconds'] ?? 0}s · kharch ₹${v['spent_inr'] ?? 0}',
          style: const TextStyle(color: C.faint, fontSize: 12)),
      if (v['planning'] == true)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Row(children: [
            SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.accent)),
            SizedBox(width: 10),
            Expanded(child: Text('Storyboard likh raha hoon: har shot ka drishya, camera, bolna aur caption…', style: TextStyle(color: C.muted))),
          ]),
        ),
      const SizedBox(height: 10),
      Wrap(spacing: 6, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
        for (final c in chars) Chip(avatar: const Icon(Icons.person_rounded, size: 16), label: Text('${c['name']}')),
        ActionChip(avatar: const Icon(Icons.add_a_photo_rounded, size: 16), label: const Text('Character / product photo'),
            onPressed: _busy ? null : _character),
      ]),
      for (final a in _list(v['approvals'])) StudioApprovalCard(key: ValueKey('ap${a['id']}'), v: a, app: app),
      if (shots.isNotEmpty) ...[
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: GlassButton(label: allPics ? 'Tasveerein dobara' : '1. Tasveerein banao', icon: Icons.image_rounded, height: 44,
              onTap: _busy ? null : () => _run(() => app.api!.studioKeyframes(widget.name)))),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: '2. Free preview', icon: Icons.slideshow_rounded, height: 44,
              onTap: _busy ? null : () => _run(() => app.api!.studioGenerate(widget.name, 'preview')))),
        ]),
        const SizedBox(height: 10),
        const Caption('3. ASLI VIDEO (card par daam, aapki haan ke baad)'),
        Row(children: [_tier('draft', est), const SizedBox(width: 8), _tier('final', est), const SizedBox(width: 8), _tier('premium', est)]),
        const SizedBox(height: 14),
        Caption('STORYBOARD · ${shots.length} SHOTS'),
        for (final s in shots) _shot(s, aspect),
        const SizedBox(height: 6),
        const Caption('4. MUSIC'),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final m in const {'upbeat': 'Josh', 'calm': 'Shaant', 'festive': 'Tyohar', 'cinematic': 'Cinematic', 'corporate': 'Office', 'lofi': 'Lo-fi'}.entries)
            ActionChip(label: Text(m.value), onPressed: _busy ? null : () => _run(() => app.api!.studioMusic(widget.name, m.key))),
        ]),
        if (v['music'] == true) const Text('✓ Music laga hai', style: TextStyle(color: C.ok, fontSize: 12)),
        const SizedBox(height: 12),
        GradientButton(
          label: v['assembling'] == true ? 'Jod raha hoon…' : '5. Final video jodo',
          icon: Icons.movie_creation_rounded,
          onTap: !allTakes || _busy || v['assembling'] == true ? null : () => _run(() => app.api!.studioAssemble(widget.name)),
        ),
        if (!allTakes)
          const Padding(padding: EdgeInsets.only(top: 6), child: Text('Har shot ka kam se kam ek take chahiye (free preview bhi chalega).',
              textAlign: TextAlign.center, style: TextStyle(color: C.faint, fontSize: 11.5))),
      ],
      if (outs.isNotEmpty) ...[
        const SizedBox(height: 16),
        const Caption('FINAL VIDEO'),
        _FinalVideo(app: app, project: widget.name, last: outs.last),
      ],
    ];
  }
}
