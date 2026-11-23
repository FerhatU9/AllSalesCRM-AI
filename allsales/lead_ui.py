"""Streamlit view for the fictional lead-scoring decision workflow."""
from __future__ import annotations

import requests
import streamlit as st
import uuid
from allsales.lead_qualification import COUNTRY_OPTIONS
from allsales.lead_explanation import build_explanation_prompt


def render_lead_form(api_url: str, headers: dict[str, str]) -> None:
    st.title("AllSales CRM | Lead Qualification")
    st.caption("Fictional leads only • Rules-based decision support • No automatic CRM updates")
    st.info("This form uses synthetic sample data. Do not enter real contact details. "
            "Unlike policy chat, it does not call Gemini or Claude or consume model credits.")

    with st.form("lead_review_form"):
        st.subheader("1. CRM lead record")
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Company name *", value="ExampleTech Ltd")
            country = st.selectbox("Country *", COUNTRY_OPTIONS, index=COUNTRY_OPTIONS.index("Netherlands"))
            employees = st.number_input("Employees *", min_value=0, max_value=1000000, value=120, step=1)
            employee_unknown = st.checkbox("Employee count not provided")
            industry = st.selectbox("Industry *", ["SaaS", "Professional services", "Retail", "Other", "Not provided"])
            contact = st.text_input("Contact name *", value="Demo Buyer")
        with c2:
            email = st.text_input("Business email *", value="demo@example.com")
            use_case = st.text_input("Stated use case *", value="Manage incoming sales leads")
            lead_source = st.text_input("Lead source *", value="Website")
            consent = st.selectbox("Marketing consent status *", ["Opted In", "Opted Out", "Unknown", "Missing"])
            owner = st.text_input("Assigned owner *", value="Demo Sales Rep")

        st.subheader("2. Scoring evidence")
        c1, c2 = st.columns(2)
        with c1:
            days = st.number_input("Days until purchase decision", min_value=0, max_value=3650, value=20)
            days_unknown = st.checkbox("Decision timing unknown")
            authority = st.selectbox("Decision authority", ["final", "influencer", "none", "unknown"],
                                     format_func=lambda v: {
                                         "final": "Controls budget / final approval",
                                         "influencer": "Influences, cannot approve",
                                         "none": "Confirmed no decision authority",
                                         "unknown": "Unknown (ask manager)",
                                     }[v])
        with c2:
            engagement = st.selectbox("Engagement", ["none", "demo_booked", "email_replied", "unknown"],
                                      format_func=lambda v: {
                                          "none": "No demo or email response",
                                          "demo_booked": "Demonstration booked",
                                          "email_replied": "Replied to outreach email",
                                          "unknown": "Unknown",
                                      }[v])
            discount = st.number_input("Proposed discount (%)", min_value=0.0, max_value=100.0,
                                       value=0.0, step=1.0)
            custom_terms = st.checkbox("Customer requests custom contract terms")

        st.subheader("3. Special escalations")
        a, b = st.columns(2)
        with a:
            security = st.checkbox("Suspected security incident")
        with b:
            outage = st.checkbox("Existing customer reports urgent service outage")
        submitted = st.form_submit_button("Evaluate fictional lead", type="primary", use_container_width=True)

    if submitted:
        st.session_state.pop("lead_ai_explanation", None)
        payload = {
            "company_name": company, "country": "" if country == "Not provided" else country,
            "employee_count": None if employee_unknown else int(employees),
            "industry": "" if industry == "Not provided" else industry,
            "contact_name": contact, "business_email": email,
            "stated_use_case": use_case, "lead_source": lead_source,
            "consent_status": consent, "assigned_owner": owner,
            "decision_days": None if days_unknown else int(days),
            "decision_authority": authority, "engagement": engagement,
            "proposed_discount_pct": float(discount), "custom_contract_terms": custom_terms,
            "suspected_security_incident": security, "urgent_service_outage": outage,
        }
        try:
            with st.spinner("Applying the synthetic handbook rules..."):
                r = requests.post(f"{api_url}/v1/leads/evaluate", headers=headers,
                                  json=payload, timeout=12)
            if not r.ok:
                st.error(f"Evaluation failed (HTTP {r.status_code}). Check that FastAPI is running and updated.")
            else:
                st.session_state["lead_decision"] = r.json()
        except (requests.RequestException, ValueError):
            st.error("Cannot reach the local FastAPI service. Verify port 8000 and restart the backend.")

    decision = st.session_state.get("lead_decision")
    if not decision:
        return
    st.divider()
    st.subheader("Decision report")
    if decision["qualification_status"] != "Qualified":
        st.warning(f"{decision['qualification_status']}: no priority tier will be assigned yet.")
    elif decision["human_review_required"]:
        st.warning("Qualified — but one or more decisions require human review before action.")
    else:
        st.success("Lead qualified based on the supplied fictional record.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Lead score", str(decision["provisional_score"]) + "/100" if decision["provisional_score"] is not None else "Unknown")
    c2.metric("Priority tier", decision["priority_tier"] or "Not assigned")
    c3.metric("Region", decision["market_region"])
    st.write("**Recommended routing:**", decision["recommended_routing"])
    st.write("**Queue status:**", decision["queue_status"])
    if decision["follow_up_target"]:
        st.write("**Follow-up target:**", decision["follow_up_target"])
    if decision["missing_fields"]:
        st.write("**Missing or invalid CRM fields:**", ", ".join(decision["missing_fields"]))
    if decision["unclear_scoring_factors"]:
        st.write("**Unclear scoring factors:**", ", ".join(decision["unclear_scoring_factors"]))
    st.markdown("#### Score breakdown")
    labels = {"company_fit": "Company fit (0/20/40)", "purchase_urgency": "Urgency (0/10/25)",
              "decision_authority": "Decision authority (0/10/20)", "engagement": "Engagement (0/5/15)"}
    st.dataframe([{"Factor": labels[k], "Points": "Unknown" if v is None else v}
                  for k, v in decision["score_components"].items()],
                 use_container_width=True, hide_index=True)
    st.markdown("#### Recommended actions (not executed)")
    for action in decision["actions"]:
        st.write(f"**{action['owner']}** — {action['action']}")
        st.caption(f"Handbook Section {action['handbook_section']}"
                   + (f" · Target: {action['deadline']}" if action.get('deadline') else ""))
    with st.expander("Rule explanations and handbook references"):
        for note in decision["explanations"]:
            st.write("• " + note)
        st.caption("Source: knowledge/allsales_sales_policy_synthetic.md — "
                   + ", ".join(decision["source_sections"]))
    st.caption("No records were saved, no messages sent, and no approvals granted. "
               "This is a local educational prototype using synthetic policy rules.")

    st.divider()
    with st.expander("Optional Gemini / Claude policy explanation"):
        st.caption("Optional AI step. Only derived policy facts are sent to Dify — "
                   "not the company name, contact name, email or use case. "
                   "This consumes model credits and cannot change the Python decision.")
        try:
            model_response = requests.get(f"{api_url}/v1/models", headers=headers, timeout=5)
            model_response.raise_for_status()
            models = model_response.json().get("models", [])
        except (requests.RequestException, ValueError):
            models = []
        if not models:
            st.info("No Dify model is available for optional explanations; the deterministic result remains usable.")
        else:
            explanation_model = st.selectbox("Explanation model", models, key="lead_explanation_model")
            if st.button("Ask AI to explain the policy (credit-consuming)", key="lead_explain"):
                st.session_state.setdefault("lead_explanation_user", str(uuid.uuid4()))
                prompt = build_explanation_prompt(decision)
                try:
                    with st.spinner(f"Asking {explanation_model} for a policy explanation..."):
                        response = requests.post(
                            f"{api_url}/v1/chat", headers=headers,
                            json={"question": prompt,
                                  "user_id": st.session_state["lead_explanation_user"],
                                  "conversation_id": "", "model": explanation_model,
                                  "allow_fallback": False}, timeout=110)
                    if response.ok:
                        data = response.json()
                        st.session_state["lead_ai_explanation"] = {
                            "text": data.get("answer", ""), "model": data.get("model", explanation_model),
                            "sources": data.get("source_documents", []),
                        }
                    else:
                        st.error(f"Policy explanation unavailable (HTTP {response.status_code}). "
                                 "The rule-based evaluation is unaffected.")
                except (requests.RequestException, ValueError):
                    st.error("Could not retrieve the optional explanation. The decision report remains valid.")
        if st.session_state.get("lead_ai_explanation"):
            result = st.session_state["lead_ai_explanation"]
            st.write(result["text"])
            st.caption("AI explanation by " + result["model"] + ". Verify section references against the handbook.")
            if result["sources"]:
                st.caption("Document labels: " + ", ".join(result["sources"]))
