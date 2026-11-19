---
name: ed-vscode-cockpit
description: VS Code cockpit - palette first, ax tree, never pixels
when_to_use: vs code, vscode, editor, rename symbol, command palette, ide, extensions, problems panel
---
GOAL: the user is working inside the editor and Hoola works alongside
- "drive Hoola from inside the IDE" means: VS Code is already
semantically controllable (ax tree, Electron accessibility), so there
is no need for pixel-clicking at all. Awesome-vscode (viatsko; a
curated catalog of themes, extensions and keybindings) is the syllabus
- but the lane always runs through the operator's semantic doors.

THE DOORS (all real operator tools, the pixel lane last):
1. COMMAND PALETTE first (key: Ctrl+Shift+P): every VS Code command
   is found by its NAME - "Format Document", "Git: Commit", "Run
   Task". Addressing by name = semantic; never coordinates.
2. QUICK OPEN (Ctrl+P): type the file name and it opens - look here
   before user_pc_search (the editor's own index is the fastest).
3. ax_find: an element by role / name (role=button name=Save) - the
   sidebar, tabs, the problems panel; a screenshot only when ax
   gives no answer.
4. INTEGRATED TERMINAL (Ctrl+`): test / build / lint from here - type
   the command, read the output; long runs go in the terminal, not
   in chat.
5. PROBLEMS panel: read diagnostics here (error / warning counts),
   read again after fixing - "it is fixed" comes from printed
   evidence, not from a guess.

THE LAWS: one turn, one editor action (the screen can move; the old
action is stale); named doors such as the palette / quick open first,
a click at x,y last of all; work in the file that is open (ask before
opening a new tab); terminal commands one at a time, read the output
before going on; installing extensions / changing settings =
ask_approval first.

NEVER: close / discard an unsaved buffer without asking (ask_approval
- "shall I save and close?"); change the user's keybindings / settings
without telling them; turn off auto-save; a pixel click when the ax
door is open; touch anyone's screen outside the editor (this lane is
the editor only); say "the tests passed" without reading the output -
the terminal's printed output is the truth.

ALSO ASKED AS (Hinglish asks this skill answers): vs code mein extension
kaise lagaye, editor ke andar se kaam karao, file kholo aur symbol rename
karo
