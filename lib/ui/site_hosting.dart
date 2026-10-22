/// v0.122 Website hosting in the app: "Live karo" card (her tap), her domain + DNS card (her tap applies it), live /
/// down cards, the hosting panel on the site page (addresses, DNS plans with check / undo, her Cloudflare key typed only
/// here, email at her domain, rollback per version).
library;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => Map<String, dynamic>.from((m as Map?) ?? const {});
void _snack(BuildContext c, String t) => ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
}

/// Asks the server for the launch / rollback card and shows it in a sheet (her tap is on the card).
Future<void> showLaunchSheet(BuildContext context, Santosh app, String siteId, String action, Map<String, dynamic> body) async {
  try {
    final card = await app.api!.siteAct(siteId, action, body);
    if (!context.mounted) return;
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (c) => SafeArea(child: SingleChildScrollView(padding: const EdgeInsets.all(12), child: SiteLaunchCard(v: card, app: app))),
    );
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
  }
}

/// "Live karein?" (launch) or "wapas karein?" (rollback) card: only her tap makes it live.
class SiteLaunchCard extends StatefulWidget {
  const SiteLaunchCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<SiteLaunchCard> createState() => _SiteLaunchCardState();
}

class _SiteLaunchCardState extends State<SiteLaunchCard> {
  bool _busy = false;
  String _done = '';
  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final site = _map(v['site']);
    final rollback = v['kind'] == 'rollback';
    final blockers = (v['blockers'] as List? ?? const []).map((e) => '$e').toList();
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(rollback ? Icons.history_rounded : Icons.rocket_launch_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(rollback ? 'Purana version live karein?' : 'Website live karein?', style: display(15))),
        ]),
        const SizedBox(height: 6),
        Text('${site['number'] ?? ''} ${site['name'] ?? ''} · v${v['version'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        for (final h in (v['hosts'] as List? ?? const [])) Text('🌐 $h', style: const TextStyle(color: C.ink, fontSize: 13)),
        if (_s(v['preview']).isNotEmpty)
          TextButton(onPressed: () => _open(widget.app.api!.absolute(_s(v['preview']))), child: const Text('Pehle preview dekh lo')),
        for (final b in blockers) Text('⛔ $b', style: const TextStyle(color: C.bad, fontSize: 12.5)),
        if (_done.isNotEmpty) Text(_done, style: const TextStyle(color: C.ok, fontWeight: FontWeight.w700)),
        if (blockers.isEmpty && _done.isEmpty)
          Align(
            alignment: Alignment.centerRight,
            child: GlassButton(
              label: rollback ? 'Haan, wapas karo' : 'Haan, live karo',
              color: C.accent,
              onTap: _busy ? null : _go,
            ),
          ),
      ]),
    );
  }

  Future<void> _go() async {
    final v = widget.v;
    final id = _s(_map(v['site'])['id']);
    setState(() => _busy = true);
    try {
      final r = v['kind'] == 'rollback'
          ? await widget.app.api!.siteAct(id, 'rollback', {'version': v['version'], 'hash': v['hash']})
          : await widget.app.api!.siteAct(id, 'launch', {'hash': v['hash']});
      if (mounted) setState(() => _done = _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

/// DNS plan card: before -> after in plain words; her tap applies it (her Cloudflare), else steps for her registrar.
class SiteDnsCard extends StatefulWidget {
  const SiteDnsCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<SiteDnsCard> createState() => _SiteDnsCardState();
}

class _SiteDnsCardState extends State<SiteDnsCard> {
  bool _busy = false;
  String _note = '';
  @override
  Widget build(BuildContext context) {
    final p = _map(widget.v['plan']);
    final manual = p['provider'] == 'manual';
    final words = (p['words'] as List? ?? const []).map((e) => '$e').toList();
    final risks = (p['risks'] as List? ?? const []).map((e) => '$e').toList();
    final steps = (p['manual_steps'] as List? ?? const []).map((e) => '$e').toList();
    final applied = p['status'] == 'applied' || widget.v['kind'] == 'dns_done';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.dns_rounded, color: C.teal, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('${p['domain'] ?? ''}: ${p['purpose'] == 'email' ? 'email' : 'website'} DNS', style: display(15))),
          Pill(applied ? 'Lag gaya' : (manual ? 'Aap daaliye' : 'Aapki haan'), fg: applied ? C.ok : C.accent),
        ]),
        const SizedBox(height: 6),
        Text(_s(widget.v['say']), style: const TextStyle(color: C.chip, fontSize: 13)),
        const SizedBox(height: 6),
        for (final w in words) Text('• $w', style: const TextStyle(fontSize: 12, color: C.ink)),
        for (final r in risks) Text('⚠ $r', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (manual) for (final s in steps) Text('→ $s', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_note.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_note, style: const TextStyle(color: C.ok))),
        const SizedBox(height: 8),
        Row(mainAxisAlignment: MainAxisAlignment.end, children: [
          TextButton(onPressed: _busy ? null : _check, child: Text(manual ? 'Maine daal diya, jaancho' : 'Jaancho')),
          if (!manual && !applied)
            GlassButton(label: 'Haan, badlo', color: C.accent, height: 38, onTap: _busy ? null : _apply),
        ]),
      ]),
    );
  }

  Future<void> _apply() async {
    final p = _map(widget.v['plan']);
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.siteDns(_s(p['id']), 'apply', {'hash': p['hash']});
      if (mounted) setState(() => _note = _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _check() async {
    final p = _map(widget.v['plan']);
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.siteDnsCheck(_s(p['id']));
      if (mounted) setState(() => _note = _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

class SiteLiveCard extends StatelessWidget {
  const SiteLiveCard({super.key, required this.v, required this.app, this.down = false});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool down;
  @override
  Widget build(BuildContext context) {
    final ok = !down || v['ok'] == true;
    return Glass(
      child: Row(children: [
        Icon(ok ? Icons.public_rounded : Icons.cloud_off_rounded, color: ok ? C.ok : C.bad),
        const SizedBox(width: 10),
        Expanded(child: Text(_s(v['say']), style: const TextStyle(fontSize: 13.5))),
        if (_s(v['url']).isNotEmpty) IconButton(icon: const Icon(Icons.open_in_new_rounded), onPressed: () => _open(_s(v['url']))),
      ]),
    );
  }
}

/// On the site page: addresses, Live karo, her domain, her Cloudflare key, email DNS, DNS plans.
class SiteHostingPanel extends StatefulWidget {
  const SiteHostingPanel({super.key, required this.app, required this.siteId, required this.ready});
  final Santosh app;
  final String siteId;
  final bool ready;
  @override
  State<SiteHostingPanel> createState() => _SiteHostingPanelState();
}

class _SiteHostingPanelState extends State<SiteHostingPanel> {
  Map<String, dynamic>? _h;
  final _domain = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final h = await widget.app.api!.siteHosting(widget.siteId);
      if (mounted) setState(() => _h = h);
    } catch (_) {}
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final h = _h ?? const {};
    final hosts = _list(h['hosts']);
    final keys = _list(h['keys']);
    final hasCf = keys.any((k) => k['provider'] == 'cloudflare');
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [Text('Live / hosting', style: display(16)), const Spacer(),
          IconButton(icon: const Icon(Icons.refresh_rounded, size: 20), onPressed: _load)]),
        if (hosts.isEmpty) const Text('Abhi live nahi.', style: TextStyle(color: C.faint)),
        for (final x in hosts)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(x['status'] == 'active' ? Icons.check_circle_rounded : Icons.hourglass_top_rounded,
                color: x['status'] == 'active' ? C.ok : C.warn, size: 20),
            title: Text(_s(x['host'])),
            subtitle: Text('${x['status']}${_s(x['ssl']).isEmpty ? '' : ' · SSL ${x['ssl']}'} · v${x['live_version']}'
                '${_s(x['problem']).isEmpty ? '' : '\n${x['problem']}'}', style: const TextStyle(fontSize: 11.5, color: C.muted)),
            trailing: x['status'] == 'active' ? IconButton(icon: const Icon(Icons.open_in_new_rounded),
                onPressed: () => _open('https://${x['host']}/')) : null,
          ),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (widget.ready)
            GlassButton(label: hosts.isEmpty ? 'Live karo' : 'Naya version live karo', icon: Icons.rocket_launch_rounded,
                color: C.accent, height: 40,
                onTap: _busy ? null : () => showLaunchSheet(context, widget.app, widget.siteId, 'launch-request', const {})),
          if (hosts.isNotEmpty)
            TextButton(onPressed: _busy ? null : _takedown, child: const Text('Band karo')),
        ]),
        const Divider(height: 24),
        Text('Apna domain', style: display(14)),
        Row(children: [
          Expanded(child: TextField(controller: _domain, decoration: const InputDecoration(hintText: 'sharmasweets.in'))),
          TextButton(onPressed: _busy ? null : () {
            final d = _domain.text.trim();
            if (d.isEmpty) return;
            _run(() => widget.app.api!.siteAct(widget.siteId, 'domain', {'domain': d}));
          }, child: const Text('Jodo')),
        ]),
        const SizedBox(height: 6),
        Row(children: [
          Icon(hasCf ? Icons.verified_rounded : Icons.key_rounded, color: hasCf ? C.ok : C.faint, size: 18),
          const SizedBox(width: 6),
          Expanded(child: Text(hasCf ? 'Aapka Cloudflare juda hai (${keys.firstWhere((k) => k['provider'] == 'cloudflare')['label']})'
              : 'Domain ka DNS Cloudflare par hai? Token jodiye, Hoola badlav aapki haan par khud lagayega.',
              style: const TextStyle(fontSize: 12, color: C.muted))),
          TextButton(onPressed: _busy ? null : () => hasCf ? _forgetKey() : _addKey(), child: Text(hasCf ? 'Hatao' : 'Jodo')),
        ]),
        TextButton.icon(onPressed: _busy ? null : () => showDomainSheet(context, widget.app, widget.siteId),
            icon: const Icon(Icons.travel_explore_rounded, size: 18), label: const Text('Naya domain chuno (daam ke saath)')),
        TextButton.icon(onPressed: _busy ? null : _email, icon: const Icon(Icons.alternate_email_rounded, size: 18),
            label: const Text('Domain par email (Google / Zoho)')),
        for (final p in _list(h['dns']).take(5))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('${p['domain']} · ${p['purpose']}', style: const TextStyle(fontSize: 13)),
            subtitle: Text('${p['status']} · ${p['todo']} badlav', style: const TextStyle(fontSize: 11.5, color: C.muted)),
            onTap: () => _showPlan(p),
            trailing: Wrap(children: [
              IconButton(tooltip: 'Jaancho', icon: const Icon(Icons.travel_explore_rounded, size: 20),
                  onPressed: () => _run(() => widget.app.api!.siteDnsCheck(_s(p['id'])))),
              if (p['status'] == 'applied')
                IconButton(tooltip: 'Wapas karo', icon: const Icon(Icons.undo_rounded, size: 20),
                    onPressed: () => _run(() => widget.app.api!.siteDns(_s(p['id']), 'undo', {}))),
            ]),
          ),
      ]),
    );
  }

  Future<void> _takedown() async {
    final yes = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
          title: const Text('Website band karein?'),
          content: const Text('Live address par site dikhna band ho jayega. Versions aur preview rahenge.'),
          actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Nahi')),
            TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Haan, band karo'))]));
    if (yes == true) _run(() => widget.app.api!.siteAct(widget.siteId, 'takedown', {}));
  }

  Future<void> _addKey() async {
    final t = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
          title: const Text('Cloudflare token'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Cloudflare > My Profile > API Tokens > "Edit zone DNS" template, sirf apna domain chuniye. '
                'Token yahin daaliye (chat mein kabhi nahi). Hoola ise tala-band rakhega.', style: TextStyle(fontSize: 12.5)),
            TextField(controller: t, obscureText: true, autocorrect: false, enableSuggestions: false,
                decoration: const InputDecoration(labelText: 'API token')),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo'))]));
    if (ok == true && t.text.trim().isNotEmpty) {
      await _run(() => widget.app.api!.siteKeySet('cloudflare', {'token': t.text.trim()}));
    }
  }

  Future<void> _forgetKey() => _run(() => widget.app.api!.siteKeyForget('cloudflare'));

  Future<void> _email() async {
    final d = TextEditingController(text: _domain.text.trim());
    final to = TextEditingController();
    String provider = 'google';
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(builder: (c, set) => AlertDialog(
          title: const Text('Domain par email'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: d, decoration: const InputDecoration(labelText: 'Domain')),
            Wrap(spacing: 6, children: [
              ChoiceChip(label: const Text('Google Workspace'), selected: provider == 'google', onSelected: (_) => set(() => provider = 'google')),
              ChoiceChip(label: const Text('Zoho Mail'), selected: provider == 'zoho', onSelected: (_) => set(() => provider = 'zoho')),
            ]),
            TextField(controller: to, decoration: const InputDecoration(labelText: 'Report kis email par (optional)')),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Plan banao'))])));
    if (ok == true && d.text.trim().isNotEmpty) {
      try {
        final plan = await widget.app.api!.siteAct(widget.siteId, 'email-dns',
            {'domain': d.text.trim(), 'provider': provider, 'report_to': to.text.trim()});
        await _load();
        if (mounted) _showPlan(plan);
      } catch (e) {
        if (mounted) _snack(context, '$e');
      }
    }
  }

  void _showPlan(Map<String, dynamic> plan) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (c) => SafeArea(child: SingleChildScrollView(padding: const EdgeInsets.all(12),
          child: SiteDnsCard(app: widget.app, v: {'plan': plan, 'say': '${plan['todo']} DNS badlav, aapki haan se.'}))),
    );
  }
}


