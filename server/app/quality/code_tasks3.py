"""v0.378 MOBILE CARD - set 3 of the coding card (owner: "GO 4"): the languages Hoola's own app is written in.

KHATA (Dart 3, 16 files): the logic layer of a Flutter shop app - models, money, an immutable cart state, JSON parsing,
an offline outbox, formats, receipt, Hinglish labels; tests are plain Dart with the project's own harness (no packages,
so no pub.dev is needed). DUKAAN-KT (Kotlin 2 / JVM, 13 files): the domain layer of an Android shop app - config, data
classes, money, customers, orders, an offline outbox, receipt; tests are `fun main()` with the project's harness.
10 jobs (5 + 5) marked exactly like sets 1 and 2 (codecard.score): the code works, scope, project rules, tests that prove
the fix. Checks and tests run with the real Dart SDK / kotlinc (quality/sdk.py); a missing toolchain SKIPS its jobs."""
from __future__ import annotations

SET = 3
STEPS, MINUTES = 40, 8.0
PARALLEL = 2              # kotlinc is a 512 MB JVM: two at a time beside the live server

# ================================================================ KHATA (Dart)
D_AGENTS = """# Rules for contributors and coding agents (khata)
- Dart 3 with sound null safety. No packages: only dart:core, dart:convert, dart:math. Never dart:io in lib/.
- Imports are relative ('../lib/x.dart' from test/, 'x.dart' inside lib/), never package: imports.
- Money is int paise everywhere, never double.
- State is immutable: final fields; a change returns a NEW object. Never mutate a list you were given.
- Data from the server (JSON maps) is never trusted: no `as` casts or `!` on it - parse with a safe default.
- Tests: test/<name>_test.dart with a main() that uses check(name, () {...}), expectEq and finish() from
  test/harness.dart. Run one: dart test/<name>_test.dart
"""
D_PUBSPEC = "name: khata\ndescription: Shop app logic.\nversion: 1.0.0\nenvironment:\n  sdk: ^3.0.0\n"
D_MODELS = """class Item {
  final String id;
  final String name;
  final int price; // paise
  const Item(this.id, this.name, this.price);
}

class Line {
  final Item item;
  final int qty;
  const Line(this.item, this.qty);
  int get total => item.price * qty;
}

class Bill {
  final String id;
  final List<Line> lines;
  const Bill(this.id, this.lines);
  int get subtotal => lines.fold(0, (s, l) => s + l.total);
}
"""
D_MONEY = """/// rate percent of a paise amount, rounded half up.
int pct(int amount, int rate) => (amount * rate + 50) ~/ 100;

/// GST at 18%.
int gst(int amount) => pct(amount, 18);
"""
D_TOTALS = """import 'models.dart';
import 'money.dart';

/// What the customer pays for a bill.
int billTotal(Bill b) => b.subtotal + gst(b.subtotal);
"""
D_FORMAT = """/// paise -> 'Rs 1234.50' (no grouping)
String formatPlain(int paise) {
  final sign = paise < 0 ? '-' : '';
  final p = paise.abs();
  return '${sign}Rs ${p ~/ 100}.${(p % 100).toString().padLeft(2, '0')}';
}
"""
D_LABELS = """/// Hinglish labels shown on the receipt.
const labels = <String, String>{
  'subtotal': 'Jod',
  'gst': 'GST',
  'total': 'Kul',
};
"""
D_RECEIPT = """import 'format.dart';
import 'labels.dart';
import 'models.dart';
import 'money.dart';
import 'totals.dart';

/// The lines printed on a receipt.
List<String> receipt(Bill b) => [
      '${labels['subtotal']}: ${formatPlain(b.subtotal)}',
      '${labels['gst']}: ${formatPlain(gst(b.subtotal))}',
      '${labels['total']}: ${formatPlain(billTotal(b))}',
    ];
"""
D_CART = """import 'models.dart';

/// The cart as the screen sees it. Immutable: add / remove return a NEW CartState (the screen rebuilds on a new object).
class CartState {
  final List<Line> lines;
  const CartState([this.lines = const []]);

  CartState add(Item item, [int qty = 1]) {
    final next = <Line>[];
    var found = false;
    for (final l in lines) {
      if (l.item.id == item.id) {
        next.add(Line(l.item, l.qty + qty));
        found = true;
      } else {
        next.add(l);
      }
    }
    if (!found) next.add(Line(item, qty));
    return CartState(List.unmodifiable(next));
  }

  CartState remove(String id) => CartState(List.unmodifiable(lines.where((l) => l.item.id != id)));

  int get count => lines.fold(0, (s, l) => s + l.qty);
}
"""
D_CART_BUG = """import 'models.dart';

/// The cart as the screen sees it.
class CartState {
  final List<Line> lines;
  CartState([List<Line>? lines]) : lines = lines ?? [];

  CartState add(Item item, [int qty = 1]) {
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].item.id == item.id) {
        lines[i] = Line(lines[i].item, lines[i].qty + qty);
        return this;
      }
    }
    lines.add(Line(item, qty));
    return this;
  }

  CartState remove(String id) {
    lines.removeWhere((l) => l.item.id == id);
    return this;
  }

  int get count => lines.fold(0, (s, l) => s + l.qty);
}
"""
D_API = """import 'models.dart';

/// One item from the server's JSON map; missing or odd fields get safe defaults.
Item parseItem(Map<String, dynamic> j) {
  final id = j['id']?.toString() ?? '';
  final name = j['name']?.toString() ?? '';
  return Item(id, name, _paise(j['price']));
}

int _paise(Object? v) {
  if (v is int) return v;
  if (v is double) return v.round();
  if (v is String) return int.tryParse(v.trim()) ?? 0;
  return 0;
}

/// Every item in the server's list (entries that are not maps are skipped).
List<Item> parseItems(List<dynamic> list) => [
      for (final j in list)
        if (j is Map<String, dynamic>) parseItem(j)
    ];
"""
D_API_BUG = """import 'models.dart';

/// One item from the server's JSON map.
Item parseItem(Map<String, dynamic> j) {
  return Item(j['id'] as String, j['name'] as String, j['price'] as int);
}

/// Every item in the server's list.
List<Item> parseItems(List<dynamic> list) => [for (final j in list) parseItem(j as Map<String, dynamic>)];
"""
D_SYNC = """/// Orders made offline wait here. Each has a client id (cid), so a retry never makes a second order.
class Outbox {
  final List<Map<String, Object>> _pending = [];

  List<Map<String, Object>> get pending => List.unmodifiable(_pending);

  void enqueue(String cid, Map<String, Object> order) {
    if (_pending.any((o) => o['cid'] == cid)) return;
    _pending.add({...order, 'cid': cid});
  }

  void done(String cid) => _pending.removeWhere((o) => o['cid'] == cid);
}
"""
D_SYNC_BUG = """/// Orders made offline wait here. Each has a client id (cid).
class Outbox {
  final List<Map<String, Object>> _pending = [];

  List<Map<String, Object>> get pending => List.unmodifiable(_pending);

  void enqueue(String cid, Map<String, Object> order) {
    _pending.add({...order, 'cid': cid});
  }

  void done(String cid) => _pending.removeWhere((o) => o['cid'] == cid);
}
"""
D_HARNESS = """var _failed = 0;

/// Run one named check; a throw marks it failed.
void check(String name, void Function() body) {
  try {
    body();
    print('ok   $name');
  } catch (e) {
    _failed++;
    print('FAIL $name: $e');
  }
}

/// Throws when actual != want.
void expectEq(Object? actual, Object? want) {
  if (actual != want) throw 'expected $want, got $actual';
}

/// Call last: ends with an error when any check failed.
void finish() {
  if (_failed > 0) throw StateError('$_failed check(s) failed');
}
"""
D_TEST_MONEY = """import '../lib/money.dart';
import 'harness.dart';

void main() {
  check('gst', () => expectEq(gst(10000), 1800));
  check('half up', () => expectEq(pct(250, 18), 45));
  finish();
}
"""
D_TEST_CART = """import '../lib/cart_state.dart';
import '../lib/models.dart';
import 'harness.dart';

void main() {
  const tea = Item('tea', 'Tea', 18000);
  check('add merges', () => expectEq(const CartState().add(tea).add(tea, 2).count, 3));
  finish();
}
"""
KHATA = {
    "AGENTS.md": D_AGENTS, "README.md": "# khata\n\nShop app logic (Dart). Tests: `dart test/<name>_test.dart`.\n",
    "pubspec.yaml": D_PUBSPEC, "lib/models.dart": D_MODELS, "lib/money.dart": D_MONEY, "lib/totals.dart": D_TOTALS,
    "lib/format.dart": D_FORMAT, "lib/labels.dart": D_LABELS, "lib/receipt.dart": D_RECEIPT,
    "lib/cart_state.dart": D_CART, "lib/api.dart": D_API, "lib/sync.dart": D_SYNC, "test/harness.dart": D_HARNESS,
    "test/money_test.dart": D_TEST_MONEY, "test/cart_state_test.dart": D_TEST_CART,
}

