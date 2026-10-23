import 'dart:io' show File;
import 'dart:math' as math;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../state.dart';
import 'employee_inbox.dart';
import 'chai_screen.dart';
import 'darzi_screen.dart';
import 'lekhak_screen.dart';
import 'office_screen.dart';
import 'employee_screen.dart';
import 'mshop_screen.dart';
import 'phonedoc_screen.dart';
import 'gst_screen.dart';
import 'payroll_screen.dart';
import 'finance_screen.dart';
import 'audit_screen.dart';
import 'insurance_screen.dart';
import 'ads_screen.dart';
import 'brand_screen.dart';
import 'aftersales_screen.dart';
import 'callcentre_screen.dart';
import 'feedback_screen.dart';
import 'helpdesk_screen.dart';
import 'samudaay_screen.dart';
import 'seva_screen.dart';
import 'shikayat_screen.dart';
import 'wapsi_screen.dart';
import 'appreview_screen.dart';
import 'cyber_screen.dart';
import 'devops_screen.dart';
import 'devsahayak_screen.dart';
import 'docwriter_screen.dart';
import 'ispnoc_screen.dart';
import 'itadmin_screen.dart';
import 'product_screen.dart';
import 'qa_screen.dart';
import 'courier_screen.dart';
import 'customs_screen.dart';
import 'drivers_screen.dart';
import 'fleet_screen.dart';
import 'logistics_screen.dart';
import 'travel_screen.dart';
import 'warehouse_screen.dart';
import 'archassist_screen.dart';
import 'interior_screen.dart';
import 'propagent_screen.dart';
import 'rentdesk_screen.dart';
import 'sitesup_screen.dart';
import 'society_screen.dart';
import 'vakil_screen.dart';
import 'legalres_screen.dart';
import 'compliance_screen.dart';
import 'contracts_screen.dart';
import 'cosec_screen.dart';
import 'notary_screen.dart';
import 'pidesk_screen.dart';
import 'dpo_screen.dart';
import 'frontoffice_screen.dart';
import 'eventplan_screen.dart';
import 'shaadi_screen.dart';
import 'tourguide_screen.dart';
import 'homestay_screen.dart';
import 'banquet_screen.dart';
import 'site_hosting.dart';
import 'site_screen.dart';
import 'app_android.dart';
import 'app_design_screen.dart';
import 'kalam_screen.dart';
import 'seo_screen.dart';
import 'thok_screen.dart';
import 'niryat_screen.dart';
import 'franchise_screen.dart';
import 'theka_screen.dart';
import 'telecall_screen.dart';
import 'video_editor.dart';
import 'operator_screen.dart';
import 'studio_screen.dart';
import 'procedures_screen.dart';
import 'call_receipt.dart';
import 'desk_cards.dart';
import 'blender_screen.dart';
import 'photo_card.dart';
import 'upi_result_card.dart';
import 'ask_form_card.dart';
import 'call_rate_card.dart';
import 'approve_sheet.dart';
import 'artifact_screen.dart';
import 'browser_live.dart';
import 'calendar_screen.dart';
import 'drive_screen.dart';
import 'sheets_screen.dart';
import 'slides_screen.dart';
import 'youtube_screen.dart';
import 'appcheck_screen.dart';
import 'motion_screen.dart';
import 'hoola_cards.dart';
import 'deal_screen.dart';
import 'market_screen.dart';
import 'handoff_screen.dart';
import 'hoola_media.dart';
import 'attach.dart';
import 'forms_screen.dart';
import 'glass.dart';
import 'notebook_screen.dart';
import 'pc_screen.dart';
import 'photos_screen.dart';
import 'live_santosh.dart';
import 'work_theatre.dart';
import 'gyaan_screen.dart';
import 'postgres_screen.dart' show PgWriteCard;
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
  bool _away = false;            // scrolled up, away from the newest message
  int _unseen = 0;               // new items that arrived while scrolled up
  /// Items already on screen when Chat opened (history): they show at once, only new ones animate in.
  late final Set<FeedItem> _old = app.feed.toSet();
  final Set<FeedItem> _animated = {};

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _lastLen = app.feed.length;
    app.addListener(_autoScroll);
    app.addListener(_maybeShare);
    _scroll.addListener(_onScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) => _maybeShare());
  }

  /// v0.49 "Share to Hoola" from another app: the files wait in the box (uploaded), the text goes in the box.
  Future<void> _maybeShare() async {
    if (app.pendingShare == null || !mounted) return;
    final s = app.takeShare();
    if (s == null) return;
    final text = (s['text'] as String? ?? '').trim();
    if (text.isNotEmpty && _text.text.trim().isEmpty) _text.text = text;
    if ((s['skipped'] as num? ?? 0) > 0) {
      final names = List<String>.from((s['skipped_names'] as List? ?? const []).map((e) => '$e'));
      _snack('${names.isEmpty ? '${s['skipped']} file' : names.join(', ')}: nahi le paye (25 MB se badi, 6 se zyada, ya padh nahi paye). '
          'Badi file Google Drive link se bhejiye.');
    }
    for (final f in List<Map<String, dynamic>>.from((s['files'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)))) {
      if (_files.length >= 6) break;
      final name = f['name'] as String? ?? 'file';
      setState(() => _uploading.add(name));
      try {
        final bytes = await File(f['path'] as String).readAsBytes();
        final r = await app.attachChatFile(name, bytes);
        if (mounted) setState(() => _files.add(r));
      } catch (e) {
        if (mounted) _snack('$name: $e');
      } finally {
        if (mounted) setState(() => _uploading.remove(name));
      }
    }
  }

  @override
  void dispose() {
    app.removeListener(_autoScroll);
    app.removeListener(_maybeShare);
    _scroll.dispose();
    _stt.stop();
    super.dispose();
  }

  // The list is reversed: offset 0 is the newest message, so Chat always opens at the latest conversation.
  void _onScroll() {
    final away = _scroll.hasClients && _scroll.offset > 240;
    if (away != _away) setState(() {
      _away = away;
      if (!away) _unseen = 0;
    });
  }

  void _autoScroll() {
    if (app.feed.length == _lastLen) return;
    final added = app.feed.length - _lastLen;
    _lastLen = app.feed.length;
    if (added <= 0) return;
    if (app.replaying || added > 2) _old.addAll(app.feed.sublist(app.feed.length - added));   // history: no animation
    if (_away) {
      if (mounted) setState(() => _unseen += added);
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients && _scroll.offset > 0) {
        _scroll.animateTo(0, duration: const Duration(milliseconds: 380), curve: Curves.easeOutCubic);
      }
    });
  }

  void _toBottom() {
    if (!_scroll.hasClients) return;
    final far = _scroll.offset > 4000;
    if (far) _scroll.jumpTo(800);   // a long way up: jump most of it, then glide the rest
    _scroll.animateTo(0, duration: const Duration(milliseconds: 420), curve: Curves.easeOutCubic);
    setState(() => _unseen = 0);
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

  /// Files waiting in the box (uploaded, sent with the next message). Any type: photo, PDF, video, Excel...
  final List<Map<String, dynamic>> _files = [];
  final Set<String> _uploading = {};

  Future<void> _attach() async {
    final picked = await pickAttachments(context, max: 6 - _files.length);
    for (final f in picked) {
      setState(() => _uploading.add(f.name));
      try {
        final r = await app.attachChatFile(f.name, f.bytes);
        if (mounted) setState(() => _files.add(r));
      } catch (e) {
        if (mounted) _snack('${f.name}: $e');
      } finally {
        if (mounted) setState(() => _uploading.remove(f.name));
      }
    }
  }

  Widget _pendingFiles() => (_files.isEmpty && _uploading.isEmpty)
      ? const SizedBox.shrink()
      : SizedBox(
          height: 40,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 18), children: [
            for (final n in _uploading)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: Chip(
                  avatar: const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                  label: Text(n, style: const TextStyle(fontSize: 12)),
                ),
              ),
            for (final f in List<Map<String, dynamic>>.from(_files))
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: InputChip(
                  avatar: Icon(hoolaFileIcon(f['media'] as String? ?? ''), size: 16, color: C.accentSoft),
                  label: Text('${f['name']}${f['leads'] != null ? ' · ${(f['leads'] as Map)['valid']} number' : ''}',
                      style: const TextStyle(fontSize: 12)),
                  onDeleted: () => setState(() => _files.remove(f)),
                ),
              ),
          ]),
        );

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  /// The text goes back into the box if it could not be sent, so nothing typed is lost on a bad network.
  Future<void> _send() async {
    var t = _text.text;
    final files = List<Map<String, dynamic>>.from(_files);
    if (t.trim().isEmpty && files.isEmpty) return;
    if (t.trim().isEmpty) t = files.map((f) => '📎 ${f['name']}').join('\n');
    _text.clear();
    setState(() => _files.clear());
    final ok = await app.send(t, files: [for (final f in files) '${f['file_id']}']);
    if (!ok && mounted) {
      setState(() => _files.addAll(files));
      if (_text.text.isEmpty) {
        _text.text = t;
        _text.selection = TextSelection.collapsed(offset: t.length);
      }
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: app,
        builder: (context, _) => Column(children: [
          _header(),
          if (app.error != null) _banner(app.error!, onTap: () => app.connect()),
          if (app.connected && !app.brainReady) _banner('Hoola ka dimaag server par connect nahi hai (ANTHROPIC_API_KEY).'),
          WorkTheatrePanel(app: app),
          Expanded(child: Stack(children: [
            Positioned.fill(child: _list()),
            Positioned(
              right: 16,
              bottom: 10,
              child: IgnorePointer(
                ignoring: !_away,
                child: AnimatedScale(
                  scale: _away ? 1 : .6,
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOutBack,
                  child: AnimatedOpacity(
                    opacity: _away ? 1 : 0,
                    duration: const Duration(milliseconds: 180),
                    child: _DownButton(count: _unseen, onTap: _toBottom),
                  ),
                ),
              ),
            ),
          ])),
          _quick(),
          _pendingFiles(),
          _composer(),
        ]),
      );

  /// Newest at the bottom; the list is reversed so it always opens on the latest conversation and stays there.
  Widget _list() {
    final feed = app.feed;
    final extra = (app.typing ? 1 : 0);
    final hero = feed.length <= 1 ? 1 : 0;
    return ListView.builder(
      controller: _scroll,
      reverse: true,
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      itemCount: extra + feed.length + hero,
      itemBuilder: (context, i) {
        if (app.typing && i == 0) {
          return Align(alignment: Alignment.centerLeft, child: _Arrive(key: const ValueKey('typing'), child: _Typing(step: app.currentStep)));
        }
        final k = i - extra;
        if (k >= feed.length) return _hero();
        final it = feed[feed.length - 1 - k];
        final fresh = !_old.contains(it) && !_animated.contains(it);
        if (fresh) _animated.add(it);
        final child = _item(it, fresh: fresh);
        return KeyedSubtree(key: ObjectKey(it), child: fresh ? _Arrive(card: it.kind != 'message', child: child) : child);
      },
    );
  }

  Widget _header() => Glass(
        margin: const EdgeInsets.fromLTRB(14, 8, 14, 6),
        padding: const EdgeInsets.all(10),
        child: Row(children: [
          LiveAvatar(online: app.connected, busy: app.typing, feeling: app.mood),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(app.aName, maxLines: 1, overflow: TextOverflow.ellipsis, softWrap: false, style: display(20, w: FontWeight.w700)),
              Text(!app.connected ? 'Connect ho raha hai…' : app.typing ? (app.currentStep ?? app.g('Kaam kar raha hoon…')) : 'Online · ${languages[app.language] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: app.connected ? C.ok : C.muted)),
            ]),
          ),
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

  Widget _item(FeedItem it, {bool fresh = false}) {
    switch (it.kind) {
      case 'message':
        final me = it.data['role'] == 'user';
        final text = it.data['text'] as String? ?? '';
        final bubble = me
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                decoration: BoxDecoration(gradient: C.youGradient, boxShadow: const [BoxShadow(color: Color(0x597C5CFF), blurRadius: 18, offset: Offset(0, 6))], borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(22), topRight: Radius.circular(22), bottomLeft: Radius.circular(22), bottomRight: Radius.circular(8))),
                child: Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
                  for (final f in (it.data['files'] as List? ?? const []))
                    if (f is Map) HoolaMediaTile(body: {'local': Map<String, dynamic>.from(f)}, app: app, maxWidth: 230),
                  for (final f in (it.data['files'] as List? ?? const []))
                    if (f is Map && f['codes'] is List) QrNote(codes: f['codes'] as List),
                  if ((it.data['files'] as List? ?? const []).isNotEmpty) const SizedBox(height: 6),
                  SelectableText(text, style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.45)),
                ]),
              )
            : Glass(
                radius: 22,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                child: fresh
                    ? _Reveal(text: text, builder: (t) => linkText(t, const TextStyle(fontSize: 15, height: 1.45, color: C.ink)))
                    : linkText(text, const TextStyle(fontSize: 15, height: 1.45, color: C.ink)));
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
      default:
        final card = feedCard(context, app, it);
        if (card != null) return card;
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
          IconButton(tooltip: 'Photo, PDF, video ya koi bhi file', onPressed: _attach, icon: const Icon(Icons.attach_file_rounded, color: C.chip)),
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
              final typing = v.text.trim().isNotEmpty || _files.isNotEmpty;
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

