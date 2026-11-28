# prompts.chat read (28 Nov 2026)

Repo: github.com/f/prompts.chat at c3e7767 (formerly "Awesome ChatGPT Prompts", ~143k stars). Read in a scratch clone,
nothing run, nothing copied into Hoola yet.

## Licence (decides what we may take)
- Code (src/, prisma/, scripts/, packages/) = **MIT**. Ideas and code may be reused with the MIT notice.
- Prompt data (prompts.csv, PROMPTS.md, user prompts) = **CC0** public domain. May be taken whole, no credit needed
  (credit anyway, it costs nothing).
- The book (src/content/book/, 34 chapters + 17 languages) is site content and falls under MIT.

## What it is
A Next.js 16 + Prisma/Postgres social site for prompts: share, vote, comment, collect, version (change requests),
categories, tags, private prompts, 17 languages, an MCP server, a Claude Code plugin, a Raycast extension, an npm
toolkit. Later grown into Bots, Bot Teams, Skills, "Taste", Classifiers and Workflows.

## The data
- prompts.csv: **3,235 prompts**, columns act / prompt / for_devs / type / contributor. Types: TEXT 2,821,
  STRUCTURED 393 (JSON / YAML), IMAGE 21. Median length 1,155 characters, longest 144k.
- Topic spread (word match, rough): code 786, image 711, business / marketing 601, video 253; India-specific only 17.
- Variables: `${Name}` or `${Name:default}` (794 prompts use it, 3,766 variables); 516 `{{x}}` left from older
  formats.
- Most prompts are "Act as a ..." persona prompts for a general chat model. They are prompts a reader pastes, not
  briefs: no locked facts, no record of what is the user's own data.

## Pieces worth noting
1. **Variable detection** (`src/lib/variable-detection.ts`): finds `[[x]]`, `{{x}}`, `[X]`, `{X}`, `<X>`, `%X%`,
   `${x}` in pasted text and offers to turn them into one format with defaults. Useful for Hoola: a prompt she pastes
   from elsewhere has blanks in many shapes; Hoola's brief has no such reader today.
2. **Local quality check** (`packages/prompts.chat/src/quality`): no model - length, gibberish, has role / task /
   constraints / examples, variable count, a 0-1 score with issues. Hoola's Prompt Score already goes further (per
   section, her facts, outcome-checked in P4), so nothing to take except the gibberish test.
3. **Duplicate check** (`src/lib/similarity.ts`): normalise (variables, brackets, punctuation out) then Jaccard words
   + trigram similarity. Hoola's community recipes (P11) have no duplicate check - this is the missing piece.
4. **Model quality gate** (`src/lib/ai/quality-check.prompt.yml`): one cheap call that only delists clear junk
   (gibberish, not an AI instruction), confidence >= 0.85, "when in doubt approve". Matches our owner-review queue;
   could pre-sort it.
5. **Improve prompt** (`improve-prompt.prompt.yml`): rewrites the whole prompt with a model ("Act as..." added,
   similar prompts pasted in). This is the silent rewrite Hoola's plan refuses (her facts can change); not to copy.
6. **Typed builders** (`packages/prompts.chat/src/builder`): chat / image / video / audio prompt objects (camera,
   lens, lighting, shot, genre, tempo...). Same idea as Hoola's anatomy slots; their field lists for video and audio
   are longer and could fill gaps in our video / music slot lists.
7. **Connections / workflows** (`PromptConnection`): prompt A -> prompt B with a label = a chain. Hoola has no chained
   prompts; nearest is a saved prompt.
8. **Classifiers + chains**: decision questions with fixed outcomes, chained by branch. Separate product, not
   prompting.
9. **MCP server**: search_prompts / get_prompt / save_prompt / improve_prompt (+ skills, bots, teams). Hoola could
   offer the same over its own recipes, but no one asked.
10. **The book**: 34 chapters (anatomy, pitfalls, few-shot, chain-of-thought, context and loop engineering,
    agents). Hoola's Learn page (P9) has short lessons from her own prompts; a chapter link per lesson would add depth.

## What Hoola could take (ranked, nothing built)
1. **Import the CC0 library as a "World prompts" shelf**: 3,235 prompts, read-only, searchable, each opened as a
   brief whose `${x}` become blanks (questions), never filled by Hoola. Filter out code-only and jailbreak-style
   rows; score each with Hoola's own checks first. Biggest visible gain, cheapest to build.
2. **Paste reader**: any blank shape in a pasted prompt -> a named blank in the brief (their detector, in Python).
3. **Duplicate check for community recipes** (normalise + Jaccard + trigram) before the owner's review.
4. **Longer video / music slot lists** from their typed builders.
5. **Chained prompts** (output of one feeds the next) - a new feature, only if she wants it.

Not to take: the whole-prompt model rewrite, the social site itself (Hoola is not a prompt social network), the
classifiers / bots / teams products.
