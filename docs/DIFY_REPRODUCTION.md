# Reproduce the Gemini and Claude Dify Chatflows

**Status:** Both workflows have been exported and examined. `dify_exports/` now contains GitHub-safe `.ifpkg` packages with valid SHA-256 manifests. The original uploaded exports were unmodified; the published copies have **only** the original workspace-specific knowledge-base ID removed. You must re-link the dataset after import.

## 1. What the workflow packages contain

| Setting | Gemini Chatflow | Claude Chatflow |
| --- | --- | --- |
| App name | AllSales CRM Sales Policy Assistant | AllSales CRM - Claude |
| Package | `dify_exports/gemini-chatflow.ifpkg` | `dify_exports/claude-chatflow.ifpkg` |
| Dify export format | `dify.app`, format_version 2 | `dify.app`, format_version 2 |
| LLM provider | `langgenius/gemini/google` | `langgenius/anthropic/anthropic` |
| LLM name | `gemini-3.5-flash-lite` | `claude-sonnet-5-5` |
| Generation configuration | `thinking_level: Low` | No explicit completion parameters |
| Workflow graph | Start → Knowledge Retrieval → LLM → Answer | Identical |
| Start node query | `sys.query` | Identical |
| LLM retrieved context | Knowledge Retrieval `result` (enabled) | Identical |
| User prompt | `{{#sys.query#}}` | Identical |
| Final answer | LLM `text` | Identical |
| Source citations | Retrieval resources enabled | Identical |

The system prompt is exactly the same in both exported workflows. It instructs the assistant to answer only from retrieved handbook content, state exact thresholds and deadlines, cite a handbook section when available, and abstain rather than invent an answer. Both exported workflows contain the full prompt in their LLM nodes.

## 2. Retrieval configuration actually stored in the exports

- Retrieval mode: `multiple` (multi-path retrieval).
- Weighted ranking: semantic/vector **0.5** and keyword **0.5**.
- Top K: **10**.
- Score threshold: **not configured** (`null`).
- Additional reranking model: **disabled** (`reranking_enable: false`).
- Exported embedding model reference: `gemini-embedding-2-preview` via `langgenius/gemini/google`.
- A reranking model name (`qwen3-rerank`) is listed in config but reranking is **disabled**; do not claim the reranker ran.
- Both exports have the same settings. The dataset ID is intentionally blank in these public packages.

**Not in the `.ifpkg` exports:** the knowledge-base content/index, exact indexing strategy/version, chunk configuration, embedding artifacts, document permissions, provider billing arrangements, and proof of which draft version was published. Earlier development screenshots show the knowledge document in Dify using **parent-child / paragraph** chunking, but a fresh workspace's settings must be confirmed manually; do not claim exact end-to-end reproduction from the exports alone.

## 3. Import into another Dify workspace

1. In Dify, configure the Gemini and Anthropic model-provider plugins and credentials within **Settings → Model Provider**. The exported packages name the providers but do not carry credentials. Supported model names may differ as providers change; document substitutions.
2. In **Knowledge**, create a new knowledge base and upload `knowledge/allsales_sales_policy_synthetic.md` (synthetic v1.0). Choose parent-child paragraph chunking if available; record the exact chosen chunk and embedding options and finish indexing.
3. From Dify **Studio**, import each `.ifpkg` file from `dify_exports/`. If your Dify release labels this action differently, follow its import-app flow. The packages are not direct Python scripts.
4. Open each app's **Knowledge Retrieval** node, select the newly indexed knowledge base, and confirm the semantic/keyword weights (0.5/0.5), Top K (10), score threshold (off), and no extra reranking. **The public files intentionally have no dataset ID.**
5. Confirm that the LLM context is Knowledge Retrieval `result`, and that the prompt includes the context token and the user question. Check model names (Flash-Lite / Sonnet) and the Answer node's LLM `text` mapping.
6. Test the app in Dify Preview. Example: **“What is the follow-up deadline for a lead scoring 62?”** Expected answer: Priority B, first personalized contact within **three business days** after qualification.
7. Publish each chatflow, create a separate **Dify app API key** for each, then set `DIFY_GEMINI_API_KEY` and `DIFY_CLAUDE_API_KEY` in your *local* `.env`. These are different from provider API keys. Never commit them.
8. Start FastAPI and Streamlit per the repository README. Verify one known question per model. This is sufficient for an installation smoke test; do not rerun all 34 paid evaluation requests.

## 4. Reproduction limitations and comparison fairness

The successful test results in `data/evaluation_34_reviewed.csv` came from the owner's existing Dify workspace. The imported public packages have **not** been live-tested in a different Dify workspace, and knowledge retrieval is external to the package. The evaluated models and prompt/retrieval configurations are consistent with the exports, but export alone cannot independently prove the historical published workflow revision. Differences in indexing or provider-model versions may change results.

Do not publish original app keys, provider credentials, private environment files, or real customers' data. This project uses a **fictional sales-policy handbook** and is suitable only as a local learning/portfolio prototype.
