---
name: cm-publish-lane
description: Campaign to CMS - publish via API or ax, approved
when_to_use: publish to wordpress, CMS, blog post live, update website content, drupal, headless cms, publish campaign page
---
GOAL: the journey from campaign content to a live page - WordPress /
Drupal / headless-CMS catalogs are the syllabus (generic CMS
knowledge; WP-CLI is a named tool category for command-line
publishing) - but the lane always runs through Hoola's own doors: OUR
OWN CMS first, then the site's API, only then the admin UI, pixels
last of all.

THE DOORS (all real operator tools):
1. OUR OWN CMS FIRST: Hoola's own CMS is on the module lane:
   app/site/cms.py (the HOOLA CMS). Make the draft here: write the
   content with doc_studio / doc_create, publish through the website
   lane (the website, website_dekho doors). Our own house first,
   outside work later.
2. WORDPRESS API: when the site's REST API is open, send posts with
   api_call - the /wp-json/wp/v2/posts pattern; use the WP-CLI
   patterns as search terms ("wp post create", "wp post list", "wp
   post update") - the same fields exist in REST (title, content,
   status). status=draft for a draft, publish only after
   ask_approval.
3. WP ADMIN UI (the last CMS lane): when the API is closed, drive
   the admin UI SEMANTICALLY - find the element by role / name with
   ax_find (textbox "Add title", button "Publish"), fill the fields
   with page_fill_form, use the palette / search by name. ONE ACTION
   PER TURN: the screen can change after a click and the old action
   goes stale - a new step starts from a new ax_find.
4. AUDIENCE GATE: when the campaign has an audience step
   (email_bulk), consent_jaanch is required before it - sending bulk
   without consent is not allowed. If consent fails, stop; do not go
   further.
5. EVIDENCE: after every publish take the printed URL + timestamp -
   read the live page's state with website_dekho and the campaign's
   state with get_campaign_status. Printed output is the truth, not
   a guess.

THE LAWS: publish = ask_approval ALWAYS (a small edit or a big
launch, never publish without asking); consent_jaanch before any
audience / bulk action; printed output = the only evidence; semantic
doors first (own CMS > API > an element named through ax > click).
Campaign side: create with create_campaign, run with
control_campaign - one publish action per turn, read the result
before moving on.

FLOW: draft (doc_studio / doc_create) -> approval (ask_approval) ->
publish (the website lane or api_call) -> verify (printed URL +
timestamp from website_dekho) -> audience (consent_jaanch, then
email_bulk) -> status (get_campaign_status). browse_web only when
the site's own door gives no answer.

NEVER: publish without ask_approval; a bulk audience (email_bulk)
without consent_jaanch; edit a live page without a printed diff
(what changed, old vs new, shown in chat); write credentials in chat
(API tokens for WP-CLI too - never in chat); skip the schedule check
before a big launch (confirm the timing with get_campaign_status); a
pixel click when the semantic door of api_call or ax_find is open.

ALSO ASKED AS (Hinglish asks this skill answers): blog post live kar do,
wordpress site par campaign publish karo, website ka content update karo
