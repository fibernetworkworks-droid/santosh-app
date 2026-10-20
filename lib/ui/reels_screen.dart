import 'dart:async';
import 'dart:io';

import 'package:android_intent_plus/android_intent.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';
import 'tv_screen.dart' show HoolaTv;

/// Hoola Reels: share any reel to Hoola (Instagram, YouTube Shorts, Facebook, Snapchat, Moj, Josh, ShareChat) and turn
/// it into something useful: save it, a reminder, the shopping list, a message for family, or "ye sach hai?".
class HoolaReels {
  static final _link = RegExp(
      r'https?://(?:www\.|m\.)?(?:youtube\.com/(?:shorts/|watch)|youtu\.be/|instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/|'
      r'facebook\.com/(?:reel|watch|share/[rv])|fb\.watch/|snapchat\.com/(?:spotlight|t)/|mojapp\.in/|[\w.]*myjosh\.in/|sharechat\.com/)',
      caseSensitive: false);

  static bool hasLink(String text) => _link.hasMatch(text);

  /// A share from another app that should open as a reel (a reel link, or one video on its own, e.g. a screen recording).
  static bool isReelShare(Map<String, dynamic> s) {
    final text = (s['text'] as String? ?? '');
    final files = (s['files'] as List? ?? const []);
    if (hasLink(text)) return true;
    if (files.length == 1 && text.trim().isEmpty) {
      final n = '${(files.first as Map)['name']}'.toLowerCase();
      return n.endsWith('.mp4') || n.endsWith('.mov') || n.endsWith('.webm') || n.endsWith('.3gp') || n.endsWith('.mkv');
    }
    return false;
  }
}

class ReelScreen extends StatefulWidget {
  const ReelScreen({super.key, this.text = '', this.filePath, this.fileName, this.reelId});
  final String text;
  final String? filePath;
  final String? fileName;
  final String? reelId;
  @override
  State<ReelScreen> createState() => _ReelScreenState();
}

class _ReelScreenState extends State<ReelScreen> {
  Map<String, dynamic>? _r;
  Map<String, dynamic>? _check;
  String? _err;
  String _busy = '';
  bool _looking = true;

