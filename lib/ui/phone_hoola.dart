import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// v0.63 "Phone mein Hoola": Hoola as the phone's assistant, the floating bubble (Android's Bubbles API), the
/// home-screen widget and in-app updates for the GitHub APK. Everything is switched on by the owner; nothing reads
/// the screen in the background.
class PhoneHoolaScreen extends StatefulWidget {
  const PhoneHoolaScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PhoneHoolaScreen> createState() => _PhoneHoolaScreenState();
}

class _PhoneHoolaScreenState extends State<PhoneHoolaScreen> with WidgetsBindingObserver {
  Map<String, dynamic> _assist = const {};
  Map<String, dynamic> _bubble = const {};
  Map<String, dynamic> _ver = const {};
  int _widgets = 0;
  Map<String, dynamic>? _latest;
  bool _checking = false;

  Santosh get app => widget.app;

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
    if (s == AppLifecycleState.resumed) _load();     // back from Android settings
  }

  Future<void> _load() async {
    final a = await Native.assistInfo();
    final b = await Native.bubbleInfo();
    final v = await Native.updateInfo();
    final w = await Native.widgetCount();
    if (!mounted) return;
    setState(() {
      _assist = a;
      _bubble = b;
      _ver = v;
      _widgets = w;
    });
    if (_latest == null && v['channel'] == 'github') _check();
  }

  Future<void> _check({bool force = false}) async {
    if (app.api == null) return;
    setState(() => _checking = true);
    try {
      final r = await app.api!.appLatest('${_ver['version'] ?? ''}', force: force);
      if (mounted) setState(() => _latest = r);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  void _snack(String t) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t)));

  Widget _card({required IconData icon, required Color color, required String title, required String sub,
      required List<Widget> children}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: color, size: 26),
            const SizedBox(width: 10),
            Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
          ]),
          const SizedBox(height: 6),
          Text(sub, style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.4)),
          const SizedBox(height: 10),
          ...children,
        ]),
      ),
    );
  }

  Widget _status(bool ok, String yes, String no) => Row(children: [
        Icon(ok ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded, size: 18, color: ok ? C.ok : C.muted),
        const SizedBox(width: 6),
        Expanded(child: Text(ok ? yes : no, style: TextStyle(fontSize: 13, color: ok ? C.ok : C.ink, fontWeight: FontWeight.w600))),
      ]);

  @override
  Widget build(BuildContext context) {
    final name = app.aName;
    final isDefault = _assist['default'] == true;
    final bubbleOk = _bubble['supported'] == true;
    final bubbleOn = _bubble['on'] == true;
    final github = (_ver['channel'] ?? 'github') == 'github';
    final latest = _latest;
    final available = latest?['available'] == true;
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('Phone mein $name')),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
        _card(
          icon: Icons.assistant_rounded,
          color: C.accent,
          title: '$name ko phone ka assistant banaiye',
          sub: 'Home button daba ke rakhiye (ya corner se swipe): $name khulega aur jo screen aap dekh rahi hain uska '
              'screenshot + text chat mein laga dega — "is message ka jawab likho", "yeh offer sahi hai?". Sirf tab, jab '
              'aap khud bulayengi; password / OTP wale khaane kabhi nahi liye jaate.',
          children: [
            _status(isDefault, '$name aapka assistant hai', 'Abhi koi aur assistant set hai'),
            const SizedBox(height: 8),
            if (!isDefault)
              const Text('Settings > Apps > Default apps > Digital assistant app > Hoola chuniye. Screen ke liye "Use text '
                  'from screen" aur "Use screenshot" ON rakhiye.', style: TextStyle(fontSize: 12.5, height: 1.4)),
            const SizedBox(height: 8),
            FilledButton.tonal(onPressed: Native.assistSettings, child: Text(isDefault ? 'Settings dekho' : 'Set karo')),
          ],
        ),
        _card(
          icon: Icons.bubble_chart_rounded,
          color: C.teal,
          title: 'Floating $name (bubble)',
          sub: 'Kisi bhi app ke upar $name ka chhota gol chehra. Tap karo: chhoti chat khulti hai, likho ya 🎙 se call. '
              'Android ka apna Bubbles feature hai — koi "draw over apps" permission nahi; bubble ko neeche kheench kar '
              'kabhi bhi hata sakti hain.',
          children: [
            if (!bubbleOk)
              const Text('Bubble Android 11 ya naye phone par chalta hai.', style: TextStyle(fontSize: 12.5, color: C.muted))
            else ...[
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: bubbleOn,
                title: Text(bubbleOn ? 'Bubble chalu hai' : 'Bubble band hai', style: const TextStyle(fontWeight: FontWeight.w700)),
                onChanged: (v) async {
                  final r = await Native.bubble(v, name);
                  await _load();
                  if (v && r['allowed'] == false && mounted) {
                    _snack('Phone ki settings mein Hoola ke liye bubbles allow kijiye.');
                    await Native.bubbleSettings();
                  }
                },
              ),
              if (bubbleOn && _bubble['allowed'] != true)
                TextButton(onPressed: Native.bubbleSettings, child: const Text('Bubbles allow karo (Android settings)')),
            ],
          ],
        ),
        _card(
          icon: Icons.widgets_rounded,
          color: const Color(0xFFFFB15C),
          title: 'Home screen par $name',
          sub: 'Widget: $name ki aakhri baat, agla reminder, aur do bade button — 🎙 Bolo (seedha call) aur ✍ Likho.',
          children: [
            _status(_widgets > 0, 'Widget laga hua hai', 'Widget nahi laga'),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: () async {
                final ok = await Native.widgetPin();
                await app.widgetSync();
                if (!ok && mounted) {
                  _snack('Home screen ko daba ke rakhiye > Widgets > Hoola chuniye.');
                }
              },
              child: const Text('Widget lagao'),
            ),
          ],
        ),
        if (github)
          _card(
            icon: Icons.system_update_rounded,
            color: C.ok,
            title: 'App update',
            sub: 'Abhi: v${_ver['version'] ?? '?'}. Naya version GitHub se aata hai; file ka checksum aur signature check '
                'hota hai, phir Android khud "Install?" poochhta hai.',
            children: [
              if (_checking) const LinearProgressIndicator(minHeight: 3),
              if (latest != null && !_checking)
                Text(available ? 'Naya: v${latest['version']} (${hoolaMb(latest['size'])})' : 'Aap sabse naye version par hain.',
                    style: TextStyle(fontWeight: FontWeight.w700, color: available ? C.accent : C.ok)),
              if (available && '${latest?['notes'] ?? ''}'.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('${latest!['notes']}', maxLines: 5, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: C.muted)),
                ),
              const SizedBox(height: 8),
              Wrap(spacing: 8, children: [
                if (available)
                  FilledButton(onPressed: () => AppUpdater.run(context, latest!), child: const Text('Update karo')),
                OutlinedButton(onPressed: _checking ? null : () => _check(force: true), child: const Text('Check karo')),
              ]),
            ],
          ),
      ]),
    );
  }
}

