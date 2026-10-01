"use client";

import { useState } from "react";
import { Terminal, Copy, Check } from "lucide-react";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }
  return (
    <button onClick={handleCopy} className="icon-btn hover:text-white" title="Copy code">
      {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
    </button>
  );
}

export function SDKQuickstart() {
  const [activeTab, setActiveTab] = useState<"python" | "curl" | "node">("python");

  const pythonCode = `import requests

API_URL = "http://localhost:8000/api/v1"
PROJECT_KEY = "af_live_your_secret_key_here"

headers = {
    "X-ApexFlow-Project-Key": PROJECT_KEY,
    "Content-Type": "application/json",
}

# 1. Create a Workflow Run
response = requests.post(
    f"{API_URL}/workflows",
    headers=headers,
    json={"name": "data_indexing_job"}
)
workflow = response.json()
print("Workflow initialized:", workflow["id"])

# 2. Queue a Step
requests.post(
    f"{API_URL}/steps",
    headers=headers,
    json={
        "workflow_id": workflow["id"],
        "step_name": "fetch_data",
        "input_payload": {"batch_size": 100}
    }
)`;

  const curlCode = `# 1. Initialize a workflow run
curl -X POST http://localhost:8000/api/v1/workflows \\
  -H "X-ApexFlow-Project-Key: af_live_your_secret_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "nightly_sync_job"}'

# 2. Poll the next queued step (FOR UPDATE SKIP LOCKED queue)
curl -X POST http://localhost:8000/api/v1/steps/poll \\
  -H "X-ApexFlow-Project-Key: af_live_your_secret_key_here"`;

  const nodeCode = `const API_URL = "http://localhost:8000/api/v1";
const PROJECT_KEY = "af_live_your_secret_key_here";

async function runWorkflow() {
  const res = await fetch(\`\${API_URL}/workflows\`, {
    method: "POST",
    headers: {
      "X-ApexFlow-Project-Key": PROJECT_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name: "export_user_data" }),
  });
  const workflow = await res.json();
  console.log("Workflow Run:", workflow.id);
}

runWorkflow();`;

  const snippets = {
    python: pythonCode,
    curl: curlCode,
    node: nodeCode,
  };

  return (
    <div className="bg-[#161620]/80 border border-white/10 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-violet-400" />
          <h3 className="text-sm font-semibold text-[#ececee]">SDK & Worker Quickstart</h3>
        </div>
        <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-lg border border-white/5">
          <button
            onClick={() => setActiveTab("python")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${activeTab === "python" ? "bg-violet-600 text-white shadow" : "text-zinc-400 hover:text-white"}`}
          >
            Python SDK
          </button>
          <button
            onClick={() => setActiveTab("curl")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${activeTab === "curl" ? "bg-violet-600 text-white shadow" : "text-zinc-400 hover:text-white"}`}
          >
            cURL
          </button>
          <button
            onClick={() => setActiveTab("node")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${activeTab === "node" ? "bg-violet-600 text-white shadow" : "text-zinc-400 hover:text-white"}`}
          >
            Node.js
          </button>
        </div>
      </div>

      <div className="relative bg-black/50 border border-white/5 rounded-xl p-4 font-mono text-xs text-violet-200 overflow-x-auto">
        <div className="absolute top-3 right-3">
          <CopyButton text={snippets[activeTab]} />
        </div>
        <pre className="pr-10 leading-relaxed whitespace-pre font-mono">{snippets[activeTab]}</pre>
      </div>
    </div>
  );
}
