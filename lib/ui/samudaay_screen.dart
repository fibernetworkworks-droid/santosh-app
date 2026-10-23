/// Profile > Community Sahayak: Hoola as her community manager (Telegram groups via her own bot, Hoola Mandali).
/// Aaj (alerts, cards waiting for her Haan, questions, join requests) · Groups (connect bot, niyam) · Log (member register)
/// · FAQ (her answers + welcome message) · Report (weekly health). Removing / ban / mute / deleting a post / announcement
/// happen ONLY when she taps Haan here or on a chat card (POST .../decide, .../act).
library;

import 'package:flutter/material.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _list(dynamic l) =>
    List<Map<String, dynamic>>.from(((l as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)));
Map<String, dynamic> _map(dynamic m) => m is Map ? Map<String, dynamic>.from(m) : <String, dynamic>{};
void _snack(BuildContext c, String t) {
  if (t.isEmpty) return;
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));
}

Color _sev(String s) => s == 'high' ? C.bad : (s == 'medium' ? C.warn : C.muted);

const _kindNames = {
  'scam': 'Scam ka shak', 'spam': 'Spam', 'abuse': 'Gaali', 'threat': 'Dhamki', 'hate': 'Nafrat', 'harassment': 'Chhed-chhaad',
  'pii': 'Personal jaankari', 'misinfo': 'Afwah?', 'flood': 'Bahut message', 'raid': 'Copy-paste hamla',
  'negativity': 'Naraazgi badhi', 'leaving': 'Log ja rahe', 'complaints': 'Ek jaisi shikayat', 'rejoin': 'Ban wala wapas',
};

Future<String?> _ask(BuildContext context, String title, String label, {String initial = '', bool obscure = false, int lines = 1}) async {
  final c = TextEditingController(text: initial);
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: c,
        obscureText: obscure,
        autocorrect: !obscure,
        enableSuggestions: !obscure,
        minLines: obscure ? 1 : lines,
        maxLines: obscure ? 1 : (lines < 2 ? 1 : 8),
        decoration: InputDecoration(labelText: label),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Rehne do')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Aage')),
      ],
    ),
  );
  if (ok != true) return null;
  final v = c.text.trim();
  return v.isEmpty ? null : v;
}

Future<Map<String, dynamic>?> _call(BuildContext context, Santosh app, String method, String path, {Object? body}) async {
  try {
    final r = await app.api!.call(method, path, body: body);
    final m = _map(r);
    if (context.mounted) _snack(context, _s(m['say']));
    return m;
  } catch (e) {
    if (context.mounted) _snack(context, '$e');
    return null;
  }
}

class SamudaayScreen extends StatefulWidget {
  const SamudaayScreen({super.key, required this.app});
  final Santosh app;
  @override
  State<SamudaayScreen> createState() => _SamudaayScreenState();
}

class _SamudaayScreenState extends State<SamudaayScreen> {
  Map<String, dynamic>? _d;
  List<Map<String, dynamic>> _members = const [];
  List<Map<String, dynamic>> _faqs = const [];
  List<Map<String, dynamic>> _templates = const [];
  Map<String, dynamic>? _report;
  String _reportFor = '';
  String _q = '';
  int _tab = 0;
  bool _busy = false;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = _map(await app.api!.call('GET', '/api/samudaay'));
      final f = _map(await app.api!.call('GET', '/api/samudaay/faqs'));
      final t = _map(await app.api!.call('GET', '/api/samudaay/templates'));
      if (!mounted) return;
      setState(() {
        _d = d;
        _faqs = _list(f['faqs']);
        _templates = _list(t['templates']);
      });
      await _loadMembers();
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Future<void> _loadMembers() async {
    try {
      final m = _map(await app.api!.call('GET', '/api/samudaay/members', query: {if (_q.isNotEmpty) 'q': _q}));
      if (mounted) setState(() => _members = _list(m['members']));
    } catch (_) {}
  }

  Future<void> _do(String method, String path, {Object? body}) async {
    setState(() => _busy = true);
    await _call(context, app, method, path, body: body);
    await _load();
    if (mounted) setState(() => _busy = false);
  }

  List<Map<String, dynamic>> get _comms => _list(_d?['communities']);

