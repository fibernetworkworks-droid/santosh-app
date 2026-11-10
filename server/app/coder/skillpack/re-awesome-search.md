---
name: re-awesome-search
description: awesome-search over our index - the lists shelf
when_to_use: awesome list, curated list, best tools list, find a list of tools, resources list, github awesome
---
GOAL: awesomelists.top ka pattern - "the Related lists": ek curated
list ke niche doosri curated lists jutti hoti hain, aur search raw
web pe nahi, un curated indexes pe chalti hai. Is skill me Hoola ka
APNA awesome-search banta hai: ingested index (crawl/scrape lanes
se aaya hua) + zoo (app/zoo_catalog.json) + publicapis +
app/datasets.py = EK searchable shelf. Index TOOLS LANE me rehta
hai - ye skill usi design ka proof hai.

THE DOORS (sab Hoola operator ke asli tools):
1. INGEST (crawl lane): crawl_start ko curated lists ka seed do -
   public awesome repos, awesomelists.top jaise index-of-indexes.
   crawl_status se progress dekho, crawl_results se rows uthao.
   Ek-do pages ke liye scrape_site / scrape_many / scrape_page.
   Naya source dhoondna ho to pehle google_search / web_sources -
   "kaunsi list hai?" wahi pehla sawaal hai.
2. SHELF (jo pehle se bhara hai): zoo (app/zoo_catalog.json) ke
   catalogs, publicapis ke APIs, app/datasets.py ke datasets -
   teeno ingested index ke saath milkar EK index. API cover karna
   ho to api_find + api_docs; stored rows ke liye data_read /
   data_fetch.
3. RANK: awesomeness = maintenance + freshness + license. Stars
   sirf approximate signal hain, verdict nahi; paid placement
   KABHI nahi - rank sirf public criteria se, sab rows pe same
   formula.
4. SERVE: query pe TOP-3 print karo - har row me name + source +
   fetched-date. Poora list dump nahi; teen best, aur ek line
   "aur chahiye to bolo".
5. REFRESH: shelf bhi code jaise stale hota hai - period pe
   crawl_start dobara chalao, naya fetched-date likho, purani row
   replace karo; freshness rank ka seedha input hai, isliye refresh
   rank girne se pehle karo, baad me nahi.
6. skill_manage: jo ingest/rank/refresh recipe bani, usko skill ke
   roop me save karo - recipe khud shelf ka hissa ban jaati hai
   (Related lists ka recursive wala hissa).

THE LAWS: printed output hi evidence hai - shelf se jo serve kiya,
print kiye bina "mil gaya" bolna mana hai; private data tenant se
bahar kabhi nahi jaata (na ingest me, na host me, na results me);
fetched-date har row pe anivarya - bina date ki row stale hai aur
serve nahi hoti; index Hoola ke tools lane ke andar hi rahega.

NEVER: login-walled index ingest karna (public-only shelf); stale
row bina fetched-date serve karna; paid ya sponsored ranking -
rank = maintenance + freshness + license only; poora list dump -
top-3 se zyada nahi, baaki "bolo to doon"; index ko bahar host
karna (tenant ke andar hi); tenant ki private data index me
ghusana ya results me bahar le jaana; bina print kiye "result mil
gaya" claim karna.
