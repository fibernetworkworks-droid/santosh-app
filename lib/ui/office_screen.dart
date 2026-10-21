/// Profile > Daftar (v0.85): Hoola as the office manager.
/// Aaj (morning list), Saamaan (stock, learned reorder point, reorder cards), Repair (tickets with SLA), Renewal (licences,
/// AMC, rent, insurance; India starter list), Team (deadlines + reminder drafts she sends), Kharcha (spend cards for her
/// Haan, petty cash, vendor bills), Note (weekly office note) and Niyam. Chat cards: spend card, morning list, nudge draft.
library;

import 'package:flutter/material.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
double? _num(String t) => double.tryParse(t.trim().replaceAll(',', '').replaceAll('₹', '').replaceAll('Rs', '').trim());
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _prio = {'urgent': 'Turant', 'high': 'Zaroori', 'normal': 'Normal', 'low': 'Aaram se'};
Color _prioCol(String p) => switch (p) { 'urgent' => C.bad, 'high' => C.accent, 'low' => C.faint, _ => C.accentSoft };
const _tstatus = {'open': 'Khula', 'assigned': 'Vendor ko diya', 'waiting': 'Parts ka intezaar', 'done': 'Theek', 'cancelled': 'Band'};

Future<Map<String, String>?> _ask(BuildContext context, String title, List<(String key, String label, bool number)> fields,
    {Map<String, String> init = const {}}) async {
  final cs = {for (final f in fields) f.$1: TextEditingController(text: init[f.$1] ?? '')};
  final ok = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final f in fields)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: TextField(
                controller: cs[f.$1],
                keyboardType: f.$3 ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
                decoration: InputDecoration(labelText: f.$2),
              ),
            ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Rehne do')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save')),
      ],
    ),
  );
  if (ok != true) return null;
  return {for (final e in cs.entries) e.key: e.value.text.trim()};
}

class OfficeScreen extends StatefulWidget {
  const OfficeScreen({super.key, required this.app, this.tab = 0});
  final Santosh app;
  final int tab;
  @override
  State<OfficeScreen> createState() => _OfficeScreenState();
}

class _OfficeScreenState extends State<OfficeScreen> {
  Santosh get app => widget.app;
  Map<String, dynamic>? _d;
  String? _err;
  int _tick = -1;

  @override
  void initState() {
    super.initState();
    _tick = app.officeTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.officeTick != _tick) {
      _tick = app.officeTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final d = await app.api!.officeAll();
      if (mounted) setState(() {
        _d = d;
        _err = null;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Future<void> _do(Future<Map<String, dynamic>> Function() f) async {
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      if (mounted && _s(r['warn']).isNotEmpty) _snack(context, _s(r['warn']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 8,
        initialIndex: widget.tab,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            title: Text('${app.aName} · Office manager'),
            bottom: const TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [
              Tab(text: 'Aaj'),
              Tab(text: 'Saamaan'),
              Tab(text: 'Repair'),
              Tab(text: 'Renewal'),
              Tab(text: 'Team'),
              Tab(text: 'Kharcha'),
              Tab(text: 'Note'),
              Tab(text: 'Niyam'),
            ]),
          ),
          body: Aurora(
            child: _d == null
                ? Center(child: _err != null ? Padding(padding: const EdgeInsets.all(24), child: Text(_err!, style: const TextStyle(color: C.bad))) : const CircularProgressIndicator())
                : TabBarView(children: [
                    _wrap(_today()),
                    _wrap(_stock()),
                    _wrap(_tickets()),
                    _wrap(_renewals()),
                    _wrap(_team()),
                    _wrap(_money()),
                    _NoteTab(app: app),
                    _wrap(_rules()),
                  ]),
          ),
        ),
      );

  Widget _wrap(List<Widget> children) => RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: children),
      );

