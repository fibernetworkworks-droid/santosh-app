// v0.999.46 CA PRACTICE on the phone (approved phone board): the GST & Accounts employee's practice side for a CA -
// her clients with this month's state, one client's folder (month -> kind -> files), the document inbox of files
// Hoola could not file by itself, and "Scan a bill" straight from the camera / a file into a client's folder.
// Same /api/practice routes as the console's Accounts > CA practice. Hoola files nothing she has not confirmed in
// the inbox; a file whose client is unclear waits there.
import 'dart:async';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

import '../native.dart';
import '../state.dart';
import 'employees_screen.dart' show callAccountsDesk;
import 'hoola_theme.dart';

String _s(Object? v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _maps(Object? v) =>
    v is List ? [for (final e in v) if (e is Map) Map<String, dynamic>.from(e)] : <Map<String, dynamic>>[];
Map<String, dynamic> _map(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
int _int(Object? v) => v is num ? v.toInt() : int.tryParse(_s(v)) ?? 0;

void _say(BuildContext context, String text) {
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
}

const _monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
    'November', 'December'];

/// "2026-10" -> "October 2026"; anything else is shown as it is.
String caMonthLabel(String m) {
  final r = RegExp(r'^(\d{4})-(\d{1,2})').firstMatch(m);
  if (r == null) return m.isEmpty ? 'No month' : m;
  final n = int.parse(r.group(2)!);
  if (n < 1 || n > 12) return m;
  return '${_monthNames[n - 1]} ${r.group(1)}';
}

/// 1234567.5 -> "₹12,34,568" (Indian grouping, whole rupees).
String caRupees(Object? v) {
  final n = v is num ? v : num.tryParse(_s(v).replaceAll(',', ''));
  if (n == null) return '';
  final whole = n.round().abs().toString();
  String out;
  if (whole.length <= 3) {
    out = whole;
  } else {
    final last = whole.substring(whole.length - 3);
    var rest = whole.substring(0, whole.length - 3);
    final parts = <String>[];
    while (rest.length > 2) {
      parts.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) parts.insert(0, rest);
    out = '${parts.join(',')},$last';
  }
  return '${n < 0 ? '-' : ''}₹$out';
}

/// The right-hand state of a client row: Complete / N missing / Nothing yet.
String caClientState(Map<String, dynamic> cl) {
  if (cl['complete'] == true) return 'Complete';
  final missing = cl['missing'] is List ? (cl['missing'] as List).length : 0;
  if (_int(cl['files_month']) == 0 && cl['last'] == null) return 'Nothing yet';
  if (missing > 0) return '$missing missing';
  return 'Nothing yet';
}

String _channelLabel(String ch) => switch (ch) {
      'phone' => 'Phone',
      'whatsapp' => 'WhatsApp',
      'email' => 'Email',
      'drive' => 'Drive',
      'pc' => 'PC',
      'console' => 'Console',
      _ => ch.isEmpty ? '' : '${ch[0].toUpperCase()}${ch.substring(1)}',
    };

String _mimeOf(String name) {
  final n = name.toLowerCase();
  if (n.endsWith('.pdf')) return 'application/pdf';
  if (n.endsWith('.jpg') || n.endsWith('.jpeg')) return 'image/jpeg';
  if (n.endsWith('.png')) return 'image/png';
  if (n.endsWith('.webp')) return 'image/webp';
  if (n.endsWith('.xlsx')) return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  if (n.endsWith('.xls')) return 'application/vnd.ms-excel';
  if (n.endsWith('.csv')) return 'text/csv';
  if (n.endsWith('.docx')) return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  if (n.endsWith('.txt')) return 'text/plain';
  if (n.endsWith('.json')) return 'application/json';
  if (n.endsWith('.zip')) return 'application/zip';
  return '*/*';
}

/// Test hooks: when set, the pages read these instead of the server (like HoolaEmployees.debugList).
class CaPracticeDebug {
  static Map<String, dynamic>? home;
  static Map<String, dynamic>? clients;
  static Map<String, dynamic>? inbox;
  static Map<String, dynamic>? folder;
  static void clear() {
    home = null;
    clients = null;
    inbox = null;
    folder = null;
  }
}

Future<Map<String, dynamic>> _home(Santosh app) async =>
    CaPracticeDebug.home ?? await app.api!.practiceHome();
Future<Map<String, dynamic>> _clients(Santosh app, {String q = ''}) async =>
    CaPracticeDebug.clients ?? await app.api!.practiceClients(q: q);

// ------------------------------------------------------------------------------------------------ shared parts
class _TopBar extends StatelessWidget {
  const _TopBar({this.trailing});
  final Widget? trailing;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return SizedBox(
      height: 56,
      child: Row(children: [
        const SizedBox(width: HoolaSpace.gutter - 4),
        IconButton(
          tooltip: 'Back',
          onPressed: () => Navigator.of(context).maybePop(),
          style: IconButton.styleFrom(
            backgroundColor: c.surface,
            side: BorderSide(color: c.line),
            fixedSize: const Size.square(48),
          ),
          icon: Icon(Icons.arrow_back_ios_new_rounded, color: c.ink, size: 18),
        ),
        const Spacer(),
        if (trailing != null) trailing!,
        const SizedBox(width: HoolaSpace.gutter - 4),
      ]),
    );
  }
}

