/// Profile > Call Centre Sahayak (v0.128): Hoola answers the business phone line, only from HER approved script.
/// Aaj (line on / off, call-backs to make, what callers asked that the script didn't know) · Script (draft, try a question,
/// send for her Haan; the line speaks only the version she approved) · Calls (call notes, masked transcript) ·
/// Niyam (provider, number, hours, hold queue, who takes over, recording, provider keys typed only here).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../native.dart';
import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

const _outcomeSay = {
  'answered': 'AI ne jawab diya',
  'appointment': 'Appointment book',
  'message': 'Message liya',
  'complaint': 'Shikayat darj',
  'transferred': 'Insaan ko di',
  'callback': 'Call-back',
  'busy': 'Line busy',
  'closed': 'Band samay',
  'dropped': 'Kat gayi',
  'failed': 'AI nahi chala',
};

Color _outcomeColor(String o) => switch (o) {
      'transferred' || 'busy' || 'closed' || 'dropped' => C.warn,
      'failed' => C.bad,
      _ => C.ok,
    };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {Map<String, String> initial = const {}, Set<String> secret = const {}, String ok = 'Aage'}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final res = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(
              controller: c[k],
              obscureText: secret.contains(k),
              maxLines: secret.contains(k) ? 1 : null,
              decoration: InputDecoration(labelText: label),
            ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: Text(ok)),
      ],
    ),
  );
  final out = res == true ? {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()} : null;
  for (final x in c.values) {
    x.dispose();
  }
  return out;
}

Future<void> _dial(BuildContext context, String number) async {
  if (number.isEmpty) return;
  final r = await Native.openExternal(url: 'tel:$number');
  if (r.isNotEmpty && r != 'ok' && context.mounted) _snack(context, r);
}

class CallCentreScreen extends StatefulWidget {
  const CallCentreScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CallCentreScreen> createState() => _CallCentreScreenState();
}

