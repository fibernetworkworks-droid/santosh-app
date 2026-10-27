/// Profile > Cyber Suraksha Sahayak: Hoola as the business's cybersecurity analyst.
/// Aaj (what matters, block / wipe cards waiting for HER tap, incidents, advisories) · Alerts (paste / upload, noise filtered, why,
/// "yeh normal hai") · Jaanch (suspicious mail with full headers, links looked up never opened, files hashed never uploaded) ·
/// Domain (her own domains: DNS / SSL / headers, breaches, software + CVE / KEV / CERT-In) · Incident (timeline, CERT-In 6 hours,
/// DPDP, Word / PDF note) · Niyam (her IPs / names / emails, keys typed only here, her rules).
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
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

Color _levelColor(String l) => switch (l) { 'matters' => C.bad, 'watch' => C.warn, _ => C.faint };
Color _verdictColor(String v) => switch (v) { 'likely_phish' || 'malicious' => C.bad, 'suspicious' => C.warn, 'clean' => C.ok, _ => C.chip };
String _verdictLabel(String v) =>
    switch (v) { 'likely_phish' => 'Fraud lagta hai', 'malicious' => 'Khatarnak', 'suspicious' => 'Shak wala', 'clean' => 'Saaf mila', _ => 'Saaf nahi pata' };
Color _flagColor(String l) => switch (l) { 'bad' => C.bad, 'warn' => C.warn, _ => C.muted };

Future<Map<String, String>?> _form(BuildContext context, String title, List<(String, String)> fields,
    {String ok = 'Aage', Set<String> long = const {'text', 'what', 'lessons', 'impact', 'done'}, Set<String> secret = const {}}) async {
  final c = {for (final (k, _) in fields) k: TextEditingController()};
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
                decoration: InputDecoration(labelText: label),
                maxLines: secret.contains(k) ? 1 : (long.contains(k) ? 6 : 1)),
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

Widget _flags(List<Map<String, dynamic>> flags, {int max = 8}) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final f in flags.take(max))
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text('• ${_s(f['text'])}', style: TextStyle(fontSize: 12.5, height: 1.3, color: _flagColor(_s(f['level'])))),
          ),
      ],
    );

class CyberScreen extends StatefulWidget {
  const CyberScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<CyberScreen> createState() => _CyberScreenState();
}

class _CyberScreenState extends State<CyberScreen> {
  Map<String, dynamic>? _d;
  int _tab = 0;
  bool _busy = false;
  String _level = 'matters';
  Map<String, dynamic>? _lastCheck;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _m(await widget.app.api!.call('GET', '/api/cyber'));
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

