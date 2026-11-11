import 'dart:convert';

import 'package:flutter/material.dart';

import '../hoola.dart';
import '../state.dart';
import 'avatar_look.dart';
import 'glass.dart';

const _names = ['Santosh', 'Raju', 'Arjun', 'Veer', 'Priya', 'Meera', 'Sakhi', 'Kavya'];

const _knock = {
  'id_or_qr': 'Anyone who has my Hoola ID / QR',
  'verified': 'Verified people only',
  'anyone': 'Anyone',
  'nobody': 'Nobody for now',
};
const _kinds = {
  'message': 'Message',
  'voice_note': 'Voice note',
  'file': 'File (PDF, photo, Excel)',
  'app_file': 'APK / EXE (after App Check)',
  'email': 'Email',
  'link': 'Website link',
  'presentation': 'Presentation',
  'meeting': 'Meeting request',
  'payment_request': 'Payment request',
  'contact_card': 'Contact card',
  'location': 'Location',
};
const _alwaysAsk = {'payment_request', 'app_file'};
const _share = {
  'free_busy': 'Whether I am free or busy',
  'office_hours': 'Office hours',
  'business_info': 'Business information',
  'price_list': 'Price list',
  'phone': 'My phone number',
  'email_address': 'My email ID',
  'address': 'My address',
};
const _aboutKeys = {'business_info', 'office_hours', 'price_list'};
const _aboutHint = {
  'business_info': 'About the business: what it does, where, how to contact (only what is fine to tell everyone)',
  'office_hours': 'For example: Mon-Sat 10 to 7, closed Sunday',
  'price_list': 'For example: ONT 1200, installation 500, 100 Mbps plan 599/month',
};
const _alone = {
  'fix_meetings': 'Fix meetings by itself in free time',
  'answer_faq': 'Answer common business questions by itself',
  'accept_files_from_vip': 'Take the VIP\'s file by itself',
};
const _langs = {
  'hinglish': 'Hinglish', 'hindi': 'हिंदी', 'marathi': 'मराठी', 'english': 'English', 'gujarati': 'ગુજરાતી',
  'tamil': 'தமிழ்', 'telugu': 'తెలుగు', 'kannada': 'ಕನ್ನಡ', 'bengali': 'বাংলা', 'punjabi': 'ਪੰਜਾਬੀ', 'malayalam': 'മലയാളം',
};

/// First run (and Profile > Mera Hoola): name your avatar, pick male / female and a voice, then set Mere Niyam
/// (how other people's avatars may reach you). [rulesOnly] opens straight at the rules.
class AvatarSetupScreen extends StatefulWidget {
  const AvatarSetupScreen({super.key, required this.app, this.rulesOnly = false, this.firstRun = false});
  final Santosh app;
  final bool rulesOnly;
  final bool firstRun;
  @override
  State<AvatarSetupScreen> createState() => _AvatarSetupScreenState();
}

