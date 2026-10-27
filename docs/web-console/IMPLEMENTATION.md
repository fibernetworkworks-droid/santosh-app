# Hoola independent web workspace

Implementation date: 27 October 2026. Based on the first prototype selected by the owner.

## Delivered

The default `/console/` now contains a Creative studio beside the existing chat, sessions, creation library, tools, voice and account views. Hoola's Night Glass tokens, avatar and saffron/violet identity remain. The new web stylesheet adds a quieter sidebar, readable conversation spacing, structured forms, responsive layouts, entrance transitions and a slowly moving orbit. Reduced-motion preferences disable the new motion.

Four forms submit durable turns through the existing authenticated `/api/conversations/{id}/messages` API. Image briefs include supported aspect/quality settings and reference IDs. Video briefs request a storyboard and estimate before paid generation. Research accepts web/files or attached-files-only preferences. Documents request a real Word, PDF, spreadsheet or presentation output. These are instructions to the existing agent, not new deterministic generation endpoints. Source preferences are brief instructions, not a server-enforced network boundary. Existing provider configuration, account budget, tool availability and approval rules still determine execution.

Uploads use the existing conversation file endpoint, with 25 MB limits, six sources per workflow and three PNG/JPEG/WebP references for images. Switching to image mode removes incompatible references. Successful submission returns to the originating conversation. Network retries retain a stable client ID, and retries stop when the account session changes.

Actual output events render as inline image/video/audio results or file cards. Downloads fetch authenticated bytes. Pages open in the existing sandboxed, bridged workspace. Files can be reused as references without uploading them again. The companion workspace supports a width control, expansion and Escape to restore. Closing a file tab aborts pending media fetching and revokes its blob URLs.

Chat uploads and retries capture their original conversation instead of consulting whichever chat is current later. Draft writes capture their own chat and text; switching chats saves the current draft immediately. Logout clears studio/panel state and recurring polling.

## Validation

- 19 passed: `test_console_build.py`, `test_console_google.py`, `test_v142_console.py`, `test_v163_panel.py` — authentication, console serving, build and panel contracts.
- 9 passed: `test_web_workspace.py`, `test_v0194_sessions.py` — real authenticated file upload, source IDs passed to the durable inbox, a single accepted turn on duplicate retries, timeline attachment persistence and existing sessions/cache contracts. Provider execution is replaced in the new test.
- 10 passed: `node --test server/tests/web/results.test.cjs` — real DOM contract doubles for media paths, stale asynchronous requests, blob cleanup, artifact launch, replay behavior and dictation regression.
- Chromium walkthrough: four form submissions, source-file requirement, actual multipart upload contract, paid-video approval wording, rendered result/reference reuse, expansion/Escape, incompatible reference removal, and no document overflow at 1024/768/390/320 px. No browser JavaScript exceptions. This uses fixture API responses with the real shipped frontend; it is not a live paid-generation check.
- JavaScript syntax checks and `git diff --check` passed.

Run browser checks from the repository root with Playwright and an installed Chromium:

```bash
node server/tests/web/workspace.browser.cjs
```

Optional environment variables: `PLAYWRIGHT_MODULE` (module name/path), `CHROMIUM_EXECUTABLE` (browser path), `CONSOLE_SHOTS` (screenshot directory). Python tests run from `server/` with the server dependencies installed.

An additional legacy project test, `test_v164_projects.py::test_files_and_the_prompt_of_a_project_chat`, fails because its spy assumes a string system prompt while the agent supplies prompt blocks. The identical failure was reproduced on unchanged commit `c91cb73`; shared backend code was not changed to accommodate that old assumption.

## Release boundary and remaining work

This is the implemented web foundation and four connected workflows, not completion of every acceptance item in `RESEARCH-AND-SPEC.md`. Rich image masking, a dedicated video timeline editor, deterministic research source controls and a larger creation-library redesign remain later acceptance items. The current creation library and editing surfaces retain their existing backend capabilities.

No mobile/desktop sources, shared backend handlers, agent prompts, schemas, version metadata or deployment workflows were changed. No migration or mobile build is required. No production deployment or paid provider generation was performed. Before public release, exercise Google/password login and configured image/document/research/video services on a staging account, including budget and approval flows. Roll back by reverting the web-only commits; legacy console remains available at `/console/?legacy=1`.
