import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../state.dart';
import 'attach.dart';
import 'glass.dart';

/// v0.67 Hoola Computer Operator: Hoola works on websites in its own browser (forms, downloads, status checks,
/// applications) and asks the owner on her phone for the steps only she may do. Passwords, OTP, Aadhaar / PAN / card /
/// bank numbers: she types them here and they go straight into the page (Hoola never sees them, nothing is stored).
/// v0.78: CAPTCHA is read by Hoola (OCR) and shown for confirmation (she taps "Haan" or corrects it).
/// Submit / send / delete: her tap. Payments: she presses the button herself in the live view.

const _kindTitle = {
  'approve': 'Aapki haan chahiye',
  'payment': 'Payment aap khud kijiye',
  'otp': 'OTP bhariye',
  'captcha': 'CAPTCHA check kijiye',
  'secret': 'Yeh aap khud bhariye',
  'question': 'Ek sawaal',
  'choice': 'Aap chuniye',
  'takeover': 'Yeh step aap kijiye',
};
const _kindIcon = {
  'approve': Icons.task_alt_rounded,
  'payment': Icons.currency_rupee_rounded,
  'otp': Icons.sms_rounded,
  'captcha': Icons.text_fields_rounded,
  'secret': Icons.lock_rounded,
  'question': Icons.help_rounded,
  'choice': Icons.list_rounded,
  'takeover': Icons.touch_app_rounded,
};
const _active = {'queued', 'running', 'waiting'};

void _snack(BuildContext context, String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

void openOperatorLive(BuildContext context, Santosh app) =>
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => OperatorLiveScreen(app: app)));

/// Polls the job's browser picture (~1 per second) while it is on screen.
class OperatorFrame extends StatefulWidget {
  const OperatorFrame({super.key, required this.app, this.onTapPage, this.fit = BoxFit.contain, this.every = 900});
  final Santosh app;
  final void Function(double x, double y)? onTapPage;   // page pixels (1280 x 900)
  final BoxFit fit;
  final int every;
  @override
  State<OperatorFrame> createState() => _OperatorFrameState();
}

class _OperatorFrameState extends State<OperatorFrame> {
  Timer? _t;
  Uint8List? _img;
  bool _busy = false;
  bool _gone = false;

  @override
  void initState() {
    super.initState();
    _poll();
    _t = Timer.periodic(Duration(milliseconds: widget.every), (_) => _poll());
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    if (_busy || widget.app.api == null) return;
    _busy = true;
    try {
      final b = await widget.app.api!.operatorFrame();
      if (!mounted) return;
      if (b != null) {
        setState(() {
          _img = Uint8List.fromList(b);
          _gone = false;
        });
      } else if (!_gone) {
        setState(() => _gone = true);
      }
    } catch (_) {
    } finally {
      _busy = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final img = _img;
    return AspectRatio(
      aspectRatio: 1280 / 900,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          color: const Color(0xFF101018),
          child: img == null
              ? Center(
                  child: _gone
                      ? const Text('Browser abhi band hai', style: TextStyle(color: C.faint))
                      : const CircularProgressIndicator(strokeWidth: 2))
              : LayoutBuilder(
                  builder: (context, box) => GestureDetector(
                    onTapUp: widget.onTapPage == null
                        ? null
                        : (d) => widget.onTapPage!(d.localPosition.dx * 1280 / box.maxWidth, d.localPosition.dy * 900 / box.maxHeight),
                    child: Image.memory(img, gaplessPlayback: true, fit: BoxFit.fill, width: box.maxWidth, height: box.maxHeight),
                  ),
                ),
        ),
      ),
    );
  }
}

/// A question from the operator job: shown in chat (and inside a call) and on the live screen.
class OperatorAskCard extends StatefulWidget {
  const OperatorAskCard({super.key, required this.v, required this.app, this.inLive = false});
  final Map<String, dynamic> v;
  final Santosh app;
  final bool inLive;
  @override
  State<OperatorAskCard> createState() => _OperatorAskCardState();
}

class _OperatorAskCardState extends State<OperatorAskCard> {
  final _box = TextEditingController();
  bool _busy = false;
  bool _show = false;

  @override
  void dispose() {
    _box.clear();
    _box.dispose();
    super.dispose();
  }

  Uint8List? _cap;
  bool _capTried = false;

