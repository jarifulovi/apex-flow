"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BellRing,
  CalendarClock,
  Check,
  CheckCircle2,
  ChevronDown,
  Copy,
  ExternalLink,
  GitBranch,
  HeartHandshake,
  HelpCircle,
  Key,
  Layers,
  Lock,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Terminal,
} from "lucide-react";

type CodeTabKey = "onboarding" | "cron";

interface FaqItem {
  id: string;
  question: string;
  answer: string[];
}

const CODE_TABS: Record<
  CodeTabKey,
  { filename: string; label: string; badge: string; code: string }
> = {
  onboarding: {
    filename: "onboarding_workflow.py",
    label: "Durable Workflow",
    badge: "Python SDK",
    code: `from apex_flow_sdk import ApexFlowClient, WorkflowContext

# 1. Connect using your project API key
client = ApexFlowClient(project_key="af_live_your_key_here")

# 2. Define a durable workflow with automatic step recovery
@client.workflow(name="customer-onboarding-pipeline")
async def onboard_customer(ctx: WorkflowContext, payload: dict):
    # Step 1: Completed outputs are saved automatically
    account = await ctx.step(
        "create-stripe-customer",
        lambda: {"customer_id": f"cus_{payload['email'].split('@')[0]}"},
        retries=3,
    )

    # Step 2: Retries pick up right here without re-running Step 1
    workspace = await ctx.step(
        "provision-workspace",
        lambda: {"workspace_url": f"https://app.example.com/{account['customer_id']}"},
        retries=3,
    )

    # Step 3: Finish onboarding
    await ctx.step(
        "send-welcome-email",
        lambda: {"email_sent": True, "to": payload["email"]},
    )

    return {"status": "active", "workspace": workspace}

# 3. Start your Python worker
if __name__ == "__main__":
    import asyncio
    asyncio.run(client.start_worker())`,
  },
  cron: {
    filename: "scheduled_cron_worker.py",
    label: "Cron & Sub-Workflows",
    badge: "Built-in Scheduler",
    code: `from apex_flow_sdk import ApexFlowClient, WorkflowContext

# 1. Initialize client (reads APEXFLOW_PROJECT_KEY from environment)
client = ApexFlowClient(worker_name="metrics-cron-worker")

# 2. Schedule recurring runs directly on your workflow decorator
@client.workflow(
    name="nightly-metrics-sync",
    cron="*/15 * * * *",
    timezone="UTC",
)
async def sync_nightly_metrics(ctx: WorkflowContext, trigger_payload: dict):
    snapshot = await ctx.step(
        "extract-warehouse-rollup",
        lambda: {"rows_synced": 4820, "source": trigger_payload.get("trigger_source")},
        retries=3,
    )

    # Trigger an isolated child workflow tracked under this parent run
    child_run_id = await ctx.child_workflow(
        name="dispatch-analytics-digest",
        metadata={"rows_synced": snapshot["rows_synced"]},
    )

    return {"status": "dispatched", "child_run_id": str(child_run_id)}

# 3. Syncs your schedule on startup and listens for triggered runs
if __name__ == "__main__":
    import asyncio
    asyncio.run(client.start_worker())`,
  },
};

const STEPS = [
  {
    step: "01",
    title: "Create a Project",
    desc: "Sign up in seconds and create a project in your console—no clusters, message queues, or extra infrastructure to deploy.",
    icon: CheckCircle2,
    badge: "1-Click Setup",
  },
  {
    step: "02",
    title: "Grab Your API Key",
    desc: "Open Project Keys and copy an API key (af_live_...) to connect your local scripts or production Python workers securely.",
    icon: Key,
    badge: "Project Auth",
  },
  {
    step: "03",
    title: "Decorate Your Python Functions",
    desc: "Install apex-flow-sdk with pip, wrap async functions in @client.workflow, and run durable steps via ctx.step(...).",
    icon: Terminal,
    badge: "pip install apex-flow-sdk",
  },
  {
    step: "04",
    title: "Run & Monitor Live",
    desc: "Watch runs progress step by step, inspect payloads, trigger scheduled jobs on demand, or replay from any prior step.",
    icon: Activity,
    badge: "Web Console",
  },
];

