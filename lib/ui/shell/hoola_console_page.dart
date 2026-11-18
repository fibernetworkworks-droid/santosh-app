// v0.898 TOOLS (owner: "REMOVE CONNECTOR INSTEAD PUT TOOLS ... SHOW ALL HOOLA FEATURES INTERACTIVE, VOCAL, FLOW, WEB
// DEVELOPMENT, APP DEVELOPMENT, CREATE, DESIGN, PROMPTING SAME AS CONSOLE PANEL SHOWN"): a page of the web console
// inside the app - the very same page the console shows, already signed in (her own key goes into the console's
// own storage on the server's own address, never anywhere else), with a slim bar: back, the title, reload, and
// open in the browser. Links to other sites leave for the browser; the page's own back history comes first.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../state.dart';
import '../hoola_theme.dart';
import 'hoola_settings.dart' show hoolaOpenNew;

/// Open [path] of the web console (e.g. '/console/web', '/console/?v=interactive') as an app page.
/// Tests replace [hoolaConsoleOpener] to see what would open.
Future<void> hoolaOpenConsole(BuildContext context, Santosh app, String path, String title) =>
    hoolaConsoleOpener(context, app, path, title);

Future<void> Function(BuildContext, Santosh, String, String) hoolaConsoleOpener =
    (context, app, path, title) => hoolaOpenNew(context, app, HoolaConsolePage(app: app, path: path, title: title));

class HoolaConsolePage extends StatefulWidget {
  const HoolaConsolePage({super.key, required this.app, required this.path, required this.title});
  final Santosh app;
  final String path, title;
  @override
  State<HoolaConsolePage> createState() => _HoolaConsolePageState();
}

class _HoolaConsolePageState extends State<HoolaConsolePage> {
  late final WebViewController _web;
  late final Uri _base, _target;
  bool _signed = false, _ready = false;
  String? _err;

  @override
  void initState() {
    super.initState();
    final server = widget.app.serverUrl.replaceAll(RegExp(r'/+$'), '');
    _base = Uri.parse(server);
    _target = Uri.parse('$server${widget.path}');
    _web = WebViewController(onPermissionRequest: (r) => r.grant())   // Hoola Flow and Vocal use the mic
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onPageFinished: (_) => _finished(),
        onWebResourceError: (e) {
          if ((e.isForMainFrame ?? true) && mounted) setState(() => _err = e.description);
        },
        onNavigationRequest: (r) {
          final u = Uri.tryParse(r.url);
          if (u == null || u.scheme == 'about' || u.scheme == 'data' || u.scheme == 'blob' || u.host == _base.host) {
            return NavigationDecision.navigate;
          }
          launchUrl(u, mode: LaunchMode.externalApplication);   // another site: the phone's browser
          return NavigationDecision.prevent;
        },
      ))
      // first a tiny page on the server's own address, so her key can go into the console's storage there
      ..loadRequest(Uri.parse('$server/healthz'));
  }

  Future<void> _finished() async {
    if (!_signed) {
      _signed = true;
      final key = jsonEncode(widget.app.apiKey);
      try {
        await _web.runJavaScript("try{localStorage.setItem('hoola.console.token',$key)}catch(e){}");
      } catch (_) {}
      await _web.loadRequest(_target);
      return;
    }
    if (mounted && !_ready) setState(() => _ready = true);
  }

  Future<void> _reload() async {
    setState(() => _err = null);
    await _web.reload();
  }

  @override
  Widget build(BuildContext context) {
    final c = HoolaColors.of(context);
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (_ready && await _web.canGoBack()) {
          await _web.goBack();
        } else if (context.mounted) {
          Navigator.of(context).pop();
        }
      },
      child: Scaffold(
        backgroundColor: c.bg,
        body: SafeArea(
          child: Column(children: [
            SizedBox(
              height: 52,
              child: Row(children: [
                IconButton(
                  tooltip: 'Back',
                  onPressed: () => Navigator.of(context).maybePop(),
                  icon: Icon(Icons.arrow_back_rounded, color: c.ink),
                ),
                Expanded(child: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: HoolaType.title(c))),
                IconButton(tooltip: 'Reload', onPressed: _reload, icon: Icon(Icons.refresh_rounded, color: c.ink2)),
                IconButton(
                  tooltip: 'Open in the browser',
                  onPressed: () => launchUrl(_target, mode: LaunchMode.externalApplication),
                  icon: Icon(Icons.open_in_new_rounded, color: c.ink2),
                ),
                const SizedBox(width: 4),
              ]),
            ),
            Divider(height: 1, color: c.line),
            Expanded(
              child: Stack(children: [
                Positioned.fill(child: WebViewWidget(controller: _web)),
                if (!_ready || _err != null)
                  Positioned.fill(
                    child: ColoredBox(
                      color: c.bg,
                      child: Center(
                        child: _err != null
                            ? Padding(
                                padding: const EdgeInsets.all(24),
                                child: Column(mainAxisSize: MainAxisSize.min, children: [
                                  Icon(Icons.cloud_off_rounded, color: c.ink3, size: 32),
                                  const SizedBox(height: 10),
                                  Text('${widget.title} did not open', style: HoolaType.title(c)),
                                  const SizedBox(height: 4),
                                  Text(_err!, textAlign: TextAlign.center, style: HoolaType.small(c)),
                                  const SizedBox(height: 14),
                                  FilledButton(onPressed: _reload, child: const Text('Try again')),
                                ]),
                              )
                            : Column(mainAxisSize: MainAxisSize.min, children: [
                                SizedBox(width: 26, height: 26, child: CircularProgressIndicator(strokeWidth: 2.4, color: c.accent)),
                                const SizedBox(height: 12),
                                Text('Opening ${widget.title}…', style: HoolaType.small(c)),
                              ]),
                      ),
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