class _CallCentreScreenState extends State<CallCentreScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  final _tryCtl = TextEditingController();
  Map<String, dynamic>? _tryRes;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _tryCtl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.call('GET', '/api/callcentre');
      if (mounted) setState(() => _d = _map(d));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<Map<String, dynamic>?> _run(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call(method, path, body: body));
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Map<String, dynamic> get _st => _map(_d?['settings']);

  // ---------------------------------------------------------------- Aaj
  Widget _today() {
    final d = _d ?? const {};
    final rep = _map(d['report']);
    final on = _st['line_on'] == true;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        border: on ? C.ok : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(on ? Icons.support_agent_rounded : Icons.phone_disabled_rounded, color: on ? C.ok : C.muted),
            const SizedBox(width: 10),
            Expanded(
                child: Text(on ? 'AI line chalu' : 'AI line band',
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
            Switch(
                value: on,
                onChanged: _busy ? null : (v) => _run('POST', '/api/callcentre/line', {'on': v})),
          ]),
          Text(_s(rep['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
          if ((d['live'] ?? 0) > 0) Text('Abhi ${d['live']} call chal rahi hai', style: const TextStyle(color: C.teal, fontSize: 12.5)),
          if (_s(_st['number']).isNotEmpty)
            Text('Number: ${_s(_st['number'])} · ${_s(_st['hours_text'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      ),
      for (final p in (d['problems'] as List? ?? const []))
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(children: [
            const Icon(Icons.info_outline_rounded, size: 16, color: C.warn),
            const SizedBox(width: 6),
            Expanded(child: Text('$p', style: const TextStyle(fontSize: 12.5, color: C.warn))),
          ]),
        ),
      const SizedBox(height: 12),
      Text('Call-back / message', style: display(15)),
      if (_list(d['messages']).isEmpty) const Text('Koi baaki nahi.', style: TextStyle(color: C.muted, fontSize: 12.5)),
      for (final m in _list(d['messages']))
        Padding(padding: const EdgeInsets.only(top: 8), child: CallCentreMessageCard(app: widget.app, data: m, onDone: _load)),
      const SizedBox(height: 12),
      if (_list(rep['unanswered']).isNotEmpty) ...[
        Text('Callers ne poocha, script mein nahi tha', style: display(15)),
        for (final q in _list(rep['unanswered']))
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Glass(
              padding: const EdgeInsets.all(10),
              child: Row(children: [
                Expanded(child: Text('${_s(q['q'])} (${q['times']}x)', style: const TextStyle(fontSize: 13))),
                TextButton(onPressed: _busy ? null : () => _addFaq(_s(q['q'])), child: const Text('Jawab jodo')),
              ]),
            ),
          ),
      ],
    ]);
  }

  Future<void> _addFaq([String q = '']) async {
    final f = await _form(context, 'Naya sawal-jawab', const [('q', 'Sawal (jaise caller poochte hain)'), ('a', 'Aapka jawab'), ('words', 'Aur shabd (comma se)')],
        initial: {'q': q});
    if (f == null || (f['q'] ?? '').isEmpty) return;
    await _run('PUT', '/api/callcentre/script', {
      'faq_add': [
        {'q': f['q'], 'a': f['a'] ?? '[blank]', 'words': (f['words'] ?? '').split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList()}
      ]
    });
  }

  // ---------------------------------------------------------------- Script
  Widget _faqTile(Map<String, dynamic> f, {bool editable = false}) {
    final a = _s(f['a']);
    final blank = a.isEmpty || a.contains('[blank]');
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Glass(
        padding: const EdgeInsets.all(10),
        border: blank ? C.warn : null,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(f['q']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
              Text(blank ? 'Jawab khaali: bhariye' : a, style: TextStyle(fontSize: 12.5, color: blank ? C.warn : C.muted)),
            ]),
          ),
          if (editable) ...[
            IconButton(
                icon: const Icon(Icons.edit_rounded, size: 18),
                onPressed: _busy
                    ? null
                    : () async {
                        final g = await _form(context, 'Jawab badlo', const [('a', 'Jawab')], initial: {'a': blank ? '' : a});
                        if (g != null && (g['a'] ?? '').isNotEmpty) {
                          await _run('PUT', '/api/callcentre/script', {
                            'faq_add': [
                              {'q': f['q'], 'a': g['a'], 'words': f['words'] ?? const []}
                            ]
                          });
                        }
                      }),
            IconButton(
                icon: const Icon(Icons.delete_outline_rounded, size: 18),
                onPressed: _busy ? null : () => _run('PUT', '/api/callcentre/script', {'faq_remove': [f['q']]})),
          ],
        ]),
      ),
    );
  }

  Widget _script() {
    final run = _d?['script'] == null ? null : _map(_d!['script']);
    final dr = _d?['draft'] == null ? null : _map(_d!['draft']);
    final rc = _map(run?['content']);
    final dc = _map(dr?['content']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(
            label: 'Business ke baare mein batao',
            icon: Icons.record_voice_over_rounded,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Aapke shabdon mein',
                        const [('words', 'Kya karte ho, timing, daam (jo bolna hai), aam sawal + jawab, appointment de sakte hain?')]);
                    if (f != null && (f['words'] ?? '').isNotEmpty) await _run('POST', '/api/callcentre/script', {'words': f['words']});
                  }),
        GlassButton(label: 'Sawal jodo', icon: Icons.add_comment_rounded, onTap: _busy ? null : () => _addFaq()),
      ]),
      const SizedBox(height: 10),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aazmao: caller yeh poochhe to?', style: TextStyle(fontWeight: FontWeight.w700)),
          Row(children: [
            Expanded(child: TextField(controller: _tryCtl, decoration: const InputDecoration(hintText: 'jaise: fees kitni hai'))),
            IconButton(
                icon: const Icon(Icons.search_rounded),
                onPressed: () async {
                  try {
                    final r = _map(await widget.app.api!.call('POST', '/api/callcentre/try', body: {'question': _tryCtl.text, 'draft': true}));
                    if (mounted) setState(() => _tryRes = r);
                  } catch (e) {
                    if (mounted) _snack(context, '$e');
                  }
                }),
          ]),
          if (_tryRes != null)
            Text(_tryRes!['found'] == true ? 'Line bolegi: ${_s(_tryRes!['a'])}' : _s(_tryRes!['say']),
                style: TextStyle(fontSize: 12.5, color: _tryRes!['found'] == true ? C.ok : C.warn)),
        ]),
      ),
      const SizedBox(height: 12),
      if (dr != null) ...[
        Row(children: [
          Expanded(child: Text('Draft v${dr['version']}', style: display(15))),
          Pill(_s(dr['status'])),
        ]),
        if (_s(dc['business']).isNotEmpty) Text('${_s(dc['business'])} · ${_s(dc['about'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        for (final f in _list(dc['faqs'])) _faqTile(f, editable: true),
        const SizedBox(height: 8),
        if (_s(dr['status']) == 'draft')
          GradientButton(
              label: 'Haan ke liye card bhejo',
              icon: Icons.fact_check_rounded,
              onTap: _busy ? null : () => _run('POST', '/api/callcentre/script/submit')),
        if (_s(dr['status']) == 'waiting')
          CallCentreScriptCard(app: widget.app, data: {
            'script_id': dr['id'],
            'version': dr['version'],
            'hash': dr['hash'],
            'status': 'waiting',
            'business': dc['business'],
            'faqs': dc['faqs'],
            'can': dc['can'],
          }, onDone: _load),
        const SizedBox(height: 14),
      ],
      Text(run == null ? 'Line par koi script nahi' : 'Line par chal raha: v${run['version']}', style: display(15)),
      if (run != null) ...[
        Text(
            'Kar sakti hai: ${[
              'sawal-jawab',
              'message',
              if (_map(rc['can'])['appointments'] == true) 'appointment',
              if (_map(rc['can'])['ticket_status'] == true) 'ticket status',
              if (_map(rc['can'])['complaints'] == true) 'shikayat',
            ].join(', ')}',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
        for (final f in _list(rc['faqs'])) _faqTile(f),
      ],
    ]);
  }

  // ---------------------------------------------------------------- Calls
  Widget _calls() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (_list(_d?['calls']).isEmpty) const Text('Abhi koi call nahi.', style: TextStyle(color: C.muted)),
        for (final c in _list(_d?['calls']))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CallCentreCallPage(app: widget.app, id: _s(c['id'])))),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(
                        child: Text('${_s(c['caller_masked'])}${_s(c['caller_name']).isNotEmpty ? ' · ${_s(c['caller_name'])}' : ''}',
                            style: const TextStyle(fontWeight: FontWeight.w800))),
                    Pill(_outcomeSay[_s(c['outcome'])] ?? _s(c['outcome']), fg: _outcomeColor(_s(c['outcome']))),
                  ]),
                  if (_s(c['summary']).isNotEmpty) Text(_s(c['summary']), style: const TextStyle(fontSize: 12.5)),
                  Text('${(c['seconds'] ?? 0)} sec · ${_s(c['lang'])}${_s(c['handover_say']).isNotEmpty ? ' · ${_s(c['handover_say'])}' : ''}',
                      style: const TextStyle(color: C.muted, fontSize: 12)),
                ]),
              ),
            ),
          ),
      ]);

  // ---------------------------------------------------------------- Niyam
  Future<void> _keys() async {
    final p = _s(_st['provider']);
    final fields = switch (p) {
      'plivo' => const [('auth_id', 'Plivo Auth ID'), ('auth_token', 'Plivo Auth Token')],
      'exotel' => const [('api_key', 'Exotel API key'), ('api_token', 'Exotel API token'), ('sid', 'Account SID'), ('subdomain', 'Subdomain (api.in.exotel.com)')],
      _ => const [('secret', 'Test line secret')],
    };
    final f = await _form(context, 'Provider ki keys (sirf yahan)', fields, secret: {'auth_token', 'api_token', 'secret'}, ok: 'Save');
    if (f == null) return;
    await _run('PUT', '/api/callcentre/keys', {'provider': p, ...f});
  }

  Future<void> _settings(Map<String, dynamic> body) => _run('PUT', '/api/callcentre/settings', body);

  Widget _rules() {
    final st = _st;
    final h = _map(st['hours']);
    final days = ((h['days'] as List?) ?? const []).map((e) => e as int).toSet();
    final urls = _map(st['urls']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Provider', style: display(15)),
      Wrap(spacing: 6, children: [
        for (final p in const ['plivo', 'exotel', 'fake'])
          ChoiceChip(
              label: Text(_s(_map(_map(st['providers'])[p])['name']).isEmpty ? p : _s(_map(_map(st['providers'])[p])['name'])),
              selected: st['provider'] == p,
              onSelected: _busy ? null : (_) => _settings({'provider': p})),
      ]),
      Text(_s(_map(_map(st['providers'])[st['provider']])['why']), style: const TextStyle(color: C.muted, fontSize: 12)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 8, children: [
        GlassButton(
            label: st['creds_set'] == true ? 'Keys badlo' : 'Keys daalo',
            icon: Icons.key_rounded,
            onTap: _busy ? null : _keys),
        GlassButton(
            label: _s(st['number']).isEmpty ? 'Number daalo' : _s(st['number']),
            icon: Icons.dialpad_rounded,
            onTap: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Provider ka number', const [('number', 'Number (jaise 020 4567 8901)')]);
                    if (f != null) await _settings({'number': f['number'] ?? ''});
                  }),
      ]),
      for (final (i, step) in ((st['setup'] as List?) ?? const []).indexed)
        Text('${i + 1}. $step', style: const TextStyle(fontSize: 12.5)),
      for (final e in urls.entries)
        Row(children: [
          Expanded(child: Text('${e.key}: ${e.value}', style: const TextStyle(fontSize: 11.5, color: C.muted))),
          IconButton(
              icon: const Icon(Icons.copy_rounded, size: 16),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: '${e.value}'));
                _snack(context, 'Copy ho gaya');
              }),
        ]),
      const SizedBox(height: 12),
      Text('Samay', style: display(15)),
      Row(children: [
        Expanded(child: Text('Khula: ${_s(st['hours_text'])}', style: const TextStyle(fontSize: 13))),
        TextButton(
            onPressed: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Khulne ka samay', const [('open', 'Khulta (10:00)'), ('close', 'Band (19:00)')],
                        initial: {'open': _s(h['open']), 'close': _s(h['close'])});
                    if (f != null) await _settings({'hours': {'open': f['open'] ?? '10:00', 'close': f['close'] ?? '19:00', 'days': days.toList()}});
                  },
            child: const Text('Badlo')),
      ]),
      Wrap(spacing: 4, children: [
        for (final (i, n) in const ['Som', 'Mangal', 'Budh', 'Guru', 'Shukra', 'Shani', 'Ravi'].indexed)
          FilterChip(
              label: Text(n),
              selected: days.contains(i),
              onSelected: _busy
                  ? null
                  : (v) {
                      final nd = {...days};
                      v ? nd.add(i) : nd.remove(i);
                      _settings({'hours': {'open': _s(h['open']), 'close': _s(h['close']), 'days': (nd.toList()..sort())}});
                    }),
      ]),
      const SizedBox(height: 6),
      Wrap(spacing: 6, children: [
        const Text('Band samay mein: ', style: TextStyle(fontSize: 13)),
        ChoiceChip(label: const Text('AI message le'), selected: st['after_hours'] == 'message', onSelected: (_) => _settings({'after_hours': 'message'})),
        ChoiceChip(label: const Text('Sirf "band hai"'), selected: st['after_hours'] == 'closed', onSelected: (_) => _settings({'after_hours': 'closed'})),
      ]),
      const SizedBox(height: 12),
      Text('Bheed', style: display(15)),
      Row(children: [
        Expanded(child: Text('Ek saath AI calls: ${st['max_concurrent']} · hold: ${st['queue_max']} baar', style: const TextStyle(fontSize: 13))),
        TextButton(
            onPressed: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Bheed', const [('max_concurrent', 'Ek saath kitni calls (1-10)'), ('queue_max', 'Hold kitni baar (15 sec each)')],
                        initial: {'max_concurrent': _s(st['max_concurrent']), 'queue_max': _s(st['queue_max'])});
                    if (f != null) {
                      await _settings({
                        if (f['max_concurrent'] != null) 'max_concurrent': int.tryParse(f['max_concurrent']!) ?? 2,
                        if (f['queue_max'] != null) 'queue_max': int.tryParse(f['queue_max']!) ?? 3,
                      });
                    }
                  },
            child: const Text('Badlo')),
      ]),
      Wrap(spacing: 6, children: [
        const Text('Sab busy ho to: ', style: TextStyle(fontSize: 13)),
        ChoiceChip(label: const Text('Call-back'), selected: st['overflow'] == 'callback', onSelected: (_) => _settings({'overflow': 'callback'})),
        ChoiceChip(label: const Text('Insaan ko do'), selected: st['overflow'] == 'transfer', onSelected: (_) => _settings({'overflow': 'transfer'})),
      ]),
      const SizedBox(height: 12),
      Text('Insaan kaun lega', style: display(15)),
      for (final p in _list(st['handover']))
        Row(children: [
          Expanded(child: Text('${_s(p['name'])} · ${_s(p['phone'])}${_s(p['role']).isNotEmpty ? ' (${_s(p['role'])})' : ''}', style: const TextStyle(fontSize: 13))),
          IconButton(
              icon: const Icon(Icons.remove_circle_outline_rounded, size: 18),
              onPressed: _busy
                  ? null
                  : () => _settings({'handover': _list(st['handover']).where((x) => x['phone'] != p['phone']).toList()})),
        ]),
      TextButton.icon(
          icon: const Icon(Icons.person_add_alt_1_rounded),
          label: const Text('Jodo'),
          onPressed: _busy
              ? null
              : () async {
                  final f = await _form(context, 'Call kisko jaaye', const [('name', 'Naam'), ('phone', 'Mobile'), ('role', 'Kaam (owner / reception)')]);
                  if (f != null && (f['phone'] ?? '').isNotEmpty) await _settings({'handover': [..._list(st['handover']), f]});
                }),
      SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Insaan ko call transfer karo (khule samay)'),
          value: st['transfer_on'] == true,
          onChanged: _busy ? null : (v) => _settings({'transfer_on': v})),
      SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Call record karo (provider par)'),
          subtitle: const Text('Shuru mein caller ko bataya jaata hai. Hoola khud awaaz nahi rakhta.'),
          value: st['record'] == true,
          onChanged: _busy ? null : (v) => _settings({'record': v})),
      Row(children: [
        Expanded(
            child: Text('Provider ka rate: ${(st['rate_inr_per_min'] ?? 0) == 0 ? 'nahi bataya' : '₹${st['rate_inr_per_min']}/min'} · max ${st['max_minutes']} min',
                style: const TextStyle(fontSize: 13))),
        TextButton(
            onPressed: _busy
                ? null
                : () async {
                    final f = await _form(context, 'Kharcha', const [('rate', '₹ per minute (bill se)'), ('max', 'Ek call max minute')],
                        initial: {'rate': _s(st['rate_inr_per_min']), 'max': _s(st['max_minutes'])});
                    if (f != null) {
                      await _settings({
                        if (f['rate'] != null) 'rate_inr_per_min': double.tryParse(f['rate']!) ?? 0,
                        if (f['max'] != null) 'max_minutes': int.tryParse(f['max']!) ?? 10,
                      });
                    }
                  },
            child: const Text('Badlo')),
      ]),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Call Centre Sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Script'), (2, 'Calls'), (3, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _script(), _calls(), _rules()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Har call ki shuruaat mein bataya jaata hai ki yeh AI sahayak hai. Line sirf aapki Haan wali script se bolti hai; '
                  'baaki sab message ya insaan ko. OTP / PIN / card kabhi nahi liya jaata. Paisa line par kabhi nahi.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

