# Claude.ai features, late 2026 (research, 18 Nov 2026)

**How this was researched.** I read Anthropic's help center (support.claude.com, privacy.claude.com), the claude.com docs and blog, and the Claude apps release notes, fetched between 17 and 18 Nov 2026. Anything I could not confirm from a primary page is marked **UNCONFIRMED**.

**Know this before reading.** Since 16 Sep 2026 the app is in the middle of a migration called the **"new Claude experience"**, which merges Chat and Cowork into one conversation. Several behaviours differ between the legacy chat and the new experience, so I say which one each item belongs to.
- Branching: in the new experience you cannot branch a conversation from an earlier point.
- Web search: there is no web search toggle in the new experience.
- Incognito: incognito chats open in the previous experience.
- Sources: https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude and https://support.claude.com/en/articles/12138966-release-notes

---

## 1. Composer, sending, model and effort

**Sending and the composer**
- You type a prompt and click the submit button.
- The **"+"** button at the lower left opens extra options. Typing **"/"** also shows options and commands. https://support.claude.com/en/articles/8114491
- The + menu items named in Anthropic Academy are "Connectors", "Web search", "Research", "Skills" and "Add folder". The web search toggle may not appear on every plan. https://academy.claude.com/tutorials/getting-started-with-claude-ai
- **Research in the new experience:** type **/deep-research**, or choose + then "Research". https://support.claude.com/en/articles/16761823

**Permission setting in the message box (new experience)**
- **"Auto"** is rolling out as the default on Pro, Max, Ultra and Team. Claude "keeps working without asking about each step", and automated safety checks run before actions.
- **"Manual"** is the default on Enterprise. Claude asks before each action.
- The setting applies to the whole conversation and can be changed at any time.
- You "can also stop or redirect Claude while it works."
- Individual connector tools can be set to "Always ask."
- Source: https://support.claude.com/en/articles/16761823

**Cowork's three permission modes**
- "Manually approve (Manual)", formerly "Ask before acting": you choose Allow or Deny for each action.
- "Automatically approve (Auto)": read-only tools are approved automatically. Write and delete tools run unless an automated check flags them. A blocked action makes Claude try a safer route or ask you. If blocks keep happening, Claude goes back to asking at every step.
- "Skip all approvals (Skip)", formerly "Act without asking".
- Permanently deleting files always needs you to click "Allow".
- Source: https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork

**Model picker**
- The model name sits next to the send button. It is under the input on web and desktop, and at the top of the screen on mobile.
- Click it to choose a model. "More models" shows extra options.
- You can change the model, effort or thinking setting at any point. The change applies from Claude's next response.
- On Enterprise, admins can hide models or effort levels per role, or set what new chats start on.
- Sources: https://support.claude.com/en/articles/8664678-change-the-model-effort-and-thinking-settings.md and https://support.claude.com/en/articles/8114491

**Effort**
- Open it from the model name, then "Effort".
- Levels: "Low", "Medium", "High", "Extra high" (Opus 4.7 and newer) and "Max".
- Each model marks its recommended level "Default".
- Higher effort gives more thorough answers but is slower, uses more tokens and reaches usage limits faster.
- Effort is available on Fable 5.2, Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.1, Opus 5, Sonnet 5, Fable 5, Opus 4.7, Opus 4.6 and Sonnet 4.6.
- Anthropic's guidance: try "Extra high" first for complex coding or agentic tasks on Opus 4.7+, and use "Max" for correctness-critical work.
- Source: https://support.claude.com/en/articles/8664678-change-the-model-effort-and-thinking-settings.md

