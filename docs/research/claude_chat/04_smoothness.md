# Smooth streaming chat techniques (research, 18 Nov 2026)

Research was web only. Nothing in the repo was changed. Each technique says what it does, the jank it removes, how to build it, and the source. Anything I could not confirm from a primary source is marked **UNCONFIRMED**.

**Main caveat:** Anthropic's help center says very little about how the claude.ai chat client behaves: scroll, stop, what happens when you leave mid-reply. Most "Claude does X" statements below come from third-party teardowns or user bug reports, and are labelled that way. The engineering patterns themselves come from primary sources: Anthropic API docs, Vercel AI SDK and Streamdown docs, the use-stick-to-bottom source code, Chrome DevRel, MUI, OpenAI API docs, Smashing Magazine, Stardrift and Ably.

---

## A. The wire: what the stream gives you (Anthropic API)

**1. Use the event structure as your UI state machine.**
- **What it does:** every stream runs in a fixed order:
  - `message_start` (a Message with empty `content`);
  - then per content block: `content_block_start`, any number of `content_block_delta`, `content_block_stop`. Each block has an `index` matching its slot in the final content array;
  - then one or more `message_delta`;
  - then `message_stop`.
- **Delta types:** `text_delta`, `input_json_delta` (tool input), `thinking_delta`, and `signature_delta` just before a thinking block closes.
- **Blocks that arrive whole, with no deltas:** `redacted_thinking`, server tool results such as `web_search_tool_result`, and fallback blocks.
- **Jank it removes:** guessing UI state from raw text. Create one UI element per `index`. A `text` block becomes a prose node, a `thinking` block a collapsible row, a `tool_use` block a tool row. Close each on `content_block_stop`.
- **Notes:**
  - `usage` token counts in `message_delta` are cumulative. Overwrite them; do not add them up.
  - Handle unknown event types quietly. The versioning policy says new event types may be added.
- Source: https://platform.claude.com/docs/en/build-with-claude/streaming

**2. Ping events are a heartbeat.**
- "Event streams might also include any number of `ping` events."
- Use them, or your own server pings, to reset a client "stalled" watchdog. Dead air should not read as a dropped connection.
- Source: same page.

**3. Treat a mid-stream error as a normal state.**
- An `event: error` can arrive inside a 200 stream, e.g. `{"type":"error","error":{"type":"overloaded_error"}}`, which would be HTTP 529 outside streaming.
- Jank it removes: a frozen half-reply with no explanation.
- UI: keep the partial text, add an inline error line under it with **Retry**, and clear the working indicator.
- Source: same page.

**4. Recover an interrupted stream from the last text block.**
- The documented recovery:
  1. Save everything received.
  2. Send a continuation request. For Claude 4.6 and later this is a *user* message: "Your previous response was interrupted and ended with [previous_response]. Continue from where you left off." Earlier models used an assistant prefill.
  3. Keep streaming.
- Caveat from the docs: "Tool use and thinking blocks cannot be partially recovered. You can resume streaming from the most recent text block."
- UI: append the continuation to the same bubble. Do not start a new one.
- Source: same page, "Error recovery".

**5. Fine-grained tool streaming lets a large tool input fill a panel live.**
- **What it does:** `eager_input_streaming: true` on a tool streams its input without server-side buffering or validation. Without it, "nothing prints for a large parameter until Claude has finished generating it."
- **Jank it removes:** a long silent gap while the model writes a page, code file or document into a tool call. The artifact panel can type live instead.
- **Notes:**
  - Concatenate `partial_json` and parse only at `content_block_stop`.
  - Guard the parse: you may get invalid or truncated JSON, especially with `stop_reason: max_tokens`.
  - On a bad parse, return a `tool_result` with `is_error: true` and content `{"INVALID_JSON": "<raw>"}`.
  - For a live preview, render the string field progressively with a partial-JSON parser (the SDK helpers expose parsed input as it streams).
- Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming

**6. Thinking display modes are part of the UI contract.**
- With `display: "omitted"`, the thinking block opens, gets one empty `thinking_delta` and a `signature_delta`, then closes. No text streams.
- With `display: "updates"` (beta), only short progress updates stream as text.
- UI: an omitted-thinking block should still show "Thinking… 7s" with a timer and no body. Do not render an empty expandable.
- Source: streaming page, "Thinking delta".

