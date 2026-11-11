

## v0.799.0 DESK ROOM (built as 0.796; their 0.796-0.798 took the numbers, all kept) - a console desk for every live AI employee (owner: "LOT OF EMPLOYEE HAS BEEN DEVELOPED IN APP BUT IT IS NOT AVAILABLE IN WEB CONSOLE CHECK THIS FIRST THEN CATEGORY WISE DEVELOP AND DESIGN IT IN CONSOLE")

THE AUDIT (catalog `employee/hire.py` x console `employees.js` DESKS x `v2.html` views): 84 employees, 63 live. Every live one
in Games (10), Education (6), Enterprise (10), Business (seo / social / leads), cad, architect and film already had a console
desk. 31 did not, and their "Open desk" tap went to `<key>desk`, a view that does not exist - nothing happened:
Finance & Banking (paisa_sahayak, vitt_sahayak, risk_desk), Retail & E-commerce (dukaan_desk, retail_growth, retail_trust),
Health Insurance (bima_desk, bima_assist, bima_risk), Voice (kaan) and Construction & Real Estate (21 const_* seats). They were
never desks on the PHONE either: they are chat tools, and `employees_screen.dart` `_deskFor` falls back to the SEO desk for
them (not changed in this release - phone code compiles only on CI).

WHAT WAS BUILT
- `server/app/employee/deskroom.py`: `DEPTS` (four departments, their lanes; Construction in five lanes), `tools_of(key)` (the
  employee's own tool + its read-only `<key>_dekho` when it exists), `spec(tool)` = the tool's schema + its FULL description from
  its own module (the registry copy is cut to 1,200 chars for the model and lost later actions' inputs) read into one form per
  action: the fields that action names, choices from `a|b|c`, hints from `( )`, `[{a, b}]` = a row table with those columns,
  `[x]` = one per line, `{k: v}` = key: value lines, `file_id` = a file picker, and what the action gives back (`->`). 423
  actions, 409 read exactly; the 14 whose inputs the tool never lists say so and show every field folded. `run()` = the SAME
  `dispatch` the chat uses, `Ctx(actor="owner")`, the conversation = her Hoola updates chat (cards land there); hired only,
  paused refused, never another employee's tool, unknown fields dropped, a 9+ digit account / card number cut to its last
  four, 90 s cap, output scrubbed. Routes: GET /api/deskroom, GET /api/deskroom/{dept}, POST /api/deskroom/{key}/run.
- `server/app/static/console/deptdesk.js` (view `deptdesk`): crumb, department switcher, hero (serif title, line, a line drawing
  per department that traces itself once, employees / working / actions counts), employee rail by lane with status dots, the
  employee panel (pitch, Working / Paused / Not hired; not hired = what it does / never / needs + Hire on the careful trust
  level), Work / Records tabs, action chips with what each gives, Find an action when there are many, the form (number / text
  / choice / Default-Yes-No / row table with + Add row and Paste from Excel / lists / file), Run (Ctrl+Enter), and the result as
  tiles, tables, flag lists, letters in the reading serif and a notes callout, with Copy. Records opens today's desk (`day`) or
  the first list by itself. Ask in chat puts a line in the chat box, never sends it.
- `employees.js`: the 30 keys -> 'deptdesk' (opened on that employee), kaan -> 'flow' (Hoola Flow is Kaan's console page).
- `v2.css` block "v0.796 DESK ROOM": tokens only, light / dark / system, scale 12.5-32, weights <= 600, entrances once and
  BACKWARDS (the form and result animate only when they first appear, never on a repaint), only the running dot loops.
- Tests `test_v0799_desk_room.py` (8): every live employee opens a real view (the audit, held), the four departments = every
  live seat, forms from the full description (>95% exact), routes + hire gate + real runs (loan EMI 16,607.15, a store GRN read
  back as stock, paused refused, account masked), dispatch-as-owner pin, console wiring, crisp CSS, a real-browser walk in light
  1280 and dark 390. Pins moved in test_v0453 / test_v0456 (openView now passes the key for deptdesk too).

NOT VERIFIED: not opened on her live console yet; actions that make a card were not walked to the card; the phone still opens
the SEO desk for these 31 (a phone desk is the next step if she wants it).
