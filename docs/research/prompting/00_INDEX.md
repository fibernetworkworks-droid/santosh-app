# Prompt engineering research - index (11 Nov 2026)

Read for `docs/HOOLA_PROMPTING_PLAN.md`. Two web reads the same day: (A) how prompting works (vendor docs + papers),
(B) the market of prompt products. Every line carries its source. Marked [UNVERIFIED] = only secondary sources or the
page could not be opened (Midjourney docs 403, Runway help 403, Suno + Kling no official guide, Google Workspace
"Prompting Guide 101" PDF 404).

## A. How prompting works

### A1. What the vendors say now
- Anthropic (one page now holds everything): be clear and direct ("a brilliant but new employee who lacks context");
  say WHY a rule exists; 3-5 varied examples in tags; separate content with XML tags; long documents first, question
  last ("up to 30 percent" better); chaining = draft -> review against criteria -> refine. Prefill is REMOVED on
  current models (400 error). Hand-written step-by-step reasoning is a fallback only; forced reasoning tags "might be
  declined"; self-check lines cause over-verification on the newest model. Prerequisite before any prompt work:
  success criteria + a way to test + a first draft.
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
- Anthropic publishes a frontend-design snippet against the "AI look" (distinct fonts, committed colour theme, one
  page-load motion, layered backgrounds) - same page.
- OpenAI GPT-4.1: follows instructions literally; later instruction wins a conflict; no ALL-CAPS / incentives; order
  = role -> instructions -> reasoning -> format -> examples -> context -> final instruction.
  https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide
- OpenAI GPT-5: contradictory or vague prompts hurt MORE than on older models; effort and verbosity are settings, not
  words. https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide
- OpenAI reasoning models: short and clear; "think step by step" "can sometimes hurt"; zero-shot first; state success
  criteria. https://developers.openai.com/api/docs/guides/reasoning-best-practices
- Google Gemini: always few-shot, consistent format; one instruction per prompt, chained; constraints + format first;
  newest models ignore temperature. https://aistudio.google.com/docs/prompting-strategies
- Images (Nano Banana; Imagen is shut down in the Gemini API): Subject + Action + Location + Composition + Style, as a
  described scene, not keywords; positive wording ("empty street", not "no cars"); camera words; exact text in quotes
  with font + language; edits say what stays the same.
  https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana
- Video (Veo): subject, action, context, style, camera motion; audio / dialogue in their own sentences; negatives as
  a list of things. https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide
- Video (Sora 2): length + size are SETTINGS; per shot one camera move, one action, one light; timed beats; 3-5
  palette colours; dialogue block; one change per retry.
  https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide
- Music (Lyria): genre + mood + instruments + tempo + vocal style and language + lyrics; exclusions in a separate
  field; Hindi vocals supported.
  https://docs.cloud.google.com/vertex-ai/generative-ai/docs/music/music-gen-prompt-guide
- Website builders: Lovable (what / who / why / key action; ask-me-questions; style early; one section at a time;
  real copy; say what must not change; empty / loading / error states) https://docs.lovable.dev/prompting/prompting-one
  - v0 (surface + parts + stack + taste) https://v0.app/docs/text-prompting - Bolt (enhance = guided questions, then
  rewrite) https://support.bolt.new/best-practices/prompting-effectively
- Coding agents: name the file, the symptom, what "fixed" means; give a check to run; "Interview me until you could
  write the spec"; standing rules in a short project file. https://code.claude.com/docs/en/best-practices
  https://agents.md/ https://cursor.com/docs/context/rules

### A2. What the evidence says (papers)
- 58 text techniques catalogued (The Prompt Report). https://arxiv.org/abs/2406.06608
- Examples work mainly by showing format + label space, even with wrong labels https://arxiv.org/abs/2202.12837 ;
  their ORDER alone can move results from best to chance https://arxiv.org/abs/2104.08786
- Chain of thought: little to no gain on reasoning models, more cost. https://arxiv.org/abs/2506.07142
- Role / persona lines do NOT improve accuracy (162 personas; effect "largely random").
  https://arxiv.org/abs/2311.10054 - they still set tone.