  // ---------------- Aaj
  Widget _today() {
    final d = _d ?? const {};
    final al = _list(d['alerts']);
    final acts = _list(d['actions']);
    final qs = _list(d['questions']);
    final jr = _list(d['join_requests']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(child: Text(_s(d['say']), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, height: 1.35))),
      const SizedBox(height: 10),
      if (acts.isNotEmpty) const _Head('Aapki haan chahiye'),
      for (final a in acts) Padding(padding: const EdgeInsets.only(bottom: 8), child: SamudaayActionCard(app: app, data: a, onDone: _load)),
      if (al.isNotEmpty) const _Head('Alert'),
      for (final a in al) Padding(padding: const EdgeInsets.only(bottom: 8), child: SamudaayAlertCard(app: app, data: a, onDone: _load)),
      if (qs.isNotEmpty) const _Head('Sawal (FAQ mein nahi)'),
      for (final q in qs) Padding(padding: const EdgeInsets.only(bottom: 8), child: SamudaayQuestionCard(app: app, data: q, onDone: _load)),
      if (jr.isNotEmpty) const _Head('Join request'),
      for (final j in jr) Padding(padding: const EdgeInsets.only(bottom: 8), child: SamudaayJoinCard(app: app, data: j, onDone: _load)),
    ]);
  }

  // ---------------- Groups
  Future<void> _connectBot() async {
    final t = await _ask(context, 'Telegram bot jodiye',
        'BotFather wala token (sirf yahan, chat mein kabhi nahi)', obscure: true);
    if (t == null) return;
    await _do('PUT', '/api/samudaay/telegram', body: {'token': t});
  }

  Future<void> _linkMandali() async {
    final g = await _ask(context, 'Hoola Mandali jodiye', 'Mandali ka naam (aap admin hon)');
    if (g == null) return;
    await _do('POST', '/api/samudaay/hoola', body: {'group': g});
  }

  Future<void> _settings(Map<String, dynamic> c) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: C.bgBottom,
      builder: (_) => _CommunitySheet(app: app, c: c),
    );
    await _load();
  }

  Widget _groups() {
    final bot = _map(_d?['bot']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.send_rounded, color: C.teal),
            const SizedBox(width: 8),
            Expanded(
                child: Text(bot.isEmpty ? 'Telegram bot juda nahi' : '@${_s(bot['username'])} juda',
                    style: const TextStyle(fontWeight: FontWeight.w800))),
            if (bot.isNotEmpty) Pill(_s(bot['status'])),
          ]),
          const SizedBox(height: 6),
          Text(
              bot.isEmpty
                  ? 'Telegram mein @BotFather se apna bot banaiye, token yahan daaliye. Token sirf is phone se server tak jaata hai, chat mein kabhi nahi.'
                  : 'Bot ko apne group mein admin banaiye (delete, ban, invite). BotFather > /setprivacy > Disable, taaki woh saare message dekh sake.',
              style: const TextStyle(color: C.muted, fontSize: 12.5)),
          if (_s(bot['last_error']).isNotEmpty) Text(_s(bot['last_error']), style: const TextStyle(color: C.bad, fontSize: 12)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            GlassButton(label: bot.isEmpty ? 'Bot jodiye' : 'Naya token', icon: Icons.key_rounded, onTap: _busy ? null : _connectBot),
            if (bot.isNotEmpty)
              GlassButton(
                  label: 'Bot hatao', icon: Icons.link_off_rounded, color: C.bad, onTap: _busy ? null : () => _do('DELETE', '/api/samudaay/telegram')),
            GlassButton(label: 'Mandali jodiye', icon: Icons.groups_rounded, onTap: _busy ? null : _linkMandali),
          ]),
        ]),
      ),
      const SizedBox(height: 10),
      if (_comms.isEmpty) const Text('Abhi koi group nahi.', style: TextStyle(color: C.muted)),
      for (final c in _comms)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Press(
            onTap: () => _settings(c),
            child: Glass(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Icon(c['platform'] == 'hoola' ? Icons.hub_rounded : Icons.send_rounded, color: C.accent, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_s(c['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                  Pill(_s(c['status'])),
                ]),
                Text(
                    '${c['members'] ?? 0} member · ${c['open_alerts'] ?? 0} alert · ${c['questions'] ?? 0} sawal · ${_s(c['language'])}'
                    '${c['welcome_ready'] == true ? ' · welcome taiyaar' : ' · welcome baaki'}',
                    style: const TextStyle(color: C.muted, fontSize: 12.5)),
              ]),
            ),
          ),
        ),
    ]);
  }

  // ---------------- Log (member register)
  Future<void> _member(Map<String, dynamic> m) async {
    final roles = Set<String>.from(((m['roles'] as List?) ?? const []).map((e) => '$e'));
    final picked = await showDialog<Set<String>>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: Text(_s(m['name'])),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Juda: ${_s(m['joined_at']).split('T').first} · ${_s(m['source'])}\nPost: ${m['posts']} · chetavni: ${m['warnings']} · ${_s(m['status'])}',
                style: const TextStyle(fontSize: 12.5)),
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: [
              for (final r in const ['owner', 'admin', 'moderator', 'vip', 'member'])
                FilterChip(
                    label: Text(r),
                    selected: roles.contains(r),
                    onSelected: (v) => set(() => v ? roles.add(r) : roles.remove(r))),
            ]),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, <String>{'__forget'}), child: const Text('Data mitao', style: TextStyle(color: C.bad))),
            TextButton(onPressed: () => Navigator.pop(d, roles), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (picked == null) return;
    if (picked.contains('__forget')) {
      await _do('DELETE', '/api/samudaay/members/${_s(m['id'])}');
    } else {
      await _do('PATCH', '/api/samudaay/members/${_s(m['id'])}', body: {'roles': picked.toList()});
    }
  }

  Widget _register() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: TextField(
              decoration: const InputDecoration(hintText: 'Naam se dhoondo', prefixIcon: Icon(Icons.search_rounded)),
              onSubmitted: (v) {
                _q = v.trim();
                _loadMembers();
              },
            ),
          ),
          IconButton(
              tooltip: 'Register Excel',
              icon: const Icon(Icons.table_view_rounded),
              onPressed: _busy ? null : () => _do('POST', '/api/samudaay/register', body: const {})),
        ]),
        const SizedBox(height: 8),
        for (final m in _members)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            onTap: () => _member(m),
            leading: CircleAvatar(
                backgroundColor: m['status'] == 'banned' || m['status'] == 'removed' ? C.bad : (m['new'] == true ? C.teal : C.violet),
                child: Text(_s(m['name']).isEmpty ? '?' : _s(m['name']).substring(0, 1).toUpperCase())),
            title: Text(_s(m['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(
                '${_s(m['joined_at']).split('T').first} · ${_s(m['source'])} · ${((m['roles'] as List?) ?? const []).join(', ')} · ${m['posts']} post',
                style: const TextStyle(fontSize: 12, color: C.muted)),
            trailing: Pill(_s(m['status'])),
          ),
      ]);

  // ---------------- FAQ + welcome
  Future<void> _addFaq([Map<String, dynamic>? f]) async {
    final q = await _ask(context, 'Sawal', 'Log kaise poochhte hain', initial: _s(f?['question']));
    if (q == null || !mounted) return;
    final a = await _ask(context, 'Aapka jawab', 'Sirf sahi baat (Hoola yahi bhejega)', initial: _s(f?['answer']), lines: 3);
    if (a == null) return;
    await _do('POST', '/api/samudaay/faqs', body: {'question': q, 'answer': a, if (f != null) 'id': f['id']});
  }

  Future<void> _welcome() async {
    final w = await _ask(context, 'Welcome message', 'Apna message ya bas idea (khaali = Hoola ka standard)', lines: 3);
    final r = await _call(context, app, 'POST', '/api/samudaay/templates', body: {if (w != null) 'from_words': w});
    if (r != null && mounted) {
      await showDialog<void>(context: context, builder: (_) => AlertDialog(content: SamudaayTemplateCard(app: app, data: r, onDone: _load)));
    }
    await _load();
  }

  Widget _faq() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          GlassButton(label: 'Naya FAQ', icon: Icons.add_comment_rounded, onTap: _busy ? null : () => _addFaq()),
          GlassButton(label: 'Welcome message', icon: Icons.waving_hand_rounded, onTap: _busy ? null : _welcome),
        ]),
        const SizedBox(height: 8),
        for (final t in _templates)
          Padding(padding: const EdgeInsets.only(bottom: 8), child: SamudaayTemplateCard(app: app, data: t, onDone: _load)),
        const _Head('Aapke jawab'),
        if (_faqs.isEmpty)
          const Text('Abhi koi FAQ nahi. Jo sawal aapse poochhe jayenge, aapka jawab yahan jud jayega.', style: TextStyle(color: C.muted, fontSize: 12.5)),
        for (final f in _faqs)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Press(
              onTap: () => _addFaq(f),
              child: Glass(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(_s(f['question']), style: const TextStyle(fontWeight: FontWeight.w800))),
                    Text('${f['uses'] ?? 0}x', style: const TextStyle(color: C.faint, fontSize: 12)),
                    IconButton(
                        icon: const Icon(Icons.delete_outline_rounded, size: 18),
                        onPressed: _busy ? null : () => _do('DELETE', '/api/samudaay/faqs/${_s(f['id'])}')),
                  ]),
                  Text(_s(f['answer']), style: const TextStyle(fontSize: 13, color: C.muted)),
                ]),
              ),
            ),
          ),
      ]);

  // ---------------- Report
  Future<void> _loadReport(String cid) async {
    try {
      final r = _map(await app.api!.call('GET', '/api/samudaay/communities/$cid/report', query: {'days': '7'}));
      if (mounted) setState(() {
        _report = r;
        _reportFor = cid;
      });
    } catch (e) {
      if (mounted) _snack(context, '$e');
    }
  }

  Widget _reportTab() {
    final r = _report;
    final h = _map(r?['health']);
    final now = _map(r?['now']);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 6, runSpacing: 6, children: [
        for (final c in _comms)
          ChoiceChip(label: Text(_s(c['name'])), selected: _reportFor == c['id'], onSelected: (_) => _loadReport(_s(c['id']))),
      ]),
      const SizedBox(height: 10),
      if (r != null) ...[
        Glass(
          child: Row(children: [
            Text('${h['score'] ?? '-'}', style: display(36, color: (h['score'] ?? 0) >= 75 ? C.ok : ((h['score'] ?? 0) >= 55 ? C.warn : C.bad))),
            const SizedBox(width: 12),
            Expanded(
                child: Text('Sehat: ${_s(h['label'])}\n${((h['why'] as List?) ?? const []).join('; ')}',
                    style: const TextStyle(fontSize: 13, height: 1.3))),
          ]),
        ),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final (k, label) in const [
            ('members', 'Member'), ('joins', 'Aaye'), ('leaves', 'Gaye'), ('active', 'Baat ki'), ('posts', 'Message'),
            ('faq_answers', 'FAQ jawab'), ('unanswered', 'Baaki sawal'), ('actions', 'Kaarwai'),
          ])
            _Stat(label, '${now[k] ?? 0}'),
        ]),
        const SizedBox(height: 8),
        Text(_s(r['say']), style: const TextStyle(fontSize: 13, height: 1.35)),
        for (final t in ((r['tips'] as List?) ?? const [])) Text('• $t', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
      ],
    ]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, title: const Text('Community Sahayak')),
        body: Aurora(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 40), children: [
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final (i, t) in const [(0, 'Aaj'), (1, 'Groups'), (2, 'Log'), (3, 'FAQ'), (4, 'Report')])
                  ChoiceChip(label: Text(t), selected: _tab == i, onSelected: (_) => setState(() => _tab = i)),
              ]),
              const SizedBox(height: 10),
              if (_busy) const LinearProgressIndicator(),
              if (_d == null) const Center(child: CircularProgressIndicator()) else [_today(), _groups(), _register(), _faq(), _reportTab()][_tab],
              const SizedBox(height: 14),
              const Text(
                  'Kisi ko nikalna, ban / mute, kisi ki post hatana aur sab ko announcement - sirf aapke "Haan" se, wajah log mein rehti hai. '
                  'Hoola sirf aapke FAQ se jawab deta hai; baaki sawal aapse poochhta hai. Message 90 din baad mit jaate hain. '
                  'Personal WhatsApp group automate nahi hote.',
                  style: TextStyle(color: C.faint, fontSize: 11.5)),
            ]),
          ),
        ),
      );
}

