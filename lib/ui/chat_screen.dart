import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../state.dart';
import 'glass.dart';
import 'live_santosh.dart';
import '../nav.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.app, this.onVoice});
  final Santosh app;
  final VoidCallback? onVoice;
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _text = TextEditingController();
  final _scroll = ScrollController();
  final SpeechToText _stt = SpeechToText();
  bool _sttReady = false;
  bool _listening = false;
  int _lastLen = 0;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    app.addListener(_autoScroll);
  }

  @override
  void dispose() {
    app.removeListener(_autoScroll);
    _stt.stop();
    super.dispose();
  }

  void _autoScroll() {
    if (app.feed.length != _lastLen) {
      _lastLen = app.feed.length;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) _scroll.animateTo(_scroll.position.maxScrollExtent + 80, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      });
    }
  }

  Future<void> _mic() async {
    if (_listening) {
      await _stt.stop();
      setState(() => _listening = false);
      return;
    }
    await app.stopSpeaking();
    _sttReady = _sttReady || await _stt.initialize(onStatus: (s) {
      if ((s == 'done' || s == 'notListening') && mounted) setState(() => _listening = false);
    });
    if (!_sttReady) {
      _snack('Microphone permission chahiye. Phone settings mein Santosh ko mic ki permission dijiye.');
      return;
    }
    setState(() => _listening = true);
    await _stt.listen(
      localeId: app.language.replaceAll('-', '_'),
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      onResult: (r) {
        _text.text = r.recognizedWords;
        if (r.finalResult && r.recognizedWords.trim().isNotEmpty) {
          app.send(r.recognizedWords, voice: true);
          _text.clear();
          setState(() => _listening = false);
        }
      },
    );
  }

  Future<void> _attach() async {
    final res = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['csv', 'xlsx'], withData: true);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    final err = await app.uploadLeads(f.name, f.bytes!);
    if (err != null) _snack('File upload nahi hui: $err');
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  void _send() {
    app.send(_text.text);
    _text.clear();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => Column(children: [
          _header(),
          if (app.error != null) _banner(app.error!, onTap: () => app.connect()),
          if (app.connected && !app.brainReady) _banner('Santosh ka dimaag server par connect nahi hai (ANTHROPIC_API_KEY).'),
          Expanded(
            child: ListView(controller: _scroll, padding: const EdgeInsets.fromLTRB(16, 8, 16, 12), children: [
              if (app.feed.length <= 1) _hero(),
              for (final it in app.feed) _item(it),
              if (app.typing) const Align(alignment: Alignment.centerLeft, child: _Typing()),
            ]),
          ),
          _quick(),
          _composer(),
        ]),
      );

  Widget _header() => Glass(
        margin: const EdgeInsets.fromLTRB(14, 8, 14, 6),
        padding: const EdgeInsets.all(10),
        child: Row(children: [
          LiveAvatar(online: app.connected, busy: app.typing),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Santosh', style: display(20, w: FontWeight.w700)),
              Text(!app.connected ? 'Connect ho raha hai…' : app.typing ? (app.currentStep ?? 'Kaam kar raha hoon…') : 'Online · ${languages[app.language] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: app.connected ? C.ok : C.muted)),
            ]),
          ),
          if (app.dryRun) const Pill('WHATSAPP TEST', fg: C.warn, bg: Color(0xE6FEF3C7)),
          if (widget.onVoice != null)
            IconButton(tooltip: 'Bolkar baat karein', onPressed: widget.onVoice, icon: const Icon(Icons.graphic_eq_rounded, color: C.accent)),
          IconButton(tooltip: 'Naya chat', onPressed: () => app.connect(fresh: true), icon: const Icon(Icons.add_comment_outlined, color: C.chip)),
        ]),
      );

  Widget _banner(String t, {VoidCallback? onTap}) => GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xE6FFEDD5), borderRadius: BorderRadius.circular(16)),
          child: Text(onTap == null ? t : '$t  (dobara koshish ke liye tap kijiye)', style: const TextStyle(fontSize: 13, color: Color(0xFF7C2D12))),
        ),
      );

  Widget _hero() => Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Column(children: [
          LiveSantosh(mood: app.typing ? 'working' : 'happy', size: 190),
          const SizedBox(height: 6),
          const Text('Boliye: "Kal subah 7 baje yaad dilana", "Doodh list mein daalo", "Pune ka mausam?"',
              textAlign: TextAlign.center, style: TextStyle(color: C.muted, fontSize: 13.5)),
        ]),
      );

  Widget _item(FeedItem it) {
    switch (it.kind) {
      case 'message':
        final me = it.data['role'] == 'user';
        final text = it.data['text'] as String? ?? '';
        final bubble = me
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                decoration: BoxDecoration(gradient: C.gradient, borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(22), topRight: Radius.circular(22), bottomLeft: Radius.circular(22), bottomRight: Radius.circular(8))),
                child: SelectableText(text, style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.45)),
              )
            : Glass(radius: 22, padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13), child: linkText(text, const TextStyle(fontSize: 15, height: 1.45, color: C.ink)));
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Align(
            alignment: me ? Alignment.centerRight : Alignment.centerLeft,
            child: ConstrainedBox(constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .82), child: bubble),
          ),
        );
      case 'steps':
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Glass(
              radius: 18,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                for (final s in it.steps)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      _stepDot(s['state'] as String? ?? ''),
                      const SizedBox(width: 10),
                      Flexible(child: Text(s['label'] as String? ?? '', style: const TextStyle(fontSize: 13, color: Color(0xFF3B3360)))),
                    ]),
                  ),
              ]),
            ),
          ),
        );
      case 'email':
        return _EmailCard(v: it.data, app: app);
      case 'campaign':
        return _CampaignCard(v: it.data, app: app);
      default:
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Align(alignment: Alignment.centerRight, child: Pill(it.data['text'] as String? ?? '', bg: const Color(0xCCFFFFFF))),
        );
    }
  }

  Widget _stepDot(String state) {
    if (state == 'running') {
      return const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.accent));
    }
    return Container(
      width: 20,
      height: 20,
      decoration: BoxDecoration(shape: BoxShape.circle, color: state == 'done' ? const Color(0xFF16A34A) : const Color(0xFFF59E0B)),
      child: Icon(state == 'done' ? Icons.check : Icons.priority_high, size: 13, color: Colors.white),
    );
  }

  Widget _quick() {
    const q = ['Kal subah 7 baje yaad dilana', 'Aaj ka mausam', 'Meri shopping list', 'Roz subah briefing bhejna'];
    return SizedBox(
      height: 44,
      child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 14), children: [
        for (final s in q)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ActionChip(label: Text(s), onPressed: () => app.send(s), backgroundColor: const Color(0xB3FFFFFF),
                labelStyle: const TextStyle(color: C.chip, fontWeight: FontWeight.w600, fontSize: 13)),
          ),
      ]),
    );
  }

  Widget _composer() => Glass(
        margin: const EdgeInsets.fromLTRB(14, 6, 14, 12),
        padding: const EdgeInsets.all(8),
        child: Row(children: [
          IconButton(tooltip: 'Leads file attach karein', onPressed: _attach, icon: const Icon(Icons.attach_file_rounded, color: C.chip)),
          Expanded(
            child: TextField(
              controller: _text,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _send(),
              decoration: InputDecoration(border: InputBorder.none, hintText: _listening ? 'Sun raha hoon…' : 'Santosh se boliye…'),
            ),
          ),
          ValueListenableBuilder(
            valueListenable: _text,
            builder: (context, v, _) {
              final typing = v.text.trim().isNotEmpty;
              return Semantics(
                button: true,
                label: typing ? 'Send' : (_listening ? 'Stop listening' : 'Speak to Santosh'),
                child: GestureDetector(
                  onTap: typing ? _send : _mic,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      gradient: C.gradient,
                      borderRadius: BorderRadius.circular(17),
                      boxShadow: [BoxShadow(color: const Color(0x5E7C3AED), blurRadius: _listening ? 26 : 16, spreadRadius: _listening ? 4 : 0)],
                    ),
                    child: Icon(typing ? Icons.send_rounded : (_listening ? Icons.stop_rounded : Icons.mic_rounded), color: Colors.white),
                  ),
                ),
              );
            },
          ),
        ]),
      );
}

