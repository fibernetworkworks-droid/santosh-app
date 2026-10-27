/// Profile > Feedback sahayak (Seva suite): Hoola as a feedback analyst.
/// Aaj (pehle kya theek karein, NPS / CSAT, alerts) · Themes (count, trend, quotes, "theek kiya") · Reviews (filters,
/// jawab ka draft -> HER tap makes it public) · Survey (signed link for ALL customers) · Sources & Niyam (sheet import,
/// Google reviews, Form, WhatsApp inbox, call notes, her numbers and reply rules). Reviews are never hidden or removed.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'attach.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).whereType<Map>().map((e) => Map<String, dynamic>.from(e)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) {
  if (t.isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

String _stars(dynamic v) {
  final n = (v is num) ? v.round() : int.tryParse(_s(v)) ?? 0;
  return n <= 0 ? '' : '★' * n.clamp(1, 5);
}

Color _labelColor(String l) => l == 'pos' ? C.ok : (l == 'neg' ? C.bad : (l == 'mixed' ? C.warn : C.muted));

Future<void> _open(BuildContext context, String url) async {
  if (url.isEmpty) return;
  try {
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  } catch (_) {
    if (context.mounted) _snack(context, 'Link nahi khula');
  }
}

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {Map<String, String> initial = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController(text: initial[k] ?? '')};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final (k, label) in fields)
            TextField(controller: c[k], decoration: InputDecoration(labelText: label), maxLines: k == 'text' ? 5 : 1),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage')),
      ],
    ),
  );
  if (ok != true) return null;
  return {for (final e in c.entries) if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim()};
}

class FeedbackScreen extends StatefulWidget {
  const FeedbackScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<FeedbackScreen> createState() => _FeedbackScreenState();
}

