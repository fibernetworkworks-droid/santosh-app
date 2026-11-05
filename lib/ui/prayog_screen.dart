/// Profile > Prayogshala (v0.415, L0 + L1): real practical labs in 3D. The list comes from /api/prayog/labs; a lab opens
/// in a WebView (three.js runs on the phone, works offline after the first open). Every reading in a lab comes from
/// its simulation code, checked against the NCERT formula on the server.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};

class PrayogScreen extends StatefulWidget {
  const PrayogScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<PrayogScreen> createState() => _PrayogScreenState();
}

class _PrayogScreenState extends State<PrayogScreen> {
  List<Map<String, dynamic>>? _labs;     // one row per set-up (its variants open from it)
  List<Map<String, dynamic>>? _hits;     // server search over every experiment, variants included
  int _total = 0;
  String _err = '';
  String _q = '';
  int _ask = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await widget.app.api!.call('GET', '/api/prayog/labs?variants=false&limit=200'));
      if (mounted) setState(() => _labs = _list(d['labs']));
    } catch (e) {
      if (mounted) setState(() => _err = 'Labs did not load: $e');
    }
  }

  Future<void> _search(String v) async {
    final q = v.trim();
    final my = ++_ask;
    setState(() => _q = q);
    if (q.isEmpty) {
      setState(() => _hits = null);
      return;
    }
    try {
      final d = _map(await widget.app.api!.call('GET', '/api/prayog/labs?limit=60&q=${Uri.encodeComponent(q)}'));
      if (mounted && my == _ask) {
        setState(() {
          _hits = _list(d['labs']);
          _total = (d['total'] as num?)?.toInt() ?? 0;
        });
      }
    } catch (e) {
      if (mounted && my == _ask) setState(() => _err = 'Search failed: $e');
    }
  }

  void _open(Map<String, dynamic> lab) {
    final url = widget.app.api!.absolute('/static/prayog/lab.html?id=${Uri.encodeComponent(_s(lab['id']))}');
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => PrayogLabView(url: url, title: _s(lab['title']), token: widget.app.api!.apiKey)));
  }

  void _family(Map<String, dynamic> lab) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => _PrayogFamily(app: widget.app, base: lab, open: _open)));
  }

  Widget _tile(Map<String, dynamic> l, {bool family = true}) {
    final n = (l['n_variants'] as num?)?.toInt() ?? 0;
    final sample = _s(l['sample']);
    final sub = [_s(l['level']), if (sample.isNotEmpty) sample, if (family && n > 0) '${n + 1} experiments', _s(l['aim'])]
        .where((x) => x.isNotEmpty)
        .join(' · ');
    return Card(
      child: ListTile(
        leading: const Icon(Icons.science_outlined, color: C.accent),
        title: Text(_s(l['title']), style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap: () => family && n > 0 ? _family(l) : _open(l),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rows = _q.isEmpty ? (_labs ?? const <Map<String, dynamic>>[]) : (_hits ?? const <Map<String, dynamic>>[]);
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final l in rows) {
      groups.putIfAbsent(_q.isEmpty ? _s(l['group']) : 'Results', () => []).add(l);
    }
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} · Prayogshala')),
      body: _labs == null && _err.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Text('Real practicals in 3D: turn the knobs, read the meters, fill the table. Every reading comes from simulation code '
                  'and is checked against the textbook formula.',
                  style: const TextStyle(color: C.muted, fontSize: 13.5)),
              const SizedBox(height: 12),
              TextField(
                decoration: const InputDecoration(hintText: 'Search experiments: pendulum, copper wire, lens…', prefixIcon: Icon(Icons.search_rounded)),
                onChanged: _search,
              ),
              if (_err.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 16), child: Text(_err, style: const TextStyle(color: C.bad))),
              if (_q.isNotEmpty && _hits != null)
                Padding(padding: const EdgeInsets.only(top: 12), child: Text('$_total found', style: const TextStyle(color: C.faint))),
              for (final g in groups.keys) ...[
                Padding(
                  padding: const EdgeInsets.only(top: 18, bottom: 6),
                  child: Text(g, style: const TextStyle(color: C.faint, fontWeight: FontWeight.w600)),
                ),
                for (final l in groups[g]!) _tile(l, family: _q.isEmpty),
              ],
              if (rows.isEmpty && (_q.isEmpty ? _labs != null : _hits != null))
                const Padding(padding: EdgeInsets.only(top: 16), child: Text('No experiment found.', style: TextStyle(color: C.muted))),
            ]),
    );
  }
}

/// One set-up and all its experiments (other samples, methods, unknowns).
class _PrayogFamily extends StatefulWidget {
  const _PrayogFamily({required this.app, required this.base, required this.open});
  final Santosh app;
  final Map<String, dynamic> base;
  final void Function(Map<String, dynamic>) open;
  @override
  State<_PrayogFamily> createState() => _PrayogFamilyState();
}

class _PrayogFamilyState extends State<_PrayogFamily> {
  List<Map<String, dynamic>>? _rows;
  String _err = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final id = Uri.encodeComponent(_s(widget.base['id']));
      final d = _map(await widget.app.api!.call('GET', '/api/prayog/labs?limit=200&base=$id'));
      if (mounted) setState(() => _rows = _list(d['labs']));
    } catch (e) {
      if (mounted) setState(() => _err = 'Experiments did not load: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_s(widget.base['title']))),
      body: _rows == null && _err.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              if (_err.isNotEmpty) Text(_err, style: const TextStyle(color: C.bad)),
              for (final l in _rows ?? const <Map<String, dynamic>>[])
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.science_outlined, color: C.accent),
                    title: Text(_s(l['title']), style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text([_s(l['level']), _s(l['sample'])].where((x) => x.isNotEmpty).join(' · '),
                        maxLines: 2, overflow: TextOverflow.ellipsis),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => widget.open(l),
                  ),
                ),
            ]),
    );
  }
}

/// One lab, full screen. Links that leave the Prayogshala open in the browser.
class PrayogLabView extends StatefulWidget {
  const PrayogLabView({super.key, required this.url, required this.title, this.token = ''});
  final String url;
  final String title;
  final String token;   // lets Ask Hoola inside the lab answer as this user (our own page, our own origin)
  @override
  State<PrayogLabView> createState() => _PrayogLabViewState();
}

class _PrayogLabViewState extends State<PrayogLabView> {
  late final WebViewController _web;
  int _progress = 0;

  @override
  void initState() {
    super.initState();
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(onPageFinished: (_) {
        if (widget.token.isNotEmpty) _web.runJavaScript('window.HOOLA_TOKEN = ${jsonEncode(widget.token)};');
      }, onProgress: (p) {
        if (mounted) setState(() => _progress = p);
      }, onNavigationRequest: (r) {
        if (!r.url.contains('/static/prayog/') && !r.url.startsWith('blob:')) {
          launchUrl(Uri.parse(r.url), mode: LaunchMode.externalApplication);
          return NavigationDecision.prevent;
        }
        return NavigationDecision.navigate;
      }))
      ..loadRequest(Uri.parse(widget.url));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title.isEmpty ? 'Prayogshala' : widget.title), actions: [
          IconButton(tooltip: 'Reload', icon: const Icon(Icons.refresh_rounded), onPressed: () => _web.reload()),
        ]),
        body: Stack(children: [
          WebViewWidget(controller: _web),
          if (_progress < 100) LinearProgressIndicator(value: _progress / 100, minHeight: 2, color: C.teal),
        ]),
      );
}
