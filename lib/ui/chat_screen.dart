import 'dart:math' as math;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../state.dart';
import 'approve_sheet.dart';
import 'artifact_screen.dart';
import 'browser_live.dart';
import 'calendar_screen.dart';
import 'sheets_screen.dart';
import 'slides_screen.dart';
import 'youtube_screen.dart';
import 'appcheck_screen.dart';
import 'hoola_cards.dart';
import 'forms_screen.dart';
import 'glass.dart';
import 'notebook_screen.dart';
import 'pc_screen.dart';
import 'photos_screen.dart';
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
      _snack('Microphone permission chahiye. Phone settings mein Hoola ko mic ki permission dijiye.');
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
          if (app.connected && !app.brainReady) _banner('Hoola ka dimaag server par connect nahi hai (ANTHROPIC_API_KEY).'),
          Expanded(
            child: ListView(controller: _scroll, padding: const EdgeInsets.fromLTRB(16, 8, 16, 12), children: [
              if (app.feed.length <= 1) _hero(),
              for (final it in app.feed) Stagger(key: ObjectKey(it), index: 0, child: _item(it)),
              if (app.typing) Align(alignment: Alignment.centerLeft, child: _Typing(step: app.currentStep)),
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
          LiveAvatar(online: app.connected, busy: app.typing, feeling: app.mood),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(app.aName, style: display(20, w: FontWeight.w700)),
              Text(!app.connected ? 'Connect ho raha hai…' : app.typing ? (app.currentStep ?? app.g('Kaam kar raha hoon…')) : 'Online · ${languages[app.language] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: app.connected ? C.ok : C.muted)),
            ]),
          ),
          if (app.dryRun) const Pill('WHATSAPP TEST', fg: C.warn, bg: Color(0x2EFFB15C)),
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
          decoration: BoxDecoration(color: const Color(0x2EFFB15C), borderRadius: BorderRadius.circular(16)),
          child: Text(onTap == null ? t : '$t  (dobara koshish ke liye tap kijiye)', style: const TextStyle(fontSize: 13, color: Color(0xFFFFD9A8))),
        ),
      );

  Widget _hero() => Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Column(children: [
          LiveSantosh(feeling: app.mood, size: 200, thought: true),
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
                decoration: BoxDecoration(gradient: C.youGradient, boxShadow: const [BoxShadow(color: Color(0x597C5CFF), blurRadius: 18, offset: Offset(0, 6))], borderRadius: const BorderRadius.only(
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
                      Flexible(child: Text(s['label'] as String? ?? '', style: const TextStyle(fontSize: 13, color: Color(0xFFD7D2F2)))),
                    ]),
                  ),
              ]),
            ),
          ),
        );
      case 'email':
        return _EmailCard(v: it.data, app: app);
      case 'calendar_event':
        return CalendarEventCard(v: it.data);
      case 'sheet':
        return SheetCard(v: it.data);
      case 'form':
        return FormCard(v: it.data);
      case 'slides':
        return SlidesCard(v: it.data);
      case 'notebook':
        return NotebookCard(v: it.data, app: app);
      case 'youtube':
        return YouTubeCard(v: it.data);
      case 'app_check':
        return AppCheckCard(v: it.data);
      case 'hoola_knock':
        return HoolaKnockCard(key: ValueKey('hk${it.data['id']}'), v: it.data, app: app);
      case 'hoola_connect':
        return HoolaConnectCard(key: ValueKey('hc${it.data['id']}'), v: it.data, app: app);
      case 'hoola_msg':
        return HoolaMsgCard(v: it.data, app: app);
      case 'hoola_group':
        return HoolaGroupCard(v: it.data, app: app);
      case 'hoola_group_post':
        return HoolaGroupPostCard(v: it.data, app: app);
      case 'photos_pick':
        return PhotosPickCard(v: it.data);
      case 'bazar':
        return _BazarCard(v: it.data, app: app);
      case 'open':
        return _OpenCard(v: it.data, app: app);
      case 'link':
        return _LinkCard(v: it.data, app: app);
      case 'pc_file':
        return PcFileCard(v: it.data, app: app);
      case 'artifact':
        return ArtifactCard(v: it.data, app: app);
      case 'browser':
        return BrowserLiveCard(v: it.data, app: app);
      case 'campaign':
        return _CampaignCard(v: it.data, app: app);
      default:
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Align(alignment: Alignment.centerRight, child: Pill(it.data['text'] as String? ?? '', bg: const Color(0x1FFFFFFF))),
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
      decoration: BoxDecoration(shape: BoxShape.circle, color: state == 'done' ? const Color(0xFF34D399) : const Color(0xFFFFC27A)),
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
            child: ActionChip(label: Text(s), onPressed: () => app.send(s), backgroundColor: const Color(0x14FFFFFF),
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
              decoration: InputDecoration(border: InputBorder.none, hintText: _listening ? app.g('Sun raha hoon…') : '${app.aName} se boliye…'),
            ),
          ),
          ValueListenableBuilder(
            valueListenable: _text,
            builder: (context, v, _) {
              final typing = v.text.trim().isNotEmpty;
              return Semantics(
                button: true,
                label: typing ? 'Send' : (_listening ? 'Stop listening' : 'Speak to ${app.aName}'),
                child: Press(
                  onTap: typing ? _send : _mic,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      gradient: C.gradient,
                      borderRadius: BorderRadius.circular(17),
                      boxShadow: [BoxShadow(color: const Color(0x59FFA046), blurRadius: _listening ? 26 : 16, spreadRadius: _listening ? 4 : 0)],
                    ),
                    child: Icon(typing ? Icons.send_rounded : (_listening ? Icons.stop_rounded : Icons.mic_rounded), color: C.onAccent),
                  ),
                ),
              );
            },
          ),
        ]),
      );
}

