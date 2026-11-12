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
// the old chips. Waves: R8 wave 1 = the 30 desks that all used the same chip layout; wave 2 = the Aurora + list family
// and the inner pages; wave 3 = DeskTabsScaffold + DeskTabBar for the swipe-tab desks (DefaultTabController).
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
      'Galla': 'Cash box',
      'Kharcha': 'Spending',
      'Dhoondhiye': 'Find',
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
    this.onRefresh,
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
  final Future<void> Function()? onRefresh;   // null = an inner page with nothing to reload
  final Widget Function() body;
  final List<Widget> actions;
  final Widget? fab;   // the desk's own main button (e.g. New doc), if it has one

  @override
  State<DeskScaffold> createState() => _DeskScaffoldState();
}

class _DeskScaffoldState extends State<DeskScaffold> {
  @override
  Widget build(BuildContext context) {
    final flat = NightGlass.on;
    const c = NightGlass.c;
    final ink = flat ? c.ink : C.ink;
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
          if (widget.onRefresh != null)
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
              ? DeskLoading(onRetry: widget.onRefresh)
              : widget.onRefresh == null
                  ? widget.body()
                  : RefreshIndicator(color: flat ? c.accent : C.accent, onRefresh: widget.onRefresh!, child: widget.body()),
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
        padding: const EdgeInsets.symmetric(horizontal: 12),
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
                        // R9: the whole 48 dp row takes the tap; the pill drawn inside stays 36
                        child: Center(child: AnimatedContainer(
                          height: 36,
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
                        )),
                      ),
                    )
                  : ChoiceChip(label: Text(deskWord(tabs[i])), selected: tab == i, onSelected: (_) => onTab(i)),
            ),
        ],
      ),
    );
  }
}

/// The first load: a spinner, and after 12 s "Still loading" + Try again (a desk whose first load failed used to spin
/// for ever). [error] shows the desk's own error line instead of the spinner.
class DeskLoading extends StatefulWidget {
  const DeskLoading({super.key, this.onRetry, this.error});
  final Future<void> Function()? onRetry;
  final String? error;
  @override
  State<DeskLoading> createState() => _DeskLoadingState();
}

class _DeskLoadingState extends State<DeskLoading> {
  static const _slow = Duration(seconds: 12);
  Timer? _t;
  bool _isSlow = false;

  @override
  void initState() {
    super.initState();
    _watch();
  }

  void _watch() {
    _t?.cancel();
    _isSlow = false;
    _t = Timer(_slow, () => mounted ? setState(() => _isSlow = true) : null);
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _retry() async {
    setState(_watch);
    await widget.onRetry?.call();
  }

  @override
  Widget build(BuildContext context) {
    final flat = NightGlass.on;
    const c = NightGlass.c;
    final ink = flat ? c.ink : C.ink;
    final soft = flat ? c.ink2 : C.muted;
    final err = widget.error;
    final stuck = _isSlow || (err != null && err.isNotEmpty);
    if (!stuck) {
      return Center(child: SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: flat ? c.ink3 : C.accent)));
    }
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.cloud_off_rounded, color: soft, size: 28),
          const SizedBox(height: 12),
          Text(err != null && err.isNotEmpty ? 'Could not load' : 'Still loading',
              style: TextStyle(color: ink, fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(err != null && err.isNotEmpty ? err : 'This desk is taking longer than usual. Check the internet and try again.',
              textAlign: TextAlign.center, style: TextStyle(color: soft, fontSize: 13)),
          const SizedBox(height: 16),
          if (widget.onRetry != null)
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
      ),
    );
  }
}

/// The swipe-tab desks' tab row (R8 wave 3): pill tabs in the new design, the old underline tabs in Night Glass.
/// Works with the DefaultTabController above it, or with [controller].
class DeskTabBar extends StatelessWidget implements PreferredSizeWidget {
  const DeskTabBar({super.key, required this.tabs, this.controller});
  final List<String> tabs;
  final TabController? controller;

  @override
  Size get preferredSize => const Size.fromHeight(52);

  @override
  Widget build(BuildContext context) {
    final labels = [for (final t in tabs) Tab(text: deskWord(t))];
    if (!NightGlass.on) {
      return TabBar(controller: controller, isScrollable: true, tabAlignment: TabAlignment.start, tabs: labels);
    }
    const c = NightGlass.c;
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 0, 4, 4),
      child: TabBar(
        controller: controller,
        isScrollable: true,
        tabAlignment: TabAlignment.start,
        dividerHeight: 0,
        indicatorSize: TabBarIndicatorSize.tab,
        indicator: BoxDecoration(color: c.pill, borderRadius: BorderRadius.circular(HoolaRadius.pill)),
        indicatorPadding: const EdgeInsets.symmetric(vertical: 6),   // R9: a 36 pill inside a 48 dp tap target
        labelColor: c.onPill,
        unselectedLabelColor: c.ink2,
        labelPadding: const EdgeInsets.symmetric(horizontal: 14),
        labelStyle: TextStyle(fontFamily: HoolaFont.sans, fontSize: 13, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(fontFamily: HoolaFont.sans, fontSize: 13, fontWeight: FontWeight.w500),
        splashBorderRadius: BorderRadius.circular(HoolaRadius.pill),
        overlayColor: WidgetStatePropertyAll(c.ink.withOpacity(0.06)),
        onTap: (_) => HapticFeedback.selectionClick(),
        tabs: [for (final l in labels) SizedBox(height: HoolaSpace.touch, child: l)],
      ),
    );
  }
}

