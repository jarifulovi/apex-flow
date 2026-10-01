import type { Metadata } from "next";
import { Header } from "@/components/shared/Header";
import { GitBranch, Filter } from "lucide-react";
import { DUMMY_WORKFLOWS } from "@/features/workflows/data";
import {
  WorkflowTable,
  WorkflowStatusBar,
} from "@/features/workflows/components/WorkflowTable";

export const metadata: Metadata = {
  title: "Workflows | ApexFlow",
  description: "Browse, inspect and manage all your registered workflows.",
};

export default function WorkflowsPage() {
  return (
    <div className="dashboard-page">
      <Header
        title="Workflows"
        subtitle="All registered workflows across your projects"
        actions={
          <div className="header-actions">
            <button className="action-btn action-btn--ghost" id="filter-workflows-btn">
              <Filter size={14} />
              Filter
            </button>
          </div>
        }
      />

      <div className="page-content">
        <WorkflowStatusBar workflows={DUMMY_WORKFLOWS} />

        <section className="dashboard-section" aria-labelledby="workflows-table-heading">
          <div className="dashboard-section-header">
            <GitBranch size={15} className="section-icon" />
            <h2 id="workflows-table-heading" className="dashboard-section-title">
              All Workflows
              <span className="section-count">{DUMMY_WORKFLOWS.length}</span>
            </h2>
          </div>
          <WorkflowTable workflows={DUMMY_WORKFLOWS} />
        </section>
      </div>
    </div>
  );
}
