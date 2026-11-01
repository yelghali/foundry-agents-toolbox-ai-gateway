---
published: true
type: workshop
title: Choose your Foundry agent identity with Toolbox and AI Gateway
short_title: Foundry identity lab
description: Explore native Azure Search MCP or custom FastMCP with project, agent or user identity through Toolbox, and collect real authorization evidence.
level: advanced
authors:
  - Yael El Ghali
contacts:
  - https://github.com/yelghali
duration_minutes: 150
navigation_levels: 2
tags: azure, foundry, agents, identity, mcp, toolbox, api-management, python
audience: developers, solution architects
sections_title:
  - Welcome and choose a track
  - Architecture and trust boundaries
  - Prerequisites and safety
  - Deploy the shared foundation
  - A - Project identity
  - B - Agent identity
  - C native - Managed user access
  - C custom - OAuth and FastMCP
  - Compare results and troubleshoot
  - Cleanup and next steps
---

# Welcome: choose the identity your workload needs

Deploy **one** hosted agent; prove **who can access its tools** with an allow and a deny.
Clone the [repository](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway)
to execute commands locally. MOAW is the reading experience, not a terminal.
Each sample is independently copyable and does not import the root lab.

## Choose one independent track

| Need | Track | Data principal | Time after setup |
| --- | --- | --- | --- |
| Shared native KB or custom API access across a project | A | Project managed identity | 45 minutes |
| Separate native KB or custom API access for each agent | B | Calling agent instance identity | 60 minutes |
| Search access follows the signed-in user | C native | User via managed `UserEntraToken` | 60 minutes |
| Custom API with delegated OAuth scopes | C custom | User authorizing the OAuth connection | 75 minutes |

- Alternatives, **not sequential exercises**. C custom needs no Search KB.
- A and B each offer **native Azure Search KB MCP** and **custom FastMCP** targets.
  The custom target is an application/agent-token API, not C's delegated OAuth server.
  Custom A/B connection configuration and local JWT tests do not by themselves
  establish live Toolbox custom-audience acquisition; require downstream token evidence.
- Budget 60–90 minutes for setup/evidence/cleanup, plus deployment/RBAC propagation.
  The 150-minute estimate covers one track.
- Reuse compatible infrastructure or choose optional foundation replay.
- Learn to separate caller, runtime, connection and data identities; invoke an
  Active pinned version and capture genuine tool allow/deny evidence.

**Before deploying:** write your track, expected principal, token audience and negative test.

---

# Architecture: where authorization actually happens

![Toolbox identity and gateway boundaries](assets/workshop-architecture.svg)

- Caller: Entra token for `https://ai.azure.com/.default`.
- Hosted runtime: `FoundryChatClient` + `FoundryToolbox`;
  `ResponsesHostServer` supplies hosted context.
- Connection: selects downstream authentication. Provisioning ARM token **≠ data token**.
- Search/API: validates downstream token and permissions. APIM cannot replace this boundary.

| Track | Connection authentication | Downstream audience | Authorization |
| --- | --- | --- | --- |
| A | `ProjectManagedIdentity` | `https://search.azure.com` | Project MI Search RBAC |
| B | `AgenticIdentityToken` | `https://search.azure.com` | Calling instance Search RBAC |
| A custom | `ProjectManagedIdentity` | Registered custom API audience | Validated project principal + role or explicit allowlist |
| B custom | `AgenticIdentityToken` | Registered custom API audience | Validated agent principal + role or explicit allowlist; experimental until observed |
| C native | `UserEntraToken` | `https://search.azure.com` | User Search RBAC |
| C custom | OAuth2 authorization code + refresh | Custom API v2 audience | JWT validation + delegated scope |

**Native ≠ custom OAuth:** native uses platform-managed user context; custom uses
authorization code and `offline_access`. Neither sample captures JWT-bearer OBO.
A user `oid` proves delegated identity, not grant type.
For A/B custom, Toolbox must acquire the API token itself. The agent and APIM
must not exchange tokens. An ARM connection accepting `audience` is not proof
that the hosted identity can acquire that audience.

[Full architecture](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/architecture.svg)
adds optional prompt-agent, raw Search and gateway paths.

**Boundary check:** why does granting the invoking developer Search access not fix B?

---

# Prerequisites, permissions and safety

## Required before deployment

- Dedicated learning resources in your own tenant/subscription; synthetic data only.
- Windows, PowerShell, Git, Azure CLI/Bicep; Python 3.12 for root tooling,
  Python 3.13 for hosted sample builds.
- Foundry account/project, existing chat deployment (default `gpt-4o-mini`),
  hosted-agent/Toolbox preview access and sufficient regional quota.
- Optional Bicep replay: existing **APIM Standard v2**; `deploy.ps1` rejects other SKUs.
  Dedicated `AIGateway` is a separate optional Terraform/portal path.
- A/B custom: a separately registered Entra API, HTTPS-reachable application-token
  FastMCP server, and permission to authorize the intended project/agent principal.
  Do not configure the C delegated-only deployment to accept application tokens.
- C custom: Azure Developer CLI supporting `azd ai connection create`,
  two Entra registrations and an HTTPS-reachable FastMCP host.
- No account? Use approved Azure provisioning or the
  [Terraform guide](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/terraform/README.md).
  Decide resource ownership before mixing Terraform and Bicep.

## Permission owners

| Owner | Required authority |
| --- | --- |
| Infrastructure deployer | Resource deployment in lab/Foundry groups; RBAC assignment write at affected scopes (e.g. Contributor + scoped RBAC Administrator) |
| Project administrator/provisioner | Connection write, Toolbox create/update; invoker Azure AI User/project-agent access; runtime model/Toolbox access |
| Search RBAC administrator | Search Index Data Reader for the selected A/B/native data object ID |
| Entra application administrator/developer | Custom API/client registration, permissions and required tenant consent/assignment |
| Intended user | Tenant sign-in policy and any connection authorization |

**Project access ≠ data access.** Subscription ownership does not grant Entra app
permissions. Use actual Entra object IDs, not ARM IDs/client IDs/agent names.
Provisioners create connections/Toolboxes only: no apps, consent, roles or hosted deployment.
B requires a supported platform calling identity; tenant/preview admins may need to enable it.

## Costs and secrets

- Replay creates **three Basic Search services**, three projects and three telemetry
  pairs even for one track. Budget for Search, tokens, hosting, APIM and log ingestion;
  no fixed price/free tier is promised.
- Never commit `.config.json`, secrets, tokens, runtime keys or live evidence.
- C custom uses interactive secret entry. azd passes the secret in child-process
  arguments: trusted workstation only, no debug output, rotate afterward.
- Validated claims/logs are sensitive. `store=false` does not guarantee no diagnostic
  logging or zero provider retention.

**Checkpoint:** confirm tenant/subscription, quota, permission scopes and cleanup ownership.
Unavailable preview? Inspect offline; do not report a live authorization success.

---

# Deploy the shared foundation

## Choose your setup

- **Own infrastructure:** Foundry project/model/hosted runtime. Native A/B/C also need
  a synthetic Search index, knowledge source and trusted KB. Record project endpoint/ARM ID,
  Search ARM ID, KB MCP URL and marker. Custom A/B instead need their registered API,
  application-token HTTPS server and exact expected principal IDs; C custom needs
  its separate delegated OAuth apps/HTTPS API.
- **Optional repository replay below:** creates all three cohorts in reviewed resources.
  APIM, `.config.json` and root `provision.py` are **not** standalone prerequisites.
- Clone/install/sign in; verify the displayed tenant/subscription:

```powershell
git clone https://github.com/yelghali/foundry-agents-toolbox-ai-gateway.git
Set-Location .\foundry-agents-toolbox-ai-gateway
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements-dev.txt
az login --tenant "<tenant-id>"
az account set --subscription "<subscription-id>"
az account show --query "{tenant:tenantId,subscription:id,name:name}" -o json
```

- Pick a new lab group; fixed `abc-a/b/c` project names must not collide.
  Review [infra.bicep](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/infra.bicep)
  and [projects.bicep](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/projects.bicep):

```powershell
.\deploy.ps1 `
  -SubscriptionId "<subscription-id>" `
  -FoundryResourceGroup "<foundry-rg>" `
  -FoundryAccountName "<foundry-account>" `
  -ApimResourceGroup "<apim-rg>" `
  -ApimName "<standard-v2-apim>" `
  -ResourceGroup "rg-foundry-identity-workshop" `
  -SearchLocation "swedencentral" `
  -ModelDeployment "gpt-4o-mini"
```

- Requires existing Foundry/APIM/model; does not deploy a model.
  Writes `.config.json`. Projects/roles live in the **existing Foundry account**;
  Search/telemetry live in the new group.
- Seed only your A/B/native cohort; creates index/marker/source/KB/root tools and
  `evidence\foundation.json`. **B/C remove an existing project Search reader role**:
  never run on a shared project.

```powershell
python .\provision.py --cohort a # choose a, b or c
$config = Get-Content .\.config.json -Raw | ConvertFrom-Json
$cohort = $config.cohorts | Where-Object label -eq "a" # match selected cohort
$cohort.project | Format-List
$cohort | Select-Object searchId, searchEndpoint, knowledgeBaseName, marker
```

- Build the KB MCP URL using your sample README's format; retain the marker locally.
- **Do not run `setup.ps1` for one track:** it provisions all cohorts/agents/gateway routes.
- Checkpoint: locate project/KB/marker, then jump to your track. Deployment ≠ authorization proof.

## Publish only the selected hosted sample

- After that track's provisioner, activate its venv and work **inside its sample folder**.
- Set deployment values; local variables are not automatically forwarded remotely:

```powershell
$env:TOOLBOX_ENDPOINT = "<endpoint printed by selected provisioner>"
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = "<existing chat deployment>"
$env:AGENT_NAME = "<new hosted agent name>"
```

- Save this as `publish_hosted.py` there; run `python .\publish_hosted.py`.
  Same API as the [root publisher](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/publish_agents.py),
  but packages **only** the selected sample, not the root multi-agent lab:

```python
import io
import os
import zipfile
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CodeConfiguration, HostedAgentDefinition, ProtocolVersionRecord,
)
from azure.identity import AzureCliCredential

source = Path(__file__).resolve().parent
with io.BytesIO() as archive:
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for filename in ("hosted_agent.py", "requirements.txt"):
            bundle.write(source / filename, filename)
    archive.seek(0)
    credential = AzureCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
    with AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential,
    ) as project:
        version = project.agents.create_version_from_code(
            agent_name=os.environ["AGENT_NAME"], code=archive,
            definition=HostedAgentDefinition(
                cpu="0.5", memory="1Gi",
                code_configuration=CodeConfiguration(
                    runtime="python_3_13",
                    entry_point=["python", "hosted_agent.py"],
                    dependency_resolution="remote_build",
                ),
                protocol_versions=[
                    ProtocolVersionRecord(protocol="responses", version="2.0.0"),
                ],
                environment_variables={
                    key: os.environ[key] for key in (
                        "FOUNDRY_PROJECT_ENDPOINT",
                        "AZURE_AI_MODEL_DEPLOYMENT_NAME", "TOOLBOX_ENDPOINT",
                    )
                },
            ),
        )
        print("Agent version:", version.version)
        print("Deployment status:", version.status)
```

- Foundry **Agents → selected version**: inspect build/start diagnostics; wait for **Active**.
  A version number is not readiness. Pin it as `AGENT_VERSION`.
- **Identity**: obtain the actual calling instance object ID; project admin grants
  runtime project/model/Toolbox access (lab publisher uses project-scoped Azure AI User).
  B additionally needs that instance's Search role. Never substitute another MI.
- Preview differs? Follow the
  [official hosting workflow](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent).
  Its `azd deploy` needs its own manifests, absent from these bare samples.
  An existing correctly configured Active version may skip publishing.

---

# A: project managed identity

![A flow: invoking user to hosted agent, Toolbox project identity and Search RBAC](assets/workshop-project-identity.svg)

The hosted agent calls Toolbox; `ProjectManagedIdentity` selects the project identity.
Choose native Search KB MCP or custom FastMCP. The downstream service, not the
invoking developer, validates and authorizes retrieval.

| Target choice | Who hosts MCP / authorizes access? |
| --- | --- |
| **Azure Search MCP** | Azure's service-provided KB contract; Search RBAC grants the project MI Search Index Data Reader. No custom server. |
| **Custom FastMCP** | Your HTTPS server validates application JWTs for your API audience and allowlists the project MI object ID. No Search RBAC or delegated-user identity. |

## Azure Search MCP

<details>
<summary>Deploy A: prerequisites, roles and commands</summary>

### Prerequisites / registration

