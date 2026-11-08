---
name: internal-comms
description: A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).
imported: true
when_to_use: weekly update, status report, hafte ka update, newsletter, FAQ jawab, incident report, leadership update, team ko update bhejna, 3P update, progress plans problems
license: Complete terms in LICENSE.txt
---
## When to use this skill
To write internal communications, use this skill for:
- 3P updates (Progress, Plans, Problems)
- Company newsletters
- FAQ responses
- Status reports
- Leadership updates
- Project updates
- Incident reports

## How to use this skill

To write any internal communication:

1. **Identify the communication type** from the request
2. **Load the appropriate guideline file** from the `examples/` directory:
    - `examples/3p-updates.md` - For Progress/Plans/Problems team updates
    - `examples/company-newsletter.md` - For company-wide newsletters
    - `examples/faq-answers.md` - For answering frequently asked questions
    - `examples/general-comms.md` - For anything else that doesn't explicitly match one of the above
3. **Follow the specific instructions** in that file for formatting, tone, and content gathering

If the communication type doesn't match any existing guideline, ask for clarification or more context about the desired format.

## Keywords
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms

<!-- HOOLA NOTE: everything below this line was added by Newtika for Hoola. The text above is Anthropic's original (Apache License 2.0, see LICENSE.txt); only the frontmatter line when_to_use was added. -->

## Hoola note (Modified by Newtika for Hoola, 4 Nov 2026)
- Write in the language SHE writes in (Hinglish, Hindi or English). Keep the section structure and length rules of the example file; only the words change.
- "My company" means HER business. Never invent numbers, names, dates or customers: use what she told you, her own data (sheets, calendar, mail, memory) or leave a clear blank like `[number]` and ask once.
- Where an example says Slack / Drive / Email / Calendar, use the tools Hoola actually has for her (email, Google Drive/Sheets/Calendar, her notebook). If she has none connected, ask her for the points and just format them.
- Short updates go straight in chat. A newsletter or report she wants as a file: use `doc_studio`. Never send, post or share to other people yourself: show the draft and wait for her tap.
- Hinglish 3P shape (same strict format): `Progress:` kya hua, `Plans:` agle hafte kya, `Problems:` kya ruka hua hai. Keep it readable in 30-60 seconds.
- Hoola's own house rules (reply style, privacy, confirm-before-send) win over this skill if they ever disagree.
