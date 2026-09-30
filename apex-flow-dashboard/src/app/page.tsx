import type { Metadata } from "next";
import Link from "next/link";
import { GitBranch, Zap, ShieldCheck, ArrowRight, Terminal } from "lucide-react";

export const metadata: Metadata = {
  title: "ApexFlow — Lightweight Workflow Orchestration",
  description: "Code-first workflow orchestration control plane. Run durable, observable workflows with any language, any infra.",
};

const FEATURES = [
  {
    icon: GitBranch,
    title: "Code-First Workflows",
    desc: "Define workflows in pure Python. No YAML, no drag-and-drop, no vendor lock-in.",
  },
  {
    icon: Zap,
    title: "Fast & Lightweight",
    desc: "Built on FastAPI and async Postgres. Handles thousands of steps with minimal overhead.",
  },
  {
    icon: ShieldCheck,
    title: "Secure by Default",
    desc: "Per-project API keys, JWT-authenticated dashboard, and scoped tenant isolation.",
  },
];

export default function LandingPage() {
  return (
    <div className="landing-layout">
      {/* Animated background */}
      <div className="auth-bg-grid" aria-hidden="true" />
      <div className="auth-orb auth-orb-1" aria-hidden="true" />
      <div className="auth-orb auth-orb-2" aria-hidden="true" />

      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-nav-brand">
          <div className="auth-logo-mark" style={{ width: 36, height: 36, borderRadius: 10 }}>
            <svg width="20" height="20" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <path d="M14 2L24 8V20L14 26L4 20V8L14 2Z" fill="url(#hexGradLanding)" stroke="rgba(139,92,246,0.4)" strokeWidth="1" />
              <path d="M14 7L19 10V16L14 19L9 16V10L14 7Z" fill="rgba(139,92,246,0.3)" />
              <defs>
                <linearGradient id="hexGradLanding" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#8B5CF6" stopOpacity="0.8" />
                  <stop offset="1" stopColor="#06B6D4" stopOpacity="0.6" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span className="landing-brand-name">ApexFlow</span>
        </div>
        <div className="landing-nav-actions">
          <Link href="/auth/login" className="landing-nav-link">Sign in</Link>
          <Link href="/auth/signup" id="landing-cta-nav" className="landing-nav-cta">
            Get started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="landing-hero">
        <div className="landing-hero-badge">
          <Terminal size={12} />
          <span>Open-source workflow orchestration</span>
        </div>

        <h1 className="landing-hero-title">
          Orchestrate workflows.
          <br />
          <span className="landing-hero-gradient">Ship faster.</span>
        </h1>

        <p className="landing-hero-subtitle">
          ApexFlow is a lightweight, code-first workflow orchestration control plane.
          Define durable workflows in Python, observe every step, and scale with confidence.
        </p>

        <div className="landing-hero-actions">
          <Link href="/auth/signup" id="landing-cta-primary" className="landing-cta-primary">
            Start for free
            <ArrowRight size={16} />
          </Link>
          <Link href="/auth/login" id="landing-cta-secondary" className="landing-cta-secondary">
            Sign in to dashboard
          </Link>
        </div>

        {/* Code snippet */}
        <div className="landing-code-block">
          <div className="landing-code-dots" aria-hidden="true">
            <span /><span /><span />
          </div>
          <pre className="landing-code"><code>{`from apexflow import workflow, step

@workflow("order-processing")
def process_order(order_id: str):
    validated = validate_order(order_id)
    charged   = charge_payment(validated)
    return fulfill_order(charged)

@step
def validate_order(order_id: str): ...`}</code></pre>
        </div>
      </main>

      {/* Features */}
      <section className="landing-features" aria-labelledby="features-heading">
        <h2 id="features-heading" className="sr-only">Features</h2>
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="landing-feature-card">
            <div className="landing-feature-icon">
              <Icon size={18} />
            </div>
            <h3 className="landing-feature-title">{title}</h3>
            <p className="landing-feature-desc">{desc}</p>
          </div>
        ))}
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <span>© {new Date().getFullYear()} ApexFlow</span>
        <span>·</span>
        <Link href="/auth/login" className="landing-footer-link">Dashboard</Link>
      </footer>
    </div>
  );
}
