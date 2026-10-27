import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

const desktopDownload = 'https://github.com/fibernetworkworks-droid/santosh-app/releases/download/desktop-latest/SantoshDesktop.exe';

String _size(num? b) {
  final v = (b ?? 0).toDouble();
  if (v >= 1024 * 1024) return '${(v / 1024 / 1024).toStringAsFixed(1)} MB';
  if (v >= 1024) return '${(v / 1024).toStringAsFixed(0)} KB';
  return '${v.toInt()} B';
}

String _ago(String? iso) {
  final t = DateTime.tryParse(iso ?? '')?.toLocal();
  if (t == null) return 'kabhi nahi';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'abhi';
  if (d.inHours < 1) return '${d.inMinutes} min pehle';
  if (d.inDays < 1) return '${d.inHours} ghante pehle';
  return '${d.inDays} din pehle';
}

/// Mera PC: pair a computer, see if it is online, search it, move files both ways, and see everything Santosh did there.
class PcScreen extends StatefulWidget {
  const PcScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PcScreen> createState() => _PcScreenState();
}

class _PcScreenState extends State<PcScreen> {
  List<Map<String, dynamic>> _devices = [];
  List<Map<String, dynamic>> _jobs = [];
  List<Map<String, dynamic>> _results = [];
  String? _code;
  DateTime? _codeUntil;
  String? _err;
  bool _loaded = false;
  bool _busy = false;
  Timer? _poll;
  final _q = TextEditingController();

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 4), (_) => _load(quiet: true));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load({bool quiet = false}) async {
    try {
      final r = await Future.wait([app.api!.pcDevices(), app.api!.pcJobs()]);
      if (!mounted) return;
      setState(() {
        final before = _devices.length;
        _devices = r[0];
        _jobs = r[1];
        _loaded = true;
        _err = null;
        if (_devices.length > before && _code != null) _code = null; // the PC just paired
      });
    } catch (e) {
      if (mounted && !quiet) setState(() => _err = e.toString());
    }
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Future<void> _newCode() async {
    try {
      final r = await app.api!.pcPairStart();
      setState(() {
        _code = r['code'] as String;
        _codeUntil = DateTime.now().add(Duration(seconds: (r['expires_in'] as num).toInt()));
      });
    } catch (e) {
      _snack(e.toString());
    }
  }

  Future<void> _search() async {
    final q = _q.text.trim();
    if (q.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.pcSearch(q);
      if (mounted) setState(() => _results = r);
      if (r.isEmpty) _snack('Kuch nahi mila. Doosre shabd try kijiye.');
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pull(Map<String, dynamic> f) async {
    setState(() => _busy = true);
    try {
      final r = await app.api!.pcPull(f['path'] as String);
      await Native.openExternal(url: app.api!.absolute(r['url'] as String));
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendToPc() async {
    final res = await FilePicker.platform.pickFiles(withData: true);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await app.api!.pcSend(f.name, f.bytes!);
      _snack(r['message'] as String? ?? 'PC par bhej diya');
      _load(quiet: true);
    } catch (e) {
      _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _pairCard() {
    final left = _codeUntil?.difference(DateTime.now()).inSeconds ?? 0;
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('PC jodiye', style: display(20)),
        const SizedBox(height: 6),
        const Text('Office ya ghar ka computer — aapka personal PC — Hoola se jodiye. Phir phone se boliye: "Sharma ka bill bhejo", '
            '"Tally mein kiska paisa baaki hai", "kal ka quotation print karo".',
            style: TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
        const SizedBox(height: 14),
        const Text('1. PC par Hoola Desktop download kijiye (Windows)', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Row(children: [
          Expanded(child: GlassButton(label: 'Link copy', height: 40, onTap: () {
            Clipboard.setData(const ClipboardData(text: desktopDownload));
            _snack('Link copy ho gaya. PC ke browser mein kholiye.');
          })),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'WhatsApp par bhejo', height: 40, onTap: () =>
              Native.openExternal(url: 'https://wa.me/?text=${Uri.encodeComponent('Santosh Desktop (PC ke liye): $desktopDownload')}'))),
        ]),
        const SizedBox(height: 14),
        const Text('2. PC par Hoola Desktop mein yeh code daaliye', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        if (_code != null && left > 0) ...[
          Center(child: SelectableText(_code!.replaceAllMapped(RegExp(r'^(\d{3})(\d{3})$'), (m) => '${m[1]} ${m[2]}'),
              style: display(40, color: C.accent))),
          Center(child: Text('${left ~/ 60}:${(left % 60).toString().padLeft(2, '0')} mein khatam · PC judte hi yahan dikhega',
              style: const TextStyle(color: C.faint, fontSize: 12))),
        ] else
          GradientButton(label: 'Code banaiye', height: 48, onTap: _newCode),
      ]),
    );
  }

  Widget _deviceCard(Map<String, dynamic> d) {
    final online = d['online'] == true;
    final folders = (d['folders'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final tally = Map<String, dynamic>.from(d['tally'] as Map? ?? const {});
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 10, height: 10, decoration: BoxDecoration(shape: BoxShape.circle, color: online ? C.ok : C.faint)),
          const SizedBox(width: 8),
          Expanded(child: Text(d['name'] as String? ?? 'PC', style: display(18))),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded, color: C.muted),
            onSelected: (v) async {
              if (v == 'remove') {
                await app.api!.pcRemove(d['id'] as String);
                _load();
              }
            },
            itemBuilder: (_) => const [PopupMenuItem(value: 'remove', child: Text('Is PC ko hataiye'))],
          ),
        ]),
        Text(
            online
                ? (d['paused'] == true ? 'Juda hai, par PC par "Rokiye" on hai' : 'Online · ${d['os'] ?? ''}')
                : 'Offline · aakhri baar ${_ago(d['last_seen'] as String?)}. PC on karke Hoola Desktop kholiye.',
            style: TextStyle(color: online ? C.ok : C.muted, fontSize: 12.5)),
        const SizedBox(height: 10),
        Text('Share kiye folder: ${folders.isEmpty ? 'koi nahi (PC par folder jodiye)' : folders.map((f) => f['label']).join(', ')}',
            style: const TextStyle(fontSize: 12.5, color: C.chip)),
        Text('${d['indexed'] ?? 0} files dhoondhne layak', style: const TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 4),
        Text(
            tally['available'] == true
                ? 'TallyPrime: juda hua (${(tally['companies'] as List? ?? const []).join(', ')})'
                : 'TallyPrime: nahi mila (Tally kholiye; Help > Settings > Connectivity > TallyPrime acts as Server)',
            style: TextStyle(fontSize: 12, color: tally['available'] == true ? C.ok : C.faint)),
      ]),
    );
  }

  /// v0.200 Hoola ka apna PC — the cloud computer Hoola itself works on. Shown on the same
  /// screen but always as its own thing, never mixed into the user's personal PC list.
  Widget _hoolaCard(Map<String, dynamic> d) {
    final online = d['online'] == true;
    final paused = d['paused'] == true;
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.cloud_rounded, size: 20, color: online ? C.ok : C.faint),
          const SizedBox(width: 8),
          Expanded(child: Text(d['name'] as String? ?? 'Hoola PC', style: display(18))),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert_rounded, color: C.muted),
            onSelected: (v) async {
              if (v == 'remove') {
                await app.api!.pcRemove(d['id'] as String);
                _load();
              }
            },
            itemBuilder: (_) => const [PopupMenuItem(value: 'remove', child: Text('Is PC ko hataiye'))],
          ),
        ]),
        Text(
            online
                ? (paused ? 'Hoola ka apna cloud computer · roka hua hai' : 'Hamesha on · Hoola ka apna cloud computer')
                : 'Hoola ka apna cloud computer · thodi der mein apne aap jud jayega',
            style: TextStyle(color: online ? C.ok : C.muted, fontSize: 12.5)),
        const SizedBox(height: 6),
        const Text('Yahan Hoola khud kaam karta hai — Chrome, files, software install. Aapke personal PC se alag, iske liye Hoola se boliye: "apne computer pe…".',
            style: TextStyle(color: C.chip, fontSize: 12.5, height: 1.35)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    // v0.200 MERA PC = USER PERSONAL PC FEATURE: this screen is the user's own computer(s).
    // Hoola ka apna PC (the cloud computer Hoola works on) is a different thing and gets its
    // own clearly-labeled section so the two are never confused.
    final hoola = _devices.where((d) => d['kind'] == 'hoola_pc').toList();
    final personal = _devices.where((d) => d['kind'] != 'hoola_pc').toList();
    final online = personal.any((d) => d['online'] == true);
    return Scaffold(
      appBar: AppBar(title: const Text('Mera PC'), backgroundColor: Colors.transparent),
      body: Aurora(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            if (_loaded && personal.isEmpty) _pairCard(),
            if (hoola.isNotEmpty) ...[
              const SizedBox(height: 6),
              const Caption('HOOLA KA APNA PC'),
              const SizedBox(height: 8),
              for (final d in hoola) Padding(padding: const EdgeInsets.only(bottom: 10), child: _hoolaCard(d)),
              const SizedBox(height: 10),
            ],
            if (personal.isNotEmpty && hoola.isNotEmpty) ...[
              const Caption('AAPKA PERSONAL PC'),
              const SizedBox(height: 8),
            ],
            for (final d in personal) Padding(padding: const EdgeInsets.only(bottom: 10), child: _deviceCard(d)),
            if (personal.isNotEmpty) ...[
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: GlassButton(label: 'Phone se PC par bhejo', icon: Icons.upload_rounded, height: 46,
                    onTap: online && !_busy ? _sendToPc : null)),
                const SizedBox(width: 8),
                Expanded(child: GlassButton(label: 'Doosra PC jodiye', icon: Icons.add_rounded, height: 46, onTap: () async {
                  await _newCode();
                  if (!mounted || _code == null) return;
                  showDialog(context: context, builder: (_) => AlertDialog(
                      backgroundColor: C.bgBottom,
                      content: Column(mainAxisSize: MainAxisSize.min, children: [
                        const Text('Naye PC par Hoola Desktop mein yeh code daaliye (10 min)'),
                        const SizedBox(height: 10),
                        SelectableText(_code!, style: display(36, color: C.accent)),
                      ])));
                })),
              ]),
            ],
            if (_devices.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Caption('PC PAR DHOONDHIYE'),
              Glass(
                radius: 18,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
                child: TextField(
                  controller: _q,
                  enabled: online,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _search(),
                  style: const TextStyle(color: C.ink, fontSize: 15),
                  decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.search_rounded, color: C.muted),
                      suffixIcon: _busy ? const Padding(padding: EdgeInsets.all(12), child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))) : null,
                      hintText: online ? 'Party ka naam, invoice no, GST, bank statement…' : 'PC offline hai',
                      border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),
                ),
              ),
              const SizedBox(height: 8),
              for (final f in _results)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Glass(
                    radius: 16,
                    padding: const EdgeInsets.fromLTRB(14, 10, 6, 10),
                    child: Row(children: [
                      Icon(switch (f['kind']) { 'pdf' => Icons.picture_as_pdf_rounded, 'excel' => Icons.grid_on_rounded,
                        'image' => Icons.image_rounded, 'word' => Icons.description_rounded, _ => Icons.insert_drive_file_rounded },
                          color: C.accentSoft),
                      const SizedBox(width: 10),
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(f['name'] as String? ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                        Text('${(f['category'] as String? ?? '').isEmpty ? '' : '${f['category']} · '}${_size(f['size'] as num?)} · ${f['modified'] ?? ''}',
                            style: const TextStyle(color: C.faint, fontSize: 11.5)),
                      ])),
                      IconButton(tooltip: 'Phone par lao', icon: const Icon(Icons.download_rounded, color: C.teal), onPressed: _busy ? null : () => _pull(f)),
                    ]),
                  ),
                ),
              const SizedBox(height: 14),
              const Caption('SANTOSH NE PC PAR KYA KIYA'),
              Glass(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                child: Column(children: [
                  if (_jobs.isEmpty) const Padding(padding: EdgeInsets.all(10), child: Text('Abhi tak kuch nahi', style: TextStyle(color: C.faint))),
                  for (final j in _jobs.take(30))
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Icon(j['status'] == 'done' ? Icons.check_circle_rounded : (j['status'] == 'sent' ? Icons.schedule_rounded : Icons.error_outline_rounded),
                            size: 16, color: j['status'] == 'done' ? C.ok : (j['status'] == 'sent' ? C.faint : C.warn)),
                        const SizedBox(width: 8),
                        Expanded(child: Text('${j['summary']}${(j['error'] as String? ?? '').isEmpty ? '' : ' · ${j['error']}'}',
                            style: const TextStyle(fontSize: 12.5))),
                        Text(_ago(j['at'] as String?), style: const TextStyle(color: C.faint, fontSize: 11)),
                      ]),
                    ),
                ]),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

