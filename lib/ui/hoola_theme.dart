// v0.860 R1 THE DESIGN SYSTEM (docs/HOOLA_APP_REDESIGN_PLAN.md, section 1): the Claude-style look in Hoola's own
// brand. ONE file holds every colour, size, corner, space and movement the redesigned screens use; a screen never
// writes a raw colour or a font size of its own (test/design_rules_test.dart keeps it that way).
//
//   Warm paper / warm charcoal neutrals, one accent (Hoola violet), serif for replies and big headlines (Literata),
//   one interface sans (Schibsted Grotesk), JetBrains Mono for code - the same three the web console uses.
//
// How a screen uses it:
//   final c = HoolaColors.of(context);          // colour roles, light or dark
//   Text('Work', style: HoolaType.heading(c));  // one of the fixed text styles
//   HoolaRadius.card, HoolaSpace.s16, HoolaMotion.page ...
//
// The old Night Glass (glass.dart) stays for the screens not moved yet (plan R2-R8); `HoolaTheme` wraps a
// redesigned screen so it follows Light / Dark / System (Santosh.appearance).
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

// ------------------------------------------------------------------------------------------------ fonts
/// Bundled in assets/fonts and declared in pubspec `fonts:` (no download, works offline).
class HoolaFont {
  static const sans = 'Schibsted Grotesk';
  static const serif = 'Literata';
  static const mono = 'JetBrains Mono';
}

// ------------------------------------------------------------------------------------------------ colours
/// Colour ROLES (never "blue" or "grey"): every text pair below reads at 4.5:1 or better (test checks it).
@immutable
class HoolaColors extends ThemeExtension<HoolaColors> {
  const HoolaColors({
    required this.dark,
    required this.bg,
    required this.surface,
    required this.raised,
    required this.sunk,
    required this.line,
    required this.lineStrong,
    required this.ink,
    required this.ink2,
    required this.ink3,
    required this.accent,
    required this.accentSoft,
    required this.onAccent,
    required this.pill,
    required this.onPill,
    required this.ok,
    required this.okSoft,
    required this.warn,
    required this.warnSoft,
    required this.bad,
    required this.badSoft,
    required this.info,
    required this.infoSoft,
    required this.code,
    required this.codeInk,
    required this.nav,
    required this.navOn,
    required this.scrim,
    required this.shadow,
  });

  final bool dark;
  final Color bg;          // the page
  final Color surface;     // cards, the composer, the tab bar, sheets
  final Color raised;      // menus, pop-overs (a step above surface)
  final Color sunk;        // her message bubble, tiles, chips, inputs
  final Color line;        // hairlines, card borders
  final Color lineStrong;  // outline buttons, search fields
  final Color ink;         // main text
  final Color ink2;        // secondary text, icons
  final Color ink3;        // captions, meta, placeholders
  final Color accent;      // Hoola violet: links, the one highlight
  final Color accentSoft;  // tinted tile behind an accent icon
  final Color onAccent;
  final Color pill;        // the primary button (near-black / near-white)
  final Color onPill;
  final Color ok, okSoft;
  final Color warn, warnSoft;   // "Needs you"
  final Color bad, badSoft;     // Delete, errors
  final Color info, infoSoft;
  final Color code;        // inline code chip / code block
  final Color codeInk;
  final Color nav;         // the floating tab bar
  final Color navOn;       // the selected tab's pill
  final Color scrim;       // behind a sheet
  final Color shadow;

  static const light = HoolaColors(
    dark: false,
    bg: Color(0xFFFAF9F6),
    surface: Color(0xFFFFFFFF),
    raised: Color(0xFFFFFFFF),
    sunk: Color(0xFFF1F0EC),
    line: Color(0xFFE5E3DD),
    lineStrong: Color(0xFFD3D1CA),
    ink: Color(0xFF1B1A17),
    ink2: Color(0xFF57554F),
    ink3: Color(0xFF6F6C65),
    accent: Color(0xFF5B45E0),
    accentSoft: Color(0xFFEEEBFD),
    onAccent: Color(0xFFFFFFFF),
    pill: Color(0xFF1B1A17),
    onPill: Color(0xFFFFFFFF),
    ok: Color(0xFF1F7A52),
    okSoft: Color(0xFFE3F2EA),
    warn: Color(0xFF8F5409),
    warnSoft: Color(0xFFFBF0DF),
    bad: Color(0xFFB8361F),
    badSoft: Color(0xFFFBE7E3),
    info: Color(0xFF2B5DB8),
    infoSoft: Color(0xFFE6EEFB),
    code: Color(0xFFF1F0EC),
    codeInk: Color(0xFF2B5DB8),
    nav: Color(0xFFFFFFFF),
    navOn: Color(0xFFECEBE6),
    scrim: Color(0x66141310),
    shadow: Color(0x40000000),
  );