class _FeedbackScreenState extends State<FeedbackScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _items = const [];
  int _tab = 0;
  int _days = 30;
  bool _busy = false;
  String _filter = '';
  String _source = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await widget.app.api!.call('GET', '/api/feedback', query: {'days': '$_days'});
      final it = await widget.app.api!.call('GET', '/api/feedback/items', query: {
        'limit': '80',
        if (_filter.isNotEmpty) 'label': _filter,
        if (_source.isNotEmpty) 'source': _source,
      });
      if (mounted) {
        setState(() {
          _d = _map(d);
          _items = _list(_map(it)['items']);
        });
      }
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<dynamic> _run(Future<dynamic> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted) _snack(context, _s(_map(r)['say']));
      await _load();
      return r;
    } catch (e) {
      if (mounted) _snack(context, '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _paste() async {
    final f = await _form(context, 'Reviews chipkaiye', const [
      ('text', 'Ek ya kai review (har review naye "-" se; "4*" bhi likh sakti hain)'),
      ('source', 'Kahan ka? google / zomato / swiggy / amazon / flipkart / text'),
    ]);
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run(() => widget.app.api!.call('POST', '/api/feedback/text', body: {'text': f['text'], 'source': f['source'] ?? 'text'}));
  }

  Future<void> _import() async {
    final files = await pickAttachments(context, max: 1, showSheet: false);
    if (files.isEmpty) return;
    final f = files.first;
    await _run(() => widget.app.api!.uploadFile('/api/feedback/import', f.name, f.bytes, timeout: const Duration(seconds: 120), tries: 2));
  }

  Future<void> _sync(String what) async {
    Map<String, dynamic> body = {'what': what};
    if (what == 'forms') {
      final f = await _form(context, 'Google Form', const [('form', 'Form ka naam ya edit link')]);
      if (f == null || (f['form'] ?? '').isEmpty) return;
      body['form'] = f['form'];
    }
    await _run(() => widget.app.api!.call('POST', '/api/feedback/sync', body: body, timeout: const Duration(seconds: 120)));
  }

  Future<void> _googleLink() async {
    try {
      final r = _map(await widget.app.api!.call('GET', '/api/feedback/google/link'));
      if (mounted) await _open(context, _s(r['url']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _settings() async {
    final st = _map(_d?['settings']);
    final f = await _form(context, 'Niyam', const [
      ('business', 'Business ka naam'),
      ('phone', 'Business phone (jawab mein dikhega)'),
      ('sign_off', 'Jawab ke neeche ("- Team Annapurna")'),
      ('language', 'Bhasha: hinglish / hi / mr / en'),
      ('avg_order_value', 'Ausat order value ₹ (rupaye ka andaaza)'),
      ('orders_per_year', 'Ek graahak saal mein kitni baar aata hai'),
      ('review_link', 'Google review link (sabko ek jaisa dikhega)'),
      ('period_days', 'Kitne din ka hisaab (30)'),
      ('reply_rule', 'Jawab ka naya niyam (jaise "har jawab mein maafi pehle")'),
    ], initial: {
      for (final k in ['business', 'phone', 'sign_off', 'language', 'review_link'])
        if (_s(st[k]).isNotEmpty) k: _s(st[k]),
      if ((st['avg_order_value'] ?? 0) != 0) 'avg_order_value': _s(st['avg_order_value']),
      if ((st['orders_per_year'] ?? 0) != 0) 'orders_per_year': _s(st['orders_per_year']),
      'period_days': _s(st['period_days'] ?? 30),
    });
    if (f == null) return;
    final body = <String, dynamic>{...f};
    for (final k in ['avg_order_value', 'orders_per_year']) {
      if (f[k] != null) body[k] = double.tryParse(f[k]!.replaceAll(',', ''));
    }
    if (f['period_days'] != null) body['period_days'] = int.tryParse(f['period_days']!);
    await _run(() => widget.app.api!.call('PUT', '/api/feedback/settings', body: body));
  }

  Future<void> _newSurvey(String kind) async {
    final f = await _form(context, kind == 'nps' ? 'NPS survey (0-10)' : 'Anubhav survey (1-5 taare)', const [
      ('title', 'Naam (jaise "Diwali order feedback")'),
      ('question', 'Sawal (khaali = Hoola ka sawal)'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.call('POST', '/api/feedback/surveys', body: {'kind': kind, ...f}));
  }

  Widget _scoreTile(String title, String value, String sub) => Expanded(
        child: Glass(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(color: C.muted, fontSize: 12)),
            Text(value, style: display(22)),
            Text(sub, style: const TextStyle(color: C.faint, fontSize: 11.5)),
          ]),
        ),
      );

  Widget _today() {
    final ff = _map(_d?['fix_first']);
    final sc = _map(_d?['scores']);
    final nps = _map(sc['nps']);
    final csat = _map(sc['csat']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(_d?['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Row(children: [
        _scoreTile('NPS', nps['nps'] == null ? '–' : '${(nps['nps'] as num) >= 0 ? '+' : ''}${nps['nps']}', '${nps['n'] ?? 0} jawab'),
        const SizedBox(width: 8),
        _scoreTile('CSAT', csat['csat'] == null ? '–' : '${csat['csat']}%', csat['avg'] == null ? '' : 'ausat ${csat['avg']}★'),
        const SizedBox(width: 8),
        _scoreTile('Bina jawab', '${_d?['unreplied_public'] ?? 0}', 'public review'),
      ]),
      const SizedBox(height: 12),
      Text('Pehle yeh theek karein', style: display(15)),
      for (final x in _list(ff['fix']))
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Glass(
            padding: const EdgeInsets.all(12),
            border: x['urgent'] == true ? C.bad : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text('${x['rank']}.', style: display(16, color: C.accent)),
                const SizedBox(width: 8),
                Expanded(child: Text(_s(x['label']), style: const TextStyle(fontWeight: FontWeight.w800))),
                Pill('${x['count']}${_s(_map(x['trend'])['say']).isNotEmpty ? ' · ${_map(x['trend'])['say']}' : ''}'),
              ]),
              for (final r in ((x['reasons'] as List?) ?? const [])) Text('• ${_s(r)}', style: const TextStyle(fontSize: 12.5)),
              for (final e in _list(x['examples']))
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('"${_s(e['text'])}"', style: const TextStyle(fontSize: 12, color: C.muted, fontStyle: FontStyle.italic)),
                ),
            ]),
          ),
        ),
      if (_list(ff['keep_doing']).isNotEmpty) ...[
        const SizedBox(height: 12),
        Text('Log pasand karte hain', style: display(15)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final k in _list(ff['keep_doing'])) Pill('${_s(k['label']).replaceAll(' - tareef', '')} · ${k['count']}', fg: C.ok),
        ]),
      ],
      const SizedBox(height: 12),
      for (final a in _list(_d?['alerts']).take(5))
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(a['kind'] == 'urgent' ? Icons.warning_amber_rounded : Icons.trending_up_rounded, color: C.warn, size: 18),
            const SizedBox(width: 6),
            Expanded(child: Text(_s(a['text']), style: const TextStyle(fontSize: 12.5))),
          ]),
        ),
      if (_s(_d?['flags']).isNotEmpty) Text(_s(_d?['flags']), style: const TextStyle(fontSize: 12, color: C.faint)),
    ]);
  }

  Future<void> _themeAct(Map<String, dynamic> t) async {
    final f = await _form(context, _s(t['label']), const [
      ('label', 'Apna naam'),
      ('fixed_on', 'Theek kab kiya (aaj / YYYY-MM-DD)'),
      ('note', 'Note (kya badla)'),
    ]);
    if (f == null) return;
    await _run(() => widget.app.api!.call('POST', '/api/feedback/themes/${Uri.encodeComponent(_s(t['key']))}', body: f));
  }

  Widget _themeCard(Map<String, dynamic> t) {
    final neg = t['pol'] == 'neg';
    final fixed = _map(t['fixed']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Press(
        onTap: () => _themeAct(t),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: t['urgent'] == true ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(neg ? Icons.sentiment_dissatisfied_rounded : Icons.sentiment_satisfied_alt_rounded, color: neg ? C.bad : C.ok, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(_s(t['label']), style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill('${t['count']}'),
            ]),
            Text(
                [
                  'pehle ${t['prev']}',
                  if (_s(_map(t['trend'])['say']).isNotEmpty) _s(_map(t['trend'])['say']),
                  '${t['people']} log',
                  if ((t['public'] ?? 0) > 0) '${t['public']} public',
                  if (t['avg_stars'] != null) 'ausat ${t['avg_stars']}★',
                  if (t['rupees'] != null) '~₹${t['rupees']} andaaza',
                ].join(' · '),
                style: const TextStyle(color: C.muted, fontSize: 12)),
            for (final e in _list(t['examples']).take(2))
              Text('"${_s(e['text'])}"', style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
            if (fixed.isNotEmpty) Text(_s(fixed['say']), style: const TextStyle(fontSize: 12, color: C.teal)),
            if (_s(t['note']).isNotEmpty) Text('Note: ${_s(t['note'])}', style: const TextStyle(fontSize: 12, color: C.faint)),
          ]),
        ),
      ),
    );
  }

  Widget _themes() {
    final th = _map(_d?['themes']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 6, children: [
        for (final d in const [7, 30, 90])
          ChoiceChip(
              label: Text('$d din'),
              selected: _days == d,
              onSelected: (_) {
                setState(() => _days = d);
                _load();
              }),
      ]),
      const SizedBox(height: 8),
      Text('Shikayatein (${th['total'] ?? 0} feedback mein)', style: display(15)),
      const SizedBox(height: 6),
      for (final t in _list(th['negative'])) _themeCard(t),
      const SizedBox(height: 8),
      Text('Tareef', style: display(15)),
      const SizedBox(height: 6),
      for (final t in _list(th['positive'])) _themeCard(t),
      if (_s(th['rupee_note']).isNotEmpty) Text(_s(th['rupee_note']), style: const TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  Widget _reviews() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final (k, t) in const [('', 'Sab'), ('neg', 'Shikayat'), ('mixed', 'Mila-jula'), ('pos', 'Tareef')])
            ChoiceChip(
                label: Text(t),
                selected: _filter == k,
                onSelected: (_) {
                  setState(() => _filter = k);
                  _load();
                }),
        ]),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: [
          ChoiceChip(
              label: const Text('Har jagah'),
              selected: _source.isEmpty,
              onSelected: (_) {
                setState(() => _source = '');
                _load();
              }),
          for (final e in _map(_d?['sources']).entries)
            ChoiceChip(
                label: Text('${_s(_map(e.value)['label'])} ${_map(e.value)['n'] ?? ''}'),
                selected: _source == e.key,
                onSelected: (_) {
                  setState(() => _source = e.key);
                  _load();
                }),
        ]),
        const SizedBox(height: 8),
        GlassButton(
            label: 'Bina-jawab reviews ke draft banao',
            icon: Icons.edit_note_rounded,
            onTap: _busy ? null : () => _run(() => widget.app.api!.call('POST', '/api/feedback/replies/draft_all', body: {'limit': 10}))),
        const Text('Har draft chat mein card ban kar aayega; har jawab par aapki Haan chahiye.', style: TextStyle(fontSize: 11.5, color: C.faint)),
        const SizedBox(height: 8),
        for (final it in _items) _ReviewTile(app: widget.app, item: it, onChanged: _load),
      ]);

  Widget _surveys() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: GlassButton(label: 'NPS (0-10)', icon: Icons.speed_rounded, onTap: _busy ? null : () => _newSurvey('nps'))),
          const SizedBox(width: 8),
          Expanded(child: GlassButton(label: 'Taare (1-5)', icon: Icons.star_rounded, onTap: _busy ? null : () => _newSurvey('csat'))),
        ]),
        const SizedBox(height: 8),
        const Text('Link SAB graahakon ko bhejiye, sirf khush logon ko chun kar nahi. Jawab ke baad Google review ka link sabko ek jaisa dikhta hai.',
            style: TextStyle(fontSize: 12, color: C.faint)),
        const SizedBox(height: 8),
        for (final v in _list(_d?['surveys'])) FeedbackSurveyCard(app: widget.app, data: v, onChanged: _load),
      ]);

  Widget _sources() {
    final g = _map(_d?['google']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Feedback lao', style: display(15)),
      const SizedBox(height: 6),
      GlassButton(label: 'Sheet / export daalo (Play, Amazon, Flipkart, Zomato, Swiggy, Typeform...)', icon: Icons.upload_file_rounded,
          onTap: _busy ? null : _import),
      const SizedBox(height: 6),
      GlassButton(label: 'Reviews chipkao', icon: Icons.content_paste_rounded, onTap: _busy ? null : _paste),
      const SizedBox(height: 6),
      GlassButton(label: 'Google Form ke jawab', icon: Icons.fact_check_rounded, onTap: _busy ? null : () => _sync('forms')),
      const SizedBox(height: 6),
      GlassButton(label: 'WhatsApp inbox se', icon: Icons.chat_rounded, onTap: _busy ? null : () => _sync('inbox')),
      const SizedBox(height: 6),
      GlassButton(label: 'Call notes se', icon: Icons.call_rounded, onTap: _busy ? null : () => _sync('calls')),
      const SizedBox(height: 12),
      Glass(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.storefront_rounded, color: C.accent),
            const SizedBox(width: 8),
            const Expanded(child: Text('Google Business Profile reviews', style: TextStyle(fontWeight: FontWeight.w800))),
            Pill(g['connected'] == true ? 'juda' : 'nahi juda', fg: g['connected'] == true ? C.ok : C.muted),
          ]),
          if (g['connected'] == true)
            Text('${_s(g['address'])} · ${_s(g['location_title'])}${_s(g['last_sync']).isNotEmpty ? ' · sync ${_s(g['last_sync']).substring(0, 10)}' : ''}',
                style: const TextStyle(fontSize: 12, color: C.muted)),
          if (_s(g['error']).isNotEmpty) Text(_s(g['error']), style: const TextStyle(fontSize: 12, color: C.warn)),
          const SizedBox(height: 8),
          if (g['connected'] == true)
            Row(children: [
              Expanded(child: GlassButton(label: 'Abhi sync', icon: Icons.sync_rounded, onTap: _busy ? null : () => _sync('google'))),
              const SizedBox(width: 8),
              Expanded(
                  child: GlassButton(
                      label: 'Hatao',
                      icon: Icons.link_off_rounded,
                      onTap: _busy ? null : () => _run(() => widget.app.api!.call('DELETE', '/api/feedback/google')))),
            ])
          else
            GradientButton(label: 'Google reviews jodiye', icon: Icons.link_rounded, onTap: _busy ? null : _googleLink),
          const SizedBox(height: 6),
          const Text('Sirf aapka apna Business Profile. Jawab Google par sirf aapki Haan se jaata hai.',
              style: TextStyle(fontSize: 11.5, color: C.faint)),
        ]),
      ),
      const SizedBox(height: 12),
      GlassButton(label: 'Niyam aur apne numbers', icon: Icons.tune_rounded, onTap: _busy ? null : _settings),
      const SizedBox(height: 8),
      for (final r in ((_map(_d?['settings'])['reply_rules'] as List?) ?? const []))
        Text('• ${_s(r)}', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 8),
      for (final n in ((_map(_d?['settings'])['never'] as List?) ?? const []))
        Text('✕ ${_s(n)}', style: const TextStyle(fontSize: 11.5, color: C.faint)),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Feedback sahayak'), actions: [
          IconButton(
              icon: const Icon(Icons.table_view_rounded),
              tooltip: 'Report (Excel + PDF)',
              onPressed: _busy ? null : () => _run(() => widget.app.api!.call('POST', '/api/feedback/report', body: {'days': _days}))),
        ]),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Themes'), (2, 'Reviews'), (3, 'Survey'), (4, 'Sources')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _themes(), _reviews(), _surveys(), _sources()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Hoola koi review hatata, chhupata ya chun-chun kar nahi dikhata. Public jawab sirf aapki Haan se. Shak wale review sirf platform ke "report" raste se.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class _ReviewTile extends StatelessWidget {
  const _ReviewTile({required this.app, required this.item, required this.onChanged});
  final Santosh app;
  final Map<String, dynamic> item;
  final VoidCallback onChanged;

  Future<void> _draft(BuildContext context) async {
    try {
      final r = _map(await app.api!.call('POST', '/api/feedback/items/${item['id']}/reply', body: {}));
      if (!context.mounted) return;
      await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: C.bgBottom,
        builder: (_) => Padding(padding: const EdgeInsets.all(16), child: SingleChildScrollView(child: FeedbackReplyCard(app: app, data: r))),
      );
      onChanged();
    } catch (e) {
      if (context.mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final flags = _list(item['flags']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: item['urgent'] == true ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 8, height: 8, decoration: BoxDecoration(color: _labelColor(_s(item['label'])), shape: BoxShape.circle)),
            const SizedBox(width: 6),
            Expanded(
                child: Text(
                    [_s(item['source_label']), _s(item['author']), _stars(item['stars']), if (item['score'] != null) 'score ${item['score']}', _s(item['at']).split('T').first]
                        .where((x) => x.isNotEmpty)
                        .join(' · '),
                    style: const TextStyle(fontSize: 12, color: C.muted))),
            if (item['replied'] == true) const Pill('jawab diya', fg: C.ok),
          ]),
          const SizedBox(height: 4),
          Text(_s(item['text']).isEmpty ? '(sirf taare)' : _s(item['text']), style: const TextStyle(fontSize: 13.5, height: 1.3)),
          if (((item['themes'] as List?) ?? const []).isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Wrap(spacing: 4, runSpacing: 4, children: [
                for (final t in (item['themes'] as List)) Pill(_s(t).replaceAll(':neg', ' −').replaceAll(':pos', ' +')),
              ]),
            ),
          for (final f in flags) Text('⚑ ${_s(f['why'])}', style: const TextStyle(fontSize: 11.5, color: C.warn)),
          if (item['replied'] != true)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(onPressed: () => _draft(context), icon: const Icon(Icons.reply_rounded, size: 18), label: const Text('Jawab ka draft')),
            ),
        ]),
      ),
    );
  }
}

