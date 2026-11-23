import Link from "next/link";
import { listOrganizations, BackendError } from "@/lib/backend";

export default async function WorkspaceIndex() {
  let organizations;
  try {
    organizations = await listOrganizations();
  } catch (err) {
    return (
      <section className="panel">
        <h1>Workspace unavailable</h1>
        <p>{err instanceof BackendError ? err.message : "Could not load your organizations."}</p>
        <p className="product-caveat">Verify that the local FastAPI server, Auth0 configuration and database are running.</p>
      </section>
    );
  }
  return (
    <>
      <div className="breadcrumb">Workspace</div>
      <div className="section-heading">
        <h1>Your organizations</h1>
        <p>Choose a company to work with its authorized lead records.</p>
      </div>
      {organizations.length === 0 ? (
        <section className="empty-state">
          No organizations are assigned to this account. Ask your development administrator to provision your identity and membership.
        </section>
      ) : (
        <section className="org-grid" aria-label="Your organizations">
          {organizations.map(org => (
            <Link key={org.id} href={"/workspace/"+org.id} className="org-card">
              <span className="pill">{org.role}</span>
              <h2>{org.name}</h2>
              <p>{org.slug}</p>
              <strong style={{color:"var(--blue)",fontSize:".87rem"}}>Open lead workspace →</strong>
            </Link>
          ))}
        </section>
      )}
      <p className="product-caveat">Development environment · Synthetic data only · No real customer access</p>
    </>
  );
}