  Widget _head(String t, {Widget? trailing}) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 14, 4, 8),
        child: Row(children: [Expanded(child: Text(t, style: display(16))), if (trailing != null) trailing]),
      );

  Widget _empty(String t) => Padding(padding: const EdgeInsets.all(18), child: Text(t, style: const TextStyle(color: C.muted)));

  // ---------------------------------------------------------------- Aaj
  List<Widget> _today() {
    final d = Map<String, dynamic>.from(_d!['today'] as Map);
    final pend = _list(d['pending_spends']);
    return [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_s(d['nice']), style: display(18)),
          const SizedBox(height: 6),
          Text(_s(d['text']), style: const TextStyle(color: C.chip, height: 1.45)),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 6, children: [
            Pill('${_list(d['low']).length} kam saamaan', fg: _list(d['low']).isEmpty ? C.muted : C.accent),
            Pill('${_list(d['tickets']).length} khuli repair', fg: _list(d['late_tickets']).isEmpty ? C.chip : C.bad),
            Pill('${_list(d['renewals']).length} renewal paas', fg: C.accent2),
            Pill('${_list(d['deadlines']).length} deadline', fg: C.teal),
            if (pend.isNotEmpty) Pill('${pend.length} Haan baaki', fg: C.accent),
          ]),
        ]),
      ),
      if (pend.isNotEmpty) ...[
        _head('Aapki Haan chahiye'),
        for (final sp in pend) Padding(padding: const EdgeInsets.only(bottom: 10), child: OfficeSpendCard(v: sp, app: app, onDone: _load)),
      ],
      const SizedBox(height: 14),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${app.aName} se boliye', style: display(15)),
          const SizedBox(height: 6),
          const Text('"Printer ka toner khatam" · "AC cabin 2 kharab hai" · "Fire NOC 15 Jan ko renew" · '
              '"Rahul ko Friday tak sales report" · "chai ka 300 kharcha hua" · bill ki photo forward kijiye',
              style: TextStyle(color: C.muted, height: 1.4)),
        ]),
      ),
    ];
  }

  // ---------------------------------------------------------------- Saamaan
  List<Widget> _stock() {
    final items = _list(_d!['items']);
    final low = items.where((i) => i['low'] == true).toList();
    return [
      Row(children: [
        Expanded(
          child: GlassButton(
            label: 'Naya saamaan',
            icon: Icons.add_rounded,
            onTap: () async {
              final r = await _ask(context, 'Naya saamaan', [
                ('name', 'Naam (A4 paper, toner, chai patti)', false),
                ('qty', 'Abhi kitna hai', true),
                ('unit', 'Unit (pcs, ream, kg, box)', false),
                ('min_qty', 'Kam se kam kitna rahe (khaali = Hoola seekhega)', true),
                ('vendor', 'Kahan se aata hai (vendor)', false),
                ('price', 'Daam per unit (₹)', true),
              ]);
              if (r == null || r['name']!.isEmpty) return;
              await _do(() => app.api!.officeItem({
                    'name': r['name'],
                    if (_num(r['qty']!) != null) 'qty': _num(r['qty']!),
                    'unit': r['unit'],
                    if (_num(r['min_qty']!) != null) 'min_qty': _num(r['min_qty']!),
                    'vendor': r['vendor'],
                    if (_num(r['price']!) != null) 'price': _num(r['price']!),
                  }));
            },
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: GradientButton(
            label: low.isEmpty ? 'Sab theek' : 'Reorder (${low.length})',
            height: 48,
            onTap: low.isEmpty ? null : () => _do(() => app.api!.officeReorder(conversationId: app.conversationId ?? '')),
          ),
        ),
      ]),
      if (items.isEmpty) _empty('Abhi koi saamaan nahi. Chat mein boliye "A4 paper 10 ream hai" ya upar se jodiye.'),
      for (final it in items) _itemTile(it),
    ];
  }

  Widget _itemTile(Map<String, dynamic> it) {
    final low = it['low'] == true;
    final per = (it['per_day'] as num?) ?? 0;
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Glass(
        border: low ? C.accent : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(it['name']), style: display(15))),
            Text('${it['qty']} ${it['unit']}', style: TextStyle(color: low ? C.accent : C.ok, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 4),
          Text([
            if (per > 0) 'roz ~$per · ${it['days_left'] ?? '-'} din ka',
            'reorder ${it['reorder_point']}',
            if ((it['on_order'] as num? ?? 0) > 0) 'order mein ${it['on_order']}',
            if (_s(it['price']).isNotEmpty) '${it['price']}/${it['unit']}',
            if (it['vendor'] != null) _s((it['vendor'] as Map)['name']),
          ].join(' · '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Text(_s(it['why']), style: const TextStyle(color: C.faint, fontSize: 11.5)),
          const SizedBox(height: 6),
          Row(children: [
            TextButton.icon(
              icon: const Icon(Icons.remove_rounded, size: 18),
              label: const Text('Use hua'),
              onPressed: () async {
                final r = await _ask(context, '${it['name']}: kitna use hua?', [('qty', 'Kitna', true)], init: {'qty': '1'});
                final q = _num(r?['qty'] ?? '');
                if (q != null) await _do(() => app.api!.officeUse(_s(it['id']), q));
              },
            ),
            TextButton.icon(
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Aaya'),
              onPressed: () async {
                final r = await _ask(context, '${it['name']}: kitna aaya?', [('qty', 'Kitna', true), ('price', 'Daam per unit (₹)', true)]);
                final q = _num(r?['qty'] ?? '');
                if (q != null) {
                  await _do(() async {
                    final x = await app.api!.officeRestock(_s(it['id']), q, price: _num(r!['price']!));
                    return {...x, 'say': _s(x['price_note']).isNotEmpty ? x['price_note'] : 'Stock badh gaya.'};
                  });
                }
              },
            ),
          ]),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------- Repair
  List<Widget> _tickets() {
    final all = _list(_d!['tickets']);
    final open = all.where((t) => ['open', 'assigned', 'waiting'].contains(t['status'])).toList();
    final done = all.where((t) => !open.contains(t)).take(15).toList();
    return [
      GlassButton(
        label: 'Kuch kharab hai',
        icon: Icons.build_rounded,
        onTap: () async {
          final r = await _ask(context, 'Nayi repair', [
            ('title', 'Kya hua (AC thanda nahi kar raha)', false),
            ('asset', 'Kaun sa / kahan (AC cabin 2)', false),
            ('priority', 'turant / zaroori / normal / aaram (khaali = Hoola tay karega)', false),
            ('vendor', 'Kisko bulana hai (vendor)', false),
          ]);
          if (r == null || r['title']!.isEmpty) return;
          await _do(() => app.api!.officeTicketNew({...r, 'conversation_id': app.conversationId ?? ''}));
        },
      ),
      _head('Khuli (${open.length})'),
      if (open.isEmpty) _empty('Koi repair khuli nahi.'),
      for (final t in open) _ticketTile(t),
      if (done.isNotEmpty) _head('Pichhli'),
      for (final t in done) _ticketTile(t),
    ];
  }

  Widget _ticketTile(Map<String, dynamic> t) {
    final pr = _s(t['priority']);
    final open = ['open', 'assigned', 'waiting'].contains(t['status']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        border: t['late'] == true ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(_s(t['number']), style: const TextStyle(color: C.faint, fontWeight: FontWeight.w800)),
            const SizedBox(width: 8),
            Expanded(child: Text(_s(t['title']), style: display(14.5))),
            Pill(_prio[pr] ?? pr, fg: _prioCol(pr)),
          ]),
          const SizedBox(height: 4),
          Text([
            if (_s(t['asset']).isNotEmpty) _s(t['asset']),
            _tstatus[_s(t['status'])] ?? _s(t['status']),
            if (t['vendor'] != null) _s((t['vendor'] as Map)['name']),
            if (open && _s(t['due_in']).isNotEmpty) (t['late'] == true ? '${t['due_in']}' : 'theek karna: ${t['due_in']}'),
            if (_s(t['cost']).isNotEmpty) _s(t['cost']),
          ].join(' · '), style: TextStyle(color: t['late'] == true ? C.bad : C.muted, fontSize: 12.5)),
          if (open)
            Row(children: [
              TextButton(onPressed: () => _do(() => app.api!.officeTicket(_s(t['id']), {'status': 'done'})), child: const Text('Theek ho gaya')),
              TextButton(
                onPressed: () async {
                  final r = await _ask(context, '${t['number']}: update', [
                    ('vendor', 'Vendor', false),
                    ('cost', 'Kharcha / quote (₹): aapki Haan ke liye card banega', true),
                    ('note', 'Note', false),
                  ]);
                  if (r == null) return;
                  await _do(() => app.api!.officeTicket(_s(t['id']), {
                        if (r['vendor']!.isNotEmpty) 'vendor': r['vendor'],
                        if (_num(r['cost']!) != null) 'cost': _num(r['cost']!),
                        if (r['note']!.isNotEmpty) 'note': r['note'],
                        'conversation_id': app.conversationId ?? '',
                      }));
                },
                child: const Text('Vendor / kharcha'),
              ),
            ]),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------- Renewal
  List<Widget> _renewals() {
    final rs = _list(_d!['renewals']).where((r) => r['status'] == 'active').toList();
    final starters = _list(_d!['starters']).where((s) => s['added'] != true).toList();
    return [
      GlassButton(label: 'Renewal jodiye', icon: Icons.event_repeat_rounded, onTap: () => _addRenewal()),
      _head('Chalu (${rs.length})'),
      if (rs.isEmpty) _empty('Abhi koi renewal nahi. Neeche ki list se shuru kijiye, tareekh apne kagaz se.'),
      for (final r in rs) _renewalTile(r),
      if (starters.isNotEmpty) ...[
        _head('Aksar office mein hote hain'),
        for (final st in starters)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Glass(
              padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_s(st['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                    if (_s(st['tip']).isNotEmpty) Text(_s(st['tip']), style: const TextStyle(color: C.faint, fontSize: 11.5)),
                  ]),
                ),
                IconButton(icon: const Icon(Icons.add_circle_rounded, color: C.accent), onPressed: () => _addRenewal(starter: st)),
              ]),
            ),
          ),
      ],
    ];
  }

  Future<void> _addRenewal({Map<String, dynamic>? starter}) async {
    final r = await _ask(
      context,
      starter == null ? 'Renewal' : _s(starter['name']),
      [
        ('name', 'Kya (Fire NOC, AC AMC, rent, domain)', false),
        ('due_on', 'Kab (15/01/2027, 3 mahine)', false),
        ('amount', 'Rakam (₹)', true),
        ('every_months', 'Har kitne mahine (0 = ek baar)', true),
        ('notice_by', 'Mana karne ki aakhri tareekh (agar ho)', false),
        ('vendor', 'Vendor / office', false),
      ],
      init: {if (starter != null) 'name': _s(starter['name']), if (starter != null) 'every_months': _s(starter['every_months'])},
    );
    if (r == null || r['name']!.isEmpty || r['due_on']!.isEmpty) return;
    await _do(() => app.api!.officeRenewal({
          'name': r['name'],
          'due_on': r['due_on'],
          if (starter != null) 'kind': starter['kind'],
          if (_num(r['amount']!) != null) 'amount': _num(r['amount']!),
          if (_num(r['every_months']!) != null) 'every_months': _num(r['every_months']!)!.round(),
          'notice_by': r['notice_by'],
          'vendor': r['vendor'],
        }));
  }

  Widget _renewalTile(Map<String, dynamic> r) {
    final left = r['days_left'] as int?;
    final col = left == null ? C.muted : (left < 0 ? C.bad : (left <= 7 ? C.accent : (left <= 30 ? C.accent2 : C.ok)));
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        border: left != null && left <= 7 ? col : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(r['name']), style: display(14.5))),
            Pill(left == null ? '-' : (left < 0 ? '${-left} din se baaki' : (left == 0 ? 'Aaj' : '$left din')), fg: col),
          ]),
          const SizedBox(height: 4),
          Text([
            _s(r['kind_label']),
            _s(r['due_nice']),
            if (_s(r['amount']).isNotEmpty) _s(r['amount']),
            if ((r['every_months'] ?? 0) != 0) 'har ${r['every_months']} mahine',
            if (_s(r['notice_by']).isNotEmpty) 'mana karne ki tareekh ${r['notice_by']}',
          ].join(' · '), style: const TextStyle(color: C.muted, fontSize: 12.5)),
          Row(children: [
            TextButton(
              onPressed: () async {
                final x = await _ask(context, '${r['name']}: renew hua', [('paid', 'Kitna diya (₹)', true)]);
                if (x == null) return;
                await _do(() => app.api!.officeRenewalDone(_s(r['id']), paid: _num(x['paid']!)));
              },
              child: const Text('Renew ho gaya'),
            ),
            TextButton(
              onPressed: () => _do(() => app.api!.officeRenewalPay(_s(r['id']), conversationId: app.conversationId ?? '')),
              child: const Text('Bhugtan card'),
            ),
          ]),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------- Team
  List<Widget> _team() {
    final dl = _list(_d!['deadlines']);
    final open = dl.where((d) => d['status'] == 'open').toList();
    final done = dl.where((d) => d['status'] != 'open').take(12).toList();
    return [
      Row(children: [
        Expanded(
          child: GlassButton(
            label: 'Deadline',
            icon: Icons.flag_rounded,
            onTap: () async {
              final r = await _ask(context, 'Nayi deadline', [
                ('title', 'Kaam', false),
                ('owner', 'Kiska (team member)', false),
                ('due_on', 'Kab tak (Friday, 28/10, 3 din)', false),
              ]);
              if (r == null || r['title']!.isEmpty || r['due_on']!.isEmpty) return;
              await _do(() => app.api!.officeDeadline(r));
            },
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: GradientButton(
            label: 'Yaad dilao',
            height: 48,
            onTap: () => _do(() => app.api!.officeNudge(conversationId: app.conversationId ?? '')),
          ),
        ),
      ]),
      const Padding(
        padding: EdgeInsets.fromLTRB(4, 8, 4, 0),
        child: Text('Yaad-dihani ke message draft bante hain: aap WhatsApp / SMS se khud bhejti hain.', style: TextStyle(color: C.faint, fontSize: 12)),
      ),
      _head('Chalu (${open.length})'),
      if (open.isEmpty) _empty('Koi deadline nahi.'),
      for (final d in open)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            border: d['late'] == true ? C.bad : null,
            padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(_s(d['title']), style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text('${_s(d['owner']).isEmpty ? '-' : d['owner']} · ${d['due_nice']}${d['late'] == true ? ' · der' : ''}',
                      style: TextStyle(color: d['late'] == true ? C.bad : C.muted, fontSize: 12.5)),
                ]),
              ),
              IconButton(
                tooltip: 'Yaad dilao',
                icon: const Icon(Icons.notifications_active_rounded, color: C.accent2),
                onPressed: () => _do(() => app.api!.officeNudge(deadline: _s(d['id']), conversationId: app.conversationId ?? '')),
              ),
              IconButton(
                tooltip: 'Ho gaya',
                icon: const Icon(Icons.check_circle_rounded, color: C.ok),
                onPressed: () => _do(() => app.api!.officeDeadlineDone(_s(d['id']))),
              ),
            ]),
          ),
        ),
      if (done.isNotEmpty) _head('Puri hui'),
      for (final d in done)
        Padding(
          padding: const EdgeInsets.only(bottom: 6, left: 4),
          child: Text('✓ ${d['title']} (${_s(d['owner'])}) · ${d['done_on']}${_s(d['done_on']).compareTo(_s(d['due_on'])) > 0 ? ' · der se' : ''}',
              style: const TextStyle(color: C.muted)),
        ),
    ];
  }

  // ---------------------------------------------------------------- Kharcha
  List<Widget> _money() {
    final spends = _list(_d!['spends']);
    final pend = spends.where((s) => s['status'] == 'pending').toList();
    final past = spends.where((s) => s['status'] != 'pending').take(15).toList();
    final petty = Map<String, dynamic>.from(_d!['petty'] as Map);
    final bills = _list(_d!['bills']).where((b) => b['paid'] != true).toList();
    return [
      if (pend.isNotEmpty) _head('Aapki Haan chahiye'),
      for (final sp in pend) Padding(padding: const EdgeInsets.only(bottom: 10), child: OfficeSpendCard(v: sp, app: app, onDone: _load)),
      _head('Petty cash', trailing: Text(_s(petty['balance']), style: display(16))),
      Row(children: [
        Expanded(
          child: GlassButton(
            label: 'Kharcha',
            icon: Icons.remove_rounded,
            onTap: () async {
              final r = await _ask(context, 'Petty cash se kharcha', [('amount', 'Rakam (₹)', true), ('what', 'Kis cheez ka', false), ('by', 'Kisne kiya', false)]);
              if (r == null || _num(r['amount']!) == null) return;
              await _do(() => app.api!.officePetty({'amount': _num(r['amount']!), 'what': r['what'], 'by': r['by'], 'kind': 'out'}));
            },
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: GlassButton(
            label: 'Paise daale',
            icon: Icons.add_rounded,
            onTap: () async {
              final r = await _ask(context, 'Petty cash mein daale', [('amount', 'Rakam (₹)', true)]);
              if (r == null || _num(r['amount']!) == null) return;
              await _do(() => app.api!.officePetty({'amount': _num(r['amount']!), 'what': 'petty cash daala', 'kind': 'in'}));
            },
          ),
        ),
      ]),
      if ((petty['no_bill'] ?? 0) > 0)
        Padding(padding: const EdgeInsets.only(top: 6, left: 4), child: Text('${petty['no_bill']} kharche bina bill ke', style: const TextStyle(color: C.accent, fontSize: 12.5))),
      for (final e in _list(petty['entries']).take(10))
        Padding(
          padding: const EdgeInsets.only(top: 6, left: 4),
          child: Text('${e['on']} · ${e['kind'] == 'in' ? '+' : '-'}${e['amount']} · ${e['what']}${_s(e['by']).isNotEmpty ? ' (${e['by']})' : ''}',
              style: TextStyle(color: e['kind'] == 'in' ? C.ok : C.chip, fontSize: 13)),
        ),
      _head('Vendor bill (${bills.length})',
          trailing: TextButton(
            onPressed: () async {
              final r = await _ask(context, 'Vendor bill', [
                ('vendor', 'Vendor', false),
                ('amount', 'Rakam (₹)', true),
                ('number', 'Bill number', false),
                ('bill_date', 'Bill ki tareekh', false),
                ('due_on', 'Due date', false),
                ('gst', 'GST (₹)', true),
              ]);
              if (r == null || _num(r['amount']!) == null) return;
              await _do(() => app.api!.officeBill({...r, 'amount': _num(r['amount']!), 'gst': _num(r['gst']!)}));
            },
            child: const Text('+ Bill'),
          )),
      if (bills.isEmpty) _empty('Koi bill baaki nahi. Bill ki photo chat mein bhejiye, Hoola darj kar dega.'),
      for (final b in bills)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Glass(
            border: (b['flags'] as List? ?? const []).isNotEmpty ? C.accent : null,
            padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${b['vendor'] == null ? '' : (b['vendor'] as Map)['name']} · ${b['amount']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text([if (_s(b['number']).isNotEmpty) _s(b['number']), _s(b['bill_date']), if (_s(b['due_nice']).isNotEmpty) 'due ${b['due_nice']}'].join(' · '),
                      style: const TextStyle(color: C.muted, fontSize: 12.5)),
                  for (final f in (b['flags'] as List? ?? const [])) Text('$f', style: const TextStyle(color: C.accent, fontSize: 12)),
                ]),
              ),
              TextButton(onPressed: () => _do(() => app.api!.officeBillPaid(_s(b['id']))), child: const Text('Paid')),
            ]),
          ),
        ),
      if (past.isNotEmpty) _head('Pichhle kharcha card'),
      for (final sp in past)
        Padding(
          padding: const EdgeInsets.only(bottom: 6, left: 4),
          child: Text('${sp['number']} · ${sp['title']} · ${_s(sp['amount']).isEmpty ? '-' : sp['amount']} · ${sp['status'] == 'approved' ? 'Haan' : 'Mana'}',
              style: TextStyle(color: sp['status'] == 'approved' ? C.ok : C.faint, fontSize: 13)),
        ),
    ];
  }

  // ---------------------------------------------------------------- Niyam
  List<Widget> _rules() {
    final st = Map<String, dynamic>.from(_d!['settings'] as Map);
    final team = _list(st['team']);
    Widget row(String k, String label, String v, {bool number = false}) => ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: Text(v.isEmpty ? '-' : v),
          trailing: const Icon(Icons.edit_rounded, size: 18),
          onTap: () async {
            final r = await _ask(context, label, [(k, label, number)], init: {k: v});
            if (r == null) return;
            final val = number ? _num(r[k]!) : r[k];
            await _do(() async {
              await app.api!.officeSettings({k: val});
              return {'say': 'Save'};
            });
          },
        );
    return [
      Glass(
        child: Column(children: [
          row('office_name', 'Office ka naam', _s(st['office_name'])),
          row('morning_time', 'Subah ki list kab', _s(st['morning_time'])),
          row('note_day', 'Hafte ka note kis din (Som..Ravi)', _s(st['note_day_name'])),
          row('note_time', 'Note kis samay', _s(st['note_time'])),
          row('month_budget', 'Mahine ka budget (₹, 0 = nahi)', '${st['month_budget'] ?? 0}', number: true),
          row('lead_days', 'Vendor kitne din mein deta hai', '${st['lead_days']}', number: true),
          row('safety_days', 'Kitne din ka extra stock', '${st['safety_days']}', number: true),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: st['enabled'] != false,
            title: const Text('Subah ki list aur hafte ka note'),
            onChanged: (v) => _do(() async {
              await app.api!.officeSettings({'enabled': v});
              return {'say': v ? 'Chalu' : 'Band'};
            }),
          ),
        ]),
      ),
      _head('Team (${team.length})',
          trailing: TextButton(
            onPressed: () async {
              final r = await _ask(context, 'Team member', [('name', 'Naam', false), ('phone', 'Mobile (yaad-dihani draft ke liye)', false), ('role', 'Kaam', false)]);
              if (r == null || r['name']!.isEmpty) return;
              await _do(() async {
                await app.api!.officeSettings({'team': [...team, r]});
                return {'say': '${r['name']} jud gaye'};
              });
            },
            child: const Text('+ Jodiye'),
          )),
      for (final m in team)
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.person_rounded),
          title: Text(_s(m['name'])),
          subtitle: Text([_s(m['role']), _s(m['phone'])].where((x) => x.isNotEmpty).join(' · ')),
          trailing: IconButton(
            icon: const Icon(Icons.close_rounded),
            onPressed: () => _do(() async {
              await app.api!.officeSettings({'team': team.where((x) => x != m).toList()});
              return {'say': 'Hata diya'};
            }),
          ),
        ),
      const SizedBox(height: 10),
      const Text('Paise kabhi khud nahi jaate: har order, repair aur renewal ka bhugtan aapki Haan ke baad aap apne app se karti hain.',
          style: TextStyle(color: C.faint, fontSize: 12)),
    ];
  }
}

