import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';

import '../api.dart';
import '../state.dart';
import 'glass.dart';
import 'plugin_widgets.dart';

/// Hoola TV: free, official live channels (Doordarshan, Sansad TV, free news, bhakti, music...). Watch on the phone,
/// or send to the TV (Chromecast / Android TV / Google TV on the same Wi-Fi).
class HoolaTv {
  /// Set once at start, so the player can open from links and phone actions too.
  static Santosh? app;
  static Api? get api => app?.api;
}

class TvScreen extends StatefulWidget {
  const TvScreen({super.key});
  @override
  State<TvScreen> createState() => _TvScreenState();
}

class _TvScreenState extends State<TvScreen> {
  List<Map<String, dynamic>> _all = [];
  List<Map<String, dynamic>> _cats = [];
  String _cat = '';
  String _q = '';
  String? _err;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = HoolaTv.api;
    if (api == null) return;
    BrandLogo.base = api.baseUrl;
    try {
      final r = await api.tvChannels();
      if (!mounted) return;
      setState(() {
        _all = List<Map<String, dynamic>>.from((r['channels'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
        _cats = List<Map<String, dynamic>>.from((r['categories'] as List).map((e) => Map<String, dynamic>.from(e as Map)));
        _loaded = true;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  List<Map<String, dynamic>> get _shown {
    final q = _q.toLowerCase();
    return _all.where((c) => (_cat.isEmpty || c['category'] == _cat) && (q.isEmpty || '${c['name']}'.toLowerCase().contains(q))).toList();
  }

  Widget _chip(String label, String value) {
    final on = _cat == value;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Press(
        onTap: () => setState(() => _cat = value),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 34,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: on ? C.accent : const Color(0x17FFFFFF),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: on ? C.accent : const Color(0x29FFFFFF)),
          ),
          child: Text(label, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: on ? C.onAccent : C.ink)),
        ),
      ),
    );
  }

  Widget _tile(Map<String, dynamic> c, List<Map<String, dynamic>> list) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => TvPlayerScreen(channelId: c['id'] as String, lineup: list.map((x) => x['id'] as String).toList()))),
        child: Glass(
          radius: 18,
          padding: const EdgeInsets.fromLTRB(8, 12, 8, 10),
          child: Column(children: [
            BrandLogo(name: c['name'] as String? ?? '', path: c['logo'] as String?, category: c['category'] as String? ?? '', size: 52),
            const SizedBox(height: 8),
            Text(c['name'] as String? ?? '', maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, height: 1.2)),
            const Spacer(),
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text(c['category_label'] as String? ?? '', style: const TextStyle(color: C.faint, fontSize: 10.5)),
              if (c['on_tv'] == true) ...[const SizedBox(width: 4), const Icon(Icons.cast_rounded, size: 12, color: C.teal)],
            ]),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final list = _shown;
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola TV'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            Text('${_all.length} free channels · phone pe dekhiye ya TV pe bhejiye',
                style: const TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 4),
            const Text('Sirf official free channels (Doordarshan, Sansad TV, free news, bhakti, music). '
                'Paid channels (Star, Sony, Colors) unke apne app mein.', style: TextStyle(color: C.faint, fontSize: 11.5)),
            const SizedBox(height: 12),
            Glass(
              radius: 18,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
              child: TextField(
                style: const TextStyle(color: C.ink, fontSize: 15),
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded, color: C.muted), hintText: 'DD Sahyadri, Aaj Tak, Aastha…',
                    border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),
                onChanged: (v) => setState(() => _q = v.trim()),
              ),
            ),
            const SizedBox(height: 12),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: [
                _chip('Sab', ''),
                for (final c in _cats) _chip('${c['label']} · ${c['count']}', c['id'] as String),
              ]),
            ),
            const SizedBox(height: 14),
            if (_err != null) Text(_err!, style: const TextStyle(color: C.bad)),
            if (!_loaded && _err == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && list.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Kuch nahi mila', style: TextStyle(color: C.muted)))),
            GridView(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3, mainAxisSpacing: 10, crossAxisSpacing: 10, mainAxisExtent: 142),
              children: [for (final c in list) _tile(c, list)],
            ),
          ]),
        ),
      ),
    );
  }
}

/// Plays one channel on the phone; "TV pe dikhao" sends it to the TV.
class TvPlayerScreen extends StatefulWidget {
  const TvPlayerScreen({super.key, required this.channelId, this.lineup = const []});
  final String channelId;
  final List<String> lineup;
  @override
  State<TvPlayerScreen> createState() => _TvPlayerScreenState();
}

class _TvPlayerScreenState extends State<TvPlayerScreen> {
  VideoPlayerController? _vc;
  Map<String, dynamic>? _ch;
  late String _id = widget.channelId;
  String? _err;
  bool _casting = false;
  bool _onTv = false;
  bool _full = false;

  @override
  void initState() {
    super.initState();
    _open(_id);
  }

  @override
  void dispose() {
    _vc?.dispose();
    SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    super.dispose();
  }

