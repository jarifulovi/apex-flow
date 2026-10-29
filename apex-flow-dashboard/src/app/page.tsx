"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Copy,
  ExternalLink,
  GitBranch,
  Key,
  Layers,
  Lock,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
  Activity,
  Database,
  Clock,
  CheckCircle2,
  HeartHandshake,
  Mail,
} from "lucide-react";

const CODE_SNIPPET = `from apex_flow_sdk import ApexFlowClient, WorkflowContext

# 1. Initialize client with your project API key
client = ApexFlowClient(project_key="af_live_your_key_here")

# 2. Define workflow with durable, memoized steps
@client.workflow(name="customer-onboarding-pipeline")
async def onboard_customer(ctx: WorkflowContext, payload: dict):
    # Step 1: Create billing account (memoized on completion)
    account = await ctx.step(
        "create-stripe-customer",
        lambda: {"customer_id": f"cus_{payload['email'].split('@')[0]}"},
    )

    # Step 2: Provision cloud workspace (with automatic retries)
    workspace = await ctx.step(
        "provision-workspace",
        lambda: {"workspace_url": f"https://app.example.com/{account['customer_id']}"},
        max_attempts=3,
    )

    # Step 3: Send confirmation notification
    await ctx.step(
        "send-welcome-email",
        lambda: {"email_sent": True, "to": payload["email"]},
    )

    return {"status": "active", "workspace": workspace}

# 3. Start worker
if __name__ == "__main__":
    import asyncio
    asyncio.run(client.start_worker())`;

const STEPS = [
  {
    step: "01",
    title: "Create Your Account",
    desc: "Sign up on the ApexFlow cloud control plane in seconds. No credit card, complicated clusters, or database installations required.",
    icon: CheckCircle2,
    badge: "1-Click Setup",
  },
  {
    step: "02",
    title: "Generate Project Key",
    desc: "Head to Project Settings and generate your secure API key (af_live_...). Your workflows and workers are instantly tenant-isolated.",
    icon: Key,
    badge: "Scoped Auth",
  },
  {
    step: "03",
    title: "Connect with Python SDK",
    desc: "Install apex-flow-sdk via pip. Wrap your Python functions with @client.workflow and execute durable steps using ctx.step(...).",
    icon: Terminal,
    badge: "pip install apex-flow-sdk",
  },
  {
    step: "04",
    title: "Observe & Control Live",
    desc: "Track execution timelines in real time. Inspect step checkpoints, automatic retries, worker heartbeats, and client-decrypted payloads.",
    icon: Activity,
    badge: "Turnkey UI",
  },
];

const CAPABILITIES = [
  {
    icon: RefreshCw,
    title: "Durable Step Checkpointing",
    desc: "Each step is memoized upon completion. If a 5-step pipeline encounters a network glitch at Step 4, restarting it skips Steps 1–3 and resumes instantly at Step 4.",
  },
  {
    icon: Lock,
    title: "Zero-Knowledge Encryption (E2EE)",
    desc: "Sensitive payloads are encrypted on your worker using authenticated AES-256-GCM before transmission. The control plane holds only ciphertext, decrypted client-side in your browser.",
  },
  {
    icon: Zap,
    title: "Zero Infrastructure to Manage",
    desc: "Connect workers over standard HTTPS REST. No Kafka clusters, Redis brokers, or Cassandra databases to deploy, maintain, or keep alive.",
  },
  {
    icon: Layers,
    title: "Transparent Large Payload Offload",
    desc: "Payloads exceeding 250KB are transparently offloaded to Cloudflare R2 or S3 with lightweight pointer descriptors dereferenced automatically by the SDK.",
  },
  {
    icon: Clock,
    title: "Advanced Flow Control",
    desc: "Fine-grained step execution delays, run-level execution timeouts, integer priority queuing, and trigger event debouncing for rapid webhook bursts.",
  },
  {
    icon: GitBranch,
    title: "Time-Travel Debugging & Forking",
    desc: "Branch execution from any prior step checkpoint (POST .../fork?from_step=N) to diagnose bugs and replay altered inputs without re-running entire pipelines.",
  },
];