/// Chat / call card `feedback_reply`: the draft and HER Haan. Only this tap makes a reply public.
class FeedbackReplyCard extends StatefulWidget {
  const FeedbackReplyCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  State<FeedbackReplyCard> createState() => _FeedbackReplyCardState();
}

class _FeedbackReplyCardState extends State<FeedbackReplyCard> {
  late final TextEditingController _c = TextEditingController(text: _s(widget.data['text']));
  late String _status = _s(widget.data['status']).isEmpty ? 'draft' : _s(widget.data['status']);
  bool _busy = false;
  String _msg = '';

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final edited = _c.text.trim() != _s(widget.data['text']).trim();
      final r = _map(await widget.app.api!.call('POST', '/api/feedback/replies/${widget.data['reply_id']}/decide',
          body: {'yes': yes, 'hash': _s(widget.data['hash']), if (yes && edited) 'text': _c.text.trim()}));
      if (!mounted) return;
      setState(() {
        _status = _s(r['status']);
        _msg = _s(r['say']);
      });
      if (yes && _status == 'approved') await Clipboard.setData(ClipboardData(text: _s(r['text'])));
    } catch (e) {
      if (mounted) setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _done() async {
    setState(() => _busy = true);
    try {
      final r = _map(await widget.app.api!.call('POST', '/api/feedback/replies/${widget.data['reply_id']}/done', body: {}));
      if (mounted) {
        setState(() {
          _status = _s(r['status']);
          _msg = _s(r['say']);
        });
      }
    } catch (e) {
      if (mounted) setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final it = _map(widget.data['item']);
    final probs = ((widget.data['problems'] as List?) ?? const []).map(_s).toList();
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.rate_review_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('Jawab: ${_s(it['source_label'])} ${_stars(it['stars'])}'.trim(), style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status),
        ]),
        const SizedBox(height: 6),
        Text('"${_s(it['text'])}"', style: const TextStyle(fontSize: 12.5, color: C.muted, fontStyle: FontStyle.italic), maxLines: 5,
            overflow: TextOverflow.ellipsis),
        const SizedBox(height: 8),
        TextField(
          controller: _c,
          enabled: _status == 'draft',
          maxLines: 6,
          minLines: 3,
          decoration: const InputDecoration(labelText: 'Jawab (badal sakti hain)', border: OutlineInputBorder()),
        ),
        for (final p in probs) Text('⚠ $p', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 6),
        Text(_s(widget.data['where_say']), style: const TextStyle(fontSize: 12, color: C.faint)),
        if (_msg.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_msg, style: const TextStyle(fontSize: 12.5))),
        const SizedBox(height: 8),
        if (_status == 'draft')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: widget.data['where'] == 'google_api' ? 'Haan, Google par daalo' : 'Haan, final',
                    icon: Icons.check_rounded,
                    onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, onTap: _busy ? null : () => _decide(false))),
          ]),
        if (_status == 'approved')
          Row(children: [
            Expanded(
                child: GlassButton(
                    label: 'Copy',
                    icon: Icons.copy_rounded,
                    onTap: () async {
                      await Clipboard.setData(ClipboardData(text: _c.text.trim()));
                      if (context.mounted) _snack(context, 'Copy ho gaya');
                    })),
            const SizedBox(width: 8),
            Expanded(child: GradientButton(label: 'Daal diya', icon: Icons.done_all_rounded, onTap: _busy ? null : _done)),
          ]),
      ]),
    );
  }
}

