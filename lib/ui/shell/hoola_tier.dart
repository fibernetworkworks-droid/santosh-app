// v0.999.10 TIER PICKER ON THE PHONE (owner: "ADD TIER PICKER IN PHONE APP ALSO"): the console's "Quality tier"
// (v0.999.9 MODEL TIERS) on the phone. GET /api/model/tier lists ULTRA / HIGH / MEDIUM / LOW with what one reply,
// one AI-employee job, one call minute and one 30-second reel cost, and the models each tier uses; PUT saves her
// pick. ULTRA asks first (the server refuses it without confirm_ultra). '' = Hoola's normal setup. Her own model
// in the console's model list still wins over the tier - said on the page.
import 'package:flutter/material.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_tabs.dart';

String _s(Object? v) => v == null ? '' : '$v';

/// A model id as a name she can read: "google/gemini-3.8-flash" -> "Gemini 3.8 Flash".
String tierModelName(String id) {
  var n = id.contains('/') ? id.split('/').last : id;
  n = n.replaceAll(RegExp(r'-\d{4}$'), '');                 // a date stamp on the end
  const caps = {'glm': 'GLM', 'gpt': 'GPT', 'hy4': 'HY4', 'v4.1': 'V4.1', 'deepseek': 'DeepSeek', 'mimo': 'MiMo'};
  return n
      .split('-')
      .where((w) => w.isNotEmpty)
      .map((w) => caps[w.toLowerCase()] ?? (w[0].toUpperCase() + w.substring(1)))
      .join(' ');
}

class HoolaTierPage extends StatefulWidget {
  const HoolaTierPage({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaTierPage> createState() => _HoolaTierPageState();
}

class _HoolaTierPageState extends State<HoolaTierPage> {
  Map<String, dynamic>? _v;
  String? _err;
  String _busy = '';
  final Set<String> _open = {};

  static const _jobs = [
    ['chat', 'Chat replies'],
    ['code', 'Apps and code'],
    ['employee', 'AI employee jobs'],
    ['call', 'Voice calls'],
    ['hoola_code', 'Hoola Code'],
    ['web', 'Websites'],
  ];
  static const _costs = [
    ['reply', 'A reply'],
    ['employee_job', 'An AI employee job'],
    ['call_minute', 'A call minute'],
    ['reel_30s', 'A 30 s reel'],
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final v = await widget.app.api!.modelTier();
      if (mounted) setState(() {
        _v = v;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<bool> _askUltra() async {
    final c = HoolaColors.of(context);
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Use ULTRA?', style: HoolaType.heading(c)),
            const SizedBox(height: 8),
            Text(_s(_v?['ultra_warning']), style: HoolaType.body(c).copyWith(color: c.ink2)),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: FilledButton.styleFrom(
                  backgroundColor: c.pill,
                  foregroundColor: c.onPill,
                  shape: const StadiumBorder(),
                  minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: const Text('Yes, use ULTRA'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
              child: const Text('Not now'),
            ),
          ]),
        ),
      ),
    );
    return ok == true;
  }

  Future<void> _pick(String tier) async {
    if (_busy.isNotEmpty || _s(_v?['selected']) == tier) return;
    var yes = false;
    if (tier == 'ultra') {
      yes = await _askUltra();
      if (!yes) return;
    }
    setState(() => _busy = tier.isEmpty ? 'normal' : tier);
    try {
      final v = await widget.app.api!.modelTierSet(tier, confirmUltra: yes);
      if (mounted) setState(() => _v = v);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = '');
    }
  }

