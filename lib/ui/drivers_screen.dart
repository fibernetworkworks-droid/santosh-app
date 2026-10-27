/// Profile > Driver Sahayak: Hoola as the driver coordinator.
/// Aaj (today / tomorrow, missing trip sheets, documents expiring, drafts) · Duty (plan + roster with law checks) ·
/// Trip sheet (her words / photo of the paper sheet, km + fuel checks) · Driver (licence in the locker, dates, leave) ·
/// Hazri (attendance for payroll) · Niyam (her limits, the law's limits, vehicles).
/// A message reaches a driver only when SHE taps send; money / advances are payroll's / hers.
library;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
Map<String, dynamic> _m(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
void _snack(BuildContext c, String t) {
  if (t.trim().isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

String _num(dynamic v) {
  if (v == null) return '';
  if (v is num) return v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1);
  return '$v';
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Save', Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'text' ? 4 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  if (res != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, [Object? body]) async {
  try {
    final r = await app.api!.call(method, path, body: body);
    final m = _m(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

Color _flagColor(String level) => switch (level) { 'bad' => C.bad, 'warn' => C.warn, _ => C.muted };

class DriversScreen extends StatefulWidget {
  const DriversScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<DriversScreen> createState() => _DriversScreenState();
}

class _DriversScreenState extends State<DriversScreen> {
  Map<String, dynamic>? _d;
  Map<String, dynamic>? _att;
  int _tab = 0;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/drivers'));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
    return r;
  }

  // ---------------------------------------------------------------- duty
  Future<void> _newDuty() async {
    final f = await _form(context, 'Nayi duty', const [
      ('driver', 'Driver (naam / D-001)'),
      ('day', 'Din (dd-mm-yyyy / aaj / kal)'),
      ('start', 'Shuru (6:00)'),
      ('end', 'Khatam (14:00)'),
      ('vehicle', 'Gaadi number'),
      ('route', 'Route (Pune - Nashik)'),
      ('break_min', 'Aaraam (minute)'),
    ], ok: 'Check karke lagao');
    if (f == null || (f['driver'] ?? '').isEmpty) return;
    final body = <String, dynamic>{...f, 'break_min': int.tryParse(f['break_min'] ?? '') ?? 0};
    final r = await _run('POST', '/api/drivers/duties', body);
    if (r != null && r['saved'] == false && mounted) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: const Text('Niyam se bahar'),
          content: Text(_s(r['say'])),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Badal deti hoon')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Phir bhi lagao (wajah ke saath)')),
          ],
        ),
      );
      if (ok != true || !mounted) return;
      final w = await _form(context, 'Wajah (log mein rahegi)', const [('reason', 'Kyun zaroori hai')], ok: 'Lagao');
      if (w == null || (w['reason'] ?? '').length < 5) return;
      await _run('POST', '/api/drivers/duties', {...body, 'force': true, 'reason': w['reason']});
    }
  }

  Future<void> _plan() async {
    final f = await _form(context, 'Kaun le sakta hai?', const [
      ('day', 'Din (kal / dd-mm-yyyy)'),
      ('start', 'Shuru'),
      ('end', 'Khatam'),
      ('vehicle', 'Gaadi'),
      ('route', 'Route'),
    ], ok: 'Dekho');
    if (f == null) return;
    final r = await _run('POST', '/api/drivers/plan', {
      'day': f['day'] ?? 'kal',
      'needs': [
        {'start': f['start'] ?? '', 'end': f['end'] ?? '', 'vehicle': f['vehicle'] ?? '', 'route': f['route'] ?? ''}
      ],
    });
    if (r == null || !mounted) return;
    final p = _list(r['plan']);
    await showModalBottomSheet<void>(
      context: context,
      builder: (_) => ListView(padding: const EdgeInsets.all(16), children: [
        Text(_s(r['say']), style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        for (final n in p)
          for (final c in _list(n['drivers']))
            ListTile(
              dense: true,
              leading: Icon(c['ok'] == true ? Icons.check_circle_rounded : (c['can'] == true ? Icons.warning_amber_rounded : Icons.block_rounded),
                  color: c['ok'] == true ? C.ok : (c['can'] == true ? C.warn : C.bad)),
              title: Text('${_s(c['code'])} ${_s(c['name'])} · hafte ${_num(c['week_h'])} ghante'),
              subtitle: Text([...((c['why_not'] as List?) ?? const []), ...((c['tips'] as List?) ?? const [])].join(' ')),
            ),
      ]),
    );
  }

  Widget _dutyTile(Map<String, dynamic> x) {
    final c = _m(x['checks']);
    final law = (c['law'] as List?) ?? const [];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: law.isNotEmpty ? C.warn : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
                child: Text('${_s(x['number'])} · ${_s(x['driver'])} · ${_s(x['day'])} ${_s(x['start'])}-${_s(x['end'])}',
                    style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_s(x['status'])),
          ]),
          Text([_s(x['vehicle']), _s(x['route']), if (c['ot_h'] != null && (c['ot_h'] as num) > 0) 'OT ${_num(c['ot_h'])} h', if (x['told'] == true) 'bata diya']
              .where((e) => e.isNotEmpty)
              .join(' · '),
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          for (final l in law) Text('• $l', style: const TextStyle(fontSize: 12, color: C.warn)),
          if (_s(x['forced']).isNotEmpty) Text('Aapki wajah: ${_s(x['forced'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
          if (_s(x['status']) == 'planned')
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (st, label) in const [('done', 'Ho gayi'), ('absent', 'Nahi aaya'), ('cancelled', 'Radd')])
                  ActionChip(label: Text(label), onPressed: _busy ? null : () => _run('POST', '/api/drivers/duties/${_s(x['id'])}/status', {'status': st})),
              ]),
            ),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------- trip sheets
  Future<void> _newTrip() async {
    final f = await _form(context, 'Trip sheet', const [
      ('driver', 'Driver'),
      ('day', 'Din (aaj / dd-mm-yyyy)'),
      ('vehicle', 'Gaadi'),
      ('text', 'Jaisa likha hai: start 45210 end 45480, diesel 40 L 3800, toll 450'),
    ], ok: 'Check karo');
    if (f == null || (f['driver'] ?? '').isEmpty) return;
    await _run('POST', '/api/drivers/trips', f);
  }

  Future<void> _tripPhoto(ImageSource src) async {
    final f = await _form(context, 'Kiski trip sheet?', const [('driver', 'Driver'), ('day', 'Din'), ('vehicle', 'Gaadi')], ok: 'Photo lo');
    if (f == null || (f['driver'] ?? '').isEmpty) return;
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 80, maxWidth: 2000);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      setState(() => _busy = true);
      final r = await widget.app.api!.uploadFile('/api/drivers/trips/photo', x.name.isEmpty ? 'trip.jpg' : x.name, bytes,
          fields: {'driver': f['driver'] ?? '', 'day': f['day'] ?? '', 'vehicle': f['vehicle'] ?? ''}, timeout: const Duration(seconds: 120), tries: 2);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _tripTile(Map<String, dynamic> t) {
    final flags = _list(t['flags']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: flags.any((f) => f['level'] == 'bad') ? C.bad : (t['status'] == 'draft' ? C.accent : null),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${_s(t['number'])} · ${_s(t['driver'])} · ${_s(t['day'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(t['status'] == 'draft' ? 'jaanchiye' : _s(t['status'])),
          ]),
          Text(
              [
                _s(t['vehicle']),
                if (t['km'] != null) '${_num(t['km'])} km (${_num(t['start_km'])}-${_num(t['end_km'])})',
                if (_s(t['start_time']).isNotEmpty) '${_s(t['start_time'])}-${_s(t['end_time'])}',
                if (t['fuel_l'] != null) 'fuel ${_num(t['fuel_l'])} L',
                if ((t['spent'] ?? 0) != 0) 'kharcha Rs ${_num(t['spent'])}',
              ].where((e) => e.isNotEmpty).join(' · '),
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          for (final f in flags) Text('• ${_s(f['say'])}', style: TextStyle(fontSize: 12, color: _flagColor(_s(f['level'])))),
          if (t['status'] == 'draft')
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(spacing: 6, children: [
                ActionChip(label: const Text('Sahi hai'), onPressed: _busy ? null : () => _run('POST', '/api/drivers/trips/${_s(t['id'])}/ok', {'ok': true})),
                ActionChip(label: const Text('Galat'), onPressed: _busy ? null : () => _run('POST', '/api/drivers/trips/${_s(t['id'])}/ok', {'ok': false})),
              ]),
            ),
        ]),
      ),
    );
  }

  // ---------------------------------------------------------------- drivers
  Future<void> _editDriver([Map<String, dynamic>? d]) async {
    final f = await _form(
        context,
        d == null ? 'Naya driver' : '${_s(d['code'])} ${_s(d['name'])}',
        [
          ('name', 'Naam'),
          ('phone', 'Mobile (10 ank)'),
          ('licence', d == null ? 'Licence number (Locker mein band rahega)' : 'Naya licence number (sirf badalna ho to)'),
          ('classes', 'Licence class (LMV, HGV, TRANS, hazardous...)'),
          ('dl_valid_to', 'Licence kab tak (dd-mm-yyyy)'),
          ('medical_valid_to', 'Medical (Form 1A) kab tak'),
          ('badge_valid_to', 'Badge kab tak'),
          ('police_on', 'Police verification kab hua'),
          ('vehicle', 'Aam gaadi'),
          ('payroll_name', 'Payroll mein naam / code'),
          ('member', 'Hoola team member (naam / Hoola ID)'),
        ],
        initial: d == null
            ? const {}
            : {
                'name': _s(d['name']),
                'phone': _s(d['phone']),
                'classes': ((d['classes'] as List?) ?? const []).join(', '),
                'dl_valid_to': _s(d['dl_valid_to']),
                'medical_valid_to': _s(d['medical_valid_to']),
                'badge_valid_to': _s(d['badge_valid_to']),
                'police_on': _s(d['police_on']),
                'vehicle': _s(d['vehicle']),
                'payroll_name': _s(d['payroll_name']),
              });
    if (f == null || f.isEmpty) return;
    if (d == null) {
      await _run('POST', '/api/drivers/drivers', f);
    } else {
      await _run('PATCH', '/api/drivers/drivers/${_s(d['id'])}', f);
    }
  }

  Future<void> _leave(Map<String, dynamic> d) async {
    final f = await _form(context, '${_s(d['name'])}: chhutti', const [
      ('start', 'Kab se'),
      ('end', 'Kab tak (ek din ho to khaali)'),
      ('kind', 'leave / sick / off / unpaid'),
      ('note', 'Note'),
    ], ok: 'Darj karo');
    if (f == null || (f['start'] ?? '').isEmpty) return;
    await _run('POST', '/api/drivers/leaves', {...f, 'driver': _s(d['id'])});
  }

  Widget _driverTile(Map<String, dynamic> d) {
    final docs = _list(d['docs']);
    final bad = docs.any((x) => x['state'] == 'expired' || x['state'] == 'missing');
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _editDriver(d),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: bad ? C.bad : (docs.any((x) => x['state'] == 'soon') ? C.warn : null),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${_s(d['code'])} · ${_s(d['name'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              if (d['active'] != true) const Pill('left'),
              if (_s(d['member_id']).isNotEmpty) const Pill('Hoola team'),
            ]),
            Text(
                [
                  _s(d['phone']),
                  if (_s(d['dl']).isNotEmpty) 'DL ${_s(d['dl'])}',
                  ((d['classes'] as List?) ?? const []).join('/').toUpperCase(),
                  _s(d['vehicle']),
                ].where((e) => e.isNotEmpty).join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12.5)),
            for (final x in docs.where((x) => x['state'] != 'ok'))
              Text(
                  '• ${_s(x['label'])}: ${x['state'] == 'missing' ? 'taareekh darj nahi' : (x['state'] == 'expired' ? 'khatam (${_s(x['on'])})' : '${x['days_left']} din (${_s(x['on'])})')}',
                  style: TextStyle(fontSize: 12, color: x['state'] == 'soon' ? C.warn : C.bad)),
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(spacing: 6, children: [
                ActionChip(label: const Text('Chhutti'), onPressed: _busy ? null : () => _leave(d)),
                ActionChip(label: const Text('Message'), onPressed: _busy ? null : () => _message(d)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _message(Map<String, dynamic> d) async {
    final f = await _form(context, '${_s(d['name'])} ko message (draft)', const [('text', 'Kya likhna hai')], ok: 'Draft banao');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '/api/drivers/messages', {'driver': _s(d['id']), 'text': f['text']});
  }

  // ---------------------------------------------------------------- tabs
  Widget _today() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Kal ki duty bhejo', icon: Icons.send_rounded, onTap: _busy ? null : () => _run('POST', '/api/drivers/day_plan', {'day': 'kal'})),
        GlassButton(label: 'Trip sheet maango', icon: Icons.receipt_long_rounded, onTap: _busy ? null : () => _run('POST', '/api/drivers/sheet_reminders')),
      ]),
      const SizedBox(height: 10),
      if (_list(d['drafts']).isNotEmpty) Text('Bhejne ke liye taiyaar', style: display(15)),
      for (final m in _list(d['drafts'])) Padding(padding: const EdgeInsets.only(top: 6), child: DriversMessageTile(app: widget.app, m: m, onDone: _load)),
      if (_list(d['duties']).isNotEmpty) ...[const SizedBox(height: 10), Text('Aaj ki duty', style: display(15))],
      for (final x in _list(d['duties'])) _dutyTile(x),
      if (_list(d['missing_sheets']).isNotEmpty) ...[const SizedBox(height: 6), Text('Trip sheet baaki', style: display(14))],
      for (final x in _list(d['missing_sheets']))
        Text('• ${_s(x['driver'])} ${_s(x['day'])} ${_s(x['start'])}-${_s(x['end'])} ${_s(x['vehicle'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
      if (_list(d['docs']).isNotEmpty) ...[const SizedBox(height: 6), Text('Kaagaz', style: display(14))],
      for (final x in _list(d['docs']))
        Text('• ${_s(x['driver'])}: ${_s(x['label'])} ${x['state'] == 'missing' ? 'darj nahi' : (x['state'] == 'expired' ? 'khatam' : '${x['days_left']} din')}',
            style: TextStyle(fontSize: 12.5, color: x['state'] == 'soon' ? C.warn : C.bad)),
      if (((d['free'] as List?) ?? const []).isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text('Aaj khaali: ${((d['free'] as List?) ?? const []).join(', ')}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        ),
    ]);
  }

  Widget _roster() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: GradientButton(label: 'Nayi duty', icon: Icons.add_rounded, height: 48, onTap: _busy ? null : _newDuty)),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Kaun khaali?', icon: Icons.person_search_rounded, onTap: _busy ? null : _plan)),
        ]),
        const SizedBox(height: 10),
        if (_list(_d?['week']).isEmpty) const Text('Agle 7 din ki koi duty nahi.', style: TextStyle(color: C.muted)),
        for (final x in _list(_d?['week'])) _dutyTile(x),
      ]);

  Widget _trips() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'Likh kar', icon: Icons.edit_note_rounded, height: 48, onTap: _busy ? null : _newTrip),
          GlassButton(label: 'Photo lo', icon: Icons.photo_camera_rounded, onTap: _busy ? null : () => _tripPhoto(ImageSource.camera)),
          GlassButton(label: 'Gallery', icon: Icons.photo_library_rounded, onTap: _busy ? null : () => _tripPhoto(ImageSource.gallery)),
        ]),
        const SizedBox(height: 10),
        for (final t in _list(_d?['trips'])) _tripTile(t),
      ]);

  Widget _drivers() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GradientButton(label: 'Naya driver', icon: Icons.person_add_alt_1_rounded, height: 48, onTap: _busy ? null : () => _editDriver()),
        const SizedBox(height: 10),
        for (final d in _list(_d?['drivers'])) _driverTile(d),
        if (_list(_d?['leaves_all']).isNotEmpty) Text('Chhutti', style: display(14)),
        for (final l in _list(_d?['leaves_all']))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('${_s(l['driver'])} · ${_s(l['start'])} - ${_s(l['end'])} (${_s(l['kind'])})'),
            trailing: IconButton(icon: const Icon(Icons.close_rounded), onPressed: _busy ? null : () => _run('DELETE', '/api/drivers/leaves/${_s(l['id'])}')),
          ),
      ]);

  bool _attLoading = false;

  Future<void> _loadAtt([String month = '']) async {
    if (_attLoading) return;
    _attLoading = true;
    try {
      final r = _m(await widget.app.api!.call('GET', '/api/drivers/attendance', query: {if (month.isNotEmpty) 'month': month}));
      if (mounted) setState(() => _att = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    _attLoading = false;
  }

  Widget _hazri() {
    if (_att == null) {
      _loadAtt();
      return const Center(child: CircularProgressIndicator());
    }
    final a = _att!;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: Text('Mahina ${_s(a['month'])}', style: display(15))),
        TextButton(
            onPressed: () async {
              final f = await _form(context, 'Kaun sa mahina?', const [('month', 'YYYY-MM (2026-10)')], ok: 'Dekho');
              if (f != null) await _loadAtt(f['month'] ?? '');
            },
            child: const Text('Badlo')),
      ]),
      for (final r in _list(a['rows']))
        Glass(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${_s(r['code'])} · ${_s(r['name'])}', style: const TextStyle(fontWeight: FontWeight.w800)),
            Text(
                'Kaam ${r['present']} din · chhutti ${r['paid_leave']} · LOP ${r['lop']} · OT ${_num(r['ot_hours'])} h · ${_num(r['km'])} km · kharcha Rs ${_num(r['spent'])}',
                style: const TextStyle(fontSize: 12.5, color: C.muted)),
            if ((r['sheets_missing'] ?? 0) != 0) Text('${r['sheets_missing']} trip sheet nahi mili', style: const TextStyle(fontSize: 12, color: C.warn)),
          ]),
        ),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(label: 'Excel', icon: Icons.table_view_rounded, onTap: _busy ? null : () => _run('POST', '/api/drivers/attendance/file', {'month': _s(a['month'])})),
        GlassButton(label: 'Payroll mein daalo', icon: Icons.payments_outlined, onTap: _busy ? null : () => _run('POST', '/api/drivers/attendance/payroll', {'month': _s(a['month'])})),
      ]),
      const SizedBox(height: 6),
      Text(_s(a['say']), style: const TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  Widget _rules() {
    final st = _m(_d?['settings']);
    final lim = _m(st['limits']);
    final notes = _m(st['law_notes']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Jo seema check hoti hai', style: display(14)),
          Text('Din ${_num(lim['day_h'])} h · hafta ${_num(lim['week_h'])} h · spread-over ${_num(lim['spread_h'])} h · do duty ke beech ${_num(lim['between_h'])} h · lagaatar ${_num(lim['days_row'])} din',
              style: const TextStyle(fontSize: 12.5)),
          for (final n in notes.values) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.muted)),
        ]),
      ),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(
            label: 'Mere niyam',
            icon: Icons.rule_rounded,
            onTap: () async {
              final f = await _form(context, 'Aapke niyam (kaanoon se sakht hi chalenge)', const [
                ('business', 'Business ka naam'),
                ('day_h', 'Din mein max ghante'),
                ('week_h', 'Hafte mein max ghante'),
                ('between_h', 'Do duty ke beech kam se kam ghante'),
                ('morning_time', 'Subah ka note (07:00)'),
                ('evening_time', 'Kal ki duty ke drafts (19:00)'),
                ('police_months', 'Police verification har kitne mahine'),
                ('note', 'Apna niyam (shabdon mein)'),
              ], initial: {'business': _s(st['business']), 'morning_time': _s(st['morning_time']), 'evening_time': _s(st['evening_time'])});
              if (f == null || f.isEmpty) return;
              final body = <String, dynamic>{...f};
              for (final k in const ['day_h', 'week_h', 'between_h']) {
                if (f[k] != null) body[k] = double.tryParse(f[k]!) ?? 0;
              }
              if (f['police_months'] != null) body['police_months'] = int.tryParse(f['police_months']!) ?? 24;
              await _run('PUT', '/api/drivers/settings', body);
            }),
        GlassButton(
            label: 'Gaadi',
            icon: Icons.local_shipping_rounded,
            onTap: () async {
              final f = await _form(context, 'Gaadi (licence class / fuel check ke liye)', const [
                ('number', 'Number'),
                ('gvw_kg', 'Gross weight kg (RC par)'),
                ('kind', 'truck / tempo / car / bus'),
                ('kmpl', 'Aam km / litre (pata ho to)'),
              ]);
              if (f == null || (f['number'] ?? '').isEmpty) return;
              await _run('PUT', '/api/drivers/vehicles', {
                'number': f['number'],
                if (f['gvw_kg'] != null) 'gvw_kg': double.tryParse(f['gvw_kg']!),
                if (f['kind'] != null) 'kind': f['kind'],
                if (f['kmpl'] != null) 'kmpl': double.tryParse(f['kmpl']!),
              });
            }),
      ]),
      const SizedBox(height: 8),
      for (final n in ((st['notes'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 12.5)),
      for (final n in ((st['never'] as List?) ?? const [])) Text('• $n', style: const TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 6),
      for (final src in ((_d?['sources'] as List?) ?? const []))
        if (src is List && src.isNotEmpty) Text('${src[0]} (${src.length > 2 ? src[2] : ''})', style: const TextStyle(fontSize: 11, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Driver Sahayak')),
        floatingActionButton: _tab <= 1
            ? FloatingActionButton.extended(onPressed: _busy ? null : _newDuty, icon: const Icon(Icons.event_note_rounded), label: const Text('Duty lagao'))
            : null,
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: () async {
              await _load();
              if (_tab == 4) await _loadAtt(_s(_att?['month']));
            },
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 90), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Duty'), (2, 'Trip sheet'), (3, 'Driver'), (4, 'Hazri'), (5, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _roster(), _trips(), _drivers(), _hazri(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Duty kaanoon ki seema (OSH Code: 8 ghante / din, 48 / hafta) aur aapke niyam se check hoti hai. Driver ko message aap bhejti hain ya aapke tap se jaata hai. Paise / advance Hoola nahi deta. Licence number Locker mein band.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// One draft message to a driver with HER send options. Only these taps send it.
class DriversMessageTile extends StatefulWidget {
  const DriversMessageTile({super.key, required this.app, required this.m, this.onDone});
  final Santosh app;
  final Map<String, dynamic> m;
  final VoidCallback? onDone;
  @override
  State<DriversMessageTile> createState() => _DriversMessageTileState();
}

class _DriversMessageTileState extends State<DriversMessageTile> {
  bool _busy = false;
  late String _status = _s(widget.m['status']);
  bool _opened = false;

  Future<void> _send(String via) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/drivers/messages/${_s(widget.m['id'])}/send', {'via': via, 'hash': _s(widget.m['hash'])});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null) _status = _s(r['status']);
      });
    }
    widget.onDone?.call();
  }

  Future<void> _open(String url) async {
    if (url.isEmpty) return;
    final r = await Native.openExternal(url: url);
    if (mounted) setState(() => _opened = true);
    if (r.isNotEmpty && r != 'ok' && mounted) _snack(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.m;
    final draft = _status == 'draft';
    return Glass(
      padding: const EdgeInsets.all(12),
      border: draft ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.drive_eta_rounded, color: C.accent, size: 18),
          const SizedBox(width: 6),
          Expanded(child: Text('${_s(m['number'])} · ${_s(m['driver'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(draft ? 'draft' : _status),
        ]),
        const SizedBox(height: 4),
        Text(_s(m['text']), style: const TextStyle(fontSize: 12.5, height: 1.3)),
        if (m['no_messages'] == true) const Text('Is driver ne message mana kiya hai: apne phone se baat kijiye.', style: TextStyle(fontSize: 12, color: C.warn)),
        if (draft)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Wrap(spacing: 6, runSpacing: 6, children: [
              if (_s(m['wa']).isNotEmpty) ActionChip(label: const Text('WhatsApp kholo'), onPressed: () => _open(_s(m['wa']))),
              if (_s(m['sms']).isNotEmpty) ActionChip(label: const Text('SMS'), onPressed: () => _open(_s(m['sms']))),
              if (_opened || _s(m['wa']).isEmpty) ActionChip(label: const Text('Maine bhej diya'), onPressed: _busy ? null : () => _send('self')),
              if (m['can_business'] == true && m['no_messages'] != true)
                ActionChip(label: const Text('Business WhatsApp se bhejo'), onPressed: _busy ? null : () => _send('business')),
              if (m['can_hoola'] == true && m['no_messages'] != true)
                ActionChip(label: const Text('Hoola Network se bhejo'), onPressed: _busy ? null : () => _send('hoola')),
              ActionChip(
                  label: const Text('Hatao'),
                  onPressed: _busy
                      ? null
                      : () async {
                          await _call(context, widget.app, 'POST', '/api/drivers/messages/${_s(m['id'])}/cancel');
                          if (mounted) setState(() => _status = 'cancelled');
                          widget.onDone?.call();
                        }),
            ]),
          )
        else if (_s(m['result']).isNotEmpty)
          Text(_s(m['result']), style: const TextStyle(fontSize: 12, color: C.ok)),
      ]),
    );
  }
}

