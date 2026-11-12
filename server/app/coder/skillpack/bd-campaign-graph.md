---
name: bd-campaign-graph
description: Campaign graph analytics - segments from engagement edges
when_to_use: campaign analytics, customer segments, who engaged, engagement graph, network analysis, best customers, clusters, influencers in my list
---
GOAL: the data around campaigns is already a GRAPH - customer and
campaign nodes, engagement edges. The classic metrics of
awesome-network-analysis run on that graph, and those metrics build
the segments the next campaign targets. Do not fight a spreadsheet -
solve it with the graph's metrics.

THE GRAPH: node = customer or campaign; edge = event - sent / read /
replied / clicked / bought. From the Bipartite shape (customers |
campaigns) comes the customer-customer projection: two customers who
engaged with the SAME campaign = an edge between them (co-engagement).

THE DATA (all existing doors):
- sheet_read / sheet_query: customers, orders, replies (the user's
  own data, in their own sheets).
- get_campaign_status: sent / delivered / read / replied per campaign.
- email_bulk_status: the results of an email campaign.
Take the rows first, then build the graph; keep only ids in the graph
code - PII such as phone / email does not go into the graph logic.

THE BUILD (pylab - there is NO networkx in the locked sandbox):
- adjacency as plain dicts, or scipy.sparse + scipy.csgraph
  (connected_components, shortest_path); the edge list from a pandas
  pivot.
- projection: M M^T (customers x customers co-engagement) or
  M^T M (campaigns x campaigns overlap). Graphs up to ~10k nodes are
  comfortable; if bigger, filter first (one segment / zone at a time).

THE METRICS (every number is quoted from pylab's printed output):
- degree: the most engaged customers - the warm audience.
- connected components / communities: natural segments - they come
  from the data, not from a guess.
- campaign overlap: how much the audiences of two campaigns overlap -
  lookalike sets; send the new campaign in that same shape.
- one-edge nodes: those who touched only one campaign - cold /
  churn-risk; the wake-up list.
- hub campaigns: the ones that connect the most people - repeat this
  shape.

THE ACT: the segment list goes into the user's sheet with sheet_append
(id + size + why included); targeting through create_campaign /
email_bulk - approval card FIRST (the money-shape law, as always). For
the one-edge group a soft wake-up message, not bulk.

THE LAWS: aggregate first, individual after - the metrics are
group-level; PII never leaves the user's tenant (not in shared output,
not in a report card, not in a doc).

NEVER: invented graph numbers; state a segment size without printed
output; bulk without the approval card; export the whole
customer-contact graph; call incomplete data a "graph" (with only sent
edges there is no engagement - get get_campaign_status first, then the
metrics).

ALSO ASKED AS (Hinglish asks this skill answers): campaign graph se customer
segments nikaalo, kaun se customer sabse zyada engage hue