- Shared project data privileges are intentional. The commands below deploy the
  unchanged native target; for custom FastMCP follow the separate target setup in
  [A's runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/README.md).
- Resource owner enables project MI; Search admin grants **project MI object ID**
  Search Index Data Reader. Replay A already grants it: verify, do not broaden.
- Project admin grants invoker/runtime access. **No custom OAuth apps, secret,
  callback or per-user downstream OAuth consent**; tenant sign-in policies still apply.
  This statement applies to native Search: custom A requires an API registration,
  but no delegated OAuth client, callback or manual agent token exchange.

### Deployment checklist

- From clone root, install/configure/provision with fresh names:

```powershell
Set-Location .\samples\project-identity
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant "<tenant-id>"
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview"
$env:CONNECTION_NAME = "my-project-kb"
$env:TOOLBOX_NAME = "my-project-tools"
python .\provision_toolbox.py
```

- Search admin assigns the verified object ID:

```powershell
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = "<project-managed-identity-object-id>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type ServicePrincipal --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

- Use **Publish only the selected hosted sample** above; wait for Active, then invoke:

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <synthetic test document>."
$env:EXPECTED_TEXT = "<known marker>"
python .\invoke_hosted.py
```

</details>

### Agent code → Toolbox

Hosted environment only for this identity test. Complete
[A runbook/scripts](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/README.md).
The provisioner selects `ProjectManagedIdentity`; the agent does not acquire Search tokens manually.

```python
import asyncio
import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential

async def main():
    credential = DefaultAzureCredential()
    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            credential=credential,
        ),
        tools=FoundryToolbox(
            credential, name="retrieval", url=os.environ["TOOLBOX_ENDPOINT"],
        ),
        instructions="Return actual requested Toolbox results/errors; never invent markers or identities.",
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()

if __name__ == "__main__":
    asyncio.run(main())
```

Input: project/model and Toolbox endpoint. Output: a hosted Responses agent; the runtime does not acquire a Search token.

### Toolbox configuration → Search connection

This excerpt from [the A provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/provision_toolbox.py)
defines the ARM connection payload and its Toolbox tool; the complete script submits both.

```python
import os
from azure.ai.projects.models import MCPToolboxTool

target = os.environ["MCP_SERVER_URL"]
project_id = os.environ["FOUNDRY_PROJECT_RESOURCE_ID"].rstrip("/")
connection_id = f"{project_id}/connections/{os.environ['CONNECTION_NAME']}"
connection_payload = {"properties": {
    "category": "RemoteTool", "authType": "ProjectManagedIdentity",
    "target": target, "audience": "https://search.azure.com",
    "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
}}
tool = MCPToolboxTool(
    name="retrieve", server_label="knowledge", server_url=target,
    project_connection_id=connection_id, require_approval="never",
)
```

Input: KB URL and project connection ID. Output: a connection-authenticated tool, not an agent-side `MCPTool`.

### Service-provided MCP contract

For the native choice, no custom server is required. Search supplies the trusted KB endpoint:

```text
https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview
Agent request: retrieve <synthetic test document> using the advertised retrieval tool
Tool input/output schema: discover from this KB's MCP tools/list, not a guessed signature
Result: actual retrieval content containing <known marker>, or authorization failure
```

## Custom FastMCP

**Custom target flow:** hosted agent → Toolbox (`ProjectManagedIdentity`) →
your API's `/mcp` → JWT validation + project-principal ACL → `identity_probe`.

### Connection and hosted agent

Keep the hosted code above unchanged and use a **fresh custom-target connection
and Toolbox**. The selected A connection remains `ProjectManagedIdentity`; its
target becomes the HTTPS API's `/mcp` URL and its audience must match the registered
API's actual token audience. Do not assume the Search audience works for this API.

In the copied A folder, start `python .\custom_server.py` with
`AZURE_TENANT_ID`, `CUSTOM_MCP_AUDIENCE` (the v2 API client-ID GUID), and
`CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS` (only the project MI object ID).
Expose its `/mcp` over HTTPS. In the provisioner's shell set
`CUSTOM_MCP_SERVER_URL`, the same `CUSTOM_MCP_AUDIENCE`, and fresh
`CONNECTION_NAME`/`TOOLBOX_NAME`; run `python .\provision_custom_toolbox.py`.
Use its printed endpoint for a separate hosted version. API registration and
ACL-only application access prerequisites are in the complete sample below.

```python
# Custom target connection shape, not an agent-side token exchange.
import os

custom_connection_payload = {"properties": {
    "category": "RemoteTool", "authType": "ProjectManagedIdentity",
    "target": os.environ["CUSTOM_MCP_SERVER_URL"],
    "audience": os.environ["CUSTOM_MCP_AUDIENCE"],
    "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
}}
```

The [complete A sample](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/README.md)
provides custom provisioning and server setup. The separate application-token
server validates JWT signature, tenant issuer, exact audience and expiry before
authorization. It requires the expected project principal, and a configured
explicit principal allowlist (ACL, not role enforcement); it must reject delegated-user
tokens. Call `identity_probe(experiment_id="<synthetic UUID>")`; the tool returns
`CUSTOM_MCP_APPLICATION_VALIDATED` and safe validated identifier claims, not JWTs
or arbitrary queries. The complete server prints validated query/result audit
events to stdout; protect those logs and captured results.

### Server code → validated project identity

Run the [full A `custom_server.py`](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/custom_server.py).
This compact equivalent uses its **required** validator, ASGI boundary and
request-scoped `ContextVar`; save beside that file, not as an unauthenticated
`mcp.run()` server. The boundary validates signature, v2 tenant issuer, exact
audience, expiry and the principal ACL, rejects delegated tokens, then sets and
resets `IDENTITY` around dispatch.

```python
import logging
import os
import uuid

import uvicorn
from fastmcp import FastMCP
from custom_server import ApplicationTokenValidator, EntraBoundary, IDENTITY

mcp = FastMCP("Application identity probe", include_fastmcp_meta=False)
logger = logging.getLogger("custom_mcp.identity")

@mcp.tool
def identity_probe(experiment_id: str) -> dict:
    experiment_id = str(uuid.UUID(experiment_id))
    identity = IDENTITY.get()
    if identity is None:
        raise RuntimeError("Validated application identity required")
    logger.info("project probe experiment=%s tid=%s oid=%s",
                experiment_id, identity["tid"], identity["oid"])
    return {"marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
            "experiment_id": experiment_id, "claims": identity}

if __name__ == "__main__":
    validator = ApplicationTokenValidator(
        os.environ["AZURE_TENANT_ID"],
        os.environ["CUSTOM_MCP_AUDIENCE"],
        [v.strip() for v in os.environ["CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS"].split(",")],
    )
    app = EntraBoundary(
        mcp.http_app(path="/mcp", stateless_http=True, json_response=True), validator,
    )
    uvicorn.run(app, host="0.0.0.0", port=8000,
                access_log=False, log_level="warning")
```

Inputs: `CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS` contains only the **project MI object
ID**, never the invoking user ID; audience is the registered v2 API client-ID GUID.
Output: validated identifier claims and marker. The optional INFO log is off by
default; enable only in a protected lab sink, never log bearer tokens.

**Custom proof:** request the advertised tool with a known marker, then use a
different non-authorized project. Require a backend allow/deny and validated
principal evidence. Local signed-token tests are not live Toolbox evidence.
**Custom acquisition needs live verification:** an accepted connection payload or
native Search success is not proof. The isolated A replay below did acquire a
custom-audience application token and correlated its validated project principal.

**One proof exercise:** retrieve the marker, then use a fresh connection to a separate
test KB where the project MI lacks access. Require actual tool authorization denial,
not model text. Correlate Active version/time, role scope and backend audit where available.
A second authorized caller must not change the data principal. Never remove shared roles;
label configuration inference separately from captured identity evidence. Continue to cleanup.

## Optional APIM evidence: A native and custom MCP

Fresh Azure hosted-agent executions on **November 1, 2026**, on the existing pinned `obs-20261031-*` routes. Original defaults are unchanged; no direct-route success is mixed into these results. Only public synthetic data was submitted. Body diagnostics are isolated (8192 bytes; no headers). Authorization/tokens, opaque consent identifiers/URLs and SDK session baggage are excluded from exports; nonsensitive queries/results are preserved.

### Live replay — a-native: PASS_NATIVE_MCP_QUERY_RESULT

Agent `obs-20261031-a-native` v2; Toolbox v2. UTC `2026-11-01T11:30:31.301838+00:00` → `2026-11-01T11:30:53.958986+00:00`. Experiment `d8606504-9ef8-4924-bb65-cb81cdd7bf51`.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call retrieve_kb_a exactly once with arguments {"query": "Find the normal access record in cohort A"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47`; status **completed**.

Actual hosted answer (model text; verify against the tool evidence below):


```text
The normal access record for cohort A is **COHORT_A_ONLY_D900EADA82**.
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/call`; request `4a6c451d-2366-4887-b6f6-b85611ef913b`; backend HTTP **200**.

UTC request `2026-11-01T11:30:51.0553478Z`; response `2026-11-01T11:30:53.6784309Z`.

Actual generated tool `observed___knowledge_base_retrieve` arguments:


```json
{
  "queries": [
    "Find the normal access record in cohort A"
  ]
}
```


Actual MCP response content:


```json
[
  {
    "type": "text",
    "text": "The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.",
    "_meta": {
      "x-request-id": "10f344ca-9891-4cb6-81a7-c73ff6336d9c"
    }
  },
  {
    "type": "text",
    "text": "{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}",
    "_meta": {
      "x-request-id": "10f344ca-9891-4cb6-81a7-c73ff6336d9c",
      "title": "Cohort A access record",
      "preserveExactValue": false
    }
  }
]
```


**3. Downstream MCP/runtime logs: what was actually observed**

Native Search MCP response is observed through APIM. Search's internal query/fan-out and service-owned console logs are **NOT_OBSERVED**; no internal query is reconstructed.

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T11:45:38.250082+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T11:30:51.017240410+00:00`.


```text
2026-11-01 11:30:51,017 INFO agent_framework: Function name: observed___knowledge_base_retrieve
```


UTC `2026-11-01T11:30:53.660194490+00:00`.


```text
2026-11-01 11:30:53,656 INFO agent_framework: Function observed___knowledge_base_retrieve succeeded.
```


<details>

<summary>Real logged exchange — a-native: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1`. Configured downstream target: `https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview` (configuration is not execution evidence).

Caller-context SHA-256: `mkZ8VlfiFfE79alJvyLel2HZ1PNcA7hz9XxwjRNg1hU=`.

Exact captured request (only sensitive baggage redacted):


```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-93f7d26f0231ba06e8c9b05f8d1c6883-771f98de90a58c19-01","baggage":"<baggage-redacted>","generateCitations":true,"KnowledgeSourceMetadata":[{"name":"ks-a","type":"searchIndex"}],"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"name":"observed___knowledge_base_retrieve","arguments":{"queries":["Find the normal access record in cohort A"]}},"jsonrpc":"2.0","id":3}
```


Exact captured response:


```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {"_meta":{"agenticReasoningTokens":28,"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"content":[{"type":"text","text":"The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.","_meta":{"x-request-id":"10f344ca-9891-4cb6-81a7-c73ff6336d9c"}},{"type":"text","text":"{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}","_meta":{"x-request-id":"10f344ca-9891-4cb6-81a7-c73ff6336d9c","title":"Cohort A access record","preserveExactValue":false}}],"structuredContent":null}
}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "822d6e3e-5eb3-4e71-b7a0-a43a3fd6ca80",
    "callerContextPresent": "True",
    "callerContextHash": "mkZ8VlfiFfE79alJvyLel2HZ1PNcA7hz9XxwjRNg1hU=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "requestTimestamp": "2026-11-01T11:30:43.9288587Z",
    "requestBody": "{\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"sampling\":{}},\"clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"}},\"jsonrpc\":\"2.0\",\"id\":0}",
    "responseTimestamp": "2026-11-01T11:30:44.4842478Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 0,\n  \"result\": {\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"tools\":{},\"tasks\":{\"list\":{},\"cancel\":{},\"requests\":{\"tools\":{\"call\":{}}}},\"resources\":{\"listChanged\":false,\"subscribe\":false},\"extensions\":{\"io.modelcontextprotocol/skills\":{}}},\"serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "87df1617-8bf9-4151-bcad-f1aa1042980c",
    "callerContextPresent": "True",
    "callerContextHash": "mkZ8VlfiFfE79alJvyLel2HZ1PNcA7hz9XxwjRNg1hU=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "requestTimestamp": "2026-11-01T11:30:47.5386346Z",
    "requestBody": "{\"method\":\"notifications/initialized\",\"jsonrpc\":\"2.0\"}",
    "responseTimestamp": "2026-11-01T11:30:48.2776489Z",
    "responseBody": "<empty-body>",
    "backendStatus": 204
  },
  {
    "apimRequestId": "0310578f-ff85-44d9-a324-a435201ff004",
    "callerContextPresent": "True",
    "callerContextHash": "mkZ8VlfiFfE79alJvyLel2HZ1PNcA7hz9XxwjRNg1hU=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "requestTimestamp": "2026-11-01T11:30:48.3868407Z",
    "requestBody": "{\"method\":\"ping\",\"jsonrpc\":\"2.0\",\"id\":1}",
    "responseTimestamp": "2026-11-01T11:30:48.4400076Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 1,\n  \"result\": {}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "4ffeee0f-8b50-4ff4-be62-007d74c3920b",
    "callerContextPresent": "True",
    "callerContextHash": "mkZ8VlfiFfE79alJvyLel2HZ1PNcA7hz9XxwjRNg1hU=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "requestTimestamp": "2026-11-01T11:30:48.4575515Z",
    "requestBody": "{\"method\":\"tools/list\",\"jsonrpc\":\"2.0\",\"id\":2}",
    "responseTimestamp": "2026-11-01T11:30:49.8580289Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 2,\n  \"result\": {\"tools\":[{\"name\":\"observed___knowledge_base_retrieve\",\"description\":\"Use knowledge_base_retrieve to search for information or documents that must be authoritative and attributable to a source. This knowledge base is always relevant to the user and any organizations they're affiliated with. You may call this tool with ambiguous queries to retrieve relevant context before asking the user for further clarification. If a Knowledge Base Description is provided, use it to understand what content is included/excluded and to scope your retrieval.\\n\\nUse queries for exactly one complete, natural-language user question or request, not keyword searches, fragments, or rewritten search syntax. Copy the user's information need as a full natural-language question or request. Within that question, include VERBATIM every distinctive token from the user: proper nouns, acronyms (CIA, GDPR), multi-word organization or product names, alphanumeric identifiers (QX-9000, v2.1.4, L1997-00-0351), quoted phrases, version strings, exact filter terms (\\\"conference papers only\\\", \\\"non-paywalled\\\"), group/sort/include/exclude directives, and negation/limit directives (\\\"exclude contractors\\\", \\\"exclude news coverage\\\", \\\"no more than 10\\\", \\\"only include public companies\\\"). Ranges, dates, and numeric thresholds also stay as written. Query in the user's language; do not translate exact terms or quoted phrases. Preserve version strings and multi-word expressions such as tax deferred and official records as written. For temporal, as-of, date range, fiscal year, quarter, and recency constraints, preserve the exact time constraint in the query. The retrieval backend performs expansion. Do not split values of one unresolved constraint into parallel calls. Reserve parallel calls for independent information needs.\\n\\nExamples:\\n\\n\\t// User Query: Which vendor owned Project Helios between 2021 and 2024?\\n\\targuments: {\\\"queries\\\": [\\\"Which vendor owned Project Helios between 2021 and 2024?\\\"]}\\n\\n\\t// User Query: Find the QX-9000 price sheet; it may be called a rate card, quote sheet, or SKU list.\\n\\targuments: {\\\"queries\\\": [\\\"Find the QX-9000 price sheet; it may be called a rate card, quote sheet, or SKU list.\\\"]}\\n\\n\\t// User Query: Find official records about \\\"rate card\\\" changes, include public companies only, and exclude forum posts.\\n\\targuments: {\\\"queries\\\": [\\\"Find official records about \\\\\\\"rate card\\\\\\\" changes, include public companies only, and exclude forum posts.\\\"]}\\nKnowledge Base Description - Foundry IQ Toolbox RBAC live-test knowledge base.\\r\\n\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"queries\":{\"description\":\"Use queries for exactly one complete, natural-language user question or request (max 400 characters; ideally under 70 words), not keyword searches, fragments, or rewritten search syntax. Copy the user's information need as a full question/request using the user's own words and language, preserving entities, references, identifiers, ranges, aliases, filters, exact terms, quoted phrases, grouping directives, comparison directives, version strings, and multi-word expressions without translating them.\\n\\nAlways return a JSON array of strings, even when issuing a single query. Example: {\\\"queries\\\": [\\\"What was Contoso's fiscal year 2024 revenue?\\\"]}.\",\"type\":\"array\",\"items\":{\"type\":\"string\",\"maxLength\":400},\"minItems\":1,\"maxItems\":1}},\"required\":[\"queries\"],\"additionalProperties\":false,\"$schema\":\"https://json-schema.org/draft/2020-12/schema\"},\"_meta\":{\"generateCitations\":true,\"KnowledgeSourceMetadata\":[{\"name\":\"ks-a\",\"type\":\"searchIndex\"}],\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"retrieve_kb_a\",\"server_label\":\"observed\",\"server_url\":\"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary\",\"original_type\":\"mcp\"}},\"execution\":{\"taskSupport\":\"optional\"}}]}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "4a6c451d-2366-4887-b6f6-b85611ef913b",
    "callerContextPresent": "True",
    "callerContextHash": "mkZ8VlfiFfE79alJvyLel2HZ1PNcA7hz9XxwjRNg1hU=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "requestTimestamp": "2026-11-01T11:30:51.0553478Z",
    "requestBody": "{\"method\":\"tools/call\",\"params\":{\"_meta\":{\"traceparent\":\"00-93f7d26f0231ba06e8c9b05f8d1c6883-771f98de90a58c19-01\",\"baggage\":\"<baggage-redacted>\",\"generateCitations\":true,\"KnowledgeSourceMetadata\":[{\"name\":\"ks-a\",\"type\":\"searchIndex\"}],\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"retrieve_kb_a\",\"server_label\":\"observed\",\"server_url\":\"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary\",\"original_type\":\"mcp\"}},\"name\":\"observed___knowledge_base_retrieve\",\"arguments\":{\"queries\":[\"Find the normal access record in cohort A\"]}},\"jsonrpc\":\"2.0\",\"id\":3}",
    "responseTimestamp": "2026-11-01T11:30:53.6784309Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 3,\n  \"result\": {\"_meta\":{\"agenticReasoningTokens\":28,\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"retrieve_kb_a\",\"server_label\":\"observed\",\"server_url\":\"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary\",\"original_type\":\"mcp\"}},\"content\":[{\"type\":\"text\",\"text\":\"The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.\",\"_meta\":{\"x-request-id\":\"10f344ca-9891-4cb6-81a7-c73ff6336d9c\"}},{\"type\":\"text\",\"text\":\"{\\\"kind\\\":\\\"reference\\\",\\\"ref_id\\\":0,\\\"uri\\\":\\\"mcp://searchindex/normal\\\",\\\"mimeType\\\":\\\"application/json\\\",\\\"sourceData\\\":{\\\"id\\\":\\\"normal\\\",\\\"title\\\":\\\"Cohort A access record\\\",\\\"content\\\":\\\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\\\"}}\",\"_meta\":{\"x-request-id\":\"10f344ca-9891-4cb6-81a7-c73ff6336d9c\",\"title\":\"Cohort A access record\",\"preserveExactValue\":false}}],\"structuredContent\":null}\n}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
  "object": "response",
  "output": [
    {
      "type": "function_call",
      "id": "fc_0a15ddabde2870bf00wUtXKXezwRim76LR5LjrgPu2IJ0hOo0k",
      "call_id": "call_eTzuB9gvZVpePVIFKEA0D7uk",
      "name": "observed___knowledge_base_retrieve",
      "arguments": "{\"queries\":[\"Find the normal access record in cohort A\"]}",
      "status": "completed",
      "response_id": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
      "agent_reference": null
    },
    {
      "type": "function_call_output",
      "id": "fco_0a15ddabde2870bf00dHWaYOz9COI7jb8Dol2LyhP93sqKLyE8",
      "call_id": "call_eTzuB9gvZVpePVIFKEA0D7uk",
      "output": "The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.\n{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}",
      "status": "completed",
      "response_id": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
      "agent_reference": null
    },
    {
      "type": "message",
      "id": "msg_0a15ddabde2870bf00dI2QLvtsYjBPP8YRGUMxoQkLCl9EggSy",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "The normal access record for cohort A is **COHORT_A_ONLY_D900EADA82**.",
          "annotations": [],
          "logprobs": []
        }
      ],
      "status": "completed",
      "response_id": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
      "agent_reference": null
    }
  ],
  "created_at": 1793532641,
  "parallel_tool_calls": false,
  "status": "completed",
  "completed_at": 1793532654,
  "usage": {
    "input_tokens": 1627,
    "input_tokens_details": {
      "cached_tokens": 0,
      "cache_write_tokens": 0
    },
    "output_tokens": 50,
    "output_tokens_details": {
      "reasoning_tokens": 0
    },
    "total_tokens": 1677
  },
  "response_id": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-a-native",
    "version": "2"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