class _NoteTab extends StatefulWidget {
  const _NoteTab({required this.app});
  final Santosh app;
  @override
  State<_NoteTab> createState() => _NoteTabState();
}

class _NoteTabState extends State<_NoteTab> {
  Map<String, dynamic>? _n;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _get(false);
  }

  Future<void> _get(bool file) async {
    setState(() => _busy = true);
    try {
      final n = await widget.app.api!.officeNote(file: file, conversationId: widget.app.conversationId ?? '');
      if (mounted) setState(() => _n = n);
      if (file && mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Word file chat mein bhej di')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 96), children: [
        GradientButton(label: 'Word file banao', icon: Icons.description_rounded, height: 48, onTap: _busy ? null : () => _get(true)),
        const SizedBox(height: 12),
        if (_n == null) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
        if (_n != null) Glass(child: SelectableText(_s(_n!['text']), style: const TextStyle(color: C.chip, height: 1.45))),
      ]);
}

// ---------------------------------------------------------------- chat cards
/// A spend Hoola prepared: her Haan / Mana. Approve never pays; it gives the vendor message draft she sends herself.
class OfficeSpendCard extends StatefulWidget {
  const OfficeSpendCard({super.key, required this.v, required this.app, this.onDone});
  final Map<String, dynamic> v;
  final Santosh app;
  final VoidCallback? onDone;
  @override
  State<OfficeSpendCard> createState() => _OfficeSpendCardState();
}