class _Head extends StatelessWidget {
  const _Head(this.t);
  final String t;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 6, bottom: 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, color: C.accentSoft)),
      );
}

class _Stat extends StatelessWidget {
  const _Stat(this.label, this.value);
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Container(
        width: 100,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          Text(label, style: const TextStyle(fontSize: 11.5, color: C.muted)),
        ]),
      );
}

/// One community's rules (language, rules text, welcome / FAQ switches, join mode, links).
class _CommunitySheet extends StatefulWidget {
  const _CommunitySheet({required this.app, required this.c});
  final Santosh app;
  final Map<String, dynamic> c;
  @override
  State<_CommunitySheet> createState() => _CommunitySheetState();
}

class _CommunitySheetState extends State<_CommunitySheet> {
  late final _rules = TextEditingController(text: _s(widget.c['rules']));
  late final _links = TextEditingController(text: ((widget.c['links_allowed'] as List?) ?? const []).join(', '));
  late String _lang = _s(widget.c['language']).isEmpty ? 'hinglish' : _s(widget.c['language']);
  late String _join = _s(widget.c['join_mode']).isEmpty ? 'ask' : _s(widget.c['join_mode']);
  late String _linksPolicy = _s(widget.c['links_policy']).isEmpty ? 'new_no' : _s(widget.c['links_policy']);
  late bool _welcome = widget.c['welcome_on'] != false;
  late bool _faq = widget.c['faq_auto'] != false;
  late bool _paused = widget.c['status'] == 'paused';