  void _openIncident(String id) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => CyberIncidentPage(app: widget.app, id: id)))
      .then((_) => _load());

  // ---------------- alerts
  Future<void> _paste() async {
    final f = await _form(context, 'Alert chipkaiye', const [
      ('text', 'Antivirus / firewall / server log / Workspace / M365 / Cloudflare alert'),
      ('source', 'Kahan se (antivirus / firewall / server / workspace / m365 / waf, zaroori nahi)'),
    ], ok: 'Jaancho');
    if (f == null || (f['text'] ?? '').isEmpty) return;
    await _run('POST', '/api/cyber/intake', f);
    setState(() => _tab = 1);
  }

  Future<void> _upload() async {
    final res = await FilePicker.platform.pickFiles(withData: true, type: FileType.custom, allowedExtensions: const ['csv', 'json', 'log', 'txt', 'eml']);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/cyber/intake/file', f.name, f.bytes!, timeout: const Duration(seconds: 120), tries: 2);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() {
      _busy = false;
      _tab = 1;
    });
  }

  Future<void> _teach(Map<String, dynamic> a) async {
    final f = await _form(context, 'Yeh normal kyun hai?', const [('reason', 'Wajah (jaise: hamara backup server hai)')], ok: 'Sikhao');
    if (f == null || (f['reason'] ?? '').isEmpty) return;
    await _run('POST', '/api/cyber/alerts/${_s(a['id'])}/teach', f);
  }

  Future<void> _incidentFrom(List<String> ids) async {
    final f = await _form(context, 'Incident note', const [('title', 'Naam (zaroori nahi)'), ('what', 'Kya hua (apne shabdon mein)')], ok: 'Kholo');
    if (f == null) return;
    final r = await _run('POST', '/api/cyber/incidents', {...f, 'alert_ids': ids});
    final i = _m(r?['incident']);
    if (i['id'] != null && mounted) _openIncident(_s(i['id']));
  }

  Future<void> _contain(String kind, String target, {String alert = '', String incident = ''}) async {
    final f = await _form(context, 'Card banao: ${_kindLabel(kind)}', [('target', 'Kis par (IP / user / device): $target'), ('reason', 'Kyun')], ok: 'Card bhejo');
    if (f == null) return;
    await _run('POST', '/api/cyber/actions', {
      'kind': kind,
      'target': (f['target'] ?? '').isEmpty ? target : f['target'],
      'reason': f['reason'] ?? '',
      if (alert.isNotEmpty) 'alert': alert,
      if (incident.isNotEmpty) 'incident': incident,
    });
  }

  Widget _alertTile(Map<String, dynamic> a) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: a['level'] == 'matters' ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Pill('${a['score']}', fg: _levelColor(_s(a['level']))),
              const SizedBox(width: 6),
              Expanded(child: Text('${_s(a['number'])} · ${_s(a['label'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
              if ((a['count'] ?? 1) is int && (a['count'] as int) > 1) Pill('x${a['count']}'),
            ]),
            const SizedBox(height: 4),
            Text(_s(a['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)),
            Text([_s(a['source_label']), if (_s(a['host']).isNotEmpty) _s(a['host']), if (_s(a['user']).isNotEmpty) _s(a['user']), if (_s(a['ip']).isNotEmpty) _s(a['ip']), _s(a['last_local'])].join(' · '),
                style: const TextStyle(fontSize: 11.5, color: C.muted)),
            for (final w in ((a['why'] as List?) ?? const []).skip(1).take(3)) Text('↳ $w', style: const TextStyle(fontSize: 12, color: C.accentSoft)),
            for (final x in ((a['advice'] as List?) ?? const []).take(2)) Text('• $x', style: const TextStyle(fontSize: 12, height: 1.3)),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 6, children: [
              if (a['status'] != 'incident') GlassButton(label: 'Incident', icon: Icons.assignment_late_rounded, height: 36, onTap: _busy ? null : () => _incidentFrom([_s(a['id'])])),
              if (_s(a['ip']).isNotEmpty) GlassButton(label: 'IP block card', icon: Icons.block_rounded, height: 36, onTap: _busy ? null : () => _contain('block_ip', _s(a['ip']), alert: _s(a['id']))),
              if (a['never_mute'] != true) GlassButton(label: 'Yeh normal hai', icon: Icons.school_rounded, height: 36, onTap: _busy ? null : () => _teach(a)),
              GlassButton(label: 'Dekh liya', height: 36, onTap: _busy ? null : () => _run('POST', '/api/cyber/alerts/${_s(a['id'])}/status', {'status': 'ack'})),
            ]),
          ]),
        ),
      );

  Widget _today() {
    final d = _d ?? const {};
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: GradientButton(label: 'Alert chipkao', icon: Icons.content_paste_rounded, height: 46, onTap: _busy ? null : _paste)),
        const SizedBox(width: 8),
        Expanded(child: GlassButton(label: 'File do', icon: Icons.upload_file_rounded, height: 46, onTap: _busy ? null : _upload)),
      ]),
      const SizedBox(height: 10),
      for (final a in _list(d['waiting'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: CyberActionCard(app: widget.app, data: {'action': a}, onDone: _load)),
      if (_list(d['matters']).isNotEmpty) Text('Zaroori', style: display(15)),
      const SizedBox(height: 6),
      for (final a in _list(d['matters']).take(6)) _alertTile(a),
      for (final i in _list(d['incidents']))
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.assignment_late_rounded, color: C.warn),
          title: Text('${_s(i['number'])} · ${_s(i['title'])}'),
          subtitle: Text(_s(i['detected_local']), style: const TextStyle(color: C.muted)),
          onTap: () => _openIncident(_s(i['id'])),
        ),
      for (final a in _list(d['advisories']).take(5)) _advTile(a),
    ]);
  }

  Widget _alertsTab() {
    final all = _list(_d?['matters']) + _list(_d?['watch']);
    final shown = all.where((a) => _level == 'all' || a['level'] == _level).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final (k, t) in const [('matters', 'Zaroori'), ('watch', 'Nazar rakho'), ('all', 'Sab')])
          ChoiceChip(label: Text(t), selected: _level == k, onSelected: (_) => setState(() => _level = k)),
        GlassButton(label: 'Chipkao', icon: Icons.content_paste_rounded, height: 36, onTap: _busy ? null : _paste),
        GlassButton(label: 'File', icon: Icons.upload_file_rounded, height: 36, onTap: _busy ? null : _upload),
        GlassButton(label: 'Hoola ke login', icon: Icons.phonelink_lock_rounded, height: 36, onTap: _busy ? null : () => _run('POST', '/api/cyber/intake', {'include_hoola': true})),
      ]),
      const SizedBox(height: 10),
      if (shown.isEmpty) const Text('Koi khula alert nahi. Shor (port scan, roke gaye hamle) yahan nahi dikhta.', style: TextStyle(color: C.muted)),
      for (final a in shown) _alertTile(a),
    ]);
  }

  // ---------------- checks
  Future<void> _checkMail() async {
    final f = await _form(context, 'Shak wala mail', const [
      ('text', 'Poora mail (Gmail: teen bindu > Show original; Outlook: View source) chipkaiye'),
      ('sender', 'Bhejne wala (zaroori nahi)'),
    ], ok: 'Jaancho');
    if (f == null || ((f['text'] ?? '').isEmpty && (f['sender'] ?? '').isEmpty)) return;
    if (!mounted) return;
    final clicked = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
              title: const Text('Kisi ne link khola / password bhara / attachment khola?'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan')),
              ],
            ));
    final r = await _run('POST', '/api/cyber/check/email', {...f, if (clicked == true) 'clicked': true});
    if (r != null && mounted) setState(() => _lastCheck = r);
  }

  Future<void> _checkLink() async {
    final f = await _form(context, 'Link jaancho (khola nahi jayega)', const [('url', 'Link(s), comma se alag')], ok: 'Jaancho');
    if (f == null || (f['url'] ?? '').isEmpty) return;
    final r = await _run('POST', '/api/cyber/check/link', {'urls': f['url']!.split(RegExp(r'[\s,]+')).where((x) => x.isNotEmpty).toList()});
    if (r != null && mounted) setState(() => _lastCheck = r);
  }

  Future<void> _checkFile() async {
    final res = await FilePicker.platform.pickFiles(withData: true);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.uploadFile('/api/cyber/check/file', f.name, f.bytes!, timeout: const Duration(seconds: 60), tries: 1);
      if (mounted) setState(() => _lastCheck = r);
      if (mounted) _snack(context, _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  Widget _checks() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GradientButton(label: 'Mail jaancho', icon: Icons.mark_email_unread_rounded, height: 46, onTap: _busy ? null : _checkMail),
          GlassButton(label: 'Link', icon: Icons.link_rounded, onTap: _busy ? null : _checkLink),
          GlassButton(label: 'File (sirf hash)', icon: Icons.fingerprint_rounded, onTap: _busy ? null : _checkFile),
        ]),
        const SizedBox(height: 10),
        if (_lastCheck != null) CyberCheckCard(app: widget.app, data: {..._lastCheck!, 'kind': _lastCheck!['sha256'] != null ? 'file' : (_lastCheck!['urls'] != null ? 'link' : 'email')}),
        const SizedBox(height: 10),
        Text('Pichhli jaanch', style: display(14)),
        for (final c in _list(_d?['checks']))
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            leading: Icon(c['kind'] == 'file' ? Icons.insert_drive_file_rounded : c['kind'] == 'link' ? Icons.link_rounded : Icons.mail_rounded,
                color: _verdictColor(_s(c['verdict']))),
            title: Text(_s(c['subject']), maxLines: 1, overflow: TextOverflow.ellipsis),
            subtitle: Text('${_verdictLabel(_s(c['verdict']))} · ${_s(c['at_local'])}', style: const TextStyle(color: C.muted, fontSize: 12)),
          ),
        const SizedBox(height: 8),
        const Text('Hoola link kabhi kholta nahi (sirf Google / VirusTotal list mein dekhta hai) aur aapki file kahin upload nahi karta, sirf uska hash.',
            style: TextStyle(fontSize: 11.5, color: C.faint)),
      ]);

  // ---------------- domains + software
  Future<void> _addDomain() async {
    final f = await _form(context, 'Apna domain', const [('domain', 'jaise ainewtika.com')], ok: 'Jodo');
    if (f == null || (f['domain'] ?? '').isEmpty) return;
    await _run('POST', '/api/cyber/domains', f);
  }

  Future<void> _addSoftware() async {
    final f = await _form(context, 'Software / device', const [
      ('product', 'Naam (Tally Prime / Windows 10 / TP-Link Archer C6)'),
      ('vendor', 'Company (zaroori nahi)'),
      ('version', 'Version'),
      ('where', 'Kahan (PC / server ka naam)'),
    ], ok: 'Jodo');
    if (f == null || (f['product'] ?? '').isEmpty) return;
    await _run('POST', '/api/cyber/software', f);
  }

  Widget _advTile(Map<String, dynamic> a) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Glass(
          padding: const EdgeInsets.all(12),
          border: a['exploited'] == true ? C.bad : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Pill(a['exploited'] == true ? 'Hamle ho rahe' : (_s(a['severity']).isEmpty ? _s(a['source']).toUpperCase() : _s(a['severity'])),
                  fg: a['exploited'] == true ? C.bad : C.warn),
              const SizedBox(width: 6),
              Expanded(child: Text(_s(a['ref']), style: const TextStyle(fontWeight: FontWeight.w800), overflow: TextOverflow.ellipsis)),
            ]),
            Text(_s(a['title']), style: const TextStyle(fontSize: 12.5)),
            if (_s(a['software']).isNotEmpty) Text('Aapka: ${_s(a['software'])} ${_s(a['where'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
            Text(_s(a['say']), style: const TextStyle(fontSize: 12, color: C.accentSoft)),
            Wrap(spacing: 6, children: [
              if (_s(a['url']).isNotEmpty) TextButton(onPressed: () => Native.openExternal(url: _s(a['url'])), child: const Text('Padho')),
              TextButton(onPressed: _busy ? null : () => _run('POST', '/api/cyber/advisories/${_s(a['id'])}/status', {'status': 'patched'}), child: const Text('Update kar diya')),
              TextButton(onPressed: _busy ? null : () => _run('POST', '/api/cyber/advisories/${_s(a['id'])}/status', {'status': 'not_ours'}), child: const Text('Hamara nahi')),
            ]),
          ]),
        ),
      );

  Widget _domains() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Domain jodo', icon: Icons.language_rounded, onTap: _busy ? null : _addDomain),
          GlassButton(label: 'Email leak jaancho', icon: Icons.person_search_rounded, onTap: _busy ? null : () => _run('POST', '/api/cyber/breach', {})),
        ]),
        const SizedBox(height: 10),
        for (final d in _list(_d?['domains'])) CyberDomainTile(app: widget.app, d: d, busy: _busy, run: _run),
        const SizedBox(height: 12),
        Text('Software aur devices', style: display(15)),
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Jodo', icon: Icons.add_rounded, height: 40, onTap: _busy ? null : _addSoftware),
          GlassButton(label: 'IT Helpdesk se lo', icon: Icons.devices_other_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/cyber/software/sync')),
          GlassButton(label: 'Naye khatre dekho', icon: Icons.refresh_rounded, height: 40, onTap: _busy ? null : () => _run('POST', '/api/cyber/advisories/refresh')),
        ]),
        for (final w in _list(_d?['software']))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('${_s(w['product'])} ${_s(w['version'])}'.trim()),
            subtitle: Text([_s(w['vendor']), _s(w['where'])].where((x) => x.isNotEmpty).join(' · '), style: const TextStyle(color: C.muted)),
            trailing: IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _busy ? null : () => _run('DELETE', '/api/cyber/software/${_s(w['id'])}')),
          ),
        const SizedBox(height: 8),
        for (final a in _list(_d?['all_advisories']).where((a) => a['status'] == 'new')) _advTile(a),
      ]);

  // ---------------- incidents
  Widget _incidents() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GradientButton(label: 'Naya incident note', icon: Icons.note_add_rounded, height: 46, onTap: _busy ? null : () => _incidentFrom(const [])),
        const SizedBox(height: 10),
        for (final i in _list(_d?['incidents']))
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.assignment_late_rounded, color: C.warn),
            title: Text('${_s(i['number'])} · ${_s(i['title'])}'),
            subtitle: Text('${_s(i['kind'])} · ${_s(i['detected_local'])}', style: const TextStyle(color: C.muted)),
            onTap: () => _openIncident(_s(i['id'])),
          ),
        const SizedBox(height: 10),
        Text('Block / wipe cards', style: display(14)),
        for (final a in _list(_d?['actions']).take(15))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('${_s(a['number'])} · ${_s(a['label'])}: ${_s(a['target'])}'),
            subtitle: Text(_s(a['status_label']), style: TextStyle(color: a['status'] == 'waiting' ? C.warn : C.muted)),
          ),
      ]);

  // ---------------- rules / keys
  Future<void> _settings() async {
    final st = _m(_d?['settings']);
    String j(dynamic l) => ((l as List?) ?? const []).join(', ');
    final f = await _form(context, 'Suraksha ke niyam', [
      ('own_ips', 'Apne office / server ke IP (abhi: ${j(st['own_ips'])})'),
      ('vip_names', 'Naam jinka fraud ho sakta hai (abhi: ${j(st['vip_names'])})'),
      ('crown_hosts', 'Zaroori server / PC (abhi: ${j(st['crown_hosts'])})'),
      ('work_emails', 'Office ke email, leak jaanch ke liye (abhi: ${j(st['work_emails'])})'),
      ('morning_time', 'Subah note ka samay (abhi: ${_s(st['morning_time'])})'),
    ], ok: 'Save');
    if (f == null || f.isEmpty) return;
    await _run('PUT', '/api/cyber/settings', f);
  }

  Future<void> _key(String provider, String label) async {
    final needsZone = provider == 'cloudflare';
    final f = await _form(context, label, [('token', 'Key / token (sirf yahan, chat mein kabhi nahi)'), if (needsZone) ('extra', 'Zone ID (32 akshar)')],
        ok: 'Jodo', secret: const {'token'});
    if (f == null || (f['token'] ?? '').isEmpty) return;
    await _run('PUT', '/api/cyber/keys/$provider', f);
  }

  Widget _rulesTab() {
    final st = _m(_d?['settings']);
    final keys = _m(st['keys']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      GlassButton(label: 'Niyam badlo', icon: Icons.tune_rounded, onTap: _busy ? null : _settings),
      const SizedBox(height: 8),
      for (final (k, label) in const [('own_ips', 'Apne IP'), ('vip_names', 'VIP naam'), ('crown_hosts', 'Zaroori systems'), ('work_emails', 'Office email')])
        Text('$label: ${((st[k] as List?) ?? const []).join(', ')}', style: const TextStyle(fontSize: 12.5)),
      const SizedBox(height: 12),
      Text('Keys (sirf server par, band tale mein)', style: display(14)),
      for (final e in keys.entries)
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(_m(e.value)['set'] == true ? Icons.check_circle_rounded : Icons.key_rounded, color: _m(e.value)['set'] == true ? C.ok : C.muted),
          title: Text(_s(_m(e.value)['label'])),
          subtitle: Text(_m(e.value)['set'] == true ? 'Judi ${_s(_m(e.value)['hint'])}' : _s(_m(e.value)['note']), style: const TextStyle(color: C.muted, fontSize: 12)),
          trailing: _m(e.value)['set'] == true
              ? IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _busy ? null : () => _run('DELETE', '/api/cyber/keys/${e.key}'))
              : TextButton(onPressed: _busy ? null : () => _key(e.key, _s(_m(e.value)['label'])), child: const Text('Jodo')),
        ),
      const Text('Google Safe Browsing aur VirusTotal ki muft key business ke liye nahi hai: business ke liye Google Web Risk (100,000 jaanch / mahina muft) '
          'aur VirusTotal premium.', style: TextStyle(fontSize: 11.5, color: C.faint)),
      const SizedBox(height: 12),
      Text('Aapne sikhaya (normal)', style: display(14)),
      for (final r in _list(_d?['rules']).where((r) => r['active'] == true))
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(_s(r['reason'])),
          subtitle: Text([_s(r['label']), _s(r['ip']), _s(r['user']), _s(r['host']), '${r['hits']} baar'].where((x) => x.isNotEmpty).join(' · '),
              style: const TextStyle(color: C.muted, fontSize: 12)),
          trailing: IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _busy ? null : () => _run('DELETE', '/api/cyber/rules/${_s(r['id'])}')),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Cyber Suraksha Sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 60), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Alerts'), (2, 'Jaanch'), (3, 'Domain'), (4, 'Incident'), (5, 'Niyam')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _alertsTab(), _checks(), _domains(), _incidents(), _rulesTab()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Hoola sirf aapke apne systems dekhta hai, kisi aur ko scan nahi karta. Block / user band / wipe sirf aapke tap se (wipe par fingerprint). '
                  'Password / OTP / API key chat mein kabhi mat dijiye.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

