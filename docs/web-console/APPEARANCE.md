# Hoola web appearance and composer

Adds Light, Dark and Match system color modes; Default Hoola, Match system and Dyslexia-friendly chat fonts; and the composer additions menu. This is Hoola branding with familiar interaction patterns, not a replica of proprietary Claude assets.

Preferences save locally in the browser. System mode responds to OS changes. The same-origin appearance-init.js applies validated preferences before styles paint, without weakening the console CSP. Denied or malformed browser storage falls back safely. Fonts apply to conversation text and the composer; code remains monospace. Dyslexia-friendly uses Verdana/Tahoma/Arial and extra letter, word and line spacing; no special-font or clinical benefit is claimed.

The + menu invokes existing file upload, image, research and document workflows and Appearance. It supports keyboard navigation, Escape, outside dismissal, focus return, and bounded positioning on phone widths. Appearance uses native radios and a select with keyboard focus containment. Both support reduced motion.

Validation: 17 unit/contract tests, six deployment tests, plus the browser walkthrough covering persistence, light/dark/system changes, font choices, file chooser, creative routing, mobile positioning, navigation history and existing workspace workflows. Light/dark screenshots visually inspected.

Release assets include appearance-init.js in both deployment allowlists and the bundle. No backend runtime behavior, mobile application, voice, model routing or PC changes. Not deployed as part of implementation.
