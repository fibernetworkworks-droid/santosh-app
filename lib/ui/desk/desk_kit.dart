// v0.868 R8 DESKS (docs/HOOLA_APP_REDESIGN_PLAN.md R8): one frame every desk stands in, instead of each desk drawing
// its own header, tab chips, busy line and loading spinner.
//
//   DeskScaffold(title, tabs, tab, onTab, loading, busy, onRefresh, actions, body)
//     - header: title + Refresh (+ the desk's own actions)
//     - tabs: pill tabs in the new design (the chip row before), English labels
//     - busy: a thin line under the tabs while the desk is saving
//     - loading: a spinner, and after 12 s "Still loading" + Try again (a desk whose first load failed used to spin
//       for ever - most desks only showed the error as a passing snack)
//     - body: pull to refresh
//
// While the new design is on it draws in the new design's dark roles (NightGlass.c), so it sits right with the
// flat cards inside every desk (glass.dart). With the new design off it keeps the Night Glass look: the same layout,
// the old chips. Waves: R8 wave 1 = the 30 desks that all used the same chip layout.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../glass.dart';
import '../hoola_theme.dart';

/// The English word for a tab label the desks used to show in Hinglish (R8 English pass).
String deskWord(String w) => const {
      'Aaj': 'Today',
      'Niyam': 'Rules',
      'Jaanch': 'Check',
      'Kirayedar': 'Tenants',
      'Hisaab': 'Accounts',
      'Kaam': 'Work',
      'Mehmaan': 'Guests',
      'Khaata': 'Ledger',
      'Khata': 'Ledger',
      'Saman': 'Stock',
      'Baaki': 'Due',
      'Taareekh': 'Dates',
    }[w] ??
    w;

class DeskScaffold extends StatefulWidget {
  const DeskScaffold({
    super.key,
    required this.title,
    required this.tabs,
    required this.tab,
    required this.onTab,
    required this.loading,
    required this.onRefresh,
    required this.body,
    this.busy = false,
    this.actions = const [],
    this.fab,
  });
  final String title;
  final List<String> tabs;
  final int tab;
  final ValueChanged<int> onTab;
  final bool loading, busy;
  final Future<void> Function() onRefresh;
  final Widget Function() body;
  final List<Widget> actions;
  final Widget? fab;   // the desk's own main button (e.g. New doc), if it has one

  @override
  State<DeskScaffold> createState() => _DeskScaffoldState();
}

class _DeskScaffoldState extends State<DeskScaffold> {
  static const _slow = Duration(seconds: 12);
  Timer? _slowTimer;
  bool _isSlow = false;

  @override
  void initState() {
    super.initState();
    _watchLoading();
  }

  @override
  void didUpdateWidget(DeskScaffold old) {
    super.didUpdateWidget(old);
    if (old.loading != widget.loading) _watchLoading();
  }

  void _watchLoading() {
    _slowTimer?.cancel();
    _isSlow = false;
    if (widget.loading) _slowTimer = Timer(_slow, () => mounted ? setState(() => _isSlow = true) : null);
  }

  @override
  void dispose() {
    _slowTimer?.cancel();
    super.dispose();
  }

  Future<void> _retry() async {
    setState(() => _isSlow = false);
    _watchLoading();
    await widget.onRefresh();
  }

  @override
  Widget build(BuildContext context) {
    final flat = NightGlass.on;
    const c = NightGlass.c;
    final ink = flat ? c.ink : C.ink;
    final soft = flat ? c.ink2 : C.muted;
    return Scaffold(
      floatingActionButton: widget.fab,
      backgroundColor: flat ? c.bg : C.bgTop,
      appBar: AppBar(
        backgroundColor: flat ? c.bg : Colors.transparent,
        surfaceTintColor: flat ? c.bg : Colors.transparent,
        elevation: 0,
        foregroundColor: ink,
        title: Text(widget.title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: flat ? TextStyle(fontFamily: HoolaFont.sans, fontSize: 18, fontWeight: FontWeight.w600, color: ink) : null),
        actions: [
          ...widget.actions,
          IconButton(tooltip: 'Refresh', onPressed: widget.onRefresh, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: Column(children: [
        if (widget.tabs.length > 1) _DeskTabs(tabs: widget.tabs, tab: widget.tab, onTab: widget.onTab, flat: flat),
        SizedBox(
          height: 2,
          child: widget.busy ? LinearProgressIndicator(minHeight: 2, color: flat ? c.accent : C.accent, backgroundColor: Colors.transparent) : null,
        ),
        Expanded(
          child: widget.loading
              ? Center(
                  child: _isSlow
                      ? Padding(
                          padding: const EdgeInsets.all(32),
                          child: Column(mainAxisSize: MainAxisSize.min, children: [
                            Icon(Icons.cloud_off_rounded, color: soft, size: 28),
                            const SizedBox(height: 12),
                            Text('Still loading', style: TextStyle(color: ink, fontSize: 16, fontWeight: FontWeight.w600)),
                            const SizedBox(height: 4),
                            Text('This desk is taking longer than usual. Check the internet and try again.',
                                textAlign: TextAlign.center, style: TextStyle(color: soft, fontSize: 13)),
                            const SizedBox(height: 16),
                            OutlinedButton(
                              onPressed: _retry,
                              style: OutlinedButton.styleFrom(
                                  foregroundColor: ink,
                                  side: BorderSide(color: flat ? c.lineStrong : C.line),
                                  shape: const StadiumBorder(),
                                  minimumSize: const Size(0, HoolaSpace.touch)),
                              child: const Text('Try again'),
                            ),
                          ]),
                        )
                      : SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: flat ? c.ink3 : C.accent)),
                )
              : RefreshIndicator(color: flat ? c.accent : C.accent, onRefresh: widget.onRefresh, child: widget.body()),
        ),
      ]),
    );
  }
}

/// The desk's tabs: pill tabs in the new design, the old chips in Night Glass.
class _DeskTabs extends StatelessWidget {
  const _DeskTabs({required this.tabs, required this.tab, required this.onTab, required this.flat});
  final List<String> tabs;
  final int tab;
  final ValueChanged<int> onTab;
  final bool flat;

  @override
  Widget build(BuildContext context) {
    const c = NightGlass.c;
    return SizedBox(
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        children: [
          for (var i = 0; i < tabs.length; i++)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: flat
                  ? Semantics(
                      selected: i == tab,
                      button: true,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(HoolaRadius.pill),
                        onTap: () {
                          HapticFeedback.selectionClick();
                          onTab(i);
                        },
                        child: AnimatedContainer(
                          duration: HoolaMotion.of(context, HoolaMotion.menu),
                          padding: const EdgeInsets.symmetric(horizontal: 14),
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: i == tab ? c.pill : c.surface,
                            borderRadius: BorderRadius.circular(HoolaRadius.pill),
                            border: Border.all(color: i == tab ? c.pill : c.line),
                          ),
                          child: Text(deskWord(tabs[i]),
                              style: TextStyle(
                                  fontFamily: HoolaFont.sans,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: i == tab ? c.onPill : c.ink2)),
                        ),
                      ),
                    )
                  : ChoiceChip(label: Text(deskWord(tabs[i])), selected: tab == i, onSelected: (_) => onTab(i)),
            ),
        ],
      ),
    );
  }
}
