# Hoola Route vs Make - feature by feature (v0.999.254 MAKE PARITY)

Owner, 27 Nov 2026: "GET EXTREEM DEEP FIND ALL HOOLA ROUTE TOOL IS FUCTIONATING PERFECTLY SAME AS MAKE OR NOT --- WE
WANT ALL MAKE FUCTION IN IT. WITH END TO END FUCTIONING".

Sources: Make's own help centre, read 27 Nov 2026 - help.make.com/general-functions, math-functions,
text-and-binary-functions, date-and-time-functions, tokens-for-datetime-formatting, array-functions, variables,
error-handling, error-handlers, throw, scenario-settings, scenario-execution-cycles-and-phases, incomplete-executions,
apps.make.com/http (HTTP v4) and make.com/en/pricing. Module names of the built-in apps (Flow control, Tools, JSON,
Data store, Text parser, Webhooks, Archive) could not be fetched page by page (their app pages 404 for a reader); they
are taken from Make's blueprint format and its public module ids, and are marked "from blueprints".

Status: **Had** = in Route before this release; **Built** = added in v0.999.254, tested end to end
(`server/tests/test_v0999_254_make_parity.py`, incl. a browser walk); **Not** = not built, with the reason.

## Scenario building blocks

| Make | Route | Status |
|---|---|---|
| Modules: trigger / action / search | trigger + tool / web request / data steps | Had |
| Router, filters on each route, fallback route | router (ways with filters, "Anything else") | Had |
| Filters between modules (AND / OR groups, text / number / date / array / boolean operators) | filter step + full filter language | Had |
| Iterator | Repeat for each (loop) | Had |
| Repeater (repeats, start, step) | loop `repeat {times, start, step}` | **Built** |
| Array aggregator | loop `collect` -> `output.results` | **Built** |
| Text aggregator (row separator) | loop `collect` + `join` -> `output.text` | **Built** |
| Numeric aggregator (SUM AVG COUNT MIN MAX) | collect + Summarise (data aggregate) | **Built** (import makes both) |
| Table aggregator | `rows_to_table` (column / row separators) | **Built** |
| Aggregate to JSON / XML, Create CSV | `json_text`, `data_to_xml`, `rows_to_csv` | **Built** (XML new) |
| Group by in an aggregator | Summarise per field / merge by key | Had (partly: no group-by inside one step) |
| Sleep | wait | Had |
| Set variable / Get variable | set / var get | Had / **Built** |
| Set multiple variables / Get multiple variables | var `set_many` / `get_many` | **Built** |
| Increment function (reset never / per run) | var `increment` (never / run) | **Built** |
| Custom variables (organization / team, a module updates them) | Variables page + var `save` -> `{{env.NAME}}` | Had / **Built** |
| Switch (cases, else) | `switch()` function in a Set step (import does this) | **Built** |
| Compose a string | set with text | Had |
| Basic trigger / on-demand run with data | by hand + start data, route inputs | Had |
| Subscenarios: Call a scenario / Return output | sub-route step (result = last step + vars) | Had |
| Webhook response (status, body) | Answer the caller | Had |
| Throw (raise an error) | Stop the run as an error | Had |
| Notes on modules | sticky notes + step labels | Had |
| AI agents / AI modules | AI steps (agent, write, summarise, classify, extract, sentiment, answer, AI switch) | Had |

## Error handling

| Make | Route | Status |
|---|---|---|
| Directives Break (retries + interval), Resume (substitute values), Ignore / Skip, Commit, Rollback | on_error break / resume / ignore / commit / rollback | Had |
| Rollback really undoes ACID modules (data stores) | rollback takes back the run's data store writes | **Built** |
| Error handler route: modules before the directive, with the error's details | on_error `steps` + `{{error.message}}` / `{{error.step}}`; drawn under the step on the canvas | **Built** |
| Handler route with no directive = handled | no `do` + steps = ignore | **Built** |
| Incomplete executions (store, retry, resolve, delete) | Incomplete runs | Had |
| "Store incomplete executions" off -> rollback | setting `keep_incomplete: false` | **Built** |
| Automatic retry of incomplete executions | break retries | Had |

## Data stores (from blueprints: datastore:AddRecord, UpdateRecord, GetRecord, ExistRecord, DeleteRecord, DeleteRecords, SearchRecord, CountRecords)

