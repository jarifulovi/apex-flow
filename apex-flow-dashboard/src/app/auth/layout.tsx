export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-layout">
      {/* Animated background grid */}
      <div className="auth-bg-grid" aria-hidden="true" />

      {/* Glowing orbs */}
      <div className="auth-orb auth-orb-1" aria-hidden="true" />
      <div className="auth-orb auth-orb-2" aria-hidden="true" />

      {/* Centered content */}
      <div className="auth-container">
        {children}
      </div>

      {/* Footer */}
      <footer className="auth-footer">
        <span>© {new Date().getFullYear()} ApexFlow. All rights reserved.</span>
      </footer>
    </div>
  );
}
