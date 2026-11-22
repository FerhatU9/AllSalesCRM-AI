"""AllSales CRM local development UI. Routes API requests through FastAPI.

DO NOT publish this UI to the internet until production authentication,
rate limits, tenant isolation, and abuse controls are implemented.
"""
import os
import uuid
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="AllSales CRM — Development", page_icon="📘", layout="centered")

if os.getenv("ALLSALES_ENV", "").strip().lower() != "local":
    st.error("Public deployment is disabled until secure user authentication and access control are implemented.")
    st.stop()

url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
app_token = os.getenv("API_APP_TOKEN", "")
if not app_token:
    st.error("API_APP_TOKEN missing in local .env")
    st.stop()
headers = {"X-API-Key": app_token}

with st.sidebar:
    workspace = st.radio("Workspace", ["Policy assistant", "Lead qualification"], index=0)

if workspace == "Lead qualification":
    from allsales.lead_ui import render_lead_form
    render_lead_form(api_url=url, headers=headers)
    st.stop()

st.title("AllSales CRM | Sales Policy Assistant")
st.caption("Development prototype • synthetic handbook • Select Gemini or Claude")

try:
    mr = requests.get(f"{url}/v1/models", headers=headers, timeout=5)
    mr.raise_for_status()
    models = mr.json().get("models", [])
except (requests.RequestException, ValueError):
    st.error("Local API is unavailable. Start FastAPI in the other PowerShell window.")
    st.stop()

if not models:
    st.error("No Dify model app configured yet. Add DIFY_GEMINI_API_KEY to .env.")
    st.stop()

if "messages_by_model" not in st.session_state:
    st.session_state.messages_by_model = {"gemini": [], "claude": []}
if "conversations_by_model" not in st.session_state:
    st.session_state.conversations_by_model = {"gemini": "", "claude": ""}
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

with st.sidebar:
    st.header("Development controls")
    selected = st.selectbox("AI model", options=models, index=0)
    if st.button("Start New Chat", use_container_width=True):
        st.session_state.messages_by_model[selected] = []
        st.session_state.conversations_by_model[selected] = ""
        st.rerun()
    st.caption("This is a local test UI, not a public production deployment.")
    st.caption("Model availability means configured, not guaranteed operational.")
    allow_fallback = st.checkbox(
        "Use backup model during temporary outages",
        value=False,
        disabled=len(models) < 2,
        help="Opt-in only. Your question may be sent to the other provider. "
             "Only transient service errors trigger fallback, not missing policy knowledge.",
    )
    if allow_fallback:
        st.caption("Fallback answers use a NEW conversation in the backup Dify app. "
                   "Follow-up questions in the selected model do not inherit that answer.")

history = st.session_state.messages_by_model[selected]
for item in history:
    with st.chat_message(item["role"]):
        if item.get("error"):
            st.error(item["content"])
        else:
            st.write(item["content"])
        if item.get("fallback_model"):
            st.info(f"Answered by {item['fallback_model'].title()} (temporary fallback, separate conversation)")
        if item.get("sources"):
            st.caption("Source document labels: " + ", ".join(item["sources"]))

question = st.chat_input("Ask about the AllSales CRM policy")
if question:
    history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner(f"Asking {selected} via Dify..."):
            try:
                resp = requests.post(
                    f"{url}/v1/chat", headers=headers,
                    json={"question": question, "user_id": st.session_state.session_id,
                          "conversation_id": st.session_state.conversations_by_model[selected],
                          "model": selected, "allow_fallback": allow_fallback}, timeout=110,
                )
                if not resp.ok:
                    try:
                        detail = resp.json().get("detail", "Request failed")
                    except ValueError:
                        detail = "Request failed"
                    st.error(f"Request failed ({resp.status_code}): {detail}")
                else:
                    data = resp.json()
                    actual_model = data.get("model", selected)
                    is_fallback = data.get("fallback_used", False) and actual_model != selected
                    if not is_fallback:
                        st.session_state.conversations_by_model[selected] = data.get("conversation_id", "")
                    else:
                        # Don't mix a Claude conversation ID into Gemini history (or vice versa).
                        st.info(f"Answered by {actual_model.title()} (temporary fallback, separate conversation). "
                                "This answer is not part of the selected model's conversation history.")
                    st.write(data["answer"])
                    sources = data.get("source_documents", [])
                    if sources:
                        st.caption("Source document labels: " + ", ".join(sources))
                    history.append({"role": "assistant", "content": data["answer"],
                                    "sources": sources,
                                    "fallback_model": actual_model if is_fallback else None})
            except (requests.RequestException, ValueError):
                st.error("Couldn't contact the local API. Verify it is running.")
