"use server";
import { auth0 } from "@/lib/auth0";
import {
  changeLeadStatus,
  createLead,
  validId,
  createFollowupRequest,
  resolveFollowupRequest,
  BackendError,
  previewLeadQualification,
  type QualificationPreview,
  type Lead,
} from "@/lib/backend";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

const STATUSES = new Set<Lead["status"]>(["new","qualified","archived"]);

async function requireSession() {
  const session = await auth0.getSession();
  if (!session) redirect("/auth/login");
}
function location(orgId:string,notice:string) {
  return "/workspace/" + orgId + "?notice=" + notice;
}

export async function addLead(orgId:string,formData:FormData):Promise<void> {
  await requireSession();
  if (!validId(orgId)) redirect("/workspace");
  const name = formData.get("company_name");
  const summary = formData.get("summary");
  if (typeof name !== "string" || !name.trim() || name.trim().length > 160 ||
      typeof summary !== "string" || summary.length > 500) redirect(location(orgId,"invalid"));
  try {
    await createLead(orgId,{company_name:name.trim(),summary});
  } catch {
    redirect(location(orgId,"failed"));
  }
  revalidatePath("/workspace/" + orgId);
  redirect(location(orgId,"created"));
}

export async function updateLeadStatus(orgId:string,leadId:string,formData:FormData):Promise<void> {
  await requireSession();
  if (!validId(orgId) || !validId(leadId)) redirect("/workspace");
  const status = formData.get("status");
  if (typeof status !== "string" || !STATUSES.has(status as Lead["status"])) {
    redirect(location(orgId,"invalid"));
  }
  try {
    await changeLeadStatus(orgId,leadId,status as Lead["status"]);
  } catch {
    redirect(location(orgId,"failed"));
  }
  revalidatePath("/workspace/" + orgId);
  redirect(location(orgId,"updated"));
}
function followupLocation(
  orgId: string,
  leadId: string,
  notice?: string
) {
  const path = `/workspace/${orgId}/leads/${leadId}/followups`;

  return notice ? `${path}?notice=${notice}` : path;
}

export async function requestFollowupAction(
  orgId: string,
  leadId: string,
  requestKey: string,
  _formData: FormData
): Promise<void> {
  await requireSession();

  if (!validId(orgId) || !validId(leadId) || !validId(requestKey)) {
    redirect("/workspace");
  }

  try {
    await createFollowupRequest(orgId, leadId, requestKey);
  } catch (err) {
    redirect(
      followupLocation(
        orgId,
        leadId,
        err instanceof BackendError && err.status === 409
          ? "conflict"
          : "failed"
      )
    );
  }

  revalidatePath(followupLocation(orgId, leadId));

  redirect(followupLocation(orgId, leadId, "created"));
}

export async function decideFollowupAction(
  orgId: string,
  leadId: string,
  followupId: string,
  formData: FormData
): Promise<void> {
  await requireSession();

  if (!validId(orgId) || !validId(leadId) || !validId(followupId)) {
    redirect("/workspace");
  }

  const decision = formData.get("decision");

  if (decision !== "approved" && decision !== "rejected") {
    redirect(followupLocation(orgId, leadId, "invalid"));
  }

  try {
    await resolveFollowupRequest(
      orgId,
      leadId,
      followupId,
      decision
    );
  } catch (err) {
    redirect(
      followupLocation(
        orgId,
        leadId,
        err instanceof BackendError && err.status === 409
          ? "conflict"
          : "failed"
      )
    );
  }

  revalidatePath(followupLocation(orgId, leadId));

  redirect(followupLocation(orgId, leadId, decision));
}

export async function qualificationPreviewAction(
  orgId: string, leadId: string, formData: FormData
): Promise<{result: QualificationPreview | null; error: string | null}> {
  await requireSession();
  if (!validId(orgId) || !validId(leadId)) {
    return {result: null, error: "Invalid record."};
  }
  const provider = formData.get("provider");
  if (formData.get("confirm_synthetic") !== "on" ||
      (provider !== "none" && provider !== "gemini" && provider !== "claude")) {
    return {result: null, error: "Confirm synthetic data and select an explanation mode."};
  }
  const string = (key: string) => {
    const value = formData.get(key);
    return typeof value === "string" ? value.trim() : "";
  };
  const facts: Record<string, string | number | boolean | null> = {};
  for (const field of [
    "country", "industry", "contact_name", "business_email", "lead_source",
    "assigned_owner", "consent_status", "decision_authority", "engagement"
  ]) facts[field] = string(field);
  for (const field of ["employee_count", "decision_days", "proposed_discount_pct"]) {
    const raw = string(field);
    const value = raw === "" ? null : Number(raw);
    if (value !== null && !Number.isFinite(value)) {
      return {result: null, error: "Enter valid numeric values."};
    }
    facts[field] = value;
  }
  for (const field of ["custom_contract_terms", "suspected_security_incident", "urgent_service_outage"]) {
    facts[field] = formData.get(field) === "on";
  }
  try {
    return {result: await previewLeadQualification(orgId, leadId, facts, provider), error: null};
  } catch (err) {
    const error = err instanceof BackendError && err.status === 422
      ? "Some values are invalid. Check the form and try again."
      : err instanceof BackendError && err.status === 409
      ? "This lead is archived and cannot be evaluated."
      : err instanceof BackendError && err.status === 403
      ? "You do not have access to evaluate this lead."
      : err instanceof BackendError && err.status === 404
      ? "The lead or preview endpoint was not found. Check access and restart the updated local API."
      : "Preview unavailable. Check your session and local API.";
    return {result: null, error};
  }
}