  Widget _mark(HoolaColors c, bool on, bool busy) {
    if (busy) return SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: c.accent));
    return Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
        color: on ? c.accent : c.ink3, size: 22);
  }

  Widget _normal(HoolaColors c) {
    final on = _s(_v?['selected']).isEmpty;
    return HoolaGroup(children: [
      HoolaRow(
        title: 'Hoola\'s normal setup',
        sub: 'Hoola picks a model for each job by itself',
        icon: Icons.auto_awesome_outlined,
        trailing: _mark(c, on, _busy == 'normal'),
        onTap: () => _pick(''),
        semantics: on ? 'Hoola\'s normal setup, selected' : 'Hoola\'s normal setup',
      ),
    ]);
  }

  Widget _tier(HoolaColors c, Map<String, dynamic> t) {
    final id = _s(t['id']);
    final on = t['selected'] == true;
    final open = _open.contains(id);
    final cost = Map<String, dynamic>.from((t['cost'] as Map?) ?? const {});
    final models = Map<String, dynamic>.from((t['models'] as Map?) ?? const {});
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, HoolaSpace.s12),
      child: Material(
        color: c.surface,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(HoolaRadius.card),
            side: BorderSide(color: on ? c.accent : c.line, width: on ? 1.5 : 1)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => _pick(id),
          child: Semantics(
            button: true,
            selected: on,
            label: '${_s(t['label'])} tier${on ? ', selected' : ''}',
            child: Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.s16, HoolaSpace.s16, HoolaSpace.s12, HoolaSpace.s8),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Text(_s(t['label']), style: HoolaType.title(c)),
                        if (id == 'ultra') ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(color: c.warnSoft, borderRadius: BorderRadius.circular(HoolaRadius.pill)),
                            child: Text('Burns credit fast', style: HoolaType.label(c).copyWith(color: c.warn)),
                          ),
                        ],
                      ]),
                      const SizedBox(height: 2),
                      Text(_s(t['line']), style: HoolaType.small(c)),
                    ]),
                  ),
                  const SizedBox(width: 8),
                  _mark(c, on, _busy == id),
                ]),
                const SizedBox(height: HoolaSpace.s12),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final k in _costs)
                    if (_s(cost[k[0]]).isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(color: c.sunk, borderRadius: BorderRadius.circular(HoolaRadius.chip)),
                        child: Text('${k[1]} · ${_s(cost[k[0]])}', style: HoolaType.label(c)),
                      ),
                ]),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => setState(() => open ? _open.remove(id) : _open.add(id)),
                    style: TextButton.styleFrom(foregroundColor: c.ink2, padding: EdgeInsets.zero,
                        minimumSize: const Size(0, HoolaSpace.touch)),
                    icon: Icon(open ? Icons.expand_less_rounded : Icons.expand_more_rounded, size: 20),
                    label: Text(open ? 'Hide the models' : 'Which models it uses', style: HoolaType.label(c)),
                  ),
                ),
                if (open)
                  Padding(
                    padding: const EdgeInsets.only(bottom: HoolaSpace.s8),
                    child: Column(children: [
                      for (final j in _jobs)
                        if (models[j[0]] is List && (models[j[0]] as List).isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              SizedBox(width: 128, child: Text(j[1], style: HoolaType.small(c))),
                              Expanded(
                                child: Text(
                                  [
                                    for (final m in (models[j[0]] as List))
                                      tierModelName(_s((m as Map)['id'])),
                                  ].join(' · backup '),
                                  style: HoolaType.small(c).copyWith(color: c.ink),
                                ),
                              ),
                            ]),
                          ),
                    ]),
                  ),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final v = _v;
    final tiers = [for (final t in (v?['tiers'] as List?) ?? const []) Map<String, dynamic>.from(t as Map)];
    final children = <Widget>[
      const HoolaTabHeader(title: 'Quality tier', sub: 'Which models do the work, and what it costs'),
      if (_err != null)
        Padding(
          padding: const EdgeInsets.all(HoolaSpace.gutter),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Could not load the tiers.', style: HoolaType.body(c)),
            Text(_err!, style: HoolaType.small(c)),
            TextButton(onPressed: _load, child: const Text('Try again')),
          ]),
        )
      else if (v == null)
        Padding(padding: const EdgeInsets.all(HoolaSpace.s32), child: Center(child: CircularProgressIndicator(color: c.accent)))
      else if (v['available'] != true)
        Padding(
          padding: const EdgeInsets.all(HoolaSpace.gutter),
          child: Text(_s(v['reason']).isEmpty ? 'Tiers are not available on this server.' : _s(v['reason']),
              style: HoolaType.body(c).copyWith(color: c.ink2)),
        )
      else ...[
        const HoolaSection('Default'),
        _normal(c),
        const HoolaSection('Tiers'),
        for (final t in tiers) _tier(c, t),
        Padding(
          padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, HoolaSpace.s4, HoolaSpace.gutter, 0),
          child: Text(
            '${_s(v['note'])} Costs are about what one thing takes; your real bill depends on how long it runs. '
            'A new video starts from the tier\'s quality, and the price card still asks before anything is paid.',
            style: HoolaType.small(c),
          ),
        ),
      ],
    ];
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(backgroundColor: c.bg, surfaceTintColor: c.bg, foregroundColor: c.ink, elevation: 0, toolbarHeight: 48),
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.only(bottom: HoolaSpace.s32),
            children: children,
          ),
        ),
      ),
    );
  }
}
