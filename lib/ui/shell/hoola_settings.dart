// v0.867 R7 SETTINGS + YOUR AI TEAM (docs/HOOLA_APP_REDESIGN_PLAN.md R7): the old Main / Profile page split in two,
// in the new design.
//
//   Settings (from the drawer's avatar) - six groups:
//     You and Hoola · Memory · Look and voice · Phone and notifications · Privacy and safety · Account
//   Your AI team - every desk and tool that sat on Main, grouped by kind of work, one search box
//                  (hoola_team_list.dart, generated from the old page's own rows)
//
// Every old Main row lands in exactly one place: test/hoola_settings_test.dart reads the old page and fails if a
// screen it opened, or an inline setting it held (name / city / briefing, language, answer by voice, background,
// wake word, Google accounts, memory pins, log out), has no way in here. Screens not rebuilt yet open in their old
// frame (hoolaOpenOld) until R8. Nothing on the server changes.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../native.dart';
import '../../state.dart';
import '../approve_key_screen.dart';
import '../avatar_look.dart';
import '../avatar_setup_screen.dart';
import '../bahar_screen.dart';
import '../call_quality_screen.dart';
import '../enterprise_screen.dart';
import '../glass.dart';
import '../hoola_net_screen.dart';
import '../hoola_samaj_screen.dart';
import '../hoola_theme.dart';
import '../id_locker_screen.dart';
import '../keep_alive.dart';
import '../kharcha_screen.dart';
import '../memory_page_screen.dart';
import '../phone_hoola.dart';
import '../procedures_screen.dart';
import '../screen_link.dart';
import '../voice_engine_screen.dart';
import '../voice_id_screen.dart';
import '../voice_learned_screen.dart';
import 'hoola_tabs.dart';
import 'hoola_team_list.dart';

/// An old (Night Glass) screen in its own frame, until its phase rebuilds it.
Future<T?> hoolaOpenOld<T>(BuildContext context, Widget screen) => Navigator.of(context)
    .push<T>(MaterialPageRoute<T>(builder: (_) => Theme(data: santoshTheme(), child: Aurora(child: screen))));

/// A screen in the new design, pushed with the app's appearance.
Future<void> hoolaOpenNew(BuildContext context, Santosh app, Widget screen) => Navigator.of(context)
    .push(MaterialPageRoute<void>(builder: (_) => HoolaTheme(appearance: app.appearance, child: screen)));

/// The shared page frame: a back arrow, a big title and a scrolling list.
class _Page extends StatelessWidget {
  const _Page({required this.title, this.sub = '', required this.children, this.onRefresh});
  final String title, sub;
  final List<Widget> children;
  final Future<void> Function()? onRefresh;
  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final list = ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.only(bottom: HoolaSpace.s32),
      children: [HoolaTabHeader(title: title, sub: sub), ...children],
    );
    return Scaffold(
      backgroundColor: c.bg,
      appBar: AppBar(
        backgroundColor: c.bg,
        surfaceTintColor: c.bg,
        foregroundColor: c.ink,
        elevation: 0,
        toolbarHeight: 48,
      ),
      body: SafeArea(top: false, child: onRefresh == null ? list : RefreshIndicator(color: c.accent, onRefresh: onRefresh!, child: list)),
    );
  }
}

Widget _chev(HoolaColors c) => Icon(Icons.chevron_right_rounded, color: c.ink3);

/// A row with a switch on the right (the whole row toggles it).
Widget _switchRow(BuildContext context,
    {required String title, String sub = '', required IconData icon, required bool value, required ValueChanged<bool> onChanged}) {
  final c = HoolaColors.of(context);
  return HoolaRow(
    title: title,
    sub: sub,
    icon: icon,
    semantics: '$title, ${value ? 'on' : 'off'}',
    trailing: Switch(value: value, onChanged: onChanged, activeColor: c.onAccent, activeTrackColor: c.accent),
    onTap: () => onChanged(!value),
  );
}