  Future<void> _loadCaptcha() async {
    _capTried = true;
    try {
      final b = await widget.app.api!.operatorCaptcha('${widget.v['id']}');
      if (mounted && b != null) setState(() => _cap = Uint8List.fromList(b));
    } catch (_) {}
    if (mounted) setState(() {});
  }

  Future<void> _newCaptcha() async {
    setState(() => _busy = true);
    try {
      final ok = await widget.app.api!.operatorCaptchaRefresh('${widget.v['id']}');
      if (!ok && mounted) _snack(context, 'Naya CAPTCHA ka button nahi mila; live view mein dekhiye');
      await _loadCaptcha();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  Widget _captchaPic() {
    if (!_capTried && widget.app.api != null) Future.microtask(_loadCaptcha);
    final img = _cap;
    if (img == null) {
      return _capTried && !widget.inLive
          ? OperatorFrame(app: widget.app, every: 900)
          : const SizedBox(height: 70, child: Center(child: CircularProgressIndicator(strokeWidth: 2)));
    }
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
      child: InteractiveViewer(maxScale: 4, child: Image.memory(img, height: 90, fit: BoxFit.contain, gaplessPlayback: true)),
    );
  }

  Future<void> _answer(bool yes, {String answer = ''}) async {
    if (widget.app.api == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.operatorAnswer('${widget.v['id']}', yes, answer: answer);
      widget.v.addAll(r);
      _box.clear();                                   // what she typed is gone from the phone too
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  /// v0.78: fill the solved CAPTCHA into the page box via the dedicated endpoint.
  Future<void> _captchaFill(String value) async {
    if (widget.app.api == null || value.isEmpty) return;
    setState(() => _busy = true);
    try {
      await widget.app.api!.operatorCaptchaFill('${widget.v['id']}', value);
      widget.v['status'] = 'approved';
      _box.clear();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final kind = '${v['kind'] ?? 'question'}';
    final status = '${v['status'] ?? 'pending'}';
    final pending = status == 'pending';
    final typed = const {'otp', 'secret'}.contains(kind);  // v0.78: captcha no longer typed by owner
    final suggestedAnswer = '${v['suggested_answer'] ?? ''}';
    final options = List<String>.from(((v['options'] as List?) ?? const []).map((e) => '$e'));
    return Glass(
      margin: widget.inLive ? EdgeInsets.zero : const EdgeInsets.symmetric(vertical: 6),
      border: pending ? C.accent : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_kindIcon[kind] ?? Icons.help_rounded, color: kind == 'payment' ? C.warn : C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text(_kindTitle[kind] ?? 'Aapse sawaal', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
          if (!pending)
            Pill(status == 'approved' || status == 'done' ? 'Ho gaya' : status == 'expired' ? 'Samay khatam' : 'Mana kiya',
                fg: status == 'approved' || status == 'done' ? C.ok : C.faint),
        ]),
        if ('${v['site'] ?? ''}'.isNotEmpty || '${v['target_name'] ?? ''}'.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text([
              if ('${v['site'] ?? ''}'.isNotEmpty) '${v['site']}',
              if ('${v['target_name'] ?? ''}'.isNotEmpty) 'Button: "${v['target_name']}"',
            ].join(' · '), style: const TextStyle(color: C.faint, fontSize: 12)),
          ),
        const SizedBox(height: 6),
        Text('${v['reason'] ?? ''}', style: const TextStyle(fontSize: 14, height: 1.35)),
        if (pending && kind == 'captcha') ...[
          const SizedBox(height: 8),
          _captchaPic(),
          if (suggestedAnswer.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
              child: Row(children: [
                const Icon(Icons.spellcheck_rounded, size: 20, color: C.accent),
                const SizedBox(width: 10),
                Expanded(child: Text(suggestedAnswer, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, letterSpacing: 2))),
              ]),
            ),
            const SizedBox(height: 6),
            Text('Hoola ne padha: "$suggestedAnswer". Sahi hai toh "Haan" dabaiye, galat ho toh neeche sahi jawab likhiye.',
                style: const TextStyle(color: C.faint, fontSize: 11.5)),
            const SizedBox(height: 8),
            TextField(
              controller: _box,
              enableSuggestions: false,
              autocorrect: false,
              keyboardType: TextInputType.visiblePassword,
              decoration: InputDecoration(
                hintText: 'Sahi CAPTCHA (agar galat padha ho)',
                isDense: true,
                filled: true,
                fillColor: C.panel,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
          ] else ...[
            const SizedBox(height: 6),
            const Text('Hoola padh nahi paaya. Neeche CAPTCHA likhiye ya chat / call mein bol dijiye.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
            const SizedBox(height: 8),
            TextField(
              controller: _box,
              enableSuggestions: false,
              autocorrect: false,
              keyboardType: TextInputType.visiblePassword,
              decoration: InputDecoration(
                hintText: 'CAPTCHA likhiye',
                isDense: true,
                filled: true,
                fillColor: C.panel,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
          ],
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton.icon(
                onPressed: _busy ? null : _newCaptcha, icon: const Icon(Icons.refresh_rounded, size: 18), label: const Text('Naya')),
          ]),
        ],
        if (pending && typed) ...[
          const SizedBox(height: 8),
          TextField(
            controller: _box,
            obscureText: !_show,
            enableSuggestions: false,
            autocorrect: false,
            keyboardType: kind == 'otp' ? TextInputType.number : TextInputType.visiblePassword,
            decoration: InputDecoration(
              hintText: kind == 'otp' ? 'OTP' : 'Yahan likhiye',
              isDense: true,
              filled: true,
              fillColor: C.panel,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              suffixIcon: IconButton(icon: Icon(_show ? Icons.visibility_off : Icons.visibility, size: 18),
                      onPressed: () => setState(() => _show = !_show)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
                kind == 'otp'
                    ? 'SMS aate hi Android "Allow" poochhega: dabaiye, OTP apne aap bhar jayega. Ya yahan likhiye / chat mein likhiye / call mein bol dijiye. Seedha website ke box mein jayega, kahin save nahi hota.'
                    : 'Yeh seedha website ke box mein jayega. Hoola ise kabhi dekhta ya rakhta nahi.',
                style: const TextStyle(color: C.faint, fontSize: 11.5)),
          ),
        ],
        if (pending && kind == 'question') ...[
          const SizedBox(height: 8),
          TextField(
            controller: _box,
            minLines: 1,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: 'Jawab',
              isDense: true,
              filled: true,
              fillColor: C.panel,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ],
        if (pending && kind == 'choice' && options.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final o in options) ActionChip(label: Text(o), onPressed: _busy ? null : () => _answer(true, answer: o)),
          ]),
        ],
        if (pending) ...[
          const SizedBox(height: 10),
          Row(children: [
            if (kind == 'payment' || kind == 'takeover' || (!widget.inLive && kind != 'question' && kind != 'choice'))
              Expanded(
                child: GlassButton(
                  label: kind == 'payment' ? 'Live kholo' : 'Live dekho',
                  icon: Icons.open_in_full_rounded,
                  onTap: widget.inLive ? null : () => openOperatorLive(context, widget.app),
                ),
              ),
            if (kind == 'payment' || kind == 'takeover' || (!widget.inLive && kind != 'question' && kind != 'choice'))
              const SizedBox(width: 8),
            if (kind != 'choice')
              Expanded(
                child: GradientButton(
                  height: 48,
                  label: switch (kind) {
                    'approve' => 'Haan, karo',
                    'payment' || 'takeover' => 'Maine kar diya',
                    'question' => 'Bhejo',
                    'captcha' => suggestedAnswer.isNotEmpty ? 'Haan, sahi hai' : 'Page mein bharo',
                    _ => 'Page mein bharo',
                  },
                  onTap: _busy
                      ? null
                      : () {
                          if (kind == 'captcha') {
                            // v0.78: confirm suggested or use corrected value
                            final corrected = _box.text.trim();
                            final value = corrected.isNotEmpty ? corrected : suggestedAnswer;
                            if (value.isEmpty) {
                              _snack(context, 'CAPTCHA likhiye');
                              return;
                            }
                            _captchaFill(value);
                            return;
                          }
                          final t = _box.text.trim();
                          if ((typed || kind == 'question') && t.isEmpty) {
                            _snack(context, 'Pehle box mein likhiye');
                            return;
                          }
                          _answer(true, answer: t);
                        },
                ),
              ),
          ]),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: _busy ? null : () => _answer(false), child: Text(kind == 'approve' ? 'Mana' : 'Nahi karna')),
          ),
          if (kind == 'payment')
            const Text('Live screen par khud "Pay" dabaiye aur apne tareeke se pay kijiye. Hoola kabhi pay nahi karta.',
                style: TextStyle(color: C.faint, fontSize: 11.5)),
        ],
      ]),
    );
  }
}