String _kindLabel(String k) => switch (k) {
      'block_ip' => 'IP block',
      'unblock_ip' => 'IP block hatao',
      'disable_user' => 'User band',
      'reset_sessions' => 'Sab jagah sign-out',
      'quarantine' => 'Quarantine',
      'isolate_pc' => 'PC alag karo',
      'wipe_device' => 'Device mitao',
      _ => k,
    };

class CyberDomainTile extends StatelessWidget {
  const CyberDomainTile({super.key, required this.app, required this.d, required this.busy, required this.run});
  final Santosh app;
  final Map<String, dynamic> d;
  final bool busy;
  final Future<Map<String, dynamic>?> Function(String method, String path, [Object? body]) run;

  @override
  Widget build(BuildContext context) {
    final vr = _m(d['verify_record']);
    final tls = _m(d['tls']);
    final score = d['score'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Glass(
        padding: const EdgeInsets.all(12),
        border: score is num && score < 70 ? C.warn : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_s(d['domain']), style: const TextStyle(fontWeight: FontWeight.w800))),
            if (score != null) Pill('$score/100', fg: score is num && score >= 80 ? C.ok : (score is num && score >= 60 ? C.warn : C.bad)),
            const SizedBox(width: 6),
            Pill(d['verified'] == true ? 'Aapka (pakka)' : 'Pakka nahi'),
          ]),
          if (tls['days_left'] != null) Text('SSL: ${tls['days_left']} din bache (${_s(tls['not_after'])})', style: const TextStyle(fontSize: 12, color: C.muted)),
          _flags(_list(d['flags'])),
          if (d['verified'] != true) ...[
            const SizedBox(height: 6),
            const Text('Gehri jaanch ke liye DNS mein yeh TXT record daaliye:', style: TextStyle(fontSize: 12)),
            SelectableText('${_s(vr['name'])}  TXT  ${_s(vr['value'])}', style: const TextStyle(fontSize: 12, color: C.accentSoft)),
          ],
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [
            GlassButton(label: 'Jaancho', icon: Icons.health_and_safety_rounded, height: 36, onTap: busy ? null : () => run('POST', '/api/cyber/domains/${_s(d['id'])}/check')),
            if (d['verified'] != true)
              GlassButton(label: 'Verify', icon: Icons.verified_rounded, height: 36, onTap: busy ? null : () => run('POST', '/api/cyber/domains/${_s(d['id'])}/verify')),
            GlassButton(label: 'Email leak', icon: Icons.person_search_rounded, height: 36, onTap: busy ? null : () => run('POST', '/api/cyber/domains/${_s(d['id'])}/breach')),
            if (d['verified'] != true)
              GlassButton(
                  label: 'TXT copy',
                  icon: Icons.copy_rounded,
                  height: 36,
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: _s(vr['value'])));
                    _snack(context, 'Copy ho gaya');
                  }),
          ]),
        ]),
      ),
    );
  }
}

