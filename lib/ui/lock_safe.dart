import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';
import 'keep_alive.dart' show HoolaKeepAlive;

/// "Phone lock par bhi Santosh": checks what can stop a call / background work on this phone and opens the right
/// Android or phone-maker setting. Only opens settings pages (Google Play allows this); never changes them itself.
class LockSafe {
  /// Set at app start so the sheet can fetch this phone maker's own steps (dontkillmyapp.com) from the server.
  static Santosh? app;
  static Future<Map<String, dynamic>> status() async => await Native.callStatus();

  /// Short reason the call may stop on lock, or null when everything looks fine.
  static String? issue(Map<String, dynamic> s, {bool inCall = false}) {
    if (s['notifications'] == false) return 'Notifications band hain — lock par call ruk sakti hai';
    if (inCall && s['running'] != true) {
      final p = (s['problem'] as String? ?? '').trim();
      return 'Lock-safe mode shuru nahi hua${p.isEmpty ? '' : ' ($p)'}';
    }
    if (s['batteryOptimized'] == true && _strict(s['brand'] as String? ?? '')) {
      return 'Phone ka battery saver Hoola ko lock par rok sakta hai';
    }
    return null;
  }

  static bool _strict(String brand) =>
      const ['vivo', 'iqoo', 'oppo', 'realme', 'oneplus', 'xiaomi', 'redmi', 'poco', 'huawei', 'honor', 'infinix', 'tecno', 'itel']
          .any(brand.contains);

  static List<String> steps(String brand) {
    if (brand.contains('vivo') || brand.contains('iqoo')) {
      return [
        'Settings → Battery → Background power consumption management → Hoola → "Allow" (High background power)',
        'Settings → Apps → Hoola → Autostart: ON',
        'Recent apps mein Hoola ko neeche kheench kar 🔒 lock kar dijiye',
        'Settings → Apps → Hoola → Notifications: ON (sab allow)',
      ];
    }
    if (brand.contains('oppo') || brand.contains('realme') || brand.contains('oneplus')) {
      return [
        'Settings → Battery → Hoola → "Allow background activity" / Unrestricted',
        'Settings → Apps → Hoola → Auto launch / Autostart: ON',
        'Recent apps mein Hoola ke upar ⋮ → Lock',
        'Notifications: ON',
      ];
    }
    if (brand.contains('xiaomi') || brand.contains('redmi') || brand.contains('poco')) {
      return [
        'Settings → Apps → Hoola → Battery saver → "No restrictions"',
        'Settings → Apps → Hoola → Autostart: ON',
        'Recent apps mein Hoola ko lock kar dijiye',
        'Notifications: ON',
      ];
    }
    if (brand.contains('samsung')) {
      return [
        'Settings → Apps → Hoola → Battery → Unrestricted',
        'Settings → Battery → Background usage limits → Hoola ko "Never sleeping apps" mein daaliye',
        'Notifications: ON',
      ];
    }
    return ['Settings → Apps → Hoola → Battery → Unrestricted', 'Notifications: ON'];
  }

  static Future<void> showFix(BuildContext context) async {
    // v0.56: the full checklist screen (problems from Android itself + "Kholo" per line); the sheet stays as fallback
    if (app?.api != null) return HoolaKeepAlive.open(context, app!);
    final s = await status();
    if (!context.mounted) return;
    final brand = (s['brand'] as String? ?? '').toLowerCase();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF151A24),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Phone lock par bhi Hoola', style: display(22)),
            const SizedBox(height: 4),
            Text(brand.isEmpty ? 'Yeh settings ek baar kar dijiye:' : '${brand[0].toUpperCase()}${brand.substring(1)} phone par yeh ek baar kar dijiye:',
                style: const TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 12),
            for (final (i, t) in steps(brand).indexed)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${i + 1}. ', style: const TextStyle(fontWeight: FontWeight.w800, color: C.accent)),
                  Expanded(child: Text(t, style: const TextStyle(fontSize: 13.5, height: 1.35))),
                ]),
              ),
            if (brand.isNotEmpty && app?.api != null) MakerSteps(app: app!, brand: brand),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton.tonal(onPressed: Native.openAutostart, child: const Text('Autostart / Background')),
              FilledButton.tonal(onPressed: Native.askBattery, child: const Text('Battery')),
              FilledButton.tonal(onPressed: Native.openNotificationSettings, child: const Text('Notifications')),
            ]),
            const SizedBox(height: 6),
          ]),
        ),
      ),
    );
  }
}

/// v0.49 The phone maker's exact steps from dontkillmyapp.com (fetched by our server, cached; credit shown).
class MakerSteps extends StatefulWidget {
  const MakerSteps({super.key, required this.app, required this.brand});
  final Santosh app;
  final String brand;
  @override
  State<MakerSteps> createState() => MakerStepsState();
}

class MakerStepsState extends State<MakerSteps> {
  late final Future<Map<String, dynamic>> _f = widget.app.api!.keepalive(widget.brand);
  bool _open = false;

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (context, snap) {
          final d = snap.data ?? const {};
          final steps = List<String>.from((d['steps'] as List? ?? const []).map((e) => '$e'));
          if (steps.isEmpty) return const SizedBox.shrink();
          return Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              InkWell(
                onTap: () => setState(() => _open = !_open),
                child: Row(children: [
                  Expanded(
                    child: Text('${d['name'] ?? widget.brand} ke liye poore steps${d['rank'] != null ? ' (sakhti: ${d['rank']}/5)' : ''}',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                  ),
                  Icon(_open ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: C.muted),
                ]),
              ),
              if (_open) ...[
                const SizedBox(height: 6),
                for (final t in steps.take(18))
                  Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(t, style: const TextStyle(fontSize: 12.5, height: 1.35))),
              ],
              Text('Source: ${d['credit'] ?? 'dontkillmyapp.com'}', style: const TextStyle(color: C.faint, fontSize: 10.5)),
            ]),
          );
        },
      );
}

/// Small warning strip on the call screen when the call may stop on lock.
class LockSafeBanner extends StatelessWidget {
  const LockSafeBanner({super.key, required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        child: Material(
          color: const Color(0x2EFFB15C),
          borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => LockSafe.showFix(context),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(children: [
                const Icon(Icons.lock_clock_rounded, size: 18, color: Color(0xFFFFD9A8)),
                const SizedBox(width: 8),
                Expanded(child: Text(text, style: const TextStyle(fontSize: 12.5, color: Color(0xFFFFD9A8), fontWeight: FontWeight.w600))),
                const Text('Theek karo', style: TextStyle(fontSize: 12.5, color: C.accent, fontWeight: FontWeight.w800)),
              ]),
            ),
          ),
        ),
      );
}