// ---------------------------------------------------------------- v0.123 domains: ideas, rupee prices, her fingerprint tap
/// Card for a domain: 'domain' = waiting her fingerprint (Haan / Nahi), 'domain_done' = bought / registering,
/// 'domain_reminder' = .in KYC or renewal ("KYC ho gaya" when it is the KYC one).
class SiteDomainCard extends StatefulWidget {
  const SiteDomainCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<SiteDomainCard> createState() => _SiteDomainCardState();
}

class _SiteDomainCardState extends State<SiteDomainCard> {
  bool _busy = false;
  String _done = '';

  Future<void> _go(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted) setState(() => _done = _s(r['say']).isEmpty ? 'Ho gaya.' : _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final kind = _s(v['kind']);
    if (kind != 'domain') {
      final kyc = kind == 'domain_reminder' && _s(v['say']).contains('KYC');
      return Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(kind == 'domain_done' ? Icons.verified_rounded : Icons.notifications_active_rounded,
                color: kind == 'domain_done' ? C.ok : C.warn),
            const SizedBox(width: 10),
            Expanded(child: Text(_done.isNotEmpty ? _done : _s(v['say']), style: const TextStyle(fontSize: 13.5))),
          ]),
          if (kyc && _done.isEmpty)
            Align(alignment: Alignment.centerRight, child: TextButton(
                onPressed: _busy ? null : () => _go(() => widget.app.api!.siteDomainKyc(_s(v['domain']))),
                child: const Text('KYC ho gaya'))),
        ]),
      );
    }
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.language_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_s(v['title']), style: display(15))),
          Text(_s(v['amount']), style: display(16)),
        ]),
        const SizedBox(height: 6),
        for (final l in ((v['lines'] as List?) ?? const []))
          Padding(padding: const EdgeInsets.only(bottom: 3),
              child: Text('• $l', style: const TextStyle(fontSize: 12.5, color: C.muted))),
        const SizedBox(height: 8),
        if (_done.isNotEmpty)
          Text(_done, style: const TextStyle(fontSize: 13))
        else
          Row(children: [
            TextButton(onPressed: _busy ? null : () => _go(() => widget.app.api!.siteDomainCancel(_s(v['id']))),
                child: const Text('Nahi')),
            const Spacer(),
            GlassButton(label: 'Haan, le lo', icon: Icons.fingerprint_rounded, color: C.accent, height: 40,
                onTap: _busy ? null : () => _go(() => widget.app.api!.siteDomainBuy(_s(v['id']), _s(v['hash'])))),
          ]),
      ]),
    );
  }
}