| Make | Route | Status |
|---|---|---|
| Data store with a data structure (typed fields, required) | Data stores page, typed fields, required checked on every write | **Built** |
| Add / replace a record (overwrite on / off) | store `add` (+ `overwrite: false`) | **Built** |
| Update a record (insert if missing) | store `update` (+ `insert_missing`) | **Built** |
| Get / Check existence / Delete / Delete all | `get` / `exists` / `delete` / `delete_all` (needs `confirm`) | **Built** |
| Search records (filter, sort, limit up to 3,200) | `search` (same filter language, sort, limit 3,200) | **Built** |
| Count records | `count` | **Built** |
| Size limit per store | per store, default 1 MB, up to 10 MB; 64 KB a record | **Built** |
| Browse / edit / delete records, CSV import / export | Data stores page | **Built** |
| (not in Make as one module) atomic counter in a record | store `increment` | **Built** (extra) |

## HTTP (apps.make.com/http, v4)

| Make | Route | Status |
|---|---|---|
| Methods GET HEAD POST PUT PATCH DELETE OPTIONS | all seven | **Built** (was GET / POST) |
| Headers, query parameters | headers, query | **Built** (query new) |
| Body: JSON, multipart/form-data with files, x-www-form-urlencoded, Custom + content type | `body_type` json / multipart (+ files) / form / raw | **Built** |
| Authentication: API key, Basic, OAuth 2.0 (credentials, not headers) | saved Sign-ins (bearer, header key, basic, query key, OAuth2), only sent to their own site | Had |
| Parse response yes / no | `parse` (JSON and XML become data) | **Built** |
| Return error if the request fails / evaluate all states as errors | `fail_on_error` (default on) | **Built** |
| Timeout 1-300 s | `timeout` 1-300 | **Built** |
| Allow redirects (max 10) | `redirects` on / off, 10 hops, each checked against private addresses | **Built** |
| Share cookies with other HTTP modules | `share_cookies` (within the run) | **Built** |
| Request compressed content | `compressed` | **Built** |
| Pagination: offset, page, next link, cursor; items path; limit 1-10,000 | `pagination {type, items, param, size, start, next, limit}` (also the Link header) | **Built** |
| Download a file | action `download` -> a file id for later steps | **Built** |
| Resolve URL | action `resolve` | **Built** |
| Mutual TLS, CA certificate, proxy | - | **Not**: Hoola sends from its own server; client certificates and proxies would need key files on the server (no safe place for them yet) |

## Webhooks

