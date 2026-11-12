import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';
import 'desk/desk_kit.dart';

Future<void> _open(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication).catchError((_) => false);
}

/// A Google Sheet Santosh created / changed, shown in the chat with an Open button.
class SheetCard extends StatelessWidget {
  const SheetCard({super.key, required this.v});
  final Map<String, dynamic> v;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'created';
    final chip = switch (status) {
      'created' => 'NEW SHEET',
      'deleted' => 'ROWS DELETED',
      'updated' => 'CHANGED',
      'shared' => 'SHARED',
      _ => status.toUpperCase(),
    };
    final tabs = (v['tabs'] as List? ?? const []).map((e) => '$e').toList();
    final link = v['link'] as String? ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.table_chart_rounded, color: C.ok, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(v['title'] as String? ?? 'Google Sheet', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(chip, fg: C.ok),
          ]),
          if (tabs.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('Tabs: ${tabs.join(', ')}', style: const TextStyle(color: C.muted, fontSize: 12.5))),
          if (link.isNotEmpty) ...[
            const SizedBox(height: 10),
            GlassButton(label: 'Open sheet', icon: Icons.open_in_new_rounded, height: 42, onTap: () => _open(link)),
          ],
        ]),
      ),
    );
  }
}

/// Profile > Google Sheets: connect a Google account for Sheets; see the sheets Santosh used recently.
class SheetsScreen extends StatefulWidget {
  const SheetsScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SheetsScreen> createState() => _SheetsScreenState();
}

class _SheetsScreenState extends State<SheetsScreen> {
  Map<String, dynamic> _st = {};
  bool _loaded = false;
  String? _err;
  int _seen = 0;

  Santosh get app => widget.app;
  List<Map<String, dynamic>> _list(String k) =>
      List<Map<String, dynamic>>.from((_st[k] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));

  @override
  void initState() {
    super.initState();
    _seen = app.sheetsLinkedTick;
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    super.dispose();
  }

  void _onApp() {
    if (app.sheetsLinkedTick != _seen) {
      _seen = app.sheetsLinkedTick;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final r = await app.api!.sheetsState();
      if (mounted) setState(() { _st = r; _loaded = true; _err = null; });
    } catch (e) {
      if (mounted) setState(() { _err = e.toString(); _loaded = true; });
    }
  }

  Future<void> _link() async {
    try {
      await _open(await app.api!.sheetsLinkUrl());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _remove(String key) async {
    try {
      final r = await app.api!.sheetsRemove(key);
      if (mounted) setState(() => _st = r);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final accounts = _list('accounts');
    final recent = _list('recent');
    final canLink = _st['can_link'] == true;
    final onlyService = accounts.isNotEmpty && accounts.every((a) => a['kind'] == 'service');
    return DeskPage(
      title: 'Google Sheets',
      onRefresh: _load,
      body: () => RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 32), children: [
            const Text('Hoola finds your Google Sheets by name, reads them, does the right sums (total, filter, group), adds and changes rows,'
                'makes new sheets, imports Excel and sends files. Deleting rows, changing more than 20'
                'rows and sharing go only after your tap.',
                style: TextStyle(color: C.muted, fontSize: 13)),
            const SizedBox(height: 14),
            if (_err != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_err!, style: const TextStyle(color: C.bad))),
            if (!_loaded) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator())),
            for (final a in accounts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Glass(child: Row(children: [
                  const Icon(Icons.table_chart_rounded, color: C.ok),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a['address'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(a['kind'] == 'service' ? 'Server service account: only shared sheets' : 'Google account',
                        style: const TextStyle(color: C.muted, fontSize: 12.5)),
                    if (a['status'] == 'error') Text(a['error'] as String? ?? 'Login fail', style: const TextStyle(color: C.bad, fontSize: 12)),
                  ])),
                  if (a['removable'] == true)
                    IconButton(icon: const Icon(Icons.close_rounded, color: C.muted), onPressed: () => _remove(a['key'] as String)),
                ])),
              ),
            if (_loaded && (accounts.isEmpty || onlyService)) ...[
              GradientButton(label: 'Link Google Sheets', icon: Icons.table_chart_rounded, height: 50, onTap: canLink ? _link : null),
              if (!canLink)
                const Padding(padding: EdgeInsets.only(top: 8),
                    child: Text('Google sign-in is not on yet on this server.', style: TextStyle(color: C.faint, fontSize: 12))),
            ] else if (_loaded)
              GlassButton(label: 'Link another Google account', icon: Icons.add_rounded, height: 44, onTap: canLink ? _link : null),
            if (recent.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Text('Recent sheets', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Glass(child: Column(children: [
                for (final r in recent)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.grid_on_rounded, color: C.chip),
                    title: Text(r['title'] as String? ?? ''),
                    subtitle: Text('${r['used'] ?? ''}', style: const TextStyle(color: C.muted, fontSize: 12)),
                    onTap: () => _open('https://docs.google.com/spreadsheets/d/${r['id']}/edit'),
                  ),
              ])),
            ],
            const SizedBox(height: 18),
            const Text('Try by voice', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final t in const [
              '"In the sales sheet, how many Pune customers have a due above 1000?"',
              '"Tell me the total sales of each salesman"',
              '"Mark Sharma Traders as Paid"',
              '"Add today\'s entry: Kale Agencies, Akola, 650"',
              '"Make this Excel a Google Sheet"',
              '"Make the October sheet an Excel and mail it to the CA"',
            ])
              Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text(t, style: const TextStyle(color: C.chip, fontSize: 13))),
          ]),
        ),
    );
  }
}
