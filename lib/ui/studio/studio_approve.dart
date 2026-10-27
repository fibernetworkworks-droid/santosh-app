import 'package:flutter/material.dart';

import '../../state.dart';
import '../glass.dart';
import 'studio_kit.dart';

/// v0.159 Money = her tap. The price sheet (screen 8): quality, every cost on its own line, what stays of the month,
/// "Haan, ₹X mein banao". Her tap here IS the approval of the card the server makes (the same numbers).

class PriceRow {
  const PriceRow(this.icon, this.color, this.title, this.sub, this.inr, {this.free = false});
  final IconData icon;
  final Color color;
  final String title;
  final String sub;
  final int inr;
  final bool free;
}

/// The rows of one generate quote (from the project's `estimates[q]` or a card).
List<PriceRow> quoteRows(Map<String, dynamic> e, {String language = ''}) {
  final rows = <PriceRow>[];
  final models = List<String>.from(((e['models'] as List?) ?? const []).map((x) => '$x'));
  final names = models.map(modelName).where((x) => x.isNotEmpty && !x.contains('lip sync')).toSet().join(' · ');
  rows.add(PriceRow(Icons.videocam_rounded, SC.teal, 'Video · ${e['shots'] ?? 0} shots',
      '${names.isEmpty ? 'AI video' : names} · ${e['seconds'] ?? 0} sec', sInt(e['video_inr'] ?? e['inr'])));
  if (sInt(e['keyframes']) > 0) {
    rows.add(PriceRow(Icons.image_rounded, SC.violet, 'Pehli tasveerein · ${e['keyframes']}', 'Nano Banana Pro · same chehra har shot mein',
        sInt(e['keyframes_inr'])));
  }
  if (sInt(e['lipsync_shots']) > 0) {
    rows.add(PriceRow(Icons.graphic_eq_rounded, C.accentSoft, 'Lip sync · ${e['lipsync_shots']} shot',
        'Sync 3${language.isEmpty ? '' : ' · ${langShown(language)}'} · ${e['lipsync_seconds'] ?? 0} sec', sInt(e['lipsync_inr'])));
  }
  if ('${e['music'] ?? ''}'.isNotEmpty) {
    rows.add(PriceRow(Icons.music_note_rounded, SC.violet, 'Music', 'Google Lyria · ${moodLabel['${e['music']}'] ?? e['music']}',
        sInt(e['music_inr'])));
  }
  rows.add(const PriceRow(Icons.mic_rounded, C.ok, 'Awaaz, captions, AI jaanch', 'Hoola ki awaaz · jodna', 0, free: true));
  return rows;
}

String modelName(String m) => const {
      'or-wan-3': 'Wan 3.0', 'or-seedance-2.5': 'Seedance 2.5', 'or-minimax-h3': 'MiniMax H3', 'or-minimax-h3-max': 'MiniMax H3 Max',
      'gemini-omni-flash': 'Gemini Omni Flash', 'sync-3': 'Sync 3 lip sync', 'or-seedance-2-fast': 'Seedance 2 Fast',
      'or-seedance-2': 'Seedance 2.0', 'or-flux-3-video': 'FLUX 3 Video', 'nano-banana-pro': 'Nano Banana Pro',
      'offline-preview': 'Free preview', 'lyria-3.5': 'Google Lyria', 'flux-dev': 'FLUX',
    }[m] ??
    m;

class PriceList extends StatelessWidget {
  const PriceList({super.key, required this.rows});
  final List<PriceRow> rows;
  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(color: SC.field, borderRadius: BorderRadius.circular(18)),
        child: Column(children: [
          for (var i = 0; i < rows.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: Color(0x0FFFFFFF)))),
              child: Row(children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(color: rows[i].color.withOpacity(.14), borderRadius: BorderRadius.circular(10)),
                  child: Icon(rows[i].icon, size: 18, color: rows[i].color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(rows[i].title, style: body(13.5, w: FontWeight.w700)),
                    Text(rows[i].sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: body(11.5, color: C.faint)),
                  ]),
                ),
                Text(rows[i].free ? 'Free' : rupees(rows[i].inr), style: body(14, w: FontWeight.w800, color: rows[i].free ? C.ok : C.ink)),
              ]),
            ),
        ]),
      );
}

