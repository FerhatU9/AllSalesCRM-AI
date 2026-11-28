import Link from "next/link";
import { randomUUID } from "node:crypto";
import { notFound } from "next/navigation";

import {
  requestFollowupAction,
  decideFollowupAction,
} from "@/app/workspace/actions";

import {
  BackendError,
  getLead,
  getLeadRecommendation,
  listFollowups,
  listOrganizations,
  validId,
  type Followup,
  type Lead,
  type LeadRecommendation,
  type Organization,
} from "@/lib/backend";

type Props = {
  params: Promise<{
    orgId: string;
    leadId: string;
  }>;
  searchParams: Promise<{
    notice?: string;
  }>;
};

const messages: Record<string, string> = {
  created: "Follow-up request created.",
  approved: "Follow-up approved.",
  rejected: "Follow-up rejected.",
  conflict: "This action is no longer available. Check the lead and request status.",
  invalid: "Invalid decision submitted.",
  failed: "Request failed. Check your permissions and local services.",
};

function formatTime(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }) + " UTC";
}

export default async function FollowupPage({
  params,
  searchParams,
}: Props) {
  const { orgId, leadId } = await params;
  const { notice } = await searchParams;

  if (!validId(orgId) || !validId(leadId)) {
    notFound();
  }

  let data:
    | {
        org: Organization;
        lead: Lead;
        requests: Followup[];
        recommendation: LeadRecommendation | null;
      }
    | undefined;

  try {
    const organizations = await listOrganizations();
    const org = organizations.find((item) => item.id === orgId);

    if (org) {
      const [lead, requests, recommendation] = await Promise.all([
        getLead(orgId, leadId),
        listFollowups(orgId, leadId),
        getLeadRecommendation(orgId, leadId).catch(() => null),
      ]);

      data = { org, lead, requests, recommendation };
    }
  } catch (err) {
    if (err instanceof BackendError && err.status === 404) {
      notFound();
    }

    return (
      <section className="panel" role="alert">
        <h1>Follow-ups unavailable</h1>
        <p>Check the local API and database connection.</p>
        <Link className="button" href={`/workspace/${orgId}`}>
          Back to workspace
        </Link>
      </section>
    );
  }

  if (!data) notFound();

  const { org, lead, requests, recommendation } = data;

  const canRequest =
    org.role !== "viewer" && lead.status === "qualified";

  const canDecide =
    org.role === "owner" || org.role === "admin";

  const now = Date.now();
  const requestKey = randomUUID();

  const noticeText =
    typeof notice === "string" &&
    Object.prototype.hasOwnProperty.call(messages, notice)
      ? messages[notice]
      : undefined;

  return (
    <>
      <div className="breadcrumb">
        <Link href="/workspace">Organizations</Link>
        <span>/</span>
        <Link href={`/workspace/${orgId}`}>{org.name}</Link>
        <span>/</span>
        <span>Follow-ups</span>
      </div>

      <div className="section-heading">
        <span className="pill">{org.role} access</span>
        <h1>{lead.company_name}</h1>
        <p>Human approval workflow for sales follow-ups.</p>
      </div>

      {noticeText && (
        <div
          className={
            "notice " +
            (notice === "failed" ||
            notice === "conflict" ||
            notice === "invalid"
              ? "error"
              : "")
          }
          role="status"
        >
          {noticeText}
        </div>
      )}

      <div className="columns">
        <section className="panel">
          <h2>Follow-up requests</h2>

          <div className="lead-list">
            {requests.length === 0 && (
              <div className="empty-state">
                No follow-up requests yet.
              </div>
            )}

            {requests.map((item) => {
              const expired = Date.parse(item.expires_at) <= now;
              const pending = item.status === "pending" && !expired;

              return (
                <article key={item.id} className="lead-row">
                  <div className="lead-row-top">
                    <h3>Sales follow-up</h3>
                    <span className="status">
                      {item.status === "pending" && expired
                        ? "expired"
                        : item.status}
                    </span>
                  </div>

                  <p>Request: {item.id}</p>
                  <p>Created: {formatTime(item.created_at)}</p>
                  <p>Expires: {formatTime(item.expires_at)}</p>

                  {item.decided_at && (
                    <p>Decided: {formatTime(item.decided_at)}</p>
                  )}

                  {item.executed_at && (
                    <p>Executed: {formatTime(item.executed_at)}</p>
                  )}

                  {canDecide && pending && (
                    <form
                      className="inline-form"
                      action={decideFollowupAction.bind(
                        null,
                        orgId,
                        leadId,
                        item.id
                      )}
                    >
                      {lead.status === "qualified" && (
                        <button
                          className="button primary"
                          type="submit"
                          name="decision"
                          value="approved"
                        >
                          Approve
                        </button>
                      )}

                      <button
                        className="button"
                        type="submit"
                        name="decision"
                        value="rejected"
                      >
                        Reject
                      </button>
                    </form>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        <aside className="lead-list">
          <section className="panel" aria-labelledby="recommendation-heading">
            <span className="pill">LangGraph · Local rules</span>
            <h2 id="recommendation-heading">Sales recommendation</h2>
            {recommendation ? (
              <>
                <h3>{recommendation.title}</h3>
                <p>{recommendation.reason}</p>
                <ul>
                  {recommendation.review_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p role="status">Recommendation unavailable. You can still review follow-ups.</p>
            )}
            <p className="product-caveat">
              Guidance only. No AI model or external delivery is used in this stage.
              Human approval is required for any follow-up action.
            </p>
          </section>

          <section className="panel">
            <h2>Request follow-up</h2>
            <p>Lead status: {lead.status}</p>

            {canRequest ? (
              <form
                className="form-stack"
                action={requestFollowupAction.bind(
                  null,
                  orgId,
                  leadId,
                  requestKey
                )}
              >
                <button className="button primary" type="submit">
                  Request follow-up
                </button>
              </form>
            ) : (
              <p className="product-caveat">
                Your role or the current lead status does not allow
                new follow-up requests.
              </p>
            )}

            <p className="product-caveat">
              Human approval is required. Automated outreach is disabled.
            </p>
          </section>
        </aside>
      </div>
    </>
  );
}