class _Typing extends StatelessWidget {
  const _Typing();
  @override
  Widget build(BuildContext context) => const Glass(
        radius: 18,
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: SizedBox(width: 40, child: LinearProgressIndicator(minHeight: 4, color: C.accent, backgroundColor: Color(0x226D3FE0))),
      );
}

class _CampaignCard extends StatelessWidget {
  const _CampaignCard({required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  static const labels = {
    'awaiting_approval': 'Meta review', 'ready': 'Taiyaar', 'sending': 'Bhej raha hoon', 'completed': 'Poora',
    'failed': 'Ruk gaya', 'cancelled': 'Cancel', 'paused': 'Ruka hua', 'waiting_limit': 'Kal tak',
  };

  @override
  Widget build(BuildContext context) {
    final n = Map<String, dynamic>.from(v['counts'] as Map? ?? {});
    final status = v['status'] as String? ?? '';
    final tpl = Map<String, dynamic>.from(v['template'] as Map? ?? {});
    Widget stat(String label, Object? x) => Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 3),
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(color: const Color(0xB3FFFFFF), borderRadius: BorderRadius.circular(14)),
            child: Column(children: [
              Text('${x ?? 0}', style: display(22)),
              Text(label, style: const TextStyle(fontSize: 11, color: C.muted)),
            ]),
          ),
        );
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text(v['title'] as String? ?? 'Campaign', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(labels[status] ?? status),
          ]),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(value: ((v['progress'] as num?) ?? 0) / 100, minHeight: 7, color: C.accent, backgroundColor: const Color(0x1F6D3FE0)),
          ),
          const SizedBox(height: 10),
          Row(children: [stat('Bheje', n['sent']), stat('Pahunche', n['delivered']), stat('Padhe', n['read']), stat('Jawab', n['replied'])]),
          if ((tpl['preview'] ?? tpl['body']) != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: const Color(0xB3FFFFFF), borderRadius: BorderRadius.circular(14)),
              child: Text('${tpl['preview'] ?? tpl['body']}', style: const TextStyle(fontSize: 13, color: Color(0xFF3B3360))),
            ),
          ],
          if (status == 'ready') ...[const SizedBox(height: 10), GradientButton(label: 'Haan, bhej do', height: 46, onTap: () => app.campaignAction(v['id'], 'send'))],
          if (status == 'sending' || status == 'awaiting_approval')
            TextButton(onPressed: () => app.campaignAction(v['id'], 'pause'), child: const Text('Rokiye')),
          if (status == 'paused') TextButton(onPressed: () => app.campaignAction(v['id'], 'resume'), child: const Text('Phir se chalao')),
        ]),
      ),
    );
  }
}