  static const darkSet = HoolaColors(
    dark: true,
    bg: Color(0xFF1D1C1A),
    surface: Color(0xFF262523),
    raised: Color(0xFF2B2A27),
    sunk: Color(0xFF2F2E2B),
    line: Color(0xFF3A3936),
    lineStrong: Color(0xFF4A4945),
    ink: Color(0xFFF3F1EC),
    ink2: Color(0xFFBBB8B0),
    ink3: Color(0xFF9C9890),
    accent: Color(0xFF9C88FF),
    accentSoft: Color(0xFF2B2547),
    onAccent: Color(0xFF14102B),
    pill: Color(0xFFF3F1EC),
    onPill: Color(0xFF1B1A17),
    ok: Color(0xFF4CC38A),
    okSoft: Color(0xFF173226),
    warn: Color(0xFFE8B062),
    warnSoft: Color(0xFF3A2E1C),
    bad: Color(0xFFF07A6A),
    badSoft: Color(0xFF3D201B),
    info: Color(0xFF8AB4F8),
    infoSoft: Color(0xFF1C2A40),
    code: Color(0xFF2F2E2B),
    codeInk: Color(0xFF8AB4F8),
    nav: Color(0xFF2A2927),
    navOn: Color(0xFF3D3C38),
    scrim: Color(0x99000000),
    shadow: Color(0x80000000),
  );

  /// The colours of the nearest HoolaTheme (light when a screen is not wrapped yet).
  static HoolaColors of(BuildContext context) => Theme.of(context).extension<HoolaColors>() ?? light;

  /// Text pairs that must stay readable (checked by test/design_rules_test.dart): [foreground, background, name].
  List<(Color, Color, String)> get readablePairs => [
        (ink, bg, 'ink/bg'), (ink2, bg, 'ink2/bg'), (ink3, bg, 'ink3/bg'),
        (ink, surface, 'ink/surface'), (ink2, surface, 'ink2/surface'), (ink3, surface, 'ink3/surface'),
        (ink, sunk, 'ink/sunk'), (ink3, sunk, 'ink3/sunk'),
        (onPill, pill, 'onPill/pill'), (onAccent, accent, 'onAccent/accent'),
        (accent, bg, 'accent/bg'), (accent, surface, 'accent/surface'),
        (ok, surface, 'ok/surface'), (warn, warnSoft, 'warn/warnSoft'), (warn, surface, 'warn/surface'),
        (bad, surface, 'bad/surface'), (bad, badSoft, 'bad/badSoft'),
        (codeInk, code, 'codeInk/code'), (info, surface, 'info/surface'),
      ];

  @override
  HoolaColors copyWith() => this;

  @override
  HoolaColors lerp(ThemeExtension<HoolaColors>? other, double t) {
    if (other is! HoolaColors) return this;
    Color l(Color a, Color b) => Color.lerp(a, b, t)!;
    return HoolaColors(
      dark: t < .5 ? dark : other.dark,
      bg: l(bg, other.bg), surface: l(surface, other.surface), raised: l(raised, other.raised),
      sunk: l(sunk, other.sunk), line: l(line, other.line), lineStrong: l(lineStrong, other.lineStrong),
      ink: l(ink, other.ink), ink2: l(ink2, other.ink2), ink3: l(ink3, other.ink3),
      accent: l(accent, other.accent), accentSoft: l(accentSoft, other.accentSoft), onAccent: l(onAccent, other.onAccent),
      pill: l(pill, other.pill), onPill: l(onPill, other.onPill),
      ok: l(ok, other.ok), okSoft: l(okSoft, other.okSoft), warn: l(warn, other.warn), warnSoft: l(warnSoft, other.warnSoft),
      bad: l(bad, other.bad), badSoft: l(badSoft, other.badSoft), info: l(info, other.info), infoSoft: l(infoSoft, other.infoSoft),
      code: l(code, other.code), codeInk: l(codeInk, other.codeInk), nav: l(nav, other.nav), navOn: l(navOn, other.navOn),
      scrim: l(scrim, other.scrim), shadow: l(shadow, other.shadow),
    );
  }
}