**Thinking display**
- Thinking and effort are independent settings.
- When thinking is on you see a **"Thinking" indicator with a timer**. Above the response there is an **expandable "Thinking" section with a summary** of Claude's reasoning.
- The toggle is labelled "Thinking" or "Extended", under Effort or on the model menu.
- Thinking **cannot be turned off** on Fable 5.2, Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.1 or Opus 5. On those, lower the effort level instead.
- Thinking sometimes stops early with a message that "the rest of the thought process isn't available". This happens when safety systems trigger. Anthropic's fix is to rephrase.
- An older version of the article said turning extended thinking on or off starts a new chat. That rule is gone from the current article.
- Sources: https://support.claude.com/en/articles/8664678-change-the-model-effort-and-thinking-settings.md and https://support.claude.com/en/articles/10574485
- The literal label **"Thought for Ns"** is **UNCONFIRMED**. The primary pages say only "indicator with a timer".

**Automatic model switch on flagged content (Opus 5 / 5.5)**
- Safety classifiers check each request, including memory, connector content, search results and files.
- When they flag a request, Claude re-runs it on a less capable model in the same conversation:
  - cybersecurity requests fall back to Opus 4.8;
  - biology requests and some frontier ML development requests fall back from Opus 5.5 to Opus 5.
- Requests that try to extract the model's reasoning (distillation) are blocked outright.
- The chat shows "a notice explaining that the model switched". The response is labelled with the model that answered.
- The picker stays on the fallback model; you switch back manually. "Editing your previous message before retrying often helps."
- Toggle: Settings > Capabilities > "Switch models when a message is flagged". With it off, a flagged request pauses the conversation.
- Source: https://support.claude.com/en/articles/16049681-why-claude-switched-models-in-your-conversation-with-opus-5-or-opus-5-5

---

## 2. Reply controls: streaming, stop, edit, retry, copy, feedback

