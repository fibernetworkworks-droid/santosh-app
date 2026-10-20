import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../api.dart';
import '../native.dart';
import 'glass.dart';
import 'tv_screen.dart' show HoolaTv;

/// Sends the phone's reel-app times (Android Usage Access) to Hoola now and then, so the avatar can answer
/// "aaj kitni reels dekhi?" too. Numbers only; never what was on the screen.
class ScrollSync {
  static DateTime? _last;

  static Future<void> maybe({bool force = false}) async {
    final api = HoolaTv.api;
    if (api == null) return;
    if (!force && _last != null && DateTime.now().difference(_last!) < const Duration(minutes: 30)) return;
    try {
      if (!await Native.usageAllowed()) return;
      final days = await Native.usageDays(days: 7);
      _last = DateTime.now();
      if (days.isNotEmpty) await api.scrollSync(days);
    } catch (_) {}
  }
}

/// Reel scroll report: time in Instagram / YouTube / Facebook / Snapchat / Moj / Josh / ShareChat, the week, the hours,
/// late night, longest sitting, a daily limit, and what you watch (from your own history download).
class ScrollScreen extends StatefulWidget {
  const ScrollScreen({super.key});
  @override
  State<ScrollScreen> createState() => _ScrollScreenState();
}

class _ScrollScreenState extends State<ScrollScreen> with WidgetsBindingObserver {
  bool? _allowed;
  Map<String, dynamic>? _r;
  String? _err;
  bool _importing = false;
  int _days = 7;