class _Title extends StatelessWidget {
  const _Title(this.title, {this.count, this.sub});
  final String title;
  final String? count;
  final String? sub;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 8, HoolaSpace.gutter + 4, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
          Flexible(
            child: Text(title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: HoolaType.pageTitle(c)),
          ),
          if (count != null) ...[
            const SizedBox(width: 10),
            Text(count!, style: HoolaType.title(c).copyWith(color: c.ink3)),
          ],
        ]),
        if (sub != null && sub!.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(sub!, style: HoolaType.small(c)),
        ],
      ]),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.child, this.onTap, this.padding = const EdgeInsets.all(HoolaSpace.s16)});
  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsets padding;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Material(
      color: c.surface,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.card), side: BorderSide(color: c.line)),
      clipBehavior: Clip.antiAlias,
      child: InkWell(onTap: onTap, child: Padding(padding: padding, child: child)),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 32, HoolaSpace.gutter + 4, 32),
      child: Text(text, textAlign: TextAlign.center, style: HoolaType.body(c).copyWith(color: c.ink2)),
    );
  }
}

class _Failed extends StatelessWidget {
  const _Failed(this.error, this.retry);
  final String error;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 32, HoolaSpace.gutter + 4, 32),
      child: Column(children: [
        Text(error, textAlign: TextAlign.center, style: HoolaType.body(c).copyWith(color: c.ink2)),
        const SizedBox(height: 12),
        OutlinedButton(
          onPressed: retry,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(120, 48),
            shape: const StadiumBorder(),
            side: BorderSide(color: c.lineStrong),
            foregroundColor: c.ink,
          ),
          child: const Text('Try again'),
        ),
      ]),
    );
  }
}