Future<bool> _confirm(BuildContext context, String title, String body, String yes, {bool danger = false}) async {
  final c = HoolaColors.of(context);
  final ok = await showModalBottomSheet<bool>(
    context: context,
    backgroundColor: c.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(title, style: HoolaType.heading(c)),
          const SizedBox(height: 8),
          Text(body, style: HoolaType.body(c).copyWith(color: c.ink2)),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(
                backgroundColor: danger ? c.bad : c.pill,
                foregroundColor: danger ? c.onAccent : c.onPill,
                shape: const StadiumBorder(),
                minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: Text(yes),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
            child: const Text('Cancel'),
          ),
        ]),
      ),
    ),
  );
  return ok == true;
}

void _say(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

// ================================================================== SETTINGS
class HoolaSettings extends StatefulWidget {
  const HoolaSettings({super.key, required this.app, required this.onReset});
  final Santosh app;
  final VoidCallback onReset;
  @override
  State<HoolaSettings> createState() => _HoolaSettingsState();
}

class _HoolaSettingsState extends State<HoolaSettings> with WidgetsBindingObserver {
  bool _wakeOn = false;
  String _wakeStatus = '';
  Timer? _wakePoll;

  Santosh get app => widget.app;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_refreshPhone());
    _wakePoll = Timer.periodic(const Duration(seconds: 5), (_) => _refreshWake());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _wakePoll?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) unawaited(_refreshPhone());   // back from a phone settings screen
  }

  Future<void> _refreshPhone() async {
    try {
      await app.refreshBackgroundInfo();
      unawaited(HoolaKeepAlive.check(app).catchError((_) => null));
    } catch (_) {}
    await _refreshWake();
  }

  Future<void> _refreshWake() async {
    try {
      final s = await Native.wakeStatus();
      if (!mounted) return;
      setState(() {
        _wakeOn = s['on'] == true || s['wanted'] == true;
        _wakeStatus = (s['status'] as String?) ?? '';
      });
    } catch (_) {}
  }

  Future<void> _toggleWake(bool on) async {
    HapticFeedback.selectionClick();
    if (on) {
      final r = await Native.wakeStart();
      if (r == 'permission' && mounted) setState(() => _wakeStatus = 'Allow the microphone, then turn it on again');
    } else {
      await Native.wakeStop();
    }
    await Future<void>.delayed(const Duration(milliseconds: 600));
    await _refreshWake();
  }

  Future<void> _pickLook() async {
    final id = await hoolaOpenOld<String>(
        context, LookPickerScreen(initial: app.aLook, avatarName: app.aName, gender: app.aFemale ? 'f' : 'm'));
    if (id == null) return;
    final e = await app.saveAvatar(look: id);
    if (e != null && mounted) _say(context, e);
  }

  Future<void> _pickLanguage() async {
    final c = HoolaColors.of(context);
    final picked = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(padding: const EdgeInsets.fromLTRB(24, 20, 24, 8), child: Align(alignment: Alignment.centerLeft, child: Text('Language', style: HoolaType.heading(c)))),
          for (final e in languages.entries)
            ListTile(
              title: Text(e.value, style: HoolaType.body(c)),
              trailing: app.language == e.key ? Icon(Icons.check_rounded, color: c.accent) : null,
              onTap: () => Navigator.pop(ctx, e.key),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (picked == null) return;
    await app.saveSettings(lang: picked);
    if (mounted) setState(() {});
  }

  List<Map<String, dynamic>> get _voices =>
      [for (final v in ((app.avatar['voices'] as Map?)?[app.aFemale ? 'f' : 'm'] as List? ?? const [])) Map<String, dynamic>.from(v as Map)];

  Future<void> _pickVoice() async {
    final c = HoolaColors.of(context);
    final picked = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: c.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .7),
          child: ListView(shrinkWrap: true, children: [
            Padding(padding: const EdgeInsets.fromLTRB(24, 20, 24, 8), child: Text('${app.aName}\'s voice on a call', style: HoolaType.heading(c))),
            for (final v in _voices)
              ListTile(
                title: Text('${v['id']}', style: HoolaType.body(c)),
                subtitle: Text('${v['label'] ?? ''}', style: HoolaType.small(c)),
                trailing: app.voiceName == v['id'] ? Icon(Icons.check_rounded, color: c.accent) : null,
                onTap: () => Navigator.pop(ctx, '${v['id']}'),
              ),
          ]),
        ),
      ),
    );
    if (picked == null) return;
    await app.saveAvatar(voice: picked);
    if (mounted) setState(() {});
  }

  Future<void> _logout() async {
    if (!await _confirm(context, 'Log out?', 'You will need to sign in again on this phone. Your chats and work stay on Hoola.', 'Log out',
        danger: true)) {
      return;
    }
    await app.signOut();
    if (!mounted) return;
    Navigator.of(context).popUntil((r) => r.isFirst);
    widget.onReset();
  }

  Future<void> _removeAccount(Map<String, dynamic> conn) async {
    final provider = _s(conn['provider']);
    final name = provider == 'google' ? 'Google' : provider;
    if (!await _confirm(context, 'Remove $name?',
        'Hoola will stop reading Gmail, Calendar, Drive, Docs and Sheets for ${_s(conn['account'])} until you connect it again.', 'Remove',
        danger: true)) {
      return;
    }
    await app.disconnectProvider(provider);
  }

  String _s(Object? v) => v == null ? '' : '$v';

  String get _spendLine {
    final u = app.usage;
    if (u == null) return 'What chat, calls, websites and videos cost, and your monthly limit';
    final spent = ((u['spent_inr'] as num?) ?? 0).round();
    final limit = ((u['limit_inr'] as num?) ?? 0).round();
    return limit > 0 ? 'This month Rs $spent of Rs $limit' : 'This month Rs $spent';
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return ListenableBuilder(
      listenable: app,
      builder: (context, _) {
        final acc = app.account;
        final conns = [for (final x in ((acc?['connections'] as List?) ?? const [])) Map<String, dynamic>.from(x as Map)];
        final bgLine = !app.background
            ? 'Off: when the app is closed, notifications and phone tasks stop'
            : !app.backgroundRunning
                ? 'Starting…'
                : app.backgroundStatus == 'connected'
                    ? 'On · ${app.aName} is on duty'
                    : app.backgroundStatus.isEmpty
                        ? 'On'
                        : 'On · ${app.backgroundStatus}';
        return _Page(
          title: 'Settings',
          onRefresh: _refreshPhone,
          children: [
            // ---- who
            Padding(
              padding: const EdgeInsets.fromLTRB(HoolaSpace.gutter, HoolaSpace.s8, HoolaSpace.gutter, 0),
              child: Material(
                color: c.surface,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(HoolaRadius.card), side: BorderSide(color: c.line)),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => hoolaOpenOld(context, AvatarSetupScreen(app: app)),
                  child: Padding(
                    padding: const EdgeInsets.all(HoolaSpace.s16),
                    child: Row(children: [
                      AvatarFace(look: app.aLook, size: 52),
                      const SizedBox(width: HoolaSpace.s12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(app.aName, style: HoolaType.title(c)),
                          Text(
                              [
                                if (_s(acc?['email']).isNotEmpty) _s(acc?['email']),
                                'Name, ${app.aFemale ? 'female' : 'male'} voice, look',
                              ].join(' · '),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: HoolaType.small(c)),
                        ]),
                      ),
                      _chev(c),
                    ]),
                  ),
                ),
              ),
            ),

            const HoolaSection('You and Hoola'),
            HoolaGroup(children: [
              HoolaRow(
                title: 'Your AI team',
                sub: 'Every desk and tool ${app.aName} works at, and hiring AI employees',
                icon: Icons.groups_2_outlined,
                tint: c.accent,
                trailing: _chev(c),
                onTap: () => hoolaOpenNew(context, app, HoolaTeam(app: app)),
              ),
              HoolaRow(
                title: 'Your name, city and morning briefing',
                sub: 'Used for the weather and the daily briefing',
                icon: Icons.person_outline_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenNew(context, app, _ProfileEditor(app: app)),
              ),
              HoolaRow(
                title: '${app.aName}\'s look',
                sub: app.aFemale ? '100 looks from around the world' : '100 looks from around the world, or the original Santosh',
                icon: Icons.palette_outlined,
                trailing: _chev(c),
                onTap: _pickLook,
              ),
              HoolaRow(
                title: 'My rules',
                sub: 'How other Hoolas can reach you through ${app.aName}',
                icon: Icons.rule_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, AvatarSetupScreen(app: app, rulesOnly: true)),
              ),
              HoolaRow(
                title: 'Hoola Network',
                sub: 'Your Hoola ID, QR, connected people and talks with other Hoolas',
                icon: Icons.hub_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, HoolaNetScreen(app: app)),
              ),
            ]),

            const HoolaSection('Memory'),
            HoolaGroup(children: [
              HoolaRow(
                title: 'About me',
                sub: 'What ${app.aName} knows about you; read it, correct it, memory switches',
                icon: Icons.psychology_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, MemoryPageScreen(app: app)),
              ),
              HoolaRow(
                title: 'What ${app.aName} remembers',
                sub: 'Pin the small things to keep in mind, or remove what is wrong',
                icon: Icons.push_pin_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenNew(context, app, _FactsScreen(app: app)),
              ),
              HoolaRow(
                title: 'Learned tasks',
                sub: 'How ${app.aName} did long tasks: view, change, turn off',
                icon: Icons.auto_awesome_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, ProceduresScreen(app: app)),
              ),
              HoolaRow(
                title: 'What ${app.aName} has learned',
                sub: 'Things learned, what was shared, installed skills',
                icon: Icons.lightbulb_outline_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, HoolaLearnedScreen(app: app)),
              ),
            ]),

            const HoolaSection('Look and voice'),
            HoolaGroup(children: [
              _switchRow(context,
                  title: 'New design',
                  sub: 'Turn off to go back to the old look',
                  icon: Icons.auto_awesome_mosaic_outlined,
                  value: app.newLook,
                  onChanged: (v) => app.setNewLook(v)),
              Padding(
                padding: const EdgeInsets.fromLTRB(HoolaSpace.s12, 12, HoolaSpace.s12, 12),
                child: Row(children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: c.ink2.withOpacity(.12), borderRadius: BorderRadius.circular(HoolaRadius.tile)),
                    child: Icon(Icons.contrast_rounded, size: 20, color: c.ink2),
                  ),
                  const SizedBox(width: HoolaSpace.s12),
                  Expanded(child: Text('Appearance', style: HoolaType.body(c).copyWith(fontWeight: FontWeight.w500))),
                  SegmentedButton<String>(
                    showSelectedIcon: false,
                    style: SegmentedButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      selectedBackgroundColor: c.pill,
                      selectedForegroundColor: c.onPill,
                      foregroundColor: c.ink2,
                      side: BorderSide(color: c.line),
                    ),
                    segments: const [
                      ButtonSegment(value: 'system', label: Text('Auto')),
                      ButtonSegment(value: 'light', label: Text('Light')),
                      ButtonSegment(value: 'dark', label: Text('Dark')),
                    ],
                    selected: {app.appearance},
                    onSelectionChanged: (v) => app.setAppearance(v.first),
                  ),
                ]),
              ),
              HoolaRow(
                title: 'Language',
                sub: languages[app.language] ?? app.language,
                icon: Icons.translate_rounded,
                trailing: _chev(c),
                onTap: _pickLanguage,
              ),
              _switchRow(context,
                  title: 'Answer by voice when I speak',
                  sub: 'If you ask by voice, ${app.aName} answers by voice',
                  icon: Icons.volume_up_outlined,
                  value: app.speakReplies,
                  onChanged: (v) async {
                    await app.saveSettings(speak: v);
                    if (mounted) setState(() {});
                  }),
              if (app.realtimeVoice && _voices.isNotEmpty)
                HoolaRow(
                  title: '${app.aName}\'s voice on a call',
                  sub: app.voiceName.isEmpty ? 'Pick a voice' : app.voiceName,
                  icon: Icons.record_voice_over_outlined,
                  trailing: _chev(c),
                  onTap: _pickVoice,
                ),
              HoolaRow(
                title: 'Call voice engine',
                sub: 'Gemini voice or another voice, and this month\'s cost',
                icon: Icons.graphic_eq_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, VoiceEngineScreen(app: app)),
              ),
              HoolaRow(
                title: 'Voice ID',
                sub: '${app.aName} can tell who is speaking: you, Mom, Dad…',
                icon: Icons.fingerprint_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, VoiceIdScreen(app: app)),
              ),
              HoolaRow(
                title: 'How you speak',
                sub: 'Your language, speed, pauses, your words, what was misheard',
                icon: Icons.hearing_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, VoiceLearnedScreen(app: app)),
              ),
              HoolaRow(
                title: 'Call quality',
                sub: 'Numbers for every call and your listening test',
                icon: Icons.insights_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, CallQualityScreen(app: app)),
              ),
            ]),

            const HoolaSection('Phone and notifications'),
            HoolaGroup(children: [
              _switchRow(context,
                  title: 'Work in the background',
                  sub: bgLine,
                  icon: Icons.notifications_active_outlined,
                  value: app.background,
                  onChanged: (v) => app.setBackground(v)),
              if (app.background && app.batteryOptimized)
                HoolaRow(
                  title: 'Battery saver can stop ${app.aName}',
                  sub: 'Set Hoola to "Unrestricted"',
                  icon: Icons.battery_alert_rounded,
                  tint: c.warn,
                  trailing: _chev(c),
                  onTap: Native.askBattery,
                ),
              ValueListenableBuilder<Map<String, dynamic>?>(
                valueListenable: HoolaKeepAlive.last,
                builder: (context, r, _) {
                  final n = (r?['problems'] as List? ?? const []).length;
                  return HoolaRow(
                    title: 'Keep ${app.aName} from being stopped',
                    sub: r == null
                        ? 'Xiaomi, Oppo, Realme, Vivo, Samsung: fix the phone settings once'
                        : n == 0
                            ? 'All good'
                            : '$n thing${n == 1 ? '' : 's'} to fix',
                    icon: Icons.shield_moon_outlined,
                    tint: n > 0 ? c.warn : null,
                    trailing: _chev(c),
                    onTap: () => HoolaKeepAlive.open(context, app),
                  );
                },
              ),
              if (!app.exactAlarms)
                HoolaRow(
                  title: 'Let alarms ring on time',
                  sub: 'Allow "Alarms and reminders"',
                  icon: Icons.alarm_rounded,
                  tint: c.warn,
                  trailing: _chev(c),
                  onTap: () async {
                    await Native.askExactAlarms();
                    await Future<void>.delayed(const Duration(seconds: 2));
                    await app.refreshBackgroundInfo();
                  },
                ),
              if (app.background && !app.hasCalendar)
                HoolaRow(
                  title: 'Calendar permission',
                  sub: 'So ${app.aName} can save meetings straight into your calendar',
                  icon: Icons.event_outlined,
                  tint: c.warn,
                  trailing: _chev(c),
                  onTap: () async {
                    await Native.askCalendar();
                    await Future<void>.delayed(const Duration(seconds: 2));
                    await app.refreshBackgroundInfo();
                  },
                ),
              _switchRow(context,
                  title: '"Hey Santosh"',
                  sub: _wakeStatus.isNotEmpty
                      ? _wakeStatus
                      : 'Say it even with the phone locked. Your voice is recognised on the phone itself; payments still need it unlocked.',
                  icon: Icons.mic_none_rounded,
                  value: _wakeOn,
                  onChanged: _toggleWake),
              HoolaRow(
                title: '${app.aName} on the phone',
                sub: 'Assistant button, floating bubble, home-screen widget, app update',
                icon: Icons.phone_android_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, PhoneHoolaScreen(app: app)),
              ),
              HoolaRow(
                title: 'Talk from outside',
                sub: 'Talk to ${app.aName} from WhatsApp, Telegram, Slack, Teams - only you',
                icon: Icons.forum_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, BaharScreen(app: app)),
              ),
              HoolaRow(
                title: 'Hoola Screen',
                sub: 'Connect a mini screen or TV: ${app.aName}\'s work and cards show live there',
                icon: Icons.connected_tv_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, ScreenLinkScreen(app: app)),
              ),
            ]),

            const HoolaSection('Privacy and safety'),
            HoolaGroup(children: [
              HoolaRow(
                title: 'ID Locker',
                sub: 'Aadhaar, PAN, Voter ID kept locked; ${app.aName} fills them into forms',
                icon: Icons.badge_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, IdLockerScreen(app: app)),
              ),
              HoolaRow(
                title: 'Fingerprint approval',
                sub: 'Cards that move money can be approved only with your fingerprint',
                icon: Icons.fingerprint_rounded,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, ApproveKeyScreen(app: app)),
              ),
            ]),

            const HoolaSection('Account'),
            HoolaGroup(children: [
              HoolaRow(
                title: 'AI spend',
                sub: _spendLine,
                icon: Icons.account_balance_wallet_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, KharchaScreen(app: app)),
              ),
              for (final cn in conns)
                HoolaRow(
                  title: '${_s(cn['provider']) == 'google' ? 'Google' : _s(cn['provider'])} · ${_s(cn['account'])}',
                  sub: 'Gmail, Calendar, Drive, Docs, Sheets · press and hold to remove',
                  icon: Icons.check_circle_outline_rounded,
                  tint: c.ok,
                  onLongPress: () => _removeAccount(cn),
                  trailing: TextButton(
                    onPressed: () => _removeAccount(cn),
                    style: TextButton.styleFrom(foregroundColor: c.bad),
                    child: const Text('Remove'),
                  ),
                ),
              HoolaRow(
                title: 'Connect your systems',
                sub: 'ERP / CRM address and key; the key never goes into the chat',
                icon: Icons.lan_outlined,
                trailing: _chev(c),
                onTap: () => hoolaOpenOld(context, EnterpriseScreen(app: app)),
              ),
              HoolaRow(
                title: 'WhatsApp sending',
                sub: app.dryRun ? 'Test mode: nothing really goes out' : 'Live',
                icon: Icons.chat_outlined,
              ),
              HoolaRow(
                title: 'Log out',
                icon: Icons.logout_rounded,
                tint: c.bad,
                onTap: _logout,
              ),
            ]),
          ],
        );
      },
    );
  }
}

