import { AuthGuard } from "@/components/shared/AuthGuard";
import { TopBar } from "@/components/shared/TopBar";
import { Sidebar } from "@/components/shared/Sidebar";
import { ProjectProvider } from "@/features/projects/context";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ProjectProvider>
        <div className="dashboard-layout">
          <TopBar />
          <div className="dashboard-body">
            <Sidebar />
            <div className="dashboard-content-area">
              <main className="dashboard-main">{children}</main>
            </div>
          </div>
        </div>
      </ProjectProvider>
    </AuthGuard>
  );
}