/// Domain chooser: her registrar accounts (keys typed only here), ideas with first-year + renewal price, own name check,
/// "Yeh lo" = the fingerprint card (nothing is bought from this sheet).
Future<void> showDomainSheet(BuildContext context, Santosh app, String siteId) async {
  await showModalBottomSheet(context: context, isScrollControlled: true, useSafeArea: true,
      builder: (c) => Padding(padding: EdgeInsets.only(bottom: MediaQuery.of(c).viewInsets.bottom),
          child: _DomainSheet(app: app, siteId: siteId)));
}

class _DomainSheet extends StatefulWidget {
  const _DomainSheet({required this.app, required this.siteId});
  final Santosh app;
  final String siteId;
  @override
  State<_DomainSheet> createState() => _DomainSheetState();
}

class _DomainSheetState extends State<_DomainSheet> {
  Map<String, dynamic>? _info;
  List<Map<String, dynamic>> _ideas = [];
  String _say = '';
  bool _busy = false;
  bool _renew = false;
  final _own = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final i = await widget.app.api!.siteDomains();
      if (mounted) setState(() => _info = i);
    } catch (_) {}
  }

  Future<void> _go(Future<void> Function() f) async {
    setState(() => _busy = true);
    try {
      await f();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  bool get _hasAccount => _list(_info?['keys']).any((k) => k['provider'] == 'porkbun' || k['provider'] == 'cf_registrar');

  Future<void> _addAccount(String provider) async {
    final a = TextEditingController(), b = TextEditingController();
    final cf = provider == 'cf_registrar';
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
          title: Text(cf ? 'Cloudflare Registrar' : 'Porkbun'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(cf ? 'Cloudflare > My Profile > API Tokens: Registrar permission wala token, aur Account ID (dashboard mein). '
                    '.com / .shop / .store jaise domain; .in nahi.'
                : 'porkbun.com > Account > API Access: API key + Secret key; domain par "API access" chalu kijiye. .in bhi milta hai.',
                style: const TextStyle(fontSize: 12.5)),
            TextField(controller: a, obscureText: true, autocorrect: false, enableSuggestions: false,
                decoration: InputDecoration(labelText: cf ? 'API token' : 'API key')),
            TextField(controller: b, obscureText: !cf, autocorrect: false, enableSuggestions: false,
                decoration: InputDecoration(labelText: cf ? 'Account ID' : 'Secret API key')),
            const SizedBox(height: 6),
            const Text('Sirf yahan daaliye, chat mein kabhi nahi. Hoola tala-band rakhta hai aur kabhi nahi dikhata.',
                style: TextStyle(fontSize: 11.5, color: C.faint)),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Jodo'))]));
    if (ok == true && a.text.trim().isNotEmpty) {
      await _go(() async {
        final r = await widget.app.api!.siteKeySet(provider, {'token': a.text.trim(), 'secret': b.text.trim()});
        if (mounted) _snack(context, _s(r['say']));
        await _load();
      });
    }
  }

  Future<void> _ideasNow() => _go(() async {
        final r = await widget.app.api!.siteDomainIdeas(widget.siteId);
        if (mounted) setState(() {
          _ideas = _list(r['ideas']);
          _say = _s(r['say']);
        });
      });

  Future<void> _check() => _go(() async {
        final d = _own.text.trim();
        if (d.isEmpty) return;
        final r = await widget.app.api!.siteDomainCheck([d]);
        final res = _list(r['results']);
        if (mounted) setState(() {
          _ideas = res.where((x) => x['available'] == true).toList();
          _say = res.isEmpty ? 'Yeh naam check nahi ho paya.' : res.map((x) => x['available'] == true
              ? '${x['domain']}: khaali, ₹${x['inr']} (phir ₹${x['renew_inr']}/saal)' : '${x['domain']}: khaali nahi').join('\n');
        });
      });

  Future<void> _take(String d) => _go(() async {
        final r = await widget.app.api!.siteDomainRequest(widget.siteId, d, autoRenew: _renew);
        if (mounted) {
          Navigator.pop(context);
          _snack(context, _s(r['say']));
        }
      });

  @override
  Widget build(BuildContext context) {
    final keys = _list(_info?['keys']);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text('Naya domain', style: display(18)),
        const SizedBox(height: 4),
        Text('Domain aapke naam par, aapke account mein. Is mahine: ₹${_info?['month_spent_inr'] ?? 0} / ₹${_info?['month_limit_inr'] ?? ''}',
            style: const TextStyle(fontSize: 12, color: C.muted)),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final p in const ['porkbun', 'cf_registrar'])
            ActionChip(
              avatar: Icon(keys.any((k) => k['provider'] == p) ? Icons.check_circle_rounded : Icons.add_rounded, size: 18,
                  color: keys.any((k) => k['provider'] == p) ? C.ok : null),
              label: Text(p == 'porkbun' ? 'Porkbun (.in, .com...)' : 'Cloudflare Registrar (.com...)'),
              onPressed: _busy ? null : () => _addAccount(p),
            ),
        ]),
        if (_info != null && !_hasAccount)
          const Padding(padding: EdgeInsets.only(top: 8), child: Text(
              'Daam dekhne aur lene ke liye pehle ek registrar account jodiye (domain usi account mein aapke naam par rahega).',
              style: TextStyle(fontSize: 12.5))),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: GlassButton(label: 'Mere business ke naam', icon: Icons.auto_awesome_rounded, height: 40,
              onTap: _busy || !_hasAccount ? null : _ideasNow)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: TextField(controller: _own, decoration: const InputDecoration(hintText: 'apna naam: sharmasweets.in'))),
          TextButton(onPressed: _busy || !_hasAccount ? null : _check, child: const Text('Dekho')),
        ]),
        if (_busy) const Padding(padding: EdgeInsets.all(12), child: Center(child: CircularProgressIndicator())),
        if (_say.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8),
            child: Text(_say, style: const TextStyle(fontSize: 12.5, color: C.muted))),
        for (final x in _ideas)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_s(x['domain']), style: display(15)),
            subtitle: Text('Pehla saal ₹${x['inr']} · phir ₹${x['renew_inr']}/saal'
                '${x['renew_jump'] == true ? ' (renew mehenga!)' : ''}${x['kyc'] == true ? ' · .in KYC aapko karni hogi' : ''}',
                style: const TextStyle(fontSize: 12)),
            trailing: TextButton(onPressed: _busy ? null : () => _take(_s(x['domain'])), child: const Text('Yeh lo')),
          ),
        SwitchListTile(contentPadding: EdgeInsets.zero, value: _renew, onChanged: (b) => setState(() => _renew = b),
            title: const Text('Har saal apne aap renew', style: TextStyle(fontSize: 13)),
            subtitle: const Text('Band rahe to Hoola 60 / 30 / 7 / 1 din pehle yaad dilayega.', style: TextStyle(fontSize: 11.5))),
        const Text('"Yeh lo" sirf card bhejta hai; domain tab hi liya jayega jab aap card par fingerprint se haan karengi. '
            'Domain ka paisa wapas nahi hota.', style: TextStyle(fontSize: 11.5, color: C.faint)),
      ])),
    );
  }
}