/// One incident: timeline, CERT-In 6 hours (from the IT Helpdesk record), DPDP, block / wipe cards, Word / PDF note.
class CyberIncidentPage extends StatefulWidget {
  const CyberIncidentPage({super.key, required this.app, required this.id});
  final Santosh app;
  final String id;
  @override
  State<CyberIncidentPage> createState() => _CyberIncidentPageState();
}

class _CyberIncidentPageState extends State<CyberIncidentPage> {
  Map<String, dynamic>? _i;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final i = _m(await widget.app.api!.call('GET', '/api/cyber/incidents/${widget.id}'));
      if (mounted) setState(() => _i = i);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _do(String method, String path, [Object? body]) async {
    setState(() => _busy = true);
    await _call(context, widget.app, method, path, body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final i = _i;
    final ci = _m(i?['cert_in']);
    final dp = _m(i?['dpdp']);
    final open = i != null && i['status'] == 'open';
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text(_s(i?['number']).isEmpty ? 'Incident' : _s(i?['number']))),
      body: Aurora(
        child: i == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
                  Glass(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_s(i['title']), style: display(16)),
                      Text('${_s(i['kind'])} · pata chala ${_s(i['detected_local'])} · ${open ? 'khula' : 'band'}', style: const TextStyle(color: C.muted, fontSize: 12)),
                      if (_s(i['systems']).isNotEmpty) Text('Systems: ${_s(i['systems'])}', style: const TextStyle(fontSize: 12.5)),
                      const SizedBox(height: 6),
                      for (final (k, label) in const [('what', 'Kya hua'), ('impact', 'Asar'), ('done', 'Kya kiya'), ('lessons', 'Seekh')])
                        if (_s(i[k]).isNotEmpty) Text('$label: ${_s(i[k])}', style: const TextStyle(fontSize: 13, height: 1.35)),
                    ]),
                  ),
                  const SizedBox(height: 10),
                  Glass(
                    border: _s(i['cert_in_due']).isNotEmpty && _s(i['cert_in_reported']).isEmpty ? C.bad : null,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('CERT-In (6 ghante)', style: display(14)),
                      Text(_s(ci['why']).isEmpty ? 'CERT-In jaanch abhi nahi hui.' : _s(ci['why']), style: const TextStyle(fontSize: 12.5)),
                      if (_s(i['cert_in_due']).isNotEmpty) Text('Aakhri samay: ${_s(i['cert_in_due'])}', style: const TextStyle(color: C.warn, fontSize: 12.5)),
                      if (_s(i['cert_in_reported']).isNotEmpty) const Text('Report bhej diya.', style: TextStyle(color: C.ok, fontSize: 12.5)),
                      if (_s(i['helpdesk_incident']).isEmpty && open)
                        TextButton(onPressed: _busy ? null : () => _do('POST', '/api/cyber/incidents/${widget.id}/cert_in'), child: const Text('CERT-In jaancho')),
                      if (dp.isNotEmpty) Text(_s(dp['say']), style: const TextStyle(fontSize: 12, color: C.accentSoft)),
                      const Text('Report ka draft IT Helpdesk ke card par hai; aap apne email se bhejiye.', style: TextStyle(fontSize: 11.5, color: C.faint)),
                    ]),
                  ),
                  const SizedBox(height: 10),
                  for (final a in _list(i['actions'])) Padding(padding: const EdgeInsets.only(bottom: 8), child: CyberActionCard(app: widget.app, data: {'action': a}, onDone: _load)),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    if (open)
                      GlassButton(
                          label: 'Timeline mein jodo',
                          icon: Icons.add_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Kya hua', const [('what', 'Baat'), ('at', 'Kab (2026-10-23T14:30, zaroori nahi)')]);
                                  if (f != null && (f['what'] ?? '').isNotEmpty) await _do('POST', '/api/cyber/incidents/${widget.id}/timeline', f);
                                }),
                    if (open)
                      GlassButton(
                          label: 'Note likho',
                          icon: Icons.edit_note_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Incident note', const [('what', 'Kya hua'), ('impact', 'Asar'), ('done', 'Kya kiya'), ('lessons', 'Seekh')], ok: 'Save');
                                  if (f != null && f.isNotEmpty) await _do('PATCH', '/api/cyber/incidents/${widget.id}', f);
                                }),
                    if (open)
                      GlassButton(
                          label: 'Block / wipe card',
                          icon: Icons.gpp_maybe_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Card', const [
                                    ('kind', 'block_ip / disable_user / reset_sessions / quarantine / isolate_pc / wipe_device'),
                                    ('target', 'Kis par'),
                                    ('reason', 'Kyun'),
                                  ], ok: 'Card bhejo');
                                  if (f != null && (f['kind'] ?? '').isNotEmpty) await _do('POST', '/api/cyber/actions', {...f, 'incident': widget.id});
                                }),
                    GlassButton(label: 'Word + PDF', icon: Icons.description_rounded, onTap: _busy ? null : () => _do('POST', '/api/cyber/incidents/${widget.id}/note')),
                    if (open)
                      GlassButton(
                          label: 'Band karo',
                          icon: Icons.done_all_rounded,
                          onTap: _busy
                              ? null
                              : () async {
                                  final f = await _form(context, 'Aage aisa na ho, iske liye kya badla?', const [('lessons', 'Seekh')], ok: 'Band karo');
                                  if (f != null) await _do('POST', '/api/cyber/incidents/${widget.id}/close', f);
                                }),
                  ]),
                  const SizedBox(height: 12),
                  Text('Timeline', style: display(14)),
                  for (final t in _list(i['timeline']))
                    Text('${_s(t['at']).replaceAll('T', ' ')} · ${_s(t['by'])}: ${_s(t['what'])}', style: const TextStyle(fontSize: 12, height: 1.35)),
                ]),
              ),
      ),
    );
  }
}