/// Santosh at work: his working pose, bouncing dots and what he is doing right now.
class _Typing extends StatefulWidget {
  const _Typing({this.step});
  final String? step;
  @override
  State<_Typing> createState() => _TypingState();
}

class _TypingState extends State<_Typing> with SingleTickerProviderStateMixin {
  late final AnimationController _t = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))..repeat();
  @override
  void dispose() {
    _t.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          AnimatedBuilder(
            animation: _t,
            builder: (context, c) => Transform.translate(offset: Offset(0, -3 * (math.sin(_t.value * 2 * math.pi)).abs()), child: c),
            child: Image.asset('assets/images/santosh_working.png', height: 74),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Glass(
              radius: 18,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                AnimatedBuilder(
                  animation: _t,
                  builder: (context, _) => Row(mainAxisSize: MainAxisSize.min, children: [
                    for (var i = 0; i < 3; i++)
                      Container(
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          color: C.accent.withOpacity(.35 + .65 * (math.sin((_t.value - i * .18) * 2 * math.pi) * .5 + .5)),
                          shape: BoxShape.circle,
                        ),
                      ),
                  ]),
                ),
                if (widget.step != null) ...[
                  const SizedBox(width: 10),
                  Flexible(child: Text(widget.step!, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C.chip))),
                ],
              ]),
            ),
          ),
        ]),
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
            decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(14)),
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
              decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(14)),
              child: Text('${tpl['preview'] ?? tpl['body']}', style: const TextStyle(fontSize: 13, color: Color(0xFFD7D2F2))),
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

  static String _size(num? b) {
    final x = (b ?? 0).toDouble();
    if (x >= 1024 * 1024) return '${(x / 1024 / 1024).toStringAsFixed(1)} MB';
    if (x >= 1024) return '${(x / 1024).toStringAsFixed(0)} KB';
    return x > 0 ? '${x.toInt()} B' : '';
  }

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'pending';
    final busy = v['busy'] == true;
    final to = v['to'] as String? ?? '';
    final subject = v['subject'] as String? ?? '';
    final body = v['body'] as String? ?? '';
    final kind = v['kind'] as String? ?? 'new';
    final atts = (v['attachments'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final when = v['send_at_label'] as String?;
    final editable = status == 'pending' || status == 'failed';
    Color chipFg = C.chip;
    String chipText = when != null ? 'DRAFT · $when' : 'DRAFT';
    if (status == 'sent') { chipText = 'BHEJ DIYA'; chipFg = C.ok; }
    if (status == 'sending') { chipText = 'JA RAHA HAI'; chipFg = C.accentSoft; }
    if (status == 'scheduled') { chipText = 'BHEJEGA · ${when ?? ''}'; chipFg = C.warn; }
    if (status == 'cancelled') { chipText = 'CANCEL'; chipFg = C.muted; }
    if (status == 'failed') { chipText = 'FAIL'; chipFg = C.bad; }
    final title = kind == 'reply' ? 'Email · jawab' : kind == 'forward' ? 'Email · forward' : 'Email';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Icon(Icons.mail_outline_rounded, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Flexible(child: Pill(chipText, fg: chipFg)),
          ]),
          const SizedBox(height: 8),
          _row('Ko', to),
          if ((v['cc'] as String? ?? '').isNotEmpty) _row('Cc', v['cc'] as String),
          if ((v['bcc'] as String? ?? '').isNotEmpty) _row('Bcc', v['bcc'] as String),
          _row('Vishay', subject),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            constraints: const BoxConstraints(maxHeight: 320),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(14)),
            child: SingleChildScrollView(child: Text(body, style: const TextStyle(fontSize: 13.5, height: 1.4, color: Color(0xFFD7D2F2)))),
          ),
          if (atts.isNotEmpty || editable) ...[
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (var i = 0; i < atts.length; i++)
                InputChip(
                  avatar: const Icon(Icons.attach_file_rounded, size: 16, color: C.chip),
                  label: Text('${atts[i]['name']}  ${_size(atts[i]['size'] as num?)}'.trim(), style: const TextStyle(fontSize: 12.5)),
                  onDeleted: editable && !busy ? () => app.removeEmailAttachment(v['id'] as String, i) : null,
                ),
              if (editable)
                ActionChip(
                  avatar: const Icon(Icons.add_rounded, size: 16, color: C.accent),
                  label: const Text('File jodiye', style: TextStyle(fontSize: 12.5)),
                  onPressed: busy ? null : () => _attach(context),
                ),
            ]),
          ],
          if (v['error'] != null && status == 'failed')
            Padding(padding: const EdgeInsets.only(top: 6), child: Text(v['error'] as String, style: const TextStyle(color: C.bad, fontSize: 12))),
          if (editable) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: GradientButton(
                  label: busy ? 'Bhej raha hoon…' : status == 'failed' ? 'Phir bhejo' : when != null ? 'Bhejo · $when' : 'Bhejo',
                  height: 46, icon: when != null ? Icons.schedule_send_rounded : Icons.send_rounded,
                  onTap: busy ? null : () => app.sendEmail(v['id'] as String,
                      to: v['to'] as String?, cc: v['cc'] as String?, subject: v['subject'] as String?, body: v['body'] as String?))),
              const SizedBox(width: 8),
              IconButton(tooltip: 'Badlo', onPressed: busy ? null : () => _edit(context), icon: const Icon(Icons.edit_outlined, color: C.chip)),
              IconButton(tooltip: 'Cancel', onPressed: busy ? null : () => app.cancelEmail(v['id'] as String), icon: const Icon(Icons.close_rounded, color: C.muted)),
            ]),
          ],
          if (status == 'scheduled')
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(children: [
                TextButton.icon(onPressed: busy ? null : () => app.sendEmail(v['id'] as String, sendNow: true),
                    icon: const Icon(Icons.send_rounded, size: 18), label: const Text('Abhi bhejo')),
                const Spacer(),
                TextButton(onPressed: busy ? null : () => app.cancelEmail(v['id'] as String), child: const Text('Cancel', style: TextStyle(color: C.muted))),
              ]),
            ),
        ]),
      ),
    );
  }

  Future<void> _attach(BuildContext context) async {
    final res = await FilePicker.platform.pickFiles(withData: true);
    final f = res?.files.single;
    if (f == null || f.bytes == null) return;
    final err = await app.addEmailAttachment(v['id'] as String, f.name, f.bytes!);
    if (err != null && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
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
    final cc = TextEditingController(text: v['cc'] as String? ?? '');
    final subject = TextEditingController(text: v['subject'] as String? ?? '');
    final body = TextEditingController(text: v['body'] as String? ?? '');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Email badlo'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: to, decoration: const InputDecoration(labelText: 'Ko (email)')),
            TextField(controller: cc, decoration: const InputDecoration(labelText: 'Cc')),
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
      v['cc'] = cc.text.trim();
      v['subject'] = subject.text.trim();
      v['body'] = body.text;
      app.notifyChange();
    }
  }
}