/// Opens the price sheet for a whole-video (or some shots) run; returns true when she said Haan and it started.
Future<bool> approveGenerate(BuildContext context, Santosh app, Map<String, dynamic> v, {List<String>? shots, String? quality}) async {
  final ok = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _GenerateSheet(app: app, v: v, shots: shots, quality: quality),
  );
  return ok == true;
}

/// A simple price sheet for one paid thing (opening pictures, music, a character photo): ask -> card -> her Haan.
Future<bool> approveSimple(BuildContext context, Santosh app,
    {required String title, required String sub, required List<PriceRow> rows, required int inr, required Map<String, dynamic> month,
    required Future<Map<String, dynamic>> Function() ask}) async {
  final ok = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _SimpleSheet(app: app, title: title, sub: sub, rows: rows, inr: inr, month: month, ask: ask),
  );
  return ok == true;
}

/// Asks the server for the card and approves it (her tap was on our sheet). Free runs start at once.
Future<String?> askAndApprove(Santosh app, Future<Map<String, dynamic>> Function() ask) async {
  final r = await ask();
  final id = '${r['waiting_owner'] ?? ''}';
  if (id.isEmpty) return null;
  final d = await app.api!.studioDecide(id, true);
  if ('${d['status']}' == 'failed') throw '${d['error'] ?? 'Shuru nahi ho paya'}';
  return id;
}

class _SheetFrame extends StatelessWidget {
  const _SheetFrame({required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Container(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * .92),
        decoration: const BoxDecoration(
          color: SC.card,
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          border: Border(top: BorderSide(color: Color(0x1AFFFFFF))),
        ),
        padding: EdgeInsets.fromLTRB(20, 10, 20, 20 + MediaQuery.of(context).padding.bottom),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(2)))),
            const SizedBox(height: 14),
            ...children,
          ]),
        ),
      );
}

Widget monthBar(Map<String, dynamic> month, int price) {
  final limit = sInt(month['limit_inr']);
  final spent = sInt(month['spent_inr']);
  final left = (limit - spent - price);
  final frac = limit <= 0 ? 0.0 : ((spent + price) / limit).clamp(0, 1).toDouble();
  return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Row(children: [
      Expanded(child: Text('Is mahine bachega', style: body(12, color: C.muted))),
      Text('${rupees(left < 0 ? 0 : left)} / ${rupees(limit)}', style: body(12, w: FontWeight.w800, color: left < 0 ? C.bad : C.ink)),
    ]),
    const SizedBox(height: 8),
    ClipRRect(
      borderRadius: BorderRadius.circular(3),
      child: LinearProgressIndicator(value: frac, minHeight: 6, backgroundColor: SC.field, color: left < 0 ? C.bad : C.accent),
    ),
    if (left < 0)
      Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Text('Is mahine ki seema se zyada hai. Kam quality ya kam shots chuniye.', style: body(11.5, color: C.bad)),
      ),
  ]);
}

class _GenerateSheet extends StatefulWidget {
  const _GenerateSheet({required this.app, required this.v, this.shots, this.quality});
  final Santosh app;
  final Map<String, dynamic> v;
  final List<String>? shots;
  final String? quality;
  @override
  State<_GenerateSheet> createState() => _GenerateSheetState();
}

class _GenerateSheetState extends State<_GenerateSheet> {
  late String _q = widget.quality ?? '${widget.v['quality_pref'] ?? 'final'}';
  bool _busy = false;
  String _err = '';

  Map<String, dynamic> get _est => sMap(sMap(widget.v['estimates'])[_q]);

  bool get _partial => widget.shots != null && widget.shots!.isNotEmpty;