  Future<void> _save() async {
    final r = await _call(context, widget.app, 'PATCH', '/api/samudaay/communities/${_s(widget.c['id'])}', body: {
      'rules': _rules.text.trim(),
      'language': _lang,
      'join_mode': _join,
      'links_policy': _linksPolicy,
      'links_allowed': _links.text,
      'welcome_on': _welcome,
      'faq_auto': _faq,
      'status': _paused ? 'paused' : 'active',
    });
    if (r != null && mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_s(widget.c['name']), style: display(20)),
            const SizedBox(height: 8),
            TextField(controller: _rules, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'Group ke niyam')),
            const SizedBox(height: 8),
            const Text('Bhasha', style: TextStyle(color: C.muted, fontSize: 12)),
            Wrap(spacing: 6, children: [
              for (final l in const ['hinglish', 'hindi', 'marathi', 'english'])
                ChoiceChip(label: Text(l), selected: _lang == l, onSelected: (_) => setState(() => _lang = l)),
            ]),
            const SizedBox(height: 6),
            const Text('Join request', style: TextStyle(color: C.muted, fontSize: 12)),
            Wrap(spacing: 6, children: [
              for (final (k, t) in const [('ask', 'Mujhse poochho'), ('auto', 'Saaf ho to le lo'), ('off', 'Kuch mat karo')])
                ChoiceChip(label: Text(t), selected: _join == k, onSelected: (_) => setState(() => _join = k)),
            ]),
            const SizedBox(height: 6),
            const Text('Link', style: TextStyle(color: C.muted, fontSize: 12)),
            Wrap(spacing: 6, children: [
              for (final (k, t) in const [('allow', 'Chalega'), ('new_no', 'Naye log nahi'), ('none', 'Bilkul nahi')])
                ChoiceChip(label: Text(t), selected: _linksPolicy == k, onSelected: (_) => setState(() => _linksPolicy = k)),
            ]),
            TextField(controller: _links, decoration: const InputDecoration(labelText: 'Theek sites (comma se)')),
            SwitchListTile(value: _welcome, onChanged: (v) => setState(() => _welcome = v), title: const Text('Naye logon ko welcome')),
            SwitchListTile(value: _faq, onChanged: (v) => setState(() => _faq = v), title: const Text('FAQ se khud jawab')),
            SwitchListTile(value: _paused, onChanged: (v) => setState(() => _paused = v), title: const Text('Is group mein rok do (pause)')),
            const SizedBox(height: 8),
            GradientButton(label: 'Save', icon: Icons.check_rounded, onTap: _save),
          ]),
        ),
      );
}

