import 'package:flutter/material.dart';

import '../native.dart';
import 'glass.dart';

/// "Phone lock par bhi Santosh": checks what can stop a call / background work on this phone and opens the right
/// Android or phone-maker setting. Only opens settings pages (Google Play allows this); never changes them itself.
class LockSafe {
  static Future<Map<String, dynamic>> status() async => await Native.callStatus();

  /// Short reason the call may stop on lock, or null when everything looks fine.
  static String? issue(Map<String, dynamic> s, {bool inCall = false}) {
    if (s['notifications'] == false) return 'Notifications band hain — lock par call ruk sakti hai';
    if (inCall && s['running'] != true) {
      final p = (s['problem'] as String? ?? '').trim();
      return 'Lock-safe mode shuru nahi hua${p.isEmpty ? '' : ' ($p)'}';
    }
    if (s['batteryOptimized'] == true && _strict(s['brand'] as String? ?? '')) {
      return 'Phone ka battery saver Santosh ko lock par rok sakta hai';
    }
    return null;
  }

  static bool _strict(String brand) =>
      const ['vivo', 'iqoo', 'oppo', 'realme', 'oneplus', 'xiaomi', 'redmi', 'poco', 'huawei', 'honor', 'infinix', 'tecno', 'itel']
          .any(brand.contains);

  static List<String> steps(String brand) {
    if (brand.contains('vivo') || brand.contains('iqoo')) {
      return [
        'Settings → Battery → Background power consumption management → Santosh → "Allow" (High background power)',
        'Settings → Apps → Santosh → Autostart: ON',
        'Recent apps mein Santosh ko neeche kheench kar 🔒 lock kar dijiye',
        'Settings → Apps → Santosh → Notifications: ON (sab allow)',
      ];
    }
    if (brand.contains('oppo') || brand.contains('realme') || brand.contains('oneplus')) {
      return [
        'Settings → Battery → Santosh → "Allow background activity" / Unrestricted',
        'Settings → Apps → Santosh → Auto launch / Autostart: ON',
        'Recent apps mein Santosh ke upar ⋮ → Lock',
        'Notifications: ON',
      ];
    }
    if (brand.contains('xiaomi') || brand.contains('redmi') || brand.contains('poco')) {
      return [
        'Settings → Apps → Santosh → Battery saver → "No restrictions"',
        'Settings → Apps → Santosh → Autostart: ON',
        'Recent apps mein Santosh ko lock kar dijiye',
        'Notifications: ON',
      ];
    }
    if (brand.contains('samsung')) {
      return [
        'Settings → Apps → Santosh → Battery → Unrestricted',
        'Settings → Battery → Background usage limits → Santosh ko "Never sleeping apps" mein daaliye',
        'Notifications: ON',
      ];
    }
    return ['Settings → Apps → Santosh → Battery → Unrestricted', 'Notifications: ON'];
  }

  static Future<void> showFix(BuildContext context) async {
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
            Text('Phone lock par bhi Santosh', style: display(22)),
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