class _OfficeSpendCardState extends State<OfficeSpendCard> {
  late final TextEditingController _a =
      TextEditingController(text: widget.v['amount_rupees'] == null ? '' : '${(widget.v['amount_rupees'] as num).round()}');
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.officeDecideSpend(_s(widget.v['id']), yes, amount: yes ? _num(_a.text) : null);
      widget.v.addAll(Map<String, dynamic>.from((r['spend'] as Map?) ?? const {}));
      if (mounted) _snack(context, _s(r['say']));
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final st = _s(v['status']);
    final pending = st == 'pending';
    final lines = _list(v['lines']);
    return Glass(
      border: pending ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.account_balance_wallet_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${v['number']} · ${v['title']}', style: display(15))),
          if (!pending) Pill(st == 'approved' ? 'Haan ${_s(v['amount'])}' : 'Mana', fg: st == 'approved' ? C.ok : C.faint),
        ]),
        if (v['vendor'] != null)
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('Vendor: ${(v['vendor'] as Map)['name']}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
        for (final l in lines)
          Text('• ${l['name']} ${l['qty']} ${_s(l['unit'])}', style: const TextStyle(color: C.chip, fontSize: 13)),
        for (final c in (v['checks'] as List? ?? const []))
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('$c', style: const TextStyle(color: C.faint, fontSize: 12))),
        if (_s(v['note']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(_s(v['note']), style: const TextStyle(color: C.accent2, fontSize: 12.5))),
        if (_s(v['month_budget']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('Is mahine: ${v['month_spent']} kharch · ${v['month_left']} bacha', style: TextStyle(color: v['over_budget'] == true ? C.bad : C.muted, fontSize: 12.5)),
          ),
        if (pending) ...[
          const SizedBox(height: 8),
          SizedBox(
            width: 160,
            child: TextField(controller: _a, keyboardType: TextInputType.number, decoration: const InputDecoration(prefixText: '₹ ', labelText: 'Rakam')),
          ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: 'Mana', onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 10),
            Expanded(child: GradientButton(label: 'Haan', height: 48, onTap: _busy ? null : () => _decide(true))),
          ]),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Haan = aage badho. Paise aap apne app se dengi.', style: TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        ],
        if (st == 'approved' && _s(v['vendor_message']).isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(_s(v['vendor_message']), style: const TextStyle(color: C.chip, fontSize: 13)),
          const SizedBox(height: 6),
          Wrap(spacing: 8, children: [
            if (_s(v['wa_link']).isNotEmpty) GlassButton(label: 'WhatsApp', icon: Icons.send_rounded, height: 40, onTap: () => Native.openExternal(url: _s(v['wa_link']))),
            if (_s(v['sms_link']).isNotEmpty) GlassButton(label: 'SMS', height: 40, onTap: () => Native.openExternal(url: _s(v['sms_link']))),
            if (_s(v['mail_link']).isNotEmpty) GlassButton(label: 'Email', height: 40, onTap: () => Native.openExternal(url: _s(v['mail_link']))),
          ]),
        ],
      ]),
    );
  }
}

