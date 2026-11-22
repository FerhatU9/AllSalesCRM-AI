import Link from "next/link";
import { auth0 } from "@/lib/auth0";

export default async function HomePage() {
  const session = await auth0.getSession();
  return (
    <main className="landing">
      <nav className="topbar"><div className="brand"><span className="brand-mark">A</span> AllSales CRM</div>
        <span className="nav-label">Sales intelligence workspace</span>
      </nav>
      <section className="hero">
        <span className="eyebrow">SALES POLICY · LEAD MANAGEMENT</span>
        <h1>Decisions your sales team can trust.</h1>
        <p className="hero-copy">Bring your sales policies, lead qualification and team workflows into one clear workspace. Start with consistent rules and keep people in control.</p>
        <div className="hero-actions">
          {session ? (
            <Link className="button primary" href="/workspace">Open workspace</Link>
          ) : (
            <a className="button primary" href="/auth/login">Sign in to workspace</a>
          )}
          <span className="muted-note">Access is restricted to approved development accounts.</span>
        </div>
      </section>
      <section className="feature-grid" aria-label="Product capabilities">
        <article className="feature"><span className="feature-icon">01</span><h2>Policy intelligence</h2><p>Find relevant guidance in approved sales documentation.</p></article>
        <article className="feature"><span className="feature-icon">02</span><h2>Lead qualification</h2><p>Use transparent, rule-based scoring and human review.</p></article>
        <article className="feature"><span className="feature-icon">03</span><h2>Company workspaces</h2><p>Keep lead records associated with their organization.</p></article>
      </section>
      <footer className="footer-note">Development environment · Synthetic data only · Not a public customer service</footer>
    </main>
  );
}
