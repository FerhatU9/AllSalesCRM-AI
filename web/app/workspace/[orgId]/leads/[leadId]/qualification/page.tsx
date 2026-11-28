import Link from "next/link";
import { notFound } from "next/navigation";
import { BackendError, getLead, listOrganizations, validId } from "@/lib/backend";
import QualificationForm from "./qualification-form";

export default async function QualificationPage({
  params,
}: {params: Promise<{orgId:string; leadId:string}>}) {
  const {orgId, leadId} = await params;
  if (!validId(orgId) || !validId(leadId)) notFound();
  const followups = `/workspace/${orgId}/leads/${leadId}/followups`;
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
  return (
    <>
      <div className="breadcrumb">
        <Link href="/workspace">Organizations</Link><span>/</span>
        <Link href={`/workspace/${orgId}`}>{org.name}</Link><span>/</span>
        <Link href={followups}>Follow-ups</Link><span>/</span>
        <span>Qualification</span>
      </div>
      <div className="section-heading">
        <span className="pill">Synthetic decision preview</span>
        <h1>{lead.company_name}</h1>
        <p>Evaluate fictional sales facts using the handbook. Stored lead status: {lead.status}.</p>
      </div>
      {org.role !== "viewer" && lead.status !== "archived"
        ? <QualificationForm orgId={orgId} leadId={leadId} />
        : <section className="panel"><h2>Preview not available</h2>
            <p>Only sales, admin and owner members can evaluate active leads.</p></section>}
    </>
  );
}
