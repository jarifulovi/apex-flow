import { AuthGuard } from "@/components/shared/AuthGuard";
import { Sidebar } from "@/components/shared/Sidebar";
import { Footer } from "@/components/shared/Footer";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="dashboard-layout">
        <Sidebar />
        <div className="dashboard-content-area">
          <main className="dashboard-main">
            {children}
          </main>
          <Footer />
        </div>
      </div>
    </AuthGuard>
  );
}
