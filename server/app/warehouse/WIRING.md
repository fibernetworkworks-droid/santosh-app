# WIRING for warehouse
summary: Godown Sahayak (warehouse manager: stock by bin with batches / expiry / serials, GRN with expiry / damage / PO-short checks and putaway suggestions, FEFO pick lists with a walking path from her list / Hoola Deals orders / Thok bills incl. waves and short picks, ABC + blind cycle counts with variance, every adjustment / write-off only on her tap, labels PDF + Excel; never moves money)
db: app.warehouse.models
router: app.warehouse.api            (make_router(require_key, current_tenant); all routes under /api/warehouse, key-protected; no public routes)
tools: app.agent.warehouse_tools     (WAREHOUSE_TOOLS / WAREHOUSE_LABELS / WAREHOUSE_HANDLERS) ; voice: yes (warehouse, warehouse_dekho)
employee: duty warehouse_work = [warehouse, warehouse_dekho, file_read] {label "Godown", say "bin-wise stock, maal aaya (GRN) aur kahan rakhna, pick list, cycle count (stock badlav / write-off aapki haan se)"} ; role warehouse_manager {label "Warehouse manager", duties [warehouse_work, records, reminders]} ; preset warehouse {label "Godown / warehouse", role warehouse_manager, rules ["Count ke baad stock badlav / write-off sirf owner ke card par tap se", "Expired maal pick mein kabhi nahi", "Paisa kabhi nahi"]} ; READ tools: [warehouse_dekho]
  - staff (staff:<id>) may do GRN, putaway, move, pick lists, pick_done, counts (plan / enter / close / recount), labels, export and RAISE write-off cards; owner-only in the tool: settings, opening, bins_many, fixing an ABC class. Customers (customer:*) are refused by both tools. No tool can approve an adjustment: only POST /api/warehouse/adjustments/{id}/decide (her app tap, hash checked, stale if stock moved since the card).
push: warehouse_adjust -> ("Godown: stock badlav aapki haan ka", "{say}")   (only when data.adjust.status == "waiting")
push: warehouse_day -> ("Aaj ka godown note", "{say}")
  (warehouse_grn, warehouse_pick, warehouse_count: no push, they update in place; publish only. pc_file events carry the PDFs / Excel.)
