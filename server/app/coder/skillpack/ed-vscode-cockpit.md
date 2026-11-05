---
name: ed-vscode-cockpit
description: VS Code cockpit - palette first, ax tree, never pixels
---
GOAL: wo editor ke andar baithi hai, Hoola uske saath chalti hai -
"drive Hoola from inside the IDE" ka matlab: VS Code pehle se hi
semantically controllable hai (ax tree, Electron accessibility), to
pixel-clicking ki zaroorat hi nahi. Awesome-vscode (viatsko; themes,
extensions, keybindings ka curated catalog) syllabus hai - par lane
hamesha Hoola ke operator ke semantic doors se chalti hai.

THE DOORS (sab operator ke asli tools, pixel lane aakhri me):
1. COMMAND PALETTE pehle (key: Ctrl+Shift+P): VS Code ka har command
   apne NAME se milta hai - "Format Document", "Git: Commit", "Run
   Task". Naam se address = semantic; coordinates kabhi nahi.
2. QUICK OPEN (Ctrl+P): file ka naam likho, khul gaya - user_pc_search
   se pehle yahan dekho (editor ka apna index sabse tez hai).
3. ax_find: element by role/name (role=button name=Save) - sidebar,
   tabs, problems panel; screenshot sirf tab jab ax jawab na de.
4. INTEGRATED TERMINAL (Ctrl+`): test/build/lint yahan se - command
   type karo, output padho; lambi runs terminal me, chat me nahi.
5. PROBLEMS panel: diagnostics yahan se padho (error/warning counts),
   fix karne ke baad dobara padho - "theek ho gaya" printed evidence
   se, andaaz se nahi.

THE LAWS: ek turn ek editor action (screen move ho sakti hai; purana
action stale hai); palette/quick-open jaise naam-wale doors pehle,
click x,y sabse aakhri me; jo file khuli hai usi me kaam (naya tab
kholne se pehle poochho); terminal commands ek-ek karke, output padh
ke aage; extensions install / settings badalna = pehle ask_approval.

NEVER: unsaved buffer close/discard karna bina poochhe (ask_approval -
"save karke band karu?"); uski keybindings/settings bina batae
badalna; auto-save band karna; pixel click jab ax door khula ho;
editor ke bahar kisi ki screen chhoona (ye lane sirf editor hai);
bina output padhe "test pass ho gaya" bolna - terminal ka printed
output hi sach hai.