String hoolaMb(dynamic size) {
  final n = (size is num) ? size.toDouble() : 0.0;
  return n <= 0 ? '' : '${(n / 1024 / 1024).toStringAsFixed(0)} MB';
}

/// Downloads the new APK (progress + Rok do), then hands it to Android's installer.
class AppUpdater {
  static Future<void> run(BuildContext context, Map<String, dynamic> rel) async {
    final info = await Native.updateInfo();
    if (info['channel'] != 'github') return;
    if (info['can_install'] != true) {
      if (!context.mounted) return;
      final go = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: C.bgBottom,
          title: const Text('Ek permission chahiye'),
          content: const Text('Update install karne ke liye Android poochhega: "Is source se apps install karein?" — '
              'Hoola ke liye ON kijiye aur wapas aaiye.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Baad mein')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Settings kholo')),
          ],
        ),
      );
      if (go == true) await Native.updatePermission();
      return;
    }
    if (!context.mounted) return;
    final path = await showDialog<String>(context: context, barrierDismissible: false, builder: (_) => _DownloadDialog(rel: rel));
    if (path == null || !context.mounted) return;
    final err = await Native.updateInstall(path);
    if (!context.mounted) return;
    if (err == 'permission') {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('"Install unknown apps" ON karke dobara "Update karo" dabaiye.')));
    } else if (err != null && err.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  /// Once a day after start: a newer version -> one gentle sheet per version (GitHub build only).
  static Future<void> maybeOffer(BuildContext context, Santosh app) async {
    try {
      final info = await Native.updateInfo();
      if (info['channel'] != 'github' || app.api == null) return;
      final p = await SharedPreferences.getInstance();
      final now = DateTime.now().millisecondsSinceEpoch;
      if (now - (p.getInt('upd_checked') ?? 0) < 20 * 3600 * 1000) return;
      await p.setInt('upd_checked', now);
      final r = await app.api!.appLatest('${info['version'] ?? ''}');
      if (r['available'] != true || p.getString('upd_offered') == r['version'] || !context.mounted) return;
      await p.setString('upd_offered', '${r['version']}');
      final go = await showModalBottomSheet<bool>(
        context: context,
        backgroundColor: const Color(0xFF151A24),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        builder: (ctx) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 14),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Naya ${app.aName} aaya hai: v${r['version']}', style: display(20)),
              const SizedBox(height: 6),
              Text('${r['notes'] ?? ''}', maxLines: 6, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: C.muted, fontSize: 13, height: 1.4)),
              const SizedBox(height: 12),
              Row(children: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Baad mein')),
                const Spacer(),
                FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text('Update karo (${hoolaMb(r['size'])})')),
              ]),
            ]),
          ),
        ),
      );
      if (go == true && context.mounted) await run(context, r);
    } catch (_) {}
  }
}

