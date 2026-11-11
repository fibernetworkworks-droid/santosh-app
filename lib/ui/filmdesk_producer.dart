/// Film desk > one film > Producer: the producer layers over /api/filmdesk/projects/<ref>/...
/// Script (coverage facts) · Shots (previs checks) · Schedule · Paisa (budget from HER rate card, waterfall, royalty terms from HER
/// contract) · Sales (festivals, release windows) · Delivery (deliverables, subtitles / dubs).
///
/// Rules this screen keeps (they are the server's rules, drawn): every number was COUNTED from her script / shot list or TYPED by her -
/// a rate, fee, deadline, holdback or guild term is never filled in for her, and a royalty term insists on the contract clause it came
/// from; 'hint' lines are heuristics, not findings; coverage never gives a reader's verdict; nothing here sends, submits, signs or pays.
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
num? _num(String? v) => (v == null || v.trim().isEmpty) ? null : num.tryParse(v.replaceAll(',', '').trim());

String _inr(dynamic v) {
  final n = v is num ? v : num.tryParse(_s(v));
  if (n == null) return '–';
  return '₹${n.toStringAsFixed(n % 1 == 0 ? 0 : 2)}';
}

void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

const _numericKeys = {
  'rate', 'fee_inr', 'amount_inr', 'net_inr', 'units', 'threshold_inr', 'cap_inr', 'floor_inr', 'qa_rounds', 'day_hours', 'setup_hours',
  'hours_per_screen_minute',
};