// ======================================================================= chat / call cards

/// `cyber_action`: block / disable / quarantine / wipe waiting for HER tap. Only this tap decides; wipe needs her fingerprint
/// once a phone key is set up (428 -> challenge -> sign -> resend).
class CyberActionCard extends StatefulWidget {
  const CyberActionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<CyberActionCard> createState() => _CyberActionCardState();
}

class _CyberActionCardState extends State<CyberActionCard> {
  bool _busy = false;
  late Map<String, dynamic> _a = _m(widget.data['action']);

  Future<Map<String, dynamic>> _proof(String id) async {
    final ch = _m(await widget.app.api!.call('POST', '/api/cyber/actions/$id/challenge'));
    final show = _m(ch['show']);
    final r = await Native.approveKeySign(_s(ch['message']), _s(show['title']).isEmpty ? 'Device mitane ki haan' : _s(show['title']), 'Hamesha ke liye: wapas nahi aayega');
    if (r['signature'] == null) {
      throw ApiException(428, switch (_s(r['error'])) {
        'cancelled' => 'Fingerprint nahi diya, isliye kuch nahi mitaya.',
        'key_invalidated' => 'Phone mein naya fingerprint juda hai: Profile > Fingerprint se haan mein phone phir se jodiye.',
        _ => 'Fingerprint se haan nahi ho payi (${_s(r['error'])}).',
      });
    }
    return {'challenge_id': ch['challenge_id'], 'device_id': r['device_id'], 'signature': r['signature']};
  }