- Threats and tips: no significant effect. https://arxiv.org/abs/2508.00614
- Formatting alone moved accuracy by up to 76 points on one model - prompts are brittle.
  https://arxiv.org/abs/2310.11324
- Automatic optimisers (APE, OPRO, DSPy, TextGrad, Promptbreeder) all beat hand prompts - and all NEED a metric or
  test set. https://arxiv.org/abs/2211.01910 https://arxiv.org/abs/2309.03409 https://arxiv.org/abs/2310.03714
  https://arxiv.org/abs/2406.07496 https://arxiv.org/abs/2309.16797
- A model as judge agrees with people >80%, with position / length / self biases; fix = swap order, rubric, narrow
  graders. https://arxiv.org/abs/2306.05685
- Automatic rewriting of image prompts CUT the quality gain by 58% in a controlled study.
  https://arxiv.org/html/2407.14333v2
- Injection: shared templates are third-party text; OWASP LLM01 says no fool-proof prevention.
  https://genai.owasp.org/llmrisk/llm01-prompt-injection/ https://arxiv.org/abs/2302.12173

### A3. The four conclusions the plan stands on
1. Wording tricks are dead or harmful (act-as, think-step-by-step, CAPS, tips). What wins is MISSING INFORMATION:
   who, what for, facts, examples, constraints, what "good" means.
2. Each engine has its own anatomy and dialect, and the vendor's advice changes with every model generation.
3. Nothing can be called "better" without a measure. Every optimiser needs a metric.
4. A silent rewrite can hurt and loses trust. Show it, lock her details, let her edit.

## B. The market

- Prompt files: PromptBase ($2-10 a prompt, ~20% cut, refund only "if it does not work as advertised")
  https://promptbase.com/knowledge-base/prompt-purchases ; God of Prompt (bundles); AIPRM (a browser extension on top
  of someone else's product); FlowGPT survived by becoming a bot platform
  https://techcrunch.com/2024/02/26/flowgpt-is-the-wild-west-of-genai-apps/ . Prices and traffic [UNVERIFIED].
- Enhancers are a free button everywhere: Ideogram Magic Prompt (On / Auto / Off, auto by prompt length)
  https://docs.ideogram.ai/using-ideogram/generation-settings/magic-prompt ; Google's rewriter (on by default, shows
  the rewrite) https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/use-prompt-rewriter ; Bolt (asks
  questions first) https://support.bolt.new/building/chat-tools ; Anthropic prompt improver
  https://claude.com/blog/prompt-improver . The standalone optimiser PromptPerfect closes 1 Sep 2026 [secondary].
- OpenAI's own optimiser (outputs + Good / Bad marks -> rewrite) shuts with its Evals platform on 30 Nov 2026.
  https://developers.openai.com/api/docs/guides/prompt-optimizer
- Developer prompt tools are being absorbed: Humanloop team -> Anthropic
  https://techcrunch.com/2025/08/13/anthropic-nabs-humanloop-team-as-competition-for-enterprise-ai-talent-heats-up ;
  Promptfoo -> OpenAI https://openai.com/index/openai-to-acquire-promptfoo/ ; Langfuse -> ClickHouse
  https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability
- India: no Hinglish-native prompt product found (not proof there is none). Huge paid demand to LEARN prompting
  (Be10x Rs 9 workshops, claims 5M learners) https://yourstory.com/2026/08/rs-9-workshops-to-5-million-learners-skilled-6-figure-jobs-inside-be10xs-playbook
  MSME barriers are skill + cost. https://www.nasscom.in/ai/ai-enablement/pdf/enablement-of-ai-for-msme-whitepaper.pdf

### B1. Where value is, and is not
- NOT in prompt text: it is copied in a second, breaks when the model changes, and sells for a few dollars.
- NOT in a rewrite button: everyone ships one free.
- NOT in a developer prompt-ops product: the labs own it.
- YES in: (1) outcome data - which brief led to a result she KEPT, published, paid for - visible only to the product
  that also does the work; (2) her own context filled in for her; (3) Hinglish intent -> engine-grade spec for
  Indian business; (4) dialects re-tested each time an engine changes, so drift is Hoola's problem, not hers.