/// One call: summary, outcome, masked transcript, flags.
class CallCentreCallPage extends StatefulWidget {
  const CallCentreCallPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CallCentreCallPage> createState() => _CallCentreCallPageState();
}

class _CallCentreCallPageState extends State<CallCentreCallPage> {
  Map<String, dynamic>? _c;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await widget.app.api!.call('GET', '/api/callcentre/calls/${widget.id}');
      if (mounted) setState(() => _c = _map(c));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(c == null ? 'Call' : _s(c['caller_masked']))),
      body: Aurora(
        child: c == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                Glass(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text(_s(c['caller_name']).isEmpty ? 'Caller' : _s(c['caller_name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                      Pill(_outcomeSay[_s(c['outcome'])] ?? _s(c['outcome']), fg: _outcomeColor(_s(c['outcome']))),
                    ]),
                    Text(_s(c['summary']), style: const TextStyle(fontSize: 13)),
                    Text('${c['seconds']} sec · ${_s(c['lang'])} · script v${c['script_version']}${c['disclosed'] == true ? ' · AI bataya' : ''}',
                        style: const TextStyle(color: C.muted, fontSize: 12)),
                    if (_s(c['handover_say']).isNotEmpty) Text('Insaan ko kyun: ${_s(c['handover_say'])}', style: const TextStyle(fontSize: 12.5)),
                  ]),
                ),
                const SizedBox(height: 8),
                if (_s(c['caller']).isNotEmpty)
                  GlassButton(label: 'Wapas call karo', icon: Icons.call_rounded, onTap: () => _dial(context, _s(c['caller']))),
                for (final f in _list(c['flags']))
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text('⚠ ${_s(f['kind'])}: ${_s(f['text'])}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
                  ),
                const SizedBox(height: 10),
                Text('Baatcheet (number chhupe hue)', style: display(15)),
                for (final t in (c['transcript'] as List? ?? const []))
                  if (t is List && t.length >= 2)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Align(
                        alignment: t[0] == 'caller' ? Alignment.centerLeft : Alignment.centerRight,
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 300),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(color: t[0] == 'caller' ? C.panel : const Color(0x337C5CFF), borderRadius: BorderRadius.circular(14)),
                          child: Text('${t[1]}', style: const TextStyle(fontSize: 13)),
                        ),
                      ),
                    ),
              ]),
      ),
    );
  }
}