const CAPABILITIES = [
  {
    icon: RefreshCw,
    title: "Step Checkpointing & Auto-Resume",
    accent: "text-violet-300 bg-violet-500/10 border-violet-500/20",
    badge: "Automatic Recovery",
    desc: "Completed steps are saved automatically. If a 5-step pipeline fails at Step 4, restarting skips Steps 1–3 and resumes right at Step 4.",
  },
  {
    icon: CalendarClock,
    title: "Declarative Cron & Scheduled Workflows",
    accent: "text-cyan-300 bg-cyan-500/10 border-cyan-500/20",
    badge: "Built-in Scheduler",
    desc: "Schedule recurring jobs directly on @client.workflow(cron='*/15 * * * *') or from the dashboard, complete with one-click Pause, Resume, and Run Now controls.",
  },
  {
    icon: GitBranch,
    title: "Time-Travel Replay & Sub-Workflows",
    accent: "text-fuchsia-300 bg-fuchsia-500/10 border-fuchsia-500/20",
    badge: "Interactive Debugging",
    desc: "Branch and replay a workflow from any prior step to test fixes without re-running earlier steps, or spawn linked child workflows.",
  },
  {
    icon: Lock,
    title: "End-to-End Payload Encryption",
    accent: "text-emerald-300 bg-emerald-500/10 border-emerald-500/20",
    badge: "Zero-Knowledge Privacy",
    desc: "Pass an encryption key in the Python client to encrypt sensitive step inputs and outputs locally before they ever leave your worker.",
  },
  {
    icon: Layers,
    title: "Seamless Large Payloads",
    accent: "text-sky-300 bg-sky-500/10 border-sky-500/20",
    badge: "Automatic Offloading",
    desc: "Pass large JSON objects and data payloads between steps without hitting queue size limits—the Python SDK handles offloading transparently.",
  },
  {
    icon: BellRing,
    title: "Instant Slack & Discord Alerts",
    accent: "text-amber-300 bg-amber-500/10 border-amber-500/20",
    badge: "Failure Notifications",
    desc: "Receive automatic notifications in Slack, Discord, or custom webhooks whenever a workflow fails, times out, or a worker goes offline.",
  },
];

