import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'glass.dart';

/// Santosh's in-app browser: websites open here without leaving the app.
class WebScreen extends StatefulWidget {
  const WebScreen({super.key, required this.url, this.title});
  final String url;
  final String? title;
  @override
  State<WebScreen> createState() => _WebScreenState();
}

class _WebScreenState extends State<WebScreen> {
  late final WebViewController _web;
  int _progress = 0;
  String _title = '';
  String _url = '';
  bool _canBack = false;
  bool _canForward = false;

  @override
  void initState() {
    super.initState();
    _url = widget.url;
    _title = widget.title ?? Uri.tryParse(widget.url)?.host ?? '';
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onProgress: (p) => mounted ? setState(() => _progress = p) : null,
        onPageFinished: (u) => _refresh(u),
        onNavigationRequest: (r) {
          final uri = Uri.tryParse(r.url);
          // phone numbers, UPI, WhatsApp, Play Store and app links go to the right app
          if (uri != null && uri.scheme != 'http' && uri.scheme != 'https' && uri.scheme != 'about' && uri.scheme != 'data') {
            launchUrl(uri, mode: LaunchMode.externalApplication).catchError((_) => false);
            return NavigationDecision.prevent;
          }
          return NavigationDecision.navigate;
        },
      ))
      ..loadRequest(Uri.parse(widget.url));
  }

  Future<void> _refresh(String u) async {
    final t = await _web.getTitle();
    final b = await _web.canGoBack();
    final f = await _web.canGoForward();
    if (!mounted) return;
    setState(() {
      _url = u;
      if (t != null && t.isNotEmpty) _title = t;
      _canBack = b;
      _canForward = f;
    });
  }

  @override
  Widget build(BuildContext context) => PopScope(
        canPop: !_canBack,
        onPopInvokedWithResult: (didPop, _) async {
          if (!didPop && await _web.canGoBack()) await _web.goBack();
        },
        child: Scaffold(
          backgroundColor: C.bgTop,
          body: SafeArea(
            child: Column(children: [
              Glass(
                margin: const EdgeInsets.fromLTRB(10, 6, 10, 6),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                radius: 20,
                child: Row(children: [
                  IconButton(tooltip: 'Band karo', icon: const Icon(Icons.close_rounded, color: C.chip), onPressed: () => Navigator.of(context).pop()),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      Text(_title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
                      Text(Uri.tryParse(_url)?.host ?? _url, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: C.muted, fontSize: 12)),
                    ]),
                  ),
                  IconButton(tooltip: 'Peeche', icon: Icon(Icons.arrow_back_rounded, color: _canBack ? C.chip : C.muted.withOpacity(.4)),
                      onPressed: _canBack ? () => _web.goBack() : null),
                  IconButton(tooltip: 'Aage', icon: Icon(Icons.arrow_forward_rounded, color: _canForward ? C.chip : C.muted.withOpacity(.4)),
                      onPressed: _canForward ? () => _web.goForward() : null),
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert_rounded, color: C.chip),
                    onSelected: (v) {
                      if (v == 'reload') _web.reload();
                      if (v == 'chrome') launchUrl(Uri.parse(_url), mode: LaunchMode.externalApplication);
                    },
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: 'reload', child: Text('Dobara load karo')),
                      PopupMenuItem(value: 'chrome', child: Text('Chrome mein kholo')),
                    ],
                  ),
                ]),
              ),
              if (_progress < 100) LinearProgressIndicator(value: _progress / 100, minHeight: 2.5, color: C.accent, backgroundColor: Colors.transparent),
              Expanded(child: WebViewWidget(controller: _web)),
            ]),
          ),
        ),
      );
}