  Future<void> _decide(bool yes) async {
    final id = _s(_a['id']);
    if (yes && _a['wipe'] == true) {
      final sure = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
                title: const Text('Pakka mitana hai?'),
                content: Text('${_s(_a['target'])}: data hamesha ke liye chala jayega.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
                  TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan, mitao')),
                ],
              ));
      if (sure != true) return;
    }
    setState(() => _busy = true);
    try {
      final body = {'yes': yes, 'hash': _s(_a['hash'])};
      Map<String, dynamic> r;
      try {
        r = _m(await widget.app.api!.call('POST', '/api/cyber/actions/$id/decide', body: body));
      } on ApiException catch (e) {
        if (!yes || e.status != 428) rethrow;
        final proof = await _proof(id);
        r = _m(await widget.app.api!.call('POST', '/api/cyber/actions/$id/decide', body: {...body, 'proof': proof}));
      }
      if (mounted) {
        setState(() => _a = _m(r['action']).isEmpty ? _a : _m(r['action']));
        _snack(context, _s(r['say']));
      }
      widget.onDone?.call();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _done(bool ok) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/cyber/actions/${_s(_a['id'])}/done', {'ok': ok});
    if (mounted) setState(() {
      _busy = false;
      if (r != null && _m(r['action']).isNotEmpty) _a = _m(r['action']);
    });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final st = _s(_a['status']);
    final wipe = _a['wipe'] == true;
    return Glass(
      border: st == 'waiting' ? (wipe ? C.bad : C.accent) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(wipe ? Icons.phonelink_erase_rounded : Icons.gpp_maybe_rounded, color: wipe ? C.bad : C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('Aapki haan chahiye · ${_s(_a['number'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_s(_a['via']) == 'cloudflare' ? 'Cloudflare se' : 'Console steps'),
        ]),
        const SizedBox(height: 6),
        Text('${_s(_a['label'])}: ${_s(_a['target'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
        if (_s(_a['reason']).isNotEmpty) Text('Kyun: ${_s(_a['reason'])}', style: const TextStyle(fontSize: 12.5, color: C.muted)),
        if (_s(_a['risk']).isNotEmpty) Text('Dhyaan: ${_s(_a['risk'])}', style: TextStyle(fontSize: 12, color: wipe ? C.bad : C.warn)),
        if (_s(_a['undo']).isNotEmpty) Text('Wapas: ${_s(_a['undo'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(_a['via']) != 'cloudflare' || st == 'approved' || st == 'failed')
          for (final x in ((_a['steps'] as List?) ?? const []).take(3)) Text('• $x', style: const TextStyle(fontSize: 12, height: 1.3)),
        const SizedBox(height: 8),
        if (st == 'waiting')
          Row(children: [
            Expanded(
                child: GradientButton(
                    label: wipe ? 'Haan, mitao' : 'Haan, karo', icon: wipe ? Icons.fingerprint_rounded : Icons.check_rounded, height: 44, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            Expanded(child: GlassButton(label: 'Mana', icon: Icons.close_rounded, height: 44, onTap: _busy ? null : () => _decide(false))),
          ])
        else if (st == 'approved')
          Wrap(spacing: 8, children: [
            GlassButton(label: 'Maine kar diya', icon: Icons.done_rounded, height: 40, onTap: _busy ? null : () => _done(true)),
            GlassButton(label: 'Nahi hua', height: 40, onTap: _busy ? null : () => _done(false)),
          ])
        else
          Text(_s(_a['status_label']), style: TextStyle(fontSize: 12.5, color: st == 'done' ? C.ok : C.muted)),
      ]),
    );
  }
}

/// `cyber_alerts`: what matters out of a batch of alerts (the noise is only counted).
class CyberAlertsCard extends StatelessWidget {
  const CyberAlertsCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final m = _list(data['matters']);
    final br = _list(data['breach']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CyberScreen(app: app))),
      child: Glass(
        border: m.isNotEmpty ? C.bad : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.shield_rounded, color: m.isNotEmpty ? C.bad : C.accent),
            const SizedBox(width: 8),
            Expanded(child: Text(m.isNotEmpty ? '${m.length} zaroori suraksha alert' : 'Suraksha alerts', style: const TextStyle(fontWeight: FontWeight.w800))),
            if (data['noise'] != null) Pill('${data['noise']} shor'),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
          for (final a in m.take(4)) ...[
            const SizedBox(height: 4),
            Text('${_s(a['number'])} · ${_s(a['label'])} (${a['score']})', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
            for (final x in ((a['advice'] as List?) ?? const []).take(1)) Text('• $x', style: const TextStyle(fontSize: 12, color: C.accentSoft)),
          ],
          for (final b in br.take(4)) Text('• ${_s(b['email'])}: ${_list(b['breaches']).map((x) => _s(x['title'])).join(', ')}', style: const TextStyle(fontSize: 12)),
        ]),
      ),
    );
  }
}