# ================================================================ DUKAAN-KT (Kotlin)
K_AGENTS = """# Rules for contributors and coding agents (dukaan-kt)
- Kotlin 2 on the JVM, standard library only. Package hoola in src/, hoola.test in test/.
- Money is Long paise everywhere, never Double.
- Never use !! - handle null explicitly.
- Data classes are immutable (val); change one with copy().
- Settings (rates, fees, limits) live in src/Config.kt only.
- Renaming a public function: keep the old name for one release, marked
  @Deprecated("...", ReplaceWith("newName(...)")) and calling the new one.
- Tests: test/<Thing>Test.kt with fun main() using check(name) { ... }, expectEq and finish() from test/Harness.kt.
"""
K_CONFIG = """package hoola

object Config {
    const val GST_RATE = 18
    const val FREE_SHIPPING_ABOVE = 49900L
    const val SHIPPING_FLAT = 4900L
}
"""
K_MODELS = """package hoola

data class Product(val sku: String, val name: String, val price: Long)

data class Line(val product: Product, val qty: Int) {
    val total: Long get() = product.price * qty
}

data class Customer(val id: String, val name: String)

data class Order(
    val id: String,
    val customerId: String,
    val lines: List<Line>,
    val subtotal: Long,
    val gst: Long,
    val shipping: Long,
    val total: Long,
    val payment: String = "prepaid",
)
"""
K_MONEY = """package hoola

/** rate percent of a paise amount, rounded half up. */
fun pct(amount: Long, rate: Int): Long = (amount * rate + 50) / 100

/** GST at the shop rate. */
fun gst(amount: Long): Long = pct(amount, Config.GST_RATE)

/** 12345 -> "Rs 123.45" */
fun formatPaise(paise: Long): String {
    val sign = if (paise < 0) "-" else ""
    val p = kotlin.math.abs(paise)
    return "${sign}Rs ${p / 100}.${(p % 100).toString().padStart(2, '0')}"
}
"""
K_MONEY_BUG = K_MONEY.replace("fun pct(amount: Long, rate: Int): Long = (amount * rate + 50) / 100",
                              "fun pct(amount: Long, rate: Int): Long = amount * rate / 100")