```


Runtime query result:


```json
{
  "scenario": "a-native",
  "agent": "obs-20261031-a-native",
  "version": "2",
  "experimentId": "d8606504-9ef8-4924-bb65-cb81cdd7bf51",
  "responseId": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
  "invocationStartedAt": "2026-11-01T11:30:31.301838+00:00",
  "invocationCompletedAt": "2026-11-01T11:30:53.958986+00:00",
  "queriedAt": "2026-11-01T11:45:38.250082+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.301144417+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.306586867+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.710540412+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,710 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.857698198+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,857 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,888 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.889011939+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.891683668+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,891 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.891835629+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,891 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.892372554+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,892 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.892485617+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,892 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.958866538+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,958 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.959539741+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,959 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.959775594+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,959 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.959846918+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,959 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.960942710+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,959 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.961365853+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 11:30:31 +0000] [44] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:31.961387472+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:31,961 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:32.166710605+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:32,166 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: eb3714e1a78f5c9891e468b66ae05c90)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:32.167525713+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:32,167 INFO azure.ai.agentserver: 192.168.0.1:40416 \"GET /readiness 1.1\" 200 20 1063\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:32.167711873+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:32,167 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.8ms (trace-id: eb3714e1a78f5c9891e468b66ae05c90)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:41.612960658+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:41,612 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 93f7d26f0231ba06e8c9b05f8d1c6883, x-ms-client-request-id: 50050814-7e45-481f-9fa7-0c86ae0d7954, trace-id: 93f7d26f0231ba06e8c9b05f8d1c6883)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:41.614843153+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:41,613 INFO azure.ai.agentserver: Creating response caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:41.614843153+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:41,614 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:41.934836813+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:41,934 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:44.461745350+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:44,461 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:44.462953034+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:44,462 INFO mcp.client.streamable_http: Negotiated protocol version: 2025-11-25"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:44.465680021+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:44,465 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:44.466319566+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:44,465 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:44.466481134+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:44,466 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:46.719869436+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:46,719 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.280742674+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,280 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 204 No Content\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.283109258+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,281 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.283109258+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,281 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.283109258+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,282 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.415280462+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,415 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.418153965+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,418 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.418349205+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,418 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:48.418627555+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:48,418 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:49.832329587+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:49,832 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:49.942087519+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:49,942 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:49.942313309+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:49,942 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:49.942418223+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:49,942 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:50.718579742+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:50,718 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:51.017240410+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:51,017 INFO agent_framework: Function name: observed___knowledge_base_retrieve"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:51.020439268+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:51,019 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:51.020439268+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:51,019 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:51.020439268+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:51,019 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:51.720958932+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:51,720 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:51.721549889+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:51,721 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:52.094601549+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:52,094 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:53.653336081+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:53,653 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:53.660194490+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:53,656 INFO agent_framework: Function observed___knowledge_base_retrieve succeeded."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:53.660194490+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:53,656 INFO agent_framework: Function duration: 2.639175s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:54.610664848+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:54,610 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:54.830060910+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:54,829 INFO azure.ai.agentserver: Response caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47 completed: status=completed output_count=3"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:54.830450687+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:54,830 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:54.831110123+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:54,831 INFO azure.ai.agentserver: 192.168.0.1:34452 \"POST /responses 1.1\" 200 1997 13218432\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:54.831311419+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:54,831 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 13218.1ms (x-request-id: 93f7d26f0231ba06e8c9b05f8d1c6883, x-ms-client-request-id: 50050814-7e45-481f-9fa7-0c86ae0d7954, trace-id: 93f7d26f0231ba06e8c9b05f8d1c6883)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:54.831466553+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:54,831 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:55.351969987+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:55,351 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:55.352254814+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:55,352 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:30:55.352348741+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:30:55,352 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential\n"
    }
  ],
  "status": "CAPTURED_CORRELATED_LINES",
  "limitation": "Bounded console SSE read, filtered to this pinned session's invocation time window. Sensitive and unrelated lines excluded; session IDs remain memory-only. Not a complete invocation log.",
  "cliStatus": "NOT_RETRIED",
  "source": "SDK get_session_log_stream; unique version/time-matched session"
}
```


Local full sources: `evidence\observability-a-native.json`, `evidence\observability-a-native-apim.json`.

</details>

<details>

<summary>Hosted service snapshot — a-native</summary>


```json
{
  "source": "evidence/observability-a-native.json#agentResponse",
  "responseId": "caresp_0a15ddabde2870bf006ESxstcTQy7QnstF1vpNBvP40kJaqo47",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___knowledge_base_retrieve",
      "call_id": "call_eTzuB9gvZVpePVIFKEA0D7uk",
      "arguments": "{\"queries\":[\"Find the normal access record in cohort A\"]}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_eTzuB9gvZVpePVIFKEA0D7uk",
      "output": "The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.\n{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}",
      "status": "completed"
    }
  ],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

### Live replay — a-custom: PASS_VALIDATED_APPLICATION_MCP_QUERY_RESULT

Agent `obs-20261031-a-custom` v1; Toolbox v1. UTC `2026-11-01T11:31:40.631888+00:00` → `2026-11-01T11:31:54.208049+00:00`. Experiment `4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e`.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call identity_probe exactly once with arguments {"experiment_id": "4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ`; status **completed**.

Actual hosted answer (model text; verify against the tool evidence below):


```text
{"marker":"CUSTOM_MCP_APPLICATION_VALIDATED","experiment_id":"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e","claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0"}}
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/call`; request `57b474e0-a134-412f-b590-0a01ffd6b783`; backend HTTP **200**.

UTC request `2026-11-01T11:31:53.1160014Z`; response `2026-11-01T11:31:53.346469Z`.

Actual generated tool `observed___identity_probe` arguments:


```json
{
  "experiment_id": "4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e"
}
```


Actual MCP result:


```json
{
  "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
  "experiment_id": "4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e",
  "claims": {
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
    "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
    "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
    "ver": "2.0"
  }
}
```


**3. Downstream MCP/runtime logs: what was actually observed**

Custom MCP console `tools/call` query/result is correlated by the experiment UUID; its returned result equals the APIM result.


```json
{
  "azureTimestamp": "2026-11-01T11:31:53.3344454+00:00",
  "event": "validated_mcp_exchange",
  "timestamp": "2026-11-01T11:31:53.334220+00:00",
  "method": "tools/call",
  "tool": "identity_probe",
  "query": {
    "experiment_id": "4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e"
  },
  "result": {
    "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
    "experiment_id": "4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e",
    "claims": {
      "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
      "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
      "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
      "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
      "ver": "2.0"
    }
  }
}
```


Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T11:46:20.153693+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T11:31:53.080653415+00:00`.


```text
2026-11-01 11:31:53,080 INFO agent_framework: Function name: observed___identity_probe
```


UTC `2026-11-01T11:31:53.325028462+00:00`.


```text
2026-11-01 11:31:53,324 INFO agent_framework: Function observed___identity_probe succeeded.
```


<details>

<summary>Real logged exchange — a-custom: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1`. Configured downstream target: `https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` (configuration is not execution evidence).

Caller-context SHA-256: `6onNNuAjiWiwac4yWAXUJbyp+oAgupRO4S59gcFFxkU=`.

Exact captured request (only sensitive baggage redacted):


```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-fea8003f21f77e6e51b4d1bf7796c674-25ada6bb63ddfb9a-01","baggage":"<baggage-redacted>","tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"name":"observed___identity_probe","arguments":{"experiment_id":"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e"}},"jsonrpc":"2.0","id":3}
```


Exact captured response:


```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {"_meta":{"tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"content":[{"type":"text","text":"{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\"}}"}],"isError":false,"structuredContent":{"marker":"CUSTOM_MCP_APPLICATION_VALIDATED","experiment_id":"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e","claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0"}}}
}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "1a47fde3-303b-4b0e-ae38-83eb7aa3ca98",
    "callerContextPresent": "True",
    "callerContextHash": "6onNNuAjiWiwac4yWAXUJbyp+oAgupRO4S59gcFFxkU=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "requestTimestamp": "2026-11-01T11:31:50.6718676Z",
    "requestBody": "{\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"sampling\":{}},\"clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"}},\"jsonrpc\":\"2.0\",\"id\":0}",
    "responseTimestamp": "2026-11-01T11:31:50.8283179Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 0,\n  \"result\": {\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"tools\":{},\"tasks\":{\"list\":{},\"cancel\":{},\"requests\":{\"tools\":{\"call\":{}}}},\"resources\":{\"listChanged\":false,\"subscribe\":false},\"extensions\":{\"io.modelcontextprotocol/skills\":{}}},\"serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "4ce7f097-18d1-4fe6-b287-a63a37da9e23",
    "callerContextPresent": "True",
    "callerContextHash": "6onNNuAjiWiwac4yWAXUJbyp+oAgupRO4S59gcFFxkU=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "requestTimestamp": "2026-11-01T11:31:50.8413289Z",
    "requestBody": "{\"method\":\"notifications/initialized\",\"jsonrpc\":\"2.0\"}",
    "responseTimestamp": "2026-11-01T11:31:50.8693776Z",
    "responseBody": "<empty-body>",
    "backendStatus": 204
  },
  {
    "apimRequestId": "268a5819-ec9a-4422-8d53-2450266ae4af",
    "callerContextPresent": "True",
    "callerContextHash": "6onNNuAjiWiwac4yWAXUJbyp+oAgupRO4S59gcFFxkU=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "requestTimestamp": "2026-11-01T11:31:50.9137721Z",
    "requestBody": "{\"method\":\"ping\",\"jsonrpc\":\"2.0\",\"id\":1}",
    "responseTimestamp": "2026-11-01T11:31:50.9423746Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 1,\n  \"result\": {}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "0bc46561-e058-4fa7-9d12-39e10e5267ef",
    "callerContextPresent": "True",
    "callerContextHash": "6onNNuAjiWiwac4yWAXUJbyp+oAgupRO4S59gcFFxkU=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "requestTimestamp": "2026-11-01T11:31:51.2195597Z",
    "requestBody": "{\"method\":\"tools/list\",\"jsonrpc\":\"2.0\",\"id\":2}",
    "responseTimestamp": "2026-11-01T11:31:51.7460367Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 2,\n  \"result\": {\"tools\":[{\"name\":\"observed___identity_probe\",\"description\":\"Return validated application identifiers for a nonsensitive experiment UUID.\",\"inputSchema\":{\"properties\":{\"experiment_id\":{\"type\":\"string\"}},\"required\":[\"experiment_id\"],\"type\":\"object\",\"$schema\":\"https://json-schema.org/draft/2020-12/schema\"},\"outputSchema\":{\"additionalProperties\":true,\"type\":\"object\",\"$schema\":\"https://json-schema.org/draft/2020-12/schema\"},\"_meta\":{\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"identity_probe\",\"server_label\":\"observed\",\"server_url\":\"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data\",\"original_type\":\"mcp\"}}}]}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "57b474e0-a134-412f-b590-0a01ffd6b783",
    "callerContextPresent": "True",
    "callerContextHash": "6onNNuAjiWiwac4yWAXUJbyp+oAgupRO4S59gcFFxkU=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "requestTimestamp": "2026-11-01T11:31:53.1160014Z",
    "requestBody": "{\"method\":\"tools/call\",\"params\":{\"_meta\":{\"traceparent\":\"00-fea8003f21f77e6e51b4d1bf7796c674-25ada6bb63ddfb9a-01\",\"baggage\":\"<baggage-redacted>\",\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"identity_probe\",\"server_label\":\"observed\",\"server_url\":\"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data\",\"original_type\":\"mcp\"}},\"name\":\"observed___identity_probe\",\"arguments\":{\"experiment_id\":\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\"}},\"jsonrpc\":\"2.0\",\"id\":3}",
    "responseTimestamp": "2026-11-01T11:31:53.346469Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 3,\n  \"result\": {\"_meta\":{\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"identity_probe\",\"server_label\":\"observed\",\"server_url\":\"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data\",\"original_type\":\"mcp\"}},\"content\":[{\"type\":\"text\",\"text\":\"{\\\"marker\\\":\\\"CUSTOM_MCP_APPLICATION_VALIDATED\\\",\\\"experiment_id\\\":\\\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\\\",\\\"claims\\\":{\\\"tid\\\":\\\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\\\",\\\"oid\\\":\\\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\\\",\\\"aud\\\":\\\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\\\",\\\"iss\\\":\\\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\\\",\\\"ver\\\":\\\"2.0\\\"}}\"}],\"isError\":false,\"structuredContent\":{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\"}}}\n}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
  "object": "response",
  "output": [
    {
      "type": "function_call",
      "id": "fc_042de0d323ac21ca00qQCmVAgTODrgzMNSNixDqLxm6wI90rIl",
      "call_id": "call_BUf9EZKP0N9znu7vmDa6NQ8A",
      "name": "observed___identity_probe",
      "arguments": "{\"experiment_id\":\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\"}",
      "status": "completed",
      "response_id": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
      "agent_reference": null
    },
    {
      "type": "function_call_output",
      "id": "fco_042de0d323ac21ca00pOh2Ar27wIyCrfJzdyOgQQRW0xAsfVHM",
      "call_id": "call_BUf9EZKP0N9znu7vmDa6NQ8A",
      "output": "{\"marker\": \"CUSTOM_MCP_APPLICATION_VALIDATED\", \"experiment_id\": \"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\", \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\"}}",
      "status": "completed",
      "response_id": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
      "agent_reference": null
    },
    {
      "type": "message",
      "id": "msg_042de0d323ac21ca00FngnlXt6C5sOn57vVgHRrQakbLR8a78c",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\"}}",
          "annotations": [],
          "logprobs": []
        }
      ],
      "status": "completed",
      "response_id": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
      "agent_reference": null
    }
  ],
  "created_at": 1793532709,
  "parallel_tool_calls": false,
  "status": "completed",
  "completed_at": 1793532715,
  "usage": {
    "input_tokens": 474,
    "input_tokens_details": {
      "cached_tokens": 0,
      "cache_write_tokens": 0
    },
    "output_tokens": 210,
    "output_tokens_details": {
      "reasoning_tokens": 0
    },
    "total_tokens": 684
  },
  "response_id": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-a-custom",
    "version": "1"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
```


Runtime query result:


```json
{
  "scenario": "a-custom",
  "agent": "obs-20261031-a-custom",
  "version": "1",
  "experimentId": "4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e",
  "responseId": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
  "invocationStartedAt": "2026-11-01T11:31:40.631888+00:00",
  "invocationCompletedAt": "2026-11-01T11:31:54.208049+00:00",
  "queriedAt": "2026-11-01T11:46:20.153693+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:40.401740514+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:40.406532641+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:40.891146604+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:40,890 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.029591638+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,029 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,059 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.060830193+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.063488386+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,063 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.063640334+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,063 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.064060818+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,064 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.064159357+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,064 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.130607327+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,130 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.131201626+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,131 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.131425621+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,131 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.131492988+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,131 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.132532452+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,131 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.132925198+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 11:31:41 +0000] [36] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.132944065+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,132 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.500049878+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,499 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 023834f65eb37d25d194817013df0a06)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.500860498+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,500 INFO azure.ai.agentserver: 192.168.0.1:56198 \"GET /readiness 1.1\" 200 20 1163\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:41.501039588+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:41,501 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.8ms (trace-id: 023834f65eb37d25d194817013df0a06)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:49.937530096+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:49,937 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: fea8003f21f77e6e51b4d1bf7796c674, x-ms-client-request-id: dee580f2-b101-416d-b3ae-5596860b850d, trace-id: fea8003f21f77e6e51b4d1bf7796c674)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:49.942221258+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:49,939 INFO azure.ai.agentserver: Creating response caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:49.942221258+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:49,940 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.296195210+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,296 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.802273924+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,802 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.803897414+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,803 INFO mcp.client.streamable_http: Negotiated protocol version: 2025-11-25"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.806878489+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,806 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.807572232+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,807 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.807697719+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,807 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.844514207+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,844 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 204 No Content\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.845728174+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,845 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.845929294+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,845 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.846019495+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,846 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.915813222+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,915 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.918567712+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,918 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.918712565+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,918 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:50.918809458+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:50,918 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:51.720794608+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:51,720 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:51.835839833+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:51,835 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:51.836094161+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:51,836 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:51.836198115+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:51,836 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:52.666196718+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:52,666 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.080653415+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,080 INFO agent_framework: Function name: observed___identity_probe"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.082899710+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,082 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.083072001+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,083 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.083158821+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,083 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.320888861+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,320 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.325028462+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,324 INFO agent_framework: Function observed___identity_probe succeeded."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.325903429+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,325 INFO agent_framework: Function duration: 0.244103s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:53.888055614+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:53,887 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:55.080147197+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:55,080 INFO azure.ai.agentserver: Response caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ completed: status=completed output_count=3"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:55.080519004+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:55,080 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:55.081132546+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:55,081 INFO azure.ai.agentserver: 192.168.0.1:50236 \"POST /responses 1.1\" 200 2317 5144800\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:55.081341223+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:55,081 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 5142.8ms (x-request-id: fea8003f21f77e6e51b4d1bf7796c674, x-ms-client-request-id: dee580f2-b101-416d-b3ae-5596860b850d, trace-id: fea8003f21f77e6e51b4d1bf7796c674)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:55.081483403+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:55,081 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:56.384616403+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:56,384 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:56.385631861+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:56,385 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:56.386149927+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:56,386 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:31:56.617654955+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:31:56,617 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential\n"
    }
  ],
  "status": "CAPTURED_CORRELATED_LINES",
  "limitation": "Bounded console SSE read, filtered to this pinned session's invocation time window. Sensitive and unrelated lines excluded; session IDs remain memory-only. Not a complete invocation log.",
  "cliStatus": "NOT_RETRIED",
  "source": "SDK get_session_log_stream; unique version/time-matched session"
}
```


Local full sources: `evidence\observability-a-custom.json`, `evidence\observability-a-custom-apim.json`.

</details>

<details>

<summary>Hosted service snapshot — a-custom</summary>


```json
{
  "source": "evidence/observability-a-custom.json#agentResponse",
  "responseId": "caresp_042de0d323ac21ca00nAXJhV0xLy0eJw9L6tKnaq6XLSlvkSbJ",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___identity_probe",
      "call_id": "call_BUf9EZKP0N9znu7vmDa6NQ8A",
      "arguments": "{\"experiment_id\":\"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\"}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_BUf9EZKP0N9znu7vmDa6NQ8A",
      "output": "{\"marker\": \"CUSTOM_MCP_APPLICATION_VALIDATED\", \"experiment_id\": \"4d578de3-3c13-487f-bdfc-d4dbf8dd4c1e\", \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\"}}",
      "status": "completed"
    }
  ],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

---

# B: calling agent identity

![B flow: user invocation, hosted calling identity and instance-specific Search role](assets/workshop-agent-identity.svg)

The same agent-to-Toolbox integration now uses `AgenticIdentityToken` on the connection.
Search must authorize the calling instance, not the project MI.

| Target choice | Who hosts MCP / authorizes access? |
| --- | --- |
| **Azure Search MCP** | Azure's service-provided KB contract; Search RBAC grants the calling agent instance Search Index Data Reader. No custom server. |
| **Custom FastMCP** | Your HTTPS server validates application JWTs for your API audience and allowlists verified calling-agent principal object IDs. Not the user, project MI or blueprint ID. |

## Azure Search MCP

<details>
<summary>Deploy B: prerequisites, calling identity, roles and commands</summary>

### Prerequisites / registration

- Separate agent data privileges; choose native Search KB or custom FastMCP.
  The commands below retain the native deployment. Custom target setup is separate in
  [B's runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/README.md).
- Platform identity workflow creates/configures blueprint + calling instance,
  **not a manually registered confidential OAuth client**.
- Project admin grants invoker/runtime access; Search admin grants **calling instance
  object ID**, not blueprint/client ID/version, Search Index Data Reader.
- No custom OAuth secret/callback/per-user downstream consent. Tenant/preview admin
  may need to enable identity creation; local execution is not an equivalent test.
  Custom B does need a separately registered API and authorized agent principals.

### Deployment checklist

- From clone root, install/configure/provision:

```powershell
Set-Location .\samples\agent-identity
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant "<tenant-id>"
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview"
$env:CONNECTION_NAME = "my-agent-kb"
$env:TOOLBOX_NAME = "my-agent-tools"
python .\provision_toolbox.py
```

- Use shared **Publish only the selected hosted sample**; configure supported
  calling identity in Foundry **Agents → agent → Identity** and obtain its object ID.
- Search admin assigns it; allow RBAC propagation and wait for Active:

```powershell
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = "<calling-agent-instance-object-id>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type ServicePrincipal --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <synthetic test document>."
$env:EXPECTED_TEXT = "<known marker>"
python .\invoke_hosted.py
```

</details>

### Agent code → Toolbox

Inside [B's hosted `main()`](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/hosted_agent.py), the authenticated client and tool share a runtime credential.
Input: runtime credential and environment; output: the hosted agent's Toolbox tool.

```python
import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential

async def main():
    credential = DefaultAzureCredential()
    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"], credential=credential,
        ),
        tools=FoundryToolbox(credential, name="retrieval", url=os.environ["TOOLBOX_ENDPOINT"]),
        instructions="Return actual requested Toolbox results/errors; never invent markers or identities.",
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()
```

### Toolbox configuration → calling-instance connection

Payload/tool shape only; the complete
[B provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/provision_toolbox.py)
submits ARM PUT and Toolbox create/update.
[B runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/README.md)
contains complete hosted/invocation scripts.

```python
import os
from azure.ai.projects.models import MCPToolboxTool

