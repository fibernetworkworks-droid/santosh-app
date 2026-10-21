import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';
import 'video_editor.dart' show VideoPlayScreen;

/// v0.68 Hoola Video Studio: Hoola directs AI-made videos (storyboard -> free preview -> paid shots -> final video).
/// Every paid step is a price card she taps; nothing is spent before it. The final video always carries the
/// "AI-generated" label, and nothing is posted anywhere by Hoola.

void _snack(BuildContext context, String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

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

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? 'pending'}';
    final pending = status == 'pending';
    final what = v['kind'] == 'character'
        ? 'Character ki photo: ${v['name'] ?? ''}'
        : '${v['shots'] ?? 0} shot · ${v['seconds'] ?? 0} sec · ${v['quality'] == 'final' ? 'Final (1080p)' : 'Draft (480p)'}';
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
        Text(what, style: const TextStyle(color: C.muted)),
        const SizedBox(height: 6),
        Text('Lagbhag ₹${v['inr'] ?? ''}  (\$${usd.toStringAsFixed(2)})',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: C.ink)),
        if (v['month_left_usd'] != null)
          Text('Is mahine bacha: \$${(v['month_left_usd'] as num).toStringAsFixed(2)}', style: const TextStyle(color: C.faint, fontSize: 12)),
        if ((v['models'] as List?)?.isNotEmpty == true)
          Text('Model: ${(v['models'] as List).join(', ')}', style: const TextStyle(color: C.faint, fontSize: 12)),
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

/// One project, updated live: shots and their state, spend, the finished video.
class StudioCard extends StatelessWidget {
  const StudioCard({super.key, required this.v, required this.app, this.margin = const EdgeInsets.symmetric(vertical: 6)});
  final Map<String, dynamic> v;
  final Santosh app;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) => ListenableBuilder(listenable: app, builder: (context, _) => _card(context));

  Widget _card(BuildContext context) {
    final shots = List<Map<String, dynamic>>.from(((v['shots'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final outs = List<Map<String, dynamic>>.from(((v['outputs'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final last = outs.isEmpty ? null : outs.last;
    final working = v['working'] == true;
    return Glass(
      margin: margin,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.auto_awesome_motion_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['project'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
          Pill(v['assembling'] == true ? 'Jod raha hoon' : working ? 'Ban raha hai' : last != null ? 'Taiyaar' : 'Storyboard',
              fg: working ? C.accent : last != null ? C.ok : C.chip),
        ]),
        const SizedBox(height: 4),
        Text('${v['aspect'] ?? ''} · ${v['style'] ?? ''} · ${v['language'] ?? ''} · kharch ₹${v['spent_inr'] ?? 0}',
            style: const TextStyle(color: C.faint, fontSize: 12)),
        if (working) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator(color: C.accent, minHeight: 3)),
        if (shots.isNotEmpty) ...[
          const SizedBox(height: 8),
          for (final s in shots)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(
                    switch ('${s['state']}') {
                      'done' => Icons.check_circle_rounded,
                      'working' => Icons.hourglass_top_rounded,
                      'failed' => Icons.error_rounded,
                      _ => Icons.radio_button_unchecked_rounded,
                    },
                    size: 16,
                    color: s['state'] == 'failed' ? C.bad : s['state'] == 'done' ? C.ok : C.faint),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                      '${s['id']} · ${s['duration']}s${s['quality'] != null ? ' · ${s['quality']}' : ''} — ${s['prompt']}'
                      '${s['error'] != null ? '\n${s['error']}' : ''}',
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 12.5, color: s['error'] != null ? C.bad : C.chip)),
                ),
              ]),
            ),
        ],
        if (last != null) ...[
          const SizedBox(height: 8),
          GestureDetector(
            onTap: () {
              final u = app.api?.absolute('${last['url']}');
              if (u != null) Navigator.of(context).push(MaterialPageRoute(builder: (_) => VideoPlayScreen(url: u, title: '${v['project']}')));
            },
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Stack(alignment: Alignment.center, children: [
                if ('${last['thumb'] ?? ''}'.isNotEmpty)
                  Image.network(app.api!.absolute('${last['thumb']}'), height: 220, fit: BoxFit.cover,
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
        ],
      ]),
    );
  }
}

/// Profile > "<name> · Video Studio": projects, this month's spend, which AI models are switched on.
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

  @override
  Widget build(BuildContext context) {
    final projects = List<Map<String, dynamic>>.from(((_home['projects'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
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
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
          Glass(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                'Bina shooting ke video: aap bataiye kya chahiye, ${app.aName} kahani (storyboard) likhta hai, pehle FREE preview '
                'dikhata hai, phir Seedance / Veo / Kling jaise AI models se asli shots. Har kharche se pehle card par daam '
                '(₹) aur aapki haan. Aapke chehre / photo sirf ijazat se; video par "AI-generated" label hamesha.',
                style: const TextStyle(fontSize: 13, height: 1.4, color: C.muted),
              ),
              const SizedBox(height: 10),
              Text('Is mahine: ₹${(spent * rate).round()} / ₹${(limit * rate).round()}',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
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
          const Text('Naya video', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [for (final i in ideas) ActionChip(label: Text(i), onPressed: () => _ask(i))]),
          const SizedBox(height: 16),
          if (_loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
          if (!_loading && projects.isEmpty)
            const Text('Abhi koi project nahi. Upar se ek chuniye ya chat mein boliye.', style: TextStyle(color: C.faint)),
          for (final p in projects) ...[
            for (final a in List<Map<String, dynamic>>.from(((p['approvals'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map))))
              StudioApprovalCard(key: ValueKey('ap${a['id']}'), v: a, app: app),
            StudioCard(key: ValueKey('pj${p['project']}${p['updated']}'), v: p, app: app),
          ],
        ]),
      ),
    );
  }
}