/// Chat card for a file Santosh brought from the PC, or a PDF Santosh made (source 'bazar': invoice, slip, receipt).
class PcFileCard extends StatelessWidget {
  const PcFileCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  bool get _made => v['source'] == 'bazar';

  /// Santosh-made PDFs get a fresh signed link on every tap, so an old chat card still opens.
  Future<String> _url() async {
    final docId = v['doc_id'] as String?;
    if (_made && docId != null && app.api != null) {
      try {
        return await app.api!.bazarFileUrl(docId);
      } catch (_) {}
    }
    return app.api?.absolute(v['url'] as String? ?? '') ?? '';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(_made ? Icons.picture_as_pdf_rounded : Icons.computer_rounded, color: C.teal),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(v['name'] as String? ?? 'File', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
              Text(_made ? 'Hoola ne banaya · ${_size(v['size'] as num?)} · PDF' : 'PC se · ${_size(v['size'] as num?)} · poori quality',
                  style: const TextStyle(color: C.faint, fontSize: 12)),
            ])),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: GradientButton(label: 'Kholiye', height: 42, onTap: () async => Native.openExternal(url: await _url()))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Link bhejo', height: 42, onTap: () async {
              final url = await _url();
              await Native.openExternal(url: 'https://wa.me/?text=${Uri.encodeComponent('${v['name']}: $url')}');
            })),
          ]),
          Padding(padding: const EdgeInsets.only(top: 6), child: Text(_made ? 'Bheja gaya link 24 ghante chalega.' : 'Link 24 ghante chalega.',
              style: const TextStyle(color: C.faint, fontSize: 11.5))),
        ]),
      ),
    );
  }
}