K_CATALOG = """package hoola

val PRODUCTS: Map<String, Product> = mapOf(
    "TEA" to Product("TEA", "Assam tea", 18000),
    "MUG" to Product("MUG", "Steel mug", 24900),
    "KETTLE" to Product("KETTLE", "Kettle", 129900),
)
"""
K_CUSTOMERS = """package hoola

class CustomerBook(private val customers: Map<String, Customer>) {
    /** The customer, or null for an unknown / deleted id. */
    fun find(id: String): Customer? = customers[id]

    /** The name to show; an unknown customer shows as Guest. */
    fun displayName(id: String): String = find(id)?.name ?: "Guest"
}
"""
K_CUSTOMERS_BUG = """package hoola

class CustomerBook(private val customers: Map<String, Customer>) {
    fun find(id: String): Customer = customers[id]!!

    fun displayName(id: String): String = find(id).name
}
"""
K_ORDERS = """package hoola

/** Price an order: GST on the subtotal, flat shipping below the free-shipping limit. */
fun placeOrder(id: String, customerId: String, lines: List<Line>, payment: String = "prepaid"): Order {
    require(lines.isNotEmpty()) { "empty order" }
    require(payment == "prepaid" || payment == "cod") { "payment" }
    val subtotal = lines.sumOf { it.total }
    val tax = gst(subtotal)
    val shipping = if (subtotal >= Config.FREE_SHIPPING_ABOVE) 0L else Config.SHIPPING_FLAT
    return Order(id, customerId, lines, subtotal, tax, shipping, subtotal + tax + shipping, payment)
}
"""
K_OUTBOX = """package hoola

/** Orders made offline wait here and go to the server in the order they were made. A cid is never queued twice. */
class Outbox {
    private val queue = ArrayDeque<Pair<String, String>>()   // cid to payload

    fun add(cid: String, payload: String) {
        if (queue.none { it.first == cid }) queue.addLast(cid to payload)
    }

    /** The next order to send (the oldest), or null. */
    fun next(): Pair<String, String>? = queue.firstOrNull()

    fun sent(cid: String) {
        queue.removeAll { it.first == cid }
    }

    val size: Int get() = queue.size
}
"""
K_OUTBOX_BUG = K_OUTBOX.replace(
    "/** Orders made offline wait here and go to the server in the order they were made. A cid is never queued twice. */",
    "/** Orders made offline wait here. A cid is never queued twice. */").replace(
    "if (queue.none { it.first == cid }) queue.addLast(cid to payload)",
    "if (queue.none { it.first == cid }) queue.addFirst(cid to payload)").replace(
    "/** The next order to send (the oldest), or null. */", "/** The next order to send, or null. */")
