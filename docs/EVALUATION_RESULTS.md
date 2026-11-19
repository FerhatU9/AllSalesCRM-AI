# Dual-model RAG evaluation — reviewed 18 November 2026

This report analyses **17 curated synthetic-handbook questions per model**, captured via the Dify service from an existing development workspace. It is **not a benchmark on unseen user traffic** or proof of production reliability.

| Metric | Gemini Flash-Lite route | Claude Sonnet 5.5 route |
| --- | ---: | ---: |
| Final recorded successful answers | 17 / 17 | 17 / 17 |
| Correct essential policy answer (manual) | 17 / 17 | 17 / 17 |
| Full expected-answer completeness | 14 / 17 | 17 / 17 |
| Wrong numbered section reference | 1 | 2 |
| Mean latency of successful recorded response | 8.84 s | 4.30 s |
| Median latency | 9.54 s | 4.17 s |
| Reported tokens, sum | 9,783 | 16,167 |

## Scoring protocol
- **PASS**: answer supplies the essential expected policy facts.
- **PARTIAL**: the essential answer is right but expected explanatory or operational details are missing.
- Wrong section numbers are recorded separately, even when the core answer is correct.
- Empty or failing API results are not graded as answers.
- Review uses the policy handbook in `knowledge/allsales_sales_policy_synthetic.md` (v1.0) and the question expectations from `data/golden_17_questions.csv`. This is a **manual comparison**, not a trained evaluator score.

## Observed omissions and citation issues
- Gemini Q09: correct score (70) and Priority B, missing the three-business-day action deadline.
- Gemini Q10: correct Enterprise Sales routing for a 250-person UK business, missing territory-owner detail and separate priority assessment.
- Gemini Q15: correct market-eligibility review, missing that it applies regardless of lead score.
- Gemini Q08 and Claude Q08: correct Priority C handling but referenced Section 3 instead of Section 4 for follow-up rules.
- Claude Q02: correctly listed preferred industries, but attributed company-fit scoring to Section 5; scoring is in Section 3.

## Reliability interpretation
All 34 **final stored results** have status `ok`, *after using a resumable script and manual retries*. This is **not** 100% first-attempt availability. The evaluation previously experienced provider overload (including Gemini Q15) and an earlier run returned multiple errors before the experiment was resumed. Do not claim the model providers were failure-free.

## Fair-comparison limitations
- Answers were collected across more than one time window and provider conditions can change.
- Source document labels are not passage-level evidence or retrieval metrics.
- The exact Dify workflow export, prompt version, and retrieval parameters are not in the ZIP; comparison settings cannot yet be independently verified from the repo alone.
- Per-model token reporting may differ and API costs were not calculated from invoices; do not equate fewer tokens with lower cost.
- A 17-question scripted set is limited. Add novel, adversarial, consent, boundary, and abstention cases before product release.

For the answer-by-answer rows, see [`data/evaluation_34_reviewed.csv`](../data/evaluation_34_reviewed.csv). Local raw intermediate results remain in `results/` (gitignored).
