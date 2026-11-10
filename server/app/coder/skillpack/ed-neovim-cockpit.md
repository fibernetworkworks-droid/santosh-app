---
name: ed-neovim-cockpit
description: Neovim cockpit - modal grammar, buffers, key lane
when_to_use: neovim, vim, terminal editor, vim commands, buffers, edit in vim
---
GOAL: wo terminal me Neovim chala rahi hai - Hoola ke liye editor
modal grammar ki bhasha seekhni hai, mouse ka rasta nahi hai.
Awesome-neovim (rockerBOO; plugins, LSP, colorschemes ka curated
catalog) syllabus hai - par driving hamesha operator ke key/type
lanes se, ek action per turn.

THE GRAMMAR (jo turn me Hoola bolegi, wo karegi):
1. MODE pehle bolo: normal (navigate), insert (likhna), command (:)
   - galat mode me type karna = editor me kachra; mode check karne
   ka bharosa nahi, :h mode ya fresh output se confirm.
2. BUFFERS/WINDOWS/TABS: :ls se buffers, :b<name> se jump, :w me save,
   :q se band - ek window ek kaam. :q!/:w! jaise force wale sirf
   ask_approval ke baad.
3. TERMINAL LANE: :term / :make se test-build; output padho, phir
   agla kadam. Lamba kaam terminal me, jawab printed output se.
4. DIAGNOSTICS: LSP/spell ki galtiyan editor ke apne UI se - Hoola
   unhe padhta hai, andaze se nahi batata.
5. MACROS/SUBSTITUTE: repeat kaam :%s/old/new/gc (confirm ke saath)
   ya macro record - bade badlav pehle chhote sample pe dikhao.

THE LAWS: ek turn ek key-sequence; modal editor me "kahan ho" har
turn ka pehla sawaal hai; file save ka faisla uska hai (Hoola kabhi
akhead :w nahi dabaata jab tak usne na kaha ho); config files
(init.lua/init.vim) padhna theek, likhna sirf ask_approval ke baad;
terminal output ka printed hissa hi evidence hai.

NEVER: bina poochhe :q!/:w!/:e! (uska edited buffer uska kaam hai -
discard irreversible hai); insert mode me akhead chhod ke jaana;
mapping/plugin install bina ask_approval; macros bade file pe bina
sample dikhae chalana; "ho gaya" bolna jab tak terminal/editor ka
printed output na ho; vim ke bahar terminal ko editor samajhna.
