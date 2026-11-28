import Link from "next/link";
import { notFound } from "next/navigation";
import { BackendError, getLead, listOrganizations, listQualificationHistory, validId } from "@/lib/backend";
import QualificationForm from "./qualification-form";

export default async function QualificationPage({
  params, searchParams,
}: {params: Promise<{orgId:string; leadId:string}>; searchParams:Promise<{offset?:string}>}) {
  const {orgId, leadId} = await params;
  if (!validId(orgId) || !validId(leadId)) notFound();
  const {offset: raw} = await searchParams;
  const offset = typeof raw === "string" && /^\d+$/.test(raw) ? Math.min(100000, Math.floor(Number(raw) / 50) * 50) : 0;
  const followups = `/workspace/${orgId}/leads/${leadId}/followups`;
  const path = `/workspace/${orgId}/leads/${leadId}/qualification`;
  const data = await (async () => {
    try {
      const org = (await listOrganizations()).find((item) => item.id === orgId);
      if (!org) return null;
      return {org, lead: await getLead(orgId, leadId)};
    } catch (err) {
      if (err instanceof BackendError && err.status === 404) return null;
      return undefined;
    }
  })();
  if (data === null) notFound();
  if (!data) return (
    <section className="panel" role="alert">
      <h1>Qualification unavailable</h1>
      <p>Check your session and local API.</p>
      <Link className="button" href={followups}>Back to follow-ups</Link>
    </section>
  );
  const {org, lead} = data;
  const history = await listQualificationHistory(orgId, leadId, offset).catch(() => null);
  return (
    <>
      <div className="breadcrumb">
        <Link href="/workspace">Organizations</Link><span>/</span>
        <Link href={`/workspace/${orgId}`}>{org.name}</Link><span>/</span>
        <Link href={followups}>Follow-ups</Link><span>/</span>
        <span>Qualification</span>
      </div>
      <div className="section-heading">
        <span className="pill">Synthetic decision support</span>
        <h1>{lead.company_name}</h1>
        <p>Evaluate fictional sales facts using the handbook. Stored lead status: {lead.status}.</p>
        <Link className="button" href={`/workspace/${orgId}/sales-intelligence`}>Sales intelligence dashboard</Link>
      </div>
      {org.role !== "viewer" && lead.status !== "archived"
        ? <QualificationForm orgId={orgId} leadId={leadId} />
        : <section className="panel"><h2>Preview not available</h2>
            <p>Only sales, admin and owner members can evaluate active leads.</p></section>}
      <section className="panel qualification-history" id="history">
        <h2>Saved qualification history</h2>
        <p className="muted-note">Reviewed, server-calculated decisions, newest first. Historical decisions may differ from the current lead status and policy.</p>
        {history === null ? <p role="alert">History unavailable. Check the updated API and database migration.</p>
          : history.length === 0 ? <p>{offset ? "No decisions on this page." : "No saved decisions yet."}</p>
          : <div className="lead-list">{history.map(snapshot => {
              const d = snapshot.decision;
              return <article className="lead-row" key={snapshot.id}>
                <div className="lead-row-top"><h3>{d.qualification_status} · {d.provisional_score ?? "—"}/100</h3><span className="status">{d.priority_tier ? `Tier ${d.priority_tier}` : "No tier"}</span></div>
                <p>{new Date(snapshot.created_at).toLocaleString("en-GB", {dateStyle:"medium",timeStyle:"short",timeZone:"UTC"})} UTC · {d.policy_version}</p>
                <p>{d.recommended_routing} · {d.queue_status}</p>
                <p>Lead status at save: {snapshot.stored_status}. Policy exception review: {d.human_review_required ? "Required" : "None flagged"}.</p>
                <details><summary>Decision details</summary>
                  <dl className="qualification-detail">{Object.entries(d.score_components).map(([label,value]) => <div key={label}><dt>{label.replaceAll("_"," ")}</dt><dd>{value ?? "Unverified"}</dd></div>)}</dl>
                  {d.missing_fields.length > 0 && <p>Missing: {d.missing_fields.join(", ")}</p>}
                  {d.unclear_scoring_factors.length > 0 && <p>Unverified: {d.unclear_scoring_factors.join(", ")}</p>}
                  <ul>{d.actions.map((action,i) => <li key={i}>{action.action} — {action.owner} {action.deadline ? `· ${action.deadline}` : ""} (section {action.handbook_section})</li>)}</ul>
                  <p>{d.source_sections.join(", ")}</p>
                </details>
              </article>;
            })}</div>}
        <div className="inline-form">
          {offset > 0 && <Link className="button" href={`${path}?offset=${offset-50}#history`}>Newer decisions</Link>}
          {history?.length === 50 && offset < 100000 && <Link className="button" href={`${path}?offset=${offset+50}#history`}>Older decisions</Link>}
        </div>
      </section>
    </>
  );
}
