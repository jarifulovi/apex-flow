import { AuthGuard } from "@/components/shared/AuthGuard";
import { Sidebar } from "@/components/shared/Sidebar";
import { Footer } from "@/components/shared/Footer";
import { ProjectProvider } from "@/features/projects/context";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ProjectProvider>
        <div className="dashboard-layout">
          <Sidebar />
          <div className="dashboard-content-area">
            <main className="dashboard-main">
              {children}
            </main>
            <Footer />
          </div>
        </div>
      </ProjectProvider>
    </AuthGuard>
  );
}