// =====================================================================================================================
// Chat / call cards
// =====================================================================================================================

/// `samudaay_alert`: what was spotted + evidence; each suggested step is ONE tap of hers (POST /alerts/{id}/act).
class SamudaayAlertCard extends StatefulWidget {
  const SamudaayAlertCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SamudaayAlertCard> createState() => _SamudaayAlertCardState();
}

class _SamudaayAlertCardState extends State<SamudaayAlertCard> {
  bool _busy = false;
  late String _status = _s(widget.data['status']).isEmpty ? 'open' : _s(widget.data['status']);

  Future<void> _act(String kind, String label) async {
    String? reason;
    if (kind == 'remove' || kind == 'ban' || kind == 'mute') {
      reason = await _ask(context, label, 'Wajah (log mein rahegi)', initial: _s(widget.data['title']));
      if (reason == null) return;
    } else {
      final ok = await showDialog<bool>(
        context: context,
        builder: (d) => AlertDialog(
          title: Text('$label?'),
          content: const Text('Yeh group mein abhi ho jayega.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Nahi')),
            TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Haan')),
          ],
        ),
      );
      if (ok != true) return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/samudaay/alerts/${_s(widget.data['id'])}/act',
        body: {'kind': kind, if (reason != null) 'reason': reason});
    if (mounted) setState(() {
        _busy = false;
        _status = r != null && r['status'] == 'done' ? 'handled' : _status;
      });
    widget.onDone?.call();
  }

  Future<void> _dismiss() async {
    final ev = _map(widget.data['evidence']);
    final hasLinks = ((ev['links'] as List?) ?? const []).isNotEmpty;
    final hasWords = ((ev['words'] as List?) ?? const []).any((w) => !'$w'.startsWith('('));
    setState(() => _busy = true);
    await _call(context, widget.app, 'POST', '/api/samudaay/alerts/${_s(widget.data['id'])}/dismiss',
        body: {'allow_site': hasLinks, 'ok_word': hasWords});
    if (mounted) setState(() {
        _busy = false;
        _status = 'dismissed';
      });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final ev = _map(d['evidence']);
    final sev = _s(d['severity']);
    final open = _status == 'open';
    return Glass(
      border: open ? _sev(sev) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.shield_rounded, color: _sev(sev)),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_kindNames[_s(d['kind'])] ?? _s(d['kind'])}${_s(d['community']).isNotEmpty ? ' · ${_s(d['community'])}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(open ? sev : _status, fg: open ? _sev(sev) : C.chip),
        ]),
        const SizedBox(height: 4),
        Text(_s(d['title']), style: const TextStyle(fontSize: 13)),
        if (_s(ev['member']).isNotEmpty)
          Text('${_s(ev['member'])} · ${ev['posts'] ?? 0} post · chetavni ${ev['warnings'] ?? 0}', style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_s(ev['text']).isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
            child: Text('"${_s(ev['text'])}"', style: const TextStyle(fontSize: 12.5, fontStyle: FontStyle.italic)),
          ),
        for (final w in ((ev['why'] as List?) ?? const [])) Text('• $w', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_s(ev['check']).isNotEmpty) Text(_s(ev['check']), style: const TextStyle(fontSize: 12, color: C.accentSoft)),
        if (_s(ev['note']).isNotEmpty) Text(_s(ev['note']), style: const TextStyle(fontSize: 12, color: C.bad)),
        if (open) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final sug in _list(d['suggest']))
              GlassButton(
                  label: _s(sug['label']),
                  height: 40,
                  color: (sug['kind'] == 'ban' || sug['kind'] == 'remove') ? C.bad : C.ink,
                  onTap: _busy ? null : () => _act(_s(sug['kind']), _s(sug['label']))),
            GlassButton(label: 'Galat alarm', height: 40, icon: Icons.close_rounded, onTap: _busy ? null : _dismiss),
          ]),
        ],
      ]),
    );
  }
}

