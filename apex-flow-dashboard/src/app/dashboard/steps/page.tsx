"use client";

import { useState } from "react";
import { Header } from "@/components/shared/Header";
import { Footprints, Filter } from "lucide-react";
import { DUMMY_STEPS } from "@/features/steps/data";
import { StepsTable } from "@/features/steps/components/StepsTable";

const ALL_STATUSES = ["all", "queued", "running", "success", "failed"] as const;
type Filter = (typeof ALL_STATUSES)[number];

export default function StepsPage() {
  const [filter, setFilter] = useState<Filter>("all");

  const filtered =
    filter === "all" ? DUMMY_STEPS : DUMMY_STEPS.filter((s) => s.status === filter);

  return (
    <div className="dashboard-page">
      <Header
        title="Steps"
        subtitle="Track execution, attempts and errors across all workflow steps"
      />

      <div className="page-content">
        {/* Filter tabs */}
        <div className="filter-tabs" role="tablist" aria-label="Step status filter">
          {ALL_STATUSES.map((s) => (
            <button
              key={s}
              role="tab"
              aria-selected={filter === s}
              id={`tab-steps-${s}`}
              className={`filter-tab${filter === s ? " filter-tab--active" : ""}`}
              onClick={() => setFilter(s)}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
              <span className="filter-tab-count">
                {s === "all"
                  ? DUMMY_STEPS.length
                  : DUMMY_STEPS.filter((st) => st.status === s).length}
              </span>
            </button>
          ))}
        </div>

        <section className="dashboard-section" aria-labelledby="steps-table-heading">
          <div className="dashboard-section-header">
            <Footprints size={15} className="section-icon" />
            <h2 id="steps-table-heading" className="dashboard-section-title">
              Execution Steps
              <span className="section-count">{filtered.length}</span>
            </h2>
          </div>
          <StepsTable steps={filtered} />
        </section>
      </div>
    </div>
  );
}
