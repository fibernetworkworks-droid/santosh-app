import 'package:flutter/material.dart';

import 'glass.dart';

/// One look for every plugin and MCP server: the brand's real logo (served by Hoola, fetched from the brand's own
/// site), a fixed-size card with the name, two lines about it and an action button that always sits in the same place.

/// What a plugin really does, in simple words (shown as a small chip).
String levelText(Map<String, dynamic> p) {
  final st = p['status'] as String? ?? '';
  final ex = p['executor'] as String? ?? '';
  return switch (st) {
    'needs_link' => 'Link karein',
    'needs_key' => 'Key daaliye',
    'not_connected' => 'Connect karein',
    'no_device' => 'Device jodiye',
    'pc_not_paired' => 'PC jodiye',
    'pc_offline' => 'PC band hai',
    'no_shop_yet' => 'Dukaan jud rahi hai',
    'demo' => 'Demo bill',
    'not_configured' => 'Jald aa raha',
    'unavailable' => 'Abhi band',
    _ => switch (ex) {
        'handoff' => 'App kholega',
        'reader' => 'SMS padhega',
        'upi' => 'UPI app kholega',
        _ => 'Hoola karega',
      },
  };
}

/// Filter group of a plugin (for the chips on top of the Connect tab).
String levelGroup(Map<String, dynamic> p) {
  final ex = p['executor'] as String? ?? '';
  final st = p['status'] as String? ?? '';
  if (ex == 'handoff') return 'open';
  if (ex == 'reader') return 'sms';
  if (st == 'ready' || st == 'core') return 'does';
  return 'other';
}

Color levelColor(String text) => switch (text) {
      'Hoola karega' => C.ok,
      'App kholega' || 'UPI app kholega' => C.teal,
      'SMS padhega' => C.violet,
      'Demo bill' || 'Link karein' || 'Key daaliye' || 'Connect karein' || 'Device jodiye' || 'PC jodiye' => C.warn,
      _ => C.faint,
    };

IconData categoryIcon(String category, [String executor = '']) {
  final c = category.toLowerCase();
  if (executor == 'shop' || c.contains('shop')) return Icons.storefront_rounded;
  if (c.contains('bill') || c.contains('utilit')) return Icons.receipt_long_rounded;
  if (c.contains('bank')) return Icons.account_balance_rounded;
  if (c.contains('payment') || c.contains('fintech')) return Icons.account_balance_wallet_rounded;
  if (c.contains('invest') || c.contains('wealth') || c.contains('finance')) return Icons.trending_up_rounded;
  if (c.contains('government')) return Icons.account_balance_outlined;
  if (c.contains('health')) return Icons.local_hospital_rounded;
  if (c.contains('food') || c.contains('dining')) return Icons.restaurant_rounded;
  if (c.contains('grocery')) return Icons.local_grocery_store_rounded;
  if (c.contains('travel') || c.contains('commute')) return Icons.flight_takeoff_rounded;
  if (c.contains('agri')) return Icons.agriculture_rounded;
  if (c.contains('home')) return Icons.home_rounded;
  if (c.contains('educat')) return Icons.school_rounded;
  if (c.contains('business') || c.contains('crm') || c.contains('sales')) return Icons.business_center_rounded;
  if (c.contains('office') || c.contains('pc')) return Icons.computer_rounded;
  if (c.contains('safety')) return Icons.health_and_safety_rounded;
  if (c.contains('native') || c.contains('skill')) return Icons.auto_awesome_rounded;
  if (c.contains('mcp') || c.contains('developer')) return Icons.hub_rounded;
  if (c.contains('market') || c.contains('social') || c.contains('communic')) return Icons.campaign_rounded;
  if (c.contains('data') || c.contains('knowledge')) return Icons.storage_rounded;
  return Icons.extension_rounded;
}

