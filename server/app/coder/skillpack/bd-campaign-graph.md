---
name: bd-campaign-graph
description: Campaign graph analytics - segments from engagement edges
when_to_use: campaign analytics, customer segments, who engaged, engagement graph, network analysis, best customers, clusters, influencers in my list
---
GOAL: campaigns ke aas-paas ka data pehle se hi ek GRAPH hai - customer
aur campaign nodes, engagement edges. Awesome-network-analysis ke
classic metrics usi graph par chalte hain, aur wahi metrics segments
banate hain jo agla campaign target karta hai. Spreadsheet se jhagda
nahi - graph ke metrics se sulajh.

THE GRAPH: node = customer ya campaign; edge = event - sent / read /
replied / clicked / bought. Bipartite shape (customers | campaigns)
se customer-customer projection banti hai: do customers ne SAME
campaign engage kiya = unke beech edge (co-engagement).

THE DATA (sab existing doors):
- sheet_read / sheet_query: customers, orders, replies (uska apna
  data, uske apne sheets).
- get_campaign_status: sent / delivered / read / replied per campaign.
- email_bulk_status: email campaign ke results.
Pehle rows lo, phir graph banao; graph code mein sirf ids rakho -
phone/email jaise PII graph logic mein nahi ghusate.

THE BUILD (pylab - locked sandbox mein networkx NAHI hai):
- adjacency plain dicts ya scipy.sparse + scipy.csgraph
  (connected_components, shortest_path); pandas pivot se edge list.
- projection: M M^T (customers x customers co-engagement) ya
  M^T M (campaigns x campaigns overlap). Graphs ~10k nodes tak
  aaram se; usse bade ho to pehle filter (ek segment/zone at a time).

THE METRICS (har number pylab ke printed output se quote hota hai):
- degree: sabse engaged customers - warm audience.
- connected components / communities: natural segments - data se
  bante hain, guess se nahi.
- campaign overlap: do campaigns ki audiences kitni milti hai -
  lookalike sets; naya campaign usi shape mein bhejo.
- one-edge nodes: sirf ek campaign chhoone wale - cold / churn-risk;
  wake-up list.
- hub campaigns: jo sabse zyada log jodte hain - isi shape repeat.

THE ACT: segment list sheet_append se uski sheet mein (id + size +
kyun included); targeting create_campaign / email_bulk se - approval
card PEHLE (the money-shape law, wahi purana). One-edge group ke liye
soft wake-up message, bulk nahi.

THE LAWS: aggregate pehle, individual baad mein - metrics group-level
hain; PII uske tenant se bahar nahi jata (na shared output, na report
card, na doc).

NEVER: invented graph numbers; printed output ke bina segment size
bolna; approval card ke bina bulk; poora customer-contact graph export
karna; adhoore data ko "graph" bolna (sirf sent edges hain to
engagement nahi hai - pehle get_campaign_status lo, phir metrics).