Future<Map<String, String>?> _ask(BuildContext context, String title, List<(String, String)> fields, {String ok = 'Save'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields) TextField(controller: c[k], decoration: InputDecoration(labelText: label)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Keep it')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

class FilmdeskProducerPage extends StatefulWidget {
  const FilmdeskProducerPage({super.key, required this.app, required this.ref, this.tab = 0});
  final Santosh app;
  final String ref;
  final int tab;
  @override
  State<FilmdeskProducerPage> createState() => _FilmdeskProducerPageState();
}

class _FilmdeskProducerPageState extends State<FilmdeskProducerPage> {
  static const _tabs = ['Script', 'Shots', 'Schedule', 'Money', 'Sales', 'Delivery'];
  late int _tab = widget.tab;
  bool _busy = false;
  bool _loading = true;
  Map<String, dynamic> _d = {};
  String get _base => '/api/filmdesk/projects/${widget.ref}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<Map<String, dynamic>?> _get(String path) async {
    try {
      return _m(await widget.app.api!.call('GET', '$_base/$path', timeout: const Duration(seconds: 60)));
    } catch (_) {
      return null;
    }
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final d = <String, dynamic>{};
    switch (_tab) {
      case 0:
        d['coverage'] = await _get('coverage');
        break;
      case 1:
        d['previs'] = await _get('previs');
        break;
      case 2:
        d['schedule'] = await _get('schedule?what=schedule');
        d['dood'] = await _get('schedule?what=dood');
        break;
      case 3:
        d['budget'] = await _get('schedule?what=plan_budget');
        d['waterfall'] = await _get('waterfall');
        d['royalties'] = await _get('royalties');
        break;
      case 4:
        d['festivals'] = await _get('festivals');
        d['windows'] = await _get('windows');
        break;
      default:
        d['deliverables'] = await _get('deliverables');
        d['localisation'] = await _get('localisation');
    }
    if (!mounted) return;
    setState(() {
      _d = d;
      _loading = false;
    });
  }

  Future<void> _post(String path, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final r = _m(await widget.app.api!.call('POST', '$_base/$path', body: body, timeout: const Duration(seconds: 120)));
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
    await _load();
  }

  Map<String, dynamic> _body(Map<String, String> f, [Map<String, dynamic> extra = const {}]) {
    final out = <String, dynamic>{...extra};
    f.forEach((k, v) {
      if (_numericKeys.contains(k)) {
        final n = _num(v);
        if (n != null) out[k] = n;
      } else if (k == 'applies_to') {
        out[k] = v.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
      } else {
        out[k] = v;
      }
    });
    return out;
  }

  Future<void> _add(String path, String title, List<(String, String)> fields, Map<String, dynamic> extra) async {
    final f = await _ask(context, title, fields);
    if (f == null) return;
    await _post(path, _body(f, extra));
  }

  // ------------------------------------------------------------ small widgets
  Widget _box(String title, List<Widget> children) => Glass(
        margin: const EdgeInsets.only(bottom: 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 6),
          ...children,
        ]),
      );

  Widget _line(String t, {bool muted = false}) =>
      Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: TextStyle(fontSize: 12.5, color: muted ? C.muted : null)));

  List<Widget> _flags(dynamic fl, [String empty = '']) {
    final out = <Widget>[];
    for (final f in (fl as List?) ?? const []) {
      if (f is Map) {
        final hint = _s(f['kind']) == 'heuristic';
        out.add(_line('${hint ? 'hint · ' : '• '}${_s(f['text'])}', muted: hint));
      } else {
        out.add(_line('• ${_s(f)}'));
      }
    }
    if (out.isEmpty && empty.isNotEmpty) out.add(_line(empty, muted: true));
    return out;
  }

  Widget _remove(String path, String op, String entry) => IconButton(
        icon: const Icon(Icons.delete_outline_rounded, size: 18),
        onPressed: _busy ? null : () => _post(path, {'op': op, 'entry': entry}),
      );

  Widget _row(String text, {Widget? trailing}) => Row(children: [
        Expanded(child: Text(text, style: const TextStyle(fontSize: 12.5))),
        if (trailing != null) trailing,
      ]);

  // ------------------------------------------------------------ tabs
  List<Widget> _script() {
    final c = _m(_d['coverage']);
    if (c.isEmpty) return [_line('Coverage could not be opened.', muted: true)];
    if ((c['scenes'] ?? 0) == 0) return [_line(_s(c['note']), muted: true)];
    return [
      _box('Script count', [
        _line('${_s(c['scenes'])} scenes · ~${_s(c['estimated_minutes'])} min · ${_s(c['characters_n'])} characters · ${_s(c['places_n'])} locations'),
        _line('Night ${_s(c['night_scenes'])} scene (${_s(c['night_pct'])}%) · location changes ${_s(c['company_moves'])} times'),
        _line('Dialogue ${_s(c['dialogue_pct'])}% · most dialogue: ${_s(c['most_dialogue'])}', muted: true),
        _line(_s(c['kind_note']), muted: true),
      ]),
      _box('Flags', _flags(c['flags'], 'Nothing was flagged.')),
      _box('Characters', [
        for (final x in _list(c['cast_table']))
          _line('${_s(x['name'])}: ${_s(x['lines'])} lines · ${_s(x['dialogue_pct'])}% · ${_s(x['scenes_n'])} scenes'),
      ]),
    ];
  }

  List<Widget> _shots() {
    final v = _m(_d['previs']);
    if (v.isEmpty) return [_line('Previs could not be opened.', muted: true)];
    if ((v['shots'] ?? 0) == 0) return [_line(_s(v['note']), muted: true)];
    return [
      _box('Shot list', [
        _line('${_s(v['shots'])} shots · ${_s(v['total_seconds'])} s'),
        _line(_s(v['note']), muted: true),
      ]),
      _box('Flags', _flags(v['flags'], 'No problem was found in the shot list.')),
      _box('By scene', [
        for (final x in _list(v['per_scene']))
          _line('Scene ${_s(x['n'])}: ${_s(x['shots'])} shots, ${_s(x['shot_seconds'])} s (script ${_s(x['script_seconds'])} s)'),
      ]),
    ];
  }

  List<Widget> _schedule() {
    final s = _m(_d['schedule']);
    final d = _m(_d['dood']);
    final plan = GlassButton(
        label: s.isEmpty ? 'Make shoot plan' : 'Plan again',
        icon: Icons.event_note_rounded,
        height: 38,
        onTap: _busy ? null : () => _add('schedule', 'Shoot plan (your real numbers)', const [
              ('start_date', 'Start date (YYYY-MM-DD)'),
              ('day_hours', 'Hours in a day'),
              ('setup_hours', 'Set-up hours'),
              ('hours_per_screen_minute', 'Hours per screen minute'),
            ], const {}));
    if (s.isEmpty) return [_box('Schedule', [_line('No plan yet. Hours are estimates until you give your own numbers.', muted: true), plan])];
    return [
      _box('Shoot days', [
        plan,
        const SizedBox(height: 6),
        ..._flags(s['flags']),
        for (final x in _list(s['days']))
          _line('Day ${_s(x['order'])} · ${_s(x['date']).isEmpty ? '[date]' : _s(x['date'])} · ${_s(x['part'])} · '
              '${((x['places'] as List?) ?? const []).join(', ')} · ${((x['scenes'] as List?) ?? const []).length} scenes · ${_s(x['hours'])} hours'),
        _line('The call sheet is made from the chat ("call sheet day 2"); anything only you know stays [blank].', muted: true),
      ]),
      if (d.isNotEmpty)
        _box('Day-out-of-days', [
          for (final x in _list(d['summary']))
            _line('${_s(x['who'])}: ${_s(x['work_days'])} working days, ${_s(x['hold_days'])} hold (days ${_s(x['first_day'])}-${_s(x['last_day'])})'),
          _line(_s(d['note']), muted: true),
        ]),
    ];
  }

  List<Widget> _paisa() {
    final b = _m(_d['budget']);
    final w = _m(_d['waterfall']);
    final r = _m(_d['royalties']);
    const termsPath = 'royalties';
    return [
      _box('Budget (from your rate card)', b.isEmpty
          ? [_line('Make a schedule first, then give your rates in the chat ("budget plan: crew 8000 per day ..."). Only your numbers are used.', muted: true)]
          : [
              _line('At least ${_inr(b['total_inr'])} (subtotal ${_inr(b['subtotal_inr'])}, contingency ${_inr(b['contingency_inr'])})'),
              for (final l in _list(b['lines']))
                _line('${_s(l['head'])}: ${_s(l['qty'])} × ${l['rate_inr'] == null ? 'no rate given' : _inr(l['rate_inr'])} = ${_inr(l['amount_inr'])}', muted: l['rate_inr'] == null),
              _line(_s(b['note']), muted: true),
            ]),
      _box('Waterfall', w.isEmpty
          ? [_line('Not made yet (chat: "waterfall: gross 5 lakh ...").', muted: true)]
          : [
              _line('Gross ${_inr(w['gross_inr'])} · matches gross: ${w['ties_to_gross'] == true ? 'yes' : 'NO'}'),
              for (final t in _list(w['tiers'])) _line('${_s(t['tier'])} · ${_s(t['name'])}: ${_inr(t['amount_inr'])} (left ${_inr(t['left_inr'])})'),
            ]),
      _box('Royalty (your contract terms)', [
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: 'Add term', icon: Icons.gavel_rounded, height: 38, onTap: _busy ? null : () => _add(termsPath, 'Contract term', const [
                ('party', 'To whom'),
                ('role', 'Role (writer / director / actor / composer ...)'),
                ('basis', 'flat_inr / percent_of_gross / percent_of_net / per_unit'),
                ('rate', 'Dar'),
                ('threshold_inr', 'Above this amount (or blank)'),
                ('cap_inr', 'Maximum rupees (or blank)'),
                ('applies_to', 'Medium (svod, tv ... or all)'),
                ('source', 'Contract clause (required)'),
              ], const {'op': 'add'})),
          GlassButton(label: 'Add income', icon: Icons.payments_rounded, height: 38, onTap: _busy ? null : () => _add(termsPath, 'Income received', const [
                ('medium', 'Medium (svod / avod / tv / theatrical / music ...)'),
                ('amount_inr', 'Rupees'),
                ('net_inr', 'Net rupees (or blank)'),
                ('units', 'Count (or blank)'),
                ('period', 'Date (YYYY-MM-DD)'),
              ], const {'op': 'receipt'})),
        ]),
        const SizedBox(height: 6),
        for (final t in _list(r['terms']))
          _row('${_s(t['id'])} · ${_s(t['party'])} · ${_s(t['basis'])} ${_s(t['rate'])} · ${_s(t['source'])}', trailing: _remove(termsPath, 'remove', _s(t['id']))),
        for (final x in _list(r['receipts']))
          _row('${_s(x['id'])} · ${_s(x['medium'])} ${_inr(x['amount_inr'])}', trailing: _remove(termsPath, 'unreceipt', _s(x['id']))),
        for (final l in _list(r['lines']))
          _line('${_s(l['party'])}: ${_inr(l['amount_inr'])}${_s(l['problem']).isEmpty ? '' : ' (${_s(l['problem'])})'}'),
        if (r.isNotEmpty) _line('Total ${_inr(r['total_inr'])} (income ${_inr(r['gross_receipts_inr'])})'),
        if (r.isNotEmpty) _line(_s(r['note']), muted: true),
      ]),
    ];
  }

  List<Widget> _sales() {
    final f = _m(_d['festivals']);
    final w = _m(_d['windows']);
    final chk = _m(w['check']);
    return [
      _box('Festival', [
        GlassButton(label: 'Add festival', icon: Icons.emoji_events_rounded, height: 38, onTap: _busy ? null : () => _add('festivals', 'Festival', const [
              ('name', 'Name'),
              ('country', 'Country'),
              ('deadline', 'Deadline (YYYY-MM-DD)'),
              ('event_date', 'Festival date'),
              ('fee_inr', 'Fee in rupees'),
              ('requires', 'Premiere rule: regional / national / international / world / none'),
            ], const {'op': 'add'})),
        const SizedBox(height: 6),
        ..._flags(f['flags']),
        for (final x in _list(f['festivals']))
          _row('${_s(x['name'])} · deadline ${_s(x['deadline']).isEmpty ? '–' : _s(x['deadline'])}'
              '${x['days_left'] == null ? '' : ' (${_s(x['days_left'])} days)'} · ${_s(x['status'])} · packet ${_s(_m(x['packet'])['done'])}/${_s(_m(x['packet'])['total'])}',
              trailing: _remove('festivals', 'remove', _s(x['id']))),
        _line(_s(f['note']), muted: true),
      ]),
      _box('Release windows', [
        GlassButton(label: 'Add window', icon: Icons.calendar_month_rounded, height: 38, onTap: _busy ? null : () => _add('windows', 'Release window', const [
              ('medium', 'Medium (theatrical / svod / avod / tv ...)'),
              ('territory', 'Territory (india, uae or world)'),
              ('start', 'Start (YYYY-MM-DD)'),
              ('end', 'Ends (or blank)'),
              ('licensee', 'Licensee'),
            ], const {'op': 'add'})),
        const SizedBox(height: 6),
        ..._flags([
          for (final c in _list(chk['conflicts'])) _s(c['why'] ?? c),
          for (final v in _list(chk['holdback_violations'])) _s(v['why']),
        ]),
        for (final x in _list(w['windows']))
          _row('${_s(x['medium'])} · ${_s(x['territory'])} · ${_s(x['start'])} → ${_s(x['end']).isEmpty ? '–' : _s(x['end'])}${x['exclusive'] == true ? ' · exclusive' : ''}',
              trailing: _remove('windows', 'remove', _s(x['id']))),
        _line(_s(chk['note']), muted: true),
      ]),
    ];
  }

  List<Widget> _delivery() {
    final d = _m(_d['deliverables']);
    final l = _m(_d['localisation']);
    return [
      _box('Deliverables (${_s(d['done'])}/${_s(d['total'])})', [
        Wrap(spacing: 8, runSpacing: 6, children: [
          GlassButton(label: 'Add item', icon: Icons.add_task_rounded, height: 38, onTap: _busy ? null : () => _add('deliverables', 'Deliverable', const [
                ('label', 'Item'),
                ('buyer', 'Buyer / festival'),
                ('due', 'Due (YYYY-MM-DD)'),
              ], const {'op': 'add'})),
          GlassButton(label: 'Festival list', icon: Icons.list_alt_rounded, height: 38,
              onTap: _busy ? null : () => _post('deliverables', {'op': 'starter', 'kind': 'festival'})),
          GlassButton(label: 'OTT list', icon: Icons.list_alt_rounded, height: 38,
              onTap: _busy ? null : () => _post('deliverables', {'op': 'starter', 'kind': 'ott'})),
        ]),
        const SizedBox(height: 6),
        ..._flags(d['flags']),
        for (final x in _list(d['deliverables']))
          _row('${_s(x['label'])} · ${_s(x['buyer'])} · ${_s(x['due']).isEmpty ? '–' : _s(x['due'])} · ${_s(x['status'])}',
              trailing: _remove('deliverables', 'remove', _s(x['id']))),
        _line(_s(d['note']), muted: true),
      ]),
      _box('Subtitles and dub (${_s(l['done'])}/${_s(l['total'])})', [
        GlassButton(label: 'Add a language', icon: Icons.translate_rounded, height: 38, onTap: _busy ? null : () => _add('localisation', 'Language', const [
              ('language', 'Language'),
              ('kind', 'subtitles / dub / both'),
              ('dub_mode', 'human / ai_voice'),
              ('voice_person', 'If an AI voice, its register number (P-001)'),
              ('vendor', 'Vendor'),
              ('due', 'Due (YYYY-MM-DD)'),
            ], const {'op': 'add'})),
        const SizedBox(height: 6),
        ..._flags(l['flags']),
        for (final x in _list(l['localisation']))
          _row('${_s(x['language'])} · ${_s(x['kind'])}${_s(x['dub_mode']).isEmpty ? '' : ' (${_s(x['dub_mode'])})'} · ${_s(x['status'])}',
              trailing: _remove('localisation', 'remove', _s(x['id']))),
        _line(_s(l['note']), muted: true),
      ]),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final body = switch (_tab) {
      0 => _script(),
      1 => _shots(),
      2 => _schedule(),
      3 => _paisa(),
      4 => _sales(),
      _ => _delivery(),
    };
    return Scaffold(
      backgroundColor: C.bgTop,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('Producer · ${widget.ref}'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: Column(children: [
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (var i = 0; i < _tabs.length; i++)
              Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                      label: Text(_tabs[i]),
                      selected: _tab == i,
                      onSelected: (_) {
                        setState(() => _tab = i);
                        _load();
                      })),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(16), children: body)),
        ),
      ]),
    );
  }
}
