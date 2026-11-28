// v0.999.57 HOOLA CRED on the phone (owner: "MAKE HOOLA CRED MORE PREMIUM ... NATIVE", design
// claude.ai/artifact/H71Uojvg4ha8RzvtSTqevz screens 11 + 12, "GO BUILD ALL"): the app's own screen for her password
// manager - the same zero-knowledge vault as the console. The master password goes only to Android's own crypto
// (tool/android/kotlin/CredCrypto.kt, PBKDF2-SHA256 600k + AES-256-GCM); the vault key lives in this screen's memory
// while it is open and unlocked, and is dropped on lock, when the app goes to the background for too long, or when the
// screen closes. The server only ever sees locked items.
import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../state.dart';
import '../hoola_theme.dart';

class CredCrypto {
  static const _ch = MethodChannel('santosh/native');
  static Future<String?> unwrap(String pw, Map meta) async {
    try {
      final w = Map<String, dynamic>.from(meta['wrapped'] as Map);
      return await _ch.invokeMethod<String>('credUnwrap',
          {'pw': pw, 'salt': meta['salt'], 'iters': meta['iters'], 'iv': w['iv'], 'ct': w['ct']});
    } on PlatformException {
      return null;
    }
  }

  static Future<Map<String, dynamic>> create(String pw) async =>
      Map<String, dynamic>.from(await _ch.invokeMethod('credCreate', {'pw': pw, 'iters': 600000}) as Map);
  static Future<List<String>> openMany(String key, List<Map<String, String>> boxes) async =>
      ((await _ch.invokeMethod<List>('credOpenMany', {'key': key, 'boxes': boxes})) ?? const []).map((e) => '$e').toList();
  static Future<Map<String, String>> seal(String key, String text) async =>
      Map<String, String>.from(await _ch.invokeMethod('credSeal', {'key': key, 'text': text}) as Map);
  static Future<List<String>> totp(List<String> secrets) async =>
      ((await _ch.invokeMethod<List>('credTotp', {'secrets': secrets})) ?? const []).map((e) => '$e').toList();
}

String _totpSecret(String v) {
  var t = v.trim();
  if (t.toLowerCase().startsWith('otpauth://')) t = Uri.tryParse(t)?.queryParameters['secret'] ?? '';
  t = t.replaceAll(RegExp(r'[\s-]'), '').toUpperCase();
  return RegExp(r'^[A-Z2-7]+=*$').hasMatch(t) && t.length >= 16 ? t : '';
}

String _host(String u) {
  final x = Uri.tryParse(u.contains('://') ? u : 'https://$u');
  return (x?.host ?? '').replaceFirst(RegExp(r'^www\.'), '');
}

final _money = RegExp(r'\b(bank|banking|netbanking|credit\s*card|debit\s*card|card|upi|paytm|phonepe|gpay|google\s*pay|razorpay|payment|wallet|sbi|hdfc|icici|axis|kotak|pnb|yes\s*bank|demat|zerodha|groww|upstox|broker)\b',
    caseSensitive: false);
bool _isMoney(Map d) => _money.hasMatch('${d['title'] ?? ''} ${((d['urls'] as List?) ?? const []).join(' ')}'.replaceAll(RegExp(r'[.\-_/]'), ' '));

int _strength(String p) {
  final cls = [RegExp(r'[a-z]'), RegExp(r'[A-Z]'), RegExp(r'\d'), RegExp(r'[^A-Za-z0-9]')].where((r) => r.hasMatch(p)).length;
  var s = (p.length ~/ 4).clamp(0, 4) + cls - 2;
  if (RegExp(r'^\d+$').hasMatch(p)) s = s.clamp(0, p.length >= 8 ? 1 : 0);
  if (RegExp(r'^(password|qwerty|12345|admin|india|welcome)', caseSensitive: false).hasMatch(p)) s = 0;
  return s.clamp(0, 4);
}

class _Item {
  _Item(this.id, this.version, this.hoola, this.data);
  final String id;
  final int version;
  final bool hoola;
  final Map<String, dynamic> data;
  String get title => '${data['title'] ?? ''}'.trim().isEmpty ? '(no title)' : '${data['title']}';
  String get user => '${data['username'] ?? ''}';
  String get password => '${data['password'] ?? ''}';
  List<String> get urls => ((data['urls'] as List?) ?? const []).map((e) => '$e').toList();
  String get totp => _totpSecret('${data['totp'] ?? ''}');
}