/// A reply Santosh wrote, waiting for approval. Edit if needed, then Bhejo.
class _EmailCard extends StatelessWidget {
  const _EmailCard({required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'pending';
    final to = v['to'] as String? ?? '';
    final subject = v['subject'] as String? ?? '';
    final body = v['body'] as String? ?? '';
    Color chipFg = C.chip;
    String chipText = 'DRAFT';
    if (status == 'sent') { chipText = 'BHEJ DIYA'; chipFg = C.ok; }
    if (status == 'cancelled') { chipText = 'CANCEL'; chipFg = C.muted; }
    if (status == 'failed') { chipText = 'FAIL'; chipFg = C.bad; }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.mail_outline_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            const Expanded(child: Text('Email', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(chipText, fg: chipFg),
          ]),
          const SizedBox(height: 8),
          _row('Ko', to),
          if ((v['cc'] as String? ?? '').isNotEmpty) _row('Cc', v['cc'] as String),
          _row('Vishay', subject),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xB3FFFFFF), borderRadius: BorderRadius.circular(14)),
            child: Text(body, style: const TextStyle(fontSize: 13.5, height: 1.4, color: Color(0xFF3B3360))),
          ),
          if (v['error'] != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(v['error'] as String, style: const TextStyle(color: C.bad, fontSize: 12))),
          if (status == 'pending' || status == 'failed') ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: GradientButton(label: status == 'failed' ? 'Phir bhejo' : 'Bhejo', height: 46, icon: Icons.send_rounded,
                  onTap: () => app.sendEmail(v['id'] as String,
                      to: v['to'] as String?, cc: v['cc'] as String?, subject: v['subject'] as String?, body: v['body'] as String?))),
              const SizedBox(width: 8),
              IconButton(tooltip: 'Badlo', onPressed: () => _edit(context), icon: const Icon(Icons.edit_outlined, color: C.chip)),
              IconButton(tooltip: 'Cancel', onPressed: () => app.cancelEmail(v['id'] as String), icon: const Icon(Icons.close_rounded, color: C.muted)),
            ]),
          ],
        ]),
      ),
    );
  }

  Widget _row(String k, String val) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 48, child: Text(k, style: const TextStyle(color: C.muted, fontSize: 12.5, fontWeight: FontWeight.w600))),
          Expanded(child: Text(val, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600))),
        ]),
      );

  Future<void> _edit(BuildContext context) async {
    final to = TextEditingController(text: v['to'] as String? ?? '');
    final subject = TextEditingController(text: v['subject'] as String? ?? '');
    final body = TextEditingController(text: v['body'] as String? ?? '');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Email badlo'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: to, decoration: const InputDecoration(labelText: 'Ko (email)')),
            TextField(controller: subject, decoration: const InputDecoration(labelText: 'Vishay')),
            TextField(controller: body, minLines: 4, maxLines: 12, decoration: const InputDecoration(labelText: 'Email')),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Rehne do')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok == true) {
      v['to'] = to.text.trim();
      v['subject'] = subject.text.trim();
      v['body'] = body.text;
      app.notifyChange();
    }
  }
}
