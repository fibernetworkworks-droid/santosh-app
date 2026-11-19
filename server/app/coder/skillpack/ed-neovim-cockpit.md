---
name: ed-neovim-cockpit
description: Neovim cockpit - modal grammar, buffers, key lane
when_to_use: neovim, vim, terminal editor, vim commands, buffers, edit in vim
---
GOAL: the user is running Neovim in a terminal - Hoola has to speak
the editor's modal grammar; there is no mouse route. Awesome-neovim
(rockerBOO; a curated catalog of plugins, LSP and colorschemes) is the
syllabus - but the driving always goes through the operator's key /
type lanes, one action per turn.

THE GRAMMAR (what Hoola says in a turn, it does):
1. Say the MODE first: normal (navigate), insert (write), command (:)
   - typing in the wrong mode = garbage in the editor; do not trust
   an assumed mode, confirm with :h mode or fresh output.
2. BUFFERS / WINDOWS / TABS: buffers with :ls, jump with :b<name>,
   save with :w, close with :q - one window, one job. Forced
   commands such as :q! / :w! only after ask_approval.
3. TERMINAL LANE: test / build with :term / :make; read the output,
   then the next step. Long work goes in the terminal, the answer
   comes from printed output.
4. DIAGNOSTICS: LSP / spell errors come from the editor's own UI -
   Hoola reads them, it does not report them from a guess.
5. MACROS / SUBSTITUTE: repeated work with :%s/old/new/gc (with
   confirm) or a recorded macro - show a big change on a small
   sample first.

THE LAWS: one turn, one key-sequence; in a modal editor "where am I"
is the first question of every turn; saving the file is the user's
decision (Hoola never presses :w on its own unless the user said so);
reading config files (init.lua / init.vim) is fine, writing them only
after ask_approval; only the printed part of terminal output is
evidence.

NEVER: :q! / :w! / :e! without asking (the user's edited buffer is
their work - a discard is irreversible); walk away
leaving it in insert mode; install a mapping / plugin without ask_approval; run a
macro on a big file without showing a sample; say "done" until there
is printed output from the terminal / editor; treat a terminal
outside vim as the editor.

ALSO ASKED AS (Hinglish asks this skill answers): vim mein file edit karo,
neovim terminal se save karo, buffer band karo
