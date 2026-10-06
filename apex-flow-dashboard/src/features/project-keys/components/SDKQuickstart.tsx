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

  const pythonCode = `# Install: pip install git+https://github.com/jarifulovi/apex-flow.git#subdirectory=sdks/python
import asyncio
from apex_flow_sdk import ApexFlowClient, WorkflowContext

client = ApexFlowClient(
    base_url="https://apex-flow-backend-kt5d.onrender.com",
    project_key="af_live_your_secret_key_here",
    worker_name="python-worker-1"
)

@client.workflow(name="data-indexing-job")
async def data_indexing_workflow(ctx: WorkflowContext, payload: dict):
    res = await ctx.step("fetch-data", lambda: {"batch_size": 100, "status": "ok"})
    return {"processed": True, "data": res}

async def main():
    run_id = await client.trigger_workflow("data-indexing-job")
    print("Workflow Run Queued:", run_id)
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)
    result = await data_indexing_workflow(ctx, {})
    print("Execution Result:", result)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())`;

  const curlCode = `# 1. Initialize a workflow run
curl -X POST https://apex-flow-backend-kt5d.onrender.com/api/v1/workflows \\
  -H "X-ApexFlow-Project-Key: af_live_your_secret_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{"workflow_name": "nightly_sync_job"}'

# 2. Poll the next queued step (FOR UPDATE SKIP LOCKED queue)
curl -X POST https://apex-flow-backend-kt5d.onrender.com/api/v1/steps/poll \\
  -H "X-ApexFlow-Project-Key: af_live_your_secret_key_here"`;

  const nodeCode = `const API_URL = "https://apex-flow-backend-kt5d.onrender.com/api/v1";
const PROJECT_KEY = "af_live_your_secret_key_here";

async function runWorkflow() {
  const res = await fetch(\`\${API_URL}/workflows\`, {
    method: "POST",
    headers: {
      "X-ApexFlow-Project-Key": PROJECT_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ workflow_name: "export_user_data" }),
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
