# Dify Chatflow exports — public, sanitized versions

This directory contains two **real exports from the existing working AllSales CRM Dify applications**. The two public packages were derived from the uploaded `.ifpkg` files. Their only workflow-data change is clearing the original Dify-workspace knowledge-base ID (`dataset_ids: []`) so the public repository does not publish internal workspace identifiers. The packages have regenerated SHA-256 manifests. **Do not confuse these sanitized public copies with byte-for-byte snapshots of the original exports.**

| File | Dify model | What to do after importing |
| --- | --- | --- |
| `gemini-chatflow.ifpkg` | `gemini-3.5-flash-lite` | Link the newly created synthetic handbook dataset |
| `claude-chatflow.ifpkg` | `claude-sonnet-5-5` | Link that same dataset |

The two exports have identical user-input → knowledge-retrieval → LLM → answer topology, the same policy instructions, and the same exported retrieval settings. Provider credentials, Dify app API keys, and the indexed knowledge base are **not** included.

Import the packages via Dify Studio; configure the model-provider plugins and their credentials **inside Dify**. Upload `../knowledge/allsales_sales_policy_synthetic.md` to a fresh Dify knowledge base and link it in each Knowledge Retrieval node before publishing. See `../docs/DIFY_REPRODUCTION.md` for the actual settings captured from the exports, and for the indexing information that cannot be recovered from app exports.

These packages were **statically validated**, but were not imported into a second Dify workspace in this audit. If Dify asks to upgrade or repair a plugin/model setting, record the change before comparing model results.
