---
name: ga-launcher-recipes
description: Steam/Deck recipes - launch, notes, playtime, approval
when_to_use: steam, steam deck, game launcher, game settings, launch options, controller, playtime, pc game not working
---
GOAL: in the Hoola launcher every game opens with its own RECIPE CARD
- launch path, flags, controller notes, known fixes - all in memory.
Syllabus: the curated community lists for Steam / Steam Deck (in the
style of SteamDB, PCGamingWiki) - these are SEARCH TERMS ("proton
rating", "controller support"), never version numbers invented from
memory.

RECIPE CARD (per game - saved with remember, brought back with
memory_search):
- launch path + executable + working dir
- flags: one flag per line, with the reason (e.g. force borderless)
- controller notes: mapping, deadzone, deck-style layout
- fixes: one-liners such as "crash on alt-tab -> do this"
The card is a living document - update it the moment you learn
something new; the game's history stays with the launcher and never
leaves the tenant. Write both lines - the new flag that worked and
the one that failed; a diary of successes only will mislead the next
session.

LAUNCH FLOW (the operator lane is the real lane):
1. Get the recipe card with memory_search; for a new game ask the
   user and make the first card.
2. Look at pc_status: is the machine free, is the client running, is
   there disk space? If something is missing tell the user, do not
   force an install yourself.
3. Launch with open_app or pc_do - one turn, one action.
4. Drive the game window semantically: ax_find (role / name) -
   "Play", "Resume", "Options" are found by name, not by
   coordinates. A screenshot only when ax gives no answer. Only one
   screen action per turn - that avoids both stale clicks and
   mistakes.

DECK-STYLE THINKING: playable-first. Before launch write the proton
note, controller mapping and performance flags on the card; during
the session keep updating playtime and new notes on the card. When
"Update available" shows, do not run it at once - ask the user and
schedule it after the session. In the proton note write only what
you saw or the user told you - no rating guessed by yourself. Save
files and playtime data stay inside the tenant. Inside the game
window too, the named door (ax_find) first, a pixel click last of
all.

SESSION CLOSE: when play ends, closing the window is not the whole
job - write the new notes on the card (remember), update playtime,
and if a save backup is wanted, ask_approval first. Next time
memory_search finds the same card and the session starts where it
stopped.

NEVER: edit a save file or overwrite a config without ask_approval
("shall I write your save?"); a cracked / pirated build or a DRM
bypass - do not even touch it; start an auto-update or background
download mid-session; a pixel click when the ax door is open; an
irreversible step such as uninstall / cloud-resync without
ask_approval; say "the game is running" without seeing the launch
output.

ALSO ASKED AS (Hinglish asks this skill answers): steam game launch karna
hai pc se, game nahi chal raha, controller set karo, launch flags lagao
