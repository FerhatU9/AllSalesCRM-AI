import Link from "next/link";
import { auth0 } from "@/lib/auth0";
import { redirect } from "next/navigation";

export default async function WorkspaceLayout({children}:{children:React.ReactNode}) {
  const session = await auth0.getSession();
  if (!session) redirect("/auth/login");
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <Link href="/workspace" className="brand"><span className="brand-mark">A</span> AllSales CRM</Link>
          <div className="user-actions">
            <span className="username">{session.user.name ?? session.user.email ?? "Signed in"}</span>
            <a href="/auth/logout" className="button">Sign out</a>
          </div>
        </div>
      </header>
      <main className="page-content">{children}</main>
    </div>
  );
}