target = os.environ["MCP_SERVER_URL"]
project_id = os.environ["FOUNDRY_PROJECT_RESOURCE_ID"].rstrip("/")
connection_id = f"{project_id}/connections/{os.environ['CONNECTION_NAME']}"
connection_payload = {"properties": {
    "category": "RemoteTool", "authType": "AgenticIdentityToken",
    "target": target, "audience": "https://search.azure.com",
    "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
}}
tool = MCPToolboxTool(
    name="retrieve", server_label="knowledge", server_url=target,
    project_connection_id=connection_id, require_approval="never",
)
```

Input: KB URL and connection ID. Output: a Toolbox tool whose connection selects the calling instance's downstream token.

### Service-provided MCP contract

For the native choice, Search hosts MCP; do not manually exchange tokens.

```text
https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview
Agent request: retrieve <synthetic test document> using the advertised retrieval tool
Tool arguments: the schema advertised by this KB's MCP tools/list
Result: retrieval content/marker if calling instance has Search access; otherwise denial
```

## Custom FastMCP

**Custom target flow:** hosted calling agent → Toolbox (`AgenticIdentityToken`) →
your API's `/mcp` → JWT validation + agent-principal ACL → `identity_probe`.

### Connection and hosted agent

Keep B's hosted code unchanged. A **fresh custom connection and Toolbox** uses
`AgenticIdentityToken`, never C's `OAuth2` connection:

In the copied B folder run `python .\custom_server.py` with `AZURE_TENANT_ID`,
`CUSTOM_MCP_AUDIENCE` (the v2 API client-ID GUID), and
`CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS` (only the actual calling agent object ID).
Expose `/mcp` over HTTPS; set `CUSTOM_MCP_SERVER_URL`, the same audience and
fresh connection/Toolbox names, then run `python .\provision_custom_toolbox.py`.
Use the printed endpoint on a separate hosted version. Registration/ACL
prerequisites are in B's complete sample.

```python
import os

custom_connection_payload = {"properties": {
    "category": "RemoteTool", "authType": "AgenticIdentityToken",
    "target": os.environ["CUSTOM_MCP_SERVER_URL"],
    "audience": os.environ["CUSTOM_MCP_AUDIENCE"],
    "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
}}
```

Follow [B's complete custom setup](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/README.md)
for the separate application/agent-token server. Configure exact agent principal
IDs, not invoking user, project MI, blueprint application ID or agent name.
An Entra agent identity is platform-created, not a hand-created confidential
OAuth client. The custom API's actual validated `oid` mapping remains experimental
until observed with that hosted instance and custom audience. Do not infer it
from a native Search configuration or a different agent's successful call.

The server validates signature, issuer, audience and expiry, then authorizes an
explicit agent principal allowlist. The sample uses ACL authorization rather
than role enforcement. Call `identity_probe` with a synthetic experiment UUID;
the result returns only safe validated identifier claims and marker
`CUSTOM_MCP_APPLICATION_VALIDATED`. The complete server prints validated
query/result audit events to stdout; protect those logs.
Two hosted identities with only one allowed
must produce backend allow/deny, with no project-identity fallback.

### Server code → validated calling-agent identity

Run the [full B `custom_server.py`](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/custom_server.py).
This compact equivalent must be saved beside that file: its validator,
`EntraBoundary` and request-scoped `IDENTITY` are required, not an optional
wrapper. Never expose the bare FastMCP app. The boundary validates signature,
v2 tenant issuer, exact audience, expiry and the agent-principal ACL, rejects
delegated tokens, then sets and resets the identity context around dispatch.

```python
import logging
import os
import uuid

import uvicorn
from fastmcp import FastMCP
from custom_server import ApplicationTokenValidator, EntraBoundary, IDENTITY

mcp = FastMCP("Application identity probe", include_fastmcp_meta=False)
logger = logging.getLogger("custom_mcp.identity")

@mcp.tool
def identity_probe(experiment_id: str) -> dict:
    experiment_id = str(uuid.UUID(experiment_id))
    identity = IDENTITY.get()
    if identity is None:
        raise RuntimeError("Validated application identity required")
    logger.info("agent probe experiment=%s tid=%s oid=%s",
                experiment_id, identity["tid"], identity["oid"])
    return {"marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
            "experiment_id": experiment_id, "claims": identity}

if __name__ == "__main__":
    validator = ApplicationTokenValidator(
        os.environ["AZURE_TENANT_ID"],
        os.environ["CUSTOM_MCP_AUDIENCE"],
        [v.strip() for v in os.environ["CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS"].split(",")],
    )
    app = EntraBoundary(
        mcp.http_app(path="/mcp", stateless_http=True, json_response=True), validator,
    )
    uvicorn.run(app, host="0.0.0.0", port=8000,
                access_log=False, log_level="warning")
```

Inputs: tenant, v2 API client-ID audience and
`CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS` containing only **verified allowed calling-agent
principal object IDs**, never user IDs. Output: validated identifiers and marker.
The optional INFO log is off by default; use a protected lab sink, never JWTs.

**Verification gate:** accepted ARM payloads and locally minted test JWTs cannot
prove Toolbox acquisition for custom APIs. Record actual backend claims/outcomes
or clearly mark this custom flow **not live verified**. No agent/APIM exchange or
delegated OAuth workaround is an acceptable substitute.

**One proof exercise:** same authorized caller and Toolbox, two distinct calling
instances; only one has Search access. Require marker vs genuine tool authorization
denial. Record object IDs/effective roles and correlated outcomes; check inherited
access and ensure project MI is not a fallback reader. Unavailable identity workflow
is a blocker, not an allow. Continue to evidence/cleanup.

## Optional APIM evidence: B native and custom MCP

Fresh Azure hosted-agent executions on **November 1, 2026**, on the existing pinned `obs-20261031-*` routes. Original defaults are unchanged; no direct-route success is mixed into these results. Only public synthetic data was submitted. Body diagnostics are isolated (8192 bytes; no headers). Authorization/tokens, opaque consent identifiers/URLs and SDK session baggage are excluded from exports; nonsensitive queries/results are preserved.

### Live replay — b-native: BLOCKED_AGENT_INSTANCE_CONTEXT

Agent `obs-20261031-b-native` v3; Toolbox v3. UTC `2026-11-01T11:32:54.514070+00:00` → `2026-11-01T11:33:05.989959+00:00`. Experiment `556675d4-b6fb-4aec-a21c-634b88955dc3`.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call retrieve_kb_b exactly once with arguments {"query": "Find the normal access record in cohort B"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM`; status **failed**.

Actual hosted error excerpt (full error in secondary capture):


```text
An internal server error occurred.
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `e80f567a-6c61-49c1-afaf-042e63bef531`; backend HTTP **200**.

UTC request `2026-11-01T11:33:06.3530183Z`; response `2026-11-01T11:33:06.878723Z`.

**No `tools/call` query was produced.** The observed `tools/list` request is discovery, not a user search or tool query.

Exact discovery parameters:


```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {
      "name": "mcp",
      "version": "0.1.0"
    },
    "io.modelcontextprotocol/clientCapabilities": {
      "sampling": {}
    },
    "traceparent": "00-57583a76c05f4692ca147b1120cc874e-e91a8ed303f5fb24-01",
    "baggage": "<baggage-redacted>"
  }
}
```


Actual MCP error excerpt (unmodified substring; full below):


```text
tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/iq-b-primary'. HTTP status: BadRequest. Reason: AgenticIdentityToken a
```


**3. Downstream MCP/runtime logs: what was actually observed**

No correlated downstream `tools/call` query/result console event was retrieved. The observed error/consent blocks this captured route before a tool query; missing logs alone do not prove no execution.

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T11:45:48.676331+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T11:33:06.857047523+00:00`.


```text
2026-11-01 11:33:06,856 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM, error_type=ToolExecutionException).
```


<details>

<summary>Real logged exchange — b-native: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1`. Configured downstream target: `https://srchabcb7puse24s5tluc.search.windows.net/knowledgebases/kb-b/mcp?api-version=2026-05-01-preview` (configuration is not execution evidence).

Caller-context SHA-256: `8YGs+YUDmmc23SIU3KOSzJ20h4+tLsObwc2dTVHw7PQ=`.

Exact captured request (only sensitive baggage redacted):


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-57583a76c05f4692ca147b1120cc874e-e91a8ed303f5fb24-01","baggage":"<baggage-redacted>"}}}
```


Exact captured response:


```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32007,
    "message": "tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/iq-b-primary'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'iq-b-primary' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\"}}]}"
  }
}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "ae24bc9a-e218-46ac-87c4-fefeeda5e59c",
    "callerContextPresent": "True",
    "callerContextHash": "8YGs+YUDmmc23SIU3KOSzJ20h4+tLsObwc2dTVHw7PQ=",
    "observedPlatformPrincipalId": "1f430487-d7ab-4b08-b99d-4e157099ab53",
    "requestTimestamp": "2026-11-01T11:33:05.7787072Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-57583a76c05f4692ca147b1120cc874e-e441b420a41cfbf1-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T11:33:06.3215581Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 1,\n  \"result\": {\"resultType\":\"complete\",\"supportedVersions\":[\"2025-11-25\",\"2026-07-28\"],\"capabilities\":{\"tools\":{},\"resources\":{},\"extensions\":{\"io.modelcontextprotocol/skills\":{},\"io.modelcontextprotocol/tasks\":{}}},\"_meta\":{\"io.modelcontextprotocol/serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}},\"instructions\":\"This server exposes tools configured in the requested Foundry toolbox. Use tools/list to enumerate available tools and tools/call to invoke them.\",\"ttlMs\":300000,\"cacheScope\":\"private\"}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "e80f567a-6c61-49c1-afaf-042e63bef531",
    "callerContextPresent": "True",
    "callerContextHash": "8YGs+YUDmmc23SIU3KOSzJ20h4+tLsObwc2dTVHw7PQ=",
    "observedPlatformPrincipalId": "1f430487-d7ab-4b08-b99d-4e157099ab53",
    "requestTimestamp": "2026-11-01T11:33:06.3530183Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-57583a76c05f4692ca147b1120cc874e-e91a8ed303f5fb24-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T11:33:06.878723Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 2,\n  \"error\": {\n    \"code\": -32007,\n    \"message\": \"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"HTTP_400\\\",\\\"message\\\":\\\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/iq-b-primary'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'iq-b-primary' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\\\"}}]}\"\n  }\n}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM",
  "object": "response",
  "output": [],
  "created_at": 1793532784,
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "parallel_tool_calls": false,
  "status": "failed",
  "response_id": "caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-b-native",
    "version": "3"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