/// Chat card `callcentre_script`: the script version waiting for HER Haan (the only way it reaches the phone line).
class CallCentreScriptCard extends StatefulWidget {
  const CallCentreScriptCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CallCentreScriptCard> createState() => _CallCentreScriptCardState();
}

class _CallCentreScriptCardState extends State<CallCentreScriptCard> {
  bool _busy = false;
  bool _all = false;
  late String _status = _s(widget.data['status']).isEmpty ? 'waiting' : _s(widget.data['status']);

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/callcentre/scripts/${_s(widget.data['script_id'])}/decide',
          body: {'yes': yes, 'hash': _s(widget.data['hash'])}));
      if (mounted) {
        setState(() => _status = _s(r['status']));
        _snack(context, _s(r['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.data;
    final faqs = _list(v['faqs']);
    final can = _map(v['can']);
    final shown = _all ? faqs : faqs.take(5).toList();
    return Glass(
      border: _status == 'waiting' ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.support_agent_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Call centre script v${v['version']}${_s(v['business']).isNotEmpty ? ' · ${_s(v['business'])}' : ''}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status),
        ]),
        if (faqs.isEmpty && _s(v['say']).isNotEmpty) Text(_s(v['say']), style: const TextStyle(fontSize: 12.5)),
        if (faqs.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('Line par sirf yahi bolega (${faqs.length} sawal):', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          for (final f in shown)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('• ${_s(f['q'])} → ${_s(f['a'])}', style: const TextStyle(fontSize: 12.5)),
            ),
          if (faqs.length > 5)
            TextButton(onPressed: () => setState(() => _all = !_all), child: Text(_all ? 'Kam dikhao' : 'Saare dekho')),
          Text(
              'Kar sakti hai: sawal-jawab, message${can['appointments'] == true ? ', appointment' : ''}${can['ticket_status'] == true ? ', ticket status' : ''}${can['complaints'] == true ? ', shikayat' : ''}',
              style: const TextStyle(fontSize: 12, color: C.muted)),
        ],
        for (final ch in (v['changes'] as List? ?? const []).take(6)) Text('· $ch', style: const TextStyle(fontSize: 12, color: C.teal)),
        if (_status == 'waiting') ...[
          const SizedBox(height: 8),
          GradientButton(label: 'Haan, yahi script chalao', icon: Icons.check_rounded, onTap: _busy ? null : () => _decide(true)),
          const SizedBox(height: 6),
          GlassButton(label: 'Mana', icon: Icons.close_rounded, onTap: _busy ? null : () => _decide(false)),
        ],
      ]),
    );
  }
}