/// `drivers_plan`: tomorrow's duty drafts (or trip-sheet reminders), one tile per driver; she sends each.
class DriversPlanCard extends StatelessWidget {
  const DriversPlanCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.event_note_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text(_s(data['title']).isNotEmpty ? _s(data['title']) : 'Driver duty ${_s(data['day'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
          for (final m in _list(data['messages'])) Padding(padding: const EdgeInsets.only(top: 8), child: DriversMessageTile(app: app, m: m)),
          TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DriversScreen(app: app))),
              child: const Text('Driver Sahayak kholo')),
        ]),
      );
}

/// `drivers_message`: one draft to one driver.
class DriversMessageCard extends StatelessWidget {
  const DriversMessageCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => DriversMessageTile(app: app, m: data);
}

/// `drivers_alert`: licence / medical / badge / police / hazardous dates ending (each with a draft for the driver).
class DriversAlertCard extends StatelessWidget {
  const DriversAlertCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Glass(
        border: C.warn,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.badge_rounded, color: C.warn),
            SizedBox(width: 8),
            Expanded(child: Text('Driver ke kaagaz', style: TextStyle(fontWeight: FontWeight.w800))),
          ]),
          for (final i in _list(data['items'])) ...[
            Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(_s(i['say']), style: TextStyle(fontSize: 12.5, color: (i['days_left'] is num && (i['days_left'] as num) < 0) ? C.bad : C.warn))),
            if (i['message'] is Map) Padding(padding: const EdgeInsets.only(top: 4), child: DriversMessageTile(app: app, m: _m(i['message']))),
          ],
        ]),
      );
}

/// `drivers_day`: the morning note.
class DriversDayCard extends StatelessWidget {
  const DriversDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DriversScreen(app: app))),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Row(children: [
              Icon(Icons.local_shipping_rounded, color: C.accent),
              SizedBox(width: 8),
              Expanded(child: Text('Aaj ke driver', style: TextStyle(fontWeight: FontWeight.w800))),
            ]),
            Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
            for (final x in _list(data['duties']).take(8))
              Text('• ${_s(x['driver'])} ${_s(x['start'])}-${_s(x['end'])} ${_s(x['vehicle'])} ${_s(x['route'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
            for (final x in _list(data['missing_sheets']).take(5))
              Text('• Trip sheet baaki: ${_s(x['driver'])} ${_s(x['day'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
          ]),
        ),
      );
}