/// A reminder message for a team member: Hoola drafts, she sends.
class OfficeNudgeCard extends StatefulWidget {
  const OfficeNudgeCard({super.key, required this.v});
  final Map<String, dynamic> v;
  @override
  State<OfficeNudgeCard> createState() => _OfficeNudgeCardState();
}

class _OfficeNudgeCardState extends State<OfficeNudgeCard> {
  late final TextEditingController _t = TextEditingController(text: _s(widget.v['text']));

  Future<void> _open(String how) async {
    final phone = _s(widget.v['phone']);
    final text = Uri.encodeComponent(_t.text.trim());
    await Native.openExternal(url: how == 'sms' ? 'sms:+91$phone?body=$text' : 'https://wa.me/91$phone?text=$text');
    if (mounted) setState(() => widget.v['opened'] = true);
  }

  @override
  Widget build(BuildContext context) {
    final phone = _s(widget.v['phone']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.notifications_active_rounded, color: C.accent2, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Yaad dilana: ${_s(widget.v['who']).isEmpty ? 'team' : widget.v['who']}', style: display(15))),
          if (widget.v['opened'] == true) const Pill('Khola', fg: C.teal),
        ]),
        const SizedBox(height: 8),
        TextField(controller: _t, minLines: 2, maxLines: 6, decoration: const InputDecoration(labelText: 'Message (badal sakti hain)')),
        const SizedBox(height: 8),
        if (phone.length == 10)
          Row(children: [
            Expanded(child: GradientButton(label: 'WhatsApp par bhejo', icon: Icons.send_rounded, height: 44, onTap: () => _open('whatsapp'))),
            const SizedBox(width: 8),
            GlassButton(label: 'SMS', height: 44, onTap: () => _open('sms')),
          ])
        else
          const Text('Number nahi hai: Office > Niyam > Team mein jodiye, ya message copy karke bhejiye.', style: TextStyle(color: C.faint, fontSize: 12)),
      ]),
    );
  }
}

