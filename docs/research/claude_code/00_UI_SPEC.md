# Claude Code (web, desktop, mobile): UI and logic, as a spec for Hoola Code

Read 14 Nov 2026 from Anthropic's own docs:
- code.claude.com/docs/en/claude-code-on-the-web
- code.claude.com/docs/en/web-quickstart
- code.claude.com/docs/en/cloud-environments
- code.claude.com/docs/en/mobile
- code.claude.com/docs/en/desktop
- code.claude.com/docs/en/routines

Plus the owner's four phone screenshots (Android Claude app, Code tab) and an unofficial endpoint page. That page, claude.ai/artifact/7YT2Ths9ujW5KghMj1bXMC, was reverse-engineered from the Android APK. It is someone else's work and was not verified; it was used only for screen names.

UNVERIFIED means the point was not found in an official doc.

## 1. New session screen

**The row under the box, in order:**
1. Environment chip. It only shows before the first message; after that, change it through "Edit cloud environment".
2. Repository chip. One session can have several repositories.
3. Branch.
4. Permission mode. Cloud sessions offer Auto, Accept edits and Plan. Manual and Bypass are not available in the cloud.
5. Model, with effort inside the model picker.

**Phone, from the owner's screenshots:**
- Title "New Session" and the line "Ready when you are" with a mascot.
- Two pill chips: "Default" (cloud icon) and "Add repository" (GitHub icon).
- Composer reading "Type or hold to talk", with a + button, a mic and a send arrow.

**Pre-fill by URL:** `?prompt=` (or `q`), `repositories=` (or `repo`), `environment=<name or id>`.

**If a session fails to start:** "Your new session couldn't start", and the prompt goes back into the box.

## 2. Environments

**Selector sheet (phone):**
- Title "Select environment", subtitle "Choose an environment for your Claude Code session".
- Rows: "Auto — Follows your repositories" (ticked), and "Default — Anthropic cloud" with a gear.
- A "+ Create environment" button.

**Create page (phone):**
- Title "Create a new environment".
- Text: "Cloud environments power Claude's code execution. You can always create or edit environments later."
- Name field, prefilled "Default".
- Network access cards:
  - None: "Sessions can't reach the internet."
  - Limited (badge Recommended): "Sessions reach only what you allow below."
  - Full: "Sessions can reach any domain."
- A white "Create" button.

**Dialog rows (docs):**
- Name.
- Network access:
  - None.
  - Limited (the default): an "Allow package managers" box, ticked by default, plus "Allowed domains" (one per line; `*.` matches subdomains).
  - Full.
- Setup script: bash, run as root, before Claude Code starts. It must exit 0. The environment's variables are not set while it runs.
- Environment variables: `.env` format, readable by everyone who uses the environment.
- Network secrets: added by a proxy outside the VM. A saved value can never be viewed again.

**Rules:**
- An environment is archived, never deleted. Sessions already using it keep running.
- A network change reaches running sessions within about a minute.
- The setup script runs on the first session. If it finishes in about 5 minutes or less, the result is snapshotted and reused. It runs again when the script or the hosts change, or about every 7 days.
- Onboarding creates "Default": Limited, no variables, no script.

## 3. Repositories

**Picker sheet (phone):** title "Repositories"; one card per repo showing the owner (grey) above the name; a search button; "+ Connect more".

**GitHub access:**
- Through the GitHub App, or `/web-setup` (which uses the local `gh` token).
- A GitHub proxy keeps credentials outside the VM.
- It blocks branch deletes and tag pushes.
- A repository not attached to the session gets a 403.

## 4. Session view

**Panels and changes:**
- The transcript, with a session rail you can show or hide.
- A Changes card showing `+N −M`, which opens the diff view.
- In the diff view you can comment on a line; the comments go along with the next message. "Compare against" sets the branch to diff with.

**Pull requests:**
- Create PR (right-click for a draft PR).
- The PR menu has Auto-fix, which watches CI and review comments.
- Merge-when-ready is on desktop only.

**Messages:**
- A message sent while Claude works is queued. Its ✕ returns the text to the box.
- Plan mode, and "Rewind to here".

**Moving work and sharing:**
- Teleport to the terminal with `claude --teleport`.
- `claude --cloud "task"` starts a cloud session.
- Share as Private, Team or Public. The other person gets a snapshot.

**Session list:** archive and delete from the sidebar ⋯ menu; an Archived tab.

**Lifecycle:** an idle VM pauses. History survives, but running shells are lost.

## 5. Long work and automation

**Command limits:**
- A command runs in the foreground for 2 minutes by default, 10 at most.
- It then moves to the background for about 30 more minutes.

**Scheduled tasks (once called routines):**
- Triggers: a schedule (no more than hourly), an API call (bearer token, payload marked untrusted), or a GitHub event.
- Each task shows history, Run now and an on/off switch.
- Runs push to `claude/` branches.

**Notifications:**
- With Remote Control, the phone gets a push when work finishes or needs a decision.
- UNVERIFIED for plain cloud sessions.

## 6. Desktop Code tab

**Environments:** Local, SSH or Cloud. The worktree toggle is off by default and lives in `.claude/worktrees/`.

**Panes:** browser, terminal, editor and side chat.

**Remote Control:** a switch per session. Connected local sessions appear on the web and in the mobile app.

## 7. Where Hoola Code stands (v0.878)

| Claude Code | Hoola Code |
|---|---|
| Named environments + selector + create/edit/archive | **Built v0.878** (`devsahayak/envs.py`, `/api/devsahayak/envs`, console first chip, phone sheets + create page) |
| Auto (follows your repositories) | Built: no environment = each repo's own Settings |
| Allow package managers box | Built v0.878 (`net.allow_for(pkgs=)`) |
| Network secrets on the environment | Keys stay per repo (Settings > repo > Keys); they apply in every environment |
| Setup script snapshot | The setup runs once per dependency key and is cached as a snapshot (`devlab.service.snapshot`) |
| Repo picker + search + Connect more | Phone v0.878; console repo chip |
| Branch, mode, model + effort | Console: all four. Phone: mode only |
| Diff + line comments + compare | Console: yes. Phone: no |
| Queued messages, Stop, rewind | Console: yes. Phone: notes + stop |
| Create PR / Auto-fix / CI loop | Yes (draft PR, CI fix rounds, Auto-fix per PR) |
| Scheduled tasks + API trigger + GitHub events | Yes (Phase 5 / 6). Phone: view only |
| Share snapshot | Read-only link, 7 days |
| Teleport to a local terminal, Remote Control | Not built (Hoola has its own PC bridge, which is frozen) |
| Network on in the cloud | Built, but OFF until `dev_net` (the server's `python -m app.devlab net` must pass first) |
