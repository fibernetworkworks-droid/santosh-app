---
name: finishing-a-branch
description: The work is done - verify, then hand it over the Hoola way
when: wrap up, finish, ready for review, open the pull request, ship it
---
1. VERIFY: the whole suite (and the build / linter the repo uses), run fresh now. Red = report the failures and stop;
   nothing is handed over red.
2. LOOK: show_diff - nothing stray (debug prints, scratch files, unrelated edits).
3. HAND OVER: done with explain (what changed and that it was proven), test_plan (each command and its result), risk
   (what could break, what was not checked), pr_title / pr_summary. Hoola opens the pull request; merging is always HER
   tap - never merge, push or delete branches yourself.
