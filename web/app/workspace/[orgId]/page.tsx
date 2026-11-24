import Link from "next/link";
import { addLead, updateLeadStatus } from "@/app/workspace/actions";
import { listLeads, listOrganizations, BackendError, type Lead } from "@/lib/backend";
import { notFound } from "next/navigation";

type Props = {
  params:Promise<{orgId:string}>;
  searchParams:Promise<{notice?:string}>;
};
const messages:Record<string,string> = {
  created:"Sample lead created.",
  updated:"Lead status updated.",
  invalid:"Check the information entered and try again.",
  failed:"Request failed. Verify your permissions and local services.",
};

export default async function OrganizationWorkspace({params,searchParams}:Props) {
  const {orgId} = await params;
  const {notice} = await searchParams;
  let organizations;
  try {
    organizations = await listOrganizations();
  } catch (err) {
    return (
      <section className="panel" role="alert">
        <h1>Workspace unavailable</h1>
        <p>{err instanceof BackendError ? err.message : "Could not load your organizations."}</p>
        <p className="product-caveat">Check the local API and database connection, then try again.</p>
        <Link className="button" href="/workspace">Back to organizations</Link>
      </section>
    );
  }
  const org = organizations.find(o => o.id === orgId);
  if (!org) notFound();
  let leads: Lead[] = [];
  let error:string|null = null;
  try {
    leads = await listLeads(orgId);
  } catch (err) {
    leads = [];
    error = err instanceof BackendError ? err.message : "Unable to load leads.";
  }
  const canWrite = org.role === "owner" || org.role === "admin" || org.role === "sales";
  return (
    <>
      <div className="breadcrumb">
        <Link href="/workspace">Organizations</Link><span>/</span><span>{org.name}</span>
      </div>
      <div className="section-heading">
        <span className="pill">{org.role} access</span>
        <h1 style={{marginTop:13}}>{org.name}</h1>
        <p>Review synthetic leads and manage their status within your company workspace.</p>
      </div>
      {notice && messages[notice] && <div className={"notice "+((notice==="failed"||notice==="invalid")?"error":"")} role="status">{messages[notice]}</div>}
      {error && <div className="notice error" role="alert">{error}</div>}
      <div className="columns">
        <section className="panel">
          <h2>Lead records</h2>
          <div className="lead-list">
            {!error && leads.length===0 && <div className="empty-state">No sample leads available yet.</div>}
            {leads.map(lead=>(
              <article key={lead.id} className="lead-row">
                <div className="lead-row-top">
                  <h3>{lead.company_name}</h3><span className="status">{lead.status}</span>
                </div>
                {lead.summary && <p>{lead.summary}</p>}
                {canWrite && !error && (
                  <form className="inline-form" action={updateLeadStatus.bind(null,orgId,lead.id)}>
                    <label className="visually-hidden" htmlFor={"status-"+lead.id}>New status for {lead.company_name}</label>
                    <select id={"status-"+lead.id} name="status" defaultValue={lead.status}>
                      <option value="new">New</option>
                      <option value="qualified">Qualified</option>
                      <option value="archived">Archived</option>
                    </select>
                    <button className="button" type="submit">Save status</button>
                  </form>
                )}
              </article>
            ))}
          </div>
        </section>
        <aside>
          {canWrite ? (
            <section className="panel">
              <h2>Add sample lead</h2>
              <form action={addLead.bind(null,orgId)} className="form-stack">
                <label>Company name<input name="company_name" placeholder="Example Company" maxLength={160} required /></label>
                <label>Summary<textarea name="summary" placeholder="Use fictional information only" maxLength={500} /></label>
                <button className="button primary" type="submit" disabled={Boolean(error)}>Create lead</button>
              </form>
              <p className="product-caveat">Do not enter real customer details.</p>
            </section>
          ) : (
            <section className="panel"><h2>Read-only access</h2><p>Your organization role does not permit editing.</p></section>
          )}
        </aside>
      </div>
    </>
  );
}