class HoolaCredScreen extends StatefulWidget {
  const HoolaCredScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaCredScreen> createState() => _CredState();
}

enum _Stage { loading, create, unlock, open, error }

class _CredState extends State<HoolaCredScreen> with WidgetsBindingObserver {
  _Stage stage = _Stage.loading;
  String err = '';
  Map<String, dynamic> meta = {};
  String? vk;
  List<_Item> items = [];
  Map<String, dynamic> uses = {};
  String filter = 'all', q = '';
  _Item? sel;
  Map<String, dynamic>? edit;   // a login being made or changed
  bool busy = false, showPw = false, wrote = false;
  int gen = 0;   // bumps when a new password is generated, so the form field shows it
  DateTime idle = DateTime.now();
  DateTime? leftAt;
  Timer? tick;
  Map<String, String> codes = {};
  final pw1 = TextEditingController(), pw2 = TextEditingController();
  static const lockMins = 10;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
    tick = Timer.periodic(const Duration(seconds: 1), (_) => _onTick());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    tick?.cancel();
    vk = null;
    pw1.dispose();
    pw2.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.paused) leftAt = DateTime.now();
    if (s == AppLifecycleState.resumed && leftAt != null && vk != null && DateTime.now().difference(leftAt!).inMinutes >= 2) {
      _lock('Locked while Hoola was in the background.');   // a phone left in a pocket locks sooner than the console
    }
  }

  Future<void> _onTick() async {
    if (vk == null || !mounted) return;
    if (DateTime.now().difference(idle).inMinutes >= lockMins) return _lock('Locked after $lockMins minutes without use.');
    final want = items.where((i) => i.totp.isNotEmpty && (filter == 'codes' || sel?.id == i.id)).toList();
    if (want.isEmpty) return;
    final got = await CredCrypto.totp(want.map((i) => i.totp).toList());
    if (!mounted) return;
    setState(() {
      for (var k = 0; k < want.length && k < got.length; k++) {
        codes[want[k].id] = got[k];
      }
    });
  }

  void _bump() => idle = DateTime.now();

  void _toast(String m, {bool bad = false}) {
    final c = HoolaColors.of(context);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(m), backgroundColor: bad ? c.bad : c.pill, behavior: SnackBarBehavior.floating));
  }

  Future<dynamic> _api(String m, String path, [Object? body]) {
    final api = widget.app.api;
    if (api == null) throw Exception('Sign in to Hoola first');
    return api.call(m, path, body: body);
  }

  Future<void> _load([String msg = '']) async {
    setState(() => stage = _Stage.loading);
    try {
      meta = Map<String, dynamic>.from(await _api('GET', '/api/cred/vault') as Map);
      if (vk != null) {
        await _decrypt();
        setState(() => stage = _Stage.open);
        return;
      }
      setState(() {
        stage = meta['exists'] == true ? _Stage.unlock : _Stage.create;
        err = msg;
      });
    } catch (e) {
      setState(() {
        stage = _Stage.error;
        err = '$e'.replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _decrypt() async {
    final raw = ((meta['items'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final texts = await CredCrypto.openMany(vk!, [for (final r in raw) {'iv': '${r['iv']}', 'ct': '${r['ct']}'}]);
    items = [
      for (var k = 0; k < raw.length; k++)
        _Item('${raw[k]['id']}', (raw[k]['version'] as num?)?.toInt() ?? 1, raw[k]['hoola'] == true,
            k < texts.length && texts[k].isNotEmpty ? Map<String, dynamic>.from(jsonDecode(texts[k]) as Map) : {'title': '(cannot be opened)'}),
    ]..sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
    try {
      uses = Map<String, dynamic>.from((await _api('GET', '/api/cred/hoola-uses') as Map)['uses'] as Map? ?? {});
    } catch (_) {
      uses = {};
    }
    if (sel != null) sel = items.where((i) => i.id == sel!.id).firstOrNull;
  }

  void _lock([String msg = 'Locked.']) {
    if (!mounted) return;
    setState(() {
      vk = null;
      items = [];
      sel = null;
      edit = null;
      codes = {};
      stage = _Stage.unlock;
      err = msg;
    });
  }

  Future<void> _copy(String text, String what) async {
    await Clipboard.setData(ClipboardData(text: text));
    _toast('$what copied - cleared in 30 s');
    Timer(const Duration(seconds: 30), () async {
      final now = await Clipboard.getData('text/plain');
      if (now?.text == text) await Clipboard.setData(const ClipboardData(text: ''));
    });
  }

  // ------------------------------------------------------------------ actions
  Future<void> _make() async {
    final a = pw1.text;
    if (a.length < 10) return _toast('Use at least 10 characters', bad: true);
    if (a != pw2.text) return _toast('The two do not match', bad: true);
    if (_strength(a) < 2) return _toast('Too easy to guess - make it longer', bad: true);
    if (!wrote) return _toast('Write it down first, then tick the box', bad: true);
    setState(() => busy = true);
    try {
      final v = await CredCrypto.create(a);
      await _api('POST', '/api/cred/vault', {'salt': v['salt'], 'iters': v['iters'], 'wrapped': v['wrapped']});
      vk = '${v['key']}';
      pw1.clear();
      pw2.clear();
      _bump();
      await _load();
      _toast('Your Hoola Cred is ready');
    } catch (e) {
      _toast('$e', bad: true);
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _unlock() async {
    setState(() => busy = true);
    final key = await CredCrypto.unwrap(pw1.text, meta);
    pw1.clear();
    if (key == null) {
      if (mounted) setState(() => busy = false);
      return _toast('That is not the master password', bad: true);
    }
    vk = key;
    _bump();
    await _decrypt();
    if (mounted) {
      setState(() {
        busy = false;
        stage = _Stage.open;
        err = '';
      });
    }
  }

  Future<void> _setHoola(_Item it, bool on) async {
    try {
      await _api('PUT', '/api/cred/items/${Uri.encodeComponent(it.id)}/hoola', on
          ? {'on': true, 'title': it.data['title'] ?? '', 'username': it.user, 'password': it.password, 'urls': it.urls, 'totp': it.data['totp'] ?? ''}
          : {'on': false});
      meta = Map<String, dynamic>.from(await _api('GET', '/api/cred/vault') as Map);
      await _decrypt();
      setState(() {});
      _toast(on ? 'Hoola may now use ${it.title} - only on your tap' : "Hoola's copy of ${it.title} is removed");
    } catch (e) {
      _toast('$e'.replaceFirst('ApiException', '').trim(), bad: true);
    }
  }

  Future<void> _save() async {
    final e = edit!;
    final now = DateTime.now().toUtc().toIso8601String();
    final data = {
      'title': '${e['title'] ?? ''}'.trim(),
      'username': '${e['username'] ?? ''}'.trim(),
      'password': '${e['password'] ?? ''}',
      'urls': '${e['url'] ?? ''}'.split(RegExp(r'[\s,]+')).where((s) => s.isNotEmpty).take(10).toList(),
      'totp': '${e['totp'] ?? ''}'.trim(),
      'folder': '${e['folder'] ?? ''}'.trim(),
      'notes': '${e['notes'] ?? ''}',
      'created': e['created'] ?? now,
      'updated': now,
    };
    if ((data['title'] as String).isEmpty) return _toast('Give it a name', bad: true);
    if ((data['totp'] as String).isNotEmpty && _totpSecret(data['totp'] as String).isEmpty) return _toast('That 2-step key is not valid', bad: true);
    final hoola = e['_hoola'] == true && !_isMoney(data);
    if (hoola && (data['urls'] as List).isEmpty) return _toast('Add the website, so Hoola knows where to use it', bad: true);
    setState(() => busy = true);
    try {
      final box = await CredCrypto.seal(vk!, jsonEncode(data));
      String id = '${e['_id'] ?? ''}';
      if (id.isEmpty) {
        id = '${(await _api('POST', '/api/cred/items', box) as Map)['id']}';
      } else {
        await _api('PUT', '/api/cred/items/${Uri.encodeComponent(id)}', {...box, 'version': e['_version']});
      }
      if (hoola || e['_was'] == true) {
        await _api('PUT', '/api/cred/items/${Uri.encodeComponent(id)}/hoola', hoola
            ? {'on': true, 'title': data['title'], 'username': data['username'], 'password': data['password'], 'urls': data['urls'], 'totp': data['totp']}
            : {'on': false});
      }
      meta = Map<String, dynamic>.from(await _api('GET', '/api/cred/vault') as Map);
      await _decrypt();
      setState(() {
        edit = null;
        sel = items.where((i) => i.id == id).firstOrNull;
        showPw = false;
      });
      _toast('Saved');
    } catch (err) {
      _toast('$err', bad: true);
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _delete(_Item it) async {
    final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
              title: Text('Delete ${it.title}?'),
              content: const Text('This cannot be undone.'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
              ],
            ));
    if (ok != true) return;
    try {
      await _api('DELETE', '/api/cred/items/${Uri.encodeComponent(it.id)}');
      meta = Map<String, dynamic>.from(await _api('GET', '/api/cred/vault') as Map);
      await _decrypt();
      setState(() => sel = null);
      _toast('Deleted');
    } catch (e) {
      _toast('$e', bad: true);
    }
  }

  String _newPassword() {
    const sets = ['abcdefghijkmnopqrstuvwxyz', 'ABCDEFGHJKLMNPQRSTUVWXYZ', '23456789', '!@#\$%^&*-_=+?'];
    final r = Random.secure();
    final all = sets.join();
    String out;
    do {
      out = List.generate(20, (_) => all[r.nextInt(all.length)]).join();
    } while (!sets.every((s) => out.split('').any(s.contains)));
    return out;
  }

  // ------------------------------------------------------------------ building
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return Listener(
      onPointerDown: (_) => _bump(),
      child: PopScope(
        canPop: edit == null && sel == null,
        onPopInvokedWithResult: (did, _) {
          if (did) return;
          setState(() {
            if (edit != null) {
              edit = null;
            } else {
              sel = null;
              showPw = false;
            }
          });
        },
        child: Scaffold(
          backgroundColor: c.bg,
          body: SafeArea(child: switch (stage) {
            _Stage.loading => Center(child: Text('Opening Hoola Cred…', style: HoolaType.body(c).copyWith(color: c.ink3))),
            _Stage.error => _center(c, [Text(err, style: HoolaType.body(c), textAlign: TextAlign.center), const SizedBox(height: 16), _pillButton(c, 'Try again', _load)]),
            _Stage.create => _createView(c),
            _Stage.unlock => _unlockView(c),
            _Stage.open => edit != null ? _editView(c) : sel != null ? _detailView(c, sel!) : _listView(c),
          }),
          floatingActionButton: stage == _Stage.open && edit == null && sel == null
              ? FloatingActionButton.extended(
                  backgroundColor: c.pill,
                  foregroundColor: c.onPill,
                  onPressed: () => setState(() => edit = {'password': _newPassword()}),
                  icon: const Icon(Icons.add),
                  label: Text('New login', style: HoolaType.button(c, color: c.onPill)),
                )
              : null,
        ),
      ),
    );
  }

  Widget _center(HoolaColors c, List<Widget> kids) => Center(
      child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: kids)));

  Widget _pillButton(HoolaColors c, String label, VoidCallback? onTap, {bool primary = true, bool wide = false}) => SizedBox(
        width: wide ? double.infinity : null,
        height: HoolaSpace.touchMain,
        child: primary
            ? FilledButton(
                style: FilledButton.styleFrom(backgroundColor: c.pill, foregroundColor: c.onPill, shape: const StadiumBorder()),
                onPressed: busy ? null : onTap,
                child: Text(label, style: HoolaType.button(c, color: c.onPill)))
            : OutlinedButton(
                style: OutlinedButton.styleFrom(foregroundColor: c.ink, side: BorderSide(color: c.lineStrong), shape: const StadiumBorder()),
                onPressed: onTap,
                child: Text(label, style: HoolaType.button(c).copyWith(fontSize: 14))),
      );

  TextStyle _serif(HoolaColors c, double size) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: size, fontWeight: FontWeight.w500, color: c.ink, height: 1.12, letterSpacing: -.3);
  TextStyle _mono(HoolaColors c, double size) => TextStyle(fontFamily: HoolaFont.mono, fontSize: size, color: c.ink, height: 1.3);

  InputDecoration _dec(HoolaColors c, String label, {String hint = ''}) => InputDecoration(
        labelText: label,
        hintText: hint.isEmpty ? null : hint,
        filled: true,
        fillColor: c.surface,
        border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.lineStrong)),
        enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.tile), borderSide: BorderSide(color: c.lineStrong)),
      );

  Widget _topBar(HoolaColors c, {String status = '', VoidCallback? back, List<Widget> actions = const []}) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 4, 4, 0),
        child: Row(children: [
          IconButton(
              tooltip: 'Back',
              onPressed: back ?? () => Navigator.of(context).maybePop(),
              icon: Icon(back == null ? Icons.close : Icons.arrow_back, color: c.ink)),
          const Spacer(),
          if (status.isNotEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(color: c.sunk, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 7, height: 7, decoration: BoxDecoration(color: c.ok, shape: BoxShape.circle)),
                const SizedBox(width: 6),
                Text(status, style: HoolaType.label(c).copyWith(fontWeight: FontWeight.w600)),
              ]),
            ),
          const Spacer(),
          ...actions,
          if (actions.isEmpty) const SizedBox(width: 48),
        ]),
      );

  Widget _tile(HoolaColors c, String title, {double size = 40}) {
    var h = 0;
    for (final r in title.runes) {
      h = (h * 31 + r) & 0x7fffffff;
    }
    final col = HSLColor.fromAHSL(1, (h % 360).toDouble(), .38, c.dark ? .42 : .36).toColor();
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: col, borderRadius: HoolaRadius.r(size >= 56 ? 20 : HoolaRadius.tile)),
      child: Text(title.isEmpty ? '?' : title.characters.first.toUpperCase(),
          style: TextStyle(fontFamily: HoolaFont.sans, fontSize: size >= 56 ? 26 : 15, fontWeight: FontWeight.w700, color: c.onAccent)),
    );
  }

  Widget _tag(HoolaColors c, String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: HoolaRadius.r(HoolaRadius.pill)),
        child: Text(text, style: HoolaType.label(c).copyWith(color: fg, fontWeight: FontWeight.w600)),
      );

  // ---- first time
  Widget _createView(HoolaColors c) => ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 32), children: [
        _topBar(c),
        const SizedBox(height: 8),
        Text('Make your Hoola Cred', style: _serif(c, 34)),
        const SizedBox(height: 12),
        Text('One master password locks every login and 2-step code you keep here. It never leaves this phone.', style: HoolaType.body(c).copyWith(color: c.ink2)),
        const SizedBox(height: 24),
        TextField(controller: pw1, obscureText: true, decoration: _dec(c, 'Master password', hint: 'At least 10 characters'), onChanged: (_) => setState(() {})),
        const SizedBox(height: 8),
        _meter(c, pw1.text),
        const SizedBox(height: 16),
        TextField(controller: pw2, obscureText: true, decoration: _dec(c, 'Type it again')),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: c.warnSoft, borderRadius: HoolaRadius.r(HoolaRadius.tile)),
          child: Text('If you forget it, nobody can open this vault, not even Hoola. Write it down somewhere safe.',
              style: HoolaType.small(c).copyWith(color: c.warn)),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: wrote,
          onChanged: (v) => setState(() => wrote = v == true),
          title: Text('I have written my master password down', style: HoolaType.body(c)),
          controlAffinity: ListTileControlAffinity.leading,
        ),
        const SizedBox(height: 8),
        _pillButton(c, busy ? 'Making your vault…' : 'Make my vault', _make, wide: true),
      ]);

  Widget _meter(HoolaColors c, String pw) {
    final s = _strength(pw);
    final col = s >= 3 ? c.ok : s == 2 ? c.warn : c.bad;
    return Row(children: [
      for (var k = 0; k < 5; k++)
        Expanded(child: Container(height: 4, margin: const EdgeInsets.only(right: 4), decoration: BoxDecoration(color: k <= s ? col : c.line, borderRadius: HoolaRadius.r(4)))),
      const SizedBox(width: 8),
      Text(['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'][s], style: HoolaType.label(c).copyWith(color: col, fontWeight: FontWeight.w600)),
    ]);
  }

  // ---- unlock
  Widget _unlockView(HoolaColors c) {
    final n = ((meta['items'] as List?) ?? const []).length;
    return ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 32), children: [
      _topBar(c),
      const SizedBox(height: 40),
      Center(
        child: Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(color: c.pill, borderRadius: HoolaRadius.r(22)),
          child: Icon(Icons.lock_outline, color: c.onPill, size: 32),
        ),
      ),
      const SizedBox(height: 20),
      Text('Welcome back', style: _serif(c, 34), textAlign: TextAlign.center),
      const SizedBox(height: 10),
      Text('${err.isEmpty ? '' : '$err '}Hoola Cred is locked. $n login${n == 1 ? '' : 's'} waiting.',
          style: HoolaType.body(c).copyWith(color: c.ink2), textAlign: TextAlign.center),
      const SizedBox(height: 24),
      TextField(controller: pw1, obscureText: true, autofocus: true, decoration: _dec(c, 'Master password'), onSubmitted: (_) => _unlock()),
      const SizedBox(height: 16),
      _pillButton(c, busy ? 'Unlocking…' : 'Unlock', _unlock, wide: true),
      const SizedBox(height: 16),
      Text('Unlocked only on this phone · locks when you leave it', style: HoolaType.small(c), textAlign: TextAlign.center),
    ]);
  }

  // ---- list
  List<_Item> get _shown {
    final s = q.trim().toLowerCase();
    return items.where((i) {
      if (filter == 'hoola' && !i.hoola) return false;
      if (filter == 'codes' && i.totp.isEmpty) return false;
      if (filter == 'fix' && !(i.password.isNotEmpty && _strength(i.password) < 2)) return false;
      return s.isEmpty || [i.title, i.user, ...i.urls, '${i.data['folder'] ?? ''}'].join(' ').toLowerCase().contains(s);
    }).toList();
  }

  Widget _listView(HoolaColors c) {
    final fix = items.where((i) => i.password.isNotEmpty && _strength(i.password) < 2).length;
    final chips = [
      ('all', 'All ${items.length}'),
      ('hoola', 'Hoola ${items.where((i) => i.hoola).length}'),
      ('codes', 'Codes ${items.where((i) => i.totp.isNotEmpty).length}'),
      ('fix', 'Fix $fix'),
    ];
    final rows = _shown;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _topBar(c, status: 'Unlocked', actions: [IconButton(tooltip: 'Lock now', onPressed: _lock, icon: Icon(Icons.lock_outline, color: c.ink))]),
      Padding(
        padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 4, HoolaSpace.gutter, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Hoola Cred', style: _serif(c, 34)),
          const SizedBox(height: 14),
          TextField(
            onChanged: (v) => setState(() => q = v),
            decoration: InputDecoration(
              hintText: 'Search ${items.length} login${items.length == 1 ? '' : 's'}',
              prefixIcon: Icon(Icons.search, color: c.ink3),
              filled: true,
              fillColor: c.surface,
              contentPadding: EdgeInsets.zero,
              border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide(color: c.lineStrong)),
              enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide(color: c.lineStrong)),
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              for (final (k, label) in chips)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(label),
                    selected: filter == k,
                    showCheckmark: false,
                    onSelected: (_) => setState(() => filter = k),
                    selectedColor: c.pill,
                    backgroundColor: c.surface,
                    labelStyle: HoolaType.label(c).copyWith(fontSize: 13, fontWeight: FontWeight.w600, color: filter == k ? c.onPill : c.ink2),
                    shape: StadiumBorder(side: BorderSide(color: filter == k ? c.pill : c.lineStrong)),
                  ),
                ),
            ]),
          ),
        ]),
      ),
      Expanded(
        child: items.isEmpty
            ? Center(child: Padding(padding: const EdgeInsets.all(32), child: Text('Your vault is empty. Add your first login with New login.', style: HoolaType.body(c).copyWith(color: c.ink3), textAlign: TextAlign.center)))
            : rows.isEmpty
                ? Center(child: Text('Nothing here.', style: HoolaType.body(c).copyWith(color: c.ink3)))
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, 0, HoolaSpace.gutter, 96),
                    itemCount: rows.length,
                    separatorBuilder: (_, __) => Divider(height: 1, color: c.line),
                    itemBuilder: (_, k) => _row(c, rows[k]),
                  ),
      ),
    ]);
  }

  Widget _row(HoolaColors c, _Item i) {
    final weak = i.password.isNotEmpty && _strength(i.password) < 2;
    final code = codes[i.id];
    return InkWell(
      onTap: () => setState(() {
        sel = i;
        showPw = false;
      }),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 64),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Row(children: [
            _tile(c, i.title),
            const SizedBox(width: 12),
            Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(i.title, style: HoolaType.title(c).copyWith(fontSize: 15), maxLines: 1, overflow: TextOverflow.ellipsis),
              Text(filter == 'codes' && code != null ? '${code.substring(0, 3)} ${code.substring(3)}' : (i.user.isEmpty ? _host(i.urls.firstOrNull ?? '') : i.user),
                  style: filter == 'codes' ? _mono(c, 15) : HoolaType.small(c), maxLines: 1, overflow: TextOverflow.ellipsis),
            ])),
            if (i.hoola) _tag(c, 'Hoola', c.accentSoft, c.accent) else if (weak) _tag(c, 'Weak', c.warnSoft, c.warn),
          ]),
        ),
      ),
    );
  }

  // ---- one login
  Widget _detailView(HoolaColors c, _Item i) {
    final money = _isMoney(i.data);
    final use = Map<String, dynamic>.from(uses[i.id] as Map? ?? {});
    final code = codes[i.id];
    final left = 30 - (DateTime.now().millisecondsSinceEpoch ~/ 1000) % 30;
    Widget field(String k, Widget v, List<Widget> acts) => Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
          child: Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(k, style: HoolaType.label(c)), const SizedBox(height: 3), v])),
            ...acts,
          ]),
        );
    Widget act(String label, VoidCallback onTap) => Padding(
          padding: const EdgeInsets.only(left: 8),
          child: OutlinedButton(
            style: OutlinedButton.styleFrom(minimumSize: const Size(56, 44), foregroundColor: c.ink, side: BorderSide(color: c.lineStrong), shape: const StadiumBorder()),
            onPressed: onTap,
            child: Text(label, style: HoolaType.label(c).copyWith(fontSize: 13, fontWeight: FontWeight.w600, color: c.ink)),
          ),
        );
    return Column(children: [
      _topBar(c, back: () => setState(() => sel = null), actions: [
        TextButton(
            onPressed: () => setState(() {
                  edit = {
                    ...i.data,
                    'url': i.urls.join(', '),
                    '_id': i.id,
                    '_version': i.version,
                    '_hoola': i.hoola,
                    '_was': i.hoola,
                  };
                  showPw = false;
                }),
            child: Text('Edit', style: HoolaType.button(c).copyWith(fontSize: 15))),
        IconButton(tooltip: 'Delete', onPressed: () => _delete(i), icon: Icon(Icons.delete_outline, color: c.bad)),
      ]),
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 24), children: [
          Center(child: _tile(c, i.title, size: 68)),
          const SizedBox(height: 10),
          Text(i.title, style: _serif(c, 28), textAlign: TextAlign.center),
          const SizedBox(height: 4),
          Text([_host(i.urls.firstOrNull ?? ''), '${i.data['folder'] ?? ''}'].where((s) => s.isNotEmpty).join(' · '),
              style: HoolaType.small(c), textAlign: TextAlign.center),
          const SizedBox(height: 12),
          if (i.user.isNotEmpty) field('User name', Text(i.user, style: _mono(c, 15)), [act('Copy', () => _copy(i.user, 'User name'))]),
          if (i.password.isNotEmpty)
            field('Password', Text(showPw ? i.password : '••••••••••••', style: _mono(c, 15)), [
              IconButton(tooltip: showPw ? 'Hide password' : 'Show password', onPressed: () => setState(() => showPw = !showPw),
                  icon: Icon(showPw ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: c.ink2)),
              act('Copy', () => _copy(i.password, 'Password')),
            ]),
          if (i.totp.isNotEmpty)
            field('2-step code · $left s', Text(code == null ? '··· ···' : '${code.substring(0, 3)} ${code.substring(3)}', style: _mono(c, 28)),
                [act('Copy', () => code == null ? null : _copy(code, '2-step code'))]),
          for (final u in i.urls)
            field('Website', Text(u, style: HoolaType.body(c).copyWith(color: c.accent)), [
              act('Open', () => launchUrl(Uri.parse(u.contains('://') ? u : 'https://$u'), mode: LaunchMode.externalApplication)),
            ]),
          if ('${i.data['notes'] ?? ''}'.isNotEmpty) field('Note', Text('${i.data['notes']}', style: HoolaType.body(c)), const []),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: money ? c.sunk : c.accentSoft, borderRadius: HoolaRadius.r(HoolaRadius.card), border: Border.all(color: money ? c.line : c.accent.withOpacity(.2))),
            child: Row(children: [
              Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(money ? 'A bank or payment login' : 'Hoola may use this login', style: HoolaType.title(c).copyWith(fontSize: 15)),
                const SizedBox(height: 3),
                Text(
                    money
                        ? 'Hoola never uses these. They stay for you alone.'
                        : i.hoola
                            ? 'On the Hoola PC, only when you tap. ${use['used'] != null && '${use['used']}'.isNotEmpty ? 'Last used ${'${use['used']}'.substring(0, 10)}.' : 'Not used yet.'}'
                            : 'Switch on to let the Hoola PC sign in here for you, only when you tap.',
                    style: HoolaType.small(c).copyWith(color: c.ink2)),
              ])),
              if (!money)
                Switch(
                  value: i.hoola,
                  activeColor: c.onAccent,
                  activeTrackColor: c.accent,
                  onChanged: i.urls.isEmpty || i.password.isEmpty ? null : (v) => _setHoola(i, v),
                ),
            ]),
          ),
        ]),
      ),
    ]);
  }

  // ---- new / edit
  Widget _editView(HoolaColors c) {
    final e = edit!;
    Widget input(String key, String label, {bool mono = false, bool secret = false, int lines = 1, String hint = ''}) => Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: TextFormField(
            key: ValueKey('$key$gen'),
            initialValue: '${e[key] ?? ''}',
            obscureText: secret && !showPw,
            maxLines: secret ? 1 : lines,
            style: mono ? _mono(c, 15) : HoolaType.body(c),
            decoration: _dec(c, label, hint: hint),
            onChanged: (v) => setState(() => e[key] = v),
          ),
        );
    final money = _isMoney({'title': e['title'] ?? '', 'urls': ['${e['url'] ?? ''}']});
    return Column(children: [
      _topBar(c, back: () => setState(() => edit = null), actions: [
        TextButton(onPressed: busy ? null : _save, child: Text(busy ? 'Saving…' : 'Save', style: HoolaType.button(c).copyWith(fontSize: 15))),
      ]),
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 32), children: [
          Text(e['_id'] == null ? 'New login' : 'Edit login', style: _serif(c, 28)),
          const SizedBox(height: 6),
          Text('Locked on this phone before it is saved.', style: HoolaType.small(c)),
          const SizedBox(height: 18),
          input('title', 'Name', hint: 'GST portal'),
          input('url', 'Website', hint: 'services.gst.gov.in'),
          input('username', 'User name', mono: true),
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(child: input('password', 'Password', mono: true, secret: true)),
            IconButton(tooltip: showPw ? 'Hide' : 'Show', onPressed: () => setState(() => showPw = !showPw), icon: Icon(showPw ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: c.ink2)),
            IconButton(
                tooltip: 'New strong password',
                onPressed: () => setState(() {
                      e['password'] = _newPassword();
                      showPw = true;
                      gen++;
                    }),
                icon: Icon(Icons.autorenew, color: c.ink2)),
          ]),
          Padding(padding: const EdgeInsets.only(bottom: 14), child: _meter(c, '${e['password'] ?? ''}')),
          input('totp', '2-step key (optional)', mono: true, hint: 'The setup key the site shows'),
          input('folder', 'Folder', hint: 'Government, Work, Family…'),
          input('notes', 'Note', lines: 3),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: money ? c.sunk : c.accentSoft, borderRadius: HoolaRadius.r(HoolaRadius.card)),
            child: Row(children: [
              Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Hoola may use this login', style: HoolaType.title(c).copyWith(fontSize: 15)),
                const SizedBox(height: 3),
                Text(money ? 'A bank or payment login - Hoola never uses these.' : 'Sent once, sealed for the Hoola PC, used only on your tap.',
                    style: HoolaType.small(c).copyWith(color: c.ink2)),
              ])),
              Switch(
                value: e['_hoola'] == true && !money,
                activeColor: c.onAccent,
                activeTrackColor: c.accent,
                onChanged: money ? null : (v) => setState(() => e['_hoola'] = v),
              ),
            ]),
          ),
          const SizedBox(height: 20),
          _pillButton(c, busy ? 'Saving…' : 'Save login', _save, wide: true),
        ]),
      ),
    ]);
  }
}
