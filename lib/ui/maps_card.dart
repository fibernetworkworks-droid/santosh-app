/// v0.449 Phase 2 NAKSHA DIKHE - Google Maps results as a readable card on the phone.
///
/// Deliberately NO map. Google's terms permit Places content with no map at all (Service Specific Terms 14.1)
/// and FORBID it on a non-Google map (14.2, and ToS 3.2.3(e): "display or use Places content on a non-Google
/// Map"), so drawing these pins on free OpenStreetMap tiles would be a licence breach, not a saving. The
/// Google map is a paid option behind a setting, never the default. Attribution rides on the card because
/// ToS 3.2.2(b) requires it wherever this content is shown, with or without a map.
///
/// Nothing here is stored. The fields are read live each time she looks.
library;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../state.dart';
import 'glass.dart';

String _s(dynamic v) => v == null ? '' : '$v';
List<Map<String, dynamic>> _rows(dynamic v) => v is List
    ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList()
    : const <Map<String, dynamic>>[];

class MapsPlacesCard extends StatelessWidget {
  const MapsPlacesCard({super.key, required this.app, required this.data});
  final Santosh app;
  final Map<String, dynamic> data;

  static String _bits(Map<String, dynamic> p) {
    final open = p['open_now'];
    final status = _s(p['status']);
    return [
      _s(p['type']),
      if (p['distance_km'] != null) '${p['distance_km']} km',
      if (p['rating'] != null)
        '★ ${p['rating']}${p['reviews'] != null ? ' (${p['reviews']})' : ''}',
      if (open == true) 'Khula hai' else if (open == false) 'Off',
      if (status.isNotEmpty && status != 'OPERATIONAL') status.replaceAll('_', ' ').toLowerCase(),
    ].where((x) => x.isNotEmpty).join(' · ');
  }

  Future<void> _go(String url) async {
    final u = Uri.tryParse(url);
    if (u != null) await launchUrl(u, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final places = _rows(data['places']);
    if (places.isEmpty) return const SizedBox.shrink();
    final near = _s(data['near']);
    final cost = data['cost_inr'];
    return Glass(
      flat: true,
      margin: const EdgeInsets.only(left: 4, right: 10, bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.place_outlined, size: 17, color: C.accent),
          const SizedBox(width: 6),
          Expanded(child: Text(_s(data['title']).isEmpty ? 'Places' : _s(data['title']),
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
          Text('${places.length}', style: const TextStyle(color: C.faint, fontSize: 12.5)),
        ]),
        if (near.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 2),
              child: Text('Near $near', style: const TextStyle(color: C.faint, fontSize: 12.5))),
        for (final p in places) _Place(p: p, go: _go),
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            [_s(data['attribution']).isEmpty ? 'Google' : _s(data['attribution']),
             if (cost is num && cost > 0) '₹$cost' else if (cost is num) 'free'].join(' · '),
            style: const TextStyle(color: C.faint, fontSize: 11.5)),
        ),
      ]),
    );
  }
}

class _Place extends StatelessWidget {
  const _Place({required this.p, required this.go});
  final Map<String, dynamic> p;
  final Future<void> Function(String) go;

  @override
  Widget build(BuildContext context) {
    final bits = MapsPlacesCard._bits(p);
    final address = _s(p['address']);
    final hours = p['hours'] is List
        ? (p['hours'] as List).map(_s).where((x) => x.isNotEmpty).toList()
        : const <String>[];
    final phone = _s(p['phone']);
    final website = _s(p['website']);
    final link = _s(p['maps_link']);
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_s(p['name']), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5)),
        if (bits.isNotEmpty)
          Text(bits, style: const TextStyle(color: C.faint, fontSize: 12.5)),
        if (address.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 1),
              child: Text(address, style: const TextStyle(fontSize: 13, height: 1.3))),
        if (hours.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 1),
              child: Text(hours.join(' · '), style: const TextStyle(color: C.faint, fontSize: 12))),
        Wrap(spacing: 4, children: [
          if (phone.isNotEmpty)
            TextButton.icon(
              onPressed: () => go('tel:${phone.replaceAll(RegExp(r'[^\d+]'), '')}'),
              icon: const Icon(Icons.call_outlined, size: 15),
              label: Text(phone, style: const TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 6), minimumSize: const Size(0, 32)),
            ),
          if (website.isNotEmpty)
            TextButton.icon(
              onPressed: () => go(website),
              icon: const Icon(Icons.language_rounded, size: 15),
              label: const Text('Website', style: TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 6), minimumSize: const Size(0, 32)),
            ),
          if (link.isNotEmpty)
            TextButton.icon(
              onPressed: () => go(link),
              icon: const Icon(Icons.map_outlined, size: 15),
              label: const Text('Maps', style: TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 6), minimumSize: const Size(0, 32)),
            ),
        ]),
      ]),
    );
  }
}