const FAQ_ITEMS: FaqItem[] = [
  {
    id: "what-is-apexflow",
    question: "What is ApexFlow and who is it built for?",
    answer: [
      "ApexFlow is a code-first durable workflow orchestration platform built for Python developers who want reliable multi-step execution, retries, and scheduling without managing complex infrastructure.",
      "You keep writing ordinary async Python code while ApexFlow tracks run state, saves completed step results, coordinates cron triggers, and gives your team a turnkey dashboard to inspect, replay, or get alerted on failures.",
    ],
  },
  {
    id: "comparisons",
    question: "How does ApexFlow compare to Temporal, DBOS, and Celery?",
    answer: [
      "Temporal requires running or paying for heavy multi-service clusters and enforcing strict deterministic replay rules in your workflow code. ApexFlow runs over a simple API key with regular Python control flow and direct step-level replay.",
      "DBOS connects your workers directly to a production database over open DB ports and doesn’t ship a turnkey console. ApexFlow isolates workers behind HTTPS API keys and includes a full web console, client-side encryption, cron management, and alerting. Compared to Celery + Redis, where a failed job restarts from scratch, ApexFlow saves every step checkpoint so completed work is never repeated.",
    ],
  },
  {
    id: "supported-languages",
    question: "Which programming languages are supported?",
    answer: [
      "Python is supported today via the open-source apex-flow-sdk package (pip install apex-flow-sdk). It supports async and sync step functions, loops, child workflows, cron decorators, and optional client-side encryption.",
      "Additional language SDKs (such as TypeScript and Go) are on the open-source roadmap as the platform expands.",
    ],
  },
  {
    id: "where-code-runs",
    question: "Where does my workflow code actually run?",
    answer: [
      "All of your workflow functions and business logic execute strictly on your own compute—your laptop during development, containers, VMs, or cloud workers.",
      "Your workers stay completely in control of your data and third-party API secrets. ApexFlow never executes user code and only coordinates workflow state, schedules, and UI telemetry over HTTPS.",
    ],
  },
  {
    id: "how-cron-works",
    question: "How do scheduled cron workflows work?",
    answer: [
      "Add cron='*/15 * * * *' (and an optional IANA timezone like 'UTC') directly to @client.workflow(...), or create and edit schedules inside the Workflows -> Schedules tab in the dashboard.",
      "When your Python worker starts, it automatically syncs its schedule definitions with your project. From the dashboard, you can view human-readable schedules and next-run countdowns, pause or resume jobs without triggering missed backfills, or click Run Now to test an execution immediately.",
    ],
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
  const [activeCodeTab, setActiveCodeTab] = useState<CodeTabKey>("onboarding");
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [openFaqIds, setOpenFaqIds] = useState<Record<string, boolean>>({
    "what-is-apexflow": true,
  });

  const currentCodeTab = CODE_TABS[activeCodeTab];

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(currentCodeTab.code);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const handleCopyInstall = () => {
    navigator.clipboard.writeText("pip install apex-flow-sdk");
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  const allExpanded =
    FAQ_ITEMS.length > 0 && FAQ_ITEMS.every((item) => Boolean(openFaqIds[item.id]));

  const toggleFaqItem = (id: string) => {
    setOpenFaqIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleToggleAllFaqs = () => {
    const nextState = !allExpanded;
    const updated: Record<string, boolean> = {};
    for (const item of FAQ_ITEMS) {
      updated[item.id] = nextState;
    }
    setOpenFaqIds(updated);
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
              <path d="M14 7L19 10V16L14 19L9 16V10L14 7Z" fill="rgba(167,139,250,0.35)" />
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
            <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20">
              v0.1.0
            </span>
          </div>
        </div>

        <div className="landing-nav-actions">
          <a
            href="#faq-heading"
            className="landing-nav-link hidden md:inline-flex"
          >
            FAQ
          </a>
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

      {/* Hero Section */}
      <header className="landing-hero">
        <div className="landing-hero-badge">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>v0.1.0</span>
          <span className="opacity-40">&bull;</span>
          <span>Python SDK Available</span>
        </div>

        <h1 className="landing-hero-title">
          Durable workflows.
          <br />
          <span className="landing-hero-gradient">Zero infrastructure.</span>
        </h1>

        <p className="landing-hero-subtitle">
          Write resilient multi-step Python workflows and cron jobs using{" "}
          <code className="font-mono text-zinc-200">@client.workflow</code> and{" "}
          <code className="font-mono text-zinc-200">ctx.step</code>. Connect any worker with a
          single API key for automatic recovery, live observability, and zero infrastructure to host.
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
            <GithubIcon className="w-4 h-4 text-violet-400" />
            Star on GitHub
          </a>
        </div>

        {/* Value Prop Ribbon */}
        <div className="landing-pill-ribbon">
          <div className="landing-pill">
            <Terminal size={14} className="landing-pill-icon" />
            <span>Python SDK (pip install)</span>
          </div>
          <div className="landing-pill">
            <RefreshCw size={14} className="landing-pill-icon" />
            <span>Automatic Step Recovery</span>
          </div>
          <div className="landing-pill">
            <CalendarClock size={14} className="landing-pill-icon" />
            <span>Declarative Cron Jobs</span>
          </div>
          <div className="landing-pill">
            <Lock size={14} className="landing-pill-icon" />
            <span>Client-Side E2EE</span>
          </div>
          <div className="landing-pill">
            <Activity size={14} className="landing-pill-icon" />
            <span>Live Web Dashboard</span>
          </div>
        </div>
      </header>

      {/* How to Use & Dual-Tab Python Code Showcase */}
      <section className="landing-section" aria-labelledby="quickstart-heading">
        <div className="landing-section-header">
          <div className="landing-section-badge">
            <Sparkles size={13} />
            <span>Quickstart</span>
          </div>
          <h2 id="quickstart-heading" className="landing-section-title">
            How to use ApexFlow in Python
          </h2>
          <p className="landing-section-subtitle">
            Go from installing the Python SDK to running fault-tolerant pipelines and scheduled jobs
            in four simple steps.
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
              <div className="mt-auto pt-4">
                <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] font-mono text-zinc-400">
                  <span>{badge}</span>
                  {step === "03" && (
                    <button
                      type="button"
                      onClick={handleCopyInstall}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300 hover:bg-white/[0.08] hover:text-white transition-colors"
                      title="Copy pip install command"
                    >
                      {copiedInstall ? (
                        <>
                          <Check size={12} className="text-emerald-400" />
                          <span className="text-emerald-300">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Interactive Dual-Tab Python SDK Code Showcase */}
        <div className="landing-code-showcase">
          <div className="landing-code-header">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="landing-code-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div className="inline-flex items-center gap-1 p-0.5 rounded-lg bg-black/50 border border-white/[0.07]">
                {(Object.keys(CODE_TABS) as CodeTabKey[]).map((key) => {
                  const tab = CODE_TABS[key];
                  const isActive = activeCodeTab === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setActiveCodeTab(key)}
                      className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                        isActive
                          ? "bg-white/[0.09] text-zinc-100 border border-white/[0.12]"
                          : "text-zinc-400 hover:text-zinc-200 border border-transparent"
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
              <span className="landing-code-title hidden sm:inline">
                {currentCodeTab.filename}
              </span>
            </div>

            <div className="flex items-center gap-2.5">
              <span className="hidden md:inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-white/[0.04] text-zinc-300 border border-white/[0.08]">
                {currentCodeTab.badge}
              </span>
              <button
                type="button"
                onClick={handleCopySnippet}
                className="landing-copy-btn"
                aria-label="Copy code snippet"
              >
                {copiedSnippet ? (
                  <>
                    <Check size={13} className="text-emerald-400" />
                    <span className="text-emerald-300">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={13} />
                    <span>Copy Code</span>
                  </>
                )}
              </button>
            </div>
          </div>
          <pre className="landing-code">
            <code>{currentCodeTab.code}</code>
          </pre>
        </div>
      </section>

      {/* Core Capabilities Grid */}
      <section className="landing-section" aria-labelledby="features-heading">
        <div className="landing-section-header">
          <div className="landing-section-badge">
            <ShieldCheck size={13} />
            <span>Capabilities</span>
          </div>
          <h2 id="features-heading" className="landing-section-title">
            Everything you need to run reliable workflows
          </h2>
          <p className="landing-section-subtitle">
            Resilient step recovery, built-in cron scheduling, client-side encryption, and failure
            alerts&mdash;ready out of the box from Python.
          </p>
        </div>

        <div className="landing-features">
          {CAPABILITIES.map(({ icon: Icon, title, accent, badge, desc }) => (
            <div key={title} className="landing-feature-card">
              <div className="flex items-center justify-between gap-2">
                <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${accent}`}>
                  <Icon size={18} />
                </div>
                <span className="px-2.5 py-0.5 rounded-md bg-white/[0.03] border border-white/[0.07] text-[11px] font-mono text-zinc-400">
                  {badge}
                </span>
              </div>
              <h3 className="landing-feature-title mt-1">{title}</h3>
              <p className="landing-feature-desc">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Streamlined Questions Drawer */}
      <section className="landing-section" aria-labelledby="faq-heading">
        <div className="landing-section-header">
          <div className="landing-section-badge">
            <HelpCircle size={13} />
            <span>Questions &amp; Positioning</span>
          </div>
          <h2 id="faq-heading" className="landing-section-title">
            Frequently asked questions
          </h2>
          <p className="landing-section-subtitle">
            Learn how ApexFlow fits into your Python stack, how it compares to alternatives, and how
            your workflows stay under your control.
          </p>
        </div>

        <div className="w-full max-w-[880px] mx-auto">
          <div className="flex justify-end mb-3">
            <button
              type="button"
              onClick={handleToggleAllFaqs}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] hover:text-zinc-100 transition-colors"
            >
              {allExpanded ? "Collapse All" : "Expand All"}
            </button>
          </div>

          <div className="flex flex-col gap-3">
            {FAQ_ITEMS.map((item) => {
              const isOpen = Boolean(openFaqIds[item.id]);
              const panelId = `faq-panel-${item.id}`;

              return (
                <div
                  key={item.id}
                  className={`landing-faq-card${isOpen ? " landing-faq-card--open" : ""}`}
                >
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => toggleFaqItem(item.id)}
                    className="w-full px-5 sm:px-6 py-4 sm:py-5 flex items-center justify-between gap-4 text-left cursor-pointer"
                  >
                    <h3 className="text-[15px] sm:text-base font-semibold text-zinc-100 leading-snug">
                      {item.question}
                    </h3>

                    <span
                      className={`shrink-0 w-7 h-7 rounded-lg border flex items-center justify-center transition-all ${
                        isOpen
                          ? "bg-violet-500/15 border-violet-500/30 text-violet-200"
                          : "bg-white/[0.03] border-white/[0.08] text-zinc-400"
                      }`}
                      aria-hidden="true"
                    >
                      <ChevronDown
                        size={15}
                        className={`transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                      />
                    </span>
                  </button>

                  {isOpen && (
                    <div
                      id={panelId}
                      role="region"
                      className="px-5 sm:px-6 pb-5 sm:pb-6 pt-1 border-t border-white/[0.06]"
                    >
                      <div className="pt-3 space-y-2.5 text-sm text-zinc-400 leading-relaxed">
                        {item.answer.map((paragraph, index) => (
                          <p key={index}>{paragraph}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Community, Contribution & Direct Help Banner */}
      <div className="landing-cta-banner">
        <div className="landing-cta-banner-glow" aria-hidden="true" />
        <div className="landing-section-badge mb-3 relative z-10">
          <HeartHandshake size={14} className="text-violet-400" />
          <span>Open Source &amp; Community</span>
        </div>
        <h2 className="landing-cta-banner-title">Contribute, collaborate, or get direct help</h2>
        <p className="landing-cta-banner-desc">
          ApexFlow is 100% open source. Whether you want to contribute new language SDKs, report an
          edge case, propose improvements, or need direct help setting up Python workflows in your
          stack&mdash;I&apos;d love to connect.
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
            <GithubIcon className="w-4 h-4 text-violet-400" />
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
          <span>&copy; {new Date().getFullYear()} ApexFlow &bull; Code-First Durable Orchestration</span>
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