/// Santosh Bazar confirm card. Amount, payee and items come from the server, never from the chat text.
class _BazarCard extends StatelessWidget {
  const _BazarCard({required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) {
    final status = v['status'] as String? ?? 'pending';
    final busy = v['busy'] == true;
    final items = (v['items'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final demo = v['demo'] == true;
    final result = v['result'] as Map?;
    final open = result?['open'] as Map?;
    String chip = 'APPROVE KAREIN';
    Color chipFg = C.warn;
    if (status == 'approved' || status == 'auto') { chip = 'APPROVED'; chipFg = C.ok; }
    if (status == 'rejected') { chip = 'CANCEL'; chipFg = C.muted; }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(v['tier'] == 3 ? Icons.currency_rupee_rounded : Icons.shopping_bag_outlined, color: C.accent, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text((v['title'] as String? ?? '').replaceFirst('[DEMO] ', ''),
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5))),
            Pill(chip, fg: chipFg),
          ]),
          if (demo) const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('DEMO: test bill hai, asli paise nahi katenge.', style: TextStyle(color: C.warn, fontSize: 12.5, fontWeight: FontWeight.w600))),
          const SizedBox(height: 8),
          if ((v['payee'] as String? ?? '').isNotEmpty)
            Text('Kisko: ${v['payee']}', style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          for (final i in items.take(12))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(children: [
                Expanded(child: Text(i['name'] as String? ?? '', style: const TextStyle(fontSize: 13.5, color: Color(0xFFD7D2F2)))),
                Text(i['price'] as String? ?? '', style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
              ]),
            ),
          if ((v['amount'] as String? ?? '').isNotEmpty) ...[
            const Divider(height: 16),
            Row(children: [
              const Expanded(child: Text('Total', style: TextStyle(fontWeight: FontWeight.w700))),
              Text(v['amount'] as String, style: display(20, w: FontWeight.w700)),
            ]),
          ],
          const SizedBox(height: 4),
          Text(v['pay_method'] as String? ?? '', style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (v['needs_pin'] == true && status == 'pending')
            const Text('UPI PIN sirf aapke UPI app mein daaliye. Hoola kabhi PIN nahi maangega.', style: TextStyle(color: C.muted, fontSize: 12)),
          if (status == 'pending') ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: GradientButton(label: busy ? 'Ho raha hai…' : 'Approve karein', height: 46, icon: Icons.check_rounded,
                  onTap: busy ? null : () => showApproveSheet(context, app, v))),
              const SizedBox(width: 8),
              TextButton(onPressed: busy ? null : () => app.decideBazar(v['id'] as String, 'reject'), child: const Text('Cancel')),
            ]),
          ],
          if (result != null && (result['message'] as String? ?? '').isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 8), child: Text(result['message'] as String, style: const TextStyle(fontSize: 13))),
          if (open != null && status != 'pending') ...[
            const SizedBox(height: 8),
            _openButtons(context, app, Map<String, dynamic>.from(open)),
          ],
        ]),
      ),
    );
  }
}