/// Chat card `callcentre_call`: what happened on one call (also shown inside her own Hoola call).
class CallCentreCallCard extends StatelessWidget {
  const CallCentreCallCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final v = data;
    final o = _s(v['outcome']);
    final flags = _list(v['flags']);
    final un = (v['unanswered'] as List? ?? const []);
    return Press(
      onTap: _s(v['id']).isEmpty
          ? null
          : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CallCentreCallPage(app: app, id: _s(v['id'])))),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.phone_in_talk_rounded, color: C.accent),
            const SizedBox(width: 8),
            Expanded(
                child: Text('Call: ${_s(v['caller_masked'])}${_s(v['caller_name']).isNotEmpty ? ' · ${_s(v['caller_name'])}' : ''}',
                    style: const TextStyle(fontWeight: FontWeight.w800))),
            Pill(_outcomeSay[o] ?? o, fg: _outcomeColor(o)),
          ]),
          if (_s(v['summary']).isNotEmpty) Text(_s(v['summary']), style: const TextStyle(fontSize: 13)),
          if (_s(v['handover_say']).isNotEmpty) Text('Insaan ko: ${_s(v['handover_say'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
          if (un.isNotEmpty) Text('Script mein nahi tha: ${un.join('; ')}', style: const TextStyle(fontSize: 12.5, color: C.warn)),
          if (flags.isNotEmpty) Text('⚠ ${flags.length} dhyaan dene wali baat', style: const TextStyle(fontSize: 12, color: C.warn)),
          Text('${v['seconds'] ?? 0} sec${v['disclosed'] == true ? ' · AI bataya' : ''}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
    );
  }
}