/// The brand's real logo on a white tile; a clean category icon or initials when there is no brand logo.
class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, required this.name, this.path, this.category = '', this.executor = '', this.size = 44});
  final String name;
  final String? path;
  final String category;
  final String executor;
  final double size;

  /// Hoola server base address (set once by the Connect screens).
  static String base = '';

  Widget _fallback() {
    final generic = executor == 'shop' || executor == 'native' || path == null;
    final words = name.replaceAll(RegExp(r'[^A-Za-z0-9 ]'), ' ').split(' ').where((w) => w.isNotEmpty).toList();
    final first = words.isEmpty ? '' : words[0];
    final initials = words.isEmpty ? '?' : (words.length == 1 ? (first.length >= 2 ? first.substring(0, 2) : first) : '${words[0][0]}${words[1][0]}');
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * .28),
        gradient: const LinearGradient(colors: [Color(0xFF2B2160), Color(0xFF3A2470)], begin: Alignment.topLeft, end: Alignment.bottomRight),
        border: Border.all(color: const Color(0x26FFFFFF)),
      ),
      alignment: Alignment.center,
      child: generic && category.isNotEmpty
          ? Icon(categoryIcon(category, executor), color: C.accentSoft, size: size * .5)
          : Text(initials.toUpperCase(), style: display(size * .34, color: C.accentSoft)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = path;
    if (p == null || base.isEmpty) return _fallback();
    final b = base.endsWith('/') ? base.substring(0, base.length - 1) : base;
    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * .14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(size * .28),
        boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 10, offset: Offset(0, 4))],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * .16),
        child: Image.network(
          '$b$p',
          fit: BoxFit.contain,
          filterQuality: FilterQuality.medium,
          gaplessPlayback: true,
          errorBuilder: (_, __, ___) => Center(
              child: Text(name.isEmpty ? '?' : name[0].toUpperCase(), style: display(size * .38, color: const Color(0xFF3A2470)))),
        ),
      ),
    );
  }
}

enum ActionKind { add, linked, attention, soon, builtin }

/// The one action button of a card: same size and place on every card.
class PluginAction extends StatelessWidget {
  const PluginAction({super.key, required this.kind, required this.label, this.onTap, this.height = 38});
  final ActionKind kind;
  final String label;
  final VoidCallback? onTap;
  final double height;

  @override
  Widget build(BuildContext context) {
    final (IconData icon, Color fg, Color bg, Color border) = switch (kind) {
      ActionKind.add => (Icons.add_rounded, C.onAccent, C.accent, C.accent),
      ActionKind.linked => (Icons.check_circle_rounded, C.ok, const Color(0x1F34D399), const Color(0x4434D399)),
      ActionKind.attention => (Icons.link_rounded, C.accentSoft, const Color(0x14FFB15C), const Color(0x66FFB15C)),
      ActionKind.soon => (Icons.schedule_rounded, C.faint, Colors.transparent, const Color(0x1FFFFFFF)),
      ActionKind.builtin => (Icons.auto_awesome_rounded, C.violet, const Color(0x1F7C5CFF), const Color(0x447C5CFF)),
    };
    return Press(
      onTap: onTap,
      child: Container(
        height: height,
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12), border: Border.all(color: border)),
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 17, color: fg),
          const SizedBox(width: 6),
          Flexible(
            child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(color: fg, fontWeight: FontWeight.w800, fontSize: 13)),
          ),
        ]),
      ),
    );
  }
}

/// Grid card: logo + badge on top, name, two lines about it, action at the bottom. Every card the same height.
class PluginCard extends StatelessWidget {
  const PluginCard({
    super.key,
    required this.name,
    required this.does,
    required this.action,
    this.logo,
    this.category = '',
    this.executor = '',
    this.badge,
    this.badgeColor = C.accentSoft,
    this.onTap,
  });
  final String name;
  final String does;
  final String? logo;
  final String category;
  final String executor;
  final String? badge;
  final Color badgeColor;
  final Widget action;
  final VoidCallback? onTap;

  static const double height = 190;

  @override
  Widget build(BuildContext context) => Press(
        onTap: onTap,
        haptic: false,
        child: Glass(
          radius: 20,
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              BrandLogo(name: name, path: logo, category: category, executor: executor, size: 44),
              const Spacer(),
              if (badge != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: badgeColor.withOpacity(.14), borderRadius: BorderRadius.circular(999)),
                  child: Text(badge!, style: TextStyle(color: badgeColor, fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: .3)),
                ),
            ]),
            const SizedBox(height: 10),
            Text(name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
            const SizedBox(height: 3),
            SizedBox(
              height: 32,
              child: Text(does, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: C.faint, fontSize: 11.5, height: 1.3)),
            ),
            const Spacer(),
            action,
          ]),
        ),
      );
}

