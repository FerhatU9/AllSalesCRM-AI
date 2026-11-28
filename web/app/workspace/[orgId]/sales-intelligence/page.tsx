import Link from "next/link";
import { notFound } from "next/navigation";
import { BackendError, getQualificationDashboard, listOrganizations, validId } from "@/lib/backend";

export default async function SalesIntelligencePage({params, searchParams}: {
  params:Promise<{orgId:string}>; searchParams:Promise<{offset?:string}>;
}) {
  const {orgId} = await params;
  if (!validId(orgId)) notFound();
  const {offset: raw} = await searchParams;
  const offset = typeof raw === "string" && /^\d+$/.test(raw) ? Math.min(100000, Math.floor(Number(raw) / 50) * 50) : 0;
  const path = `/workspace/${orgId}`;
  const data = await (async () => {
    try {
      const org = (await listOrganizations()).find(item => item.id === orgId);
      if (!org) return null;
      return {org, dashboard: await getQualificationDashboard(orgId, offset)};
    } catch (err) {
      if (err instanceof BackendError && err.status === 404) return null;
      return undefined;
    }
  })();
  if (data === null) notFound();
  if (!data) return <section className="panel" role="alert">
    <h1>Sales intelligence unavailable</h1><p>Check your session, updated API and database migration.</p>
    <Link className="button" href={path}>Back to leads</Link>
  </section>;
  const {org, dashboard:d} = data;
  const metrics: [string, number][] = [
    ["Active leads", d.total_active], ["Evaluated", d.evaluated], ["Not evaluated", d.not_evaluated],
    ["Tier A", d.tier_a], ["Tier B", d.tier_b], ["Tier C", d.tier_c], ["Needs review or incomplete", d.needs_clarification],
  ];
  return <>
    <div className="breadcrumb"><Link href="/workspace">Organizations</Link><span>/</span><Link href={path}>{org.name}</Link><span>/</span><span>Sales intelligence</span></div>
    <div className="section-heading">
      <span className="pill">Saved synthetic decisions</span><h1>Sales intelligence</h1>
      <p>Latest reviewed qualification per active lead in {org.name}. Previews and AI answers are excluded.</p>
    </div>
    <div className="metric-grid">{metrics.map(([label,value]) => <section className="panel metric-card" key={label}><span>{label}</span><strong>{value}</strong></section>)}</div>
    <section className="panel qualification-history">
      <h2>Active lead decisions</h2>
      <p className="muted-note">Scores are historical recommendations, not CRM status changes or follow-up approvals. Policy exceptions may still require human review.</p>
      {!d.leads.length ? <p>{offset ? "No leads on this page." : "No active leads yet."}</p> :
        <div className="lead-list">{d.leads.map(lead => {
          const latest = lead.latest;
          return <article className="lead-row" key={lead.id}>
            <div className="lead-row-top"><h3>{lead.company_name}</h3><span className="status">CRM: {lead.status}</span></div>
            {latest ? <>
              <p><strong>{latest.decision.qualification_status} · {latest.decision.provisional_score ?? "—"}/100 · {latest.decision.priority_tier ? `Tier ${latest.decision.priority_tier}` : "No tier"}</strong></p>
              <p>{latest.decision.recommended_routing} · {latest.decision.queue_status}</p>
              <p>Saved {new Date(latest.created_at).toLocaleString("en-GB",{dateStyle:"medium",timeStyle:"short",timeZone:"UTC"})} UTC · {latest.decision.policy_version}{latest.decision.human_review_required ? " · Policy review required" : ""}</p>
            </> : <p>No reviewed decision saved.</p>}
            <Link className="button" href={`${path}/leads/${lead.id}/qualification`}>View qualification</Link>
          </article>;
        })}</div>}
      <div className="inline-form">
        {offset > 0 && <Link className="button" href={`${path}/sales-intelligence?offset=${offset-50}`}>Previous leads</Link>}
        {offset+50 < d.total_active && offset < 100000 && <Link className="button" href={`${path}/sales-intelligence?offset=${offset+50}`}>Next leads</Link>}
      </div>
    </section>
  </>;
}
