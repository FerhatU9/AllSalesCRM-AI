import "server-only";
import { auth0 } from "@/lib/auth0";

export type Organization = { id:string; name:string; slug:string; role:"owner"|"admin"|"sales"|"viewer" };
export type Lead = { id:string; organization_id:string; company_name:string; summary:string; status:"new"|"qualified"|"archived" };

export class BackendError extends Error {
  constructor(public readonly status:number, message="The service is unavailable.") {
    super(message);
    this.name = "BackendError";
  }
}

const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);

function configuredBackend(): URL {
  const parsed = new URL(process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000");
  if (parsed.protocol !== "http:" || !LOCAL_HOSTS.has(parsed.hostname) ||
      parsed.username || parsed.password || parsed.search || parsed.hash ||
      parsed.pathname !== "/") {
    throw new BackendError(503, "Development backend URL is invalid.");
  }
  return parsed;
}

export function validId(value:string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

async function apiRequest<T>(path:string, init:RequestInit = {}):Promise<T> {
  const { token } = await auth0.getAccessToken();
  const base = configuredBackend();
  const url = new URL(path, base);
  if (url.origin !== base.origin || !url.pathname.startsWith("/v1/")) {
    throw new BackendError(503, "Invalid backend route.");
  }
  let response:Response;
  try {
    response = await fetch(url, {
      ...init,
      cache: "no-store",
      headers: {
        Authorization: "Bearer " + token,
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
      },
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    throw new BackendError(503, "Cannot connect to the local API.");
  }
  if (!response.ok) {
    const message = response.status === 403
      ? "You do not have permission to perform this action."
      : response.status === 404
      ? "The requested record was not found."
      : response.status === 401
      ? "Your API authorization was rejected."
      : "The local API could not complete the request.";
    throw new BackendError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export async function listOrganizations():Promise<Organization[]> {
  const result = await apiRequest<{organizations:Organization[]}>("/v1/account/organizations");
  return result.organizations;
}

function leadPath(orgId:string, leadId?:string):string {
  if (!validId(orgId) || (leadId !== undefined && !validId(leadId))) {
    throw new BackendError(404, "Invalid record identifier.");
  }
  return "/v1/organizations/" + orgId + "/leads" + (leadId ? "/" + leadId : "");
}

export async function listLeads(orgId:string):Promise<Lead[]> {
  return apiRequest<Lead[]>(leadPath(orgId));
}
export async function createLead(orgId:string, input:{company_name:string;summary:string}):Promise<Lead> {
  return apiRequest<Lead>(leadPath(orgId), {method:"POST",body:JSON.stringify(input)});
}
export async function changeLeadStatus(orgId:string,leadId:string,status:Lead["status"]):Promise<Lead> {
  return apiRequest<Lead>(leadPath(orgId,leadId),{method:"PATCH",body:JSON.stringify({status})});
}