/// Survey card (`feedback_survey` and the Survey tab): link, WhatsApp draft she sends herself, open / close.
class FeedbackSurveyCard extends StatelessWidget {
  const FeedbackSurveyCard({super.key, required this.app, required this.data, this.onChanged});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onChanged;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Glass(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(data['kind'] == 'nps' ? Icons.speed_rounded : Icons.star_rounded, color: C.accent),
              const SizedBox(width: 8),
              Expanded(child: Text(_s(data['title']), style: const TextStyle(fontWeight: FontWeight.w800))),
              Pill(data['active'] == false ? 'band' : '${data['responses'] ?? 0} jawab'),
            ]),
            Text(_s(data['question']), style: const TextStyle(fontSize: 12.5, color: C.muted)),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              TextButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: _s(data['link'])));
                    if (context.mounted) _snack(context, 'Link copy');
                  },
                  icon: const Icon(Icons.link_rounded, size: 18),
                  label: const Text('Link copy')),
              TextButton.icon(
                  onPressed: () => _open(context, _s(data['whatsapp'])),
                  icon: const Icon(Icons.send_rounded, size: 18),
                  label: const Text('WhatsApp draft')),
              TextButton.icon(onPressed: () => _open(context, _s(data['link'])), icon: const Icon(Icons.visibility_rounded, size: 18), label: const Text('Dekho')),
              if (onChanged != null)
                TextButton(
                    onPressed: () async {
                      try {
                        await app.api!.call('POST', '/api/feedback/surveys/${data['id']}/active', body: {'active': data['active'] == false});
                        onChanged?.call();
                      } catch (e) {
                        if (context.mounted) _snack(context, '$e');
                      }
                    },
                    child: Text(data['active'] == false ? 'Kholo' : 'Band karo')),
            ]),
          ]),
        ),
      );
}

/// Chat / call card for `feedback_alert` (urgent review, spike, rating drop), `feedback_report` (monthly) and
/// `feedback_update` (new feedback read): one line + opens the screen.
class FeedbackNoteCard extends StatelessWidget {
  const FeedbackNoteCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final kind = _s(data['kind']);
    final urgent = kind == 'urgent';
    final text = _s(data['text']).isNotEmpty ? _s(data['text']) : _s(data['say']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => FeedbackScreen(app: app))),
      child: Glass(
        border: urgent ? C.bad : null,
        child: Row(children: [
          Icon(urgent ? Icons.warning_amber_rounded : (kind == 'spike' || kind == 'rating' ? Icons.trending_up_rounded : Icons.forum_rounded),
              color: urgent ? C.bad : C.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: const TextStyle(fontWeight: FontWeight.w700, height: 1.3))),
          const Icon(Icons.chevron_right_rounded, color: C.muted),
        ]),
      ),
    );
  }
}