```


Runtime query result:


```json
{
  "scenario": "b-native",
  "agent": "obs-20261031-b-native",
  "version": "3",
  "experimentId": "556675d4-b6fb-4aec-a21c-634b88955dc3",
  "responseId": "caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM",
  "invocationStartedAt": "2026-11-01T11:32:54.514070+00:00",
  "invocationCompletedAt": "2026-11-01T11:33:05.989959+00:00",
  "queriedAt": "2026-11-01T11:45:48.676331+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.206006339+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.214327395+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.613580436+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,613 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.744657423+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,744 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,776 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.777733633+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.780430969+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,780 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.780587484+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,780 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.781003245+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,780 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.781102878+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,781 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.939579634+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,939 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.940401575+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,940 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.940643652+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,940 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.940718373+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,940 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.941981532+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,940 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.942474877+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 11:32:54 +0000] [43] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:54.942497819+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:54,942 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:55.387620570+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:55,387 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 7479006397cff6a7f5b39202ffd17bfc)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:55.388511899+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:55,388 INFO azure.ai.agentserver: 192.168.0.1:38012 \"GET /readiness 1.1\" 200 20 1356\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:32:55.388705859+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:32:55,388 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.9ms (trace-id: 7479006397cff6a7f5b39202ffd17bfc)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:04.787255642+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:04,787 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 57583a76c05f4692ca147b1120cc874e, x-ms-client-request-id: 64c8b009-8f24-4a97-bb37-32b017f64adb, trace-id: 57583a76c05f4692ca147b1120cc874e)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:04.790338917+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:04,788 INFO azure.ai.agentserver: Creating response caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:04.790338917+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:04,788 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:04.790338917+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:04,788 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:04.790338917+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:04,789 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:05.398093082+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:05,397 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.296506162+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,296 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.316464030+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,316 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.317799717+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,316 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.317967727+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,317 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.853341917+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,853 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.857047523+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,856 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM, error_type=ToolExecutionException)."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.857704058+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,857 INFO azure.ai.agentserver: Response caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM completed: status=failed output_count=0"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.860244471+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,859 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.860977628+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,860 INFO azure.ai.agentserver: 192.168.0.1:58414 \"POST /responses 1.1\" 200 513 2074122\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.861224589+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,861 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 2073.7ms (x-request-id: 57583a76c05f4692ca147b1120cc874e, x-ms-client-request-id: 64c8b009-8f24-4a97-bb37-32b017f64adb, trace-id: 57583a76c05f4692ca147b1120cc874e)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.861372517+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,861 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:06.869070061+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:06,869 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported.\n"
    }
  ],
  "status": "CAPTURED_CORRELATED_LINES",
  "limitation": "Bounded console SSE read, filtered to this pinned session's invocation time window. Sensitive and unrelated lines excluded; session IDs remain memory-only. Not a complete invocation log.",
  "cliStatus": "NOT_RETRIED",
  "source": "SDK get_session_log_stream; unique version/time-matched session"
}
```


Local full sources: `evidence\observability-b-native.json`, `evidence\observability-b-native-apim.json`.

</details>

<details>

<summary>Hosted service snapshot — b-native</summary>


```json
{
  "source": "evidence/observability-b-native.json#agentResponse",
  "responseId": "caresp_01b1a5e25eb686ba00nAqkei63O1CxTFvr7U0l7hEIANUnfGvM",
  "status": "failed",
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "events": [],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

### Live replay — b-custom: BLOCKED_AGENT_INSTANCE_CONTEXT

Agent `obs-20261031-b-custom` v2; Toolbox v2. UTC `2026-11-01T11:33:55.363434+00:00` → `2026-11-01T11:34:07.890199+00:00`. Experiment `3245f2aa-8d99-4933-8aef-ba9bc5a998d4`.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call identity_probe exactly once with arguments {"experiment_id": "3245f2aa-8d99-4933-8aef-ba9bc5a998d4"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu`; status **failed**.

Actual hosted error excerpt (full error in secondary capture):


```text
An internal server error occurred.
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `a93d79f7-39c6-40ba-aad9-d774f1e4c0e2`; backend HTTP **200**.

UTC request `2026-11-01T11:34:08.35145Z`; response `2026-11-01T11:34:08.7753488Z`.

**No `tools/call` query was produced.** The observed `tools/list` request is discovery, not a user search or tool query.

Exact discovery parameters:


```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {
      "name": "mcp",
      "version": "0.1.0"
    },
    "io.modelcontextprotocol/clientCapabilities": {
      "sampling": {}
    },
    "traceparent": "00-f7ba87c30a659da09d35ca485f729048-03a27e45381f5ffe-01",
    "baggage": "<baggage-redacted>"
  }
}
```


Actual MCP error excerpt (unmodified substring; full below):


```text
tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/obs-20261031-b-custom-data'. HTTP status: BadRequest. Reason: AgenticI
```


**3. Downstream MCP/runtime logs: what was actually observed**

No correlated downstream `tools/call` query/result console event was retrieved. The observed error/consent blocks this captured route before a tool query; missing logs alone do not prove no execution.

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T11:46:33.387469+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T11:34:08.757078772+00:00`.


```text
2026-11-01 11:34:08,756 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu, error_type=ToolExecutionException).
```


<details>

<summary>Real logged exchange — b-custom: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1`. Configured downstream target: `https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` (configuration is not execution evidence).

Caller-context SHA-256: `niWeK9gjh8rD2RP4u3C7hr/y/kWTUoFxGZEHl1ZbWEE=`.

Exact captured request (only sensitive baggage redacted):


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-f7ba87c30a659da09d35ca485f729048-03a27e45381f5ffe-01","baggage":"<baggage-redacted>"}}}
```


Exact captured response:


```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32007,
    "message": "tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/obs-20261031-b-custom-data'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'obs-20261031-b-custom-data' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\"}}]}"
  }
}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "3b911b43-edc6-47b4-90d4-52a9b97fedd3",
    "callerContextPresent": "True",
    "callerContextHash": "niWeK9gjh8rD2RP4u3C7hr/y/kWTUoFxGZEHl1ZbWEE=",
    "observedPlatformPrincipalId": "d6fb1ff2-6587-4169-b279-20103b371ab7",
    "requestTimestamp": "2026-11-01T11:34:08.0872851Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-f7ba87c30a659da09d35ca485f729048-7c6fe98bd3ebed82-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T11:34:08.3015446Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 1,\n  \"result\": {\"resultType\":\"complete\",\"supportedVersions\":[\"2025-11-25\",\"2026-07-28\"],\"capabilities\":{\"tools\":{},\"resources\":{},\"extensions\":{\"io.modelcontextprotocol/skills\":{},\"io.modelcontextprotocol/tasks\":{}}},\"_meta\":{\"io.modelcontextprotocol/serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}},\"instructions\":\"This server exposes tools configured in the requested Foundry toolbox. Use tools/list to enumerate available tools and tools/call to invoke them.\",\"ttlMs\":300000,\"cacheScope\":\"private\"}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "a93d79f7-39c6-40ba-aad9-d774f1e4c0e2",
    "callerContextPresent": "True",
    "callerContextHash": "niWeK9gjh8rD2RP4u3C7hr/y/kWTUoFxGZEHl1ZbWEE=",
    "observedPlatformPrincipalId": "d6fb1ff2-6587-4169-b279-20103b371ab7",
    "requestTimestamp": "2026-11-01T11:34:08.35145Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-f7ba87c30a659da09d35ca485f729048-03a27e45381f5ffe-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T11:34:08.7753488Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 2,\n  \"error\": {\n    \"code\": -32007,\n    \"message\": \"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"HTTP_400\\\",\\\"message\\\":\\\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/obs-20261031-b-custom-data'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'obs-20261031-b-custom-data' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\\\"}}]}\"\n  }\n}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu",
  "object": "response",
  "output": [],
  "created_at": 1793532847,
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "parallel_tool_calls": false,
  "status": "failed",
  "response_id": "caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-b-custom",
    "version": "2"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
```


Runtime query result:


```json
{
  "scenario": "b-custom",
  "agent": "obs-20261031-b-custom",
  "version": "2",
  "experimentId": "3245f2aa-8d99-4933-8aef-ba9bc5a998d4",
  "responseId": "caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu",
  "invocationStartedAt": "2026-11-01T11:33:55.363434+00:00",
  "invocationCompletedAt": "2026-11-01T11:34:07.890199+00:00",
  "queriedAt": "2026-11-01T11:46:33.387469+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:54.943190441+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:54.950515049+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.360515698+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,360 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.493663601+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,493 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,525 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.526666608+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.529394024+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,529 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.529550930+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,529 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.529977589+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,529 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.530069091+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,530 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.685916858+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,685 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.686808003+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,686 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.687057274+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,687 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.687128794+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,687 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.688355006+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,687 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.688910692+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 11:33:55 +0000] [44] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:55.688937539+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:55,688 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:56.231936511+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:56,231 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: b9b20f898c196b8a21aac4ab69ccfb3a)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:56.232807477+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:56,232 INFO azure.ai.agentserver: 192.168.0.1:41298 \"GET /readiness 1.1\" 200 20 1141\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:33:56.233006758+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:33:56,232 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.9ms (trace-id: b9b20f898c196b8a21aac4ab69ccfb3a)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:07.049556761+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:07,049 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: f7ba87c30a659da09d35ca485f729048, x-ms-client-request-id: c206a246-a07a-49da-8cf2-b563693ed167, trace-id: f7ba87c30a659da09d35ca485f729048)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:07.050264469+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:07,050 INFO azure.ai.agentserver: Creating response caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:07.050553544+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:07,050 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:07.051083466+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:07,051 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:07.051447860+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:07,051 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:07.917654213+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:07,917 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.283768856+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,283 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.306350111+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,306 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.307710042+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,306 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.307891220+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,307 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.752247024+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,752 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.757078772+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,756 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu, error_type=ToolExecutionException)."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.757843225+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,757 INFO azure.ai.agentserver: Response caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu completed: status=failed output_count=0"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.760246488+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,759 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.761413506+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,761 INFO azure.ai.agentserver: 192.168.0.1:58632 \"POST /responses 1.1\" 200 513 1712108\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.761686907+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,761 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 1711.9ms (x-request-id: f7ba87c30a659da09d35ca485f729048, x-ms-client-request-id: c206a246-a07a-49da-8cf2-b563693ed167, trace-id: f7ba87c30a659da09d35ca485f729048)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.761840392+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,761 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:08.769546736+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:08,769 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported.\n"
    }
  ],
  "status": "CAPTURED_CORRELATED_LINES",
  "limitation": "Bounded console SSE read, filtered to this pinned session's invocation time window. Sensitive and unrelated lines excluded; session IDs remain memory-only. Not a complete invocation log.",
  "cliStatus": "NOT_RETRIED",
  "source": "SDK get_session_log_stream; unique version/time-matched session"
}
```


Local full sources: `evidence\observability-b-custom.json`, `evidence\observability-b-custom-apim.json`.

</details>

<details>

<summary>Hosted service snapshot — b-custom</summary>


```json
{
  "source": "evidence/observability-b-custom.json#agentResponse",
  "responseId": "caresp_0946eead73318ecd00J7D5eY0cqb2lVLEV5avVDWH9nmSfxbmu",
  "status": "failed",
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "events": [],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

---

# C native: managed user context and a trusted Search KB

![C native flow: signed-in user context through Toolbox to trusted Search](assets/workshop-native-user.svg)

The hosted runtime supplies managed user context to Toolbox; `UserEntraToken` selects downstream authentication.
Search checks the user's RBAC, without custom OAuth client or MCP server code.

<details>
<summary>Deploy C native: prerequisites, user authorization, roles and commands</summary>

### Prerequisites / registration / consent

- Trusted Search KB, platform-managed user context supported by the hosted runtime.
  **No custom API/client registration, secret or callback**; do not substitute FastMCP.
- Project admin grants invoker/runtime access and enables supported user context.
- Search admin grants **eventual invoking user's object ID** Search Index Data Reader,
  not automatically the provisioning administrator.
- Intended user completes any platform connection authorization in browser;
  tenant restrictions may require admin approval. Retry afresh, never auto-follow consent URLs.

### Deployment checklist

- From clone root, install/configure/provision:

```powershell
Set-Location .\samples\user-identity\trusted-kb
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant "<tenant-id>"
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview"
$env:CONNECTION_NAME = "my-user-kb"
$env:TOOLBOX_NAME = "my-user-tools"
python .\provision_toolbox.py
```

- Intended user identifies themselves; separately authorized Search admin assigns the role:

```powershell
az login --tenant "<tenant-id>"
az ad signed-in-user show --query id -o tsv
$env:DATA_PRINCIPAL_OBJECT_ID = "<intended-invoking-user-object-id>"
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type User --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

- Use shared hosted publishing; wait for Active and complete connection authorization.
  Sign in as the **intended caller**, then invoke:

```powershell
az login --tenant "<tenant-id>"
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <synthetic test document>."
$env:EXPECTED_TEXT = "<known marker>"
python .\invoke_hosted.py
```

</details>

## Agent code → Toolbox

This is the same runtime pattern in [the native hosted agent](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/hosted_agent.py).
Input: hosted credential and Toolbox URL; output: a hosted Responses agent, not a manually forwarded user token.

```python
import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential

async def main():
    credential = DefaultAzureCredential()
    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"], credential=credential,
        ),
        tools=FoundryToolbox(credential, name="retrieval", url=os.environ["TOOLBOX_ENDPOINT"]),
        instructions="Return actual requested Toolbox results/errors; never invent markers or identities.",
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()
```

## Toolbox configuration → native user connection

Configuration only, **not a manual token exchange**. Complete
[native runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/README.md)
and [provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/provision_toolbox.py).

```python
import os
from azure.ai.projects.models import MCPToolboxTool

target = os.environ["MCP_SERVER_URL"]
project_id = os.environ["FOUNDRY_PROJECT_RESOURCE_ID"].rstrip("/")
connection_id = f"{project_id}/connections/{os.environ['CONNECTION_NAME']}"
connection_payload = {"properties": {
    "category": "RemoteTool", "authType": "UserEntraToken",
    "target": target, "audience": "https://search.azure.com",
    "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
}}
tool = MCPToolboxTool(
    name="retrieve", server_label="knowledge", server_url=target,
    project_connection_id=connection_id, require_approval="never",
)
```

Input: KB URL and connection ID. Output: a Toolbox tool using managed user authentication.

## Service-provided MCP contract

The trusted KB provides its own MCP tools and argument schema; no FastMCP code belongs in this track.

```text
https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview
Agent request: retrieve <synthetic test document> using the advertised retrieval tool
Tool arguments: discover this KB's schema through MCP tools/list
Result: actual retrieval content/marker for an authorized user; otherwise denial
```

**One proof exercise:** two users may invoke the same Active agent, only one has
Search access. Sign in separately, complete required authorization and retry.
Record user object IDs, effective roles and actual marker/denial outcomes with
available downstream evidence. Consent challenge is inconclusive. Check inherited roles;
service-level RBAC is not document isolation (production needs ACL/filter enforcement).
Describe managed native user access, not an unobserved OBO exchange. Continue to cleanup.

## Optional APIM evidence: C native MCP

Fresh Azure hosted-agent executions on **November 1, 2026**, on the existing pinned `obs-20261031-*` routes. Original defaults are unchanged; no direct-route success is mixed into these results. Only public synthetic data was submitted. Body diagnostics are isolated (8192 bytes; no headers). Authorization/tokens, opaque consent identifiers/URLs and SDK session baggage are excluded from exports; nonsensitive queries/results are preserved.

### Live replay — c-native: BLOCKED_PLATFORM_USER_TOKEN_FLOW

Agent `obs-20261031-c-native` v2; Toolbox v2. UTC `2026-11-01T11:34:57.231496+00:00` → `2026-11-01T11:35:14.968297+00:00`. Experiment `7f4f5874-6c7f-4187-8a6e-ab38ca0464f1`.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call retrieve_kb_c exactly once with arguments {"query": "Find the normal access record in cohort C"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65`; status **failed**.

Actual hosted error excerpt (full error in secondary capture):


```text
('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for \'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\'. HTTP s
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `468be3c0-cf32-4db7-97e2-71798f6d5eb1`; backend HTTP **200**.

UTC request `2026-11-01T11:35:15.0648224Z`; response `2026-11-01T11:35:15.8619238Z`.

**No `tools/call` query was produced.** The observed `tools/list` request is discovery, not a user search or tool query.

Exact discovery parameters:


```json
{}
```


Actual MCP error excerpt (unmodified substring; full below):


```text
tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service i
```


**3. Downstream MCP/runtime logs: what was actually observed**

No correlated downstream `tools/call` query/result console event was retrieved. The observed error/consent blocks this captured route before a tool query; missing logs alone do not prove no execution.

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T11:45:59.582499+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T11:35:15.845855489+00:00`.


```text
2026-11-01 11:35:15,841 ERROR agent_framework_foundry_hosting._responses: Failed to prepare agent: ('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for \'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.Cog
```


UTC `2026-11-01T11:35:15.845855489+00:00`.


```text
mcp.shared.exceptions.McpError: tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest
```


<details>

<summary>Real logged exchange — c-native: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1`. Configured downstream target: `https://srchabcc7puse24s5tluc.search.windows.net/knowledgebases/kb-c/mcp?api-version=2026-05-01-preview` (configuration is not execution evidence).

Caller-context SHA-256: `EnkKDKNgqpdnLUY1cgG1WxtN+3fU4Cc2IHmbP0tzsh8=`.

Exact captured request (only sensitive baggage redacted):


```json
{"method":"tools/list","jsonrpc":"2.0","id":2}
```


Exact captured response:


