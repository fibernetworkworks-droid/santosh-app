/// Hoola: the app. Each owner names their own AI avatar (default "Santosh").
const appName = 'Hoola';

const _fem = {
  'raha': 'rahi', 'gaya': 'gayi', 'karunga': 'karungi', 'dunga': 'dungi', 'lunga': 'lungi', 'jaunga': 'jaungi',
  'bataunga': 'bataungi', 'dekhunga': 'dekhungi', 'bhejunga': 'bhejungi', 'rakhunga': 'rakhungi', 'sakta': 'sakti',
  'chahta': 'chahti', 'karta': 'karti', 'deta': 'deti', 'leta': 'leti', 'dekhta': 'dekhti', 'padhta': 'padhti',
  'likhta': 'likhti', 'banata': 'banati', 'dhoondhta': 'dhoondhti', 'rakhta': 'rakhti', 'jaanta': 'jaanti',
  'samajhta': 'samajhti', 'bharta': 'bharti', 'sunta': 'sunti', 'bolta': 'bolti', 'chalata': 'chalati',
  'sambhalta': 'sambhalti', 'maangega': 'maangegi', 'karega': 'karegi', 'dega': 'degi', 'bhejega': 'bhejegi',
  'lega': 'legi', 'batayega': 'batayegi', 'maangta': 'maangti', 'jodta': 'jodti', 'kholta': 'kholti', 'bhejta': 'bhejti',
  'nikalta': 'nikalti',
};
final _femRe = RegExp(r'\b(' + (_fem.keys.toList()..sort((a, b) => b.length.compareTo(a.length))).join('|') + r')\b',
    caseSensitive: false);

/// Masculine Hindi self-references -> feminine (for a female avatar).
String genderedHi(String text) => text.replaceAllMapped(_femRe, (m) {
      final w = m.group(1)!;
      final out = _fem[w.toLowerCase()]!;
      return w[0] == w[0].toUpperCase() && w[0] != w[0].toLowerCase() ? out[0].toUpperCase() + out.substring(1) : out;
    });