  Api? get _api => HoolaTv.api;
  Santosh? get _app => HoolaTv.app;

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    final api = _api;
    if (api == null) return;
    setState(() {
      _looking = true;
      _err = null;
    });
    try {
      Map<String, dynamic> r;
      if (widget.reelId != null) {
        r = await api.reelGet(widget.reelId!);
      } else if (widget.filePath != null) {
        final bytes = await File(widget.filePath!).readAsBytes();
        r = await api.reelLookFile(widget.fileName ?? 'reel.mp4', bytes, text: widget.text);
      } else {
        r = await api.reelLook(widget.text);
      }
      if (!mounted) return;
      setState(() {
        _r = r;
        if (r['checks'] != null) _check = {'checks': r['checks'], 'overall': r['overall']};
      });
    } catch (e) {
      if (mounted) setState(() => _err = e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _looking = false);
    }
  }

  Future<void> _pickRecording() async {
    final api = _api;
    if (api == null) return;
    final res = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: const ['mp4', 'mov', 'webm', '3gp', 'mkv', 'jpg', 'jpeg', 'png', 'webp']);
    final path = res?.files.single.path;
    if (path == null) return;
    setState(() {
      _looking = true;
      _err = null;
    });
    try {
      final bytes = await File(path).readAsBytes();
      final r = await api.reelLookFile(res!.files.single.name, bytes, text: (_r?['url'] as String?) ?? widget.text);
      if (mounted) setState(() => _r = r);
    } catch (e) {
      if (mounted) _snack(e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _looking = false);
    }
  }

  String get _id => _r?['reel_id'] as String? ?? '';

  Future<void> _run(String what, Future<void> Function() fn) async {
    if (_busy.isNotEmpty || _id.isEmpty) return;
    setState(() => _busy = what);
    try {
      await fn();
    } catch (e) {
      if (mounted) _snack(e is ApiException ? e.message : '$e');
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  // 1 save
  Future<void> _save() => _run('save', () async {
        final api = _api!;
        if (_r?['saved'] == true) {
          await api.reelUnsave(_id);
          setState(() => _r = {...?_r, 'saved': false});
          _snack('Saved se hata di');
          return;
        }
        final r = await api.reelSave(_id);
        setState(() => _r = r);
        _snack('${r['say'] ?? 'Save ho gayi'}');
      });

  // 2 remind
  Future<void> _remind() async {
    final now = DateTime.now();
    DateTime at(int addDays, int h) => DateTime(now.year, now.month, now.day + addDays, h);
    final sunday = at((DateTime.sunday - now.weekday + 7) % 7 == 0 ? 7 : (DateTime.sunday - now.weekday + 7) % 7, 11);
    final options = <(String, DateTime)>[
      if (now.hour < 18) ('Aaj shaam 7 baje', at(0, 19)),
      ('Kal subah 9 baje', at(1, 9)),
      ('Kal shaam 7 baje', at(1, 19)),
      ('Is Sunday 11 baje', sunday),
    ];
    final picked = await showModalBottomSheet<DateTime>(
      context: context,
      backgroundColor: C.bgBottom,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 10),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Kab yaad dilaun?', style: display(18)),
            const SizedBox(height: 12),
            for (final o in options)
              ListTile(
                leading: const Icon(Icons.alarm_rounded, color: C.accent),
                title: Text(o.$1, style: const TextStyle(fontWeight: FontWeight.w700)),
                onTap: () => Navigator.pop(ctx, o.$2),
              ),
            ListTile(
              leading: const Icon(Icons.edit_calendar_rounded, color: C.teal),
              title: const Text('Din aur time chuniye', style: TextStyle(fontWeight: FontWeight.w700)),
              onTap: () async {
                final d = await showDatePicker(context: ctx, firstDate: now, lastDate: now.add(const Duration(days: 730)), initialDate: now);
                if (d == null || !ctx.mounted) return;
                final t = await showTimePicker(context: ctx, initialTime: const TimeOfDay(hour: 19, minute: 0));
                if (t == null || !ctx.mounted) return;
                Navigator.pop(ctx, DateTime(d.year, d.month, d.day, t.hour, t.minute));
              },
            ),
          ]),
        ),
      ),
    );
    if (picked == null) return;
    String two(int n) => n.toString().padLeft(2, '0');
    final iso = '${picked.year}-${two(picked.month)}-${two(picked.day)}T${two(picked.hour)}:${two(picked.minute)}';
    await _run('remind', () async {
      final r = await _api!.reelRemind(_id, iso);
      _snack('${r['say'] ?? 'Reminder lag gaya'}');
    });
  }

  // 3 shop
  Future<void> _shop() async {
    final r = _r!;
    final products = List<Map<String, dynamic>>.from((r['products'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final ingredients = List<String>.from(((r['recipe'] as Map?)?['ingredients'] as List? ?? const []).map((e) => '$e'));
    final names = [
      for (final p in products)
        ((p['brand'] as String? ?? '').isEmpty || '${p['name']}'.toLowerCase().contains('${p['brand']}'.toLowerCase()))
            ? '${p['name']}'
            : '${p['brand']} ${p['name']}',
      ...ingredients,
    ];
    if (names.isEmpty) {
      _snack('Is reel mein khareedne layak cheez nahi mili.');
      return;
    }
    final chosen = names.toSet();
    final go = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: C.bgBottom,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .8),
            child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(18, 18, 18, 12), children: [
              Text('Shopping list mein daalein?', style: display(18)),
              const SizedBox(height: 6),
              const Text('Neeche ke link se daam milaiye; khareedna aap khud karenge.', style: TextStyle(color: C.faint, fontSize: 12)),
              const SizedBox(height: 8),
              for (final n in names)
                CheckboxListTile(
                  value: chosen.contains(n),
                  activeColor: C.accent,
                  title: Text(n, style: const TextStyle(fontWeight: FontWeight.w600)),
                  onChanged: (v) => set(() => v == true ? chosen.add(n) : chosen.remove(n)),
                ),
              for (final p in products) ...[
                const SizedBox(height: 6),
                Text('${p['name']} dhoondhiye', style: const TextStyle(color: C.muted, fontSize: 12.5, fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final l in List<Map<String, dynamic>>.from((p['links'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map))))
                    GlassButton(label: '${l['name']}', icon: Icons.open_in_new_rounded, height: 38, onTap: () => _open('${l['url']}')),
                ]),
              ],
              const SizedBox(height: 16),
              GradientButton(label: 'List mein daalo', icon: Icons.add_shopping_cart_rounded, onTap: () => Navigator.pop(ctx, true)),
            ]),
          ),
        ),
      ),
    );
    if (go != true || chosen.isEmpty) return;
    await _run('shop', () async {
      final res = await _api!.reelShop(_id, items: chosen.toList());
      _snack('${res['say'] ?? 'List mein daal diya'}');
    });
  }

  // 4 family (the owner chooses WhatsApp etc. and taps send there)
  Future<void> _family() => _run('family', () async {
        final text = await _api!.reelShareText(_id);
        await AndroidIntent(action: 'android.intent.action.SEND', type: 'text/plain', arguments: <String, dynamic>{
          'android.intent.extra.TEXT': text,
        }).launchChooser('Family ko bhejo');
      });

  // 5 ye sach hai?
  Future<void> _sach() => _run('check', () async {
        final r = await _api!.reelCheck(_id);
        setState(() => _check = r);
        if ((r['checks'] as List? ?? const []).isEmpty) _snack('${r['note'] ?? 'Check karne layak daava nahi mila'}');
      });

  void _askInChat() {
    final app = _app;
    if (app == null) return;
    final url = _r?['url'] as String? ?? '';
    final t = _r?['title'] as String? ?? '';
    Navigator.of(context).popUntil((r) => r.isFirst);
    app.onShared({'files': <dynamic>[], 'text': 'Is reel ke baare mein: ${t.isEmpty ? '' : '"$t" '}$url'.trim(), 'skipped': 0});
  }

  Future<void> _open(String url) async {
    final u = Uri.tryParse(url);
    if (u != null) await launchUrl(u, mode: LaunchMode.externalApplication);
  }

  void _snack(String t) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  // ---------------------------------------------------------------- UI
  Widget _action(String key, IconData icon, String label, Color color, VoidCallback onTap, {bool on = false}) => Press(
        onTap: onTap,
        child: Glass(
          radius: 18,
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            _busy == key
                ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2))
                : Icon(on ? Icons.bookmark_rounded : icon, color: color, size: 26),
            const SizedBox(height: 6),
            Text(label, textAlign: TextAlign.center, maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5, height: 1.15)),
          ]),
        ),
      );

  Widget _section(String title, List<Widget> children) => Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Glass(
          radius: 18,
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: C.muted, letterSpacing: .4)),
            const SizedBox(height: 8),
            ...children,
          ]),
        ),
      );

  Widget _bullet(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('•  ', style: TextStyle(color: C.accent)),
          Expanded(child: Text(t, style: const TextStyle(fontSize: 13.5, height: 1.35))),
        ]),
      );

  static const _verdict = {
    'sach': ('Sahi lagta hai', C.ok, Icons.verified_rounded),
    'galat': ('Galat lagta hai', C.bad, Icons.dangerous_rounded),
    'adhoora': ('Aadha sach / bhramak', C.warn, Icons.error_outline_rounded),
    'pata_nahi': ('Pakka nahi', C.muted, Icons.help_outline_rounded),
  };

  Widget _checkCard() {
    final c = _check!;
    final checks = List<Map<String, dynamic>>.from((c['checks'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    if (checks.isEmpty) return const SizedBox.shrink();
    final o = _verdict[c['overall']] ?? _verdict['pata_nahi']!;
    return _section('YE SACH HAI?', [
      Row(children: [
        Icon(o.$3, color: o.$2),
        const SizedBox(width: 8),
        Expanded(child: Text('${c['say'] ?? o.$1}', style: TextStyle(fontWeight: FontWeight.w800, color: o.$2))),
      ]),
      const SizedBox(height: 10),
      for (final ch in checks) ...[
        Text('"${ch['claim']}"', style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 13)),
        const SizedBox(height: 4),
        Text('${(_verdict[ch['verdict']] ?? _verdict['pata_nahi']!).$1}: ${ch['why']}',
            style: TextStyle(color: (_verdict[ch['verdict']] ?? _verdict['pata_nahi']!).$2, fontSize: 12.5, fontWeight: FontWeight.w600)),
        Wrap(spacing: 10, children: [
          for (final s in List<Map<String, dynamic>>.from((ch['sources'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map))))
            TextButton(
              style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(0, 30)),
              onPressed: () => _open('${s['url']}'),
              child: Text('${s['title']}'.isEmpty ? 'source' : '${s['title']}', style: const TextStyle(color: C.teal, fontSize: 12)),
            ),
        ]),
        const SizedBox(height: 8),
      ],
      const Text('Google Search se jaancha: yeh ishara hai, aakhri faisla nahi.', style: TextStyle(color: C.faint, fontSize: 11)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola Reels'), backgroundColor: Colors.transparent, actions: [
        IconButton(
          tooltip: 'Saved reels',
          icon: const Icon(Icons.collections_bookmark_rounded),
          onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SavedReelsScreen())),
        ),
      ]),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
          if (_looking)
            Glass(
              radius: 20,
              padding: const EdgeInsets.all(22),
              child: Column(children: const [
                SizedBox(width: 30, height: 30, child: CircularProgressIndicator(strokeWidth: 2.5)),
                SizedBox(height: 14),
                Text('Hoola reel dekh raha hai…', style: TextStyle(fontWeight: FontWeight.w700)),
              ]),
            ),
          if (_err != null && !_looking) ...[
            Glass(radius: 18, padding: const EdgeInsets.all(16), child: Text(_err!, style: const TextStyle(color: C.bad))),
            const SizedBox(height: 12),
            GlassButton(label: 'Screen recording chuniye', icon: Icons.video_library_rounded, onTap: _pickRecording),
          ],
          if (r != null && !_looking) ...[
            Row(children: [
              Pill('${r['platform_name'] ?? 'Reel'}'.toUpperCase(), fg: C.accent),
              const SizedBox(width: 8),
              if ((r['kind'] as String? ?? 'other') != 'other') Pill('${r['kind']}'.toUpperCase()),
              const Spacer(),
              if ((r['url'] as String? ?? '').isNotEmpty)
                IconButton(icon: const Icon(Icons.open_in_new_rounded, color: C.muted), onPressed: () => _open('${r['url']}')),
            ]),
            const SizedBox(height: 8),
            Text((r['title'] as String? ?? '').isEmpty ? 'Reel' : '${r['title']}', style: display(21)),
            const SizedBox(height: 8),
            if ((r['summary'] as String? ?? '').isNotEmpty)
              Text('${r['summary']}', style: const TextStyle(fontSize: 14.5, height: 1.45, color: C.ink)),
            const SizedBox(height: 6),
            Row(children: [
              const Icon(Icons.auto_awesome_rounded, size: 13, color: C.faint),
              const SizedBox(width: 5),
              Expanded(child: Text('${r['ai_label'] ?? 'AI se bana'}', style: const TextStyle(color: C.faint, fontSize: 11))),
            ]),
            if (r['needs_video'] == true) ...[
              const SizedBox(height: 12),
              Glass(
                radius: 18,
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Row(children: [
                    Icon(Icons.screen_share_rounded, color: C.warn, size: 20),
                    SizedBox(width: 8),
                    Expanded(child: Text('Poori reel samajhne ke liye', style: TextStyle(fontWeight: FontWeight.w800))),
                  ]),
                  const SizedBox(height: 6),
                  Text('${r['how_to_show'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 13, height: 1.35)),
                  const SizedBox(height: 10),
                  GlassButton(label: 'Recording / screenshot chuniye', icon: Icons.video_library_rounded, onTap: _pickRecording),
                ]),
              ),
            ],
            for (final w in List<Map<String, dynamic>>.from((r['warnings'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map))))
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: const Color(0x22F87171), borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0x55F87171))),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Icon(Icons.warning_amber_rounded, color: C.warn, size: 20),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${w['say']}', style: const TextStyle(fontSize: 13, height: 1.35))),
                  ]),
                ),
              ),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount: 5,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
              childAspectRatio: .78,
              children: [
                _action('save', Icons.bookmark_add_rounded, r['saved'] == true ? 'Saved' : 'Save', C.accent, _save, on: r['saved'] == true),
                _action('remind', Icons.alarm_add_rounded, 'Yaad dilao', C.teal, _remind),
                _action('shop', Icons.shopping_bag_rounded, 'Khareedo', C.accentSoft, _shop),
                _action('family', Icons.family_restroom_rounded, 'Family ko', C.violet, _family),
                _action('check', Icons.fact_check_rounded, 'Ye sach hai?', C.ok, _sach),
              ],
            ),
            if (_check != null) _checkCard(),
            if (r['recipe'] is Map)
              _section('RECIPE · ${(r['recipe'] as Map)['dish'] ?? ''}'.toUpperCase(), [
                for (final i in ((r['recipe'] as Map)['ingredients'] as List? ?? const [])) _bullet('$i'),
                if ((((r['recipe'] as Map)['steps'] as List?) ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 8),
                  for (final (n, st) in (((r['recipe'] as Map)['steps'] as List?) ?? const []).indexed) _bullet('${n + 1}. $st'),
                ],
              ]),
            if ((r['products'] as List? ?? const []).isNotEmpty)
              _section('REEL MEIN DIKHA SAAMAAN', [
                for (final p in (r['products'] as List))
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    leading: const Icon(Icons.local_offer_rounded, color: C.accentSoft),
                    title: Text('${(p as Map)['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: '${p['brand']}'.isEmpty ? null : Text('${p['brand']}', style: const TextStyle(color: C.faint)),
                    trailing: const Icon(Icons.search_rounded, color: C.muted),
                    onTap: () => _open('${((p['links'] as List?) ?? const [{'url': ''}]).first['url']}'),
                  ),
              ]),
            if ((r['places'] as List? ?? const []).isNotEmpty)
              _section('JAGAH', [
                for (final p in (r['places'] as List))
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    leading: const Icon(Icons.place_rounded, color: C.teal),
                    title: Text('${(p as Map)['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: '${p['city']}'.isEmpty ? null : Text('${p['city']}', style: const TextStyle(color: C.faint)),
                    trailing: const Icon(Icons.map_rounded, color: C.muted),
                    onTap: () => _open('${p['map']}'),
                  ),
              ]),
            if ((r['events'] as List? ?? const []).isNotEmpty)
              _section('TAREEKH / OFFER', [
                for (final e in (r['events'] as List)) _bullet('${(e as Map)['what']}${'${e['when']}'.isEmpty ? '' : ' · ${e['when']}'}'),
              ]),
            if ((r['song'] as String? ?? '').isNotEmpty) _section('GAANA', [_bullet('${r['song']}')]),
            const SizedBox(height: 16),
            GlassButton(label: 'Hoola se is reel ke baare mein poochho', icon: Icons.chat_bubble_rounded, onTap: _askInChat),
          ],
        ]),
      ),
    );
  }
}

