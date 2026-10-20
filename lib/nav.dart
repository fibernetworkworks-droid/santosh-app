import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'ui/tv_screen.dart';
import 'ui/web_screen.dart';

/// Lets non-UI code (phone actions) open screens.
final navKey = GlobalKey<NavigatorState>();

/// Open a link inside Santosh's own browser. Returns false if the app isn't on screen.
Future<bool> openInApp(String url, {String? title}) async {
  final nav = navKey.currentState;
  final uri = Uri.tryParse(url);
  if (nav == null || uri == null) return false;
  if (uri.scheme != 'http' && uri.scheme != 'https') {
    return launchUrl(uri, mode: LaunchMode.externalApplication);
  }
  nav.push(MaterialPageRoute(builder: (_) => WebScreen(url: url, title: title)));
  return true;
}

/// Open a Hoola TV channel in the player. Returns false if the app isn't on screen.
Future<bool> openTv(String channelId) async {
  final nav = navKey.currentState;
  if (nav == null || channelId.isEmpty) return false;
  nav.push(MaterialPageRoute(builder: (_) => TvPlayerScreen(channelId: channelId)));
  return true;
}

final _urlRe = RegExp(r'(https?://[^\s<>()\[\]"]+[^\s<>()\[\]".,;:!?])', caseSensitive: false);

/// Chat text with tappable links that open in Santosh's browser.
Widget linkText(String text, TextStyle style, {Color linkColor = const Color(0xFF6D3FE0)}) {
  final spans = <InlineSpan>[];
  var last = 0;
  for (final m in _urlRe.allMatches(text)) {
    if (m.start > last) spans.add(TextSpan(text: text.substring(last, m.start)));
    final url = m.group(0)!;
    final host = Uri.tryParse(url)?.host.replaceFirst('www.', '') ?? url;
    spans.add(TextSpan(
      text: host.isEmpty ? url : '🔗 $host',
      style: TextStyle(color: linkColor, fontWeight: FontWeight.w700, decoration: TextDecoration.underline, decorationColor: linkColor),
      recognizer: TapGestureRecognizer()..onTap = () => openInApp(url),
    ));
    last = m.end;
  }
  if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
  return SelectableText.rich(TextSpan(style: style, children: spans));
}