/// `samudaay_action`: a prepared step (remove / ban / mute / delete / warn / announcement) - runs only on her Haan.
class SamudaayActionCard extends StatefulWidget {
  const SamudaayActionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SamudaayActionCard> createState() => _SamudaayActionCardState();
}

class _SamudaayActionCardState extends State<SamudaayActionCard> {
  bool _busy = false;
  late String _status = _s(widget.data['status']).isEmpty ? 'pending' : _s(widget.data['status']);
  String _result = '';

  Future<void> _decide(bool yes) async {
    final d = widget.data;
    String reason = _s(d['reason']);
    if (yes && d['needs_reason'] == true && reason.isEmpty) {
      final r = await _ask(context, _s(d['label']), 'Wajah (log mein rahegi)');
      if (r == null) return;
      reason = r;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/samudaay/actions/${_s(d['id'])}/decide',
        body: {'yes': yes, 'hash': _s(d['hash']), 'reason': reason});
    if (mounted) {
      setState(() {
        _busy = false;
        if (r != null) {
          _status = _s(r['status']);
          _result = _s(r['result']);
        }
      });
    }
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final danger = const ['remove', 'ban', 'mute', 'delete_post'].contains(d['kind']);
    final pending = _status == 'pending';
    return Glass(
      border: pending ? (danger ? C.bad : C.accent) : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(d['kind'] == 'announce' ? Icons.campaign_rounded : Icons.gavel_rounded, color: danger ? C.bad : C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(d['label'])}${_s(d['member']).isNotEmpty ? ': ${_s(d['member'])}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status),
        ]),
        Text(_s(d['community']), style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_s(d['post']).isNotEmpty) Text('Post: "${_s(d['post'])}"', style: const TextStyle(fontSize: 12.5, fontStyle: FontStyle.italic)),
        if (_s(d['text']).isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
            child: Text(_s(d['text']), style: const TextStyle(fontSize: 13)),
          ),
        if (_s(d['reason']).isNotEmpty) Text('Wajah: ${_s(d['reason'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
        if ((d['hours'] ?? 0) > 0 && d['kind'] == 'mute') Text('${d['hours']} ghante', style: const TextStyle(fontSize: 12, color: C.muted)),
        if (_result.isNotEmpty) Text(_result, style: const TextStyle(fontSize: 12, color: C.faint)),
        if (pending) ...[
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: GradientButton(label: 'Haan, karo', icon: Icons.check_rounded, height: 46, onTap: _busy ? null : () => _decide(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Nahi', height: 46, onTap: _busy ? null : () => _decide(false)),
          ]),
        ],
      ]),
    );
  }
}