Widget _openButtons(BuildContext context, Santosh app, Map<String, dynamic> open) {
  if (open['kind'] == 'links') {
    final links = (open['links'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    return Wrap(spacing: 8, runSpacing: 8, children: [
      for (final l in links)
        ActionChip(avatar: const Icon(Icons.send_rounded, size: 16), label: Text(l['name'] as String? ?? ''),
            onPressed: () => app.openBazar({'url': l['url']})),
    ]);
  }
  if (open['kind'] == 'share') {
    return SelectableText(open['text'] as String? ?? '', style: const TextStyle(fontSize: 13));
  }
  return OutlinedButton.icon(
    icon: Icon(open['kind'] == 'upi' ? Icons.currency_rupee_rounded : Icons.open_in_new_rounded),
    label: Text(open['label'] as String? ?? 'Kholiye'),
    onPressed: () async {
      final r = await app.openBazar(open);
      if (r != 'ok' && context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(r)));
    },
  );
}

class _OpenCard extends StatelessWidget {
  const _OpenCard({required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(v['pack'] as String? ?? '', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            if ((v['message'] as String? ?? '').isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text(v['message'] as String, style: const TextStyle(fontSize: 13))),
            const SizedBox(height: 8),
            _openButtons(context, app, v),
          ]),
        ),
      );
}

class _LinkCard extends StatelessWidget {
  const _LinkCard({required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('${v['name']} jodiye', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('Ek baar apne account se login kijiye (OTP unke page par aayega). Phir Hoola aapke liye order kar sakta hai.',
                    style: TextStyle(fontSize: 13))),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.link_rounded),
              label: Text('${v['name']} link karein'),
              onPressed: () async {
                final err = await app.linkApp(v['pack_id'] as String);
                if (err != null && context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
              },
            ),
          ]),
        ),
      );
}