/// Two-column grid where every card has the same height.
class PluginGrid extends StatelessWidget {
  const PluginGrid({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => GridView(
        shrinkWrap: true,
        padding: EdgeInsets.zero,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2, mainAxisSpacing: 12, crossAxisSpacing: 12, mainAxisExtent: PluginCard.height),
        children: children,
      );
}

/// List row for the full plugin list: logo, name, what it does, and its honest level.
class PluginRow extends StatelessWidget {
  const PluginRow({super.key, required this.p, required this.onTap});
  final Map<String, dynamic> p;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final lv = levelText(p);
    final col = levelColor(lv);
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(children: [
          BrandLogo(name: p['name'] as String? ?? '', path: p['logo'] as String?, category: p['category'] as String? ?? '',
              executor: p['executor'] as String? ?? '', size: 38),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(p['name'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
              Text(p['kind'] as String? ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: col.withOpacity(.13), borderRadius: BorderRadius.circular(999)),
            child: Text(lv, style: TextStyle(color: col, fontSize: 10.5, fontWeight: FontWeight.w800)),
          ),
          const Icon(Icons.chevron_right_rounded, color: C.faint, size: 20),
        ]),
      ),
    );
  }
}

/// Example sentences for a plugin, so the owner knows what to say.
List<String> examplesFor(Map<String, dynamic> p) {
  final n = p['name'] as String? ?? '';
  return switch (p['executor'] as String? ?? '') {
    'bbps' => ['$n ka bill kitna hai?', '$n ka bill bhar do'],
    'shop' => ['Paas ki ${n.toLowerCase()} se saamaan mangwao'],
    'upi' => ['$n se Priya ko 500 bhejo'],
    'ride' => ['$n se station ke liye cab book karo'],
    'mcp' => ['$n se order karo', '$n pe kya offer hai?'],
    'handoff' => ['$n kholo', '$n ka kaam karna hai, details tayaar karo'],
    'reader' => ['$n ke SMS se is mahine ka kharch batao'],
    'device' => ['$n se TV / AC chalao'],
    _ => ['$n se madad chahiye'],
  };
}

/// Bottom sheet with everything about one plugin: big logo, what it does, honest level, what to say, the action.
Future<void> showPluginSheet(BuildContext context, Map<String, dynamic> p, {Widget? action, void Function(String)? onSay}) {
  final lv = levelText(p);
  return showModalBottomSheet(
    context: context,
    backgroundColor: C.bgBottom,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            BrandLogo(name: p['name'] as String? ?? '', path: p['logo'] as String?, category: p['category'] as String? ?? '',
                executor: p['executor'] as String? ?? '', size: 60),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(p['name'] as String? ?? '', style: display(19)),
                const SizedBox(height: 4),
                Text('${p['category'] ?? ''}', style: const TextStyle(color: C.faint, fontSize: 12.5)),
                const SizedBox(height: 6),
                Pill(lv, fg: levelColor(lv), bg: levelColor(lv).withOpacity(.14)),
              ]),
            ),
          ]),
          if ((p['does'] as String? ?? '').isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(p['does'] as String, style: const TextStyle(color: C.chip, fontSize: 13.5, height: 1.4)),
          ],
          const SizedBox(height: 14),
          const Text('Hoola se aise kahiye', style: TextStyle(color: C.muted, fontSize: 12, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          for (final e in examplesFor(p))
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Press(
                onTap: onSay == null
                    ? null
                    : () {
                        Navigator.of(ctx).pop();
                        onSay(e);
                      },
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    Expanded(child: Text('"$e"', style: const TextStyle(fontSize: 13))),
                    if (onSay != null) const Icon(Icons.send_rounded, size: 16, color: C.accentSoft),
                  ]),
                ),
              ),
            ),
          if (action != null) ...[const SizedBox(height: 10), action],
        ]),
      ),
    ),
  );
}
