import Link from "next/link";

interface AuthCardProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer?: {
    label: string;
    linkText: string;
    href: string;
  };
}

export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <div className="auth-card">
      {/* Logo / Brand */}
      <div className="mb-8 flex flex-col items-center">
        <div className="auth-logo-mark">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <path
              d="M14 2L24 8V20L14 26L4 20V8L14 2Z"
              fill="url(#hexGrad)"
              stroke="rgba(139,92,246,0.4)"
              strokeWidth="1"
            />
            <path
              d="M14 7L19 10V16L14 19L9 16V10L14 7Z"
              fill="rgba(139,92,246,0.3)"
            />
            <defs>
              <linearGradient id="hexGrad" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                <stop stopColor="#8B5CF6" stopOpacity="0.8" />
                <stop offset="1" stopColor="#06B6D4" stopOpacity="0.6" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-white">{title}</h1>
        <p className="mt-1.5 text-sm text-zinc-400">{subtitle}</p>
      </div>

      {/* Form Content */}
      <div>{children}</div>

      {/* Footer Link */}
      {footer && (
        <p className="mt-6 text-center text-sm text-zinc-500">
          {footer.label}{" "}
          <Link
            href={footer.href}
            className="font-medium text-violet-400 hover:text-violet-300 transition-colors"
          >
            {footer.linkText}
          </Link>
        </p>
      )}
    </div>
  );
}
