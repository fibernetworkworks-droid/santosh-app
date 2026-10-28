# Hoola progress and research

Adds a wall-clock elapsed-response display to the existing single-avatar progress subtitle. One interval updates one element; it is cleared on turn end, navigation and sign-out. This is elapsed frontend response time, not model compute time or a completion estimate. No fabricated percentages are shown.

The disclosure contains brief, allowlisted activity summaries from backend events, never raw reasoning, arguments, or private source contents. Search progress distinguishes public/knowledge sources, connected files and connected email. Distinct search tool-call IDs are counted once across running/done events. Completed turns retain a collapsed, neutral Activity record; failures are not labelled successful. Activity records are current-session UI, not a new durable history store; reopening a conversation still uses existing server history.

Research source choices: public web + attachments; connected apps + attachments; both; or attached files only. The request asks the existing agent to decompose the question, run distinct relevant queries, read and compare evidence, cite sources and state coverage gaps. Connected apps must already be authorized. No account connection or write action is requested. Actual search execution and availability remain with the existing backend and configured services; UI selection is not a new independent research engine or permission boundary.

Validation: 19 unit/contract tests; browser walkthrough verifies advancing elapsed time, one progress row, safe activity disclosure, search states and deduplicated counts, retained collapsed activity, all research source-scope submissions, and existing workspace/navigation responsive checks. Services are simulated; live research quality and connector availability have not been verified.

Web implementation only. No mobile, voice backend, model routing, PC or default-branch changes. Not deployed as part of implementation.