worker: app.warehouse.service.tick   (call every minute, e.g. `await asyncio.to_thread(warehouse.tick)`; morning note once a day within 3 h after her morning_time, only when there is something)
prompt: GODOWN: stock by bin, "maal aaya" (GRN; challan photo -> file_read first, then `warehouse action=grn` with lines incl. batch / expiry), "kahan rakhein" (putaway), "order nikalo" (`action=pick`: source list | deal | thok), "aaj kya ginein" (`action=count`, blind: never tell the counter the system quantity), toota / expire / gum maal (`action=writeoff`). Any stock change after a count or a write-off is ONLY a card for her tap: say "aapki haan ka card bheja hai", never that the stock changed. Prices come from her stock list; never invent quantities, expiry dates or prices; never move money.
persona: Godown mein ginti ke waqt system ki maatra kabhi mat batao (blind count); stock badlav / write-off ho to "aapki haan ka card bheja hai" kaho, khud kabhi mat badlo.
flutter: WarehouseScreen in lib/ui/warehouse_screen.dart ; profile tile title "<name> · Godown" subtitle "Bin-wise stock, maal aamad, pick list, ginti; badlav aapki haan se" icon Icons.warehouse_rounded ; cards: warehouse_adjust -> WarehouseAdjustCard (also in calls: yes; one card per data['adjust']['id'], updated in place) ; warehouse_grn -> WarehouseGrnCard (also in calls: no; key data['grn']['id']) ; warehouse_pick -> WarehousePickCard (also in calls: no; key data['pick']['id']) ; warehouse_count -> WarehouseCountCard (also in calls: no; key data['count']['id']) ; warehouse_day -> WarehouseDayCard (also in calls: no). All widgets take (app:, data:) (+ optional onDone) and use only `app.api!.call(...)`.
features: warehouse
env: none
requirements: none (reportlab QR / Code128 + openpyxl, already present)
android: none
neighbours: thok (wholesale bills / purchases: a GRN against a Thok purchase and a pick for a Thok bill do NOT change the shared stock count again), net/deal.py (Hoola Deals stock list = SKU master + prices; accepted orders -> pick lists; handover changes the shared count itself), logistics (shipments / LR / e-way bill after dispatch), courier (pickups / parcels), fleet, drivers, customs (import clearance before the GRN), niryat (export invoice / packing list), wapsi (returns desk: a return that comes back is a GRN here).
claude_md: |
  ## v0.1xx Godown Sahayak: Hoola as a warehouse manager ("Warehouse manager" on the Employee page)
  - Owner's spec: tracks stock by bin -> plans picking -> counts cycle stock -> waits for her Haan on STOCK ADJUSTMENTS AFTER A
    COUNT (write-offs); never moves money. Server `server/app/warehouse/{rules,models,service,api}.py`, tools `warehouse` /
    `warehouse_dekho` (`agent/warehouse_tools.py`, chat + calls), duty `warehouse_work`, role `warehouse_manager`, preset `warehouse`,
    API `/api/warehouse/*`, app Profile > Godown (`lib/ui/warehouse_screen.dart`: Aaj / Bin / Aamad / Pick / Ginti / Niyam,
    `WarehouseBinPage`), cards WarehouseAdjustCard (`warehouse_adjust`, also in calls), WarehouseGrnCard, WarehousePickCard,
    WarehouseCountCard, WarehouseDayCard. Tests `server/tests/test_logi_warehouse.py` (8).
  - Locations: bins `zone-aisle-rack-bin` (A-12, B-03-R2-4; many at once), kind pick / bulk / receiving / dispatch / quarantine /
    damage, capacity in units; walking order = zone, aisle, racks up in odd aisles and back down in even ones (serpentine), bin.
    RCV / QTN / DMG bins made by Hoola when needed.
  - SKUs (SKU-0001, her own pack barcode optional, track none / batch / serial) are LINKED to her Hoola Deals stock list
    (`hoola_stock` key, matched with `deal.match`); prices are read from the stock list and Thok's average cost (`thok_items.cost`),
    never stored here. Bin quantities live in `warehouse_lots` (SKU + bin + batch: expiry, mfg, serials, ok / hold).
    Shared count rule: GRN from a challan / PO / photo / sheet / list adds to `hoola_stock.qty`, a pick from her own list takes
    from it, an approved adjustment changes it; Thok purchases / bills and Hoola Deals handover already change it, so a GRN
    against a Thok purchase and picks for Thok bills / Deals orders leave it alone. `recon` shows bins vs the stock list (fixed
    only through a count + her card). Opening stock goes into bins without touching the shared count.
  - GRN (GRN-0001): lines from her words, a CSV / Excel sheet (item / qty / batch / expiry / mfg / serial columns by name), a
    challan photo read with file_read first, or a Thok purchase; checks: expiry passed -> quarantine bin (never pickable), near
    expiry, shelf life left < 30%, damaged qty -> damage bin (write-off only by card), duplicate serials refused, batch missing
    for batch SKUs, short / missing vs her PO (`expected`) -> a supplier message draft she sends, items not on her stock list
    named. Putaway suggestions: same SKU (same batch best) first, empty bins next, fast movers (ABC A or 8+ picks in 30 days)
    near dispatch, slow ones further back, never over a bin's free capacity, never quarantine / damage / dispatch; "Haan, aise
    rakho" applies them; moves refuse an over-full bin unless forced. Movement ledger (`warehouse_moves`) per bin: opening / grn /
    putaway / move / pick / adjust / writeoff with ref, who, reason, synced (CGST Rule 56 stock account shape).
  - Pick lists (PL-0001): her list, Hoola Deals seller orders in accepted / packing (service bookings skipped), Thok billed bills;
    several orders = a wave (lines merged per SKU with each order's share kept). Allocation FEFO (first expiry, then oldest
    received, pick bins before bulk), expired lots never and named, quantities held by other open lists not promised twice,
    serial SKUs need the scanned serials; tasks sorted in walking order; short lines said. Picker confirms per task (blank = all);
    less than planned = short pick + a blind spot count of that bin; duplicate list for an open order refused; walking-order PDF.
  - Cycle counts: ABC by yearly usage value (90-day picks x her cost, else stock-list price; picks count when no value), split 80 /
    95% (editable; her fixed class stays); schedule A 30 / B 90 / C 180 days (editable), `count_bins_per_day` (10). Counts
    (CC-0001: cycle / spot / recount) are BLIND: no system quantity in any view or sheet while open; the system figure is noted at
    the moment each line is entered; lines not counted are never assumed zero (unless she says so); found-new items become lines.
    Close -> variance (diff, rupee value from her costs, within tolerance A 1 unit / 0.5%, B 2 / 1%, C 5 / 3%), accuracy %, SKUs
    get last_counted; any difference = ONE adjustment card (ADJ-0001) listing lines outside tolerance as "pehle dobara gino";
    recount makes a new count and the waiting card goes stale.
  - Her tap: `decide_adjust(by_tap=True)` only from `POST /api/warehouse/adjustments/{id}/decide {yes, hash}`; the hash must match
    the card and the bins must still hold what the card was made from (picked / moved since = stale, nothing changes, count again).
    Approved -> lots set to the counted quantity, ledger with reason, shared stock count changed for linked SKUs; minus lines carry the
    GST note (Section 17(5)(h) ITC reversal for goods lost / stolen / destroyed / written off / gifted, her CA decides). Write-off
    (damaged / expired / lost / theft / sample) is the same card, raised by anyone, decided only by her.
  - Reports: stock by bin, SKU view (FEFO lots), ledger, near-expiry (her days, 30) + expired, slow (60 days) / dead (180 days) stock
    with value, recon; Excel exports (stock / ledger / abc / expiry / slow / variance); QR + Code128 labels PDF for bins
    ("HOOLA-BIN:A-12") and SKUs ("HOOLA-SKU:SKU-0001", her own pack barcode when set; our codes are internal, never a GS1 GTIN);
    scanned label text is understood by the tools. Morning note (`warehouse_day`) at her time when there is something.
  - Never: changing stock after a count / writing off without her tap, showing the system quantity to a counter, picking expired
    goods, storing prices, paying anyone, reversing ITC or filing anything.
  - Research (23 Oct 2026): CGST Rule 56(2) stock account (opening, receipts, supplies, goods lost / stolen / destroyed / written
    off / gifts / samples, closing) and Rule 56(16) records at every place of business (gstzen.in "Maintenance of accounts by
    registered persons | CGST Rule 56"); Section 36 keeps records 72 months; Section 17(5)(h) blocks ITC on goods lost, stolen,
    destroyed, written off, gifted or free samples (taxmann.com "ITC Reversal for Time-Expired Goods under the CGST Act", updated
    1 May 2024; CBIC Circular 72/46/2018-GST for expired drugs); ABC cycle counting (A top 10-20% of SKUs ~70-80% of value, counted
    most often, A discrepancies recounted; racklify.com "ABC Cycle Counting: Implementation Steps, KPIs and Best Practices");
    FSSAI storage / warehousing (Licensing and Registration Amendment Regulations notified 10 Mar 2026, new turnover thresholds from
    1 Apr 2026: registration up to Rs 1.5 crore, state licence to Rs 50 crore, central above; FIFO / FEFO, hygiene, temperature logs
    for cold storage; blogs.seyecs.com "FSSAI License for Food Storage and Warehousing Units: 2026 Guide"). Count days / tolerances
    are starter numbers she can change, not rules.
not_verified: Flutter screen + cards could not be compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/warehouse_screen.dart (Dart 3 record patterns in `for`). Labels / sheets PDFs were generated in tests but not printed or scanned on a real phone / scanner. Thok purchase -> GRN uses ThokPurchase.lines as stored by thok.service.purchase; a later change of that JSON shape breaks it. Hoola Deals pick source reads Deal.quote.lines (seller side) directly. The ITC / Rule 56 lines are plain-words guidance, not tax advice. No barcode scanner in the app: labels are read from a photo (qrread in chatfiles) or typed.
