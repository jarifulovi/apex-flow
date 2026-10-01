import type { Metadata } from "next";
import { Header } from "@/components/shared/Header";
import { KeyRound, ShieldCheck } from "lucide-react";
import { DUMMY_PROJECT_KEYS } from "@/features/project-keys/data";
import {
  ProjectKeyList,
  CreateKeyButton,
} from "@/features/project-keys/components/ProjectKeyList";

export const metadata: Metadata = {
  title: "Project Keys | ApexFlow",
  description: "Create and manage API keys to authenticate your SDK workers.",
};

const activeCount = DUMMY_PROJECT_KEYS.filter((k) => k.status === "active").length;

export default function ProjectKeysPage() {
  return (
    <div className="dashboard-page">
      <Header
        title="Project Keys"
        subtitle="API keys used to authenticate your SDK workers against the backend"
        actions={<CreateKeyButton />}
      />

      <div className="page-content">
        {/* Info banner */}
        <div className="info-banner">
          <ShieldCheck size={16} className="text-violet-400 shrink-0" />
          <p className="info-banner-text">
            Keys are shown <strong>once</strong> at creation. Store them securely — ApexFlow only
            stores a SHA-256 hash. Revoke unused keys promptly.
          </p>
        </div>

        <section className="dashboard-section" aria-labelledby="keys-heading">
          <div className="dashboard-section-header">
            <KeyRound size={15} className="section-icon" />
            <h2 id="keys-heading" className="dashboard-section-title">
              Your Keys
              <span className="section-count">{activeCount} active</span>
            </h2>
          </div>
          <ProjectKeyList keys={DUMMY_PROJECT_KEYS} />
        </section>
      </div>
    </div>
  );
}