// ================================================================== PROFILE (name, city, briefing)
class _ProfileEditor extends StatefulWidget {
  const _ProfileEditor({required this.app});
  final Santosh app;
  @override
  State<_ProfileEditor> createState() => _ProfileEditorState();
}

class _ProfileEditorState extends State<_ProfileEditor> {
  final _name = TextEditingController();
  final _city = TextEditingController();
  String? _briefing;
  bool _loading = true, _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _name.dispose();
    _city.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final p = await widget.app.api!.profile();
      _name.text = p['name'] as String? ?? '';
      _city.text = p['city'] as String? ?? '';
      final b = p['briefing_time'] as String?;
      _briefing = (b == null || b == 'off' || b.isEmpty) ? null : b;
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _pickTime() async {
    final parts = (_briefing ?? '07:30').split(':');
    final t = await showTimePicker(context: context, initialTime: TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1])));
    if (t != null) setState(() => _briefing = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}');
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await widget.app.api!.saveProfile({
        'name': _name.text.trim(),
        'city': _city.text.trim(),
        'language': languages[widget.app.language],
        'briefing_time': _briefing ?? 'off',
        'conversation_id': widget.app.conversationId,
      });
      if (mounted) {
        _say(context, 'Saved');
        Navigator.of(context).maybePop();
      }
    } catch (e) {
      if (mounted) _say(context, 'Could not save: ${'$e'.replaceFirst('Exception: ', '')}');
    }
    if (mounted) setState(() => _saving = false);
  }

  InputDecoration _field(HoolaColors c, String label) => InputDecoration(
        labelText: label,
        labelStyle: HoolaType.small(c),
        filled: true,
        fillColor: c.sunk,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(HoolaRadius.tile), borderSide: BorderSide.none),
      );

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return _Page(
      title: 'Your details',
      sub: 'For the weather and the morning briefing',
      children: [
        if (_loading)
          Padding(padding: const EdgeInsets.only(top: 48), child: Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3)))
        else
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const SizedBox(height: HoolaSpace.s8),
              TextField(controller: _name, style: HoolaType.body(c), textCapitalization: TextCapitalization.words, decoration: _field(c, 'Your name')),
              const SizedBox(height: HoolaSpace.s12),
              TextField(controller: _city, style: HoolaType.body(c), textCapitalization: TextCapitalization.words, decoration: _field(c, 'City (for the weather)')),
              const SizedBox(height: HoolaSpace.s16),
              HoolaGroup(children: [
                _switchRow(context,
                    title: 'Morning briefing',
                    sub: _briefing == null ? 'Off' : 'Every day at $_briefing: weather, reminders, lists',
                    icon: Icons.wb_sunny_outlined,
                    value: _briefing != null,
                    onChanged: (on) => on ? _pickTime() : setState(() => _briefing = null)),
                if (_briefing != null)
                  HoolaRow(title: 'Change the time', icon: Icons.schedule_rounded, trailing: _chev(c), onTap: _pickTime),
              ]),
              const SizedBox(height: HoolaSpace.s24),
              FilledButton(
                onPressed: _saving ? null : _save,
                style: FilledButton.styleFrom(
                    backgroundColor: c.pill,
                    foregroundColor: c.onPill,
                    shape: const StadiumBorder(),
                    minimumSize: const Size.fromHeight(HoolaSpace.touchMain)),
                child: Text(_saving ? 'Saving…' : 'Save'),
              ),
            ]),
          ),
      ],
    );
  }
}

