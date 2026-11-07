# Compact web progress: cause and correction

The execution system emits separate streams for work state, tool steps, reasoning, operator/browser sessions, approvals, and outputs. The web client was presenting nearly all of these as conversation content:

- `stepEvent` created open tool groups and individual argument/result rows.
- `thinkEvent` created open reasoning cards containing raw reasoning text.
- Browser and operator-task updates reached `renderCard`'s generic fallback, which printed task, URL, session and step metadata with `kvRows`.
- Timeline replay requested steps and reconstructed the same operational content on reload.
- The account stream forwarded non-local cards from other chats into the open conversation, including operational browser events.
- `workEvent` automatically opened the detailed live-work panel at the start of tasks.
- Replay used the presence of a user message to decide whether assistant messages should appear. If a busy operation filled the page of history with events, the user message could fall outside that page and the final answer could be skipped.

The web presentation now collapses routine operational events into one live status above the composer. It shows Thinking, Working on it, Preparing your response, Waiting for the next step, or Reviewing an incomplete result based on real events. No timers invent completion percentages. The activity stops on the actual typing-off signal and resets on chat switch/logout. Raw reasoning and tool arguments are not rendered in the conversation. History omits routine operation cards. Unrelated-chat routine progress is not forwarded into the open chat. The detailed activity panel opens only when requested.

Approvals, questions, payment restrictions, drafts and completed output cards remain available. Assistant messages and streamed final text remain visible; this change does not fabricate a successful result or change the agent's execution quality. Failed/partial work is not labelled complete. Backend event storage and mobile behavior remain unchanged.

Validation: pure presentation-policy tests distinguish task updates from approvals, preserve file/artifact output, and verify English status labels. The Chromium fixture emits 30 live steps and reasoning, checks that one status updates without exposing internal text, delivers a final streamed answer and typing-off, verifies another chat's progress remains hidden, and replays 25 browser updates while retaining an approval card. Existing workflow, result, sidebar, alignment and responsive checks also pass.

Mobile implementation is the next phase. The shared event protocol is intentionally unchanged so that mobile can adopt the same classification separately.