class _AvatarSetupScreenState extends State<AvatarSetupScreen> {
  late int _page;
  late final TextEditingController _name;
  final _words = TextEditingController();
  late final TextEditingController _vip;
  late final TextEditingController _blocked;
  late String _gender;
  String _voice = '';
  String _look = '';            // '' = Santosh; f001..f100 / m001..m100
  late Map<String, dynamic> _rules;
  bool _busy = false;
  String? _err;
  List<String> _summary = [];

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    _page = widget.rulesOnly ? 2 : 0;
    _name = TextEditingController(text: app.aName);
    _gender = app.aFemale ? 'f' : 'm';
    _voice = app.avatar['voice'] as String? ?? '';
    _look = app.aLook;
    _rules = Map<String, dynamic>.from(jsonDecode(jsonEncode(app.avatarRules)) as Map);
    _rules.putIfAbsent('accept', () => <String, dynamic>{});
    _rules.putIfAbsent('share', () => <String, dynamic>{});
    _rules.putIfAbsent('decide_alone', () => <String, dynamic>{});
    _rules.putIfAbsent('quiet', () => <String, dynamic>{'on': true, 'from': '22:00', 'to': '08:00', 'vip_can_ring': true});
    _rules.putIfAbsent('learning', () => <String, dynamic>{'learn_from_my_work': true, 'share_lessons': 'ask'});
    _rules.putIfAbsent('about', () => <String, dynamic>{'business_info': '', 'office_hours': '', 'price_list': ''});
    _rules.putIfAbsent('selling', () => <String, dynamic>{'auto_quote': 'off', 'auto_quote_max': 25000, 'auto_accept': false,
          'auto_accept_max': 25000, 'trusted': <String>[], 'valid_minutes': 120, 'catalog': 'connected', 'show_stock': false,
          'auto_ready': true, 'packers': <String>[]});
    _vip = TextEditingController(text: List<String>.from(_rules['vip'] as List? ?? const []).join(', '));
    _blocked = TextEditingController(text: List<String>.from(_rules['blocked_topics'] as List? ?? const []).join(', '));
  }

  @override
  void dispose() {
    _name.dispose();
    _words.dispose();
    _vip.dispose();
    _blocked.dispose();
    super.dispose();
  }

  String get _n => _name.text.trim().isEmpty ? 'Santosh' : _name.text.trim();
  String _gv(String s) => _gender == 'f' ? genderedHi(s) : s;

  Map<String, dynamic> _sub(String k) => (_rules[k] as Map).cast<String, dynamic>();

  List<String> _split(String s) => s.split(RegExp(r'[,\n]')).map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

  Future<void> _next() async {
    setState(() => _err = null);
    if (_page == 0) {
      setState(() => _busy = true);
      final e = await app.saveAvatar(name: _n);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      setState(() => _page = 1);
    } else if (_page == 1) {
      setState(() => _busy = true);
      final e = await app.saveAvatar(gender: _gender, voice: _voice);
      final e2 = e == null ? await app.saveAvatar(look: lookFits(_look, _gender) ? _look : (_gender == 'f' ? 'f001' : '')) : null;
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null || e2 != null) {
        setState(() => _err = e ?? e2);
        return;
      }
      setState(() => _page = 2);
    } else if (_page == 2) {
      _rules['vip'] = _split(_vip.text);
      _rules['blocked_topics'] = _split(_blocked.text);
      setState(() => _busy = true);
      final e = await app.saveAvatar(rules: _rules);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      setState(() {
        _summary = List<String>.from(app.avatar['rules_summary'] as List? ?? const []);
        _page = 3;
      });
    } else {
      setState(() => _busy = true);
      final e = await app.saveAvatar(setupDone: true);
      if (!mounted) return;
      setState(() => _busy = false);
      if (e != null) {
        setState(() => _err = e);
        return;
      }
      if (!widget.firstRun && Navigator.of(context).canPop()) Navigator.of(context).pop();
    }
  }

  Future<void> _understand() async {
    final t = _words.text.trim();
    if (t.isEmpty) return;
    setState(() { _busy = true; _err = null; });
    try {
      final r = await app.api!.avatarParseRules(t);
      if (!mounted) return;
      setState(() {
        _rules = Map<String, dynamic>.from(r['rules'] as Map);
        _vip.text = List<String>.from(_rules['vip'] as List? ?? const []).join(', ');
        _blocked.text = List<String>.from(_rules['blocked_topics'] as List? ?? const []).join(', ');
      });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Understood. Look below, then tap Next.')));
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickTime(String key) async {
    final q = _sub('quiet');
    final parts = (q[key] as String? ?? '22:00').split(':');
    final t = await showTimePicker(
        context: context, initialTime: TimeOfDay(hour: int.tryParse(parts[0]) ?? 22, minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0));
    if (t == null) return;
    setState(() => q[key] = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}');
  }

  // ---------------------------------------------------------------- pages
  Widget _namePage() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Give your Hoola a name', style: display(26)),
        const SizedBox(height: 6),
        const Text('This is your AI companion. You choose the name: it will talk to you by this name, and other people\'s Hoolas '
            'will know it as "yours" by this name.', style: TextStyle(color: C.muted, fontSize: 13.5)),
        const SizedBox(height: 18),
        Glass(
          child: TextField(
            controller: _name,
            maxLength: 20,
            textCapitalization: TextCapitalization.words,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            decoration: const InputDecoration(border: InputBorder.none, counterText: '', hintText: 'e.g. Santosh'),
            onChanged: (_) => setState(() {}),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final n in _names)
            ChoiceChip(
              label: Text(n),
              selected: _name.text.trim() == n,
              showCheckmark: false,
              selectedColor: C.accent,
              labelStyle: TextStyle(color: _name.text.trim() == n ? C.onAccent : C.chip, fontWeight: FontWeight.w600),
              onSelected: (_) => setState(() => _name.text = n),
            ),
        ]),
        const SizedBox(height: 14),
        const Text('You can write the name in Hindi, Marathi or any language. Bank, police or government names are not allowed.',
            style: TextStyle(color: C.faint, fontSize: 12)),
      ]);

  Widget _genderCard(String g, String title, String sub, IconData icon) {
    final on = _gender == g;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() {
          if (_gender != g) _voice = '';
          if (!lookFits(_look, g)) _look = g == 'f' ? 'f001' : '';
          _gender = g;
        }),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: on ? const Color(0x33FFB15C) : C.panel,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: on ? C.accent : C.line, width: on ? 2 : 1),
          ),
          child: Column(children: [
            Icon(icon, size: 34, color: on ? C.accent : C.chip),
            const SizedBox(height: 6),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(sub, textAlign: TextAlign.center, style: const TextStyle(color: C.muted, fontSize: 12)),
          ]),
        ),
      ),
    );
  }

  /// The 3D look: one of 100 from around the world for her / for him (men can keep the original Santosh).
  Widget _lookCard() {
    final l = lookFits(_look, _gender) ? _look : (_gender == 'f' ? 'f001' : '');
    return Glass(
      child: Row(children: [
        SizedBox(width: 74, height: 108, child: Image.asset(lookFull(l), fit: BoxFit.contain)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('$_n\'s look', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 2),
            Text(_gender == 'f' ? '100 voices, from all over the world. This is what will show on calls, chat and the Hoola Network.'
                : '100 voices, from all over the world, or the original Santosh. This is what will show on calls, chat and the Hoola Network.', style: const TextStyle(color: C.muted, fontSize: 12.5)),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.palette_outlined, size: 18),
              label: const Text('Change the look'),
              onPressed: () async {
                final id = await Navigator.of(context).push<String>(
                    MaterialPageRoute(builder: (_) => LookPickerScreen(initial: l, avatarName: _n, gender: _gender)));
                if (id != null && mounted) setState(() => _look = id);
              },
            ),
          ]),
        ),
      ]),
    );
  }

  Widget _voicePage() {
    final voices = List<Map<String, dynamic>>.from(((app.avatar['voices'] as Map?)?[_gender] as List? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map)));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Is $_n male or female?', style: display(24)),
      const SizedBox(height: 6),
      const Text('This decides the voice and the way it speaks.', style: TextStyle(color: C.muted, fontSize: 13.5)),
      const SizedBox(height: 16),
      Row(children: [
        _genderCard('m', 'Male', '"$_n is working on it"', Icons.face_rounded),
        const SizedBox(width: 12),
        _genderCard('f', 'Female', '"$_n is working on it"', Icons.face_3_rounded),
      ]),
      const SizedBox(height: 14),
      _lookCard(),
      const SizedBox(height: 18),
      Text('$_n\'s voice (on calls)', style: const TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final v in voices)
          ChoiceChip(
            label: Text('${v['id']} · ${v['label']}'),
            selected: (_voice.isEmpty ? (voices.isNotEmpty ? voices.first['id'] : '') : _voice) == v['id'],
            showCheckmark: false,
            selectedColor: C.accent,
            labelStyle: TextStyle(
                color: (_voice.isEmpty ? (voices.isNotEmpty ? voices.first['id'] : '') : _voice) == v['id'] ? C.onAccent : C.chip,
                fontWeight: FontWeight.w600,
                fontSize: 12.5),
            onSelected: (_) => setState(() => _voice = v['id'] as String),
          ),
      ]),
    ]);
  }

  Widget _section(String title, [String? sub]) => Padding(
        padding: const EdgeInsets.only(top: 18, bottom: 6),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
          if (sub != null) Text(sub, style: const TextStyle(color: C.muted, fontSize: 12.5)),
        ]),
      );

  Widget _chip(String label, bool on, VoidCallback tap) => ChoiceChip(
        label: Text(label),
        selected: on,
        showCheckmark: false,
        selectedColor: C.accent,
        labelStyle: TextStyle(color: on ? C.onAccent : C.chip, fontWeight: FontWeight.w600, fontSize: 12.5),
        onSelected: (_) => tap(),
      );

  /// v0.105 Bechna: what the avatar may do alone when another avatar sends a list (order still needs the buyer's tap).
  List<Widget> _sellingSection() {
    final sell = _sub('selling');
    String inr(dynamic v) => '₹${(v is num ? v : num.tryParse('$v') ?? 0).toInt()}';
    return [
      _section('Selling (Hoola Network)', _gv('When a list arrives, when $_n may send a quote by itself. An order always needs the customer\'s yes.')),
      Wrap(spacing: 8, runSpacing: 8, children: [
        _chip('Ask every time', (sell['auto_quote'] ?? 'off') == 'off', () => setState(() => sell['auto_quote'] = 'off')),
        _chip('By itself to trusted people', sell['auto_quote'] == 'trusted', () => setState(() => sell['auto_quote'] = 'trusted')),
        _chip('By itself to all connected people', sell['auto_quote'] == 'connected', () => setState(() => sell['auto_quote'] = 'connected')),
      ]),
      if ((sell['auto_quote'] ?? 'off') != 'off') ...[
        const SizedBox(height: 6),
        Text('Only quotes with full stock, up to this amount: ${inr(sell['auto_quote_max'])}', style: const TextStyle(color: C.muted, fontSize: 12.5)),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final x in const [5000, 25000, 100000]) _chip(inr(x), sell['auto_quote_max'] == x, () => setState(() => sell['auto_quote_max'] = x)),
        ]),
      ],
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: Text('Confirm the order by itself after the customer\'s yes (if in stock, up to ${inr(sell['auto_accept_max'])})'),
        value: sell['auto_accept'] == true,
        onChanged: (v) => setState(() => sell['auto_accept'] = v),
      ),
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: const Text('Send the customer a pickup code as soon as it is packed'),
        value: sell['auto_ready'] != false,
        onChanged: (v) => setState(() => sell['auto_ready'] = v),
      ),
      const SizedBox(height: 4),
      const Text('Who sees the price list:', style: TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 8, children: [
        _chip('No one', sell['catalog'] == 'off', () => setState(() => sell['catalog'] = 'off')),
        _chip('To connected people', (sell['catalog'] ?? 'connected') == 'connected', () => setState(() => sell['catalog'] = 'connected')),
        _chip('To everyone', sell['catalog'] == 'public', () => setState(() => sell['catalog'] = 'public')),
      ]),
      const SizedBox(height: 8),
      Glass(
        child: TextFormField(
          initialValue: List<String>.from(sell['trusted'] as List? ?? const []).join(', '),
          decoration: const InputDecoration(border: InputBorder.none, labelText: 'Trusted customers (name / Hoola ID)'),
          onChanged: (t) => sell['trusted'] = _split(t),
        ),
      ),
      const SizedBox(height: 8),
      Glass(
        child: TextFormField(
          initialValue: List<String>.from(sell['packers'] as List? ?? const []).join(', '),
          decoration: const InputDecoration(border: InputBorder.none, labelText: 'Who will pack (blank = team manager + packers)'),
          onChanged: (t) => sell['packers'] = _split(t),
        ),
      ),
    ];
  }

  Widget _rulesPage() {
    final accept = _sub('accept');
    final share = _sub('share');
    final alone = _sub('decide_alone');
    final quiet = _sub('quiet');
    final learning = _sub('learning');
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('My Rules', style: display(26)),
      const SizedBox(height: 6),
      Text(_gv('Other people\'s Hoolas will talk to you only through $_n. With these rules, $_n decides what to tell you, '
          'what to handle itself and what to refuse.'), style: const TextStyle(color: C.muted, fontSize: 13.5)),
      const SizedBox(height: 14),
      Glass(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Say or write it in your own words', style: TextStyle(fontWeight: FontWeight.w700)),
          TextField(
            controller: _words,
            minLines: 2,
            maxLines: 5,
            decoration: const InputDecoration(
                border: InputBorder.none,
                hintText: 'For example: "Family and Swati can always reach me. Refuse loan callers. Do not disturb me after 11 pm. '
                    'Fix meetings by yourself in free time."'),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
                onPressed: _busy ? null : _understand, icon: const Icon(Icons.auto_awesome_rounded, size: 18), label: const Text('Understand')),
          ),
        ]),
      ),
      _section('Who can send a request'),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final e in _knock.entries) _chip(e.value, _rules['knock'] == e.key, () => setState(() => _rules['knock'] = e.key)),
      ]),
      _section('VIPs: can always reach me', 'Name or Hoola ID, comma separated'),
      Glass(child: TextField(controller: _vip, decoration: const InputDecoration(border: InputBorder.none, hintText: 'Family, Swati, @kunal.raj'))),
      _section('Refuse directly', 'Requests $_n should refuse by itself'),
      Glass(child: TextField(controller: _blocked, decoration: const InputDecoration(border: InputBorder.none, hintText: 'loan, insurance, sales pitch'))),
      _section('What can come in', 'Direct = $_n takes it · Ask = asks you first · Refuse = no'),
      for (final e in _kinds.entries)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(children: [
            Expanded(child: Text(e.value, style: const TextStyle(fontSize: 13))),
            Wrap(spacing: 6, children: [
              if (!_alwaysAsk.contains(e.key))
                _chip('Auto', accept[e.key] == 'auto', () => setState(() => accept[e.key] = 'auto')),
              _chip('Ask', (accept[e.key] ?? 'ask') == 'ask', () => setState(() => accept[e.key] = 'ask')),
              _chip('Refuse', accept[e.key] == 'never', () => setState(() => accept[e.key] = 'never')),
            ]),
          ]),
        ),
      _section(_gv('What $_n may tell others')),
      for (final e in _share.entries) ...[
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(e.value),
          value: share[e.key] == true,
          onChanged: (v) => setState(() => share[e.key] = v),
        ),
        if (_aboutKeys.contains(e.key) && share[e.key] == true)
          Glass(
            child: TextFormField(
              initialValue: (_sub('about')[e.key] as String?) ?? '',
              minLines: 1,
              maxLines: 5,
              decoration: InputDecoration(border: InputBorder.none, hintText: _aboutHint[e.key]),
              onChanged: (t) => _sub('about')[e.key] = t,
            ),
          ),
      ],
      _section(_gv('What $_n may do by itself'), 'It will ask you first about everything else. Never any money without your tap.'),
      for (final e in _alone.entries)
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: Text(e.value),
          value: alone[e.key] == true,
          onChanged: (v) => setState(() => alone[e.key] = v),
        ),
      _section('Quiet hours'),
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: const Text('Do not disturb at this time'),
        value: quiet['on'] == true,
        onChanged: (v) => setState(() => quiet['on'] = v),
      ),
      if (quiet['on'] == true) ...[
        Row(children: [
          TextButton(onPressed: () => _pickTime('from'), child: Text('Se ${quiet['from'] ?? '22:00'}')),
          TextButton(onPressed: () => _pickTime('to'), child: Text('Until ${quiet['to'] ?? '08:00'}')),
        ]),
        SwitchListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          title: const Text('VIPs can still reach me'),
          value: quiet['vip_can_ring'] == true,
          onChanged: (v) => setState(() => quiet['vip_can_ring'] = v),
        ),
      ],
      _section(_gv('In which language $_n tells you')),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final e in _langs.entries) _chip(e.value, (_rules['language'] ?? 'hinglish') == e.key, () => setState(() => _rules['language'] = e.key)),
      ]),
      _section('Learning'),
      SwitchListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: Text(_gv('Let $_n keep learning from my work')),
        value: learning['learn_from_my_work'] == true,
        onChanged: (v) => setState(() => learning['learn_from_my_work'] = v),
      ),
      const SizedBox(height: 4),
      const Text('Share what it has learned with others (without personal details):', style: TextStyle(color: C.muted, fontSize: 12.5)),
      const SizedBox(height: 6),
      Wrap(spacing: 8, runSpacing: 8, children: [
        _chip('Never', learning['share_lessons'] == 'never', () => setState(() => learning['share_lessons'] = 'never')),
        _chip('Ask first', (learning['share_lessons'] ?? 'ask') == 'ask', () => setState(() => learning['share_lessons'] = 'ask')),
        _chip('In my groups', learning['share_lessons'] == 'groups', () => setState(() => learning['share_lessons'] = 'groups')),
      ]),
      ..._sellingSection(),
      const SizedBox(height: 14),
      const Text('This always stays: money only with your tap. PINs, OTPs and passwords never go to anyone.',
          style: TextStyle(color: C.teal, fontSize: 12.5, fontWeight: FontWeight.w600)),
    ]);
  }

  Widget _confirmPage() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Hello! I am $_n.', style: display(26)),
        const SizedBox(height: 6),
        Text(_gv('These are your rules. $_n will talk to other Hoolas according to them. You can change them any time in Profile > My Rules.'),
            style: const TextStyle(color: C.muted, fontSize: 13.5)),
        const SizedBox(height: 14),
        Glass(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final l in _summary)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Padding(padding: EdgeInsets.only(top: 2), child: Icon(Icons.check_rounded, size: 16, color: C.ok)),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_gv(l), style: const TextStyle(fontSize: 13))),
                ]),
              ),
          ]),
        ),
      ]);

  @override
  Widget build(BuildContext context) {
    final pages = [_namePage, _voicePage, _rulesPage, _confirmPage];
    final last = _page == 3;
    final canBack = _page > (widget.rulesOnly ? 2 : 0);
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        automaticallyImplyLeading: !widget.firstRun,
        title: Text(widget.firstRun ? appName : (widget.rulesOnly ? 'My Rules' : 'My Hoola')),
      ),
      body: Aurora(
        child: SafeArea(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                for (var i = widget.rulesOnly ? 2 : 0; i < 4; i++)
                  Expanded(
                    child: Container(
                      height: 4,
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      decoration: BoxDecoration(color: i <= _page ? C.accent : C.line, borderRadius: BorderRadius.circular(2)),
                    ),
                  ),
              ]),
            ),
            Expanded(
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
                pages[_page](),
                if (_err != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_err!, style: const TextStyle(color: C.bad))),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Row(children: [
                if (canBack)
                  Padding(
                    padding: const EdgeInsets.only(right: 10),
                    child: TextButton(onPressed: _busy ? null : () => setState(() => _page -= 1), child: const Text('Back')),
                  ),
                Expanded(
                  child: GradientButton(
                    label: _busy ? 'Please wait…' : (last ? 'Start' : 'Next'),
                    icon: last ? Icons.check_rounded : Icons.arrow_forward_rounded,
                    onTap: _busy ? null : _next,
                  ),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