/// The morning office list in the chat.
class OfficeDayCard extends StatelessWidget {
  const OfficeDayCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.business_center_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('Aaj ka office', style: display(16))),
            if ((v['pending_spends'] ?? 0) > 0) Pill('${v['pending_spends']} Haan baaki', fg: C.accent),
            if ((v['late_tickets'] ?? 0) > 0) Pill('${v['late_tickets']} der', fg: C.bad),
          ]),
          const SizedBox(height: 8),
          Text(_s(v['text']), style: const TextStyle(color: C.chip, height: 1.4)),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => OfficeScreen(app: app))),
              child: const Text('Office kholo'),
            ),
          ),
        ]),
      );
}

/// The weekly office note in the chat (the Word file comes as its own file card).
class OfficeNoteCard extends StatelessWidget {
  const OfficeNoteCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final n = Map<String, dynamic>.from((v['numbers'] as Map?) ?? const {});
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.summarize_rounded, color: C.teal, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Hafte ka office note', style: display(16))),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 6, children: [
          Pill('Repair ${n['tickets_closed'] ?? 0}/${n['tickets_opened'] ?? 0} theek'),
          Pill('Manzoor ${n['approved'] ?? '₹0'}', fg: C.ok),
          Pill('Renewal ${n['renewals_coming'] ?? 0} aane wale', fg: C.accent2),
          if ((n['deadlines_missed'] ?? 0) > 0) Pill('${n['deadlines_missed']} deadline der', fg: C.bad),
        ]),
        const SizedBox(height: 8),
        Text(_s(v['text']).split('\n').skip(2).take(9).join('\n'), style: const TextStyle(color: C.muted, fontSize: 12.5, height: 1.35)),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => OfficeScreen(app: app, tab: 6))),
            child: const Text('Poora note'),
          ),
        ),
      ]),
    );
  }
}