/// The card for one feed item (approvals, downloads, drafts, Hoola Network...). Shared by Chat and the live call, so
/// nothing that needs a tap is ever only in Chat. Returns null for plain messages and notes.
Widget? feedCard(BuildContext context, Santosh app, FeedItem it) {
  switch (it.kind) {
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
    case 'motion':
      return MotionCard(v: it.data);
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
    case 'hoola_outbox':
      return HoolaOutboxCard(v: it.data, app: app);
    case 'hoola_pick':
      return PickCard(key: ValueKey('hp${it.data['id']}${it.data['status']}'), v: it.data, app: app);
    case 'hoola_khata':
      return KhataCard(v: it.data, app: app);
    case 'hoola_rfq':
      return CompareCard(key: ValueKey('rq${it.data['id']}${it.data['state']}'), v: it.data, app: app);
    case 'a2a_task':
      return A2ATaskCard(key: ValueKey('a2a${(it.data['task'] as Map?)?['id']}${(it.data['task'] as Map?)?['updated_at']}'), v: it.data, app: app);
    case 'a2a_out':
      return A2AOutCard(key: ValueKey('ao${(it.data['out'] as Map?)?['id']}${(it.data['out'] as Map?)?['updated_at']}'), v: it.data, app: app);
    case 'handoff_reminder':
      return ConsentReminderCard(v: it.data, app: app);
    case 'digilocker':
      return DigiLockerCard(v: it.data, app: app);
    case 'hoola_mandate':
      return MandateCard(key: ValueKey('md${it.data['id']}${it.data['state']}'), v: it.data, app: app);
    case 'hoola_promo':
      return PromoCard(key: ValueKey('pr${it.data['id']}'), v: it.data, app: app);
    case 'hoola_deal':
      return DealCard(key: ValueKey('hd${it.data['id']}${it.data['state']}${it.data['updated']}'), v: it.data, app: app);
    case 'hoola_chain':
      return HoolaChainCard(v: it.data, app: app);
    case 'hoola_ticket':
      return HoolaTicketCard(v: it.data, app: app);
    case 'hoola_lesson':
      return HoolaLessonCard(v: it.data, app: app);
    case 'hoola_samaj':
      return HoolaSamajCard(v: it.data, app: app);
    case 'photos_pick':
      return PhotosPickCard(v: it.data);
    case 'bazar':
      return _BazarCard(v: it.data, app: app);
    case 'open':
      return _OpenCard(v: it.data, app: app);
    case 'link':
      return _LinkCard(v: it.data, app: app);
    case 'employee_ask':
      return EmployeeAskCard(key: ValueKey('ea${it.data['id']}'), v: it.data, app: app);
    case 'studio':
      return StudioCard(key: ValueKey('sp${it.data['project']}'), v: it.data, app: app);
    case 'google_reconnect':
      return GoogleReconnectCard(v: it.data, app: app);
    case 'studio_approval':
      return StudioApprovalCard(key: ValueKey('sa${it.data['id']}'), v: it.data, app: app);
    case 'operator_task':
      return OperatorTaskCard(key: ValueKey('ot${it.data['id']}'), v: it.data, app: app);
    case 'operator_ask':
      return OperatorAskCard(key: ValueKey('oq${it.data['id']}'), v: it.data, app: app);
    case 'video_job':
      return VideoJobCard(key: ValueKey('vj${it.data['id']}'), v: it.data, app: app);
    case 'mshop_bill':
      return MShopBillCard(key: ValueKey('mb${it.data['job_id']}${it.data['status']}'), v: it.data, app: app);
    case 'mshop_ready':
      return MShopReadyCard(key: ValueKey('mr${it.data['job_id']}'), v: it.data, app: app);
    case 'mshop_day':
      return MShopDayCard(v: it.data, app: app);
    case 'theka_bill':
    case 'theka_letter':
    case 'theka_day':
      return ThekaCard(key: ValueKey('tk${it.data['bill_id'] ?? it.data['text'] ?? it.data['title']}'), v: it.data, app: app);
    case 'fr_statement':
    case 'fr_day':
      return FrStatementCard(key: ValueKey('fr${it.data['statement_id'] ?? it.data['text']}'), v: it.data, app: app);
    case 'niryat_pi':
    case 'niryat_day':
      return NiryatCard(key: ValueKey('np${it.data['shipment_id'] ?? it.data['text']}'), v: it.data, app: app);
    case 'thok_order':
      return ThokOrderCard(key: ValueKey('to${it.data['order_id']}'), v: it.data, app: app);
    case 'thok_alert':
    case 'thok_day':
      return ThokCard(v: it.data, app: app);
    case 'seo_update':
    case 'seo_week':
    case 'seo_alert':
    case 'seo_draft':
      return SeoCard(kind: it.kind, v: it.data, app: app);
    case 'ins_day':
    case 'ins_advice':
      return InsCard(key: ValueKey('ins${it.data['advice_id'] ?? it.data['text']}'), v: it.data, app: app);
    case 'audit_update':
      return AuditCard(v: it.data, app: app);
    case 'tele_day':
      return TeleDayCard(v: it.data, app: app);
    // v0.133 Seva suite
    case 'seva_exception':
      return SevaExceptionCard(key: ValueKey('sx${it.data['id']}'), app: app, data: it.data);
    case 'seva_ticket':
      return SevaTicketCard(app: app, data: it.data);
    case 'seva_sla':
      return SevaTicketCard(app: app, data: it.data);
    case 'gyaan_sources':
      return GyaanSourcesCard(app: app, data: it.data);
    case 'seva_day':
      return SevaDayCard(app: app, data: it.data);
    case 'helpdesk_ticket':
      return HelpdeskTicketCard(key: ValueKey('ht${it.data['ticket']}'), app: app, data: it.data);
    case 'helpdesk_change':
      return HelpdeskChangeCard(key: ValueKey('hc${(it.data['change'] as Map?)?['id']}'), app: app, data: it.data);
    case 'helpdesk_escalate':
      return HelpdeskEscalateCard(app: app, data: it.data);
    case 'helpdesk_alert':
      return HelpdeskAlertCard(app: app, data: it.data);
    case 'helpdesk_day':
      return HelpdeskDayCard(app: app, data: it.data);
    case 'shikayat_comp':
      return ShikayatCompCard(key: ValueKey('sc${(it.data['comp'] as Map?)?['id']}'), app: app, data: it.data);
    case 'shikayat_case':
      return ShikayatCaseCard(app: app, data: it.data);
    case 'shikayat_message':
      return ShikayatMessageCard(app: app, data: it.data);
    case 'shikayat_day':
      return ShikayatNoteCard(app: app, data: it.data);
    case 'shikayat_alert':
      return ShikayatNoteCard(app: app, data: it.data);
    case 'aftersales_charge':
      return AftersalesChargeCard(key: ValueKey('ac${it.data['visit_id']}'), app: app, data: it.data);
    case 'aftersales_reminders':
      return AftersalesRemindersCard(app: app, data: it.data);
    case 'aftersales_visit':
      return AftersalesVisitCard(app: app, data: it.data);
    case 'aftersales_report':
      return AftersalesReportCard(app: app, data: it.data);
    case 'aftersales_day':
      return AftersalesDayCard(app: app, data: it.data);
    case 'feedback_reply':
      return FeedbackReplyCard(key: ValueKey('fr${it.data['reply_id']}'), app: app, data: it.data);
    case 'feedback_alert':
      return FeedbackNoteCard(app: app, data: it.data);
    case 'feedback_report':
      return FeedbackNoteCard(app: app, data: it.data);
    case 'feedback_update':
      return FeedbackNoteCard(app: app, data: it.data);
    case 'feedback_survey':
      return FeedbackSurveyCard(app: app, data: it.data);
    case 'wapsi_refund':
      return WapsiRefundCard(key: ValueKey('wr${(it.data['refund'] as Map?)?['id']}'), app: app, data: it.data);
    case 'wapsi_return':
      return WapsiReturnCard(app: app, data: it.data);
    case 'wapsi_day':
      return WapsiDayCard(app: app, data: it.data);
    case 'samudaay_alert':
      return SamudaayAlertCard(key: ValueKey('sa${it.data['id']}'), app: app, data: it.data);
    case 'samudaay_action':
      return SamudaayActionCard(key: ValueKey('sq${it.data['id']}'), app: app, data: it.data);
    case 'samudaay_question':
      return SamudaayQuestionCard(key: ValueKey('sn${it.data['id']}'), app: app, data: it.data);
    case 'samudaay_join':
      return SamudaayJoinCard(key: ValueKey('sj${it.data['id']}'), app: app, data: it.data);
    case 'samudaay_template':
      return SamudaayTemplateCard(app: app, data: it.data);
    case 'samudaay_week':
      return SamudaayInfoCard(app: app, data: it.data);
    case 'samudaay_info':
      return SamudaayInfoCard(app: app, data: it.data);
    case 'callcentre_script':
      return CallCentreScriptCard(key: ValueKey('cs${it.data['script_id']}'), app: app, data: it.data);
    case 'callcentre_call':
      return CallCentreCallCard(app: app, data: it.data);
    case 'callcentre_message':
      return CallCentreMessageCard(key: ValueKey('cm${it.data['id']}'), app: app, data: it.data);
    // v0.137 Tech suite
    case 'devsahayak_task':
      return DevTaskCard(key: ValueKey('dt${(it.data['task'] as Map?)?['id']}'), app: app, data: it.data);
    case 'devsahayak_push':
      return DevTaskCard(key: ValueKey('dt${(it.data['task'] as Map?)?['id']}'), app: app, data: it.data);
    case 'devsahayak_review':
      return DevReviewCard(key: ValueKey('dr${(it.data['review'] as Map?)?['id']}'), app: app, data: it.data);
    case 'devsahayak_merge':
      return DevActionCard(key: ValueKey('da${(it.data['action'] as Map?)?['id']}'), app: app, data: it.data);
    case 'devsahayak_deploy':
      return DevActionCard(key: ValueKey('da${(it.data['action'] as Map?)?['id']}'), app: app, data: it.data);
    case 'qa_run':
      return QaRunCard(key: ValueKey('qr${(it.data['run'] as Map?)?['id']}'), app: app, data: it.data);
    case 'qa_bug':
      return QaBugCard(key: ValueKey('qb${(it.data['bug'] as Map?)?['id']}'), app: app, data: it.data);
    case 'qa_export':
      return QaExportCard(key: ValueKey('qe${(it.data['export'] as Map?)?['id']}'), app: app, data: it.data);
    case 'qa_ready':
      return QaReadyCard(app: app, data: it.data);
    case 'qa_cases':
      return QaCasesCard(app: app, data: it.data);
    case 'itadmin_change':
      return ItadminChangeCard(key: ValueKey('ic${(it.data['change'] as Map?)?['id']}'), app: app, data: it.data);
    case 'itadmin_checklist':
      return ItadminChecklistCard(key: ValueKey('il${(it.data['checklist'] as Map?)?['id']}'), app: app, data: it.data);
    case 'itadmin_renewal':
      return ItadminRenewalCard(app: app, data: it.data);
    case 'itadmin_review':
      return ItadminReviewCard(app: app, data: it.data);
    case 'itadmin_guide':
      return ItadminGuideCard(key: ValueKey('ig${(it.data['guide'] as Map?)?['id']}'), app: app, data: it.data);
    case 'itadmin_day':
      return ItadminDayCard(app: app, data: it.data);
    case 'ispnoc_fault':
      return IspnocFaultCard(key: ValueKey('nf${(it.data['fault'] as Map?)?['id']}'), app: app, data: it.data);
    case 'ispnoc_ticket':
      return IspnocTicketCard(key: ValueKey('nt${(it.data['ticket'] as Map?)?['id']}'), app: app, data: it.data);
    case 'ispnoc_change':
      return IspnocChangeCard(key: ValueKey('nc${(it.data['change'] as Map?)?['id']}'), app: app, data: it.data);
    case 'ispnoc_alert':
      return IspnocAlertCard(app: app, data: it.data);
    case 'ispnoc_day':
      return IspnocDayCard(app: app, data: it.data);
    case 'cyber_action':
      return CyberActionCard(key: ValueKey('ca${(it.data['action'] as Map?)?['id']}'), app: app, data: it.data);
    case 'cyber_alerts':
      return CyberAlertsCard(app: app, data: it.data);
    case 'cyber_check':
      return CyberCheckCard(app: app, data: it.data);
    case 'cyber_incident':
      return CyberIncidentCard(app: app, data: it.data);
    case 'cyber_advisory':
      return CyberAdvisoryCard(app: app, data: it.data);
    case 'cyber_posture':
      return CyberPostureCard(app: app, data: it.data);
    case 'cyber_day':
      return CyberDayCard(app: app, data: it.data);
    case 'devops_build':
      return DevopsBuildCard(app: app, data: it.data);
    case 'devops_deploy':
      return DevopsDeployCard(key: ValueKey('od${(it.data['deploy'] as Map?)?['id']}'), app: app, data: it.data);
    case 'devops_alert':
      return DevopsAlertCard(app: app, data: it.data);
    case 'devops_script':
      return DevopsScriptCard(app: app, data: it.data);
    case 'devops_day':
      return DevopsDayCard(app: app, data: it.data);
    case 'docwriter_doc':
      return DocwriterDocCard(key: ValueKey('wd${(it.data['doc'] as Map?)?['id']}'), app: app, data: it.data);
    case 'docwriter_publish':
      return DocwriterPublishCard(key: ValueKey('wp${(it.data['doc'] as Map?)?['id']}${it.data['hash']}'), app: app, data: it.data);
    case 'docwriter_sync':
      return DocwriterSyncCard(app: app, data: it.data);
    case 'docwriter_shots':
      return DocwriterShotsCard(app: app, data: it.data);
    case 'appreview_report':
      return AppReviewReportCard(key: ValueKey('ar${it.data['id']}'), app: app, data: it.data);
    case 'appreview_handoff':
      return AppReviewHandoffCard(key: ValueKey('ah${it.data['id']}'), app: app, data: it.data);
    case 'appreview_alert':
      return AppReviewAlertCard(app: app, data: it.data);
    case 'product_publish':
      return ProductPublishCard(key: ValueKey('pp${it.data['id']}'), app: app, data: it.data);
    case 'product_backlog':
      return ProductNoteCard(app: app, data: it.data);
    case 'product_spec':
      return ProductNoteCard(key: ValueKey('ps${(it.data['spec'] as Map?)?['id']}'), app: app, data: it.data);
    case 'product_release':
      return ProductNoteCard(key: ValueKey('pr${(it.data['release'] as Map?)?['id']}'), app: app, data: it.data);
    case 'product_day':
      return ProductNoteCard(app: app, data: it.data);
    // v0.139 Safar suite
    case 'customs_filing':
      return CustomsFilingCard(key: ValueKey('cf${(it.data['filing'] as Map?)?['id']}'), app: app, data: it.data);
    case 'customs_shipment':
      return CustomsShipmentCard(key: ValueKey('cs${(it.data['shipment'] as Map?)?['id']}'), app: app, data: it.data);
    case 'customs_alert':
      return CustomsAlertCard(app: app, data: it.data);
    case 'customs_day':
      return CustomsDayCard(app: app, data: it.data);
    case 'travel_booking':
      return TravelBookingCard(key: ValueKey('tb${it.data['id']}'), app: app, data: it.data);
    case 'travel_quote':
      return TravelQuoteCard(key: ValueKey('tq${it.data['id']}'), app: app, data: it.data);
    case 'travel_trip':
      return TravelNoteCard(key: ValueKey('tt${(it.data['trip'] as Map?)?['id']}'), app: app, data: it.data);
    case 'travel_reminder':
      return TravelNoteCard(app: app, data: it.data);
    case 'travel_day':
      return TravelNoteCard(app: app, data: it.data);
    case 'warehouse_adjust':
      return WarehouseAdjustCard(key: ValueKey('wa${(it.data['adjust'] as Map?)?['id']}'), app: app, data: it.data);
    case 'warehouse_grn':
      return WarehouseGrnCard(key: ValueKey('wg${(it.data['grn'] as Map?)?['id']}'), app: app, data: it.data);
    case 'warehouse_pick':
      return WarehousePickCard(key: ValueKey('wk${(it.data['pick'] as Map?)?['id']}'), app: app, data: it.data);
    case 'warehouse_count':
      return WarehouseCountCard(key: ValueKey('wc${(it.data['count'] as Map?)?['id']}'), app: app, data: it.data);
    case 'warehouse_day':
      return WarehouseDayCard(app: app, data: it.data);
    case 'fleet_spend':
      return FleetSpendCard(key: ValueKey('fs${(it.data['spend'] as Map?)?['id']}'), app: app, data: it.data);
    case 'fleet_trip':
      return FleetTripCard(key: ValueKey('ft${(it.data['trip'] as Map?)?['id']}'), app: app, data: it.data);
    case 'fleet_alert':
      return FleetAlertCard(app: app, data: it.data);
    case 'fleet_day':
      return FleetDayCard(app: app, data: it.data);
    case 'courier_card':
      return CourierActionCard(key: ValueKey('cc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'courier_parcel':
      return CourierParcelCard(key: ValueKey('cp${(it.data['parcel'] as Map?)?['id']}'), app: app, data: it.data);
    case 'courier_day':
      return CourierDayCard(app: app, data: it.data);
    case 'drivers_plan':
      return DriversPlanCard(key: ValueKey('dp${it.data['day']}${it.data['title']}'), app: app, data: it.data);
    case 'drivers_message':
      return DriversMessageCard(key: ValueKey('dm${it.data['id']}'), app: app, data: it.data);
    case 'drivers_alert':
      return DriversAlertCard(app: app, data: it.data);
    case 'drivers_day':
      return DriversDayCard(app: app, data: it.data);
    case 'logistics_ewb':
      return LogisticsEwbCard(key: ValueKey('le${(it.data['ask'] as Map?)?['id']}'), app: app, data: it.data);
    case 'logistics_update':
      return LogisticsUpdateCard(key: ValueKey('lu${(it.data['message'] as Map?)?['id']}'), app: app, data: it.data);
    case 'logistics_shipment':
      return LogisticsShipmentCard(key: ValueKey('ls${(it.data['shipment'] as Map?)?['id']}'), app: app, data: it.data);
    case 'logistics_alert':
      return LogisticsAlertCard(app: app, data: it.data);
    case 'logistics_day':
      return LogisticsDayCard(app: app, data: it.data);
    // v0.144 Makaan suite
    case 'propagent_card':
      return PropagentCardCard(key: ValueKey('gpc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'propagent_visit':
      return PropagentVisitCard(key: ValueKey('gpv${(it.data['visit'] as Map?)?['id']}'), app: app, data: it.data);
    case 'propagent_alert':
      return PropagentAlertCard(app: app, data: it.data);
    case 'propagent_day':
      return PropagentDayCard(app: app, data: it.data);
    case 'rentdesk_approval':
      return RentdeskApprovalCard(key: ValueKey('gra${(it.data['approval'] as Map?)?['id']}'), app: app, data: it.data);
    case 'rentdesk_message':
      return RentdeskMessageCard(key: ValueKey('grm${(it.data['message'] as Map?)?['id']}'), app: app, data: it.data);
    case 'rentdesk_receipt':
      return RentdeskReceiptCard(key: ValueKey('grr${(it.data['payment'] as Map?)?['id']}'), app: app, data: it.data);
    case 'rentdesk_alert':
      return RentdeskAlertCard(app: app, data: it.data);
    case 'rentdesk_day':
      return RentdeskDayCard(app: app, data: it.data);
    case 'sitesup_indent':
      return SitesupIndentCard(key: ValueKey('gsi${(it.data['indent'] as Map?)?['id']}'), app: app, data: it.data);
    case 'sitesup_stop':
      return SitesupStopCard(key: ValueKey('gss${(it.data['stop'] as Map?)?['id']}'), app: app, data: it.data);
    case 'sitesup_report':
      return SitesupReportCard(key: ValueKey('gsr${(it.data['report'] as Map?)?['id']}'), app: app, data: it.data);
    case 'sitesup_alert':
      return SitesupAlertCard(app: app, data: it.data);
    case 'sitesup_day':
      return SitesupDayCard(app: app, data: it.data);
    case 'interior_quote':
      return InteriorQuoteCard(key: ValueKey('giq${(it.data['quote'] as Map?)?['id']}'), app: app, data: it.data);
    case 'interior_order':
      return InteriorOrderCard(key: ValueKey('gio${(it.data['order'] as Map?)?['id']}'), app: app, data: it.data);
    case 'interior_change':
      return InteriorChangeCard(key: ValueKey('gic${(it.data['change'] as Map?)?['id']}'), app: app, data: it.data);
    case 'interior_payment':
      return InteriorPaymentCard(key: ValueKey('gip${(it.data['stage'] as Map?)?['id']}'), app: app, data: it.data);
    case 'interior_concept':
      return InteriorConceptCard(app: app, data: it.data);
    case 'interior_alert':
      return InteriorNoteCard(app: app, data: it.data);
    case 'interior_day':
      return InteriorNoteCard(app: app, data: it.data);
    case 'archassist_transmittal':
      return ArchTransmittalCard(key: ValueKey('gat${(it.data['transmittal'] as Map?)?['id']}'), app: app, data: it.data);
    case 'archassist_submission':
      return ArchSubmissionCard(key: ValueKey('gas${(it.data['submission'] as Map?)?['id']}'), app: app, data: it.data);
    case 'archassist_invoice':
      return ArchInvoiceCard(key: ValueKey('gai${(it.data['invoice'] as Map?)?['id']}'), app: app, data: it.data);
    case 'archassist_area':
      return ArchAreaCard(app: app, data: it.data);
    case 'archassist_alert':
      return ArchNoteCard(app: app, data: it.data);
    case 'archassist_day':
      return ArchNoteCard(app: app, data: it.data);
    case 'society_card':
      return SocietyApprovalCard(key: ValueKey('gyc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'society_complaint':
      return SocietyComplaintCard(key: ValueKey('gyx${(it.data['complaint'] as Map?)?['id']}'), app: app, data: it.data);
    case 'society_alert':
      return SocietyAlertCard(app: app, data: it.data);
    case 'society_day':
      return SocietyDayCard(app: app, data: it.data);
    // v0.150 Kanoon suite
    case 'vakil_card':
      return VakilCardCard(key: ValueKey('kvc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'vakil_draft':
      return VakilDraftCard(key: ValueKey('kvd${(it.data['draft'] as Map?)?['id']}'), app: app, data: it.data);
    case 'vakil_alert':
      return VakilNoteCard(app: app, data: it.data);
    case 'vakil_day':
      return VakilNoteCard(app: app, data: it.data);
    case 'legalres_memo':
      return LegalresMemoCard(key: ValueKey('klm${(it.data['matter'] as Map?)?['id']}:${(it.data['memo'] as Map?)?['v']}'), app: app, data: it.data);
    case 'legalres_share':
      return LegalresShareCard(key: ValueKey('kls${(it.data['share'] as Map?)?['id']}'), app: app, data: it.data);
    case 'compliance_filing':
      return ComplianceFilingCard(key: ValueKey('kcf${(it.data['filing'] as Map?)?['id']}'), app: app, data: it.data);
    case 'compliance_cert':
      return ComplianceCertCard(key: ValueKey('kcc${(it.data['cert'] as Map?)?['id']}'), app: app, data: it.data);
    case 'compliance_alert':
      return ComplianceNoteCard(app: app, data: it.data);
    case 'compliance_day':
      return ComplianceNoteCard(app: app, data: it.data);
    case 'contracts_card':
      return ContractsCardCard(key: ValueKey('ktc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'contracts_review':
      return ContractsReviewCard(key: ValueKey('ktr${(it.data['contract'] as Map?)?['id']}'), app: app, data: it.data);
    case 'contracts_alert':
      return ContractsNoteCard(app: app, data: it.data);
    case 'contracts_day':
      return ContractsNoteCard(app: app, data: it.data);
    case 'cosec_filing':
      return CosecFilingCard(key: ValueKey('ksf${(it.data['filing'] as Map?)?['id']}'), app: app, data: it.data);
    case 'cosec_notice':
    case 'cosec_minutes':
      return CosecMeetingCard(key: ValueKey('ksm${(it.data['meeting'] as Map?)?['id']}:${it.kind}'), app: app, data: it.data);
    case 'cosec_alert':
      return CosecNoteCard(app: app, data: it.data);
    case 'cosec_day':
    case 'cosec_event':
      return CosecNoteCard(app: app, data: it.data);
    case 'notary_print':
      return NotaryPrintCard(key: ValueKey('knp${(it.data['doc'] as Map?)?['id']}'), app: app, data: it.data);
    case 'notary_doc':
      return NotaryDocCard(key: ValueKey('knd${(it.data['doc'] as Map?)?['id']}'), app: app, data: it.data);
    case 'notary_entry':
      return NotaryEntryCard(app: app, data: it.data);
    case 'notary_alert':
      return NotaryNoteCard(app: app, data: it.data);
    case 'notary_day':
      return NotaryNoteCard(app: app, data: it.data);
    case 'pidesk_share':
      return PideskShareCard(key: ValueKey('kps${(it.data['share'] as Map?)?['id']}'), app: app, data: it.data);
    case 'pidesk_report':
      return PideskReportCard(app: app, data: it.data);
    case 'pidesk_doc':
      return PideskDocCard(app: app, data: it.data);
    case 'pidesk_case':
      return PideskNoteCard(key: ValueKey('kpc${(it.data['case'] as Map?)?['id']}'), app: app, data: it.data);
    case 'pidesk_alert':
      return PideskNoteCard(app: app, data: it.data);
    case 'dpo_card':
      return DpoCardCard(key: ValueKey('kdc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'dpo_request':
      return DpoRequestCard(key: ValueKey('kdr${(it.data['request'] as Map?)?['id']}'), app: app, data: it.data);
    case 'dpo_breach':
      return DpoBreachCard(key: ValueKey('kdb${(it.data['breach'] as Map?)?['id']}'), app: app, data: it.data);
    case 'dpo_alert':
      return DpoAlertCard(app: app, data: it.data);
    case 'dpo_day':
      return DpoDayCard(app: app, data: it.data);
    // v0.152 Mehmaan suite
    case 'frontoffice_card':
      return FrontofficeCardCard(key: ValueKey('mfc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'frontoffice_message':
      return FrontofficeMessageCard(key: ValueKey('mfm${(it.data['message'] as Map?)?['id']}'), app: app, data: it.data);
    case 'frontoffice_booking':
      return FrontofficeBookingCard(key: ValueKey('mfb${(it.data['booking'] as Map?)?['id']}'), app: app, data: it.data);
    case 'frontoffice_alert':
      return FrontofficeAlertCard(app: app, data: it.data);
    case 'frontoffice_day':
      return FrontofficeDayCard(app: app, data: it.data);
    case 'eventplan_booking':
      return EventplanBookingCard(key: ValueKey('meb${(it.data['booking'] as Map?)?['id']}'), app: app, data: it.data);
    case 'eventplan_doc':
      return EventplanDocCard(key: ValueKey('med${(it.data['doc'] as Map?)?['id']}'), app: app, data: it.data);
    case 'eventplan_message':
      return EventplanMessageCard(key: ValueKey('mem${(it.data['message'] as Map?)?['id']}'), app: app, data: it.data);
    case 'eventplan_spend':
      return EventplanSpendCard(key: ValueKey('mes${(it.data['spend'] as Map?)?['id']}'), app: app, data: it.data);
    case 'eventplan_alert':
    case 'eventplan_day':
      return EventplanNoteCard(app: app, data: it.data);
    case 'shaadi_card':
      return ShaadiCardCard(key: ValueKey('msc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'shaadi_alert':
    case 'shaadi_day':
      return ShaadiNoteCard(app: app, data: it.data);
    case 'tourguide_card':
      return TourguideCardCard(key: ValueKey('mtc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'tourguide_booking':
      return TourguideBookingCard(key: ValueKey('mtb${(it.data['booking'] as Map?)?['id']}'), app: app, data: it.data);
    case 'tourguide_plan':
      return TourguidePlanCard(app: app, data: it.data);
    case 'tourguide_script':
      return TourguideScriptCard(app: app, data: it.data);
    case 'tourguide_alert':
      return TourguideAlertCard(app: app, data: it.data);
    case 'tourguide_day':
      return TourguideDayCard(app: app, data: it.data);
    case 'homestay_card':
      return HomestayCardCard(key: ValueKey('mhc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'homestay_booking':
      return HomestayBookingCard(key: ValueKey('mhb${(it.data['booking'] as Map?)?['id']}'), app: app, data: it.data);
    case 'homestay_alert':
      return HomestayAlertCard(app: app, data: it.data);
    case 'homestay_day':
      return HomestayDayCard(app: app, data: it.data);
    case 'banquet_card':
      return BanquetCardCard(key: ValueKey('mbc${(it.data['card'] as Map?)?['id']}'), app: app, data: it.data);
    case 'banquet_alert':
    case 'banquet_day':
      return BanquetNoteCard(app: app, data: it.data);
    case 'brand_design':
      return BrandDesignCard(v: it.data, app: app);
    case 'site_board':
      return SiteBoardCard(v: it.data, app: app);
    case 'app_board':
      return AppBoardCard(v: it.data, app: app);
    case 'app_android':
      return AndroidBuildCard(v: it.data, app: app);
    case 'site_lead':
      return SiteLeadCard(v: it.data, app: app);
    case 'site_launch':
      return SiteLaunchCard(v: it.data, app: app);
    case 'site_dns':
      return SiteDnsCard(v: it.data, app: app);
    case 'site_live':
      return SiteLiveCard(v: it.data, app: app);
    case 'site_down':
      return SiteLiveCard(v: it.data, app: app, down: true);
    case 'site_domain':
      return SiteDomainCard(v: it.data, app: app);
    case 'site_care':
      return SiteCareCard(v: it.data, app: app);
    case 'site_github':
      return SiteGithubCard(v: it.data, app: app);
    case 'brand_idea':
      return BrandIdeaCard(v: it.data, app: app);
    case 'ads_change':
      return AdsPlanCard(v: it.data, app: app);
    case 'ads_report':
      return AdsReportCard(v: it.data, app: app);
    case 'ads_copy':
      return AdsCopyCard(v: it.data, app: app);
    case 'kalam_piece':
      return KalamPieceCard(v: it.data, app: app);
    case 'kalam_publish':
      return KalamPublishCard(v: it.data, app: app);
    case 'tele_logged':
      return TeleLoggedCard(v: it.data, app: app);
    case 'fin_report':
    case 'fin_alert':
      return FinCard(v: it.data, app: app);
    case 'payroll_run':
      return PayRunCard(key: ValueKey('pr${it.data['run_id']}'), v: it.data, app: app);
    case 'payroll_day':
      return PayDayCard(v: it.data, app: app);
    case 'gst_return':
      return GstReturnCard(key: ValueKey('gr${it.data['return_id']}'), v: it.data, app: app);
    case 'gst_day':
      return GstDayCard(v: it.data, app: app);
    case 'phonedoc_case':
      return PhoneDocCard(key: ValueKey('pd${it.data['case']}'), v: it.data, app: app);
    case 'chai_plan':
      return ChaiPlanCard(key: ValueKey('cp${it.data['for_date']}'), v: it.data, app: app);
    case 'darzi_quote':
      return DarziQuoteCard(key: ValueKey('dq${it.data['id']}'), v: it.data, app: app);
    case 'darzi_ready':
      return DarziReadyCard(key: ValueKey('dr${it.data['order_id']}'), v: it.data, app: app);
    case 'darzi_day':
      return DarziDayCard(v: it.data, app: app);
    case 'office_spend':
      return OfficeSpendCard(key: ValueKey('os${it.data['id']}'), v: it.data, app: app);
    case 'office_nudge':
      return OfficeNudgeCard(key: ValueKey('on${it.data['id']}'), v: it.data);
    case 'office_day':
      return OfficeDayCard(v: it.data, app: app);
    case 'office_note':
      return OfficeNoteCard(v: it.data, app: app);
    case 'lekhak_doc':
      return LekhakDocCard(key: ValueKey('ld${it.data['id']}'), v: it.data, app: app);
    case 'lekhak_sign':
      return LekhakSignCard(key: ValueKey('ls${it.data['id']}'), v: it.data, app: app);
    case 'employee_report':
      return EmployeeReportCard(v: it.data, app: app);
    case 'biz_handover':
      return BizHandoverCard(v: it.data, app: app);
    case 'procedure':
      return ProcedureLearnedCard(v: it.data, app: app);
    case 'call_rate':
      return CallRateCard(key: ValueKey('rate${it.data['call_id']}'), v: it.data, app: app);
    case 'ask_form':
      return AskFormCard(key: ValueKey('af${it.data['id']}'), v: it.data, app: app);
    case 'upi_result':
      return UpiResultCard(key: ValueKey('upi${it.data['txn_ref']}${it.data['status']}'), v: it.data, app: app);
    case 'call_receipt':
      return CallReceiptCard(key: ValueKey('cr${it.data['call_id']}'), v: it.data, app: app);
    case 'sheet_milaan':
      return SheetMilaanCard(key: ValueKey('sm${it.data['id']}'), v: it.data, app: app);
    case 'doc_edit':
      return DocEditCard(key: ValueKey('de${it.data['id']}'), v: it.data, app: app);
    case 'memory_saved':
      return MemorySavedChip(v: it.data, app: app);
    case 'pg_write':
      return PgWriteCard(key: ValueKey('pgw${it.data['id']}${it.data['status']}'), v: it.data, app: app);
    case 'blender3d':
      return Blender3dCard(key: ValueKey('b3${it.data['id']}${it.data['version']}${it.data['status']}'), v: it.data, app: app);
    case 'photo_made':
      return PhotoMadeCard(key: ValueKey('ph${it.data['file_id']}'), v: it.data, app: app);
    case 'pc_file':
      return PcFileCard(v: it.data, app: app);
    case 'artifact':
      return ArtifactCard(v: it.data, app: app);
    case 'browser':
      return BrowserLiveCard(v: it.data, app: app);
    case 'campaign':
      return _CampaignCard(v: it.data, app: app);
    default:
      return null;
  }
}

/// A new message or card arriving: fades in, slides up a little and settles (cards also grow in), like Claude's chat.
class _Arrive extends StatelessWidget {
  const _Arrive({super.key, required this.child, this.card = false});
  final Widget child;
  final bool card;
  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: Duration(milliseconds: card ? 460 : 340),
        curve: Curves.easeOutCubic,
        builder: (context, v, c) => Opacity(
          opacity: v.clamp(0, 1),
          child: Transform.translate(
            offset: Offset(0, (1 - v) * 14),
            child: card ? Transform.scale(scale: .965 + .035 * v, alignment: Alignment.bottomCenter, child: c) : c,
          ),
        ),
        child: child,
      );
}

/// Hoola's new reply appears word by word (fast, like streaming), then stays as normal text.
class _Reveal extends StatefulWidget {
  const _Reveal({required this.text, required this.builder});
  final String text;
  final Widget Function(String) builder;
  @override
  State<_Reveal> createState() => _RevealState();
}

class _RevealState extends State<_Reveal> with SingleTickerProviderStateMixin {
  late final List<String> _words = widget.text.split(RegExp(r'(?<=\s)'));
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: (_words.length * 28).clamp(250, 1600)),
  )..forward();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          if (_c.isCompleted) return widget.builder(widget.text);
          final n = (_words.length * Curves.easeOut.transform(_c.value)).ceil().clamp(1, _words.length);
          // the full text is laid out invisibly underneath, so the bubble does not jump in size while revealing
          return Stack(children: [
            Opacity(opacity: 0, child: widget.builder(widget.text)),
            widget.builder(_words.take(n).join()),
          ]);
        },
      );
}

/// Back to the newest message; shows how many arrived while you were reading above.
class _DownButton extends StatelessWidget {
  const _DownButton({required this.count, required this.onTap});
  final int count;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: count > 0 ? '$count naye message, neeche jaiye' : 'Sabse neeche jaiye',
        child: GestureDetector(
          onTap: onTap,
          child: Stack(clipBehavior: Clip.none, children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xEE231B45),
                border: Border.all(color: const Color(0x33FFFFFF)),
                boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 14, offset: Offset(0, 6))],
              ),
              child: const Icon(Icons.keyboard_arrow_down_rounded, color: C.ink, size: 28),
            ),
            if (count > 0)
              Positioned(
                right: -4,
                top: -6,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: C.accent, borderRadius: BorderRadius.circular(10)),
                  child: Text(count > 99 ? '99+' : '$count', style: const TextStyle(color: C.onAccent, fontSize: 11, fontWeight: FontWeight.w800)),
                ),
              ),
          ]),
        ),
      );
}

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
    final money = (v['money'] as bool?) ?? (v['amount'] as String? ?? '').isNotEmpty;
    String chip = money ? 'APPROVE KAREIN' : 'HAAN CHAHIYE';
    Color chipFg = C.warn;
    if (status == 'approved' || status == 'auto') { chip = 'APPROVED'; chipFg = C.ok; }
    if (status == 'rejected') { chip = 'CANCEL'; chipFg = C.muted; }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(v['tier'] == 3 ? Icons.currency_rupee_rounded : (money ? Icons.shopping_bag_outlined : Icons.touch_app_rounded),
                color: C.accent, size: 20),
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
            Text('${money ? 'Kisko' : 'Kahan'}: ${v['payee']}', style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
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
          if ((v['pay_method'] as String? ?? '').isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(v['pay_method'] as String, style: const TextStyle(color: C.muted, fontSize: 12.5)),
          ],
          if (v['needs_pin'] == true && status == 'pending')
            const Text('UPI PIN sirf aapke UPI app mein daaliye. Hoola kabhi PIN nahi maangega.', style: TextStyle(color: C.muted, fontSize: 12)),
          if (status == 'pending') ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: GradientButton(label: busy ? 'Ho raha hai…' : (money ? 'Approve karein' : 'Haan, karo'), height: 46, icon: Icons.check_rounded,
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
