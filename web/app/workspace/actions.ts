"use server";
import { auth0 } from "@/lib/auth0";
import { changeLeadStatus, createLead, validId, type Lead } from "@/lib/backend";
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