---

## B. Perceived latency (before the first word)

**7. Show the user's message immediately (optimistic send) and switch to "working" at once.**
- **What it does:** her bubble appears the moment she hits Send. The status goes ready → submitted → streaming → ready/error (the AI SDK's `useChat` status values).
- **Jank it removes:** a dead gap between Send and anything happening.
- **Notes:**
  - Give the local message a client id. Keep it on failure with "Not sent · Retry".
  - Sending always scrolls to the bottom, even when auto-scroll is paused (MUI's rule).
- Sources: https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat (status, `setMessages` "useful for optimistic updates"); https://mui.com/x/react-chat/behavior/scrolling/

**8. Show a working indicator with a live label and an elapsed timer.**
- **What it does:** claude.ai's help article describes a "Thinking" indicator "with a timer showing how long Claude has been processing", and an expandable "Thinking" section above the reply that shows a summary.
- **Jank it removes:** not knowing whether it is stuck. A ticking clock separates slow from dead.
- **Notes:** start the timer at submit. Keep the label short and in the present tense ("Thinking", "Searching the web").
- Source: https://support.claude.com/en/articles/10574485 (the fetched copy was the French translation; the wording above is translated).
- Whether the section is collapsed by default is **UNCONFIRMED** in that article. Claude Code's docs describe thinking as "collapsed by default" (quoted in https://claudeissues.com/issue/62672-docs-extended-thinking-docs-omit-collapsed-summary-rendering-behavior).

**9. Delay the empty assistant bubble briefly so a fast reply does not flash a placeholder.**
- Smashing's reference build waits **300 ms** before the bubble appears, and **200 ms** before a retry restarts.
- Jank it removes: a skeleton or "…" flashing for 50 ms on fast replies.
- Source: https://smashingmagazine.com/2026/05/designing-stable-interfaces-streaming-content/

---

## C. Text pacing

**10. Release text word by word on a steady clock, not in network bursts (smoothStream).**
- **What it does:** buffer the incoming tokens and release complete chunks at an even rate.
- **AI SDK `smoothStream` parameters:**
  - `delayInMs` defaults to **10 ms** per chunk (`null` turns delays off).
  - Chunking: `"word"` (default), `"line"`, a RegExp, a callback, or an `Intl.Segmenter`.
  - The delay is skipped while the document is hidden.
- **Jank it removes:** network bursts landing as visible jumps of 20-80 characters, then stalls.
- **Notes:**
  - For CJK, Thai and Vietnamese, use `new Intl.Segmenter(locale, {granularity:'word'})`. Word chunking needs spaces.
  - For Devanagari, use a grapheme- or word-aware segmenter. Never split code points.
- Source: https://ai-sdk.dev/docs/reference/ai-sdk-core/smooth-stream

**11. Flush to the DOM once per animation frame.**
- **What it does:** collect characters in a `pending` buffer and schedule one `requestAnimationFrame(flush)`, guarded by a `rafQueued` flag. Browsers paint about 60 times a second.
- **Jank it removes:** layout thrash from touching the DOM per character, and cursor flicker. Smashing measured the cursor being removed and re-added up to 80 times a second when rebuilding at a ~30 ms interval.
- **Notes:** run auto-scroll once per flush, not once per token.
- Sources: Smashing (above). AI SDK `useChat` also has a `throttle` option in ms (React/Vue; default off).

**12. Fade in only the newly added words.**
- **What it does:** Streamdown's `animated` mode wraps new tokens in spans with a CSS animation:
  - `sep` = `"word"` (default) or `"char"`;
  - duration **150 ms**;
  - easing `"ease"`.
  React reconciliation means "only newly-mounted spans trigger the CSS animation".
- **Jank it removes:** words "popping" in.
- **Notes:**
  - When `isAnimating` is false, the animate plugin is dropped, so finished messages render with no extra spans. Do this to keep long chats light.
  - Character mode creates many more DOM nodes; use it sparingly.
- Source: https://streamdown.ai/docs/animation

**13. Respect reduced motion.**
- Under `prefers-reduced-motion: reduce`, render the whole response at once with no typing animation, and stop the cursor blink (a blinking cursor counts as flashing content).
- Source: Smashing (above).

---

## D. Incremental markdown (no flicker, no broken half-syntax)

**14. Append. Never re-parse the whole message into `innerHTML` on every chunk.**
- **What it does:** use `append()`, or a streaming parser that holds output back "until it's clear" and then appends to what is already rendered.
- **Jank it removes:** full re-layout of the message each tick, lost text selection, restarted animations, and visible repaint flashes.
- **Notes:**
  - Re-parsing the accumulated Markdown means "the entire set of previous chunks plus the new chunk need to be re-parsed as HTML."
  - Sanitize the *accumulated* output (e.g. with DOMPurify), not single chunks: dangerous markup can be split across chunks. If the sanitizer removes anything, stop rendering.
- Source: https://developer.chrome.com/docs/ai/render-llm-responses (recommends the `streaming-markdown` parser)

**15. Memoize per block: finished blocks never re-render.**
- **What it does:** Streamdown splits Markdown into blocks, memoizes each block, and caches each block's parse. "Only blocks with changed content are re-rendered… Completed blocks remain stable and don't re-render."
- **Jank it removes:** long replies getting slower as they grow, a finished table re-flowing when a new paragraph arrives, and a code block's highlighting re-running.
- **Notes:** key blocks by position or stable id. Only the last, open block re-renders per flush. Streamdown claims rendering "stays consistent regardless of content length", but publishes no benchmark.
- Source: https://streamdown.ai/docs/memoization

**16. Close unterminated syntax before rendering (remend).**
- **What remend closes** (each can be turned off):
  - bold `**`, italic `*`/`_`, bold-italic `***`, inline code, strikethrough `~~`, block math `$$`;
  - links and images;
  - setext headings, and `>` inside list items treated as a comparison operator;
  - incomplete HTML tags at the end of the text, which are stripped.
- **Incomplete links:** `[text](url` becomes `[text](streamdown:incomplete-link)`, and an incomplete image becomes a loading placeholder. `linkMode` is `"protocol"` (placeholder URL) or `"text-only"`.
- remend "respects code blocks", and exposes `isWithinCodeBlock` so you do not "fix" `**` inside code.
- **Jank it removes:** raw `**` and `[` showing mid-stream, then everything snapping into bold or a link at once.
- **Not documented by remend:** code-fence closing and table completion. Treat them yourself; see technique 17.
- Sources: https://streamdown.ai/docs/configuration ; https://github.com/vercel/streamdown/tree/main/packages/remend

**17. Draw an open code block or table as its final element right away.** (**UNCONFIRMED** as a documented library feature; it is the standard derivation from 15 and 16.)
- **What it does:** when an opening ```` ``` ```` arrives with no closing fence, render a code container with its language label and append lines into it. Do not show raw backticks. For a table, render the header row once the separator row (`|---|`) arrives. Add body rows as each line ends. Never render a half row.
- **Jank it removes:** a big block of raw text suddenly turning into a styled code box or table (the largest single layout jump in most chat UIs).
- **Notes:**
  - Defer syntax highlighting of the open block. Run Shiki or another highlighter on block close, or debounced at about 200 ms. **UNCONFIRMED** value.
  - Give tables horizontal scroll on narrow screens.
  - Streamdown adds copy, download and full-screen controls to code, tables and Mermaid (`controls` prop).

**18. Show a caret at the end of the streaming text.**
- Streamdown has `caret: "block" | "circle"`.
- Mark the caret `aria-hidden` and remove it on stop, error or done.
- Sources: https://streamdown.ai/docs/configuration ; Smashing (above).

---

## E. Scrolling

**19. Stick to the bottom only while the user is at the bottom.**
- **What it does:** follow new content while the user is within a threshold of the bottom. Stop the moment they scroll up.
- **Thresholds in practice:**
  - use-stick-to-bottom: **70 px** (`STICK_TO_BOTTOM_OFFSET_PX`);
  - Smashing: **60 px**. Without a threshold, "tiny layout changes (like a new line) would briefly create a gap and break auto-scroll";
  - MUI chat: **150 px** buffer.
- **Jank it removes:** the page yanking her back down while she reads, and the opposite failure (losing the lock because a new line changed the height).
- Sources: https://raw.githubusercontent.com/stackblitz-labs/use-stick-to-bottom/main/src/useStickToBottom.ts ; Smashing ; MUI (above).

**20. Detect "user scrolled up" the way use-stick-to-bottom does.**
- **Escaping the lock:**
  - The scroll handler compares `scrollTop` after a short timeout. If it went *down* (the user moved up the page), set `escapedFromLock`.
  - A wheel event with negative `deltaY` escapes at once.
  - An active **text selection** (mouse down plus a selection inside the container) also releases the lock, so following never fights her highlighting.
- **Re-locking:** scrolling back within the threshold re-locks.
- **Following:** use a ResizeObserver on the content, not per-token scroll calls. It keeps the lock when content *shrinks* too (e.g. a collapsing tool row).
- **Animation:** a velocity-based spring, not a fixed-duration ease. Defaults: damping **0.7**, stiffness **0.05**, mass **1.25**. On a content resize it keeps animating for **350 ms** (`RETAIN_ANIMATION_DURATION_MS`). `"instant"` is available.
- It does not rely on CSS `overflow-anchor`, which Safari lacks.
- Reset the "user scrolled" flag when a new stream starts (Smashing).
- Sources: use-stick-to-bottom source + README https://github.com/stackblitz-labs/use-stick-to-bottom ; Smashing.

**21. Show a "jump to latest" button while auto-scroll is paused.**
- **What it does:** a floating button appears once the user scrolls away from the bottom. Clicking it smoothly returns to the latest message. MUI can show an unseen-message count badge on it.
- **Jank it removes:** "is it still writing?" with no way back.
- Sources: MUI (above); https://microsoft.github.io/simplechat/latest-release/release-260-chat-scroll-508/ (the view stays put during generation, with a floating scroll-to-latest control).
- Known claude.ai failure mode, reported by users: the desktop app auto-scrolling during streaming even after the user scrolled up — https://claudeissues.com/issue/53382-bug-desktop-app-chat-window-auto-scrolls-to-bottom-during-streaming-even-when-us . This is the thing to avoid.

**22. Loading older history must not move the view.**
- MUI anchors to the first visible message, so "prepending history never causes a scroll jump".
- Source: MUI.

**23. Flutter: build the list reversed and lift it for the keyboard with padding, not offset jumps.**
- **What it does:**
  - With `ListView(reverse: true)`, offset 0 is the bottom, so "stay at bottom" is free.
  - Move content up for the keyboard by changing bottom padding (viewInsets). `jumpTo` offset maths is reported as inaccurate.
  - Follow streamed growth only when at the bottom. Otherwise pin the current position (e.g. ListViewObserver's chat "keep position" mode, which its author says supports ChatGPT-style generated messages).
  - Inserting at both ends of a reversed list can jump. One write-up fixes this with `CustomScrollView(center:)`.
- Sources:
  - https://pub.dev/documentation/flutter_keyboard_controller/latest/
  - https://medium.com/@linxunfeng/flutter-keep-im-message-position-greatly-upgraded-supports-generative-messages-like-chatgpt-2b199a7b14e7
  - https://besthub.dev/articles/fixing-jumping-behavior-in-flutter-chat-lists-with-customscrollview-center-0beb64225105
- All are third-party; verify on device.

---

## F. Tool-call and thinking rows

**24. Collapse thinking by default, with a live label and timer, and summarize it.**
- Claude.ai shows an expandable "Thinking" section above the reply, with a timer during processing and a summary on click.
- Claude Code collapses thinking by default (Ctrl+O expands it).
- Source: https://support.claude.com/en/articles/10574485 ; the claudeissues 62672 issue above quotes the Claude Code docs.

**25. Tool rows: one compact row per tool block, present tense while running, past tense with elapsed time when done, collapsed by default.**
- Derived from the event model (technique 1). A `tool_use` block opens a row ("Searching the web…"). Its result closes it ("Searched the web · 3 results · 2.1s"). Details sit behind a disclosure arrow.
- An official Anthropic description of claude.ai's tool-row wording or timing: **UNCONFIRMED**. No help-center source found.
- **Jank it removes:** long tool output pushing the answer off screen, and rows changing size every second. Keep collapsed rows a fixed height, so the clock updating does not cause reflow.

**26. Stream artifacts into a side panel while the chat keeps going.**
- A teardown of claude.ai: artifacts open in a split pane, and "in-thread refinement continues while the pane is open".
- With fine-grained tool streaming (technique 5), the panel can type the file live.
- Sources: https://aiuxplayground.com/teardowns/claude/output ; https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them

---

## G. Stop, retry, edit and branch

**27. Stop must be clean, and must survive resumable streams.**
- **Client side (Smashing):** cancel the timer, set `isStreaming=false`, clear `pending`, reset `rafQueued` so no queued characters write after stop, remove the caret, add a "response stopped" label, and move focus to Retry.
- **The trap:** with resumable streams, a client abort counts as a *disconnect*. `stop()` only closes the HTTP connection and generation keeps running. Closing the tab or refreshing has the same effect.
- **The fix the AI SDK docs prescribe — a separate stop endpoint that:**
  1. checks `activeStreamId`;
  2. saves the partial assistant message with an insert or merge, so an older client snapshot never overwrites a newer server message;
  3. cancels the work;
  4. clears `activeStreamId` only if it still matches.
- **Rules from the same docs:**
  - "Do not call the stop endpoint from route cleanup code." Only an explicit user action calls it.
  - After a stop, do not auto-reconnect until a new message or a retry.
- Also: a new message sent mid-stream must stop the active stream first, so two loops never write at once (Smashing).
- Sources: https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams ; Smashing.

**28. Retry makes a new version, with 1/N navigation. It never overwrites.**
- Claude.ai teardown: "Try again generates an alternate answer instead of overwriting the first one", with a "1/N navigation with Previous version tooltip".
- Editing a user message branches the thread.
- Under each answer: copy, read aloud, thumbs up/down, Try again.
- Selecting text shows a Reply tooltip that quotes the selection into the composer as a removable chip.
- Sources: https://aiuxplayground.com/teardowns/claude/output ; https://intelligencebyintent.com/insights/conversation-branching-the-ai-feature-most-executives-dont-know-about
- Official help-center wording: **UNCONFIRMED**.

**29. Retry after an error replaces the failed row in place.**
- Remove the whole failed message row (not just the bubble), reset state, and restart.
- Label the button `aria-label="Retry: <first 60 chars of question>"`.
- Source: Smashing.

---

## H. Resuming an in-flight response (tab switch, reload, app in the background)

**30. Generation must not belong to the HTTP request.**
- **What it does:** run the model call in a worker. Write each chunk to a durable per-message buffer (Stardrift: a Redis stream keyed by `chat_id` + `message_id`). The SSE handler only relays from the buffer.
- **Jank it removes:** a reload or tab switch killing the answer, and paying twice to regenerate.
- **Notes:**
  - Keep a *separate* status store (`chat_id → active message_id`, with states pending / ongoing / complete).
  - Deleting the buffer at the end creates a race: the reader may not have seen the final chunk.
- Source: https://stardrift.ai/blog/streaming-resumptions

**31. Reattach by message id, from an offset.**
- **What it does:** on mount, on visibility regained, or on reconnect, the client asks "is there an active stream for this chat?" and resumes.
- **AI SDK:**
  - `useChat({resume:true})` sends GET `/api/chat/[id]/stream` on mount and when the page becomes visible after a network drop.
  - The server answers **204** when `activeStreamId` is null, otherwise `resumeExistingStream`.
  - The default transport assumes a *full replay*: on the first `start` chunk it resets and rebuilds the partial reply (no duplicated text). If you send only the remaining chunks, set `resumeStreamIsReplay:false`.
- **`resumable-stream` (Redis):**
  - one `INCR` + `SUBSCRIBE` per stream;
  - "The producer will always complete the stream, even if the reader of the original stream goes away";
  - a second reader receives the buffered messages, then the live chunks;
  - a finished stream returns 422.
- **Ably:** the client keeps its rendered offset and reconnects with session id + offset. Example: a drop at token 1,247 resumes at 1,248.
- **OpenAI Responses background mode:**
  - `background:true`; poll while `queued`/`in_progress`;
  - resume a stream by passing the last event's `sequence_number` as `starting_after`;
  - cancel is idempotent;
  - you cannot stream later a response created without `stream:true`.
- **Notes:** number every SSE event (`id:` = sequence) so `Last-Event-ID` or `starting_after` works. Make the client dedupe by sequence.
- Sources:
  - https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams
  - https://github.com/vercel/resumable-stream
  - https://ably.com/blog/resumable-llm-streaming-session-recovery-across-reconnects
  - https://developers.openai.com/api/docs/guides/background

**32. Multi-device and multi-tab: separate session state from the connection.**
- "Device B has no position in Device A's stream." Persist the session server-side.
- Ably notes that Vercel's Redis package covers single-device recovery; multi-device continuity needs different architecture.
- Expect race conditions when two tabs reconnect at once.
- Source: Ably (above).

**33. What claude.ai and ChatGPT actually do when you leave: UNCONFIRMED.**
- No official Anthropic or OpenAI article says whether a reply keeps generating after you close the tab, switch chats or background the app.
- Evidence is anecdotal and points both ways:
  - A guide says a closed-tab reply "keeps running in the background", which causes the "A previous response is still running" state — https://parix.ai/blog/a-previous-response-is-still-running/
  - Bug reports say switching tabs or projects mid-stream *discarded* the reply or message — https://claudeissues.com/issue/44480-bug-messages-disappear-when-switching-tabs-while-response-is-streaming and https://claudeissues.com/issue/28787-bug-navigating-to-a-different-project-mid-generation-interrupts-and-discards-the
  - ChatGPT background tabs: Chrome tab discarding cuts the stream ("Network Error"). Vendor blog, not OpenAI — https://www.superchargebrowser.com/library/keep-chatgpt-running-background-chrome/
- **Lesson:** the server must own the reply, and every surface must reattach (techniques 30-31). Also clear a stale "working" flag server-side, so a dead turn never blocks the chat.

---

## I. Offline, reconnect and message status

**34. Each message has a visible status: sending → sent → failed (Retry).**
- Optimistic local message with a client id, which the server uses to dedupe.
- Flyer's Flutter stream widget tracks per-stream `Loading` / `Streaming` / `Completed` / `Error`. On completion or error, swap the stream message for a normal persisted `TextMessage`.
- Sources: https://pub.dev/documentation/flyer_chat_text_stream_message/latest/ ; AI SDK `useChat` (`status`, `clearError`, `regenerate`, `resumeStream`).

**35. Reconnect silently, show it quietly, then reattach.**
- On drop: keep the partial text, show a small "Reconnecting…" line (not an error), retry with backoff, then call resume (technique 31). Only after repeated failure show "Couldn't finish · Retry".
- A watchdog fed by pings (technique 2) tells a stall apart from a long tool call.
- AI SDK `resume` re-checks after the page becomes visible again following a disconnect.
- Specific backoff timings: **UNCONFIRMED** from any primary source.

---

## J. Mobile-specific

**36. Keyboard:** the list lifts with the keyboard by padding (technique 23). Sending keeps focus in the composer and scrolls to bottom (MUI rule). A swipe down on the list may dismiss the keyboard (common Flutter pattern; **UNCONFIRMED** in a primary source).

**37. Background:** a phone app *will* be suspended. Design for reattach on resume from the app lifecycle, not for keeping a socket alive. Server-owned generation plus resume (30-31) is the only robust answer. Pair with a push notification when a long reply finishes. Claude.ai web users are filing feature requests for exactly this — https://claudeissues.com/issue/21002-feature-browser-notification-when-task-completes-in-claude-ai-web-version (a request, not a shipped feature).

**38. Haptics:** a light tick on send and on completion is common in native chat apps. **UNCONFIRMED.** I found no primary source documenting Claude's or ChatGPT's haptics.

**39. Accessibility on both surfaces:**
- live region `role="log"`, `aria-live="polite"`, `aria-atomic="false"` (only new text announced); `assertive` only for errors;
- caret `aria-hidden`;
- hide controls with `display:none` so hidden buttons are not focusable.
- Source: Smashing.

---

## Top 15 smoothness techniques ranked

1. **Server-owned generation plus reattach by message id and offset.** Reload, tab switch or app background never loses or restarts a reply (30, 31).
2. **Per-block memoized incremental markdown.** Finished blocks never re-render; only the open block updates (15).
3. **Append, never full `innerHTML` re-parse**, with one DOM flush per `requestAnimationFrame` (11, 14).
4. **Stick to bottom with a ~60-70 px threshold**, a ResizeObserver, and release on scroll-up, wheel-up or text selection (19, 20).
5. **"Jump to latest" button** whenever following is paused (21).
6. **Steady word pacing**: about 10 ms per word smoothing with a locale-aware segmenter, skipped when hidden (10).
7. **Close unterminated syntax** (remend) so raw `**` and `[` never flash (16).
8. **Open code fences and tables render as their final element at once**; highlight on block close (17).
9. **Optimistic user message plus a working row with a live label and elapsed timer** from submit (7, 8).
10. **Thinking and tool rows collapsed and fixed-height**, present tense while running, past tense with a time when done (24, 25).
11. **Real stop**: an explicit stop endpoint that saves the partial, cancels work and blocks auto-reconnect; abort is not stop (27).
12. **Mid-stream errors inline**: partial kept, short reason, in-place Retry; resume from the last text block (3, 4, 29).
13. **Retry and edit create versions or branches with 1/N navigation**, never overwrite (28).
14. **150 ms fade on new words only**, dropped once streaming ends; reduced motion = instant (12, 13).
15. **Flutter: reversed list, keyboard lift by padding, follow only at bottom**, swap the stream message for a persisted message on completion (23, 34).

## Sources used
- https://platform.claude.com/docs/en/build-with-claude/streaming
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming
- https://support.claude.com/en/articles/10574485
- https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them
- https://aiuxplayground.com/teardowns/claude/output
- https://intelligencebyintent.com/insights/conversation-branching-the-ai-feature-most-executives-dont-know-about
- https://github.com/vercel/streamdown
- https://streamdown.ai/docs/animation
- https://streamdown.ai/docs/memoization
- https://streamdown.ai/docs/configuration
- https://github.com/vercel/streamdown/tree/main/packages/remend
- https://ai-sdk.dev/docs/reference/ai-sdk-core/smooth-stream
- https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat
- https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams
- https://github.com/vercel/resumable-stream
- https://github.com/stackblitz-labs/use-stick-to-bottom
- https://raw.githubusercontent.com/stackblitz-labs/use-stick-to-bottom/main/src/useStickToBottom.ts
- https://developer.chrome.com/docs/ai/render-llm-responses
- https://smashingmagazine.com/2026/05/designing-stable-interfaces-streaming-content/
- https://mui.com/x/react-chat/behavior/scrolling/
- https://microsoft.github.io/simplechat/latest-release/release-260-chat-scroll-508/
- https://stardrift.ai/blog/streaming-resumptions
- https://ably.com/blog/resumable-llm-streaming-session-recovery-across-reconnects
- https://developers.openai.com/api/docs/guides/background
- https://pub.dev/documentation/flyer_chat_text_stream_message/latest/
- https://pub.dev/documentation/flutter_keyboard_controller/latest/
- https://medium.com/@linxunfeng/flutter-keep-im-message-position-greatly-upgraded-supports-generative-messages-like-chatgpt-2b199a7b14e7
- https://besthub.dev/articles/fixing-jumping-behavior-in-flutter-chat-lists-with-customscrollview-center-0beb64225105
- Anecdotal, for behaviour on leaving:
  - https://parix.ai/blog/a-previous-response-is-still-running/
  - https://claudeissues.com/issue/44480-bug-messages-disappear-when-switching-tabs-while-response-is-streaming
  - https://claudeissues.com/issue/28787-bug-navigating-to-a-different-project-mid-generation-interrupts-and-discards-the
  - https://claudeissues.com/issue/53382-bug-desktop-app-chat-window-auto-scrolls-to-bottom-during-streaming-even-when-us
  - https://claudeissues.com/issue/62672-docs-extended-thinking-docs-omit-collapsed-summary-rendering-behavior
  - https://claudeissues.com/issue/21002-feature-browser-notification-when-task-completes-in-claude-ai-web-version
  - https://www.superchargebrowser.com/library/keep-chatgpt-running-background-chrome/