| Make | Route | Status |
|---|---|---|
| Custom webhook (its own address) | webhook trigger (secret address) | Had |
| Webhook queue (calls wait, processed in turn; queue size) | calls faster than 1 per 6 s wait in the queue and run in order; `queue_max` default 667 (Make's number) | **Built** (were refused with 429) |
| Webhook data kept while the scenario is off | `queue_when_off` | **Built** |
| IP restrictions | `allow_ips` (addresses / ranges) | **Built** |
| Get request headers / HTTP method | `{{vars.request.headers}}`, `.method`, `.query` (sign-in headers never kept) | **Built** |
| Webhook response | Answer the caller | Had |
| Mailhook (an email address that starts a scenario) | app event "new email" on her inbox | **Not** as its own address: Hoola has no inbound mail domain per route yet; the import says so |

## Text parser, JSON, XML, CSV, Markdown, Archive

| Make | Route | Status |
|---|---|---|
| Match pattern (global, case sensitive, multiline, singleline, continue if no match) -> $1, $2 | `regex_match` (same options) | **Built** |
| Replace (pattern, $1 / $& in the new value) | `regex_replace` and `replace()` with `/re/g` | **Built** |
| HTML to text, get elements from HTML | `html_text`, `html_select` | Had |
| Parse JSON / Create JSON | `json_parse` / `json_text` | Had |
| Parse XML / Create XML | `xml_to_data` / `data_to_xml` | Had / **Built** |
| Parse CSV / Create CSV | `csv_to_rows` / `rows_to_csv` | Had |
| Markdown to HTML (and back) | `markdown_to_html` / `html_to_markdown` | **Built** |
| Archive: create / extract ZIP | file `zip` / `unzip` (50 MB, zip-bomb guard) | **Built** |
| Encryptor (encrypt / decrypt) | hashes, HMAC | Partly (no symmetric encryption step: keys would sit in a route) |

## Functions (help.make.com function pages) - all in `{{ }}` under Make's own names and snake_case

| Group | Make functions | Status |
|---|---|---|
| General | get, set, if, ifempty, switch, omit, pick, equal | **Built** (get / if-else had) |
| Math | abs, average, ceil, floor, formatNumber, max, min, median, parseNumber, round, stdevP, stdevS, sum, trunc | **Built** (rest had) |
| Text and binary | ascii, base64, capitalize, contains, decodeURL, encodeURL, escapeHTML, escapeJSON, escapeMarkdown, indexOf, length, lower, md5, replace (regex), replaceEmojiCharacters, sha1, sha256, sha512 (+ HMAC key), split, startcase, stripHTML, substring, toBinary, toString, trim, upper | **Built** |
| Date and time | formatDate / parseDate with Make's tokens (YYYY, MM, Do, dddd, HH, hh A, X, x, Z ...), addSeconds .. addYears, setSecond .. setYear, setDay (Sunday = 1 or a day name) | **Built** |
| Array | add, remove, arrayDiff, arrayIntersect, contains, deduplicate, distinct, first, last, flatten, join, keys, length, map, merge, reverse, shuffle, slice, sort (asc / desc / ci + key), toArray, toCollection | **Built** |
| Keywords | now, timestamp, uuid, random, pi, newline, space, tab, emptystring, emptyarray, erase | **Built** |
| System variables | execution id, scenario name ... | `{{run.id}}`, `{{run.route}}`, `{{run.started_at}}`, `{{run.attempt}}` - **Built** |
| Operators | + - * / %, = != < > <= >=, and / or | Had (`=` from Make is turned into `==` on import) |

## Scenario settings (help.make.com/scenario-settings)

| Make | Route | Status |
|---|---|---|
| Process data in order | `in_order`: one run at a time, oldest first, none while one waits in Incomplete runs | **Built** |
| Keep data confidential | `confidential`: the run log keeps the steps, not their data | **Built** |
| Store incomplete executions | `keep_incomplete` | **Built** |
| Commit after each module | `auto_commit` | **Built** |
| Errors before deactivation | `stop_after_errors` | Had |
| Discard data if storage is full | queue full -> 429 with the reason | Partly |
| Commit trigger last | - | **Not**: Route triggers are not transactional (a webhook / an app item is taken once) |
| Cycles per run | one run per call / per new item | **Not** the same: Route starts a run per item (Make runs cycles inside one execution) |
| Use updated variable values | runs always read the variables of the moment | Had (always "updated") |

## Scheduling

| Make | Route | Status |
|---|---|---|
| At regular intervals, Once, Every day, Days of the week, Days of the month, Specified dates, On demand | every_minutes / every_hours, once, at, days, monthdays, dates, by hand | Had |
| Start / end of the schedule | `start_date` / `end_date` | **Built** (start) / Had (end) |
| Immediately (instant triggers) | webhook, form, chat, error, route, MCP | Had |
| Minimum interval 1 minute (paid plans) | 15 minutes | **Not** changed: kept at 15 so one server is not flooded; app events can look every 5 minutes |
| Choose where to start (polling triggers: from now, all, since a date) | app events `start: now / all / since` | **Built** |

## Around the scenario

| Make | Route | Status |
|---|---|---|
| Scenario history, run details per module, replay a run | Runs, step-by-step log (inner steps too), Run again, debug a past run | Had |
| Operations counted per run | `summary.operations` on the run page | **Built** |
| Run this module only, Run once | Test step, Test route | Had |
| Versions, restore | Versions | Had |
| Blueprint export / import | route as a file; **Make blueprint import** (modules, filters, routers, iterators + aggregators, error handlers, data stores, HTTP, formulas `{{1.x}}` -> `{{steps.y.output.x}}`) | Had / **Built** |
| Make Grid (map of scenarios and what they touch) | Grid page: routes, starts, data stores, apps, web addresses, runs / on-error links | **Built** |
| Folders, tags, search | folders, tags, search | Had |
| Teams and roles | team members who may run a route | Had (partly) |
| Connections and keys | Connections page + Sign-ins | Had |
| Templates | Templates | Had |
| Make apps (2,500+ app modules) | Hoola tools + Composio apps (1,600+) + web request | Partly: apps come through Hoola's tools / Composio, not one module per app action |
| Custom apps SDK, Make Bridge, devices, Grid editing, scenario as an embedded product | - | **Not**: out of scope for a personal / business assistant |
| Custom JS functions (Enterprise) | Python code step (locked sandbox) | Had (Python, not JS) |

## What a Make user should know

- Route runs a step once with a whole list; Make runs each bundle through the modules. A Make iterator becomes a
  Repeat for each; a search that gives many bundles gives one list here. The import says so wherever it happens.
- Make arrays count from 1 (`{{1.items[1]}}`); Route counts from 0. The import changes `[1]` to `[0]`.
- Sign-ins never travel in a blueprint (Make leaves them out too): save them under Sign-ins.
- Data store records stay in Make: make the store here (or bring its CSV in) after the import.

## Not verified

On her server, with a real Make blueprint export of her own, with real app accounts.