Widget _sheetHandle(HoolaColors c) => Center(
      child: Container(
        width: 36,
        height: 4,
        margin: const EdgeInsets.only(top: 10, bottom: 12),
        decoration: BoxDecoration(color: c.lineStrong, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
      ),
    );

/// The client chooser. Returns the client id, '' for "Not sure — let me file it later" (only when [later]), or null
/// when she closed the sheet.
Future<String?> caPickClient(BuildContext context, List<Map<String, dynamic>> clients,
    {bool later = true, String title = 'Which client is this for?'}) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    showDragHandle: false,
    builder: (ctx) {
      final c = HoolaColors.of(ctx);
      return SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .75),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            _sheetHandle(c),
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 0, HoolaSpace.gutter + 4, 8),
              child: Text(title, style: HoolaType.heading(c)),
            ),
            Flexible(
              child: ListView(shrinkWrap: true, children: [
                if (clients.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(HoolaSpace.gutter + 4),
                    child: Text('No clients yet. Add them on the console: Accounts > CA practice > Add client.',
                        style: HoolaType.body(c).copyWith(color: c.ink2)),
                  ),
                for (final cl in clients)
                  ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter + 4),
                    title: Text(_s(cl['name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
                    subtitle: _s(cl['gstin']).isEmpty ? null : Text(_s(cl['gstin']), style: HoolaType.small(c)),
                    onTap: () => Navigator.of(ctx).pop(_s(cl['id'])),
                  ),
              ]),
            ),
            if (later)
              Padding(
                padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 4, HoolaSpace.gutter, 12),
                child: TextButton(
                  onPressed: () => Navigator.of(ctx).pop(''),
                  style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48), foregroundColor: c.ink2),
                  child: const Text('Not sure — let me file it later'),
                ),
              ),
          ]),
        ),
      );
    },
  );
}

// ------------------------------------------------------------------------------------------------ clients
class CaClientsPage extends StatefulWidget {
  const CaClientsPage({super.key, required this.app});
  final Santosh app;
  @override
  State<CaClientsPage> createState() => _CaClientsPageState();
}