/// The job card in chat: what Hoola is doing on the site, then the result (proof + files).
class OperatorTaskCard extends StatefulWidget {
  const OperatorTaskCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<OperatorTaskCard> createState() => _OperatorTaskCardState();
}

class _OperatorTaskCardState extends State<OperatorTaskCard> {
  Future<void> _stop() async {
    try {
      final r = await widget.app.api!.operatorCancel('${widget.v['id']}');
      widget.v.addAll(r);
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: widget.app,
        builder: (context, _) => _card(context),
      );

  Widget _card(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? 'queued'}';
    final live = _active.contains(status);
    final proof = List<String>.from(((v['proof'] as List?) ?? const []).map((e) => '$e'));
    final outs = List<Map<String, dynamic>>.from(((v['outputs'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Glass(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.computer_rounded, color: status == 'failed' ? C.bad : C.accent),
          const SizedBox(width: 8),
          Expanded(
            child: Text('${v['task'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
          ),
          Pill(switch (status) {
            'queued' => 'Line mein',
            'running' => 'Kaam chalu',
            'waiting' => 'Aapka intezaar',
            'done' => 'Ho gaya',
            'cancelled' => 'Rok diya',
            'stopped' => 'Ruk gaya',
            _ => 'Nahi hua',
          }, fg: status == 'done' ? C.ok : status == 'waiting' ? C.warn : status == 'failed' ? C.bad : C.accent),
        ]),
        const SizedBox(height: 4),
        Text([
          if ('${v['site'] ?? ''}'.isNotEmpty) '${v['site']}',
          if ((v['steps'] as num? ?? 0) > 0) '${v['steps']} kadam',
          if ('${v['stage'] ?? ''}'.isNotEmpty) '${v['stage']}',
        ].join(' · '), style: const TextStyle(color: C.faint, fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis),
        if (live && status != 'queued') ...[
          const SizedBox(height: 8),
          GestureDetector(onTap: () => openOperatorLive(context, widget.app), child: OperatorFrame(app: widget.app, every: 900)),
          Row(children: [
            TextButton.icon(onPressed: () => openOperatorLive(context, widget.app), icon: const Icon(Icons.open_in_full_rounded, size: 16),
                label: const Text('Live')),
            const Spacer(),
            TextButton(onPressed: _stop, child: const Text('Rok do')),
          ]),
        ],
        if (!live && '${v['summary'] ?? ''}'.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text('${v['summary']}', style: const TextStyle(fontSize: 13.5, height: 1.35)),
        ],
        if (proof.isNotEmpty) ...[
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: [for (final p in proof) Pill(p, fg: C.ok)]),
        ],
        if (outs.isNotEmpty) ...[
          const SizedBox(height: 6),
          for (final o in outs)
            Row(children: [
              Icon(o['file_id'] != null ? Icons.description_rounded : Icons.block_rounded, size: 16,
                  color: o['file_id'] != null ? C.accent : C.bad),
              const SizedBox(width: 6),
              Expanded(child: Text('${o['name']}${o['refused'] != null ? ' — ${o['refused']}' : ''}',
                  style: const TextStyle(fontSize: 12.5), overflow: TextOverflow.ellipsis)),
            ]),
        ],
        if ('${v['recipe'] ?? ''}'.isNotEmpty && !live)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('Seekh liya: ${v['recipe']} (agli baar tez)', style: const TextStyle(color: C.teal, fontSize: 12)),
          ),
        if (status == 'failed' && '${v['error'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 6), child: Text('${v['error']}', style: const TextStyle(color: C.bad, fontSize: 12.5))),
      ]),
    );
  }
}

