# Hoola artifact workflows

The existing Creations section becomes Artifacts: searchable/filterable saved outputs plus four guided template starters (dashboard, calculator, interactive guide and business report). Templates submit real briefs through the existing agent; they are not canned completed artifacts.

Live ready page artifacts open beside the conversation when chat is active and no other workspace is open. Pending outputs do not open an editor, and duplicate events do not reopen a manually dismissed artifact. Existing panel previews keep isolated sandboxed iframes without allow-same-origin; page URLs must be same-origin artifact routes.

HTML artifacts support Preview/Code, saved version selection, conversational revision through the existing revise API, and export of the selected HTML version. File artifacts expose Refine in chat, download and the existing approval-backed sharing request. This does not add arbitrary direct source saving or claim WYSIWYG editing for Office files. Interactive controls within an artifact remain supported through its existing bridge. Public sharing still requires the existing approval card; clicking Share alone does not publish it.

Tab controls support keyboard navigation. Async library results and page views are generation-guarded against stale responses. File/page share requests capture their originating conversation. Existing backend identity/authorization and artifact version storage remain unchanged.

Validation: 19 unit/contract tests, 13 backend artifact/panel tests; new browser walkthrough for template briefs, library search races, live auto-open, sandbox policy, revision, version selection, HTML download, approval-backed share request and responsive widths; existing workspace/navigation/research/geometry walkthrough passes. Services are simulated, so live provider generation and external publication are not exercised.

Web assets only; no mobile, voice, PC or backend runtime changes. Implementation is local, not deployed.
