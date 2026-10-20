/// "Roz ke kaam": the plugins people use every day, first on the Connect tab. A home-screen style grid of big HD
/// brand logos per section (Paisa bhejo, Khana aur kirana, Safar, Bills, Shopping, Sehat aur sarkari, Bank), with a
/// small status mark on each icon: juda / taiyaar (green), jodiye (saffron), jald (grey).
library;

import 'package:flutter/material.dart';

import 'glass.dart';
import 'plugin_widgets.dart';

const _sectionIcon = {
  'pay': Icons.currency_rupee_rounded,
  'food': Icons.restaurant_rounded,
  'ride': Icons.local_taxi_rounded,
  'bills': Icons.bolt_rounded,
  'shop': Icons.shopping_bag_rounded,
  'health': Icons.health_and_safety_rounded,
  'money': Icons.account_balance_rounded,
};

class TopPlugins extends StatefulWidget {
  const TopPlugins({super.key, required this.sections, required this.onOpen});
  final List<Map<String, dynamic>> sections;
  final void Function(Map<String, dynamic> pack) onOpen;
  @override
  State<TopPlugins> createState() => _TopPluginsState();
}

class _TopPluginsState extends State<TopPlugins> {
  String _sel = '';

  @override
  Widget build(BuildContext context) {
    final secs = widget.sections;
    if (secs.isEmpty) return const SizedBox.shrink();
    final cur = secs.firstWhere((s) => s['id'] == _sel, orElse: () => secs.first);
    final items = List<Map<String, dynamic>>.from(((cur['items'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final ready = items.where((p) => _state(p) == _Mark.ready).length;
    return Glass(
      radius: 24,
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(gradient: C.gradient, borderRadius: BorderRadius.circular(11)),
            child: const Icon(Icons.bolt_rounded, color: C.onAccent, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Roz ke kaam', style: display(18)),
              const Text('Sabse zyada use hone wale · ek tap mein', style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ]),
        const SizedBox(height: 12),
        SizedBox(
          height: 34,
          child: ListView(scrollDirection: Axis.horizontal, children: [
            for (final s in secs) _chip(s, s['id'] == cur['id']),
          ]),
        ),
        const SizedBox(height: 14),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          switchInCurve: Curves.easeOutCubic,
          transitionBuilder: (c, a) => FadeTransition(
              opacity: a, child: SlideTransition(position: Tween(begin: const Offset(0, .03), end: Offset.zero).animate(a), child: c)),
          child: GridView.count(
            key: ValueKey(cur['id']),
            crossAxisCount: 4,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            padding: EdgeInsets.zero,
            mainAxisSpacing: 10,
            crossAxisSpacing: 6,
            childAspectRatio: .72,
            children: [for (final p in items) _AppTile(p: p, mark: _state(p), onTap: () => widget.onOpen(p))],
          ),
        ),
        if (items.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Text(
                ready == items.length ? 'Sab taiyaar · Hoola se bas kahiye' : '$ready / ${items.length} taiyaar · baaki ek tap mein jodiye',
                style: const TextStyle(color: C.faint, fontSize: 11.5)),
          ),
      ]),
    );
  }

  Widget _chip(Map<String, dynamic> s, bool on) => Padding(
        padding: const EdgeInsets.only(right: 8),
        child: Press(
          onTap: () => setState(() => _sel = s['id'] as String),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: on ? C.accent : const Color(0x14FFFFFF),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(color: on ? C.accent : const Color(0x24FFFFFF)),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(_sectionIcon[s['id']] ?? Icons.apps_rounded, size: 15, color: on ? C.onAccent : C.accentSoft),
              const SizedBox(width: 6),
              Text('${s['title']}', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: on ? C.onAccent : C.ink)),
            ]),
          ),
        ),
      );
}

enum _Mark { ready, add, soon, none }

_Mark _state(Map<String, dynamic> p) {
  final st = p['status'] as String? ?? '';
  if (st == 'ready' || st == 'core') return _Mark.ready;
  if (st == 'needs_link' || st == 'no_shop_yet' || st == 'not_connected' || st == 'needs_key') return _Mark.add;
  if (st == 'not_configured' || st == 'unavailable') return _Mark.soon;
  return _Mark.none;   // demo bills etc.
}

class _AppTile extends StatelessWidget {
  const _AppTile({required this.p, required this.mark, required this.onTap});
  final Map<String, dynamic> p;
  final _Mark mark;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final name = _short(p['name'] as String? ?? '');
    final (IconData? icon, Color col) = switch (mark) {
      _Mark.ready => (Icons.check_rounded, C.ok),
      _Mark.add => (Icons.add_rounded, C.accent),
      _Mark.soon => (Icons.schedule_rounded, C.faint),
      _Mark.none => (null, C.faint),
    };
    return Semantics(
      button: true,
      label: '${p['name']}, ${levelText(p)}',
      child: Press(
        onTap: onTap,
        child: Column(children: [
          Stack(clipBehavior: Clip.none, children: [
            Opacity(
              opacity: mark == _Mark.soon ? .55 : 1,
              child: BrandLogo(
                  name: p['name'] as String? ?? '',
                  path: p['logo'] as String?,
                  category: p['category'] as String? ?? '',
                  executor: p['executor'] as String? ?? '',
                  size: 60),
            ),
            if (icon != null)
              Positioned(
                right: -4,
                bottom: -4,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(color: col, shape: BoxShape.circle, border: Border.all(color: C.bgBottom, width: 2)),
                  child: Icon(icon, size: 12, color: mark == _Mark.soon ? C.bgBottom : C.onAccent),
                ),
              ),
          ]),
          const SizedBox(height: 7),
          Text(name, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, height: 1.15)),
        ]),
      ),
    );
  }

  /// "Vi (Vodafone Idea)" -> "Vi", "MSEDCL (Mahavitaran)" -> "MSEDCL", "Uber India" -> "Uber".
  static String _short(String n) {
    var s = n.replaceAll(RegExp(r'\s*\(.*?\)'), '').trim();
    s = s.replaceAll(RegExp(r'\s+(India|booking|Rail Connect|Digital)$', caseSensitive: false), '');
    return s.isEmpty ? n : s;
  }
}
