# Conversation geometry

Uses a shared 880px maximum conversation width for messages and composer, retains symmetric reserved scrollbar space, and constrains flexible message/result children. Long URLs wrap; preformatted code and wide tables scroll internally. Code remains monospace and preformatted.

A reading anchor is captured as a text Range where supported (element fallback elsewhere). Sidebar/workspace class changes, width controls and window resizing restore the visible text position through the short layout transition. Readers who are following the bottom remain there; readers scrolled up are not pulled to the final answer. User input cancels active anchor restoration. Removed conversation elements invalidate their anchors.

Validation: existing 19 unit/contract tests; browser walkthrough extended with a very long URL and unbroken code line, internal code scrolling, shared centering, and visible text anchor checks across workspace opening and closing. Existing desktop/mobile, workspace, theme, history and research checks remain included. Web assets only; no backend or mobile changes.