  Api? get _api => HoolaTv.api;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) _load(); // back from Settings > Usage access
  }

  Future<void> _load() async {
    final api = _api;
    if (api == null) return;
    final ok = await Native.usageAllowed();
    if (mounted) setState(() => _allowed = ok);
    try {
      if (ok) await ScrollSync.maybe(force: true);
      final r = await api.scrollReport(days: _days);
      if (mounted) {
        setState(() {
          _r = r;
          _err = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = e is ApiException ? e.message : '$e');
    }
  }

  Future<void> _budget(int m) async {
    try {
      await _api!.scrollBudget(m);
      await _load();
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    }
  }

  Future<void> _import() async {
    final res = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: const ['zip', 'json', 'html']);
    final f = res?.files.single;
    if (f?.path == null) return;
    setState(() => _importing = true);
    try {
      final bytes = await File(f!.path!).readAsBytes();
      final r = await _api!.scrollImport(f.name, bytes);
      _snack('${r['note'] ?? 'History padh li'}');
      await _load();
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }

  Future<void> _forget() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Scroll data mitayein?'),
        content: const Text('Hoola ke paas rakha saara scroll time, limit aur history ka saar mit jayega.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Mitao', style: TextStyle(color: C.bad))),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await _api!.scrollForget();
      _snack('Mita diya');
      await _load();
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    }
  }

  void _snack(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  static String hm(num mins) {
    final m = mins.round();
    if (m < 60) return '$m min';
    return m % 60 == 0 ? '${m ~/ 60} ghante' : '${m ~/ 60}h ${m % 60}m';
  }

  static const _appColors = {
    'Instagram': Color(0xFFE1306C), 'YouTube': Color(0xFFFF4B4B), 'Facebook': Color(0xFF4A86F7), 'Snapchat': Color(0xFFFFE15A),
    'Moj': Color(0xFFFFA43A), 'Josh': Color(0xFF8B5CF6), 'ShareChat': Color(0xFF22C55E), 'TikTok': Color(0xFF2DD4BF),
  };

  // ---------------------------------------------------------------- pieces
  Widget _card(Widget child, {EdgeInsets pad = const EdgeInsets.all(16)}) =>
      Padding(padding: const EdgeInsets.only(bottom: 12), child: Glass(radius: 20, padding: pad, child: child));

  Widget _onboarding() => _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.insights_rounded, color: C.accent, size: 26),
          SizedBox(width: 10),
          Expanded(child: Text('Apni reel ki aadat dekhiye', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17))),
        ]),
        const SizedBox(height: 10),
        const Text(
            'Android ki "Usage access" chalu kijiye. Hoola sirf itna dekhega ki Instagram, YouTube, Facebook, Snapchat, Moj, '
            'Josh, ShareChat kitni der khule rahe. Screen pe kya tha, woh kabhi nahi.',
            style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.4)),
        const SizedBox(height: 12),
        const Text('Settings khulegi → Hoola chuniye → "Allow usage access" on kijiye → wapas aaiye.',
            style: TextStyle(color: C.faint, fontSize: 12.5)),
        const SizedBox(height: 14),
        GradientButton(label: 'Usage access chalu karo', icon: Icons.toggle_on_rounded, onTap: Native.usageSettings),
      ]));

  Widget _week(Map<String, dynamic> r) {
    final daily = List<Map<String, dynamic>>.from((r['daily'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
    final budget = (r['budget_min'] as num? ?? 0).toDouble();
    final top = [...daily.map((d) => (d['min'] as num).toDouble()), budget, 30.0].reduce((a, b) => a > b ? a : b);
    const names = ['Som', 'Mangal', 'Budh', 'Guru', 'Shukra', 'Shani', 'Ravi'];
    final trend = r['trend_pct'] as num?;
    return _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(hm(r['total_min'] as num), style: display(30, w: FontWeight.w800)),
            Text('${r['period_days']} din mein · roz ~${hm(r['avg_min'] as num)} · ~${r['reels_est']} reels',
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ]),
        ),
        if (trend != null)
          Pill('${trend > 0 ? '▲' : '▼'} ${trend.abs()}%', fg: trend > 0 ? C.bad : C.ok, bg: (trend > 0 ? C.bad : C.ok).withOpacity(.14)),
      ]),
      const SizedBox(height: 18),
      SizedBox(
        height: 140,
        child: LayoutBuilder(builder: (ctx, box) {
          final h = box.maxHeight - 22;
          return Stack(children: [
            if (budget > 0)
              Positioned(
                left: 0,
                right: 0,
                bottom: 22 + h * budget / top,
                child: Row(children: [
                  Expanded(child: Container(height: 1.2, color: C.warn.withOpacity(.7))),
                  Text(' limit ${hm(budget)}', style: const TextStyle(color: C.warn, fontSize: 10)),
                ]),
              ),
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              for (final d in daily)
                Expanded(
                  child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                    Tooltip(
                      message: hm(d['min'] as num),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 500),
                        margin: const EdgeInsets.symmetric(horizontal: 5),
                        height: ((d['min'] as num).toDouble() / top * h).clamp(3.0, h),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(6),
                          gradient: LinearGradient(
                              begin: Alignment.bottomCenter,
                              end: Alignment.topCenter,
                              colors: budget > 0 && (d['min'] as num) > budget
                                  ? [const Color(0xFFF87171), const Color(0xFFFFB15C)]
                                  : [C.violet, C.accent2]),
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(names[DateTime.parse(d['date'] as String).weekday - 1],
                        style: const TextStyle(color: C.faint, fontSize: 10)),
                  ]),
                ),
            ]),
          ]);
        }),
      ),
    ]));
  }

  Widget _apps(Map<String, dynamic> r) {
    final apps = List<Map<String, dynamic>>.from((r['apps'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
    if (apps.isEmpty) return const SizedBox.shrink();
    final top = (apps.first['min'] as num).toDouble();
    return _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('APP KE HISAAB SE', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: C.faint, letterSpacing: .8)),
      const SizedBox(height: 10),
      for (final a in apps)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(width: 10, height: 10, decoration: BoxDecoration(color: _appColors[a['app']] ?? C.accent, shape: BoxShape.circle)),
              const SizedBox(width: 8),
              Expanded(child: Text('${a['app']}', style: const TextStyle(fontWeight: FontWeight.w800))),
              Text(hm(a['min'] as num), style: const TextStyle(fontWeight: FontWeight.w800)),
            ]),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: top > 0 ? (a['min'] as num) / top : 0,
                minHeight: 7,
                backgroundColor: const Color(0x14FFFFFF),
                color: _appColors[a['app']] ?? C.accent,
              ),
            ),
            const SizedBox(height: 4),
            Text('${a['sessions']} baar khola · sabse lambi baar ${hm(a['longest'] as num)} · ${a['share']}%',
                style: const TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      if (apps.any((a) => a['app'] == 'YouTube'))
        const Text('YouTube mein lambe videos bhi gine jaate hain (Shorts alag nahi dikhte).', style: TextStyle(color: C.faint, fontSize: 11)),
    ]));
  }

  Widget _hours(Map<String, dynamic> r) {
    final hours = List<double>.from((r['hours'] as List).map((e) => (e as num).toDouble()));
    final top = hours.reduce((a, b) => a > b ? a : b);
    if (top <= 0) return const SizedBox.shrink();
    return _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('DIN MEIN KAB', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: C.faint, letterSpacing: .8)),
      const SizedBox(height: 12),
      SizedBox(
        height: 56,
        child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          for (var h = 0; h < 24; h++)
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 1),
                height: (hours[h] / top * 56).clamp(2.0, 56.0),
                decoration: BoxDecoration(
                  color: (h >= 23 || h < 5) ? const Color(0xFFF87171) : C.teal.withOpacity(.35 + .65 * hours[h] / top),
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
        ]),
      ),
      const SizedBox(height: 6),
      const Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text('12am', style: TextStyle(color: C.faint, fontSize: 10)),
        Text('6am', style: TextStyle(color: C.faint, fontSize: 10)),
        Text('12pm', style: TextStyle(color: C.faint, fontSize: 10)),
        Text('6pm', style: TextStyle(color: C.faint, fontSize: 10)),
        Text('11pm', style: TextStyle(color: C.faint, fontSize: 10)),
      ]),
    ]));
  }

  Widget _stat(IconData icon, Color color, String big, String small) => Glass(
        radius: 18,
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 8),
          Text(big, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
          const SizedBox(height: 2),
          Text(small, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.faint, fontSize: 11.5)),
        ]),
      );

  Widget _stats(Map<String, dynamic> r) {
    final longest = Map<String, dynamic>.from(r['longest'] as Map);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: 1.55,
        children: [
          _stat(Icons.bedtime_rounded, const Color(0xFFF87171), hm(r['late_min'] as num), 'raat 11 ke baad · ${r['late_days']} din'),
          _stat(Icons.hourglass_bottom_rounded, C.warn, hm(longest['min'] as num),
              'sabse lambi sitting${'${longest['app']}'.isEmpty ? '' : ' · ${longest['app']}'}'),
          _stat(Icons.schedule_rounded, C.teal, '${r['peak_text']}'.isEmpty ? '—' : '${r['peak_text']}', 'sabse zyada scroll'),
          _stat(Icons.today_rounded, C.accent, hm(r['today_min'] as num),
              (r['budget_min'] as num? ?? 0) > 0 ? 'aaj · limit ${hm(r['budget_min'] as num)}' : 'aaj'),
        ],
      ),
    );
  }

  Widget _insights(Map<String, dynamic> r) => _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.auto_awesome_rounded, color: C.accent, size: 18),
          SizedBox(width: 8),
          Text('Hoola ki baat', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 10),
        for (final t in (r['insights'] as List))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('•  ', style: TextStyle(color: C.accent)),
              Expanded(child: Text('$t', style: const TextStyle(fontSize: 13.5, height: 1.4))),
            ]),
          ),
      ]));

  Widget _budgetCard(Map<String, dynamic> r) {
    final cur = (r['budget_min'] as num? ?? 0).toInt();
    return _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('ROZ KI LIMIT', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: C.faint, letterSpacing: .8)),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final m in const [0, 30, 60, 90, 120, 180])
          ChoiceChip(
            label: Text(m == 0 ? 'Koi nahi' : hm(m)),
            selected: cur == m,
            selectedColor: C.accent,
            labelStyle: TextStyle(color: cur == m ? C.onAccent : C.ink, fontWeight: FontWeight.w700),
            backgroundColor: const Color(0x17FFFFFF),
            onSelected: (_) => _budget(m),
          ),
      ]),
    ]));
  }

  Widget _taste(String source, Map<String, dynamic> t) {
    final topics = List<Map<String, dynamic>>.from((t['topics'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final creators = List<Map<String, dynamic>>.from((t['top_creators'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    List<String> strs(String k) => List<String>.from((t[k] as List? ?? const []).map((e) => '$e'));
    return _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Icon(source == 'youtube' ? Icons.smart_display_rounded : Icons.camera_alt_rounded,
            color: source == 'youtube' ? const Color(0xFFFF4B4B) : const Color(0xFFE1306C)),
        const SizedBox(width: 8),
        Expanded(
            child: Text(source == 'youtube' ? 'YouTube pe aap kya dekhte ho' : 'Instagram pe aap kya dekhte ho',
                style: const TextStyle(fontWeight: FontWeight.w800))),
      ]),
      const SizedBox(height: 4),
      Text('${t['items']} videos · ${t['days']} din · roz ~${t['per_day']} · sabse zyada ${t['busiest_day']}'
          '${(t['late_share'] as num? ?? 0) > 0 ? ' · ${t['late_share']}% raat mein' : ''}',
          style: const TextStyle(color: C.faint, fontSize: 11.5)),
      if ('${t['summary']}'.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text('${t['summary']}', style: const TextStyle(fontSize: 13.5, height: 1.4)),
      ],
      if (topics.isNotEmpty) ...[
        const SizedBox(height: 12),
        for (final tp in topics)
          Padding(
            padding: const EdgeInsets.only(bottom: 7),
            child: Row(children: [
              SizedBox(width: 120, child: Text('${tp['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5))),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(5),
                  child: LinearProgressIndicator(
                      value: ((tp['share'] as num) / 100).clamp(0, 1).toDouble(),
                      minHeight: 8,
                      backgroundColor: const Color(0x14FFFFFF),
                      color: C.accent2),
                ),
              ),
              SizedBox(width: 40, child: Text(' ${tp['share']}%', style: const TextStyle(color: C.faint, fontSize: 11.5))),
            ]),
          ),
      ],
      if (creators.isNotEmpty) ...[
        const SizedBox(height: 8),
        const Text('Sabse zyada dekhe creators', style: TextStyle(color: C.muted, fontSize: 12, fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: [for (final c in creators.take(8)) Pill('${c['name']} · ${c['count']}', fg: C.chip)]),
      ],
      for (final g in strs('good')) Padding(padding: const EdgeInsets.only(top: 8), child: Text('👍 $g', style: const TextStyle(fontSize: 12.5))),
      for (final w in strs('watch_out')) Padding(padding: const EdgeInsets.only(top: 8), child: Text('⚠ $w', style: const TextStyle(fontSize: 12.5, color: C.warn))),
      for (final s in strs('suggestions')) Padding(padding: const EdgeInsets.only(top: 8), child: Text('💡 $s', style: const TextStyle(fontSize: 12.5))),
      const SizedBox(height: 8),
      Text('${t['ai_label'] ?? 'AI ka andaaza'}', style: const TextStyle(color: C.faint, fontSize: 10.5)),
    ]));
  }

  Widget _importCard(Map<String, dynamic> r) {
    final tastes = Map<String, dynamic>.from(r['tastes'] as Map? ?? const {});
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const Padding(padding: EdgeInsets.fromLTRB(4, 8, 4, 10), child: Caption('AAP KYA DEKHTE HO')),
      for (final e in tastes.entries) _taste(e.key, Map<String, dynamic>.from(e.value as Map)),
      _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tastes.isEmpty ? 'Apni history Hoola ko dikhaiye' : 'History dobara daalein', style: const TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        const Text('Instagram aur YouTube aapko apni history download karne dete hain. Woh file Hoola ko dijiye: '
            'Hoola topics, creators aur waqt ka saar banayega. Poori list save nahi hoti.',
            style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
        const SizedBox(height: 10),
        const ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: Text('Instagram se kaise', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          children: [
            Text('Instagram → Profile → ☰ → Accounts Center → Your information and permissions → Download your information → '
                'Some of your information → "Your activity" (Ads & topics / Likes / Saved) → Download to device → '
                'Format: JSON, Date range: Last 3 months → Create files. Email aane par zip download karke yahan chuniye.',
                style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.45)),
            SizedBox(height: 8),
          ],
        ),
        const ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: Text('YouTube se kaise', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          children: [
            Text('takeout.google.com → "Deselect all" → sirf "YouTube and YouTube Music" chuniye → "All YouTube data included" '
                'mein sirf "history" → Next → Create export. Zip download karke yahan chuniye.',
                style: TextStyle(color: C.muted, fontSize: 12.5, height: 1.45)),
            SizedBox(height: 8),
          ],
        ),
        const SizedBox(height: 6),
        _importing
            ? const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator()))
            : GlassButton(label: 'History file chuniye (zip / json / html)', icon: Icons.upload_file_rounded, onTap: _import),
      ])),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      appBar: AppBar(title: const Text('Scroll report'), backgroundColor: Colors.transparent, actions: [
        PopupMenuButton<String>(
          onSelected: (v) {
            if (v == 'forget') {
              _forget();
            } else {
              setState(() => _days = int.parse(v));
              _load();
            }
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: '7', child: Text('Pichhle 7 din')),
            PopupMenuItem(value: '14', child: Text('Pichhle 14 din')),
            PopupMenuItem(value: '30', child: Text('Pichhle 30 din')),
            PopupMenuItem(value: 'forget', child: Text('Scroll data mitao')),
          ],
        ),
      ]),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_allowed == false) _onboarding(),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (r == null && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (r != null) ...[
              if (r['has_data'] == true) ...[
                _week(r),
                _stats(r),
                _apps(r),
                _hours(r),
                _budgetCard(r),
              ],
              _insights(r),
              _importCard(r),
              const SizedBox(height: 8),
              const Text('Hoola sirf yeh ginta hai ki reel apps kitni der khule rahe (Android Usage Access), aur aapki di hui history '
                  'ka saar rakhta hai. Screen pe kya tha, DM, comments: kuch nahi padhta.',
                  style: TextStyle(color: C.faint, fontSize: 11, height: 1.4)),
            ],
          ]),
        ),
      ),
    );
  }
}