/// The frame of a swipe-tab desk (R8 wave 3): header (title, the desk's actions, Refresh), [DeskTabBar], the first-load
/// state, and the pages you swipe between. [pages] is only built once the desk has loaded. [pullAll] = one pull to
/// refresh over every page (desks whose pages are plain lists); otherwise each page keeps its own.
class DeskTabsScaffold extends StatelessWidget {
  const DeskTabsScaffold({
    super.key,
    required this.title,
    required this.tabs,
    required this.pages,
    this.initialIndex = 0,
    this.loading = false,
    this.error,
    this.onRefresh,
    this.pullAll = false,
    this.actions = const [],
    this.fab,
  });
  final String title;
  final List<String> tabs;
  final List<Widget> Function() pages;
  final int initialIndex;
  final bool loading;
  final String? error;
  final Future<void> Function()? onRefresh;
  final bool pullAll;
  final List<Widget> actions;
  final Widget? fab;

  @override
  Widget build(BuildContext context) {
    final flat = NightGlass.on;
    const c = NightGlass.c;
    final ink = flat ? c.ink : C.ink;
    final stuck = error != null && error!.isNotEmpty;
    Widget body;
    if (loading || stuck) {
      body = DeskLoading(onRetry: onRefresh, error: error);
    } else {
      body = TabBarView(children: pages());
      if (pullAll && onRefresh != null) body = RefreshIndicator(color: flat ? c.accent : C.accent, onRefresh: onRefresh!, child: body);
    }
    return DefaultTabController(
      length: tabs.length,
      initialIndex: initialIndex.clamp(0, tabs.length - 1),
      child: Scaffold(
        floatingActionButton: fab,
        backgroundColor: flat ? c.bg : C.bgTop,
        appBar: AppBar(
          backgroundColor: flat ? c.bg : Colors.transparent,
          surfaceTintColor: flat ? c.bg : Colors.transparent,
          elevation: 0,
          foregroundColor: ink,
          title: Text(title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: flat ? TextStyle(fontFamily: HoolaFont.sans, fontSize: 18, fontWeight: FontWeight.w600, color: ink) : null),
          actions: [
            ...actions,
            if (onRefresh != null) IconButton(tooltip: 'Refresh', onPressed: onRefresh, icon: const Icon(Icons.refresh_rounded)),
          ],
          bottom: DeskTabBar(tabs: tabs),
        ),
        body: Aurora(child: body),
      ),
    );
  }
}

/// The frame of a one-page desk or screen (R8 wave 4): header (title, the screen's actions, Refresh when it can
/// reload), the first-load / error state ([DeskLoading]) and the page. The page keeps its own pull to refresh.
class DeskPage extends StatelessWidget {
  const DeskPage({
    super.key,
    required this.title,
    required this.body,
    this.loading = false,
    this.error,
    this.onRefresh,
    this.actions = const [],
    this.fab,
  });
  final String title;
  final Widget Function() body;
  final bool loading;
  final String? error;
  final Future<void> Function()? onRefresh;
  final List<Widget> actions;
  final Widget? fab;

  @override
  Widget build(BuildContext context) {
    final flat = NightGlass.on;
    const c = NightGlass.c;
    final ink = flat ? c.ink : C.ink;
    final stuck = error != null && error!.isNotEmpty;
    return Scaffold(
      floatingActionButton: fab,
      backgroundColor: flat ? c.bg : C.bgTop,
      appBar: AppBar(
        backgroundColor: flat ? c.bg : Colors.transparent,
        surfaceTintColor: flat ? c.bg : Colors.transparent,
        elevation: 0,
        foregroundColor: ink,
        title: Text(title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: flat ? TextStyle(fontFamily: HoolaFont.sans, fontSize: 18, fontWeight: FontWeight.w600, color: ink) : null),
        actions: [
          ...actions,
          if (onRefresh != null) IconButton(tooltip: 'Refresh', onPressed: onRefresh, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: Aurora(child: loading || stuck ? DeskLoading(onRetry: onRefresh, error: error) : body()),
    );
  }
}
