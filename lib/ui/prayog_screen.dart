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
  List<Map<String, dynamic>>? _labs;
  String _err = '';
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await widget.app.api!.call('GET', '/api/prayog/labs'));
      if (mounted) setState(() => _labs = _list(d['labs']));
    } catch (e) {
      if (mounted) setState(() => _err = 'Labs did not load: $e');
    }
  }

  void _open(Map<String, dynamic> lab) {
    final url = widget.app.api!.absolute('/static/prayog/lab.html?id=${Uri.encodeComponent(_s(lab['id']))}');
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => PrayogLabView(url: url, title: _s(lab['title']), token: widget.app.api!.apiKey)));
  }

  @override
  Widget build(BuildContext context) {
    final q = _q.toLowerCase();
    final labs = (_labs ?? const <Map<String, dynamic>>[])
        .where((l) => q.isEmpty || '${l['title']} ${l['topic']} ${l['group']} ${l['level']}'.toLowerCase().contains(q))
        .toList();
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final l in labs) {
      groups.putIfAbsent(_s(l['group']), () => []).add(l);
    }
    return Scaffold(
      appBar: AppBar(title: Text('${widget.app.aName} · Prayogshala')),
      body: _labs == null && _err.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Text('Real practicals in 3D: turn the knobs, read the meters, fill the table. Every reading comes from simulation code '
                  'and is checked against the NCERT formula to within 1%.',
                  style: const TextStyle(color: C.muted, fontSize: 13.5)),
              const SizedBox(height: 12),
              TextField(
                decoration: const InputDecoration(hintText: 'Search labs: pendulum, lens, Ohm…', prefixIcon: Icon(Icons.search_rounded)),
                onChanged: (v) => setState(() => _q = v.trim()),
              ),
              if (_err.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 16), child: Text(_err, style: const TextStyle(color: C.bad))),
              for (final g in groups.keys) ...[
                Padding(
                  padding: const EdgeInsets.only(top: 18, bottom: 6),
                  child: Text(g, style: const TextStyle(color: C.faint, fontWeight: FontWeight.w600)),
                ),
                for (final l in groups[g]!)
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.science_outlined, color: C.accent),
                      title: Text(_s(l['title']), style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text('${_s(l['level'])} · ${_s(l['aim'])}', maxLines: 2, overflow: TextOverflow.ellipsis),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => _open(l),
                    ),
                  ),
              ],
              if (_labs != null && labs.isEmpty)
                const Padding(padding: EdgeInsets.only(top: 16), child: Text('No lab found.', style: TextStyle(color: C.muted))),
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