class _CaClientsPageState extends State<CaClientsPage> {
  final _q = TextEditingController();
  Timer? _wait;
  bool _loading = true;
  bool _busy = false;
  String? _error;
  Map<String, dynamic> _summary = const {};
  List<Map<String, dynamic>> _list = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _wait?.cancel();
    _q.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([_home(widget.app), _clients(widget.app, q: _q.text.trim())]);
      if (!mounted) return;
      setState(() {
        _summary = _map(r[0]['summary']);
        _list = _maps(r[1]['clients']);
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  void _search(String _) {
    _wait?.cancel();
    _wait = Timer(const Duration(milliseconds: 300), _load);
  }

  Future<void> _open(Widget page) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => HoolaTheme(appearance: widget.app.appearance, child: page)));
    if (mounted) _load();
  }

  Future<void> _scan() async {
    final c = HoolaColors.of(context);
    final how = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          _sheetHandle(c),
          for (final (key, icon, label) in const [
            ('camera', Icons.photo_camera_outlined, 'Take a photo'),
            ('photo', Icons.photo_library_outlined, 'Choose a photo'),
            ('file', Icons.description_outlined, 'Choose a file'),
          ])
            ListTile(
              leading: Icon(icon, color: c.ink2),
              title: Text(label, style: HoolaType.title(c)),
              onTap: () => Navigator.of(ctx).pop(key),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (how == null || !mounted) return;
    List<int>? bytes;
    var name = 'bill.jpg';
    try {
      if (how == 'file') {
        final res = await FilePicker.platform.pickFiles(withData: true);
        final f = res == null || res.files.isEmpty ? null : res.files.first;
        if (f == null || f.bytes == null) return;
        bytes = f.bytes!;
        name = f.name;
      } else {
        final x = await ImagePicker().pickImage(
            source: how == 'camera' ? ImageSource.camera : ImageSource.gallery, imageQuality: 85, maxWidth: 2400);
        if (x == null) return;
        bytes = await x.readAsBytes();
        name = x.name.isEmpty ? 'bill.jpg' : x.name;
      }
    } catch (e) {
      if (mounted) _say(context, 'Could not read the file: $e');
      return;
    }
    if (bytes == null || !mounted) return;
    final clientId = await caPickClient(context, _list);
    if (clientId == null || !mounted) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.practiceUpload(bytes, name, clientId: clientId.isEmpty ? null : clientId);
      final files = _maps(r['files']);
      final f = files.isEmpty ? const <String, dynamic>{} : files.first;
      if (!mounted) return;
      if (_s(f['status']) == 'filed') {
        final who = _list.where((e) => _s(e['id']) == clientId).map((e) => _s(e['name'])).firstOrNull ?? 'the client';
        _say(context, 'Filed in $who\'s folder.');
      } else {
        final why = _s(f['why']);
        _say(context, why.isEmpty ? 'It is in the document inbox.' : 'In the document inbox: $why');
      }
      await _load();
    } catch (e) {
      if (mounted) _say(context, 'Upload failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _row(BuildContext context, Map<String, dynamic> cl) {
    final c = HoolaColors.of(context);
    final state = caClientState(cl);
    final color = state == 'Complete' ? c.ok : (state.endsWith('missing') ? c.warn : c.ink3);
    final last = _map(cl['last']);
    final sub = last.isNotEmpty
        ? [_s(last['name']), _channelLabel(_s(last['channel']))].where((e) => e.isNotEmpty).join(' · ')
        : _s(cl['gstin']);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 8),
      child: _Card(
        onTap: () => _open(CaFolderPage(app: widget.app, clientId: _s(cl['id']), name: _s(cl['name']))),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_s(cl['name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
              if (sub.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
              ],
            ]),
          ),
          const SizedBox(width: 12),
          Text(state, style: HoolaType.label(c).copyWith(color: color)),
          const SizedBox(width: 4),
          Icon(Icons.chevron_right_rounded, color: c.ink3),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final waiting = _int(_summary['waiting']);
    final count = _summary.containsKey('clients') ? _int(_summary['clients']) : _list.length;
    final children = <Widget>[
      const _TopBar(),
      _Title('Clients', count: _loading ? null : '$count'),
      Padding(
        padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 12),
        child: TextField(
          controller: _q,
          onChanged: _search,
          textInputAction: TextInputAction.search,
          style: HoolaType.body(c),
          decoration: InputDecoration(
            hintText: 'Search clients',
            hintStyle: HoolaType.body(c).copyWith(color: c.ink3),
            prefixIcon: Icon(Icons.search_rounded, color: c.ink3),
            filled: true,
            fillColor: c.sunk,
            contentPadding: const EdgeInsets.symmetric(vertical: 14),
            border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide.none),
            enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide.none),
            focusedBorder: OutlineInputBorder(
                borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide(color: c.accent)),
          ),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 16),
        child: _Card(
          onTap: () => _open(CaInboxPage(app: widget.app)),
          child: Row(children: [
            Icon(Icons.inbox_outlined, color: waiting > 0 ? c.warn : c.ink2),
            const SizedBox(width: 12),
            Expanded(
              child: Text('Document inbox · ${waiting == 0 ? 'nothing waiting' : '$waiting need you'}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
            ),
            Icon(Icons.chevron_right_rounded, color: c.ink3),
          ]),
        ),
      ),
      if (_loading)
        const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator()))
      else if (_error != null)
        _Failed(_error!, () {
          setState(() => _loading = true);
          _load();
        })
      else if (_list.isEmpty)
        _Empty(_q.text.trim().isEmpty
            ? 'No clients yet. Add them on the console: Accounts > CA practice > Add client.'
            : 'No client matches "${_q.text.trim()}".')
      else
        for (final cl in _list) _row(context, cl),
      const SizedBox(height: 24),
    ];
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(physics: const AlwaysScrollableScrollPhysics(), children: children),
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Container(
          padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 10, HoolaSpace.gutter, 10),
          decoration: BoxDecoration(color: c.bg, border: Border(top: BorderSide(color: c.line))),
          child: Row(children: [
            Expanded(
              child: SizedBox(
                height: 48,
                child: FilledButton.icon(
                  onPressed: _busy ? null : _scan,
                  style: FilledButton.styleFrom(
                    backgroundColor: c.pill,
                    foregroundColor: c.onPill,
                    shape: const StadiumBorder(),
                  ),
                  icon: _busy
                      ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                      : const Icon(Icons.document_scanner_outlined, size: 18),
                  label: Text('Scan a bill', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.button(c, color: c.onPill)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: SizedBox(
                height: 48,
                child: OutlinedButton.icon(
                  onPressed: () => callAccountsDesk(context, widget.app),
                  style: OutlinedButton.styleFrom(
                    shape: const StadiumBorder(),
                    side: BorderSide(color: c.lineStrong),
                    foregroundColor: c.ink,
                    backgroundColor: c.surface,
                  ),
                  icon: const Icon(Icons.call_rounded, size: 18),
                  label: const Text('Call GST & Accounts', maxLines: 1, overflow: TextOverflow.ellipsis),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ one client's folder
class CaFolderPage extends StatefulWidget {
  const CaFolderPage({super.key, required this.app, required this.clientId, this.name = ''});
  final Santosh app;
  final String clientId;
  final String name;
  @override
  State<CaFolderPage> createState() => _CaFolderPageState();
}

class _CaFolderPageState extends State<CaFolderPage> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic> _client = const {};
  List<Map<String, dynamic>> _files = const [];
  String? _opening;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = CaPracticeDebug.folder ?? await widget.app.api!.practiceFolder(widget.clientId);
      if (!mounted) return;
      setState(() {
        _client = _map(r['client']);
        _files = _maps(r['files']);
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _openFile(Map<String, dynamic> f) async {
    final id = _s(f['id']);
    if (id.isEmpty || _opening != null) return;
    setState(() => _opening = id);
    try {
      final got = await widget.app.api!.practiceDownload(id);
      final name = got.name == 'file' && _s(f['name']).isNotEmpty ? _s(f['name']) : got.name;
      final safe = name.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/$safe');
      await file.writeAsBytes(got.bytes, flush: true);
      final err = await Native.shareFile(file.path, mime: _mimeOf(safe), title: 'Open $safe');
      if (err != null && err.isNotEmpty && mounted) _say(context, err);
    } catch (e) {
      if (mounted) _say(context, 'Could not open the file: $e');
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  /// month (newest first) -> kind label -> files.
  List<(String, List<(String, List<Map<String, dynamic>>)>)> _grouped() {
    final months = <String, Map<String, List<Map<String, dynamic>>>>{};
    for (final f in _files) {
      final m = _s(f['month']);
      final k = _s(f['kind_label']).isNotEmpty ? _s(f['kind_label']) : (_s(f['kind']).isEmpty ? 'Other' : _s(f['kind']));
      ((months[m] ??= <String, List<Map<String, dynamic>>>{})[k] ??= <Map<String, dynamic>>[]).add(f);
    }
    final keys = months.keys.toList()..sort((a, b) => b.compareTo(a));
    return [
      for (final m in keys) (m, [for (final e in months[m]!.entries) (e.key, e.value)]),
    ];
  }

  Widget _fileRow(BuildContext context, Map<String, dynamic> f) {
    final c = HoolaColors.of(context);
    final facts = _map(f['facts']);
    final amount = facts['total'] == null ? '' : caRupees(facts['total']);
    final meta = [_channelLabel(_s(f['channel']))].where((e) => e.isNotEmpty).join(' · ');
    final busy = _opening == _s(f['id']);
    return InkWell(
      onTap: () => _openFile(f),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: HoolaSpace.touch),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.s16, vertical: 10),
          child: Row(children: [
            Icon(Icons.insert_drive_file_outlined, size: 20, color: c.ink2),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_s(f['name']), maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.body(c)),
                if (meta.isNotEmpty) Text(meta, style: HoolaType.small(c)),
              ]),
            ),
            if (amount.isNotEmpty) ...[
              const SizedBox(width: 8),
              Text(amount, style: HoolaType.label(c).copyWith(color: c.ink)),
            ],
            if (busy) ...[
              const SizedBox(width: 8),
              const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
            ],
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final name = _s(_client['name']).isNotEmpty ? _s(_client['name']) : widget.name;
    final senders = <Object?>[...((_client['phones'] as List?) ?? const []), ...((_client['emails'] as List?) ?? const [])]
        .map((e) => '$e')
        .where((e) => e.isNotEmpty)
        .toList();
    final children = <Widget>[
      const _TopBar(),
      _Title(name.isEmpty ? 'Client' : name,
          sub: senders.isEmpty ? 'No senders yet' : 'Files from ${senders.join(', ')}'),
      if (_loading)
        const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator()))
      else if (_error != null)
        _Failed(_error!, () {
          setState(() => _loading = true);
          _load();
        })
      else if (_files.isEmpty)
        const _Empty('No files in this folder yet. Scan a bill or forward it to Hoola.')
      else
        for (final (month, kinds) in _grouped()) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter + 4, 12, HoolaSpace.gutter + 4, 8),
            child: Text(caMonthLabel(month), style: HoolaType.heading(c)),
          ),
          for (final (kind, files) in kinds)
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 8),
              child: _Card(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(HoolaSpace.s16, 8, HoolaSpace.s16, 4),
                    child: Text('$kind · ${files.length}', style: HoolaType.label(c)),
                  ),
                  for (final f in files) _fileRow(context, f),
                ]),
              ),
            ),
        ],
      const SizedBox(height: 24),
    ];
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(physics: const AlwaysScrollableScrollPhysics(), children: children),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ the document inbox
class CaInboxPage extends StatefulWidget {
  const CaInboxPage({super.key, required this.app});
  final Santosh app;
  @override
  State<CaInboxPage> createState() => _CaInboxPageState();
}