K_RECEIPT = """package hoola

/** The lines printed on a receipt. */
fun receipt(o: Order): List<String> = listOf(
    "Subtotal: ${formatPaise(o.subtotal)}",
    "GST: ${formatPaise(o.gst)}",
    "Shipping: ${formatPaise(o.shipping)}",
    "Total: ${formatPaise(o.total)}",
)
"""
K_HARNESS = """package hoola.test

private var failed = 0

/** Run one named check; a throw marks it failed. */
fun check(name: String, body: () -> Unit) {
    try {
        body()
        println("ok   $name")
    } catch (e: Throwable) {
        failed++
        println("FAIL $name: $e")
    }
}

/** Throws when actual != want. */
fun expectEq(actual: Any?, want: Any?) {
    if (actual != want) throw AssertionError("expected $want, got $actual")
}

/** Call last: exits 1 when any check failed. */
fun finish() {
    if (failed > 0) kotlin.system.exitProcess(1)
}
"""
K_TEST_MONEY = """package hoola.test

import hoola.formatPaise
import hoola.gst

fun main() {
    check("gst") { expectEq(gst(10000), 1800L) }
    check("format") { expectEq(formatPaise(12345), "Rs 123.45") }
    finish()
}
"""
DUKAAN_KT = {
    "AGENTS.md": K_AGENTS, "README.md": "# dukaan-kt\n\nShop app domain layer (Kotlin). Tests: compile src + test with "
                                       "kotlinc, run each test's main.\n",
    "src/Config.kt": K_CONFIG, "src/Models.kt": K_MODELS, "src/Money.kt": K_MONEY, "src/Catalog.kt": K_CATALOG,
    "src/Customers.kt": K_CUSTOMERS, "src/Orders.kt": K_ORDERS, "src/Outbox.kt": K_OUTBOX, "src/Receipt.kt": K_RECEIPT,
    "test/Harness.kt": K_HARNESS, "test/MoneyTest.kt": K_TEST_MONEY,
}


def _dtest(name: str, imports: str, body: str) -> str:
    return f"{imports}import 'harness.dart';\n\nvoid main() {{\n{body}  finish();\n}}\n"


def _ktest(imports: str, body: str) -> str:
    return f"package hoola.test\n\n{imports}\nfun main() {{\n{body}    finish()\n}}\n"


