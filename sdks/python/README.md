# ApexFlow Python SDK (`apex-flow-sdk`)

> **Lightweight, Durable Workflow Orchestration Client for Python Applications.**

---

## 📦 Installation

```bash
pip install apex-flow-sdk
```

---

## 🚀 Quickstart Example

```python
import asyncio
from apex_flow_sdk import ApexFlowClient, WorkflowContext

client = ApexFlowClient(base_url="http://localhost:8000")

@client.workflow(name="process-lead-ai")
async def process_lead_workflow(ctx: WorkflowContext, user_input: str):
    # Step 1: Extract lead info
    extracted_data = await ctx.step(
        "extract-lead-info",
        lambda: {"name": "Alice", "company": "Acme Corp"},
        retries=3,
    )

    # Step 2: Create CRM record
    crm_record = await ctx.step(
        "create-crm-record",
        lambda: {"crm_id": "CRM-1002"},
    )

    return {"status": "completed", "crm_record": crm_record}
```
