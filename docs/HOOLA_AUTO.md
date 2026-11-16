# HOOLA AUTO - a whole client project, run by specialist agents (v0.947)

Owner's ask: "IN APP AND WEB CONSOLE THERE WILL BE A SEPERATE SECTION ... HOOLA AUTO IN CODE SECTION -- USER WILL ATTACH ALL
ENVIRONMENT TO IT -- THEN INTAKE IS TAKEN FROM CLIENT -- ONCE THIS APPROVED --- ALL SPECIAL AGENT WILL START WORK IN
PARALLEL ... EVERY AGENT WILL HAVE ITS OWN WORKING SCREEN ... % OF WORK DONE ... PROPER TIK ON EVERY WORK" + "EVERY AGENT
SCREEN SHOULD HAVE ITS OWN CHAT" + intake from the outside world. Design: claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz
(the boards, in the real Hoola Code brand, light + dark). Pipeline diagram: claude.ai/artifact/BVvxNCvrBbA9w15s3u3uT8.

## The flow

| Step | What happens | Her tap |
|---|---|---|
| Attach environments | GitHub (her token), repos added in Hoola Code, a Hoola Code environment, keys sealed per repo host | - |
| Client intake | 30 questions in 10 sections. Sources: her answers, the client's no-login link, documents, recordings (Kaan), pasted email / WhatsApp, a repo scan. Every answer keeps where it came from; two sources that disagree = a conflict she settles | Send for review |
| G1 Scope sign-off | Analyst + Planner (one model call) write stories, tasks, sprints, an estimate and a proposed cap | Approve / ask for changes (re-plans with her words) |
| G2 Design approval | Architect + UX (one call): parts, data, API, screens, risks | Approve / changes (re-designs) |
| G3 Plan + price | Tasks per sprint, the team, the estimate, the cap (editable), the merge rule | Approve -> the project branch `hoola/auto-<slug>-<id>` is made from main in every repo; sprint 1 starts |
| Build | The conductor (worker, every minute) starts each ready task as a real Hoola Code session (`devsahayak.service.start_bg`, mode auto, base = the project branch, her environment). At most `auto_parallel` (3) per project; the server itself runs `dev_ws_live` (2) at a time, the rest wait their turn. A finished task's PR joins the project branch only when its CI is green (or the repo has no CI): Hoola Code's own review, quality gate and reality check already ran inside the session | - |
| G4 Sprint demo | When every task of the sprint is done: what was built, with PRs and proof | Approve -> next sprint / changes -> a fix task in this sprint |
| G5 Change approval | She asks an agent for something the approved stories do not cover -> a priced change request; nothing is built before her yes | Approve -> a task / Not now |
| G6 UAT sign-off | After the last sprint: test the project branch | Approve / changes -> a fix sprint |
| G7 Go-live | Opens one PR per repo, project branch -> her main branch. NOT merged | Approve; then "Merge into main" per PR = a separate tap with the head sha she saw; red / pending CI needs her written reason |
| G8 Handover | The Docs agent writes README / runbook / handover in a session; then the gate | Approve -> done |

## The laws (each has a test in `server/tests/test_v0947_hoola_auto.py`)
- Agents never touch her main branch: sessions work on the project branch; the conductor merges only PRs whose base is
  the project branch, only with green / no CI. Her main changes only through `golive_merge` (her tap, head-sha guard).
- Every gate tap carries the gate's hash (what she saw is what she approved); a changed gate answers 409.
- Past the cost cap every running session is stopped and the project pauses with a "needs you" line.
- The client link: a random token shown once, only its sha256 kept, 30 days, one project, answers + confirm + sign-off
  only; the client never sees a document or the text the agents read; 300 actions a day per link.
- Every word from her or the client is scrubbed: keys / tokens refused or masked, "password / pin / otp / cvv / secret /
  token / api key: <value>" always masked.
- Documents, recordings, chats and repos are DATA for the Intake agent, never instructions (said in the prompt).

## Code
- Server `server/app/hoolaauto/`: `models.py` (auto_projects, auto_answers, auto_sources, auto_gates, auto_tasks,
  auto_events, auto_changes, auto_msgs; registered in db.init_db + `ensure_tables`), `roster.py` (16 agents, the 30
  intake questions, the 8 gates, the phases), `service.py` (projects, environments view, intake + sources + client link,
  plan / design calls, gates, the conductor `tick` / `tick_project`, change requests, agent chat, the screens' views),
  `api.py` (`/api/auto/*` behind her sign-in; public `/api/auto/c/{token}/*`).
- Page `/auto/intake/{token}` = `server/app/static/auto/intake.html|js|css` (no sign-in, noindex, never framed).
- Console: `server/app/static/console/hoolaauto.js` + hooks in `code.js` (sidebar row + project group, `#/auto...`
  routes) + the `v0.947 HOOLA AUTO` block in `hoolacode.css`.
- Phone: `lib/ui/hoola_auto.dart` + the "Hoola Auto" row in `lib/ui/devsahayak_drawer.dart`.
- Worker: `hoolaauto` joins the Tech suite loop in `worker.py`. Push kind `auto_needs` (push.py).
- Settings: `auto_enabled`, `auto_parallel` 3, `auto_task_inr` 25 (the estimate per task), `auto_cap_inr` 1500,
  `auto_client_days` 30.

## Not built in this version (said in the product too)
- Jira / Slack / Figma / cloud consoles / error trackers are not connected: agents read what she pastes or uploads.
- "Call with the Intake agent" (a live voice intake) - the option is shown as not in this version.
- The Watch agent after go-live (errors in production) and staging deploys by the DevOps agent beyond what her CI does.
- Cost: real spend = Hoola Code's metered session cost + an estimate per planning / chat call (Rs 4).
- Parallelism is bounded by the server: `dev_ws_live` (2) sessions run at once; raising it needs a bigger server.

## Not verified
No real GitHub repo, model or phone has run a Hoola Auto project yet: every test uses a fake model, a fake GitHub and
fake Hoola Code sessions. The phone Dart compiles first on CI.