// ================================================================== WHAT HOOLA REMEMBERS
class _FactsScreen extends StatefulWidget {
  const _FactsScreen({required this.app});
  final Santosh app;
  @override
  State<_FactsScreen> createState() => _FactsScreenState();
}

class _FactsScreenState extends State<_FactsScreen> {
  List<Map<String, dynamic>>? _facts;
  String _err = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final f = await widget.app.api!.memory();
      if (mounted) setState(() {
        _facts = f;
        _err = '';
      });
    } catch (e) {
      if (mounted) setState(() {
        _facts ??= const [];
        _err = '$e'.replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _pin(Map<String, dynamic> f) async {
    try {
      await widget.app.api!.pinMemory((f['id'] as num).toInt(), f['pinned'] != true);
      await _load();
    } catch (e) {
      if (mounted) _say(context, '$e'.replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _forget(Map<String, dynamic> f) async {
    if (!await _confirm(context, 'Forget this?', '"${f['text']}"', 'Forget', danger: true)) return;
    try {
      await widget.app.api!.forget((f['id'] as num).toInt());
      await _load();
    } catch (e) {
      if (mounted) _say(context, '$e'.replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final f = _facts;
    final pinned = [for (final x in f ?? const <Map<String, dynamic>>[]) if (x['pinned'] == true) x];
    final rest = [for (final x in f ?? const <Map<String, dynamic>>[]) if (x['pinned'] != true) x];
    Widget row(Map<String, dynamic> x) => HoolaRow(
          title: '${x['text'] ?? ''}',
          sub: x['auto'] == true ? 'Remembered from your conversations' : '',
          icon: x['pinned'] == true ? Icons.push_pin_rounded : Icons.push_pin_outlined,
          tint: x['pinned'] == true ? c.accent : null,
          semantics: '${x['text']}${x['pinned'] == true ? ', pinned' : ''}',
          onTap: () => _pin(x),
          trailing: IconButton(
            tooltip: 'Forget',
            icon: Icon(Icons.delete_outline_rounded, color: c.ink3),
            onPressed: () => _forget(x),
          ),
        );
    return _Page(
      title: 'What ${widget.app.aName} remembers',
      sub: 'Tap a memory to pin it (always kept in mind). Other memories are found by meaning.',
      onRefresh: _load,
      children: [
        if (f == null)
          Padding(padding: const EdgeInsets.only(top: 48), child: Center(child: CircularProgressIndicator(strokeWidth: 2, color: c.ink3)))
        else if (f.isEmpty)
          HoolaEmpty(
              icon: Icons.psychology_outlined,
              title: _err.isEmpty ? 'Nothing remembered yet' : 'Memories could not be opened',
              sub: _err.isEmpty ? 'Say "Remember that Mom\'s birthday is 5 June".' : _err,
              onRetry: _err.isEmpty ? null : _load)
        else ...[
          if (pinned.isNotEmpty) ...[
            HoolaSection('Pinned', count: pinned.length, color: c.accent),
            HoolaGroup(children: [for (final x in pinned) row(x)]),
          ],
          if (rest.isNotEmpty) ...[
            HoolaSection('Remembered', count: rest.length),
            HoolaGroup(children: [for (final x in rest) row(x)]),
          ],
        ],
      ],
    );
  }
}

// ================================================================== YOUR AI TEAM
class HoolaTeam extends StatefulWidget {
  const HoolaTeam({super.key, required this.app});
  final Santosh app;
  @override
  State<HoolaTeam> createState() => _HoolaTeamState();
}

/// Pure: entries grouped in the fixed order, filtered by her search words (tested).
List<(String, List<HoolaTeamEntry>)> teamSections(List<HoolaTeamEntry> all, String query) {
  final words = query.toLowerCase().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).toList();
  bool hit(HoolaTeamEntry e) {
    final hay = '${e.title} ${e.sub} ${e.group}'.toLowerCase();
    return words.every(hay.contains);
  }

  return [
    for (final g in hoolaTeamGroups)
      if (all.any((e) => e.group == g && hit(e))) (g, [for (final e in all) if (e.group == g && hit(e)) e]),
  ];
}

class _HoolaTeamState extends State<HoolaTeam> {
  final _search = TextEditingController();
  String _q = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    final app = widget.app;
    final all = hoolaTeamEntries(app);
    final sections = teamSections(all, _q);
    final desks = all.where((e) => e.group != 'Tools and apps').length;
    return _Page(
      title: 'Your AI team',
      sub: '$desks desks and ${all.length - desks} tools',
      children: [
        HoolaSearch(controller: _search, hint: 'Search desks and tools', onChanged: (v) => setState(() => _q = v)),
        if (sections.isEmpty)
          const HoolaEmpty(icon: Icons.search_off_rounded, title: 'Nothing matches', sub: 'Try another word.')
        else
          for (final (g, entries) in sections) ...[
            HoolaSection(g, count: entries.length),
            HoolaGroup(children: [
              for (final e in entries)
                HoolaRow(
                  title: e.title,
                  sub: e.sub,
                  icon: e.icon,
                  tint: g == 'Hire and manage' ? c.accent : null,
                  trailing: _chev(c),
                  onTap: () => hoolaOpenOld(context, e.open(app)),
                ),
            ]),
          ],
      ],
    );
  }
}