/// `samudaay_question`: a member asked something her FAQ doesn't cover. Her words go back as the reply and into the FAQ.
class SamudaayQuestionCard extends StatefulWidget {
  const SamudaayQuestionCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SamudaayQuestionCard> createState() => _SamudaayQuestionCardState();
}

class _SamudaayQuestionCardState extends State<SamudaayQuestionCard> {
  final _c = TextEditingController();
  bool _busy = false;
  bool _save = true;
  String _status = '';

  Future<void> _send({String faqId = '', bool ignore = false}) async {
    if (!ignore && faqId.isEmpty && _c.text.trim().isEmpty) return;
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/samudaay/questions/${_s(widget.data['id'])}', body: {
      if (ignore) 'ignore': true,
      'answer': _c.text.trim(),
      'save_faq': _save,
      if (faqId.isNotEmpty) 'faq_id': faqId,
    });
    if (mounted) setState(() {
        _busy = false;
        _status = r == null ? _status : (ignore ? 'ignored' : 'answered');
      });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final likely = _map(d['likely']);
    final done = _status.isNotEmpty || (_s(d['status']).isNotEmpty && d['status'] != 'open');
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.help_outline_rounded, color: C.teal),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(d['member'])} ne poochha${_s(d['community']).isNotEmpty ? ' · ${_s(d['community'])}' : ''}',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
          if ((d['count'] ?? 1) > 1) Pill('${d['count']} log'),
        ]),
        const SizedBox(height: 4),
        Text('"${_s(d['text'])}"', style: const TextStyle(fontSize: 13.5, fontStyle: FontStyle.italic)),
        if (done)
          Padding(padding: const EdgeInsets.only(top: 6), child: Pill(_status.isNotEmpty ? _status : _s(d['status'])))
        else ...[
          if (likely.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('Shayad yeh FAQ: ${_s(likely['question'])}', style: const TextStyle(fontSize: 12, color: C.muted)),
            GlassButton(label: 'Yahi jawab bhejo', height: 38, onTap: _busy ? null : () => _send(faqId: _s(likely['id']))),
          ],
          TextField(controller: _c, minLines: 1, maxLines: 4, decoration: const InputDecoration(hintText: 'Aapka jawab (Hoola yahi bhejega)')),
          CheckboxListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              value: _save,
              onChanged: (v) => setState(() => _save = v ?? true),
              title: const Text('Agli baar ke liye FAQ mein rakho', style: TextStyle(fontSize: 12.5))),
          Row(children: [
            Expanded(child: GradientButton(label: 'Jawab bhejo', icon: Icons.send_rounded, height: 44, onTap: _busy ? null : () => _send())),
            const SizedBox(width: 8),
            GlassButton(label: 'Chhodo', height: 44, onTap: _busy ? null : () => _send(ignore: true)),
          ]),
        ],
      ]),
    );
  }
}

/// `samudaay_join`: someone wants to join (flags from name / bio). Approving / declining is her tap.
class SamudaayJoinCard extends StatefulWidget {
  const SamudaayJoinCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SamudaayJoinCard> createState() => _SamudaayJoinCardState();
}

class _SamudaayJoinCardState extends State<SamudaayJoinCard> {
  bool _busy = false;
  String _status = '';

