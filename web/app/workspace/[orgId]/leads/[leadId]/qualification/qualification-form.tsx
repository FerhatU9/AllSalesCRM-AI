"use client";

import { useRef, useState, useTransition, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { qualificationPreviewAction, saveQualificationAction } from "@/app/workspace/actions";
import type { QualificationPreview } from "@/lib/backend";

const SAMPLE: Record<string, string> = {
  country: "Netherlands", employee_count: "120", industry: "SaaS",
  contact_name: "Demo Buyer", business_email: "buyer@example.test",
  lead_source: "Website", consent_status: "Opted In", assigned_owner: "Demo Rep",
  decision_days: "20", decision_authority: "final", engagement: "none",
  proposed_discount_pct: "0", provider: "none",
};
const LABELS: Record<string, string> = {
  company_fit: "Company fit", purchase_urgency: "Purchase urgency",
  decision_authority: "Decision authority", engagement: "Engagement",
};
const checkboxes = [
  ["custom_contract_terms", "Custom contract terms"],
  ["suspected_security_incident", "Suspected security incident"],
  ["urgent_service_outage", "Urgent service outage"],
];

const FAILURE_GUIDANCE: Record<NonNullable<QualificationPreview["explanation_failure"]>, string> = {
  missing_configuration: "The selected Dify app key is not configured in the local backend .env.",
  invalid_configuration: "Check the Dify base URL and selected app configuration in the local backend.",
  access_rejected: "Dify rejected access. Check the published Chatflow's app API key.",
  rate_limited: "Dify or its model provider reached a usage limit. Check quota and billing.",
  provider_busy: "Dify or its upstream model returned a service error. Check the Chatflow run and try again later.",
  request_rejected: "Dify rejected the request. Check the published Chatflow and its run history.",
  timeout: "Dify did not respond in time. Check the Chatflow run before trying again.",
  network: "The backend could not contact Dify. Check connectivity and the API address.",
  invalid_response: "Dify returned an unexpected response. Check the published Chatflow's API.",
  empty_answer: "Dify returned an empty answer. Check the Chatflow's retrieval and Answer nodes.",
  unknown: "The selected provider is unavailable. Check the local API terminal and Dify run history.",
};

function Results({result}: {result: QualificationPreview}) {
  const d = result.decision;
  return (
    <div className="lead-list">
      <section className="panel" aria-labelledby="deterministic">
        <span className="pill">LangGraph · Deterministic rules</span>
        <h2 id="deterministic">{d.qualification_status}</h2>
        <div className="qualification-score">
          <strong>{d.provisional_score === null ? "—" : `${d.provisional_score}/100`}</strong>
          <span>Provisional score · {d.priority_tier ? `Tier ${d.priority_tier}` : "No assigned tier"}</span>
        </div>
        <dl className="qualification-detail">
          {Object.entries(d.score_components).map(([key, value]) => (
            <div key={key}><dt>{LABELS[key] ?? key}</dt><dd>{value ?? "Unverified"}</dd></div>
          ))}
          <div><dt>Market</dt><dd>{d.market_region}</dd></div>
          <div><dt>Routing</dt><dd>{d.recommended_routing}</dd></div>
          <div><dt>Queue</dt><dd>{d.queue_status}</dd></div>
          <div><dt>Follow-up target</dt><dd>{d.follow_up_target ?? "Not set"}</dd></div>
          <div><dt>Policy exception review</dt><dd>{d.human_review_required ? "Required" : "None flagged"}</dd></div>
        </dl>
        {d.missing_fields.length > 0 && <p><strong>Missing:</strong> {d.missing_fields.join(", ")}</p>}
        {d.unclear_scoring_factors.length > 0 && <p><strong>Unverified:</strong> {d.unclear_scoring_factors.join(", ")}</p>}
        <h3>Policy actions to review</h3>
        {d.actions.length ? <ul>{d.actions.map((action, i) => (
          <li key={i}>{action.action} — {action.owner}{action.deadline ? ` · ${action.deadline}` : ""} (section {action.handbook_section})</li>
        ))}</ul> : <p>No additional policy actions flagged.</p>}
        {d.explanations.length > 0 && <ul>{d.explanations.map((item, i) => <li key={i}>{item}</li>)}</ul>}
        <p className="muted-note">{d.policy_version} · {d.source_sections.join(", ") || "—"}</p>
        <p className="product-caveat">Stored status remains {result.stored_status}. A preview alone stores nothing. Saving records only the deterministic decision; no automated actions are taken. Human approval remains required for every follow-up.</p>
      </section>
      <section className="panel">
        <span className="pill">Optional · Advisory only</span>
        <h2>AI explanation</h2>
        {result.explanation_status === "complete" ? <>
          <p><strong>{result.provider === "gemini" ? "Gemini" : "Claude"} via Dify</strong> — verify against the handbook.</p>
          <p className="qualification-explanation">{result.explanation}</p>
          {result.source_documents.length > 0
            ? <p className="muted-note">Provider-reported sources: {result.source_documents.join(", ")}</p>
            : <p className="muted-note">No source documents were reported. Verify the answer against the handbook.</p>}
        </> : result.explanation_status === "abstained" ? <>
          <p><strong>{result.provider === "gemini" ? "Gemini" : "Claude"} via Dify</strong> — no supported explanation returned.</p>
          <p className="qualification-explanation">{result.explanation}</p>
          <p className="muted-note">The model abstained. Check the Dify run's Knowledge Retrieval results. The deterministic score and policy actions above remain authoritative.</p>
        </> : <p>{
          result.explanation_status === "not_requested" ? "No AI model requested. The deterministic preview is complete."
          : result.explanation_status === "withheld_incomplete" ? "Explanation withheld until the required facts and scoring factors are complete."
          : `${FAILURE_GUIDANCE[result.explanation_failure ?? "unknown"]} The deterministic result remains valid.`
        }</p>}
        <p className="product-caveat">AI text is not an approval, a policy override or a guarantee of correctness.</p>
      </section>
    </div>
  );
}

export default function QualificationForm({orgId, leadId}: {orgId:string; leadId:string}) {
  const form = useRef<HTMLFormElement>(null);
  const router = useRouter();
  const reviewed = useRef<{data: FormData; key: string} | null>(null);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [result, setResult] = useState<QualificationPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  function clearPreview() {
    reviewed.current = null;
    setResult(null); setError(null); setSaved(false); setSaveError(null);
  }
  function loadExample() {
    for (const [key, value] of Object.entries(SAMPLE)) {
      const field = form.current?.elements.namedItem(key);
      if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement) field.value = value;
    }
    for (const key of ["confirm_synthetic", ...checkboxes.map(([name]) => name)]) {
      const field = form.current?.elements.namedItem(key);
      if (field instanceof HTMLInputElement) field.checked = false;
    }
    clearPreview();
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    clearPreview();
    startTransition(async () => {
      try {
        const response = await qualificationPreviewAction(orgId, leadId, data);
        if (response.result) reviewed.current = {data, key: crypto.randomUUID()};
        setResult(response.result); setError(response.error);
      } catch {
        setError("Preview unavailable. Check your session and local API.");
      }
    });
  }
  function save() {
    const snapshot = reviewed.current;
    if (!snapshot || !result?.review_digest || pending || saved) return;
    setSaveError(null);
    startTransition(async () => {
      try {
        const response = await saveQualificationAction(orgId, leadId, snapshot.data, snapshot.key, result.review_digest);
        setSaveError(response.error);
        if (response.result) {
          setSaved(true);
          router.refresh();
        }
      } catch {
        setSaveError("Could not confirm the save. Retry the same reviewed decision.");
      }
    });
  }
  return (
    <div className="columns">
      <section className="panel">
        <h2>Structured lead facts</h2>
        <p className="muted-note">Company name and use case come from the stored record. Enter fictional facts only. Unknown or missing facts are not guessed.</p>
        <form ref={form} className="form-stack" onSubmit={submit} onChange={clearPreview}>
          <fieldset disabled={pending} className="qualification-fields">
            <button type="button" className="button" onClick={loadExample}>Load synthetic example</button>
            <div className="qualification-grid">
              <label>Country<input name="country" maxLength={80} /></label>
              <label>Employees<input name="employee_count" type="number" min="0" max="1000000" step="1" /></label>
              <label>Industry<input name="industry" maxLength={120} /></label>
              <label>Fictional contact<input name="contact_name" maxLength={120} /></label>
              <label>Fictional business email<input name="business_email" type="email" maxLength={254} /></label>
              <label>Lead source<input name="lead_source" maxLength={120} /></label>
              <label>Consent status<select name="consent_status" defaultValue="Missing">
                <option>Missing</option><option>Unknown</option><option>Opted In</option><option>Opted Out</option>
              </select></label>
              <label>Assigned owner<input name="assigned_owner" maxLength={120} /></label>
              <label>Days to decision<input name="decision_days" type="number" min="0" max="3650" step="1" /></label>
              <label>Decision authority<select name="decision_authority" defaultValue="unknown">
                <option value="unknown">Unknown</option><option value="final">Final decision maker</option>
                <option value="influencer">Influencer</option><option value="none">None</option>
              </select></label>
              <label>Engagement<select name="engagement" defaultValue="unknown">
                <option value="unknown">Unknown</option><option value="demo_booked">Demo booked</option>
                <option value="email_replied">Email replied</option><option value="none">None</option>
              </select></label>
              <label>Proposed discount (%)<input name="proposed_discount_pct" type="number" min="0" max="100" step="0.1" /></label>
            </div>
            <h3 className="subheading">Policy exceptions</h3>
            {checkboxes.map(([name, label]) => (
              <label className="qualification-check" key={name}><input name={name} type="checkbox" />{label}</label>
            ))}
            <label>Explanation mode<select name="provider" defaultValue="none">
              <option value="none">Local rules only (default)</option>
              <option value="gemini">Gemini via Dify</option><option value="claude">Claude via Dify</option>
            </select></label>
            <p className="muted-note">Selecting a model sends only derived policy facts to Dify, may incur provider costs, and can take up to two minutes. No contact identifiers or raw lead text are sent.</p>
            <label className="qualification-check"><input name="confirm_synthetic" type="checkbox" required />I confirm that this evaluation uses fictional demonstration data only.</label>
            <button className="button primary" type="submit" disabled={pending}>{pending ? "Working…" : "Preview qualification"}</button>
          </fieldset>
        </form>
        {error && <p className="notice error" role="alert">{error}</p>}
      </section>
      {result ? <div className="lead-list">
        <Results result={result} />
        <section className="panel">
          <h2>Save reviewed decision</h2>
          <p>Save the deterministic score, routing and policy actions for this synthetic lead. The original facts, contact details and AI explanation are not stored. This does not change the lead status or approve a follow-up.</p>
          <button type="button" className="button primary" disabled={pending || saved || !result.review_digest} onClick={save}>
            {saved ? "Decision saved" : pending ? "Saving…" : "Save qualification"}
          </button>
          {saved && <p className="notice" role="status">Qualification saved. See the history below.</p>}
          {saveError && <p className="notice error" role="alert">{saveError}</p>}
          {!result.review_digest && <p className="notice error">Restart the updated API and preview again to enable saving.</p>}
        </section>
      </div> :
        <section className="panel" role="status">
          <h2>Qualification preview</h2>
          <p>{pending ? "Evaluating the submitted facts. Please wait." : "Submit synthetic facts to see the score, routing and policy actions. Nothing is saved in the CRM."}</p>
        </section>}
    </div>
  );
}
