---
name: cm-publish-lane
description: Campaign to CMS - publish via API or ax, approved
---
GOAL: campaign content se live page tak ka safar - WordPress/Drupal/
headless-CMS catalogs syllabus hai (generic CMS gyaan; WP-CLI ek named
tool category hai command-line publishing ki) - par lane hamesha Hoola
ke apne doors se chalti hai: pehle APNA CMS, phir site ka API, phir hi
admin UI, pixel sabse aakhri me.

THE DOORS (sab operator ke asli tools):
1. APNA CMS PEHLE: Hoola ka apna CMS module lane pe hai:
   app/site/cms.py (the HOOLA CMS). Draft yahin banao:
   doc_studio/doc_create se
   content likho, publish website lane se karo (website, website_dekho
   doors). Apna ghar pehle, bahar ka kaam baad me.
2. WORDPRESS API: site ka REST API khula ho to api_call se posts
   bhejo - /wp-json/wp/v2/posts pattern; search terms ke roop me
   WP-CLI patterns use karo ("wp post create", "wp post list", "wp
   post update") - wahi fields REST me bhi milte hain (title, content,
   status). Draft me status=draft, publish me ask_approval ke baad.
3. WP ADMIN UI (aakhri CMS lane): API band ho to admin UI SEMANTIC
   chalao - ax_find se element by role/name (textbox "Add title",
   button "Publish"), page_fill_form se fields bharo, palette/search
   by name. EK ACTION PER TURN: click ke baad screen badal sakti hai,
   purana action stale - naya step naye ax_find se.
4. AUDIENCE GATE: campaign me audience step hai (email_bulk) to usse
   pehle consent_jaanch zaroori - bina consent ka bulk bhejna mana
   hai. consent fail ho to ruk jao, aage nahi badhna.
5. EVIDENCE: har publish ke baad printed URL + timestamp lo -
   website_dekho se live page ka state padho, get_campaign_status se
   campaign ki haalat. Printed output hi sach hai, andaaz nahi.

THE LAWS: publish = ask_approval ALWAYS (chhota edit ho ya bada
launch, poochhe bina publish nahi); consent_jaanch before any
audience/bulk action; printed output = only evidence; semantic doors
pehle (apna CMS > API > ax naam wale element > click). Campaign
side: create_campaign se banao, control_campaign se chalao -
ek turn ek publish action, result padh ke aage badho.

FLOW: draft (doc_studio/doc_create) -> approval (ask_approval) ->
publish (website lane ya api_call) -> verify (website_dekho se
printed URL + timestamp) -> audience (consent_jaanch, phir email_bulk)
-> status (get_campaign_status). browse_web sirf tab jab site ka apna
door jawab na de.

NEVER: bina ask_approval publish karna; consent_jaanch ke bina bulk
audience (email_bulk); live page edit bina printed diff ke (kya badla,
purana vs naya, chat me dikha do); credentials chat me likhna (API
tokens WP-CLI me bhi, chat me kabhi nahi); bade launch se pehle
schedule na dekhna (get_campaign_status se timing confirm karo);
pixel click jab api_call ya ax_find ka semantic door khula ho.