class _CaInboxPageState extends State<CaInboxPage> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _waiting = const [];
  List<Map<String, dynamic>> _clientList = const [];
  Map<String, String> _kinds = const {};
  final _month = <String, String>{};   // file id -> the month chip she picked
  final _busy = <String>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([
        CaPracticeDebug.inbox != null ? Future.value(CaPracticeDebug.inbox!) : widget.app.api!.practiceInbox(),
        _home(widget.app),
        _clients(widget.app),
      ]);
      if (!mounted) return;
      setState(() {
        _waiting = _maps(r[0]['waiting']);
        _kinds = {for (final e in _map(r[1]['kinds']).entries) e.key: '${e.value}'};
        _clientList = _maps(r[2]['clients']);
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  String _clientName(String id) =>
      _clientList.where((e) => _s(e['id']) == id).map((e) => _s(e['name'])).firstOrNull ?? 'the client';

  Future<void> _file(Map<String, dynamic> f, String clientId) async {
    final id = _s(f['id']);
    final guess = _map(f['guess']);
    final month = _month[id] ?? _s(guess['month']);
    setState(() => _busy.add(id));
    try {
      await widget.app.api!.practiceFile(id, clientId, month: month.isEmpty ? null : month, rememberSender: true);
      if (!mounted) return;
      setState(() => _waiting = [for (final w in _waiting) if (_s(w['id']) != id) w]);
      _say(context, 'Added to ${_clientName(clientId)}.');
    } catch (e) {
      if (mounted) _say(context, 'Could not file it: $e');
    } finally {
      if (mounted) setState(() => _busy.remove(id));
    }
  }

  Future<void> _other(Map<String, dynamic> f) async {
    final pick = await caPickClient(context, _clientList, later: false, title: 'Pick the client');
    if (pick == null || pick.isEmpty || !mounted) return;
    await _file(f, pick);
  }

  Future<void> _drop(Map<String, dynamic> f) async {
    final id = _s(f['id']);
    setState(() => _busy.add(id));
    try {
      await widget.app.api!.practiceDrop(id);
      if (!mounted) return;
      setState(() => _waiting = [for (final w in _waiting) if (_s(w['id']) != id) w]);
      _say(context, 'Removed from the inbox.');
    } catch (e) {
      if (mounted) _say(context, 'Could not remove it: $e');
    } finally {
      if (mounted) setState(() => _busy.remove(id));
    }
  }

  Widget _card(BuildContext context, Map<String, dynamic> f) {
    final c = HoolaColors.of(context);
    final id = _s(f['id']);
    final guess = _map(f['guess']);
    final gClient = _s(guess['client_id']);
    final gName = _s(guess['client']).isNotEmpty ? _s(guess['client']) : (gClient.isEmpty ? '' : _clientName(gClient));
    final kind = _kinds[_s(guess['kind'])] ?? _s(guess['kind']);
    final months = [for (final m in (guess['months'] is List ? guess['months'] as List : const [])) '$m'];
    final picked = _month[id] ?? _s(guess['month']);
    final from = [_channelLabel(_s(f['channel'])), _s(f['sender'])].where((e) => e.isNotEmpty).join(' · ');
    final looks = [
      if (kind.isNotEmpty) kind,
      if (gName.isNotEmpty) 'for $gName',
      if (picked.isNotEmpty && months.isEmpty) caMonthLabel(picked),
    ].join(' ');
    final busy = _busy.contains(id);
    return Padding(
      padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 12),
      child: _Card(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(_s(f['name']).isEmpty ? 'A file' : _s(f['name']), maxLines: 2, overflow: TextOverflow.ellipsis, style: HoolaType.title(c)),
          if (from.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(from, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.small(c)),
          ],
          if (_s(f['why']).isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(_s(f['why']), style: HoolaType.body(c)),
          ],
          if (_s(f['message']).isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(HoolaSpace.s12),
              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
              child: Text(_s(f['message']), maxLines: 4, overflow: TextOverflow.ellipsis, style: HoolaType.small(c).copyWith(color: c.ink2)),
            ),
          ],
          if (looks.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('Looks like: $looks', style: HoolaType.label(c)),
          ],
          if (months.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final m in months)
                ChoiceChip(
                  label: Text(caMonthLabel(m)),
                  selected: picked == m,
                  onSelected: busy ? null : (_) => setState(() => _month[id] = m),
                ),
            ]),
          ],
          const SizedBox(height: 14),
          if (gClient.isNotEmpty) ...[
            SizedBox(
              height: 48,
              child: FilledButton(
                onPressed: busy ? null : () => _file(f, gClient),
                style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
                child: busy
                    ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: c.onPill))
                    : Text('Yes, add to $gName', maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.button(c, color: c.onPill)),
              ),
            ),
            const SizedBox(height: 8),
          ],
          SizedBox(
            height: 48,
            child: OutlinedButton(
              onPressed: busy ? null : () => _other(f),
              style: OutlinedButton.styleFrom(
                shape: const StadiumBorder(),
                side: BorderSide(color: c.lineStrong),
                foregroundColor: c.ink,
                backgroundColor: c.surface,
              ),
              child: Text(gClient.isEmpty ? 'Pick a client' : 'Pick another client'),
            ),
          ),
          const SizedBox(height: 4),
          SizedBox(
            height: 48,
            child: TextButton(
              onPressed: busy ? null : () => _drop(f),
              style: TextButton.styleFrom(shape: const StadiumBorder()),
              child: Text('Not for me', style: TextStyle(color: c.bad)),
            ),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final children = <Widget>[
      const _TopBar(),
      _Title('Document inbox',
          count: _loading ? null : '${_waiting.length}',
          sub: 'Files Hoola could not file by itself. Nothing is filed until you say so.'),
      if (_loading)
        const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator()))
      else if (_error != null)
        _Failed(_error!, () {
          setState(() => _loading = true);
          _load();
        })
      else if (_waiting.isEmpty)
        const _Empty('Nothing is waiting. Every file has its client.')
      else
        for (final f in _waiting) _card(context, f),
      const SizedBox(height: 24),
    ];
    return Scaffold(
      backgroundColor: c.bg,
      body: SafeArea(
        child: RefreshIndicator(
          color: c.accent,
          onRefresh: _load,
          child: ListView(physics: const AlwaysScrollableScrollPhysics(), children: children),
        ),
      ),
    );
  }
}