// ---------------------------------------------------------------- v0.124 care (visits, enquiries, uptime, tips), agency, GitHub
class SiteCareCard extends StatelessWidget {
  const SiteCareCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  Widget build(BuildContext context) {
    final site = _map(v['site']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.insights_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${_s(site['name'])} · ${_s(v['month'])}', style: display(15))),
        ]),
        const SizedBox(height: 6),
        Wrap(spacing: 14, runSpacing: 6, children: [
          _stat('Visit', _s(v['views']), _s(v['views_prev'])),
          _stat('Enquiry', _s(v['leads']), _s(v['leads_prev'])),
          if (v['uptime_pct'] != null) _stat('Chalu rahi', '${v['uptime_pct']}%', ''),
        ]),
        for (final t in ((v['tips'] as List?) ?? const []))
          Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $t', style: const TextStyle(fontSize: 12.5, color: C.muted))),
      ]),
    );
  }
}

Widget _stat(String label, String value, String prev) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(value, style: display(18)),
      Text(prev.isEmpty ? label : '$label (pehle $prev)', style: const TextStyle(fontSize: 11.5, color: C.faint)),
    ]);

class SiteGithubCard extends StatefulWidget {
  const SiteGithubCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<SiteGithubCard> createState() => _SiteGithubCardState();
}

