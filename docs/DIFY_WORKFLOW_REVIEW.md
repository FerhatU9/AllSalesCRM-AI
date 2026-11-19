# Dify workflow export review

## Scope

Reviewed the two `.ifpkg` files uploaded from Dify Studio (Gemini and Claude), extracted `app.yaml` and `manifest.yaml` from each ZIP package, validated the SHA-256 manifests, and compared graph nodes, model configuration, retrieval settings, system prompts and Answer mappings.

## Verified

- Both original exports are genuine, structurally consistent `dify.app` format v2 packages, each containing `manifest.yaml` and `app.yaml` with matching recorded file hash and size.
- Each app contains exactly four connected workflow nodes: **User Input → Knowledge Retrieval → LLM → Answer**.
- Gemini uses `gemini-3.5-flash-lite` with `thinking_level: Low`; Claude uses `claude-sonnet-5-5`.
- Both use **the same system prompt**, user question selector, linked handbook dataset reference in the original exports, retriever mode, 0.5/0.5 keyword/semantic weighting, Top K 10, disabled rerank, and the same Answer mapping.
- Both public packages contain no environment/conversation variables, no embedded API credentials, and no original workspace-specific knowledge-base ID. Their manifests were regenerated and revalidated.
- The exported `retriever_resource` feature is enabled for both apps. A document name in the Streamlit API response is a **document label**, not a verified passage-level citation.

## Not verified

- The original source files' embedded knowledge-base index/contents (Dify does not include those in app exports).
- Whether the exported draft matches the historical *published* version at the exact time of evaluation.
- Successful fresh-workspace import, knowledge-relink, and live query using these public sanitized packages.
- A live failure-triggered model fallback; only the offline fallback suite has passed.
- Public deployment security: no user login, roles, real-company CRM integration or tenant isolation.

## Public-export modification

The original files were preserved untouched outside the repository. To avoid publishing a workspace-specific knowledge-base identifier, the public `.ifpkg` files set `dataset_ids: []` on the retrieval node. All other workflow YAML bytes were preserved. `manifest.yaml` hashes and sizes were updated accordingly. After import, **rebind the synthetic handbook knowledge base** in both nodes before attempting queries.

**Finding:** Workflow-export evidence is now sufficient for a *documented local prototype*, but not proof of independently reproduced or production-ready deployment.