/// WCAG contrast ratio of two opaque colours (1..21).
double hoolaContrast(Color a, Color b) {
  double lum(Color c) {
    double ch(double v) => v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
    return 0.2126 * ch(c.red / 255) + 0.7152 * ch(c.green / 255) + 0.0722 * ch(c.blue / 255);
  }

  final x = lum(a), y = lum(b);
  return (x > y ? x + 0.05 : y + 0.05) / (x > y ? y + 0.05 : x + 0.05);
}

// ------------------------------------------------------------------------------------------------ type
/// The ONE type scale (sp). Weights 400 / 500 / 600 / 700 only; nothing under 12.
class HoolaType {
  static TextStyle _sans(double size, FontWeight w, Color c, {double h = 1.35, double ls = 0}) =>
      TextStyle(fontFamily: HoolaFont.sans, fontSize: size, fontWeight: w, color: c, height: h, letterSpacing: ls);

  /// The home greeting, a drawer title: serif, large, quiet.
  static TextStyle hero(HoolaColors c) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: 32, fontWeight: FontWeight.w400, color: c.ink, height: 1.2, letterSpacing: -.3);
  /// Screen titles in a big header.
  static TextStyle display(HoolaColors c) => _sans(22, FontWeight.w700, c.ink, h: 1.25, ls: -.2);
  /// Top-bar titles, sheet titles.
  static TextStyle heading(HoolaColors c) => _sans(18, FontWeight.w600, c.ink, h: 1.3);
  /// Card / row titles.
  static TextStyle title(HoolaColors c) => _sans(16, FontWeight.w600, c.ink, h: 1.35);
  /// Reading text in the interface (her message, rows, forms).
  static TextStyle bodyLarge(HoolaColors c) => _sans(16, FontWeight.w400, c.ink, h: 1.45);
  static TextStyle body(HoolaColors c) => _sans(15, FontWeight.w400, c.ink, h: 1.45);
  /// Meta lines, secondary text.
  static TextStyle small(HoolaColors c) => _sans(13, FontWeight.w400, c.ink3, h: 1.4);
  /// Tab labels, badges, section labels (12 is the floor: Devanagari names on budget phones).
  static TextStyle label(HoolaColors c) => _sans(12, FontWeight.w500, c.ink2, h: 1.3);
  /// Button text.
  static TextStyle button(HoolaColors c, {Color? color}) => _sans(16, FontWeight.w600, color ?? c.ink, h: 1.2);
  /// Hoola's reply: the serif at reading size (Claude's reply sits in a serif too; ours is Literata, v0.253).
  static TextStyle reply(HoolaColors c) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: 17, fontWeight: FontWeight.w400, color: c.ink, height: 1.6);
  /// Headings INSIDE a reply (markdown # / ## / ###).
  static TextStyle replyH1(HoolaColors c) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: 22, fontWeight: FontWeight.w600, color: c.ink, height: 1.3);
  static TextStyle replyH2(HoolaColors c) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: 18, fontWeight: FontWeight.w600, color: c.ink, height: 1.35);
  static TextStyle replyH3(HoolaColors c) =>
      TextStyle(fontFamily: HoolaFont.serif, fontSize: 16, fontWeight: FontWeight.w600, color: c.ink, height: 1.4);
  /// Code (blocks 13, inline 14 to sit with 17 serif).
  static TextStyle code(HoolaColors c, {double size = 13}) =>
      TextStyle(fontFamily: HoolaFont.mono, fontSize: size, fontWeight: FontWeight.w400, color: c.codeInk, height: 1.5);

  /// The Material TextTheme the redesigned screens inherit (so a plain Text() is already right).
  static TextTheme textTheme(HoolaColors c) => TextTheme(
        displayLarge: hero(c),
        displayMedium: hero(c).copyWith(fontSize: 28),
        displaySmall: display(c),
        headlineLarge: display(c),
        headlineMedium: display(c),
        headlineSmall: heading(c),
        titleLarge: heading(c),
        titleMedium: title(c),
        titleSmall: _sans(15, FontWeight.w600, c.ink),
        bodyLarge: bodyLarge(c),
        bodyMedium: body(c),
        bodySmall: small(c),
        labelLarge: _sans(14, FontWeight.w600, c.ink),
        labelMedium: label(c),
        labelSmall: label(c),
      );
}

// ------------------------------------------------------------------------------------------------ shape + space
class HoolaRadius {
  static const double chip = 8, tile = 12, card = 16, cardLg = 18, dialog = 20, sheet = 28, pill = 999;
  static BorderRadius r(double v) => BorderRadius.circular(v);
}