class _SiteGithubCardState extends State<SiteGithubCard> {
  bool _busy = false;
  String _done = '';

  Future<void> _go(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted) setState(() => _done = _s(r['say']).isEmpty ? 'Ho gaya.' : _s(r['say']));
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final card = _s(v['kind']) == 'github';
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.code_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_done.isNotEmpty ? _done : _s(v['say']), style: const TextStyle(fontSize: 13.5))),
          if (!card && _s(v['url']).isNotEmpty)
            IconButton(icon: const Icon(Icons.open_in_new_rounded), onPressed: () => _open(_s(v['url']))),
        ]),
        if (card && _done.isEmpty)
          Row(children: [
            Text('${v['files']} files · ${v['size_kb']} KB', style: const TextStyle(fontSize: 12, color: C.faint)),
            const Spacer(),
            TextButton(onPressed: _busy ? null : () => _go(() => widget.app.api!.siteGithubCancel(_s(v['id']))),
                child: const Text('Nahi')),
            GlassButton(label: 'Haan, daalo', icon: Icons.upload_rounded, color: C.accent, height: 40,
                onTap: _busy ? null : () => _go(() => widget.app.api!.siteGithubPush(_s(v['id']), _s(v['hash'])))),
          ]),
      ]),
    );
  }
}

