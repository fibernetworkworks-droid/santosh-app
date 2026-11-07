---
name: bd-eval-benchmarks
description: Quality regression evals - public golden sets, scored runs
---
GOAL: "Hoola ab pehle se accha jawab deta hai?" - feel se nahi, SCORE se.
Public datasets se golden set banao, har bade change ke baad wahi suite
phir chalao. Score gira = regression, chhota sa bhi. Yeh skill quality
regression ka meter hai; awesome-public-datasets (79k+ stars, topic-wise
vetted open data) uski eent hain.

THE GOLDEN SET (jawab dataset se copy hote hain, khud se kabhi nahi):
- SQuAD - Wikipedia reading-comprehension QA, 100k+ questions, context
  + sawaal + sahi jawab dataset mein hi likha - QA suite ka material.
- 20 Newsgroups - ~18,000 posts, 20 topics - classification suite.
- IMDb - 50k labelled movie reviews - sentiment suite.
- data.gov.in open APIs (crop prices, rainfall, sarkari stats) -
  Hinglish numeric QA ka material; numbers sarkari, guessed nahi.
- DataChallenges / Economics / Climate rows - jab suite ka topic wahan
  milta hai. Har golden row ke saath source sheet mein hi rehta hai.

THE PIPELINE (sab existing doors):
1. data_fetch(url=open-data API, fields=...) -> ds_id; page-table ho to
   scrape_page; uska apna sheet ho to sheet_read.
2. sheet_create + sheet_append: columns input / expected / kind /
   source. Source = dataset ka naam - traceable golden set.
3. RUN: delegate_task (har worker 5-10 items, capped turns) se answers;
   pure-computation suite seedha pylab se.
4. SCORE: pylab (pandas/numpy, locked sandbox) - exact match, keyword
   hit, numeric tolerance; result table PRINT karo. Score printed
   output se quote hota hai, mental maths se kabhi nahi.
5. THE LEDGER: sheet_append ek row = date / suite / n / score / app
   version. Regression = same suite, score neeche vs pichhli row.

THE LAWS: chhota aur baar-baar (20-50 items) bada aur kabhi-kabhi se
behtar; har bade change ke baad SAME suite; naya capability = naya
suite, purana suite delete nahi (trend hi regression ka proof hai);
suite ki source sheet hi suite ki truth hai.

NEVER: invented golden answers (dataset hi truth hai); pass karne ke
liye answers tune karna (teaching to the test - suite bekaar ho jata
hai); printed output ke bina score bolna; uske private customer rows
ko eval data banana (privacy - eval ka maidan public data hai); ek
suite banakar "quality theek hai" kehna - suite tab tak zinda hai jab
tak har change ke baad chal raha hai.