class HoolaSpace {
  static const double s4 = 4, s8 = 8, s12 = 12, s16 = 16, s20 = 20, s24 = 24, s32 = 32;
  /// Minimum touch target (R9: 48 dp, Android's accessibility guideline - was 44, the iOS figure); main buttons 48.
  static const double touch = 48, touchMain = 48;
  /// Side gutter of a phone screen.
  static const double gutter = 16;
}

class HoolaShadow {
  /// Only floating things carry a shadow: the composer, the tab bar, menus, sheets.
  static List<BoxShadow> float(HoolaColors c) =>
      [BoxShadow(color: c.shadow.withOpacity(c.dark ? .5 : .18), blurRadius: 28, spreadRadius: -12, offset: const Offset(0, 8))];
}

// ------------------------------------------------------------------------------------------------ motion
/// Every movement in one place. When the phone asks for less motion (Accessibility > Remove animations), every
/// transition becomes a short fade and springs stop.
class HoolaMotion {
  static const page = Duration(milliseconds: 280);
  static const sheet = Duration(milliseconds: 320);
  static const menu = Duration(milliseconds: 160);
  static const fade = Duration(milliseconds: 200);
  static const reducedFade = Duration(milliseconds: 120);
  static const Curve ease = Cubic(.2, .7, .2, 1);          // the house curve (the console's --ease)
  static const Curve spring = Cubic(.34, 1.36, .64, 1);    // a small overshoot for cards / sheets entering
  static const Curve exit = Curves.easeInCubic;

  /// True when the phone asks for less motion.
  static bool reduced(BuildContext context) => MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  /// A duration that collapses under reduced motion.
  static Duration of(BuildContext context, Duration d) => reduced(context) ? reducedFade : d;
}

