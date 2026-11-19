# Evaluation methodology

The original golden dataset contains 17 questions with expected answers. The saved historical results showed 13 exact passes, 2 partial-but-core-correct answers, and 2 incorrect answers. Therefore core-answer correctness was **15/17 (88.2%)**. LLM-as-judge scores averaged **0.941** for groundedness and **0.853** for context relevance. These are **historical** results, not performance after the latest retrieval changes.

## Required next experiment

Run all 17 questions on the current Dify configuration **without modifying prompts or knowledge midway**. Capture actual answers, error codes, response time, and document labels. Review each actual answer against `data/golden_17_questions.csv`. Use Pass / Partial / Incorrect with clearly stated criteria. If it fails due to high demand, record an API failure rather than counting it as an answer-quality success.

For retrieval metrics, record whether the expected parent/child chunk appears in top-1/top-3/top-5 as a separate measurement. Note that the Dify response's source document name alone does **not** identify the exact chunk. Use Dify retrieval traces/screenshots or dedicated retrieval tests for chunk-level metrics. Don't infer citations from a source label.

## Known targeted cases

- Score 48 Priority C: correct chunk ranked first; retrieval score 0.72.
- Score 62 Priority B: correct chunk ranked first; retrieval score 0.66.
- Priority A score 75–100: correct chunk ranked first; retrieval score 0.68.
- Discount 15%: target Parent-Chunk-26 Child C-2 found in a more direct search but scored 0.18, below unrelated priority rules.
- Mandatory CRM fields: matching Parent-Chunk-08 found below unrelated passages in one test.

Comparisons should use the same question set, model, retrieval settings, judgment rubric, and conditions for both versions whenever possible.