```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32007,
    "message": "tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\r\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\r\\nStatus Code: 400 BadRequest\\r\\nError Code: ValidationError\\r\\nReason Phrase: Bad Request\\r\\nResponse Body: {\\n  \\\"error\\\": {\\n    \\\"code\\\": \\\"ValidationError\\\",\\n    \\\"severity\\\": null,\\n    \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\",\\n    \\\"messageFormat\\\": null,\\n    \\\"messageParameters\\\": null,\\n    \\\"referenceCode\\\": null,\\n    \\\"detailsUri\\\": null,\\n    \\\"target\\\": \\\"UserToken\\\",\\n    \\\"details\\\": [\\n      {\\n        \\\"code\\\": \\\"Invalid\\\",\\n        \\\"severity\\\": null,\\n        \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\",\\n        \\\"messageFormat\\\": null,\\n        \\\"messageParameters\\\": {},\\n        \\\"referenceCode\\\": null,\\n        \\\"detailsUri\\\": null,\\n        \\\"target\\\": \\\"UserToken\\\",\\n        \\\"details\\\": [],\\n        \\\"innerError\\\": null,\\n        \\\"debugInfo\\\": null,\\n        \\\"additionalInfo\\\": null\\n      }\\n    ],\\n    \\\"innerError\\\": null,\\n    \\\"debugInfo\\\": null,\\n    \\\"additionalInfo\\\": null\\n  },\\n  \\\"correlation\\\": {\\n    \\\"operation\\\": \\\"7e01a9229eabc0436791651dbf0a0f0d\\\",\\n    \\\"request\\\": \\\"abeb5319c4529f23\\\"\\n  },\\n  \\\"environment\\\": \\\"eastus2\\\",\\n  \\\"location\\\": \\\"eastus2\\\",\\n  \\\"time\\\": \\\"2026-11-01T11:35:15.8434545+00:00\\\",\\n  \\\"componentName\\\": \\\"obotoken\\\",\\n  \\\"statusCode\\\": 400\\n}\"}}]}"
  }
}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "fc265650-6426-48c3-a1a4-dd7fc5f16a47",
    "callerContextPresent": "True",
    "callerContextHash": "EnkKDKNgqpdnLUY1cgG1WxtN+3fU4Cc2IHmbP0tzsh8=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "requestTimestamp": "2026-11-01T11:35:14.4419253Z",
    "requestBody": "{\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"sampling\":{}},\"clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"}},\"jsonrpc\":\"2.0\",\"id\":0}",
    "responseTimestamp": "2026-11-01T11:35:14.8467863Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 0,\n  \"result\": {\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"tools\":{},\"tasks\":{\"list\":{},\"cancel\":{},\"requests\":{\"tools\":{\"call\":{}}}},\"resources\":{\"listChanged\":false,\"subscribe\":false},\"extensions\":{\"io.modelcontextprotocol/skills\":{}}},\"serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "e03b483e-7d82-4ab6-82b8-4e02d5adddd5",
    "callerContextPresent": "True",
    "callerContextHash": "EnkKDKNgqpdnLUY1cgG1WxtN+3fU4Cc2IHmbP0tzsh8=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "requestTimestamp": "2026-11-01T11:35:14.9462727Z",
    "requestBody": "{\"method\":\"notifications/initialized\",\"jsonrpc\":\"2.0\"}",
    "responseTimestamp": "2026-11-01T11:35:14.9751122Z",
    "responseBody": "<empty-body>",
    "backendStatus": 204
  },
  {
    "apimRequestId": "6adb9002-4d0a-45a9-bb20-de6d9f11e791",
    "callerContextPresent": "True",
    "callerContextHash": "EnkKDKNgqpdnLUY1cgG1WxtN+3fU4Cc2IHmbP0tzsh8=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "requestTimestamp": "2026-11-01T11:35:15.0175271Z",
    "requestBody": "{\"method\":\"ping\",\"jsonrpc\":\"2.0\",\"id\":1}",
    "responseTimestamp": "2026-11-01T11:35:15.0517585Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 1,\n  \"result\": {}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "468be3c0-cf32-4db7-97e2-71798f6d5eb1",
    "callerContextPresent": "True",
    "callerContextHash": "EnkKDKNgqpdnLUY1cgG1WxtN+3fU4Cc2IHmbP0tzsh8=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "requestTimestamp": "2026-11-01T11:35:15.0648224Z",
    "requestBody": "{\"method\":\"tools/list\",\"jsonrpc\":\"2.0\",\"id\":2}",
    "responseTimestamp": "2026-11-01T11:35:15.8619238Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 2,\n  \"error\": {\n    \"code\": -32007,\n    \"message\": \"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"HTTP_400\\\",\\\"message\\\":\\\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\\\"error\\\\\\\": {\\\\n    \\\\\\\"code\\\\\\\": \\\\\\\"ValidationError\\\\\\\",\\\\n    \\\\\\\"severity\\\\\\\": null,\\\\n    \\\\\\\"message\\\\\\\": \\\\\\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\\\",\\\\n    \\\\\\\"messageFormat\\\\\\\": null,\\\\n    \\\\\\\"messageParameters\\\\\\\": null,\\\\n    \\\\\\\"referenceCode\\\\\\\": null,\\\\n    \\\\\\\"detailsUri\\\\\\\": null,\\\\n    \\\\\\\"target\\\\\\\": \\\\\\\"UserToken\\\\\\\",\\\\n    \\\\\\\"details\\\\\\\": [\\\\n      {\\\\n        \\\\\\\"code\\\\\\\": \\\\\\\"Invalid\\\\\\\",\\\\n        \\\\\\\"severity\\\\\\\": null,\\\\n        \\\\\\\"message\\\\\\\": \\\\\\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\\\",\\\\n        \\\\\\\"messageFormat\\\\\\\": null,\\\\n        \\\\\\\"messageParameters\\\\\\\": {},\\\\n        \\\\\\\"referenceCode\\\\\\\": null,\\\\n        \\\\\\\"detailsUri\\\\\\\": null,\\\\n        \\\\\\\"target\\\\\\\": \\\\\\\"UserToken\\\\\\\",\\\\n        \\\\\\\"details\\\\\\\": [],\\\\n        \\\\\\\"innerError\\\\\\\": null,\\\\n        \\\\\\\"debugInfo\\\\\\\": null,\\\\n        \\\\\\\"additionalInfo\\\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\\\"innerError\\\\\\\": null,\\\\n    \\\\\\\"debugInfo\\\\\\\": null,\\\\n    \\\\\\\"additionalInfo\\\\\\\": null\\\\n  },\\\\n  \\\\\\\"correlation\\\\\\\": {\\\\n    \\\\\\\"operation\\\\\\\": \\\\\\\"7e01a9229eabc0436791651dbf0a0f0d\\\\\\\",\\\\n    \\\\\\\"request\\\\\\\": \\\\\\\"abeb5319c4529f23\\\\\\\"\\\\n  },\\\\n  \\\\\\\"environment\\\\\\\": \\\\\\\"eastus2\\\\\\\",\\\\n  \\\\\\\"location\\\\\\\": \\\\\\\"eastus2\\\\\\\",\\\\n  \\\\\\\"time\\\\\\\": \\\\\\\"2026-11-01T11:35:15.8434545+00:00\\\\\\\",\\\\n  \\\\\\\"componentName\\\\\\\": \\\\\\\"obotoken\\\\\\\",\\\\n  \\\\\\\"statusCode\\\\\\\": 400\\\\n}\\\"}}]}\"\n  }\n}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65",
  "object": "response",
  "output": [],
  "created_at": 1793532913,
  "error": {
    "code": "server_error",
    "message": "('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for \\'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\\'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\"error\\\\\": {\\\\n    \\\\\"code\\\\\": \\\\\"ValidationError\\\\\",\\\\n    \\\\\"severity\\\\\": null,\\\\n    \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\",\\\\n    \\\\\"messageFormat\\\\\": null,\\\\n    \\\\\"messageParameters\\\\\": null,\\\\n    \\\\\"referenceCode\\\\\": null,\\\\n    \\\\\"detailsUri\\\\\": null,\\\\n    \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n    \\\\\"details\\\\\": [\\\\n      {\\\\n        \\\\\"code\\\\\": \\\\\"Invalid\\\\\",\\\\n        \\\\\"severity\\\\\": null,\\\\n        \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\",\\\\n        \\\\\"messageFormat\\\\\": null,\\\\n        \\\\\"messageParameters\\\\\": {},\\\\n        \\\\\"referenceCode\\\\\": null,\\\\n        \\\\\"detailsUri\\\\\": null,\\\\n        \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n        \\\\\"details\\\\\": [],\\\\n        \\\\\"innerError\\\\\": null,\\\\n        \\\\\"debugInfo\\\\\": null,\\\\n        \\\\\"additionalInfo\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\"innerError\\\\\": null,\\\\n    \\\\\"debugInfo\\\\\": null,\\\\n    \\\\\"additionalInfo\\\\\": null\\\\n  },\\\\n  \\\\\"correlation\\\\\": {\\\\n    \\\\\"operation\\\\\": \\\\\"7e01a9229eabc0436791651dbf0a0f0d\\\\\",\\\\n    \\\\\"request\\\\\": \\\\\"abeb5319c4529f23\\\\\"\\\\n  },\\\\n  \\\\\"environment\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"location\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"time\\\\\": \\\\\"2026-11-01T11:35:15.8434545+00:00\\\\\",\\\\n  \\\\\"componentName\\\\\": \\\\\"obotoken\\\\\",\\\\n  \\\\\"statusCode\\\\\": 400\\\\n}\"}}]}'))"
  },
  "parallel_tool_calls": false,
  "status": "failed",
  "response_id": "caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-c-native",
    "version": "2"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
```


Runtime query result:


```json
{
  "scenario": "c-native",
  "agent": "obs-20261031-c-native",
  "version": "2",
  "experimentId": "7f4f5874-6c7f-4187-8a6e-ab38ca0464f1",
  "responseId": "caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65",
  "invocationStartedAt": "2026-11-01T11:34:57.231496+00:00",
  "invocationCompletedAt": "2026-11-01T11:35:14.968297+00:00",
  "queriedAt": "2026-11-01T11:45:59.582499+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:57.411761706+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:57.416469834+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:57.825062009+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:57,824 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:57.984955127+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:57,984 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,016 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.017307071+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.020140999+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,020 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.020286946+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,020 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.020691418+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,020 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.020781693+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,020 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.089066951+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,089 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.089929427+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,089 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.090242651+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,090 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.090315376+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,090 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.091401267+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,090 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.091816800+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 11:34:58 +0000] [47] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.091837648+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,091 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.109658762+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,109 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: cfcc03aad8ffcedeff71cca300441b36)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.110546426+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,110 INFO azure.ai.agentserver: 192.168.0.1:56518 \"GET /readiness 1.1\" 200 20 943\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:34:58.110729847+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:34:58,110 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.9ms (trace-id: cfcc03aad8ffcedeff71cca300441b36)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:13.142523318+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:13,142 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 0c1f38c13923d932fb5a7e2cce8c1be1, x-ms-client-request-id: bb4705bd-51de-4380-a698-ab390b949719, trace-id: 0c1f38c13923d932fb5a7e2cce8c1be1)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:13.144834013+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:13,144 INFO azure.ai.agentserver: Creating response caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:13.145508715+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:13,145 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.073075447+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,072 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.823259992+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,823 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.824523680+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,824 INFO mcp.client.streamable_http: Negotiated protocol version: 2025-11-25"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.827620327+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,827 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.828364812+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,827 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.828495663+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,828 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.950398958+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,950 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 204 No Content\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.951419648+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,951 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.951572295+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,951 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:14.951663015+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:14,951 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.026310773+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,026 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.029330091+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,029 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.029481559+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,029 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.029602076+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,029 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.837484710+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,837 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,841 ERROR agent_framework_foundry_hosting._responses: Failed to prepare agent: ('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for \\'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\\'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\"error\\\\\": {\\\\n    \\\\\"code\\\\\": \\\\\"ValidationError\\\\\",\\\\n    \\\\\"severity\\\\\": null,\\\\n    \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\",\\\\n    \\\\\"messageFormat\\\\\": null,\\\\n    \\\\\"messageParameters\\\\\": null,\\\\n    \\\\\"referenceCode\\\\\": null,\\\\n    \\\\\"detailsUri\\\\\": null,\\\\n    \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n    \\\\\"details\\\\\": [\\\\n      {\\\\n        \\\\\"code\\\\\": \\\\\"Invalid\\\\\",\\\\n        \\\\\"severity\\\\\": null,\\\\n        \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\",\\\\n        \\\\\"messageFormat\\\\\": null,\\\\n        \\\\\"messageParameters\\\\\": {},\\\\n        \\\\\"referenceCode\\\\\": null,\\\\n        \\\\\"detailsUri\\\\\": null,\\\\n        \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n        \\\\\"details\\\\\": [],\\\\n        \\\\\"innerError\\\\\": null,\\\\n        \\\\\"debugInfo\\\\\": null,\\\\n        \\\\\"additionalInfo\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\"innerError\\\\\": null,\\\\n    \\\\\"debugInfo\\\\\": null,\\\\n    \\\\\"additionalInfo\\\\\": null\\\\n  },\\\\n  \\\\\"correlation\\\\\": {\\\\n    \\\\\"operation\\\\\": \\\\\"7e01a9229eabc0436791651dbf0a0f0d\\\\\",\\\\n    \\\\\"request\\\\\": \\\\\"abeb5319c4529f23\\\\\"\\\\n  },\\\\n  \\\\\"environment\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"location\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"time\\\\\": \\\\\"2026-11-01T11:35:15.8434545+00:00\\\\\",\\\\n  \\\\\"componentName\\\\\": \\\\\"obotoken\\\\\",\\\\n  \\\\\"statusCode\\\\\": 400\\\\n}\"}}]}'))"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 3488, in __aenter__"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self.connect()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework_foundry_hosting/_toolbox.py\", line 267, in connect"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await super().connect(reset=reset)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 1932, in connect"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self._run_on_lifecycle_owner(\"connect\", reset=reset)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 1828, in _run_on_lifecycle_owner"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await future"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 1728, in _run_lifecycle_owner"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self._connect_on_owner("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    ...<3 lines>..."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 2071, in _connect_on_owner"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self.load_tools()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 2536, in load_tools"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self._load_tools_locked()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 2574, in _load_tools_locked"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    tool_list = await self.session.list_tools(params=params)  # type: ignore[union-attr]"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/mcp/client/session.py\", line 529, in list_tools"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    result = await self.send_request("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "             ^^^^^^^^^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    ...<2 lines>..."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    ^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/mcp/shared/session.py\", line 306, in send_request"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    raise McpError(response_or_error.error)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "mcp.shared.exceptions.McpError: tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\r\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\r\\nStatus Code: 400 BadRequest\\r\\nError Code: ValidationError\\r\\nReason Phrase: Bad Request\\r\\nResponse Body: {\\n  \\\"error\\\": {\\n    \\\"code\\\": \\\"ValidationError\\\",\\n    \\\"severity\\\": null,\\n    \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\",\\n    \\\"messageFormat\\\": null,\\n    \\\"messageParameters\\\": null,\\n    \\\"referenceCode\\\": null,\\n    \\\"detailsUri\\\": null,\\n    \\\"target\\\": \\\"UserToken\\\",\\n    \\\"details\\\": [\\n      {\\n        \\\"code\\\": \\\"Invalid\\\",\\n        \\\"severity\\\": null,\\n        \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\",\\n        \\\"messageFormat\\\": null,\\n        \\\"messageParameters\\\": {},\\n        \\\"referenceCode\\\": null,\\n        \\\"detailsUri\\\": null,\\n        \\\"target\\\": \\\"UserToken\\\",\\n        \\\"details\\\": [],\\n        \\\"innerError\\\": null,\\n        \\\"debugInfo\\\": null,\\n        \\\"additionalInfo\\\": null\\n      }\\n    ],\\n    \\\"innerError\\\": null,\\n    \\\"debugInfo\\\": null,\\n    \\\"additionalInfo\\\": null\\n  },\\n  \\\"correlation\\\": {\\n    \\\"operation\\\": \\\"7e01a9229eabc0436791651dbf0a0f0d\\\",\\n    \\\"request\\\": \\\"abeb5319c4529f23\\\"\\n  },\\n  \\\"environment\\\": \\\"eastus2\\\",\\n  \\\"location\\\": \\\"eastus2\\\",\\n  \\\"time\\\": \\\"2026-11-01T11:35:15.8434545+00:00\\\",\\n  \\\"componentName\\\": \\\"obotoken\\\",\\n  \\\"statusCode\\\": 400\\n}\"}}]}"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": ""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "The above exception was the direct cause of the following exception:"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": ""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework_foundry_hosting/_responses.py\", line 1044, in _handle_prepared_response"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self._ensure_agent_ready()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework_foundry_hosting/_responses.py\", line 940, in _ensure_agent_ready"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await stack.enter_async_context(cast(AbstractAsyncContextManager[Any], agent))"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/opt/python/3.13.17/lib/python3.13/contextlib.py\", line 668, in enter_async_context"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    result = await _enter(cm)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "             ^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_agents.py\", line 1085, in __aenter__"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    return await self.open()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "           ^^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_agents.py\", line 1077, in open"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    await self._async_exit_stack.enter_async_context(context_manager)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/opt/python/3.13.17/lib/python3.13/contextlib.py\", line 668, in enter_async_context"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    result = await _enter(cm)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "             ^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 3494, in __aenter__"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "    raise ToolExecutionException(\"Failed to enter context manager.\", inner_exception=ex) from ex"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845855489+00:00",
      "stream": "stderr",
      "line": "agent_framework.exceptions.ToolExecutionException: ('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution faile"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.845891153+00:00",
      "stream": "stderr",
      "line": "d for \\'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\\'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\"error\\\\\": {\\\\n    \\\\\"code\\\\\": \\\\\"ValidationError\\\\\",\\\\n    \\\\\"severity\\\\\": null,\\\\n    \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\",\\\\n    \\\\\"messageFormat\\\\\": null,\\\\n    \\\\\"messageParameters\\\\\": null,\\\\n    \\\\\"referenceCode\\\\\": null,\\\\n    \\\\\"detailsUri\\\\\": null,\\\\n    \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n    \\\\\"details\\\\\": [\\\\n      {\\\\n        \\\\\"code\\\\\": \\\\\"Invalid\\\\\",\\\\n        \\\\\"severity\\\\\": null,\\\\n        \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 79eeba9b-1eb1-4679-8360-17d170b1a900 Correlation ID: d69d68e1-9795-463b-bbb9-ebd741c7b8cb Timestamp: 2026-11-01 11:35:15Z\\\\\",\\\\n        \\\\\"messageFormat\\\\\": null,\\\\n        \\\\\"messageParameters\\\\\": {},\\\\n        \\\\\"referenceCode\\\\\": null,\\\\n        \\\\\"detailsUri\\\\\": null,\\\\n        \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n        \\\\\"details\\\\\": [],\\\\n        \\\\\"innerError\\\\\": null,\\\\n        \\\\\"debugInfo\\\\\": null,\\\\n        \\\\\"additionalInfo\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\"innerError\\\\\": null,\\\\n    \\\\\"debugInfo\\\\\": null,\\\\n    \\\\\"additionalInfo\\\\\": null\\\\n  },\\\\n  \\\\\"correlation\\\\\": {\\\\n    \\\\\"operation\\\\\": \\\\\"7e01a9229eabc0436791651dbf0a0f0d\\\\\",\\\\n    \\\\\"request\\\\\": \\\\\"abeb5319c4529f23\\\\\"\\\\n  },\\\\n  \\\\\"environment\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"location\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"time\\\\\": \\\\\"2026-11-01T11:35:15.8434545+00:00\\\\\",\\\\n  \\\\\"componentName\\\\\": \\\\\"obotoken\\\\\",\\\\n  \\\\\"statusCode\\\\\": 400\\\\n}\"}}]}'))"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.847793411+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,847 INFO azure.ai.agentserver: Response caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65 completed: status=failed output_count=0"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.848074969+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,848 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.848737185+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,848 INFO azure.ai.agentserver: 192.168.0.1:48580 \"POST /responses 1.1\" 200 3322 2707522\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.848947296+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,848 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 2705.5ms (x-request-id: 0c1f38c13923d932fb5a7e2cce8c1be1, x-ms-client-request-id: bb4705bd-51de-4380-a698-ab390b949719, trace-id: 0c1f38c13923d932fb5a7e2cce8c1be1)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:15.849087174+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:15,849 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:35:18.934346756+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:35:18,934 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported.\n"
    }
  ],
  "status": "CAPTURED_CORRELATED_LINES",
  "limitation": "Bounded console SSE read, filtered to this pinned session's invocation time window. Sensitive and unrelated lines excluded; session IDs remain memory-only. Not a complete invocation log.",
  "cliStatus": "NOT_RETRIED",
  "source": "SDK get_session_log_stream; unique version/time-matched session"
}
```