/// `cyber_check`: a mail / link / file verdict with its flags.
class CyberCheckCard extends StatelessWidget {
  const CyberCheckCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final v = _s(data['verdict']);
    final kind = _s(data['kind']);
    final hd = _m(data['helpdesk']);
    return Glass(
      border: _verdictColor(v) == C.bad ? C.bad : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(kind == 'file' ? Icons.insert_drive_file_rounded : kind == 'link' ? Icons.link_rounded : Icons.mark_email_unread_rounded, color: _verdictColor(v)),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['subject']).isEmpty ? (_s(data['from']).isEmpty ? 'Jaanch' : _s(data['from'])) : _s(data['subject']),
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_verdictLabel(v), fg: _verdictColor(v)),
        ]),
        const SizedBox(height: 6),
        Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
        _flags(_list(data['flags'])),
        for (final x in ((data['actions'] as List?) ?? const []).take(3)) Text('→ $x', style: const TextStyle(fontSize: 12, color: C.accentSoft, height: 1.3)),
        if (_m(hd['incident']).isNotEmpty) Text('IT Helpdesk incident khula: ${_s(hd['ticket'])}', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (v == 'likely_phish' || v == 'malicious')
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: GlassButton(label: '1930 (paisa gaya ho to)', icon: Icons.call_rounded, height: 38, onTap: () => Native.openExternal(url: 'tel:1930')),
          ),
      ]),
    );
  }
}