/// Reels the owner saved: search them by anything ("paneer", "Goa", "kurta").
class SavedReelsScreen extends StatefulWidget {
  const SavedReelsScreen({super.key});
  @override
  State<SavedReelsScreen> createState() => _SavedReelsScreenState();
}

class _SavedReelsScreenState extends State<SavedReelsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loaded = false;
  String? _err;
  Timer? _debounce;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final api = HoolaTv.api;
    if (api == null) return;
    try {
      final r = await api.reelsSaved(q: _q);
      if (mounted) {
        setState(() {
          _items = r;
          _loaded = true;
          _err = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _err = e is ApiException ? e.message : '$e');
    }
  }

  static const _icons = {
    'recipe': Icons.restaurant_rounded, 'product': Icons.shopping_bag_rounded, 'fashion': Icons.checkroom_rounded,
    'place': Icons.place_rounded, 'travel': Icons.flight_rounded, 'fitness': Icons.fitness_center_rounded,
    'finance': Icons.currency_rupee_rounded, 'health': Icons.favorite_rounded, 'news': Icons.newspaper_rounded,
    'education': Icons.school_rounded, 'music': Icons.music_note_rounded, 'comedy': Icons.sentiment_very_satisfied_rounded,
    'tech': Icons.devices_rounded,
  };

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Saved reels'), backgroundColor: Colors.transparent),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
              const Text('Kisi bhi app ki reel: Share dabaiye, Hoola chuniye.', style: TextStyle(color: C.muted, fontSize: 13)),
              const SizedBox(height: 12),
              Glass(
                radius: 18,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
                child: TextField(
                  style: const TextStyle(color: C.ink, fontSize: 15),
                  decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search_rounded, color: C.muted),
                      hintText: 'paneer, Goa, kurta, workout…',
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none),
                  onChanged: (v) {
                    _debounce?.cancel();
                    _debounce = Timer(const Duration(milliseconds: 300), () {
                      _q = v.trim();
                      _load();
                    });
                  },
                ),
              ),
              const SizedBox(height: 14),
              if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
              if (!_loaded && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
              if (_loaded && _items.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(
                      child: Text('Abhi koi saved reel nahi.\nInstagram / YouTube mein reel kholiye → Share → Hoola → Save.',
                          textAlign: TextAlign.center, style: TextStyle(color: C.muted))),
                ),
              for (final r in _items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Press(
                    onTap: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => ReelScreen(reelId: r['reel_id'] as String)))
                        .then((_) => _load()),
                    child: Glass(
                      radius: 18,
                      padding: const EdgeInsets.all(14),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Container(
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(color: const Color(0x22FFB15C), borderRadius: BorderRadius.circular(12)),
                          child: Icon(_icons[r['kind']] ?? Icons.movie_rounded, color: C.accent),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${r['title']}'.isEmpty ? 'Reel' : '${r['title']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
                            const SizedBox(height: 3),
                            Text('${r['summary']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12.5)),
                            const SizedBox(height: 5),
                            Text('${r['platform_name']}${'${r['note']}'.isEmpty ? '' : ' · ${r['note']}'}',
                                style: const TextStyle(color: C.faint, fontSize: 11)),
                          ]),
                        ),
                      ]),
                    ),
                  ),
                ),
            ]),
          ),
        ),
      );
}