/// Full screen live view: see Hoola's browser, answer its question, or do a step with your own hands.
class OperatorLiveScreen extends StatefulWidget {
  const OperatorLiveScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<OperatorLiveScreen> createState() => _OperatorLiveScreenState();
}

class _OperatorLiveScreenState extends State<OperatorLiveScreen> {
  final _txt = TextEditingController();
  Map<String, dynamic>? _job;
  Timer? _t;
  bool _hide = true;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 2), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    _txt.clear();
    _txt.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (app.api == null) return;
    try {
      final r = await app.api!.operatorHome();
      final a = r['active'];
      if (!mounted) return;
      setState(() => _job = a == null ? null : Map<String, dynamic>.from(a as Map));
    } catch (_) {}
  }

  Future<void> _input(String kind, {double x = 0, double y = 0, String text = '', String key = ''}) async {
    try {
      await app.api!.operatorInput(kind, x: x, y: y, text: text, key: key);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final job = _job;
    final pending = job == null ? null : job['pending'];
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${app.aName} ka browser')),
      body: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 28), children: [
        if (job != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text('${job['stage'] ?? ''}${'${job['site'] ?? ''}'.isNotEmpty ? ' · ${job['site']}' : ''}',
                style: const TextStyle(color: C.muted, fontSize: 13)),
          ),
        OperatorFrame(app: app, every: 500, onTapPage: (x, y) => _input('click', x: x, y: y)),
        const SizedBox(height: 6),
        const Text('Page par tap = aapka click. Hoola tab tak ruka rehta hai jab tak aap "Maine kar diya" na dabayein.',
            style: TextStyle(color: C.faint, fontSize: 11.5)),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: TextField(
              controller: _txt,
              obscureText: _hide,
              enableSuggestions: false,
              autocorrect: false,
              decoration: InputDecoration(
                hintText: 'Page mein likhiye (jahan aapne tap kiya)',
                isDense: true,
                filled: true,
                fillColor: C.panel,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                suffixIcon: IconButton(icon: Icon(_hide ? Icons.visibility : Icons.visibility_off, size: 18),
                    onPressed: () => setState(() => _hide = !_hide)),
              ),
            ),
          ),
          const SizedBox(width: 6),
          IconButton(
            icon: const Icon(Icons.keyboard_return_rounded, color: C.accent),
            tooltip: 'Likho',
            onPressed: () {
              final t = _txt.text;
              _txt.clear();
              if (t.isNotEmpty) _input('type', text: t);
            },
          ),
        ]),
        Wrap(spacing: 6, children: [
          for (final k in const ['Enter', 'Tab', 'Backspace', 'ArrowDown'])
            ActionChip(label: Text(k == 'Backspace' ? '⌫' : k == 'ArrowDown' ? '↓' : k), onPressed: () => _input('key', key: k)),
        ]),
        const SizedBox(height: 12),
        if (pending is Map) OperatorAskCard(key: ValueKey('live${pending['id']}'), v: Map<String, dynamic>.from(pending), app: app, inLive: true),
        if (job == null)
          const Padding(padding: EdgeInsets.all(16), child: Text('Abhi koi website ka kaam nahi chal raha.', style: TextStyle(color: C.faint))),
        if (job != null)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () async {
                await app.api!.operatorCancel('${job['id']}');
                _load();
              },
              child: const Text('Kaam rok do'),
            ),
          ),
      ]),
    );
  }
}

