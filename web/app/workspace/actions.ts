"use server";
import { auth0 } from "@/lib/auth0";
import {
  changeLeadStatus,
  createLead,
  validId,
  createFollowupRequest,
  resolveFollowupRequest,
  BackendError,
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