Local full sources: `evidence\observability-c-native.json`, `evidence\observability-c-native-apim.json`.

</details>

<details>

<summary>Hosted service snapshot — c-native</summary>


```json
{
  "source": "evidence/observability-c-native.json#agentResponse",
  "responseId": "caresp_02e1e1d0d642c50b00rZWFgz9lPAZJNYd2lP5IMbK6xRFNXw65",
  "status": "failed",
  "error": {
    "code": "server_error",
    "messageExcerpt": "('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for \\'/subsc",
    "observedErrorCodes": [
      "AADSTS500016"
    ],
    "fullError": "evidence/observability-c-native.json#agentResponse.error"
  },
  "events": [],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

---

# C custom: OAuth2 Toolbox to your FastMCP API

![C custom flow: browser authorization code and refresh to a JWT-validating API](assets/workshop-custom-oauth.svg)

The hosted agent calls Toolbox; an OAuth connection obtains the authorizing user's API token.
Your FastMCP boundary validates that token before dispatching `probe_echo`; this is not proven OBO.

<details>
<summary>Deploy C custom: app registration, consent, HTTPS hosting and commands</summary>

### Prerequisites / registration / consent

- Custom delegated API, **not native Search**. Entra app developer/admin creates
  two single-tenant registrations in **Entra ID → App registrations**:
  - **API resource:** record Application ID; manifest `api.requestedAccessTokenVersion = 2`;
    **Expose an API** → `api://<API-application-id>` → delegated `access_as_user`.
    Choose user/admin consent setting according to tenant policy.
  - **Separate confidential client:** add delegated API `access_as_user` permission;
    create short-lived client secret, securely retain its **value**, not ID.
    Do not guess the redirect URI; provisioner discovers it.
- Entra admin grants required permission consent/user assignment. This is separate
  from the intended user's connection authorization; subscription roles grant neither.
- Project admin grants invoker/runtime model/Toolbox access.

### Deployment checklist

- Server terminal, from clone root:

```powershell
Set-Location .\samples\user-identity\custom-oauth
python -m venv .server-venv
.\.server-venv\Scripts\Activate.ps1
python -m pip install -r .\server-requirements.txt
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:ENTRA_AUDIENCE = "<API-application-client-id-GUID>"
python .\server.py
```

- Keep server running; publish port 8000 `/mcp` behind approved HTTPS hosting/TLS,
  preserving its environment. Foundry cannot reach localhost; sample creates no cloud host.
  Use the actual v2 audience (normally API client ID GUID).
- Second terminal **inside the same sample folder**, install/configure client:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant "<tenant-id>"
azd auth login --tenant-id "<tenant-id>"
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<your-custom-server>/mcp"
$env:CONNECTION_NAME = "my-custom-oauth"
$env:TOOLBOX_NAME = "my-custom-tools"
$env:OAUTH_CLIENT_ID = "<OAuth-client-application-id>"
$env:OAUTH_SCOPE = "api://<API-application-id>/access_as_user"
$secret = Read-Host "OAuth client secret value" -AsSecureString
$env:OAUTH_CLIENT_SECRET = [System.Net.NetworkCredential]::new("", $secret).Password
try { python .\provision_toolbox.py }
finally { Remove-Item Env:\OAUTH_CLIENT_SECRET; $secret = $null }
```

- Register **exact printed `properties.redirectUrl`** as a **Web** redirect on
  the OAuth client, not API app. This is platform callback discovery, not server
  OAuth-provider discovery.
- Foundry connection authorization: intended user checks client/API/scopes and
  approves in browser; complete required admin approval.
- Use shared hosted publishing for **agent package, not `server.py`**; wait for Active:

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = 'Call probe_echo with experiment_id "11111111-2222-4333-8444-555555555555", message "oauth-toolbox", count 1. Return the real result.'
$env:EXPECTED_TEXT = "CUSTOM_MCP_ENTRA_VALIDATED"
python .\invoke_hosted.py
```

</details>

## Agent code → Toolbox

The [custom hosted agent](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/hosted_agent.py) uses the same runtime pattern.
Input: project/model and Toolbox URL; output: a hosted Responses agent. OAuth belongs to the connection.

```python
import os
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential

async def main():
    credential = DefaultAzureCredential()
    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"], credential=credential,
        ),
        tools=FoundryToolbox(credential, name="retrieval", url=os.environ["TOOLBOX_ENDPOINT"]),
        instructions="Return actual requested Toolbox results/errors; never invent markers or identities.",
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()
```

## OAuth client → connection → Toolbox configuration

Complete [custom runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/README.md),
[provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/provision_toolbox.py)
and [server middleware](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/server.py).
Provider endpoints are explicit; provisioner passes them to
`azd ai connection create --auth-type oauth2`:

Input: client ID/secret, API scope and tenant endpoints. Output: an OAuth connection; register its discovered Web redirect URI and complete user authorization before invoking.

```powershell
$base = "https://login.microsoftonline.com/$env:AZURE_TENANT_ID/oauth2/v2.0/"
azd ai connection create $env:CONNECTION_NAME --kind remote-tool `
  --target $env:MCP_SERVER_URL --auth-type oauth2 `
  --authorization-url "${base}authorize" --token-url "${base}token" `
  --refresh-url "${base}token" --client-id $env:OAUTH_CLIENT_ID `
  --client-secret $env:OAUTH_CLIENT_SECRET `
  --scopes "$env:OAUTH_SCOPE offline_access" `
  --project-endpoint $env:FOUNDRY_PROJECT_ENDPOINT --no-prompt --force
```

Use the complete provisioner for redacted errors, timeout handling and redirect discovery; secret-in-argv requires a trusted workstation and no debug logging.
After connection creation, this SDK excerpt attaches the custom server to Toolbox:

```python
import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPToolboxTool
from azure.identity import AzureCliCredential

endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
connection_id = (
    os.environ["FOUNDRY_PROJECT_RESOURCE_ID"].rstrip("/")
    + "/connections/" + os.environ["CONNECTION_NAME"]
)
credential = AzureCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
with AIProjectClient(endpoint=endpoint, credential=credential) as project:
    version = project.toolboxes.create_version(
        name=os.environ["TOOLBOX_NAME"],
        tools=[MCPToolboxTool(
            name="retrieve", server_label="custom_probe",
            server_url=os.environ["MCP_SERVER_URL"],
            project_connection_id=connection_id, require_approval="never",
        )],
    )
    project.toolboxes.update(name=os.environ["TOOLBOX_NAME"], default_version=version.version)
print("TOOLBOX_ENDPOINT=" + endpoint + f"/toolboxes/{os.environ['TOOLBOX_NAME']}/mcp?api-version=v1")
```

Input: existing OAuth connection ID and HTTPS MCP URL. Output: the Toolbox endpoint consumed by the agent.

## Custom MCP: validate token before dispatch

The following three excerpts compose the [complete server](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/server.py).
Use its pinned server requirements; this validates a supplied token, not an OAuth authorization server or token exchange.

```python
import os
import jwt

TENANT = os.environ["ENTRA_TENANT_ID"]
AUDIENCE = os.environ["ENTRA_AUDIENCE"]
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
KEYS = jwt.PyJWKClient(
    f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys",
    cache_keys=True, lifespan=3600, timeout=15,
)

def validate(token):
    key = KEYS.get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token, key, algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER,
        options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid", "scp"]},
        leeway=30,
    )
    if claims["tid"] != TENANT or "access_as_user" not in claims["scp"].split():
        raise jwt.InvalidTokenError("Required tenant or delegated scope missing")
    return {name: claims.get(name) for name in ("tid", "oid", "aud", "iss", "scp", "azp", "ver")}
```

Signature/issuer/audience/timing/tenant/scope are enforced; `azp`/`ver` are returned,
not client allowlist checks. Delegated scope is not a row/document ACL.

### Request boundary → validated identity context

Input: HTTP bearer token. Output: request-local validated claims, or 401 before any MCP handler; `/healthz` is readiness only.

```python
import contextvars
from starlette.responses import JSONResponse

IDENTITY = contextvars.ContextVar("validated_identity", default=None)

class EntraBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"] == "/healthz":
            return await JSONResponse({"status": "ready"})(scope, receive, send)
        authorization = dict(scope["headers"]).get(b"authorization", b"").decode("ascii", errors="ignore")
        try:
            if not authorization.startswith("Bearer "):
                raise jwt.InvalidTokenError("Bearer token required")
            identity = validate(authorization[7:])
        except Exception:
            return await JSONResponse(
                {"error": "invalid_delegated_token"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
        handle = IDENTITY.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            IDENTITY.reset(handle)
```

### Validated context → MCP handler and result

Input: experiment UUID, allowlisted message and count 1–3. Output: sanitized arguments, marker and validated claims; never a bearer token.

```python
import uuid
from typing import Literal
import uvicorn
from fastmcp import FastMCP

mcp = FastMCP("Direct Toolbox Entra experiment", include_fastmcp_meta=False)

@mcp.tool
def probe_echo(
    experiment_id: str,
    message: Literal["hello-toolbox", "oauth-toolbox", "managed-toolbox"],
    count: int = 1,
) -> dict:
    experiment_id = str(uuid.UUID(experiment_id))
    if not 1 <= count <= 3:
        raise ValueError("count must be 1-3")
    identity = IDENTITY.get()
    if not identity:
        raise RuntimeError("Validated delegated identity required")
    args = {"experiment_id": experiment_id, "message": message, "count": count}
    return {"marker": "CUSTOM_MCP_ENTRA_VALIDATED", "arguments": args, "claims": identity}

if __name__ == "__main__":
    uvicorn.run(
        EntraBoundary(mcp.http_app(path="/mcp", stateless_http=True, json_response=True)),
        host="0.0.0.0", port=8000, access_log=False, log_level="warning",
    )
```

Keep the boundary wrapper when hosting; do not expose an unwrapped `mcp.http_app`.
The complete server adds structured audit events; retain claims only under the lab's privacy policy.

**One proof exercise:** compare actual returned UUID/message/count and validated
claims with the consenting user; retain no bearer token. Require no-token rejection:

```powershell
curl.exe -i "https://<your-custom-server>/mcp"
```

Normally 401, never a tool result. Controlled wrong-audience/missing-scope tokens
must also fail before tool execution; retain only statuses/sanitized reasons.
Distinguish ingress rejection from API validation. `/healthz` proves readiness only.
This is **authorization code + refresh**, not JWT-bearer OBO. Test consent/user binding:
the consenting user may differ from a later caller.

## Optional APIM evidence: C custom MCP

Fresh Azure hosted-agent executions on **November 1, 2026**, on the existing pinned `obs-20261031-*` routes. Original defaults are unchanged; no direct-route success is mixed into these results. Only public synthetic data was submitted. Body diagnostics are isolated (8192 bytes; no headers). Authorization/tokens, opaque consent identifiers/URLs and SDK session baggage are excluded from exports; nonsensitive queries/results are preserved.

### Live replay — c-custom: BLOCKED_OAUTH_CONSENT_REQUIRED

Agent `obs-20261031-c-custom` v2; Toolbox v3. UTC `2026-11-01T11:36:16.844683+00:00` → `2026-11-01T11:36:31.171699+00:00`. Experiment `dc8101ed-8983-41e9-a944-1fb7a69b91ed`.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call probe_echo exactly once with arguments {"experiment_id": "dc8101ed-8983-41e9-a944-1fb7a69b91ed", "message": "oauth-toolbox", "count": 2}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb`; status **incomplete**.

No hosted answer/tool output; returned event types:


```json
[
  "oauth_consent_request"
]
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `092f46e9-297e-4f5b-b29f-917f8f00b674`; backend HTTP **200**.

UTC request `2026-11-01T11:36:29.8106109Z`; response `2026-11-01T11:36:31.6934449Z`.

**No `tools/call` query was produced.** The observed `tools/list` request is discovery, not a user search or tool query.

Exact discovery parameters:


```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {
      "name": "mcp",
      "version": "0.1.0"
    },
    "io.modelcontextprotocol/clientCapabilities": {
      "sampling": {}
    },
    "traceparent": "00-398ba1ff2858f3c3edd27a4558abd71c-dec6b6ce83690969-01",
    "baggage": "<baggage-redacted>"
  }
}
```


Actual MCP error excerpt (unmodified substring; full below):


```text
tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"CONSENT_REQUIRED","message":"<consent-url-redacted>"}}]}
```


**3. Downstream MCP/runtime logs: what was actually observed**

No correlated downstream `tools/call` query/result console event was retrieved. The observed error/consent blocks this captured route before a tool query; missing logs alone do not prove no execution.

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T11:46:09.698070+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T11:36:31.936390392+00:00`.


```text
2026-11-01 11:36:31,936 WARNING agent_framework_foundry_hosting._responses: Consent URL for tool 'observed': <consent-url-redacted>
```


<details>

<summary>Real logged exchange — c-custom: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1`. Configured downstream target: `https://abc-custom-mcp-e8383e4d.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` (configuration is not execution evidence).

Caller-context SHA-256: `+pG4dG7duQJ+rpHM/GrKhQD8DThwyBG1z4GOrz1FE+c=`.