  Future<void> _go(bool yes) async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/samudaay/joins/${_s(widget.data['id'])}', body: {'yes': yes});
    if (mounted) setState(() {
        _busy = false;
        _status = r == null ? _status : _s(r['status']);
      });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final flags = ((d['flags'] as List?) ?? const []).map((e) => '$e').toList();
    return Glass(
      border: flags.isNotEmpty ? C.warn : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.person_add_alt_1_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(
              child: Text('${_s(d['name'])}${_s(d['username']).isNotEmpty ? ' (@${_s(d['username'])})' : ''} judna chahte hain',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        if (_s(d['community']).isNotEmpty) Text(_s(d['community']), style: const TextStyle(color: C.muted, fontSize: 12)),
        if (_s(d['bio']).isNotEmpty) Text('Bio: ${_s(d['bio'])}', style: const TextStyle(fontSize: 12.5)),
        for (final f in flags) Text('⚠ $f', style: const TextStyle(fontSize: 12, color: C.warn)),
        const SizedBox(height: 8),
        if (_status.isNotEmpty)
          Pill(_status)
        else
          Row(children: [
            Expanded(child: GradientButton(label: 'Andar lo', icon: Icons.check_rounded, height: 44, onTap: _busy ? null : () => _go(true))),
            const SizedBox(width: 8),
            GlassButton(label: 'Mana', height: 44, onTap: _busy ? null : () => _go(false)),
          ]),
      ]),
    );
  }
}

/// `samudaay_template`: welcome / rules message waiting for her approval (hash-checked on the server).
class SamudaayTemplateCard extends StatefulWidget {
  const SamudaayTemplateCard({super.key, required this.app, required this.data, this.onDone});
  final Santosh app;
  final Map<String, dynamic> data;
  final VoidCallback? onDone;
  @override
  State<SamudaayTemplateCard> createState() => _SamudaayTemplateCardState();
}

class _SamudaayTemplateCardState extends State<SamudaayTemplateCard> {
  bool _busy = false;
  late String _status = _s(widget.data['status']);

  Future<void> _approve() async {
    setState(() => _busy = true);
    final r = await _call(context, widget.app, 'POST', '/api/samudaay/templates/${_s(widget.data['id'])}/approve',
        body: {'hash': _s(widget.data['hash'])});
    if (mounted) setState(() {
        _busy = false;
        _status = r == null ? _status : 'approved';
      });
    widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final problems = ((d['problems'] as List?) ?? const []).map((e) => '$e').toList();
    final preview = _s(d['preview']).isNotEmpty ? _s(d['preview']) : _s(d['text']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          const Icon(Icons.waving_hand_rounded, color: C.accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${d['kind'] == 'rules' ? 'Niyam' : 'Welcome'} message · ${_s(d['language'])}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Pill(_status == 'approved' ? 'manzoor' : 'draft'),
        ]),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(12)),
          child: Text(preview, style: const TextStyle(fontSize: 13)),
        ),
        for (final p in problems) Text('⚠ $p', style: const TextStyle(fontSize: 12, color: C.warn)),
        if (_status != 'approved') ...[
          const SizedBox(height: 8),
          GradientButton(label: 'Haan, yahi bhejo', icon: Icons.check_rounded, height: 44, onTap: _busy || problems.isNotEmpty ? null : _approve),
        ],
      ]),
    );
  }
}

/// `samudaay_week` (weekly health) and `samudaay_info` (a group got joined, etc.): text cards.
class SamudaayInfoCard extends StatelessWidget {
  const SamudaayInfoCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;
  @override
  Widget build(BuildContext context) {
    final h = _map(data['health']);
    final tips = ((data['tips'] as List?) ?? const []).map((e) => '$e').toList();
    final text = _s(data['say']).isNotEmpty ? _s(data['say']) : _s(data['text']);
    return Glass(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(h.isEmpty ? Icons.groups_rounded : Icons.monitor_heart_rounded, color: C.teal),
          const SizedBox(width: 8),
          Expanded(
              child: Text(h.isEmpty ? 'Community' : '${_s(data['community'])} · hafte ki sehat ${h['score']}/100',
                  style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 4),
        Text(text, style: const TextStyle(fontSize: 13, height: 1.35)),
        for (final t in tips) Text('• $t', style: const TextStyle(fontSize: 12.5, color: C.accentSoft)),
        const SizedBox(height: 6),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SamudaayScreen(app: app))),
              child: const Text('Community Sahayak kholo')),
        ),
      ]),
    );
  }
}
