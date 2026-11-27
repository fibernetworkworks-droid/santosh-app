"""Sample query plans, schemas and benchmark output for the Database Engine Developer desk tests (made up, no real data)."""

PG_TEXT = """                                                         QUERY PLAN
------------------------------------------------------------------------------------------------------------------------------
 Sort  (cost=21458.12..21458.25 rows=50 width=40) (actual time=412.551..413.020 rows=4980 loops=1)
   Sort Key: o.created_at DESC
   Sort Method: external merge  Disk: 4096kB
   Buffers: shared hit=1520 read=6812, temp read=512 written=514
   ->  Hash Join  (cost=35.50..21456.71 rows=50 width=40) (actual time=0.512..398.110 rows=4980 loops=1)
         Hash Cond: (o.customer_id = c.id)
         ->  Seq Scan on orders o  (cost=0.00..21334.00 rows=50 width=32) (actual time=0.015..390.402 rows=4980 loops=1)
               Filter: ((status = 'paid'::text) AND (customer_id = 42))
               Rows Removed by Filter: 995020
               Buffers: shared hit=1500 read=6800
         ->  Hash  (cost=23.00..23.00 rows=1000 width=16) (actual time=0.401..0.402 rows=1000 loops=1)
               Buckets: 1024  Batches: 1  Memory Usage: 55kB
               ->  Seq Scan on customers c  (cost=0.00..23.00 rows=1000 width=16) (actual time=0.004..0.150 rows=1000 loops=1)
 Planning Time: 0.311 ms
 Execution Time: 414.208 ms
(15 rows)
"""

PG_LOOP = """Nested Loop  (cost=0.00..90000.00 rows=10 width=8) (actual time=0.05..2210.33 rows=3000 loops=1)
  ->  Seq Scan on line_items li  (cost=0.00..80.00 rows=3000 width=8) (actual time=0.01..0.90 rows=3000 loops=1)
  ->  Seq Scan on products p  (cost=0.00..30.00 rows=1 width=8) (actual time=0.30..0.73 rows=1 loops=3000)
        Filter: (id = li.product_id)
        Rows Removed by Filter: 1999
Execution Time: 2211.00 ms
"""

PG_JSON = """[{"Plan": {"Node Type": "Aggregate", "Plan Rows": 1, "Actual Rows": 1, "Actual Loops": 1, "Actual Total Time": 95.2, "Total Cost": 18000,
  "Plans": [{"Node Type": "Bitmap Heap Scan", "Relation Name": "events", "Alias": "e", "Plan Rows": 120, "Actual Rows": 250000, "Actual Loops": 1,
    "Actual Total Time": 90.1, "Total Cost": 17000, "Recheck Cond": "(kind = 'click'::text)", "Exact Heap Blocks": 2000, "Lossy Heap Blocks": 5400,
    "Plans": [{"Node Type": "Bitmap Index Scan", "Index Name": "events_kind_idx", "Plan Rows": 120, "Actual Rows": 250000, "Actual Loops": 1,
      "Actual Total Time": 12.0, "Total Cost": 400}]}]},
  "Planning Time": 0.2, "Execution Time": 95.6}]"""

MYSQL_TREE = """-> Sort: o.created_at DESC  (cost=101234 rows=99800) (actual time=880..881 rows=4980 loops=1)
    -> Filter: (o.customer_id = 42)  (cost=101234 rows=99800) (actual time=0.05..870 rows=4980 loops=1)
        -> Table scan on o  (cost=101234 rows=998000) (actual time=0.04..790 rows=1000000 loops=1)
"""

MYSQL_TABLE = """+----+-------------+-------+------------+------+---------------+------+---------+------+--------+----------+-----------------------------+
| id | select_type | table | partitions | type | possible_keys | key  | key_len | ref  | rows   | filtered | Extra                       |
+----+-------------+-------+------------+------+---------------+------+---------+------+--------+----------+-----------------------------+
|  1 | SIMPLE      | o     | NULL       | ALL  | idx_status    | NULL | NULL    | NULL | 998000 |    10.00 | Using where; Using filesort |
+----+-------------+-------+------------+------+---------------+------+---------+------+--------+----------+-----------------------------+
"""

SQLITE_EQP = """QUERY PLAN
|--SCAN o
|--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
`--USE TEMP B-TREE FOR ORDER BY
"""

SCHEMA = """CREATE TABLE customers (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  name TEXT,
  created_at TIMESTAMP DEFAULT now()
);
CREATE TABLE orders (
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT REFERENCES customers(id),
  status TEXT NOT NULL,
  total NUMERIC(12,2),
  created_at TIMESTAMP NOT NULL
);
CREATE TABLE audit_log (
  at TIMESTAMP,
  message TEXT
);
CREATE INDEX orders_status_idx ON orders (status);
CREATE INDEX orders_status_created_idx ON orders (status, created_at);
"""

QUERY = "SELECT * FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.customer_id = 42 AND o.status = 'paid' ORDER BY o.created_at DESC"

PGBENCH = """pgbench (16.2)
transaction type: <builtin: TPC-B (sort of)>
scaling factor: 50
query mode: simple
number of clients: 16
number of threads: 4
duration: 60 s
number of transactions actually processed: 512340
number of failed transactions: 0 (0.000%)
latency average = 1.874 ms
latency stddev = 0.912 ms
initial connection time = 21.330 ms
tps = 8538.912345 (without initial connection time)
"""

PGBENCH_SLOW = PGBENCH.replace("latency average = 1.874 ms", "latency average = 2.610 ms").replace("tps = 8538.912345", "tps = 6130.400000")

SYSBENCH = """SQL statistics:
    queries performed:
        read:                            1401540
        write:                           400440
        other:                           200220
        total:                           2002200
    transactions:                        100110 (1668.41 per sec.)
    queries:                             2002200 (33368.21 per sec.)
    ignored errors:                      0      (0.00 per sec.)

Latency (ms):
         min:                                    3.12
         avg:                                    9.58
         max:                                  141.30
         95th percentile:                       15.27
         sum:                               959010.11
"""