/// `cyber_incident`: an incident note was opened (CERT-In clock when it applies).
class CyberIncidentCard extends StatelessWidget {
  const CyberIncidentCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final i = _m(data['incident']);
    return Press(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CyberIncidentPage(app: app, id: _s(i['id'])))),
      child: Glass(
        border: _s(i['cert_in_due']).isNotEmpty ? C.bad : C.warn,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.assignment_late_rounded, color: C.warn),
            const SizedBox(width: 8),
            Expanded(child: Text('${_s(i['number'])} · ${_s(i['title'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          const SizedBox(height: 6),
          Text(_s(data['say']), style: const TextStyle(fontSize: 12.5, height: 1.35)),
          if (_s(i['cert_in_due']).isNotEmpty) Text('CERT-In aakhri samay: ${_s(i['cert_in_due'])}', style: const TextStyle(fontSize: 12.5, color: C.bad)),
        ]),
      ),
    );
  }
}

/// `cyber_advisory`: new CVE / CISA KEV / CERT-In matches for her software.
class CyberAdvisoryCard extends StatelessWidget {
  const CyberAdvisoryCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CyberScreen(app: app))),
        child: Glass(
          border: C.warn,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Row(children: [Icon(Icons.system_security_update_warning_rounded, color: C.warn), SizedBox(width: 8), Expanded(child: Text('Software khatre', style: TextStyle(fontWeight: FontWeight.w800)))]),
            const SizedBox(height: 6),
            Text(_s(data['say']), style: const TextStyle(fontSize: 12.5)),
            for (final a in _list(data['advisories']).take(4))
              Text('• ${_s(a['ref'])} ${_s(a['software'])}${a['exploited'] == true ? ' (hamle ho rahe)' : ''}',
                  style: TextStyle(fontSize: 12, color: a['exploited'] == true ? C.bad : C.ink)),
          ]),
        ),
      );
}

/// `cyber_posture`: her domain's score and what to fix first.
class CyberPostureCard extends StatelessWidget {
  const CyberPostureCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final sc = data['score'];
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.language_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(data['domain']), style: const TextStyle(fontWeight: FontWeight.w800))),
          if (sc != null) Pill('$sc/100', fg: sc is num && sc >= 80 ? C.ok : (sc is num && sc >= 60 ? C.warn : C.bad)),
        ]),
        const SizedBox(height: 4),
        _flags(_list(data['flags']).where((f) => f['level'] != 'info').toList(), max: 6),
      ]),
    );
  }
}

/// `cyber_day`: the morning security note.
class CyberDayCard extends StatelessWidget {
  const CyberDayCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Press(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CyberScreen(app: app))),
        child: Glass(
          child: Row(children: [
            const Icon(Icons.shield_moon_rounded, color: C.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(_s(data['say']), style: const TextStyle(fontSize: 13, height: 1.35))),
          ]),
        ),
      );
}