Exact captured request (only sensitive baggage redacted):


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-398ba1ff2858f3c3edd27a4558abd71c-dec6b6ce83690969-01","baggage":"<baggage-redacted>"}}}
```


Exact captured response:


```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32006,
    "message": "tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"CONSENT_REQUIRED\",\"message\":\"<consent-url-redacted>\"}}]}"
  }
}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "6db843c5-c109-4cc4-bf4d-953096b5533d",
    "callerContextPresent": "True",
    "callerContextHash": "+pG4dG7duQJ+rpHM/GrKhQD8DThwyBG1z4GOrz1FE+c=",
    "observedPlatformPrincipalId": "114281a8-d2fe-407c-a1cf-28461136d9af",
    "requestTimestamp": "2026-11-01T11:36:29.4868012Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-398ba1ff2858f3c3edd27a4558abd71c-825f773f7a9ea1af-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T11:36:29.6440545Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 1,\n  \"result\": {\"resultType\":\"complete\",\"supportedVersions\":[\"2025-11-25\",\"2026-07-28\"],\"capabilities\":{\"tools\":{},\"resources\":{},\"extensions\":{\"io.modelcontextprotocol/skills\":{},\"io.modelcontextprotocol/tasks\":{}}},\"_meta\":{\"io.modelcontextprotocol/serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}},\"instructions\":\"This server exposes tools configured in the requested Foundry toolbox. Use tools/list to enumerate available tools and tools/call to invoke them.\",\"ttlMs\":300000,\"cacheScope\":\"private\"}\n}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "092f46e9-297e-4f5b-b29f-917f8f00b674",
    "callerContextPresent": "True",
    "callerContextHash": "+pG4dG7duQJ+rpHM/GrKhQD8DThwyBG1z4GOrz1FE+c=",
    "observedPlatformPrincipalId": "114281a8-d2fe-407c-a1cf-28461136d9af",
    "requestTimestamp": "2026-11-01T11:36:29.8106109Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-398ba1ff2858f3c3edd27a4558abd71c-dec6b6ce83690969-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T11:36:31.6934449Z",
    "responseBody": "{\n  \"jsonrpc\": \"2.0\",\n  \"id\": 2,\n  \"error\": {\n    \"code\": -32006,\n    \"message\": \"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"CONSENT_REQUIRED\\\",\\\"message\\\":\\\"<consent-url-redacted>\\\"}}]}\"\n  }\n}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb",
  "object": "response",
  "output": [
    {
      "id": "<oauth-request-id-redacted>",
      "response_id": "caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb",
      "type": "oauth_consent_request",
      "consent_link": "<consent-url-redacted>",
      "server_label": "observed",
      "agent_reference": null
    }
  ],
  "created_at": 1793532988,
  "parallel_tool_calls": false,
  "status": "incomplete",
  "response_id": "caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-c-custom",
    "version": "2"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
```


Runtime query result:


```json
{
  "scenario": "c-custom",
  "agent": "obs-20261031-c-custom",
  "version": "2",
  "experimentId": "dc8101ed-8983-41e9-a944-1fb7a69b91ed",
  "responseId": "caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb",
  "invocationStartedAt": "2026-11-01T11:36:16.844683+00:00",
  "invocationCompletedAt": "2026-11-01T11:36:31.171699+00:00",
  "queriedAt": "2026-11-01T11:46:09.698070+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:16.740915107+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:16.748858649+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.178423134+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,178 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.317553063+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,317 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,350 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.351236677+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.354109363+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,354 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.354275730+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,354 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.354728304+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,354 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.354830352+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,354 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.598980061+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,597 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.604794410+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,604 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.605528522+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,605 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.605713529+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,605 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.610584677+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,606 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.612971057+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 11:36:17 +0000] [45] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.613031149+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,612 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.707477410+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,707 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 5563d02904a78d87690fdecbfa4d55d1)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.709204777+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,709 INFO azure.ai.agentserver: 192.168.0.1:37330 \"GET /readiness 1.1\" 200 20 1907\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:17.709490497+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:17,709 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 1.8ms (trace-id: 5563d02904a78d87690fdecbfa4d55d1)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.300209925+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,295 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 398ba1ff2858f3c3edd27a4558abd71c, x-ms-client-request-id: 460e6180-c4ff-4913-8303-538640cf3a92, trace-id: 398ba1ff2858f3c3edd27a4558abd71c)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.300209925+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,299 INFO azure.ai.agentserver: Creating response caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb: streaming=False background=False store=True model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.300687903+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,300 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.713922371+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,713 INFO azure.identity.aio._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.873219378+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,873 INFO azure.ai.agentserver: Foundry storage POST ***/storage/responses?api-version=v1 -> 201 (158.8ms, x-ms-client-request-id=7a249aba-d5e8-11f1-a33c-2edc0203a0ec, traceparent=, x-request-id=82665c0f40ddfbfde09b476ffd39645d, apim-request-id=0c345108-4715-413a-bc62-27f5d2895c16, has_call_id=True)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.873938861+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,873 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:28.874731621+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:28,874 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:29.083758493+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:29,083 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:29.616499701+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:29,616 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:29.637215755+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:29,637 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:29.641734746+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:29,637 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:29.641941493+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:29,641 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.665770357+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,665 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.670078220+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,670 WARNING azure.ai.agentserver.core._experimental: Class azure.ai.agentserver.core.storage._state.FoundryStateStore: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.670412363+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,670 INFO azure.identity.aio._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.670749218+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,670 INFO azure.identity.aio._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.713638102+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,713 INFO azure.identity.aio._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.785687687+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,785 WARNING azure.ai.agentserver.core: Foundry storage GET ***/storage/state_stores/*?api-version=v1 -> 404 (71.7ms, x-ms-client-request-id=7c1eb5e4-d5e8-11f1-a33c-2edc0203a0ec, traceparent=, x-request-id=604a228f16931123a8bd8e4ae1b4fc69, apim-request-id=cfba75d9-1451-4c0c-9f83-d3bffaf0531e)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.786106968+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,786 WARNING azure.ai.agentserver.core._experimental: Class azure.ai.agentserver.core.storage._errors.FoundryStorageNotFoundError: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.850208203+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,850 INFO azure.ai.agentserver.core: Foundry storage POST ***/storage/state_stores?api-version=v1 -> 201 (63.5ms, x-ms-client-request-id=7c304d0e-d5e8-11f1-a33c-2edc0203a0ec, traceparent=, x-request-id=604a228f16931123a8bd8e4ae1b4fc69, apim-request-id=8299b073-d18d-4c94-9097-a165cf9ebaba)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.934865188+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,934 INFO azure.ai.agentserver.core: Foundry storage POST ***/storage/state_stores/*/items?api-version=v1 -> 201 (83.8ms, x-ms-client-request-id=7c3a1d0c-d5e8-11f1-a33c-2edc0203a0ec, traceparent=, x-request-id=604a228f16931123a8bd8e4ae1b4fc69, apim-request-id=9706adf5-6689-4990-85e9-88ff0da34324)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:31.936390392+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:31,936 WARNING agent_framework_foundry_hosting._responses: Consent URL for tool 'observed': <consent-url-redacted>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.037978160+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,037 INFO azure.ai.agentserver: Foundry storage POST ***/storage/responses/caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb?api-version=v1 -> 200 (100.6ms, x-ms-client-request-id=7c4747c0-d5e8-11f1-a33c-2edc0203a0ec, traceparent=, x-request-id=82665c0f40ddfbfde09b476ffd39645d, apim-request-id=2019c892-d04c-4488-8682-1881c4d38b07, has_call_id=True)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.038329922+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,038 INFO azure.ai.agentserver: Response caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb completed: status=incomplete output_count=1"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.038621938+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,038 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.039302263+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,039 INFO azure.ai.agentserver: 192.168.0.1:36396 \"POST /responses 1.1\" 200 3081 3746143\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.039527126+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,039 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 3742.3ms (x-request-id: 398ba1ff2858f3c3edd27a4558abd71c, x-ms-client-request-id: 460e6180-c4ff-4913-8303-538640cf3a92, trace-id: 398ba1ff2858f3c3edd27a4558abd71c)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.039676144+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,039 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T11:36:32.858399312+00:00",
      "stream": "stderr",
      "line": "2026-11-01 11:36:32,858 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported.\n"
    }
  ],
  "status": "CAPTURED_CORRELATED_LINES",
  "limitation": "Bounded console SSE read, filtered to this pinned session's invocation time window. Sensitive and unrelated lines excluded; session IDs remain memory-only. Not a complete invocation log.",
  "cliStatus": "NOT_RETRIED",
  "source": "SDK get_session_log_stream; unique version/time-matched session"
}
```


Local full sources: `evidence\observability-c-custom.json`, `evidence\observability-c-custom-apim.json`.

</details>

<details>

<summary>Hosted service snapshot — c-custom</summary>


```json
{
  "source": "evidence/observability-c-custom.json#agentResponse",
  "responseId": "caresp_072513b129f42efa00FbUyLcSGmShgBkil9fwhT75iEIQVVZjb",
  "status": "incomplete",
  "error": null,
  "events": [
    {
      "type": "oauth_consent_request"
    }
  ],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

---

# Compare results and troubleshoot

## Record one selected track

### Six-path evidence matrix (fresh November 1 upstream APIM replay)

The agent code, Toolbox/connection configuration and service/backend contract are
shown in each corresponding A/B/C section above. The six **Real logged exchange**
foldables contain the correlated APIM request/response bodies and timestamps.
Configuration is not proof that a downstream request occurred.

| Path | Toolbox → MCP configured identity | Backend contract | APIM result | Hosted snapshot | Downstream MCP log |
| --- | --- | --- | --- | --- | --- |
| A native | Project `oid`; `ProjectManagedIdentity` | Service-provided Search KB MCP; Search MI accesses index | PASS tool query/result | Completed call and tool output in A | Search internal query/fan-out NOT_OBSERVED; no service-owned MCP console capture |
| A custom | Project `oid`; `ProjectManagedIdentity` | Application-only FastMCP validates API audience and allowlisted project `oid` | PASS validated marker/result | Completed call and tool output in A | Correlated validated query/result in `mcpValidatedQueryResultEvents` |
| B native | Intended agent-instance `oid`; `AgenticIdentityToken` | Service-provided Search KB MCP | BLOCKED `AgentInstanceClientId` | Failed service response; no tool output | NOT_OBSERVED: context resolution blocked |
| B custom | Intended agent-instance `oid`; `AgenticIdentityToken` | Application-only FastMCP validates API audience and allowlisted agent `oid` | BLOCKED `AgentInstanceClientId` | Failed service response; no tool output | NOT_OBSERVED: context resolution blocked |
| C native | Intended user `oid`; `UserEntraToken` | Managed Search user connection; user Search roles/ACLs | BLOCKED `AADSTS500016` | Failed context entry in C native | NOT_OBSERVED: user token flow blocked |
| C custom | Intended delegated user `oid`; `OAuth2` | Separate delegated FastMCP validates audience, issuer and scope | BLOCKED pending consent | Incomplete; consent event only | NOT_OBSERVED: no consent-completed tool call |

The OAuth2 connection uses **authorization-code consent**, not literal OBO.
The original direct C custom OAuth success is a different invocation and route;
it does not turn this optional upstream APIM consent-blocked capture into a PASS.
Native Search query text in the tool call is observed at the MCP boundary, not
an observed internal Search query or actual backend fan-out.

The three numbered stages in each scenario distinguish the exact user prompt, actual hosted response, generated MCP arguments (or blocked discovery), APIM result and downstream console evidence. Full sanitized bodies are secondary foldables. Fresh pinned hosted console queries are saved in `evidence\observability-hosted-runtime.json`; their explicit statuses distinguish unavailable or uncorrelated logs from service response snapshots. Native Search internal queries remain not observed. All six new invocation records and telemetry are retained locally in ignored `evidence\observability-real-exchanges.json` and per-scenario files; historical UUID-named records remain separate.

| Item | Local evidence |
| --- | --- |
| Environment | Tenant/subscription, track, project and test backend |
| Hosted state | Active name/version, connection auth and Toolbox endpoint |
| Identity | Actual object ID, audience, RBAC scope or delegated scope |
| Allow/deny | Timestamp/correlation, genuine tool result/marker vs actual failure |
| Limits | Backend audit, validated API claims or configuration inference? |

- No tokens, secrets, personal prompts or production response bodies.
- Use existing [observability queries](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/observability.md).
  Allow ingestion delay. Standalone samples do not install root custom audit middleware.

## Troubleshoot by boundary

- Deployment: subscription, Standard v2 SKU, preview/quota and RBAC write scope.
- 401: tenant/issuer/audience/expiry; never print tokens.
- 403: actual downstream principal/effective permissions; wait for propagation.
- Consent challenge: browser approval then retry; not an authorization deny proof.
- Unreachable tool: verify HTTPS reachability from service network, not localhost.
- No marker: inspect actual tool result, not model narrative.
- No logs: verify diagnostics/ingestion; absence in one query does not prove no storage.

## Optional gateway extension

- The six real exchanges above use separate `obs-20261031-*` **upstream** APIs;
  do not enable body capture or repoint default traffic on original APIs.
  These replay helpers target an already configured ABC lab, not the independent
  environment-variable sample provisioners:

```powershell
# Existing ignored ABC runtime configurations; never commit their contents.
$configPath = "..\foundry-ai-gateway\foundry-abc-observability\.config.json"
$customPath = "..\foundry-ai-gateway\foundry-abc-observability\.custom-mcp-config.json"
az account show --query "{name:name,state:state}" -o json

# New application-only server; reuses existing API registration without editing C OAuth.
python .\deploy_application_probe.py --config $configPath --custom-config $customPath --action build
python .\deploy_application_probe.py --config $configPath --custom-config $customPath --action deploy
$customEndpoint = (Get-Content .\evidence\application-probe-deploy.json -Raw | ConvertFrom-Json).endpoint

# Choose only the desired isolated scenario; existing original agents are never republished.
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario a-custom --action deploy --custom-endpoint $customEndpoint
python .\deploy_application_probe.py --config $configPath --custom-config $customPath --action allowlist
python .\deploy_application_probe.py --config $configPath --custom-config $customPath --action check

# Correlate safe captures, then validate embedded bodies and isolation.
python .\collect_mcp_exchanges.py --custom-config $customPath
python .\collect_hosted_runtime_logs.py --config $configPath
python .\compile_observability_evidence.py
python .\update_observability_workshop.py
python .\validate_observability_docs.py
python .\audit_observability.py --config $configPath
python -m unittest test_observability test_custom_application_samples test_standalone_samples test_local -q
```

- `--scenario` accepts `a-native`, `a-custom`, `b-native`, `b-custom`, `c-native`,
  `c-custom`; replay commands are included in each foldable. Hosted sessions use
  a specific recorded agent version, never an original default selector.
- The bounded B/C-OAuth alternative used
  `--republish --requirements .\hosted\observability-latest-requirements.txt`
  on **only the isolated probe names**. It did not resolve B's platform context
  error or C's missing OAuth consent. The stable manifest avoids the original
  incompatible `mcp.Client` import; both versions and initial failures are retained.
- Allow Azure Monitor ingestion delay before `--action collect`. A new replay
  has new IDs/timestamps: recompile and refresh workshop excerpts rather
  than treating the captured bodies above as synthetic expected outputs.
- Inventory: six isolated APIs, six Toolboxes, six hosted agent names, two custom
  downstream connections, and container `obs-application-mcp-20261031`.
  `evidence\observability-real-exchanges.json` contains correlated safe captures.
  Read-only auditing confirmed all **11 original agent default endpoints unchanged**
  across replay attempts and all six isolated diagnostics at 8192 bytes with no headers.
  Native Search internal queries remain **not observed**, not reconstructed.

- Review root README before billable full `setup.ps1`/`verify.ps1`; these assume/provision
  all showcase routes, not a copied sample.
- B data gateway, C ingress, no-store and BYOM/dedicated AI Gateway are distinct
  experiments. Standard v2 is the verified classic environment; dedicated gateway
  has separate Terraform/portal prerequisites.
- Runtime keys are gateway-wide; strict separate model boundaries need separate gateways.

**Reflect:** no-store, log capture, user authorization and model access are independent controls.

---

# Cleanup and next steps

Keep an inventory of newly created resources/roles/connections/Toolboxes/versions/apps.
Never delete pre-existing/shared resources.

- Stop/delete hosted deployments and custom hosting first.
- If you ran the optional observability extension, inventory and remove only
  its six `obs-20261031-*` APIM APIs and their dedicated backends/loggers/diagnostics,
  isolated hosted agents/Toolboxes, two custom downstream connections and
  `obs-application-mcp-20261031` container resources. Do not remove original
  ABC routes, shared loggers or the pre-existing C OAuth connection.
- Remove workshop connections/Toolboxes/agents through supported Foundry management.
- Delete dedicated, newly created `abc-*` projects in the **existing Foundry account**.
- Save role assignment IDs before deleting identities. Remove workshop Foundry roles
  (including model roles for the three Search MIs) and user/agent Search roles.
- Review dedicated group contents, then delete only if everything belongs to this workshop:

```powershell
az resource list --resource-group "rg-foundry-identity-workshop" -o table
az group delete --name "rg-foundry-identity-workshop" --yes
```

- Keep reused Foundry/model/APIM. Separately owned Terraform environment:
  review `terraform plan -destroy` before teardown; Bicep has no automatic inverse.
- Remove dedicated OAuth grants/apps, revoke/rotate client secret and clear local
  environment. Stop local server; remove evidence/config/venvs per retention policy.
- Verify resource inventory **and billing**: deleting Search group alone is incomplete.

Production: use the
[secure target architecture](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/recommended-secure-architecture.svg),
least privilege, controlled consent, document ACLs, supported private networking and
content-minimized diagnostics. Validate preview identity paths in your environment.

**Done:** one hosted allow, genuine deny, labeled evidence limitations and verified cleanup.
MOAW publication/preview: [maintainer guide](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/moaw-publishing.md).
