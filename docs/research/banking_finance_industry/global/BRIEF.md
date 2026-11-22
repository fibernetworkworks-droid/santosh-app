# Research brief: every finance & banking job an AI employee could do, worldwide

## What this is for
Hoola is an AI-coworker product. Users "hire" AI employees (e.g. "Money Safety Assistant", "Payroll officer").
We are building the Finance & Banking department and need the COMPLETE list of possible AI employees,
for users in EVERY country (not India only). An "AI employee" = a role (bundle of jobs-to-be-done) that an
AI agent with tools (read documents, calculate, draft, check, track deadlines, call official APIs, prepare
papers for a human to sign) can do for a person, a small business, a professional firm, or a financial
institution.

## Hard limits (shape every role)
- The AI never moves money, places/cancels an order, approves/declines a loan/claim/account/KYC, freezes an
  account, files a regulatory report AS the institution, signs an audit opinion/valuation/financial statement,
  or gives personalised regulated advice as if licensed. It PREPARES, CHECKS, EXPLAINS, CALCULATES, DRAFTS,
  TRACKS and REMINDS; a named human decides; money moves only on the user's own tap through official rails.
- Never asks for PIN / OTP / CVV / card numbers / passwords.
- Mark each role with a tier: A = admin/prepare (safe), B = assist a named licensed/accountable person,
  C = reserved for humans (list these separately as "never an AI employee" with the reason).

## What to find (deep, sourced)
For your assigned segment, worldwide:
1. Every human job/role that exists (use occupation taxonomies: O*NET / US BLS OOH, EU ESCO, ILO ISCO-08,
   UK SOC, Australia ANZSCO, industry job boards and bank org charts) and the TASKS inside each.
2. Group those tasks into AI-employee roles (one role = a coherent job a customer would hire).
3. For each role:
   - Name (plain English) and one line on what it does
   - Who hires it (consumer / sole trader / SME / accounting-or-advisory firm / bank / NBFC-lender /
     fintech / broker / asset manager / insurer-adjacent / government / NGO)
   - 6-12 concrete jobs-to-be-done (tasks) it performs
   - Tier A/B (and what stays with the human: who decides / signs)
   - Data and rails it needs (documents, open-banking/AA APIs, broker APIs, credit bureau, payment
     gateways, tax portals, SWIFT/ISO 20022, etc.)
   - How it differs by country/region: name the key rules/regulators/systems per region
     (US, EU/EEA, UK, Gulf/GCC, India, SE Asia/Singapore, China/HK, Japan/Korea, Australia/NZ, Africa
     (Nigeria/Kenya/South Africa), Latin America (Brazil Pix, Mexico), Canada). Say "check" when unsure.
   - Existing AI products/companies already doing it (evidence that it is doable), with links
4. Pains with evidence (surveys, regulator complaint statistics, industry reports) that show demand.
5. Sources: real URLs you actually opened. Mark anything from memory as "from memory - verify".

## Output
Write your full result as Markdown to the file path given in your task (use the Write tool), aiming for
completeness over brevity (typically 40-120 roles for a big segment, fewer for a small one; do not pad).
Number roles within your segment. End with: "Never an AI employee (tier C) in this segment" and "Top 10
roles to build first and why". Then reply to me with only: the file path, the role count, and 5 lines on
the most important findings.