const COMPARISONS = [
  {
    feature: "Developer Ergonomics",
    apex: "Code-First (Python)",
    dbos: "Code-First (Python/TS)",
    temporal: "Complex SDK / DSL",
    celery: "Decorator-based",
  },
  {
    feature: "Infrastructure Setup",
    apex: "Zero Ops (REST API Key)",
    dbos: "Direct PostgreSQL Conn",
    temporal: "Heavy (Clusters + ES)",
    celery: "Medium (Redis / RabbitMQ)",
  },
  {
    feature: "Durable Step Resumption",
    apex: "✅ Yes (Step Memoization)",
    dbos: "✅ Yes",
    temporal: "✅ Yes",
    celery: "❌ No (Whole task fails)",
  },
  {
    feature: "Zero-Knowledge Encryption",
    apex: "✅ AES-256-GCM Client E2EE",
    dbos: "❌ No",
    temporal: "❌ Custom Data Converter",
    celery: "❌ No",
  },
  {
    feature: "Turnkey Web Dashboard",
    apex: "✅ Included (Next.js)",
    dbos: "❌ No native cloud UI",
    temporal: "✅ Heavy Web UI",
    celery: "⚠️ Basic (Flower)",
  },
  {
    feature: "Large Payload Offload",
    apex: "✅ Automatic R2/S3 (>250KB)",
    dbos: "❌ Manual",
    temporal: "⚠️ 2MB hard ceiling",
    celery: "❌ Broker bloat",
  },
  {
    feature: "Time-Travel Forking",
    apex: "✅ POST .../fork?from_step=N",
    dbos: "✅ Supported",
    temporal: "⚠️ Replay only",
    celery: "❌ No",
  },
];

function GithubIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