/// On the site page after hosting: the last 30 days, what to improve, client / staff (agency), GitHub export.
class SiteCarePanel extends StatefulWidget {
  const SiteCarePanel({super.key, required this.app, required this.siteId});
  final Santosh app;
  final String siteId;
  @override
  State<SiteCarePanel> createState() => _SiteCarePanelState();
}

class _SiteCarePanelState extends State<SiteCarePanel> {
  Map<String, dynamic>? _r;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await widget.app.api!.siteCare(widget.siteId);
      if (mounted) setState(() => _r = r);
    } catch (_) {}
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() f) async {
    setState(() => _busy = true);
    try {
      final r = await f();
      if (mounted && _s(r['say']).isNotEmpty) _snack(context, _s(r['say']));
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _ask(String title, String hint, {String initial = ''}) async {
    final t = TextEditingController(text: initial);
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
          title: Text(title),
          content: TextField(controller: t, decoration: InputDecoration(hintText: hint)),
          actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Theek'))]));
    return ok == true ? t.text.trim() : null;
  }

  Future<void> _github() async {
    final t = TextEditingController();
    bool private = true;
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(builder: (c, set) => AlertDialog(
          title: const Text('GitHub mein daalo'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Pehli baar: GitHub > Settings > Developer settings > Fine-grained token (Contents + Administration: write). '
                'Token sirf yahan, chat mein kabhi nahi.', style: TextStyle(fontSize: 12)),
            TextField(controller: t, obscureText: true, autocorrect: false, enableSuggestions: false,
                decoration: const InputDecoration(labelText: 'GitHub token (agar pehle se juda hai to khaali chhodiye)')),
            SwitchListTile(contentPadding: EdgeInsets.zero, value: private, onChanged: (b) => set(() => private = b),
                title: const Text('Private repo', style: TextStyle(fontSize: 13))),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Card banao'))])));
    if (ok != true) return;
    await _run(() async {
      if (t.text.trim().isNotEmpty) await widget.app.api!.siteKeySet('github', {'token': t.text.trim()});
      return widget.app.api!.siteGithubRequest(widget.siteId, private: private);
    });
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final site = _map(r?['site']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [Text('Dekh-bhaal (30 din)', style: display(16)), const Spacer(),
          IconButton(icon: const Icon(Icons.refresh_rounded, size: 20), onPressed: _load)]),
        if (r == null)
          const Text('...', style: TextStyle(color: C.faint))
        else ...[
          Wrap(spacing: 14, runSpacing: 6, children: [
            _stat('Visit', _s(r['views']), _s(r['views_prev'])),
            _stat('Enquiry', _s(r['leads']), _s(r['leads_prev'])),
            if (r['uptime_pct'] != null) _stat('Chalu rahi', '${r['uptime_pct']}%', ''),
          ]),
          for (final p in ((r['top_pages'] as List?) ?? const []).take(4))
            Text('${(p as List)[0]} · ${p[1]}', style: const TextStyle(fontSize: 12, color: C.muted)),
          for (final t in ((r['tips'] as List?) ?? const []))
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $t', style: const TextStyle(fontSize: 12.5))),
          const SizedBox(height: 4),
          const Text('Visit hum khud ginte hain: na cookie, na IP, na koi tracker.', style: TextStyle(fontSize: 11, color: C.faint)),
        ],
        const Divider(height: 22),
        Wrap(spacing: 8, runSpacing: 6, children: [
          ActionChip(avatar: const Icon(Icons.business_center_rounded, size: 18),
              label: Text(_s(site['client']).isEmpty ? 'Client batao' : 'Client: ${site['client']}'),
              onPressed: _busy ? null : () async {
                final c = await _ask('Kis client ki website?', 'Sharma ji', initial: _s(site['client']));
                if (c != null) _run(() => widget.app.api!.siteAssign(widget.siteId, client: c));
              }),
          ActionChip(avatar: const Icon(Icons.badge_rounded, size: 18), label: const Text('Staff ko do'),
              onPressed: _busy ? null : () async {
                final c = await _ask('Kaun staff is par kaam karega? (Team ka id, khaali = sirf aap)', 'asha');
                if (c != null) _run(() => widget.app.api!.siteAssign(widget.siteId, staff: c));
              }),
          ActionChip(avatar: const Icon(Icons.code_rounded, size: 18), label: const Text('GitHub mein daalo'),
              onPressed: _busy ? null : _github),
        ]),
      ]),
    );
  }
}