**Streaming and stop**
- No help article describes text streaming or a chat-level **Stop** button. Both are **UNCONFIRMED** as documented.
- The closest primary statements:
  - in the new experience you can "stop or redirect Claude while it works" (https://support.claude.com/en/articles/16761823);
  - you can "jump in to course-correct or provide additional direction mid-task" (https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork);
  - voice mode ends with a "Stop" button (§10).

**Edit and branching**
- Editing an earlier message "creates a separate version of the chat with its own artifacts, so you can explore another direction without losing previous work." https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md
- A support/tutorial result describes going back to a previous message and clicking "Edit" to start a new conversation branch. Source: search result for https://support.claude.com/en/articles/11649438, which now redirects to claude.com tutorials.
- Within a conversation, artifact versions are switched with a "version selector". Source: search snippet of the artifacts article.
- In the **new experience, branching is listed as unavailable**. https://support.claude.com/en/articles/16761823
- The exact "< 1/2 >" arrow UI for message versions is **UNCONFIRMED** (third-party only).

**Retry / regenerate**
- Third-party guides describe a "Retry" control with a "With no changes" option. This is **UNCONFIRMED** in primary docs.
- Primary docs only mention "edit and retry" after a model-switch block. https://support.claude.com/en/articles/16049681

**Copy**
- Legacy artifacts have controls to "view code, copy content, or download". https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md
- Custom visuals offer "Copy as image" (§6).
- A per-message copy button is **UNCONFIRMED** in primary docs.

**Feedback (thumbs up / down)**
- Rating a reply stores "the entire related conversation", including styles, preferences and model settings, "in our secured back-end for up to 5 years".
- The feedback is de-linked from your user and customer IDs, and may be used for research and training.
- Source: https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training
- Team and Enterprise admins can turn it off: Organization settings > Data and Privacy > "Rate chats". https://support.claude.com/en/articles/10504844

---

## 3. Tools in the chat: what shows while Claude works

**Web search**
- During a search you see "an indicator that Claude is searching".
- Claude processes multiple sources and replies with direct citations, source links and quotes. "Every response includes citations."
- Image results come from Bing and show a source link.
- Approximate location (from your IP) may be used for local results.
- Usage: free accounts have limits that reset every 5 hours, and both search and fetch count toward them.
- Prompts like "Search the web" force a search; you can also tell Claude not to search.
- Source: https://support.claude.com/en/articles/10684626-enabling-using-web-search.md

**Web search toggle**
- Legacy: + then "Web search", shown with a checkmark.
- New experience: "There is no web search toggle. Claude searches the web when it judges that doing so will help."
- On Team and Enterprise, an Owner must first enable it in Organization settings > Capabilities.
- Source: https://support.claude.com/en/articles/10684626-enabling-using-web-search.md

**Web fetch**
- With search on, Claude can fetch URLs you give it.
- On free accounts the whole article enters the context window. Anthropic's example: summarising a 10,000-word article uses far more than a search.
- Source: https://support.claude.com/en/articles/10684626-enabling-using-web-search.md

**Past-chat search** is shown as a tool call in the current chat (§8).

**Project knowledge search**
- When RAG is on, you see Claude using a "project knowledge search tool".
- A visual indicator marks the project as RAG-enabled.
- Source: https://support.claude.com/en/articles/11473015-retrieval-augmented-generation-rag-for-projects

**Agentic task progress (Cowork and the new experience)**
- "Progress indicators show what Claude is doing at each step."
- "Claude surfaces its reasoning and approach so you can follow along."
- Complex work may be split into subtasks.
- Finished outputs are delivered to the session to preview and download.
- Source: https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork
- Exact row text such as "Searched the web" or "Ran N commands" is **UNCONFIRMED**.

**Connector tool approval**
- Claude may ask before using a connector's tool. You choose **"Allow once"** or **"Always allow"**. https://claude.com/docs/connectors/getting-started.md
- MCP tool-call raw data is hidden in shared chats (§9).

---

## 4. Research

**Availability and turning it on**
- Paid plans (Pro, Max, Ultra, Team, Enterprise), on web, Desktop and Mobile. Web search must be on.
- Turn it on with + then "Research"; a blue indicator appears.
- New experience: /deep-research or + then "Research".
- Sources: https://support.claude.com/en/articles/11088861-using-research-on-claude.md and https://support.claude.com/en/articles/16761823

**How it works**
- Claude "runs multiple searches that build on each other", decides what to investigate next, explores different angles, and "works through open questions systematically".
- It uses your connectors (Google Workspace and others turned on for the chat) "automatically, without asking for approval each time".
- It cannot use local MCP servers configured in Desktop.
- Source: https://support.claude.com/en/articles/11088861-using-research-on-claude.md

**Mobile limitation**
- Research started on mobile searches the web only and skips connectors, with no error or sign that they were skipped.
- Source: https://support.claude.com/en/articles/11088861-using-research-on-claude.md

**Model and usage**
- Research runs on Opus 5.5 and falls back to Opus 4.8, whatever model is selected for the chat.
- It uses limits faster than a normal chat.
- If Claude isn't researching, Anthropic suggests the prompt "Claude, please use the research tool to…".
- Source: https://support.claude.com/en/articles/11088861-using-research-on-claude.md

**Duration and output**
- Anthropic's integrations post: research can take "anywhere from five to 45 minutes"; "most reports complete in five to 15 minutes".
- It covers "hundreds of internal and external sources" and compiles a single report with citations linking to the original material.
- Sources: https://claude.com/blog/integrations and https://claude.com/blog/research ("easy-to-check citations")

**Not documented (UNCONFIRMED)**
- Whether Research asks clarifying questions before starting.
- The progress UI during a run, notifications, and whether you can leave mid-run.
- Anthropic Academy only says you can ask Claude to "ask you questions before it starts". https://academy.claude.com/tutorials/getting-started-with-claude-ai

---

## 5. Artifacts

**What they are and where they live**
- Content you'd put in front of someone: a design, deck, document, dashboard or small tool.
- Claude typically creates one when the content is "typically over 15 lines", self-contained and likely to be edited or reused.
- Artifacts open in their own window beside the chat. Template-based ones open on a canvas or page you work in directly.
- Everything is saved in the sidebar's **"Artifacts" tab**.
- On iOS and Android you can view and edit artifacts but cannot change sharing settings.
- Source: https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md

**Types (templates since 16 Sep 2026)**
- **Docs, Slides, Design:** all plans.
- **Data:** dashboards, data stories, narrated short videos, letters. Pro and up.
- **Sheets** (cross-tab formulas) and **Whiteboards:** beta, Pro and up.
- **Motion:** animated explainers exported as MP4. Beta, Team and Enterprise.
- Non-template artifacts: documents, code, single-page sites, images, diagrams, dashboards, small tools. https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md
- Legacy chat artifact formats include HTML and React apps, Markdown, Mermaid and SVG. https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude.md

**Editing**
- Ask Claude for changes, or edit directly: type in a doc, edit a slide, move elements on a canvas.
- In a doc, highlight text and click **"Edit with Claude"**. Several pending Markdown edits are applied in one pass when you send.
- In-place draft editing launched 12 Jun 2026.
- On an error, click **"Try fixing with Claude"**; Anthropic notes the fix is not guaranteed.
- Sources: https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md and https://support.claude.com/en/articles/12138966-release-notes

**Export**
- Docs: Word, PDF, Markdown or Google Docs.
- Slides: PowerPoint, PDF or Google Slides.
- Design: .zip, PDF, PowerPoint or standalone HTML.
- Motion: MP4.
- Source: https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md

**Sharing**
- Artifacts start private.
- Current artifacts use "Share" with access levels "Can view", "Commenter" and "Can edit".
- Who has access on Pro, Max and Ultra: "Only you" or "Anyone with the link".
- Who has access on Team and Enterprise: "Only people invited", "Anyone at [org]" or "Anyone with the link". Artifacts stay inside the org by default.
- Email invites are in beta.
- Source: https://support.claude.com/en/articles/9547008-publishing-remixing-and-sharing-artifacts.md

**Legacy artifacts (made before 16 Sep 2026)**
- They show "Publish" instead of "Share". A published one can be opened by anyone with the link, without a Claude account.
- Signed-in viewers can copy and save it.
- **"Get embed code"** with an "Allowed domains" list.
- "Unpublish" is permanent: you can't republish, and it deletes the artifact's storage.
- To build on someone's legacy artifact: copy its code into a new chat. The old "remix" button is not described in current docs (**UNCONFIRMED**).
- Sources: https://support.claude.com/en/articles/9547008-publishing-remixing-and-sharing-artifacts.md and https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md

**AI-powered artifacts ("Artifacts that use Claude")**
- An artifact can call Claude itself. Users sign in and spend their own plan's limits; the creator needs no API key and pays nothing.
- New artifacts ask for permission the first time they use Claude.
- Connected apps (Pro and up): an artifact can read and write in apps such as Asana, Google Calendar and Slack. Everyone connects their own apps.
- Storage (Pro and up), personal or shared:
  - 100 MB and 25,000 records per artifact;
  - uploads up to 20 MB each (2 MB for SVG), 5,000 files and 1 GB total.
- Prerequisite: "Code execution and file creation" (called "Create and edit files" in the new layout) must be on.
- Source: https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md

---

## 6. Inline custom visuals (beta, 12 Mar 2026)

- HTML-built diagrams and charts shown **inline in the reply**, with buttons, sliders and a full-screen view.
- Nothing to turn on: Claude decides when a visual helps, or you ask ("chart this data").
- Clicking inside a visual in chat can send a follow-up prompt (example: "drill into Q3").
- Visuals are ephemeral. To keep one: **"Copy as image"**, **"Download"** as .svg or .html, or **"Save as artifact"**.
- They do **not render on iOS or Android**; mobile apps got inline interactive apps separately on 25 Mar 2026.
- Anthropic recommends Opus for complex visuals.
- Source: https://support.claude.com/en/articles/13979539

---

## 7. Files: uploads and creation

**Uploads in chat**
- **500 MB per file, up to 20 files per chat.**
- Images up to 8000×8000 px; Anthropic recommends 1000×1000 or larger.
- PDFs up to 1,000 pages:
  - ≤100 pages: Claude reads text **and visuals** (images, charts, graphics);
  - 101–1,000 pages: text only;
  - over 1,000 pages: "Uploaded file is too large".
- Other documents: text only, embedded images ignored.
- Types:
  - documents: PDF, DOCX, CSV, TXT, HTML, ODT, RTF, EPUB, JSON, XLSX (XLSX needs code execution on);
  - images: JPEG, PNG, GIF, WebP.
- Ways to add: + then "Add files or photos", drag and drop, or paste.
- Source: https://support.claude.com/en/articles/8241126-upload-files-to-claude.md

**Project files**
- 30 MB per file. The count is unlimited but the content must fit the context window. Text extraction only, except multimodal PDFs.
- Source: https://support.claude.com/en/articles/8241126-upload-files-to-claude.md

**Code execution and file creation**
- Claude creates .xlsx (with working formulas and charts), .pptx, .docx and PDF, plus .py, PNG charts, .csv, .md and .html.
- Code runs in an isolated, per-user sandbox. Task time and container lifetime are limited.
- **30 MB per file** for uploads and downloads in the sandbox. Larger PDFs can be processed without loading into context.
- Files stay downloadable for the whole chat, and can be saved to Google Drive. On mobile, "Download" opens the system preview or another app.
- Network egress:
  - individual plans: "Allow network egress" toggle;
  - Team: default is package managers only;
  - Enterprise: default off;
  - admin options: Off, Package managers only, plus specific domains, or All domains.
- It is on by default for Free, Pro, Max and Ultra under Settings > Capabilities, and on mobile under Settings > Capabilities.
- Public chat sharing is disabled for chats with file artifacts on individual plans.
- Source: https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude.md

**In the new experience**
- Created files appear alongside the conversation.
- Desktop has a "Storage folder" and "Trusted folders".
- Claude asks before permanently deleting files.
- Source: https://support.claude.com/en/articles/16761823

---

## 8. Projects, memory, past chats, incognito

**Projects**
- All plans; Free accounts can create up to 5.
- "+ New Project", with a name and description that Claude does not see.
- Knowledge panel on the right, added with "+". "Set project instructions" then "Save instructions".
- Context does not carry between a project's chats unless it is in the knowledge base.
- Star projects to pin them in the side panel. Archive, unarchive, and delete ("Yes, delete"; archived projects must be unarchived first).
- Move a chat in with "Add to project" and the "Move chat" modal.
- Team and Enterprise sharing: "Can view" / "Can edit", plus a "Shared with you" tab.
- Source: https://support.claude.com/en/articles/9519177

**Project RAG**
- Paid plans only.
- Turns on automatically when knowledge nears the context limit, giving up to 10× capacity, and can switch back.
- Works with web search, thinking and Research.
- Source: https://support.claude.com/en/articles/11473015-retrieval-augmented-generation-rag-for-projects

**New projects (beta)**
- A project is one conversation that Claude splits into parallel cloud threads.
- A "Library" holds the files you add and the files Claude produces.
- Source: https://support.claude.com/en/articles/9517075-what-are-projects.md

**Memory**
- On by default for Free, Pro, Max and Ultra. Free users have had chat-history memory since Mar 2026.
- Since 10 Jul 2026 memory is **categorized topic entries Claude reads and updates during chats**. This replaced the legacy summary that updated every 24 hours.
- Say "remember this" to save something directly. Changes apply from the next conversation.
- View, edit or delete under Settings > Your Claude > "Manage" next to Your memory > "Topics".
- **Project memory:** each project has its own memory and uses your account memory too; "Use account memory" can be turned off on the project page.
- The "Generate memory from chats" toggle offers:
  - "Pause memory": memory is kept but not used, and nothing is added during the pause;
  - "Reset memory": permanently deletes everything.
- **Sensitive topics** (health, religion, politics and similar) are off by default. Turn on with "Include sensitive topics in memory"; a notice shows on each save.
- Never saved, even if asked: government ID numbers, criminal history, financial account numbers, immigration status.
- **Memory off for one chat:** + then "Memory" before the first message. A crossed-out memory icon appears by the title.
- Import and export of memory exists and is experimental.
- Deleting a chat does not delete memories made from it.
- Sources: https://support.claude.com/en/articles/11817273-manage-memory.md and https://support.claude.com/en/articles/12138966-release-notes

**Search and reference past chats**
- Paid plans, on by default.
- Uses RAG, "shows each search as a tool call in the current chat", with citations linking to the source chats.
- Scope: non-project chats, plus a project's own chats within that project.
- Toggle: "Search and reference chats".
- Source: https://support.claude.com/en/articles/11817273-manage-memory.md

**Incognito**
- All plans. Start one with the ghost icon at the upper right of a new chat outside a project.
- Not saved to history or memory, and not searchable.
- On Team and Enterprise, kept at least 30 days and visible to Owners through data export.
- Opens in the old experience, so no code execution or file creation.
- Sources: https://support.claude.com/en/articles/11817273-manage-memory.md and https://support.claude.com/en/articles/16761823

**Monthly recap (beta)**
- Settings > Reflect: topics, most active day, peak hour.
- Source: release notes, 9 Jul 2026, https://support.claude.com/en/articles/12138966-release-notes

---

## 9. Personalization, chat management, sharing, export

**Instructions for Claude**
- Account-wide instructions at Settings > "Your Claude" > "Instructions" ("Account" in the older layout).
- Cowork global instructions migrate here.
- Source: https://support.claude.com/en/articles/10185728-understanding-claude-s-personalization-features.md

**Styles**
- Support snippets say custom styles migrate automatically to skills, disabled by default (enable them in Customize > Skills), and the styles menu will be removed.
- One snippet says Concise, Explanatory and Formal are retired and Learning is kept as a skill, and gives the slash example "/concise-pirate-style".
- The full article (https://support.claude.com/en/articles/10181068-styles-are-moving-to-skills) returned 404 when I fetched it, so these details are **partially UNCONFIRMED**.

**Rename and delete**
- Web: "⋮" on a chat, then "Rename" or "Delete".
- "Chats and tasks" lists the full history, with "Select" and "Select all" for bulk delete.
- iOS: touch and hold a chat. Android: the ⋮ menu, or the checklist icon for bulk delete.
- Deleted chats leave the history immediately and are removed from back-end systems within 30 days.
- Source: https://support.claude.com/en/articles/8230524
- Starring chats and sidebar chat search are **UNCONFIRMED** in primary docs (third-party only). In the new experience, chats and tasks share one **"Recents"** list. https://support.claude.com/en/articles/16761823

**Share a chat**
- "Share" at the upper right creates a **snapshot**: messages before sharing, plus artifacts.
- Later messages stay private. To update, unshare and share again.
- Attached files are excluded, and raw MCP tool data is hidden.
- Anyone with the link can view; Team and Enterprise can share only within the org.
- Unshare by switching "Public" to "Private", or via Settings > Privacy > "Shared chats" > "Unshare".
- Source: https://support.claude.com/en/articles/10593882-share-and-unshare-chats

**Export your data**
- Settings > Privacy > "Export data" (not available on mobile).
- The link arrives by email and **expires after 24 hours**; you must be signed in.
- Team and Enterprise members need the org setting "Allow members to export their own data".
- Source: https://support.claude.com/en/articles/9450526-export-your-claude-data.md

---

## 10. Connectors (MCP), skills, browser and computer use

**Connectors**
- Customize > Connectors > "Discover"; listings are labelled Verified or Community; click "Connect to Claude".
- A connected connector shows status "Connected", "Reconnect" if access is lost, and offers "Disconnect" and "Remove".
- Per chat: + then "Connectors", with a toggle for each.
- Tool permissions: **"Always allow" / "Needs approval" / "Blocked"**, plus "Always ask" in Cowork.
- Custom connectors by remote MCP URL; **the Free plan allows 1 custom connector**. Auth choices: "Sign in now", "Sign in when needed", "No sign-in", plus up to 4 request headers.
- Desktop also takes local .mcpb extensions.
- Web supports MCP Apps that show interactive content in the conversation.
- Sources: https://claude.com/docs/connectors/getting-started.md and https://claude.com/docs/connectors/custom/remote-mcp.md

**Skills**
- "Folders of instructions, scripts, and resources" that Claude loads as needed. Requires code execution.
- Anthropic's built-in Excel, Word, PowerPoint and PDF skills are used automatically when relevant. If Claude doesn't use one, name it in your prompt.
- Custom skills are uploaded as a ZIP: Customize > Skills > "+" > "+ Create skill" > "Upload a skill".
- Org-provisioned and partner skills come from the Skills Directory.
- How a skill's use is shown in chat is **UNCONFIRMED**.
- Sources: https://support.claude.com/en/articles/12512176-what-are-skills and https://support.claude.com/en/articles/12512180-use-skills-in-claude

**Claude in Chrome**
- Permission modes: "Manually approve", "Automatically approve" (the default in the Cowork side panel) and "Skip all approvals".
- Site prompt options: "Allow this action", "Always allow actions on this site", "Decline".
- Always needs explicit approval: permission changes, granting authorizations, entering sensitive information, permanent deletions.
- **Blocked outright:** purchases and financial transactions, creating accounts, credit card or ID data, trades, and following instructions found in emails or web pages.
- Source: https://support.claude.com/en/articles/12902446

**Computer use**
- Beta on Pro, Max and Ultra.
- Claude clicks, types and navigates; it needs Desktop open.
- Sources: https://support.claude.com/en/articles/16761823 and release notes, 23 Mar 2026

---

## 11. Long tasks, leaving and returning, context, limits, errors

**Leaving a running task (new experience)**
- "Longer tasks run in the cloud, so they continue if you close your laptop or leave the page. Results appear in the conversation when they finish."
- Several tasks can run at once.
- Tasks started on desktop appear on mobile, where you can "check progress, answer Claude's questions, and redirect work".
- Scheduled tasks run with no device online.
- Source: https://support.claude.com/en/articles/16761823
- Resuming a plain streaming chat reply after a reload is **UNCONFIRMED** for the legacy chat; only third-party reports cover it.

**Notifications**
- A "Response completions" toggle under Settings > General > Notifications is **UNCONFIRMED**. Only third-party guides and bug reports mention it.
- Release notes say Chrome sends "notifications when input is needed" (29 Sep 2025).

**Context window and compaction**
- Newest models on paid plans have up to a **1M**-token window; others have 500K or 200K. Part of the window is reserved for the reply.
- **Automatic context management** (requires code execution): near the limit, Claude summarizes earlier messages.
- "Your full chat history is preserved so Claude can reference it even after summarization."
- Status text: Claude "organizing its thoughts".
- Compaction uses more of your usage limit. Rare cases, such as a huge first message, can still hit the limit.
- Source: https://support.claude.com/en/articles/11647753-how-usage-and-length-limits-work.md

**Usage limits**
- A 5-hour session limit (starts at your first message) and weekly limits. Shared across claude.ai, Claude Code and Desktop.
- Shown under Settings > Usage > "Current session".
- Verified Ultra accounts have no 5-hour limit. Usage credits let work continue instead of stopping.
- Source: https://support.claude.com/en/articles/11647753-how-usage-and-length-limits-work.md

**Exact error and limit messages**
- "Approaching session limit" / "Approaching weekly limit"
- "You've used X% of your weekly limit."
- "5-hour limit reached - resets [time]"
- "You've reached your weekly limit. It resets [day] at [time]."
- "5-hour limit resets [time] - continuing with usage credits"
- "Now using credits…"
- "Your message will exceed the length limit for this chat." / "Try attaching fewer or smaller files or starting a new conversation."
- "Due to unexpected capacity constraints, Claude is unable to respond to your message. Please try again soon." (does not show on the status page)
- "There was an error logging you in"
- Source: https://support.claude.com/en/articles/12466728-understanding-claude-error-messages.md

---

## 12. Voice, mobile, desktop, keyboard

**Voice mode**
- Beta on all plans, on mobile, desktop and web.
- Start it with the sound-wave icon. On web and desktop it ends with **"Stop"**.
- Listening modes: hands-free (the default; speak to interrupt) or push-to-talk.
- A limited set of preset voices; no voice cloning.
- Starts on the model family you last used in text chat. **Fable is not available**.
- Has web search and connectors; the Free plan can connect 1 tool.
- Saved as a text transcript; audio is deleted by default.
- Many languages, with non-English in beta.
- Dictation (speech to text) is separate from voice mode.
- Source: https://support.claude.com/en/articles/11101966-use-voice-mode.md

**Android device features**
- Drafts messages and emails that you send yourself.
- Reads and creates calendar events.
- Sets alarms and timers.
- Location and Maps.
- Health Connect (read-only; US, Android 14+).
- Permission prompts: "Allow once / Always allow / Don't allow".
- Reminders are on iOS only.
- Source: https://support.claude.com/en/articles/11869629-use-claude-with-android-apps

**Mac desktop quick entry**
- Double-tap Option (configurable) to open Claude from any app.
- "Drag to take a screenshot", or click a window to attach it.
- Caps Lock dictation.
- Needs macOS 12+, and macOS 14+ for dictation. Not on Windows.
- Source: search result for https://support.claude.com/en/articles/12626668

**Keyboard shortcuts**
- The only official list I found is for **Claude Docs**: Cmd+/ opens the list; Cmd+B/I/U, Cmd+K, Cmd+Option+1–6, Cmd+Option+M for comments, and "/", "@" and ":" inserts.
- Source: https://support.claude.com/en/articles/17458093
- Slides accessibility keys: F6, Tab, Return, Escape, arrow keys. https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md
- **General claude.ai chat shortcuts (new chat, search) are UNCONFIRMED.** Third-party sources conflict (Ctrl+K, Ctrl+Shift+O, Ctrl+O).

---

## 13. How Claude runs a task end to end (Anthropic's own statements)

- In the new experience, Claude "decides which tool to use"; you don't pick a mode. https://support.claude.com/en/articles/16761823
- On "Auto", Claude keeps working without asking about each step, with automated safety checks before actions. You can stop or redirect it at any time. https://support.claude.com/en/articles/16761823
- Research runs chained searches, picks its next lines of inquiry from what it finds, and uses connectors without asking each time. https://support.claude.com/en/articles/11088861-using-research-on-claude.md
- Cowork shows progress per step, can split work into subtasks, accepts mid-task steering, asks you questions, and delivers files to the session. https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork

---

## 14. Other recent surfaces (release notes only, not researched in depth)

All from https://support.claude.com/en/articles/12138966-release-notes:
- Claude Meetings (beta, Team/Enterprise): joins Google Meet as a note-taker.
- Personal Finance (beta, US): linked bank, card and investment accounts.
- Claude Duet (research preview, 21 Oct 2026): a proactive agent app.
- Time and focus: break reminders and quiet hours.
- Desktop release channels: Stable or Latest.
- Salesforce in Claude (beta).
- Claude Tag in Slack (Team/Enterprise).