class _DownloadDialog extends StatefulWidget {
  const _DownloadDialog({required this.rel});
  final Map<String, dynamic> rel;
  @override
  State<_DownloadDialog> createState() => _DownloadDialogState();
}

class _DownloadDialogState extends State<_DownloadDialog> {
  int _pct = 0;
  String? _err;
  Timer? _poll;
  bool _closed = false;

  void _close(String? path) {
    if (_closed || !mounted) return;
    _closed = true;
    Navigator.of(context).pop(path);
  }

  @override
  void initState() {
    super.initState();
    final r = widget.rel;
    Native.updateDownload('${r['apk_url']}', '${r['sha256'] ?? ''}', (r['size'] as num? ?? 0).toInt()).then((res) {
      final path = res['path'] as String?;
      if (path != null && path.isNotEmpty) {
        _close(path);
      } else if (mounted && !_closed) {
        final e = '${res['error'] ?? 'Download nahi ho paya'}';
        if (e == 'cancelled') {
          _close(null);
        } else {
          setState(() => _err = e);
        }
      }
    });
    _poll = Timer.periodic(const Duration(milliseconds: 400), (_) async {
      final p = await Native.updateProgress();
      if (mounted && p >= 0) setState(() => _pct = p);
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PopScope(
        canPop: false,
        child: AlertDialog(
          backgroundColor: C.bgBottom,
          title: Text(_err == null ? 'Naya version aa raha hai' : 'Update nahi hua'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (_err == null) ...[
              Text('v${widget.rel['version']} · ${hoolaMb(widget.rel['size'])}', style: const TextStyle(color: C.muted, fontSize: 13)),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(value: _pct <= 0 ? null : _pct / 100, minHeight: 8),
              ),
              const SizedBox(height: 6),
              Text(_pct >= 100 ? 'Check kar raha hoon…' : '$_pct%', style: const TextStyle(fontWeight: FontWeight.w700)),
            ] else
              Text(_err!, style: const TextStyle(fontSize: 13.5)),
          ]),
          actions: [
            TextButton(
              onPressed: () async {
                if (_err == null) await Native.updateCancel();
                _close(null);
              },
              child: Text(_err == null ? 'Rok do' : 'Theek hai'),
            ),
          ],
        ),
      );
}