/// Profile > "<name> · Computer Operator": a new job, the jobs, what it learned.
class OperatorScreen extends StatefulWidget {
  const OperatorScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<OperatorScreen> createState() => _OperatorScreenState();
}

class _OperatorScreenState extends State<OperatorScreen> {
  final _task = TextEditingController();
  final _url = TextEditingController();
  final List<({String id, String name})> _files = [];
  Map<String, dynamic> _home = const {};
  bool _loading = true;
  bool _busy = false;
  int _tick = -1;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_onApp);
    _load();
  }

  @override
  void dispose() {
    app.removeListener(_onApp);
    _task.dispose();
    _url.dispose();
    super.dispose();
  }

  void _onApp() {
    if (app.operatorTick != _tick) {
      _tick = app.operatorTick;
      _load();
    }
  }

  Future<void> _load() async {
    if (app.api == null) return;
    try {
      final r = await app.api!.operatorHome();
      if (mounted) setState(() => _home = r);
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _attach() async {
    final picked = await pickAttachments(context, max: 8 - _files.length);
    for (final f in picked) {
      try {
        final r = await app.attachChatFile(f.name, f.bytes);
        setState(() => _files.add((id: '${r['file_id']}', name: f.name)));
      } catch (e) {
        if (mounted) _snack(context, 'Upload nahi hua: $e');
      }
    }
  }

  Future<void> _start() async {
    final t = _task.text.trim();
    if (t.length < 6) {
      _snack(context, 'Kya karna hai, thoda saaf likhiye');
      return;
    }
    setState(() => _busy = true);
    try {
      await app.api!.operatorStart(t, startUrl: _url.text.trim(), fileIds: _files.map((e) => e.id).toList(),
          conversationId: app.conversationId ?? '');
      _task.clear();
      _url.clear();
      _files.clear();
      if (mounted) _snack(context, '${app.aName} kaam par lag gaya. Chat mein live card hai.');
      await _load();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final active = _home['active'];
    final tasks = List<Map<String, dynamic>>.from(((_home['tasks'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    final recipes = List<Map<String, dynamic>>.from(((_home['recipes'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
    return Scaffold(
      backgroundColor: C.bgBottom,
      appBar: AppBar(backgroundColor: Colors.transparent, title: Text('${app.aName} · Computer Operator')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 28), children: [
          Glass(
            child: Text(
              'Cyber cafe wale bhaiya ki tarah: online form, sarkari portal, bill / certificate / statement download, '
              'status check, application. ${app.aName} apne browser mein kaam karta hai (aapke login wahin save rehte hain), '
              'official help padhta hai aur har poora kaam seekh leta hai. CAPTCHA Hoola khud padhta hai aur aapko dikhaata hai — '
              'aap sirf "Haan" kaho. Password aur OTP aap deti hain; submit se pehle aapki haan; payment aap khud dabati hain.',
              style: const TextStyle(fontSize: 13, height: 1.4, color: C.muted),
            ),
          ),
          if (_home['available'] == false)
            const Padding(
              padding: EdgeInsets.only(top: 10),
              child: Text('Is server par Computer Operator abhi chalu nahi hai (Chromium install karna hoga).', style: TextStyle(color: C.bad)),
            ),
          const SizedBox(height: 14),
          if (active is Map) ...[
            OperatorTaskCard(key: ValueKey('act${active['id']}${active['updated_at']}'), v: Map<String, dynamic>.from(active), app: app),
            const SizedBox(height: 10),
          ] else ...[
            const Text('Naya kaam', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            TextField(
              controller: _task,
              minLines: 3,
              maxLines: 6,
              decoration: InputDecoration(
                hintText: 'Jaise: "MSEDCL site se is mahine ka bill PDF download karo, consumer no. 1234..." ya '
                    '"Passport seva par appointment ka status dekho". Password / Aadhaar yahan mat likhiye.',
                hintStyle: const TextStyle(color: C.faint, fontSize: 13),
                filled: true,
                fillColor: C.panel,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _url,
              keyboardType: TextInputType.url,
              decoration: InputDecoration(
                hintText: 'Website (optional), jaise www.mahadiscom.in',
                isDense: true,
                filled: true,
                fillColor: C.panel,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final f in _files) InputChip(label: Text(f.name, overflow: TextOverflow.ellipsis), onDeleted: () => setState(() => _files.remove(f))),
              ActionChip(avatar: const Icon(Icons.attach_file_rounded, size: 18), label: const Text('Documents / photo'), onPressed: _attach),
            ]),
            const SizedBox(height: 12),
            GradientButton(label: _busy ? 'Shuru ho raha hai...' : 'Kaam do', icon: Icons.play_arrow_rounded, onTap: _busy ? null : _start),
          ],
          const SizedBox(height: 18),
          if (recipes.isNotEmpty) ...[
            const Text('Seekhe hue kaam', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final r in recipes)
              Glass(
                margin: const EdgeInsets.only(bottom: 8),
                child: Row(children: [
                  const Icon(Icons.auto_awesome_rounded, color: C.teal, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      Text('${r['site'] ?? ''} · ${r['runs'] ?? 0} baar · ${((r['variables'] as List?) ?? const []).length} cheezein poochta hai',
                          style: const TextStyle(color: C.faint, fontSize: 12)),
                    ]),
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline_rounded, color: C.faint),
                    onPressed: () async {
                      await app.api!.operatorForget('${r['name']}');
                      _load();
                    },
                  ),
                ]),
              ),
            const SizedBox(height: 10),
          ],
          if (tasks.isNotEmpty) const Text('Pichhle kaam', style: TextStyle(fontWeight: FontWeight.w700)),
          if (_loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
          for (final t in tasks.where((t) => !_active.contains(t['status'])))
            OperatorTaskCard(key: ValueKey('t${t['id']}${t['updated_at']}'), v: t, app: app),
        ]),
      ),
    );
  }
}