/// Push = the new screen slides in from the right with a soft fade; reduced motion = a plain fade.
class HoolaPageTransition extends PageTransitionsBuilder {
  const HoolaPageTransition();
  @override
  Widget buildTransitions<T>(PageRoute<T> route, BuildContext context, Animation<double> animation,
      Animation<double> secondaryAnimation, Widget child) {
    if (HoolaMotion.reduced(context)) return FadeTransition(opacity: animation, child: child);
    final inC = CurvedAnimation(parent: animation, curve: HoolaMotion.ease, reverseCurve: HoolaMotion.exit);
    final outC = CurvedAnimation(parent: secondaryAnimation, curve: HoolaMotion.ease);
    return SlideTransition(
      position: Tween(begin: const Offset(.18, 0), end: Offset.zero).animate(inC),
      child: FadeTransition(
        opacity: Tween<double>(begin: 0, end: 1).animate(inC),
        child: SlideTransition(
          position: Tween(begin: Offset.zero, end: const Offset(-.06, 0)).animate(outC),
          child: child,
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------------------------------------ ThemeData
/// The Material theme of a redesigned screen, built only from the tokens above.
ThemeData hoolaTheme(Brightness brightness) {
  final c = brightness == Brightness.dark ? HoolaColors.darkSet : HoolaColors.light;
  final scheme = ColorScheme(
    brightness: brightness,
    primary: c.pill,
    onPrimary: c.onPill,
    secondary: c.accent,
    onSecondary: c.onAccent,
    tertiary: c.accent,
    onTertiary: c.onAccent,
    error: c.bad,
    onError: c.dark ? c.onPill : c.onAccent,
    surface: c.surface,
    onSurface: c.ink,
    onSurfaceVariant: c.ink2,
    outline: c.lineStrong,
    outlineVariant: c.line,
    surfaceTint: Colors.transparent,
    shadow: c.shadow,
    scrim: c.scrim,
  );
  final text = HoolaType.textTheme(c);
  final pillShape = RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill));
  const buttonSize = Size(64, HoolaSpace.touchMain);
  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    fontFamily: HoolaFont.sans,
    textTheme: text,
    scaffoldBackgroundColor: c.bg,
    canvasColor: c.bg,
    dividerColor: c.line,
    splashFactory: InkRipple.splashFactory,
    highlightColor: Colors.transparent,
    visualDensity: VisualDensity.standard,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    extensions: [c],
    iconTheme: IconThemeData(color: c.ink2, size: 22),
    appBarTheme: AppBarTheme(
      backgroundColor: c.bg,
      surfaceTintColor: Colors.transparent,
      foregroundColor: c.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: true,
      titleTextStyle: HoolaType.heading(c),
      systemOverlayStyle: c.dark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
    ),
    dividerTheme: DividerThemeData(color: c.line, thickness: 1, space: 1),
    cardTheme: CardTheme(
      color: c.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.card), side: BorderSide(color: c.line)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: c.pill, foregroundColor: c.onPill, minimumSize: buttonSize, shape: pillShape,
        textStyle: HoolaType.button(c), padding: const EdgeInsets.symmetric(horizontal: 22),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: c.ink, minimumSize: buttonSize, shape: pillShape, side: BorderSide(color: c.lineStrong),
        textStyle: HoolaType.button(c).copyWith(fontWeight: FontWeight.w500), padding: const EdgeInsets.symmetric(horizontal: 20),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size(48, HoolaSpace.touch),
          textStyle: HoolaType.button(c).copyWith(fontSize: 15, fontWeight: FontWeight.w500), shape: pillShape),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(foregroundColor: c.ink, minimumSize: const Size(HoolaSpace.touch, HoolaSpace.touch)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: c.surface,
      hintStyle: HoolaType.bodyLarge(c).copyWith(color: c.ink3),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      border: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide(color: c.lineStrong)),
      enabledBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide(color: c.lineStrong)),
      focusedBorder: OutlineInputBorder(borderRadius: HoolaRadius.r(HoolaRadius.pill), borderSide: BorderSide(color: c.ink2, width: 1.4)),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: c.surface,
      selectedColor: c.navOn,
      side: BorderSide(color: c.line),
      shape: pillShape,
      labelStyle: HoolaType.body(c).copyWith(fontSize: 14),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
      showCheckmark: false,
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: c.surface,
      surfaceTintColor: Colors.transparent,
      modalBackgroundColor: c.surface,
      modalBarrierColor: c.scrim,
      showDragHandle: true,
      dragHandleColor: c.lineStrong,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(HoolaRadius.sheet))),
    ),
    dialogTheme: DialogTheme(
      backgroundColor: c.raised,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.dialog)),
      titleTextStyle: HoolaType.heading(c),
      contentTextStyle: HoolaType.body(c).copyWith(color: c.ink2),
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: c.raised,
      surfaceTintColor: Colors.transparent,
      elevation: 6,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.cardLg), side: BorderSide(color: c.line)),
      textStyle: HoolaType.bodyLarge(c),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: c.pill,
      contentTextStyle: HoolaType.body(c).copyWith(color: c.onPill),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: HoolaRadius.r(HoolaRadius.card)),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.onPill : c.surface),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.pill : c.lineStrong),
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: c.accent, linearTrackColor: c.line, circularTrackColor: c.line),
    listTileTheme: ListTileThemeData(
      iconColor: c.ink2,
      textColor: c.ink,
      titleTextStyle: HoolaType.bodyLarge(c),
      subtitleTextStyle: HoolaType.small(c),
      minVerticalPadding: 12,
      contentPadding: const EdgeInsets.symmetric(horizontal: HoolaSpace.gutter),
    ),
    pageTransitionsTheme: const PageTransitionsTheme(builders: {
      TargetPlatform.android: HoolaPageTransition(),
      TargetPlatform.iOS: HoolaPageTransition(),
    }),
  );
}

// ------------------------------------------------------------------------------------------------ the wrapper
/// Light / Dark / System, as she chose (Santosh.appearance: 'system' | 'light' | 'dark').
ThemeMode hoolaMode(String appearance) => switch (appearance) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };

/// Wraps a redesigned screen in the new theme while the rest of the app still wears Night Glass.
/// [appearance] = Santosh.appearance.
class HoolaTheme extends StatelessWidget {
  const HoolaTheme({super.key, required this.appearance, required this.child});
  final String appearance;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final mode = hoolaMode(appearance);
    final dark = mode == ThemeMode.dark ||
        (mode == ThemeMode.system && MediaQuery.platformBrightnessOf(context) == Brightness.dark);
    final theme = hoolaTheme(dark ? Brightness.dark : Brightness.light);
    return AnimatedTheme(
      data: theme,
      duration: HoolaMotion.of(context, HoolaMotion.fade),
      child: AnnotatedRegion<SystemUiOverlayStyle>(
        value: (dark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark)
            .copyWith(statusBarColor: Colors.transparent, systemNavigationBarColor: theme.scaffoldBackgroundColor),
        child: DefaultTextStyle(style: HoolaType.body(theme.extension<HoolaColors>()!), child: child),
      ),
    );
  }
}