/// Chat card `callcentre_message`: a call-back / message for her (anything the script couldn't do).
class CallCentreMessageCard extends StatefulWidget {
  const CallCentreMessageCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CallCentreMessageCard> createState() => _CallCentreMessageCardState();
}

class _CallCentreMessageCardState extends State<CallCentreMessageCard> {
  bool _done = false;
  bool _busy = false;

  Future<void> _mark() async {
    setState(() => _busy = true);
    try {
      await widget.app.api!.call('POST', '/api/callcentre/messages/${_s(widget.data['id'])}/done', body: {'note': ''});
      if (mounted) setState(() => _done = true);
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.data;
    final done = _done || m['status'] == 'done';
    return Glass(
      border: m['reminder'] == true && !done ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(m['kind'] == 'callback' ? Icons.phone_callback_rounded : Icons.message_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(m['name']).isNotEmpty ? '${_s(m['name'])} · ' : ''}${_s(m['caller_masked'])}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          if (done) const Pill('ho gaya', fg: C.ok),
        ]),
        Text(_s(m['text']), style: const TextStyle(fontSize: 13)),
        if (_s(m['callback_at']).isNotEmpty) Text('Call-back: ${_s(m['callback_at'])}', style: const TextStyle(fontSize: 12.5, color: C.teal)),
        if (!done) ...[
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GlassButton(label: 'Call karo', icon: Icons.call_rounded, onTap: () => _dial(context, _s(m['caller'])))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Ho gaya', icon: Icons.check_rounded, onTap: _busy ? null : _mark)),
          ]),
        ],
      ]),
    );
  }
}