TASKS: list[dict] = [
    # ------------------------------------------------------------ Dart
    {"id": "dart_fix_json_crash", "kind": "fix", "repo": "khata", "lang": "dart",
     "request": ("App crash ho jata hai: kuch items server se bina price ke aate hain, ya price \"250\" (text) aata hai. "
                 "Crash nahi hona chahiye: price na ho to 0, text number ho to woh number."),
     "files": {"lib/api.dart": D_API_BUG}, "must_test": True,
     "allow": r"^(lib/api\.dart|test/.+\.dart)$",
     "check": ("import 'lib/api.dart';\n\nvoid main() {\n"
               "  if (parseItem({'id': 'a', 'name': 'Tea', 'price': '250'}).price != 250) throw 'text price';\n"
               "  if (parseItem({'id': 'b', 'name': 'Mug'}).price != 0) throw 'missing price';\n"
               "  if (parseItem({'id': 'c', 'name': 'Pen', 'price': null}).price != 0) throw 'null price';\n"
               "  if (parseItem({'id': 'd', 'name': 'Cup', 'price': 120}).price != 120) throw 'int price';\n"
               "  if (parseItems([{'id': 'e', 'name': 'X', 'price': ' 75 '}]).single.price != 75) throw 'list';\n}\n"),
     "solution": {"lib/api.dart": D_API,
                  "test/api_test.dart": _dtest("api", "import '../lib/api.dart';\n",
                                               "  check('text price', () => expectEq(parseItem({'id': 'a', 'name': 'T', "
                                               "'price': '250'}).price, 250));\n")}},
    {"id": "dart_fix_mutated_state", "kind": "fix", "repo": "khata", "lang": "dart",
     "request": ("Cart mein item add karne par screen update nahi hoti (Flutter rebuild nahi hota), aur 'undo' ke liye "
                 "rakha purana cart bhi badal jaata hai."),
     "files": {"lib/cart_state.dart": D_CART_BUG, "test/cart_state_test.dart": D_TEST_CART.replace("const CartState()", "CartState()")},
     "must_test": True,
     "allow": r"^(lib/cart_state\.dart|test/.+\.dart)$",
     "check": ("import 'lib/cart_state.dart';\nimport 'lib/models.dart';\n\nvoid main() {\n  const tea = Item('tea', 'Tea', 18000);\n"
               "  final s0 = CartState();\n  final s1 = s0.add(tea);\n  final s2 = s1.add(tea, 2);\n"
               "  if (identical(s0, s1) || identical(s1, s2)) throw 'add must return a new state';\n"
               "  if (s0.count != 0 || s1.count != 1 || s2.count != 3) throw 'old states changed: ${s0.count} ${s1.count} ${s2.count}';\n"
               "  final s3 = s2.remove('tea');\n  if (s2.count != 3 || s3.count != 0 || identical(s2, s3)) throw 'remove';\n}\n"),
     "solution": {"lib/cart_state.dart": D_CART.replace("const CartState([this.lines = const []]);",
                                                        "const CartState([this.lines = const []]);"),
                  "test/cart_state_test.dart": _dtest("cart", "import '../lib/cart_state.dart';\nimport '../lib/models.dart';\n",
                                                      "  const tea = Item('tea', 'Tea', 18000);\n  final s0 = CartState();\n"
                                                      "  check('old state kept', () { s0.add(tea); expectEq(s0.count, 0); });\n")}},
    {"id": "dart_fix_duplicate_order", "kind": "fix", "repo": "khata", "lang": "dart",
     "request": "Network wapas aane par retry hota hai aur server par ek hi order do baar ban jaata hai.",
     "files": {"lib/sync.dart": D_SYNC_BUG}, "must_test": True,
     "allow": r"^(lib/sync\.dart|test/.+\.dart)$",
     "check": ("import 'lib/sync.dart';\n\nvoid main() {\n  final o = Outbox();\n  o.enqueue('c1', {'total': 100});\n"
               "  o.enqueue('c1', {'total': 100});\n  if (o.pending.length != 1) throw 'retry queued twice';\n"
               "  o.enqueue('c2', {'total': 50});\n  if (o.pending.length != 2) throw 'second order lost';\n"
               "  o.done('c1');\n  if (o.pending.length != 1 || o.pending.single['cid'] != 'c2') throw 'done';\n}\n"),
     "solution": {"lib/sync.dart": D_SYNC,
                  "test/sync_test.dart": _dtest("sync", "import '../lib/sync.dart';\n",
                                                "  check('no double', () { final o = Outbox(); o.enqueue('c', {}); "
                                                "o.enqueue('c', {}); expectEq(o.pending.length, 1); });\n")}},
    {"id": "dart_write_inr", "kind": "write", "repo": "khata", "lang": "dart",
     "request": ("lib/format.dart mein formatInr(paise) jodo, Indian grouping ke saath: 123456750 -> 'Rs 12,34,567.50', "
                 "5 -> 'Rs 0.05', -150000 -> '-Rs 1,500.00'."),
     "files": {}, "must_test": True,
     "allow": r"^(lib/format\.dart|test/.+\.dart|README\.md)$",
     "check": ("import 'lib/format.dart';\n\nvoid main() {\n  const want = {123456750: 'Rs 12,34,567.50', 5: 'Rs 0.05', "
               "-150000: '-Rs 1,500.00', 99900: 'Rs 999.00', 10000000: 'Rs 1,00,000.00', 0: 'Rs 0.00', "
               "100000000000: 'Rs 1,00,00,00,000.00'};\n"
               "  want.forEach((p, s) { if (formatInr(p) != s) throw '$p -> ${formatInr(p)}, want $s'; });\n}\n"),
     "solution": {"lib/format.dart": D_FORMAT + """
/// paise -> 'Rs 12,34,567.50' (Indian grouping: last 3 digits, then pairs)
String formatInr(int paise) {
  final sign = paise < 0 ? '-' : '';
  final p = paise.abs();
  final r = (p ~/ 100).toString();
  final last3 = r.length > 3 ? r.substring(r.length - 3) : r;
  var rest = r.length > 3 ? r.substring(0, r.length - 3) : '';
  final groups = <String>[];
  while (rest.length > 2) {
    groups.insert(0, rest.substring(rest.length - 2));
    rest = rest.substring(0, rest.length - 2);
  }
  if (rest.isNotEmpty) groups.insert(0, rest);
  final whole = [...groups, last3].join(',');
  return '${sign}Rs $whole.${(p % 100).toString().padLeft(2, '0')}';
}
""",
                  "test/format_test.dart": _dtest("format", "import '../lib/format.dart';\n",
                                                  "  check('grouping', () => expectEq(formatInr(123456750), 'Rs 12,34,567.50'));\n")}},
    {"id": "dart_feature_discount", "kind": "write", "repo": "khata", "lang": "dart",
     "request": ("Bill mein discount (paise) jodo: Bill('b', lines, discount: 1000) - default 0, purane calls waise hi chalein. "
                 "Total = (subtotal - discount) + us par GST. Receipt mein discount ki line 'Chhoot: Rs 10.00' jaisi aaye, "
                 "sirf jab discount > 0 ho."),
     "files": {}, "must_test": True,
     "allow": r"^(lib/(models|totals|receipt|labels)\.dart|test/.+\.dart)$",
     "check": ("import 'lib/models.dart';\nimport 'lib/receipt.dart';\nimport 'lib/totals.dart';\n\nvoid main() {\n"
               "  const lines = [Line(Item('t', 'Tea', 18000), 1)];\n  const plain = Bill('a', lines);\n"
               "  if (billTotal(plain) != 21240) throw 'old bills changed: ${billTotal(plain)}';\n"
               "  const off = Bill('b', lines, discount: 1000);\n"
               "  if (billTotal(off) != 20060) throw 'discount total ${billTotal(off)}';\n"
               "  final r = receipt(off);\n  if (!r.contains('Chhoot: Rs 10.00')) throw 'receipt: $r';\n"
               "  if (receipt(plain).any((l) => l.startsWith('Chhoot'))) throw 'Chhoot line on a bill without discount';\n}\n"),
     "solution": {
         "lib/models.dart": D_MODELS.replace("""  final List<Line> lines;
  const Bill(this.id, this.lines);""", """  final List<Line> lines;
  final int discount; // paise
  const Bill(this.id, this.lines, {this.discount = 0});"""),
         "lib/totals.dart": D_TOTALS.replace("int billTotal(Bill b) => b.subtotal + gst(b.subtotal);",
                                             "int billTotal(Bill b) => (b.subtotal - b.discount) + gst(b.subtotal - b.discount);"),
         "lib/labels.dart": D_LABELS.replace("  'gst': 'GST',", "  'discount': 'Chhoot',\n  'gst': 'GST',"),
         "lib/receipt.dart": D_RECEIPT.replace("""      '${labels['gst']}: ${formatPlain(gst(b.subtotal))}',""",
                                               """      if (b.discount > 0) '${labels['discount']}: ${formatPlain(b.discount)}',
      '${labels['gst']}: ${formatPlain(gst(b.subtotal - b.discount))}',"""),
         "test/bill_test.dart": _dtest("bill", "import '../lib/models.dart';\nimport '../lib/totals.dart';\n",
                                       "  check('discount', () => expectEq(billTotal(const Bill('b', [Line(Item('t', 'T', 18000), 1)], "
                                       "discount: 1000)), 20060));\n")}},
    # ------------------------------------------------------------ Kotlin
    {"id": "kt_fix_rounding", "kind": "fix", "repo": "dukaan-kt", "lang": "kotlin",
     "request": "999 paise par 5% ka hisaab 49 paise aata hai; half-up rounding se 50 hona chahiye.",
     "files": {"src/Money.kt": K_MONEY_BUG}, "must_test": True,
     "allow": r"^(src/Money\.kt|test/.+\.kt)$",
     "check": ("package hoola.check\n\nimport hoola.*\n\nfun main() {\n    require(pct(999, 5) == 50L) { \"999@5 = ${pct(999, 5)}\" }\n"
               "    require(pct(1000, 18) == 180L)\n    require(pct(1, 18) == 0L)\n    require(pct(250, 18) == 45L)\n"
               "    require(gst(10000) == 1800L)\n}\n"),
     "solution": {"src/Money.kt": K_MONEY,
                  "test/PctTest.kt": _ktest("import hoola.pct\n", "    check(\"half up\") { expectEq(pct(999, 5), 50L) }\n")}},
    {"id": "kt_fix_null_crash", "kind": "fix", "repo": "dukaan-kt", "lang": "kotlin",
     "request": ("Order screen crash hoti hai (NullPointerException) jab customer id kisi purane / deleted customer ki ho. "
                 "Aisa customer 'Guest' naam se dikhe."),
     "files": {"src/Customers.kt": K_CUSTOMERS_BUG}, "must_test": True,
     "allow": r"^(src/Customers\.kt|test/.+\.kt)$",
     "forbid": [[r"^src/", r"!!"]],
     "check": ("package hoola.check\n\nimport hoola.*\n\nfun main() {\n"
               "    val book = CustomerBook(mapOf(\"c1\" to Customer(\"c1\", \"Asha\")))\n"
               "    require(book.displayName(\"c1\") == \"Asha\")\n    require(book.displayName(\"gone\") == \"Guest\")\n"
               "    require(book.find(\"gone\") == null)\n}\n"),
     "solution": {"src/Customers.kt": K_CUSTOMERS,
                  "test/CustomersTest.kt": _ktest("import hoola.Customer\nimport hoola.CustomerBook\n",
                                                  "    check(\"guest\") { expectEq(CustomerBook(mapOf<String, Customer>())"
                                                  ".displayName(\"x\"), \"Guest\") }\n")}},
    {"id": "kt_fix_outbox_order", "kind": "fix", "repo": "dukaan-kt", "lang": "kotlin",
     "request": ("Offline bane orders server par ulte kram mein pahunchte hain (sabse naya pehle). Jis kram mein bane, usi "
                 "kram mein jaane chahiye."),
     "files": {"src/Outbox.kt": K_OUTBOX_BUG}, "must_test": True,
     "allow": r"^(src/Outbox\.kt|test/.+\.kt)$",
     "check": ("package hoola.check\n\nimport hoola.Outbox\n\nfun main() {\n    val o = Outbox()\n"
               "    o.add(\"a\", \"1\"); o.add(\"b\", \"2\"); o.add(\"c\", \"3\"); o.add(\"a\", \"1\")\n"
               "    require(o.size == 3) { \"size ${o.size}\" }\n    val seen = mutableListOf<String>()\n"
               "    while (true) { val n = o.next() ?: break; seen += n.first; o.sent(n.first) }\n"
               "    require(seen == listOf(\"a\", \"b\", \"c\")) { \"order $seen\" }\n"
               "    o.add(\"d\", \"4\"); o.add(\"e\", \"5\")\n    require(o.next()?.first == \"d\")\n}\n"),
     "solution": {"src/Outbox.kt": K_OUTBOX,
                  "test/OutboxTest.kt": _ktest("import hoola.Outbox\n",
                                               "    check(\"oldest first\") { val o = Outbox(); o.add(\"a\", \"1\"); "
                                               "o.add(\"b\", \"2\"); expectEq(o.next()?.first, \"a\") }\n")}},
    {"id": "kt_feature_cod", "kind": "write", "repo": "dukaan-kt", "lang": "kotlin",
     "request": ("Cash on delivery (payment = \"cod\") par Rs 40 COD fee jodo: Order mein alag codFee field (default 0), "
                 "total mein jude (COD fee par GST nahi), aur receipt mein 'COD fee: Rs 40.00' line sirf COD order par."),
     "files": {}, "must_test": True,
     "allow": r"^(src/(Config|Models|Orders|Receipt)\.kt|test/.+\.kt)$",
     "want": [[r"^src/Config\.kt$", r"COD_FEE\s*=\s*4000L?"]],
     "check": ("package hoola.check\n\nimport hoola.*\n\nfun main() {\n    val lines = listOf(Line(PRODUCTS.getValue(\"TEA\"), 1))\n"
               "    val p = placeOrder(\"o1\", \"c1\", lines)\n    require(p.codFee == 0L && p.total == 26140L) { \"prepaid $p\" }\n"
               "    val c = placeOrder(\"o2\", \"c1\", lines, \"cod\")\n"
               "    require(c.codFee == 4000L && c.total == 30140L && c.gst == 3240L) { \"cod $c\" }\n"
               "    require(\"COD fee: Rs 40.00\" in receipt(c)) { receipt(c).toString() }\n"
               "    require(receipt(p).none { it.startsWith(\"COD\") })\n}\n"),
     "solution": {
         "src/Config.kt": K_CONFIG.replace("    const val SHIPPING_FLAT = 4900L\n", "    const val SHIPPING_FLAT = 4900L\n    const val COD_FEE = 4000L\n"),
         "src/Models.kt": K_MODELS.replace('    val payment: String = "prepaid",\n', '    val payment: String = "prepaid",\n    val codFee: Long = 0L,\n'),
         "src/Orders.kt": K_ORDERS.replace(
             "    return Order(id, customerId, lines, subtotal, tax, shipping, subtotal + tax + shipping, payment)",
             "    val cod = if (payment == \"cod\") Config.COD_FEE else 0L\n"
             "    return Order(id, customerId, lines, subtotal, tax, shipping, subtotal + tax + shipping + cod, payment, cod)"),
         "src/Receipt.kt": K_RECEIPT.replace('''fun receipt(o: Order): List<String> = listOf(
    "Subtotal: ${formatPaise(o.subtotal)}",
    "GST: ${formatPaise(o.gst)}",
    "Shipping: ${formatPaise(o.shipping)}",
    "Total: ${formatPaise(o.total)}",
)''', '''fun receipt(o: Order): List<String> = buildList {
    add("Subtotal: ${formatPaise(o.subtotal)}")
    add("GST: ${formatPaise(o.gst)}")
    add("Shipping: ${formatPaise(o.shipping)}")
    if (o.codFee > 0) add("COD fee: ${formatPaise(o.codFee)}")
    add("Total: ${formatPaise(o.total)}")
}'''),
         "test/OrdersTest.kt": _ktest("import hoola.Line\nimport hoola.PRODUCTS\nimport hoola.placeOrder\n",
                                      "    check(\"cod\") { expectEq(placeOrder(\"o\", \"c\", listOf(Line(PRODUCTS.getValue(\"TEA\"), 1)), "
                                      "\"cod\").codFee, 4000L) }\n")}},
    {"id": "kt_rename_deprecated", "kind": "write", "repo": "dukaan-kt", "lang": "kotlin",
     "request": ("Money.kt ka formatPaise naam badal kar formatRupees karo aur har jagah naya naam use karo; purana naam ek "
                 "release tak chalta rahe (AGENTS.md)."),
     "files": {},
     "allow": r"^(src/(Money|Receipt)\.kt|test/.+\.kt|README\.md)$",
     "want": [[r"^src/Money\.kt$", r"@Deprecated\([^)]*ReplaceWith\("]],
     "check": ("package hoola.check\n\nimport hoola.*\nimport java.io.File\n\n@Suppress(\"DEPRECATION\")\nfun main() {\n"
               "    require(formatRupees(12345) == \"Rs 123.45\")\n    require(formatPaise(-5) == \"-Rs 0.05\") { \"old name must still work\" }\n"
               "    File(\"src\").listFiles()!!.filter { it.name != \"Money.kt\" }.forEach {\n"
               "        require(\"formatPaise\" !in it.readText()) { \"old name still used in ${it.name}\" }\n    }\n"
               "    val o = placeOrder(\"o\", \"c\", listOf(Line(PRODUCTS.getValue(\"MUG\"), 1)))\n"
               "    require(receipt(o).last() == \"Total: Rs 342.82\") { receipt(o).toString() }\n}\n"),
     "solution": {
         "src/Money.kt": K_MONEY.replace("/** 12345 -> \"Rs 123.45\" */\nfun formatPaise(paise: Long): String {",
                                         "/** 12345 -> \"Rs 123.45\" */\nfun formatRupees(paise: Long): String {")
                         + '\n@Deprecated("Renamed to formatRupees", ReplaceWith("formatRupees(paise)"))\n'
                           'fun formatPaise(paise: Long): String = formatRupees(paise)\n',
         "src/Receipt.kt": K_RECEIPT.replace("formatPaise", "formatRupees"),
         "test/MoneyTest.kt": K_TEST_MONEY.replace("formatPaise", "formatRupees")}},
]

for _t in TASKS:
    _t["base"] = KHATA if _t["repo"] == "khata" else DUKAAN_KT
