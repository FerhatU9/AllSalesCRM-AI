# AllSales CRM v0.8 — Install on the existing v0.6/v0.7 project

This patch updates the code and docs only. It does **not** contain `.env`, Dify API keys, `.venv` or any runtime credentials.

1. In VS Code, use the terminal for your existing project (the directory containing `app.py`).
2. Make optional safety copies of your current UI and API files:

```powershell
Copy-Item app.py app_before_v08_backup.py
Copy-Item backend\api.py backend\api_before_v08_backup.py
```

3. Download `AllSalesCRM_Lead_Qualification_v0_8_PATCH.zip` to Windows Downloads and run:

```powershell
Expand-Archive -Path "$HOME\Downloads\AllSalesCRM_Lead_Qualification_v0_8_PATCH.zip" -DestinationPath . -Force
```

4. Verify without making any API calls:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.demo_lead_decisions
```

Expected in a matching v0.7 local project: **66 passed**, and a sample case returning 85/100, Priority A, SMB Sales Team.

5. Stop your old FastAPI and Streamlit processes in their existing terminals (Ctrl+C). Start FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

In another terminal start Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

6. Open `http://localhost:8501` → sidebar **Workspace** → **Lead qualification**. Keep the provided sample data, click **Evaluate fictional lead**, and check the score/route. Try removing the country to confirm that it switches to Incomplete with no tier.

7. The optional **Gemini/Claude policy explanation** makes a Dify request only when you explicitly click its button. If you don't click, lead qualification consumes **zero LLM credits**.

If the two servers were already running and refuse to restart because ports are in use, stop the old processes instead of changing ports or API keys. For a clean standalone setup, extract the full v0.8 GitHub ZIP to a **new folder**, keep your own `.env` in the original folder, and follow its README setup guide.

**Don't upload `.env` or customer data to GitHub.**