  Future<void> _open(String id) async {
    final api = HoolaTv.api;
    if (api == null) return;
    BrandLogo.base = api.baseUrl;
    final old = _vc;
    setState(() {
      _id = id;
      _vc = null;
      _err = null;
    });
    await old?.dispose();
    try {
      final ch = await api.tvChannel(id);
      if (!mounted) return;
      setState(() => _ch = ch);
      final urls = [ch['url'] as String, ...List<String>.from((ch['alternates'] as List? ?? const []).map((e) => '$e'))];
      final headers = <String, String>{
        if ((ch['user_agent'] as String? ?? '').isNotEmpty) 'User-Agent': ch['user_agent'] as String,
        if ((ch['referrer'] as String? ?? '').isNotEmpty) 'Referer': ch['referrer'] as String,
      };
      for (final u in urls) {
        final vc = VideoPlayerController.networkUrl(Uri.parse(u), httpHeaders: headers, formatHint: VideoFormat.hls);
        try {
          await vc.initialize().timeout(const Duration(seconds: 20));
          if (!mounted || _id != id) {
            await vc.dispose();
            return;
          }
          await vc.play();
          setState(() => _vc = vc);
          return;
        } catch (_) {
          await vc.dispose();
        }
      }
      if (mounted) setState(() => _err = '${ch['name']} abhi chal nahi raha. Thodi der baad try kijiye ya doosra channel dekhiye.');
    } catch (e) {
      if (mounted) setState(() => _err = e is ApiException ? e.message : '$e');
    }
  }

  void _step(int d) {
    final l = widget.lineup;
    if (l.isEmpty) return;
    final i = l.indexOf(_id);
    _open(l[((i < 0 ? 0 : i) + d) % l.length]);
  }

  Future<void> _cast() async {
    final api = HoolaTv.api;
    if (api == null) return;
    setState(() => _casting = true);
    try {
      final r = await api.tvCast(_id);
      final ok = r['status'] == 'ok' && r['playing'] == true;
      if (ok) {
        await _vc?.pause();
        setState(() => _onTv = true);
      }
      _snack(ok ? '${_ch?['name'] ?? 'Channel'} ${r['tv_name'] ?? 'TV'} pe chal raha hai' : (r['error'] ?? r['say'] ?? 'TV pe nahi chala').toString());
    } catch (e) {
      _snack(e is ApiException ? e.message : '$e');
    }
    if (mounted) setState(() => _casting = false);
  }

  Future<void> _stopTv() async {
    try {
      await HoolaTv.api?.tvStop();
    } catch (_) {}
    if (mounted) setState(() => _onTv = false);
    await _vc?.play();
  }

  void _snack(String t) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));
  }

  void _toggleFull() {
    setState(() => _full = !_full);
    if (_full) {
      SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
      SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    } else {
      SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
      SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    }
  }

  Widget _video() {
    final vc = _vc;
    return GestureDetector(
      onDoubleTap: _toggleFull,
      child: Container(
        color: Colors.black,
        child: AspectRatio(
          aspectRatio: vc != null && vc.value.isInitialized && vc.value.aspectRatio > 0 ? vc.value.aspectRatio : 16 / 9,
          child: Stack(alignment: Alignment.center, children: [
            if (vc != null) VideoPlayer(vc),
            if (vc == null && _err == null) const CircularProgressIndicator(color: C.accent),
            if (_err != null)
              Padding(padding: const EdgeInsets.all(20), child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: C.chip))),
            if (_onTv)
              Container(
                color: const Color(0xCC000000),
                alignment: Alignment.center,
                child: const Column(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.cast_connected_rounded, color: C.teal, size: 40),
                  SizedBox(height: 8),
                  Text('TV pe chal raha hai', style: TextStyle(color: C.ink, fontWeight: FontWeight.w700)),
                ]),
              ),
            Positioned(
              right: 6,
              bottom: 6,
              child: IconButton(
                  icon: Icon(_full ? Icons.fullscreen_exit_rounded : Icons.fullscreen_rounded, color: Colors.white),
                  onPressed: _toggleFull),
            ),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_full) return Scaffold(backgroundColor: Colors.black, body: Center(child: _video()));
    final ch = _ch;
    return Scaffold(
      appBar: AppBar(title: Text(ch?['name'] as String? ?? 'Hoola TV'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: ListView(padding: const EdgeInsets.fromLTRB(0, 0, 0, 32), children: [
          _video(),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                BrandLogo(name: ch?['name'] as String? ?? '', path: ch?['logo'] as String?, category: ch?['category'] as String? ?? '', size: 46),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(ch?['name'] as String? ?? '', style: display(18)),
                    Text('${ch?['category_label'] ?? ''}${(ch?['quality'] ?? 0) != 0 ? ' · ${ch?['quality']}p' : ''} · Live',
                        style: const TextStyle(color: C.faint, fontSize: 12.5)),
                  ]),
                ),
              ]),
              const SizedBox(height: 16),
              if (!_onTv)
                PluginAction(
                    kind: ch?['on_tv'] == true ? ActionKind.add : ActionKind.attention,
                    label: _casting ? 'TV dhoondh raha hoon…' : 'TV pe dikhao',
                    height: 48,
                    onTap: _casting || ch == null ? null : _cast)
              else
                PluginAction(kind: ActionKind.linked, label: 'TV pe band karo', height: 48, onTap: _stopTv),
              const SizedBox(height: 8),
              Text(
                  ch?['on_tv'] == true
                      ? 'Chromecast, Android TV ya Google TV phone ke Wi-Fi par ho.'
                      : 'Yeh channel shayad sirf phone pe chale. Samsung / LG TV ke liye Hoola se kahiye: "TV pe YouTube pe ${ch?['name'] ?? ''} live lagao".',
                  style: const TextStyle(color: C.faint, fontSize: 11.5)),
              if (widget.lineup.length > 1) ...[
                const SizedBox(height: 16),
                Row(children: [
                  Expanded(child: GlassButton(label: 'Pichla', icon: Icons.skip_previous_rounded, height: 44, onTap: () => _step(-1))),
                  const SizedBox(width: 10),
                  Expanded(child: GlassButton(label: 'Agla', icon: Icons.skip_next_rounded, height: 44, onTap: () => _step(1))),
                ]),
              ],
            ]),
          ),
        ]),
      ),
    );
  }
}