  Future<void> _go() async {
    setState(() {
      _busy = true;
      _err = '';
    });
    try {
      await askAndApprove(widget.app, () => widget.app.api!.studioGenerate('${widget.v['project']}', _q, shots: widget.shots));
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => _err = '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final est = sMap(widget.v['estimates']);
    final e = _est;
    final shots = sList(widget.v['shots']);
    final inr = _partial ? null : sInt(e['inr']);
    return _SheetFrame(children: [
      Text('${widget.v['project']} · ${_partial ? '${widget.shots!.length} shot' : '${shots.length} shots'} · '
              '${_partial ? '' : '${widget.v['seconds'] ?? 0} sec'}'
          .toUpperCase(), style: body(11.5, w: FontWeight.w700, color: C.faint)),
      const SizedBox(height: 4),
      Text('Video banane ka kharcha', style: sora(20)),
      const SizedBox(height: 16),
      SSegment<String>(
        height: 54,
        items: {
          for (final q in const ['draft', 'final', 'premium'])
            q: '${qualityShort[q]}${est[q] == null || _partial ? '' : '\n${rupees(sMap(est[q])['inr'])}'}',
        },
        value: _q,
        onChanged: (q) => setState(() => _q = q),
      ),
      const SizedBox(height: 16),
      if (_partial)
        Text('Sirf chune hue shots banenge. Daam card par dikhega, phir yahi haan maani jayegi.', style: body(13, color: C.muted, height: 1.4))
      else ...[
        Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
          Text(rupees(inr), style: sora(40, w: FontWeight.w700)),
          const SizedBox(width: 10),
          Flexible(child: Text('lagbhag · ${qualityWhat[_q] ?? ''}', maxLines: 2, style: body(12.5, color: C.faint))),
        ]),
        const SizedBox(height: 14),
        PriceList(rows: quoteRows(e, language: '${widget.v['language'] ?? ''}')),
        const SizedBox(height: 16),
        monthBar(sMap(widget.v['month']), inr ?? 0),
      ],
      const SizedBox(height: 14),
      Text('Asli kharcha jitna laga utna hi katega, isse zyada kabhi nahi. Koi shot fail hua to uska paisa nahi.',
          style: body(12, color: C.faint, height: 1.45)),
      if (_err.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_err, style: body(12.5, color: C.bad))),
      const SizedBox(height: 16),
      Row(children: [
        Expanded(child: SButton(label: 'Abhi nahi', primary: false, onTap: () => Navigator.pop(context, false))),
        const SizedBox(width: 10),
        Expanded(
          flex: 2,
          child: SButton(
            label: _partial ? 'Haan, banao' : 'Haan, ${rupees(inr)} mein banao',
            icon: Icons.check_rounded,
            busy: _busy,
            onTap: _go,
          ),
        ),
      ]),
    ]);
  }
}

class _SimpleSheet extends StatefulWidget {
  const _SimpleSheet({required this.app, required this.title, required this.sub, required this.rows, required this.inr,
      required this.month, required this.ask});
  final Santosh app;
  final String title;
  final String sub;
  final List<PriceRow> rows;
  final int inr;
  final Map<String, dynamic> month;
  final Future<Map<String, dynamic>> Function() ask;
  @override
  State<_SimpleSheet> createState() => _SimpleSheetState();
}

class _SimpleSheetState extends State<_SimpleSheet> {
  bool _busy = false;
  String _err = '';

  Future<void> _go() async {
    setState(() {
      _busy = true;
      _err = '';
    });
    try {
      await askAndApprove(widget.app, widget.ask);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => _err = '$e'.replaceFirst('Exception: ', ''));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) => _SheetFrame(children: [
        Text(widget.sub.toUpperCase(), style: body(11.5, w: FontWeight.w700, color: C.faint)),
        const SizedBox(height: 4),
        Text(widget.title, style: sora(20)),
        const SizedBox(height: 14),
        Text(rupees(widget.inr), style: sora(38, w: FontWeight.w700)),
        const SizedBox(height: 12),
        PriceList(rows: widget.rows),
        if (widget.month.isNotEmpty) ...[const SizedBox(height: 16), monthBar(widget.month, widget.inr)],
        if (_err.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_err, style: body(12.5, color: C.bad))),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(child: SButton(label: 'Abhi nahi', primary: false, onTap: () => Navigator.pop(context, false))),
          const SizedBox(width: 10),
          Expanded(flex: 2, child: SButton(label: 'Haan, ${rupees(widget.inr)}', icon: Icons.check_rounded, busy: _busy, onTap: _go)),
        ]),
      ]);
}

