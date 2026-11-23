# Claude + Gemini configuration guide — for fresh installations

**Status:** Claude and Gemini were tested successfully in the development workspace. This guide describes how to set them up in a new workspace; do not re-create or repurchase keys for the currently working apps.


The goal is to compare **two AI models** while keeping retrieval, handbook, and prompts the same.
We use Dify model-provider integration first. A direct Anthropic Python SDK adapter is planned later,
not silently treated as completed.

## 1. Anthropic Console (Claude account and billing)
1. Sign in to https://platform.claude.com/ and create an organization.
2. In billing, check any available trial credits, then consider a small prepaid balance.
3. Disable automatic top-ups if you want manual cost control. Set alerts/limits where available.
4. Create an API key for development and save it securely. Do NOT put it in Git or chat messages.
   A Claude chat subscription and Anthropic API billing are separate.

## 2. Configure Dify provider
1. Sign in to your existing Dify workspace.
2. Open **Plugins / Marketplace** (navigation can change), install the official **Anthropic** model-provider plugin.
   Official listing: https://marketplace.dify.ai/plugin/langgenius/anthropic
3. Open **Settings → Model Provider → Anthropic** and enter the Anthropic API key into Dify's provider credential form.
4. Confirm Claude model availability. Start with Claude Sonnet 5.5 if present (`claude-sonnet-5-5`),
   or choose another actually enabled model displayed in your workspace; record its exact model ID.

## 3. Create an equivalent Claude workflow
1. **Duplicate** the Gemini-based AllSales CRM Dify Chatflow. Do not modify the working original.
2. Name duplicate `AllSales CRM - Claude` and keep **the identical** knowledge base,
   retrieval settings, system prompt and Answer node wiring.
3. Change ONLY the LLM provider and model to Claude (and equivalent decoding settings when supported).
4. Publish the Claude Chatflow.
5. In its **Access Point → API** area create a new Dify APP API key.
6. Add that Dify APP key to `DIFY_CLAUDE_API_KEY` in the local `.env` file.
   This is NOT your direct Anthropic key. The direct Anthropic key stays in Dify's provider settings.

## 4. Test model selection locally
Run existing tests, then start FastAPI and Streamlit per README.
Both model choices should now appear in the Streamlit sidebar.
Ask the same policy question with each model in independent conversations.
The demo only treats a model as *configured* when an app key exists; actual operational status requires a live test.

## 5. Run a controlled A/B test
To preview without API costs:

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_models --limit 3
```

To send THREE questions to BOTH provider routes (6 real Dify requests, may spend credits):

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_models --live --limit 3
```

Only after those succeed, run 17 questions per provider (34 real Dify calls):

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_models --live --limit 17
```

The CSV contains answers, latency, token counts (when provided), provider errors, and document labels.
**It does not automatically score correctness.** Manually compare the responses to handbook evidence.
The LLM choice must not accidentally change retrieval configuration. Document prompt/model versions.

## Safety and cost
- API credits are paid usage; never run the 34 calls by default.
- Do not send real customer data to either model at this stage.
- Never expose provider credentials to Streamlit clients or GitHub.
- Do not auto-fallback silently for high-impact policy answers: record errors, apply constraints,
  and allow fallback only when permitted by business privacy and source-evidence rules.
