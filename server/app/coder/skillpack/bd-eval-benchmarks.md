---
name: bd-eval-benchmarks
description: Quality regression evals - public golden sets, scored runs
when_to_use: benchmark models, compare two models fairly, evaluate answer quality, regression test the AI, golden set, score runs, is Hoola better now
---
GOAL: "Does Hoola answer better now than before?" - not by feel, by SCORE.
Build a golden set from public datasets and run the same suite again after
every big change. A lower score = a regression, however small. This skill
is the meter for quality regression; awesome-public-datasets (79k+ stars,
vetted open data by topic) is its building material.

THE GOLDEN SET (answers are copied from the dataset, never made up):
- SQuAD - Wikipedia reading-comprehension QA, 100k+ questions; context +
  question + right answer are written in the dataset itself - material
  for the QA suite.
- 20 Newsgroups - ~18,000 posts, 20 topics - the classification suite.
- IMDb - 50k labelled movie reviews - the sentiment suite.
- data.gov.in open APIs (crop prices, rainfall, government statistics) -
  material for numeric QA; the numbers are official, not guessed.
- DataChallenges / Economics / Climate rows - when the suite's topic is
  found there. The source stays in the sheet beside every golden row.

THE PIPELINE (all existing doors):
1. data_fetch(url=open-data API, fields=...) -> ds_id; for a table on a
   page use scrape_page; for the user's own sheet use sheet_read.
2. sheet_create + sheet_append: columns input / expected / kind /
   source. Source = the dataset's name - a traceable golden set.
3. RUN: answers through delegate_task (5-10 items per worker, capped
   turns); a pure-computation suite directly in pylab.
4. SCORE: pylab (pandas / numpy, locked sandbox) - exact match, keyword
   hit, numeric tolerance; PRINT the result table. A score is quoted from
   printed output, never from mental maths.
5. THE LEDGER: one sheet_append row = date / suite / n / score / app
   version. Regression = same suite, score lower than the previous row.

THE LAWS: small and often (20-50 items) beats big and rarely; the SAME
suite after every big change; a new capability = a new suite, the old
suite is not deleted (the trend is the proof of a regression); the
suite's source sheet is the suite's truth.

NEVER: invented golden answers (the dataset is the truth); tune answers
in order to pass (teaching to the test - the suite becomes useless);
state a score without printed output; turn the user's
private customer rows into eval data (privacy - evals run on public data);
build one suite and say "quality is fine" - a suite is alive only while it runs after
every change.

ALSO ASKED AS (Hinglish asks this skill answers): quality regression ka eval
suite banao, do model compare karo, Hoola pehle se behtar hai kya