export default function LandingPage() {
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [copiedInstall, setCopiedInstall] = useState(false);

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(CODE_SNIPPET);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const handleCopyInstall = () => {
    navigator.clipboard.writeText("pip install apex-flow-sdk");
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  return (
    <div className="landing-layout">
      {/* Background Ambience */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
        <div className="auth-bg-grid" />
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />
      </div>

      {/* Header / Navigation */}
      <nav className="landing-nav">
        <div className="landing-nav-brand">
          <div className="auth-logo-mark" style={{ width: 38, height: 38, borderRadius: 10 }}>
            <svg width="22" height="22" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <path
                d="M14 2L24 8V20L14 26L4 20V8L14 2Z"
                fill="url(#hexGradLanding)"
                stroke="rgba(139,92,246,0.4)"
                strokeWidth="1"
              />
              <path d="M14 7L19 10V16L14 19L9 16V10L14 7Z" fill="rgba(139,92,246,0.3)" />
              <defs>
                <linearGradient id="hexGradLanding" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#8B5CF6" stopOpacity="0.8" />
                  <stop offset="1" stopColor="#06B6D4" stopOpacity="0.6" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="flex items-center gap-2">
            <span className="landing-brand-name">ApexFlow</span>
            <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30">
              v0.1.0
            </span>
          </div>
        </div>

        <div className="landing-nav-actions">
          {/* Open Source GitHub link */}
          <a
            href="https://github.com/jarifulovi/apex-flow"
            target="_blank"
            rel="noopener noreferrer"
            className="landing-nav-github"
            title="ApexFlow GitHub Repository"
          >
            <GithubIcon className="w-4 h-4 text-violet-400" />
            <span className="hidden sm:inline">Open Source</span>
          </a>

          <Link href="/auth/login" className="landing-nav-link">
            Sign in
          </Link>
          <Link href="/auth/signup" id="landing-cta-nav" className="landing-nav-cta">
            Get started
          </Link>
        </div>
      </nav>

      {/* Hero Section (No SDK at the top) */}
      <header className="landing-hero">
        <div className="landing-hero-badge">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>v0.1.0 Released</span>
          <span className="opacity-40">•</span>
          <span>Open-Source Durable Workflow Engine</span>
        </div>

        <h1 className="landing-hero-title">
          Durable workflows.
          <br />
          <span className="landing-hero-gradient">Zero infrastructure.</span>
        </h1>

        <p className="landing-hero-subtitle">
          ApexFlow is a lightweight, code-first workflow orchestration engine. Define durable,
          fault-tolerant Python pipelines with automatic step checkpointing, client-side zero-knowledge
          encryption, and instant observability—without managing complex brokers or database clusters.
        </p>

        <div className="landing-hero-actions">
          <Link href="/auth/signup" id="landing-cta-primary" className="landing-cta-primary">
            Start building free
            <ArrowRight size={17} />
          </Link>
          <Link href="/auth/login" id="landing-cta-secondary" className="landing-cta-secondary">
            Sign in to dashboard
          </Link>
          <a
            href="https://github.com/jarifulovi/apex-flow"
            target="_blank"
            rel="noopener noreferrer"
            className="landing-cta-secondary"
          >
            <GithubIcon className="w-4 h-4 text-violet-300" />
            Star on GitHub
          </a>
        </div>

        {/* Value Prop Ribbon */}
        <div className="landing-pill-ribbon">
          <div className="landing-pill">
            <Zap size={14} className="landing-pill-icon" />
            <span>Zero Ops (REST API Key)</span>
          </div>
          <div className="landing-pill">
            <RefreshCw size={14} className="landing-pill-icon" />
            <span>Automatic Step Memoization</span>
          </div>
          <div className="landing-pill">
            <Lock size={14} className="landing-pill-icon" />
            <span>Client AES-256-GCM E2EE</span>
          </div>
          <div className="landing-pill">
            <Layers size={14} className="landing-pill-icon" />
            <span>Auto Payload Offload (&gt;250KB)</span>
          </div>
        </div>
      </header>

      {/* How to Use at a Glance (The progressive 4-step onboarding journey) */}
      <section className="landing-section" aria-labelledby="quickstart-heading">
        <div className="landing-section-header">
          <div className="landing-section-badge">
            <Sparkles size={13} />
            <span>Quickstart Journey</span>
          </div>
          <h2 id="quickstart-heading" className="landing-section-title">
            How to use ApexFlow at a glance
          </h2>
          <p className="landing-section-subtitle">
            From zero to running resilient, durable production workflows in four straightforward steps.
          </p>
        </div>

        <div className="landing-steps-grid">
          {STEPS.map(({ step, title, desc, icon: Icon, badge }) => (
            <div key={step} className="landing-step-card">
              <div className="landing-step-header">
                <span className="landing-step-number">{step}</span>
                <div className="landing-step-icon">
                  <Icon size={18} />
                </div>
              </div>
              <h3 className="landing-step-title">{title}</h3>
              <p className="landing-step-desc">{desc}</p>
              <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-violet-300/80">
                <span>{badge}</span>
                {step === "03" && (
                  <button
                    onClick={handleCopyInstall}
                    className="p-1 hover:text-white transition-colors"
                    title="Copy pip install command"
                  >
                    {copiedInstall ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* 30-Second Python SDK Example */}
        <div className="landing-code-showcase">
          <div className="landing-code-header">
            <div className="landing-code-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <div className="landing-code-title">example_workflow.py — ApexFlow Python SDK</div>
            <button
              onClick={handleCopySnippet}
              className="landing-copy-btn"
              aria-label="Copy code snippet"
            >
              {copiedSnippet ? (
                <>
                  <Check size={13} className="text-emerald-400" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy size={13} />
                  <span>Copy Code</span>
                </>
              )}
            </button>
          </div>
          <pre className="landing-code">
            <code>{CODE_SNIPPET}</code>
          </pre>
        </div>
      </section>

      {/* Core Capabilities Grid */}
      <section className="landing-section" aria-labelledby="features-heading">
        <div className="landing-section-header">
          <div className="landing-section-badge">
            <ShieldCheck size={13} />
            <span>Enterprise Durability</span>
          </div>
          <h2 id="features-heading" className="landing-section-title">
            Engineered for resilience, speed, and privacy
          </h2>
          <p className="landing-section-subtitle">
            Everything required to orchestrate mission-critical workflows without the burden of managing
            complex distributed infrastructure.
          </p>
        </div>

        <div className="landing-features">
          {CAPABILITIES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="landing-feature-card">
              <div className="landing-feature-icon">
                <Icon size={20} />
              </div>
              <h3 className="landing-feature-title">{title}</h3>
              <p className="landing-feature-desc">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture & Engine Comparison Table */}
      <section className="landing-section" aria-labelledby="comparison-heading">
        <div className="landing-section-header">
          <div className="landing-section-badge">
            <Database size={13} />
            <span>Architecture Comparison</span>
          </div>
          <h2 id="comparison-heading" className="landing-section-title">
            How ApexFlow compares
          </h2>
          <p className="landing-section-subtitle">
            The code-first ergonomics of DBOS, paired with a turnkey, zero-ops cloud control plane.
          </p>
        </div>

        <div className="landing-table-wrap">
          <table className="landing-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th className="highlight-col">ApexFlow ⚡</th>
                <th>DBOS Transact</th>
                <th>Temporal.io</th>
                <th>Celery + Redis</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISONS.map((row) => (
                <tr key={row.feature}>
                  <td className="font-medium text-white">{row.feature}</td>
                  <td className="highlight-col font-semibold text-violet-200">{row.apex}</td>
                  <td>{row.dbos}</td>
                  <td>{row.temporal}</td>
                  <td>{row.celery}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Community, Contribution & Direct Help Banner */}
      <div className="landing-cta-banner">
        <div className="landing-cta-banner-glow" aria-hidden="true" />
        <div className="landing-section-badge mb-3 relative z-10">
          <HeartHandshake size={14} className="text-violet-400" />
          <span>Open Source & Community</span>
        </div>
        <h2 className="landing-cta-banner-title">Contribute, collaborate, or get direct help</h2>
        <p className="landing-cta-banner-desc">
          ApexFlow is 100% open source. Whether you want to contribute new language SDKs, report an edge case,
          propose architectural improvements, or need direct help setting up workflows in your stack—I&apos;d love to connect.
        </p>
        <div className="flex items-center gap-3.5 flex-wrap justify-center relative z-10">
          <a
            href="mailto:jarifulovi@gmail.com"
            className="landing-cta-primary"
            title="Send an email to jarifulovi@gmail.com"
          >
            <Mail size={16} />
            <span>jarifulovi@gmail.com</span>
          </a>
          <a
            href="https://github.com/jarifulovi/apex-flow"
            target="_blank"
            rel="noopener noreferrer"
            className="landing-cta-secondary"
            title="Contribute on GitHub"
          >
            <GithubIcon className="w-4 h-4 text-violet-300" />
            <span>Contribute on GitHub</span>
          </a>
        </div>
      </div>

      {/* Modern Developer Footer */}
      <footer className="landing-footer">
        <div className="flex items-center gap-3">
          <div className="auth-logo-mark" style={{ width: 26, height: 26, borderRadius: 6 }}>
            <svg width="14" height="14" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <path
                d="M14 2L24 8V20L14 26L4 20V8L14 2Z"
                fill="url(#hexGradLandingFoot)"
                stroke="rgba(139,92,246,0.4)"
                strokeWidth="1"
              />
              <defs>
                <linearGradient id="hexGradLandingFoot" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#8B5CF6" stopOpacity="0.8" />
                  <stop offset="1" stopColor="#06B6D4" stopOpacity="0.6" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span>© {new Date().getFullYear()} ApexFlow • Code-First Durable Orchestration</span>
        </div>

        <div className="landing-footer-links">
          <Link href="/dashboard" className="landing-footer-link">
            Dashboard
          </Link>
          <Link href="/auth/login" className="landing-footer-link">
            Sign In
          </Link>
          <Link href="/auth/signup" className="landing-footer-link">
            Sign Up
          </Link>
          <a
            href="https://github.com/jarifulovi/apex-flow"
            target="_blank"
            rel="noopener noreferrer"
            className="landing-footer-link flex items-center gap-1"
          >
            <span>GitHub</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </footer>
    </div>
  );
}
