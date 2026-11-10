import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

/// v0.127 Hoola Screen: a connected mini screen / TV / monitor shows Hoola's live work (view only).
/// The phone stays the remote: every Haan, payment and OTP is still done on the phone.
class ScreenLinkScreen extends StatefulWidget {
  const ScreenLinkScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<ScreenLinkScreen> createState() => _ScreenLinkScreenState();
}

class _ScreenLinkScreenState extends State<ScreenLinkScreen> {
  Map<String, dynamic> _info = const {};
  Map<String, dynamic>? _board;
  bool _busy = false;
  Timer? _t;

  @override
  void initState() {
    super.initState();
    _load(sync: true);
    _t = Timer.periodic(const Duration(seconds: 3), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _load({bool sync = false}) async {
    final info = sync ? await widget.app.screenSync() : await Native.screenInfo();
    Map<String, dynamic>? b;
    try {
      b = await widget.app.api!.screenPreview();
    } catch (_) {}
    if (mounted) setState(() {
      _info = info;
      _board = b ?? _board;
    });
  }

  Future<void> _set({bool? on, bool? awake}) async {
    final r = await widget.app.screenSync(on: on, awake: awake);
    if (mounted) setState(() => _info = r);
  }

  Future<void> _revoke() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Close all links?'),
        content: const Text('The board will stop on the screens / browsers where the old link is open. A new link will be made for this phone automatically.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Close')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await widget.app.screenRevoke();
      await _load(sync: true);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Old links closed. New link ready.')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _step(String n, String t, String d) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          CircleAvatar(radius: 12, backgroundColor: C.accent, child: Text(n, style: const TextStyle(color: C.onAccent, fontSize: 12, fontWeight: FontWeight.w800))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(t, style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(d, style: const TextStyle(color: C.muted, fontSize: 13)),
          ])),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final connected = _info['connected'] == true;
    final showing = _info['showing'] == true;
    final on = _info['on'] != false;
    final url = widget.app.screenUrl;
    final b = _board;
    final now = (b?['now'] as List?) ?? const [];
    final cards = (b?['cards'] as List?) ?? const [];
    return Scaffold(
      appBar: AppBar(title: const Text('Hoola Screen')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Glass(
          tint: connected ? C.ok : null,
          opacity: connected ? .12 : .07,
          child: Row(children: [
            Icon(connected ? Icons.connected_tv_rounded : Icons.tv_off_rounded, size: 36, color: connected ? C.ok : C.faint),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(connected ? 'Screen linked: ${_info['name'] ?? 'Screen'}' : 'No screen linked yet',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              Text(
                  connected
                      ? (showing
                          ? '${widget.app.aName}\'s live board is showing there${_info['width'] != null ? ' (${_info['width']}x${_info['height']})' : ''}.'
                          : on ? 'Board is opening...' : 'Board is off: turn the switch on below.')
                      : 'The board will show by itself once you connect a screen by HDMI cable or wireless display.',
                  style: const TextStyle(color: C.muted, fontSize: 13)),
            ])),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          child: Column(children: [
            SwitchListTile(
              value: on,
              onChanged: (v) => _set(on: v),
              title: const Text('Show the board on the linked screen'),
              subtitle: const Text('Off = the screen will just mirror the phone'),
            ),
            SwitchListTile(
              value: _info['awake'] != false,
              onChanged: (v) => _set(awake: v),
              title: const Text('Keep the phone screen on while the board runs'),
              subtitle: const Text('Android stops the board when the phone locks; so keeping it on is better'),
            ),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('How to link a screen', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 10),
            _step('1', 'Cable (most reliable)', 'Connect a mini screen / TV with a USB-C to HDMI adapter. The phone needs "DisplayPort over USB-C" (Samsung S / Tab, many flagships). Many budget phones do not have it.'),
            _step('2', 'Wireless display', 'Open the phone\'s Cast / Screen Cast / Smart View and choose a screen. The board shows on screens that support Miracast; some phones only mirror.'),
            _step('3', 'Any browser (wireless)', 'Tablet, laptop, old phone or a smart-TV browser: open the link below there. The same live board shows.'),
            const Text('The board is view-only. Approvals, payments and OTPs are only on this phone.', style: TextStyle(color: C.warn, fontSize: 13)),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Link for browser', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 6),
            SelectableText(url.isEmpty ? 'Making the link...' : url, style: const TextStyle(color: C.muted, fontSize: 12)),
            const SizedBox(height: 4),
            const Text('The link works for 30 days. Anyone who gets the link can see the board, so open it only on your own screens.',
                style: TextStyle(color: C.faint, fontSize: 12)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton.icon(
                onPressed: url.isEmpty
                    ? null
                    : () {
                        Clipboard.setData(ClipboardData(text: url));
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Link copied')));
                      },
                icon: const Icon(Icons.copy_rounded, size: 18),
                label: const Text('Copy'),
              ),
              OutlinedButton.icon(
                onPressed: url.isEmpty ? null : () => Native.openExternal(url: url),
                icon: const Icon(Icons.open_in_browser_rounded, size: 18),
                label: const Text('View on this phone'),
              ),
              OutlinedButton.icon(
                onPressed: _busy ? null : _revoke,
                icon: const Icon(Icons.link_off_rounded, size: 18),
                label: const Text('Close all links'),
              ),
            ]),
          ]),
        ),
        const SizedBox(height: 12),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('On the board now', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 6),
            if (b == null) const Text('...', style: TextStyle(color: C.muted)),
            if (b != null && now.isEmpty && cards.isEmpty)
              const Text('Empty for now. Ask for some work and it will show live there.', style: TextStyle(color: C.muted)),
            for (final s in now)
              ListTile(dense: true, contentPadding: EdgeInsets.zero, leading: const Icon(Icons.autorenew_rounded, color: C.accent),
                  title: Text('${(s as Map)['label'] ?? ''}')),
            for (final c in cards.take(3))
              ListTile(dense: true, contentPadding: EdgeInsets.zero, leading: const Icon(Icons.pending_actions_rounded, color: C.warn),
                  title: Text('${(c as Map)['title'] ?? ''}'), subtitle: Text('${c['body'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis)),
          ]),
        ),
      ]),
    );
  }
}