/// The price card in chat / calls (when Hoola was asked by words): the same lines, Haan / Mana.
class StudioApprovalCard extends StatefulWidget {
  const StudioApprovalCard({super.key, required this.v, required this.app});
  final Map<String, dynamic> v;
  final Santosh app;
  @override
  State<StudioApprovalCard> createState() => _StudioApprovalCardState();
}

class _StudioApprovalCardState extends State<StudioApprovalCard> {
  bool _busy = false;

  Future<void> _decide(bool yes) async {
    setState(() => _busy = true);
    try {
      final r = await widget.app.api!.studioDecide('${widget.v['id']}', yes);
      widget.v.addAll(r);
    } catch (e) {
      if (mounted) studioSnack(context, '$e');
    }
    if (mounted) setState(() => _busy = false);
  }

  List<PriceRow> _rows(Map<String, dynamic> v) {
    switch ('${v['kind']}') {
      case 'keyframes':
        return [PriceRow(Icons.image_rounded, SC.violet, 'Pehli tasveerein · ${v['shots'] ?? 0}', 'Nano Banana Pro', sInt(v['inr']))];
      case 'music':
        return [PriceRow(Icons.music_note_rounded, SC.violet, 'Music', 'Google Lyria · ${moodLabel['${v['mood']}'] ?? v['mood'] ?? ''}', sInt(v['inr']))];
      case 'character':
        return [PriceRow(Icons.person_rounded, SC.violet, 'Character ki photo', '${v['name'] ?? ''}', sInt(v['inr']))];
    }
    if (v['video_inr'] == null) {
      return [PriceRow(Icons.videocam_rounded, SC.teal, '${v['shots'] ?? 0} shot · ${qualityShort['${v['quality']}'] ?? ''}',
          '${v['seconds'] ?? 0} sec', sInt(v['inr']))];
    }
    return quoteRows(v);
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final status = '${v['status'] ?? 'pending'}';
    final pending = status == 'pending';
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: SC.card,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: pending ? C.accent.withOpacity(.6) : SC.line),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Icon(Icons.movie_filter_rounded, color: C.accent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Video Studio · ${v['project'] ?? ''}', style: body(13.5, w: FontWeight.w800))),
          if (!pending)
            Tag(status == 'approved' ? 'Haan kaha' : status == 'rejected' ? 'Mana kiya' : status == 'failed' ? 'Ruk gaya' : status,
                fg: status == 'approved' ? C.ok : status == 'failed' ? C.bad : C.faint),
        ]),
        const SizedBox(height: 10),
        Text(rupees(v['inr']), style: sora(28, w: FontWeight.w700)),
        const SizedBox(height: 10),
        PriceList(rows: _rows(v)),
        if (v['month_left_usd'] != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Is mahine bacha: ~${rupees((v['month_left_usd'] as num) * 85)}', style: body(11.5, color: C.faint)),
          ),
        if ('${v['error'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 8), child: Text('${v['error']}', style: body(12.5, color: C.bad))),
        if (pending) ...[
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: SButton(label: 'Mana', primary: false, height: 48, onTap: _busy ? null : () => _decide(false))),
            const SizedBox(width: 10),
            Expanded(flex: 2, child: SButton(label: 'Haan, banao', height: 48, busy: _busy, onTap: () => _decide(true))),
          ]),
          const SizedBox(height: 8),
          Text('Asli kharcha jitna laga utna hi likha jayega (isse zyada kabhi nahi).', style: body(11.5, color: C.faint)),
        ],
      ]),
    );
  }
}
