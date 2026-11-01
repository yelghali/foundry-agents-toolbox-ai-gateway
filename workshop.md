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
or arbitrary queries. Logging is disabled by default; protect any captured results.

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

These are actual **hosted agent → APIM → Toolbox → MCP** runs, not illustrative
payloads. Original agents/default traffic remain direct and unchanged. API names
start with `obs-20261031-`; body diagnostics are enabled only there, at 8192 bytes,
with **no logged request/response headers**. Tokens, consent URLs and SDK baggage
(opaque session/user propagation metadata) are redacted from exported evidence.
Prompts/results and SDK metadata persist in Azure Monitor: use only public demo data.

Set `$configPath` and `$customPath` to your existing ignored `.config.json` and
`.custom-mcp-config.json`; do not publish either file. Run commands from the repository root.

<details>
<summary>Real logged exchange — A native KB: PASS at the MCP query/result boundary</summary>

Isolated agent `obs-20261031-a-native`, pinned **v2**, Toolbox **v2**.
APIM request `76e91f3f-c243-4f7f-9b1f-7f28f9716e8c`; POST at
`2026-10-31T20:55:10.0167621Z`, response at `2026-10-31T20:55:12.7560888Z`, HTTP **200**.
Caller context was present; only SHA-256 hash
`AUlffY76/sqO0o/7DbQt1GT8C2aSLQmKZ0J7rmRQI/o=` was exported.

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1`.
Exact captured request, with baggage redacted:

```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-d80ac5f9a5ba5d2d9b86f7d163553dd8-c870c06cfc63b113-01","baggage":"<baggage-redacted>","generateCitations":true,"KnowledgeSourceMetadata":[{"name":"ks-a","type":"searchIndex"}],"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"name":"observed___knowledge_base_retrieve","arguments":{"queries":["Find the normal access record in cohort A"]}},"jsonrpc":"2.0","id":3}
```

Exact captured response:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {"_meta":{"agenticReasoningTokens":28,"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"content":[{"type":"text","text":"The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.","_meta":{"x-request-id":"216c96c5-00b7-4b0e-8f6c-38e2029a779c"}},{"type":"text","text":"{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}","_meta":{"x-request-id":"216c96c5-00b7-4b0e-8f6c-38e2029a779c","title":"Cohort A access record","preserveExactValue":false}}],"structuredContent":null}
}
```

The configured KB URL is visible in `tool_configuration`; the returned
`mcp://searchindex/normal` reference is observed result evidence, **not a captured
Search HTTP destination/query**. Native Search's internally generated downstream
query and server-side token claims were not observed at this upstream hop.

```powershell
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario a-native --action replay
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario a-native --action collect
```

Persistent safe evidence: `evidence\observability-a-native.json` and
`evidence\observability-a-native-apim.json`. An earlier SDK dependency/import
failure is retained separately; it is not counted as a successful call.

</details>

<details>
<summary>Real logged exchange — A custom FastMCP: PASS with validated application principal</summary>

Isolated agent `obs-20261031-a-custom`, pinned **v1**, Toolbox **v1**.
APIM request `b0edd264-f627-4710-b8b2-097645d0f475`; POST at
`2026-10-31T20:56:00.9115468Z`, response at `2026-10-31T20:56:01.0913094Z`, HTTP **200**.
Caller context was present; only hash
`O3e0czaXCqvPTiZRGRlJCtHWp0DkMZvP838G581OYvs=` was exported.
POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1`.

Exact captured request, with baggage redacted:

```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-3c92d5e24759a4e50b3d70a5a738f650-52b7b621ab1b8c89-01","baggage":"<baggage-redacted>","tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"name":"observed___identity_probe","arguments":{"experiment_id":"eafd7a76-c831-493e-a437-2848861fe1b0"}},"jsonrpc":"2.0","id":3}
```

Exact captured response:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {"_meta":{"tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"content":[{"type":"text","text":"{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"eafd7a76-c831-493e-a437-2848861fe1b0\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\"}}"}],"isError":false,"structuredContent":{"marker":"CUSTOM_MCP_APPLICATION_VALIDATED","experiment_id":"eafd7a76-c831-493e-a437-2848861fe1b0","claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0"}}}
}
```

Actual console event from **observed** Azure container `obs-application-mcp-20261031`,
correlated by the same UUID (not just by configured URL):

```json
{"event":"validated_mcp_exchange","timestamp":"2026-10-31T20:56:01.079265+00:00","method":"tools/call","tool":"identity_probe","query":{"experiment_id":"eafd7a76-c831-493e-a437-2848861fe1b0"},"result":{"marker":"CUSTOM_MCP_APPLICATION_VALIDATED","experiment_id":"eafd7a76-c831-493e-a437-2848861fe1b0","claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0"}}}
```

The data `oid` is A's **project MI**, not the hosted agent's platform identity.
The server verifies signature, tenant/v2 issuer, audience/timing and explicit
principal ACL, rejecting delegated `scp` tokens. It performs no token acquisition
or OBO. The new server's `/healthz` returned **200**; anonymous `/mcp` returned **401**
`{"error":"invalid_application_token"}`. C's delegated-only server is unchanged.

```powershell
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario a-custom --action replay
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario a-custom --action collect
python .\collect_mcp_exchanges.py --custom-config $customPath
```

Persistent safe evidence: `evidence\observability-a-custom.json`,
`evidence\observability-a-custom-apim.json`, `evidence\observability-mcp-exchanges.json`.

</details>


### Hosted responses and downstream log evidence

These snapshots are persisted hosted service responses, not runtime console logs.
Runtime console logs were not captured for these invocations.

<details>
<summary>Hosted service snapshot — a-native</summary>

```json
{
  "source": "evidence/observability-a-native.json#agentResponse",
  "responseId": "caresp_0816b801af31f0a400UaMG2RXFne1TB5U7vAlqgWyXy6yUvORA",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___knowledge_base_retrieve",
      "call_id": "call_9nfjE2V8hiGg6msYZ0qimQpJ",
      "arguments": "{\"queries\":[\"Find the normal access record in cohort A\"]}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_9nfjE2V8hiGg6msYZ0qimQpJ",
      "output": "The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.\n{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}",
      "status": "completed"
    }
  ],
  "runtimeConsoleLog": "NOT_CAPTURED",
  "limitation": "Hosted service response snapshot; not a runtime console log. No new invocation or telemetry retrieval performed."
}
```

</details>

<details>
<summary>Hosted service snapshot — a-custom</summary>

```json
{
  "source": "evidence/observability-a-custom.json#agentResponse",
  "responseId": "caresp_009cf52f1d17852000yvjk70kp279ttoKLVa8PacM47VhHftyl",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___identity_probe",
      "call_id": "call_EjJMsvHgK7gxMWWsC7o60B3k",
      "arguments": "{\"experiment_id\":\"eafd7a76-c831-493e-a437-2848861fe1b0\"}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_EjJMsvHgK7gxMWWsC7o60B3k",
      "output": "{\"marker\": \"CUSTOM_MCP_APPLICATION_VALIDATED\", \"experiment_id\": \"eafd7a76-c831-493e-a437-2848861fe1b0\", \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\"}}",
      "status": "completed"
    }
  ],
  "runtimeConsoleLog": "NOT_CAPTURED",
  "limitation": "Hosted service response snapshot; not a runtime console log. No new invocation or telemetry retrieval performed."
}
```

</details>

<details>
<summary>Actual MCP console event — a-custom only</summary>

This is the correlated application server's validated request/result, not a
reconstruction from APIM or model text. No corresponding console event was
observed for the other five selected paths; the matrix gives the reasons.

```json
{
  "azureTimestamp": "2026-10-31T20:56:01.0796207+00:00",
  "event": "validated_mcp_exchange",
  "timestamp": "2026-10-31T20:56:01.079265+00:00",
  "method": "tools/call",
  "tool": "identity_probe",
  "query": {
    "experiment_id": "eafd7a76-c831-493e-a437-2848861fe1b0"
  },
  "result": {
    "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
    "experiment_id": "eafd7a76-c831-493e-a437-2848861fe1b0",
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
from the successful native Search flow.

The server validates signature, issuer, audience and expiry, then authorizes an
explicit agent principal allowlist. The sample uses ACL authorization rather
than role enforcement. Call `identity_probe` with a synthetic experiment UUID;
the result returns only safe validated identifier claims and marker
`CUSTOM_MCP_APPLICATION_VALIDATED`. Logging is off by default.
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

<details>
<summary>Real logged exchange — B native KB: BLOCKED at agent-instance context resolution</summary>

Actual isolated `obs-20261031-b-native` **agent v3 / Toolbox v3**, including the
bounded October-30 hosting SDK retry with request-scoped agent creation.
APIM request `0f8d72ff-ffb1-452d-babf-6a9e4068861e`; request
`2026-10-31T21:09:47.4998162Z`, response `2026-10-31T21:09:47.7646644Z`.
The wrapper was HTTP **200**, but MCP returned **-32007** with downstream
connection resolution **HTTP_400**: this is **not a successful KB call**.
Caller context was present and forwarded; its exported SHA-256 hash was
`uOhtoqcxTMbmOxCaHpxvltA160TG6/mr/23dYizYHvY=`.

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1`.
Exact captured request, with baggage redacted:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-3b8495ad966418ff6453883c486ad010-2c0bab6ea5c19604-01","baggage":"<baggage-redacted>"}}}
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

Configured destination:
`https://srchabcb7puse24s5tluc.search.windows.net/knowledgebases/kb-b/mcp?api-version=2026-05-01-preview`.
**No native MCP query/result or Search internal query was observed**: discovery
failed first. Header presence/hash is not proof that Toolbox resolved instance
and blueprint context. Both pinned October-2 and October-30 SDK attempts
encountered this same resolver error. No project/user authentication fallback,
forged caller context, or manual token exchange was attempted.

```powershell
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario b-native --action replay
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario b-native --action collect
```

Safe evidence: `evidence\observability-b-native.json` and
`evidence\observability-b-native-apim.json`; the earlier v2 attempt is retained
in `evidence\observability-b-native-stable.json`.

</details>

<details>
<summary>Real logged exchange — B custom FastMCP: deployed and ready, but BLOCKED before invocation</summary>

Actual isolated `obs-20261031-b-custom` **agent v2 / Toolbox v2**.
APIM request `f1b2c5ee-6ce1-4d81-bf10-804ecc8b431b`; POST
`2026-10-31T21:10:24.3861895Z`, response `2026-10-31T21:10:24.608785Z`.
Wrapper HTTP **200** / MCP **-32007** / source **HTTP_400**.
Caller context was present; only hash
`RE/w/kVgxwV/qKZz0WbA2gu98dHPVK8ntl2ZhoUXGLo=` was exported.

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1`.
Exact captured request, with baggage redacted:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-dab7e1c364de77f34f5a1284d965cb45-f32c30b1475b9976-01","baggage":"<baggage-redacted>"}}}
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

Configured custom destination is the separate ready server
`https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp`.
Its principal ACL contains A's project MI and this B agent's
`d6fb1ff2-6587-4169-b279-20103b371ab7`; it accepts only validated application tokens,
not user/delegated tokens. **No B token claims or validated custom query/result
were observed** for experiment `1163be77-5d52-4dd9-8853-f4ead9f9f2b8`.
The server's readiness/anonymous-401 probes and A's successful call do not prove B
acquisition. The configured URL is not an observed B destination.

```powershell
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario b-custom --action replay
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario b-custom --action collect
python .\collect_mcp_exchanges.py --custom-config $customPath
```

Safe evidence: `evidence\observability-b-custom.json`,
`evidence\observability-b-custom-apim.json`, `evidence\application-probe-check.json`.
The earlier SDK attempt is retained in `evidence\observability-b-custom-stable.json`.
No C OAuth secret/connection/consent was changed to enable this application-only target.

</details>


### Hosted responses and downstream log evidence

These snapshots are persisted hosted service responses, not runtime console logs.
Runtime console logs were not captured for these invocations.

<details>
<summary>Hosted service snapshot — b-native</summary>

```json
{
  "source": "evidence/observability-b-native.json#agentResponse",
  "responseId": "caresp_01f8845ff2bd80c200GYB9dp6bCG95imb0PZJRCl7ITsTBzyh3",
  "status": "failed",
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "events": [],
  "runtimeConsoleLog": "NOT_CAPTURED",
  "limitation": "Hosted service response snapshot; not a runtime console log. No new invocation or telemetry retrieval performed."
}
```

</details>

<details>
<summary>Hosted service snapshot — b-custom</summary>

```json
{
  "source": "evidence/observability-b-custom.json#agentResponse",
  "responseId": "caresp_03786019a4f2cb7b006i79bsWf4pS13JknS2zbmeufzU5ABa21",
  "status": "failed",
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "events": [],
  "runtimeConsoleLog": "NOT_CAPTURED",
  "limitation": "Hosted service response snapshot; not a runtime console log. No new invocation or telemetry retrieval performed."
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

## Prerequisites / registration / consent

- Trusted Search KB, platform-managed user context supported by the hosted runtime.
  **No custom API/client registration, secret or callback**; do not substitute FastMCP.
- Project admin grants invoker/runtime access and enables supported user context.
- Search admin grants **eventual invoking user's object ID** Search Index Data Reader,
  not automatically the provisioning administrator.
- Intended user completes any platform connection authorization in browser;
  tenant restrictions may require admin approval. Retry afresh, never auto-follow consent URLs.

## Deployment checklist

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

<details>
<summary>Real logged exchange — C UserEntraToken native KB: BLOCKED by AADSTS500016</summary>

Actual isolated `obs-20261031-c-native` **agent v2 / Toolbox v2**;
`UserEntraToken` still references the original trusted KB connection.
APIM request `d83d1d91-10a6-405a-b70a-a719bca0dddb`; POST
`2026-10-31T20:58:51.3406004Z`, response `2026-10-31T20:58:52.2783609Z`.
Wrapper HTTP **200**, MCP **-32007**, platform token-flow **HTTP_400**.
Caller context was present; only hash
`HhzxiZtErp6HAS4jUIk4FpMxNSqdr3qIydEjZOn2OwM=` was exported.

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1`.
Exact captured request:

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
    "message": "tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\r\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\r\\nStatus Code: 400 BadRequest\\r\\nError Code: ValidationError\\r\\nReason Phrase: Bad Request\\r\\nResponse Body: {\\n  \\\"error\\\": {\\n    \\\"code\\\": \\\"ValidationError\\\",\\n    \\\"severity\\\": null,\\n    \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: e6103290-ded6-4c37-b298-02c884b76600 Correlation ID: 95157e84-50f5-463b-8f68-c0faa441f021 Timestamp: 2026-10-31 20:58:52Z\\\",\\n    \\\"messageFormat\\\": null,\\n    \\\"messageParameters\\\": null,\\n    \\\"referenceCode\\\": null,\\n    \\\"detailsUri\\\": null,\\n    \\\"target\\\": \\\"UserToken\\\",\\n    \\\"details\\\": [\\n      {\\n        \\\"code\\\": \\\"Invalid\\\",\\n        \\\"severity\\\": null,\\n        \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: e6103290-ded6-4c37-b298-02c884b76600 Correlation ID: 95157e84-50f5-463b-8f68-c0faa441f021 Timestamp: 2026-10-31 20:58:52Z\\\",\\n        \\\"messageFormat\\\": null,\\n        \\\"messageParameters\\\": {},\\n        \\\"referenceCode\\\": null,\\n        \\\"detailsUri\\\": null,\\n        \\\"target\\\": \\\"UserToken\\\",\\n        \\\"details\\\": [],\\n        \\\"innerError\\\": null,\\n        \\\"debugInfo\\\": null,\\n        \\\"additionalInfo\\\": null\\n      }\\n    ],\\n    \\\"innerError\\\": null,\\n    \\\"debugInfo\\\": null,\\n    \\\"additionalInfo\\\": null\\n  },\\n  \\\"correlation\\\": {\\n    \\\"operation\\\": \\\"05418752701db43fa2041d4286645b63\\\",\\n    \\\"request\\\": \\\"00f71df1db2197cd\\\"\\n  },\\n  \\\"environment\\\": \\\"eastus2\\\",\\n  \\\"location\\\": \\\"eastus2\\\",\\n  \\\"time\\\": \\\"2026-10-31T20:58:52.2586051+00:00\\\",\\n  \\\"componentName\\\": \\\"obotoken\\\",\\n  \\\"statusCode\\\": 400\\n}\"}}]}"
  }
}
```

Configured destination:
`https://srchabcc7puse24s5tluc.search.windows.net/knowledgebases/kb-c/mcp?api-version=2026-05-01-preview`.
**No KB MCP query/result or downstream Search query was observed** because user
token resolution failed during discovery. The error's timestamp/correlation IDs
are actual platform evidence, not a guessed tenant-consent diagnosis.
No project/agent Search grant, app-only fallback or custom OBO bypass was added
to this track.

```powershell
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario c-native --action replay
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario c-native --action collect
```

Safe evidence: `evidence\observability-c-native.json`,
`evidence\observability-c-native-apim.json`.

</details>


### Hosted responses and downstream log evidence

These snapshots are persisted hosted service responses, not runtime console logs.
Runtime console logs were not captured for these invocations.

<details>
<summary>Hosted service snapshot — c-native</summary>

```json
{
  "source": "evidence/observability-c-native.json#agentResponse",
  "responseId": "caresp_0c8bf7382b257626009DmMkGPfMs8skRD1dcTbXkkgZMpkZZXB",
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
  "runtimeConsoleLog": "NOT_CAPTURED",
  "limitation": "Hosted service response snapshot; not a runtime console log. No new invocation or telemetry retrieval performed."
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

## Prerequisites / registration / consent

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

## Deployment checklist

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

<details>
<summary>Real logged exchange — C OAuth custom FastMCP: BLOCKED pending existing-connection consent</summary>

Actual isolated `obs-20261031-c-custom` **agent v2 / Toolbox v3**, using the
existing OAuth connection, audience and delegated-only FastMCP server unchanged.
APIM request `e655a810-a569-4103-a831-e8ae0bda91f8`; POST
`2026-10-31T21:10:59.3376409Z`, response `2026-10-31T21:11:00.0846683Z`.
Wrapper HTTP **200**, MCP **-32006 / CONSENT_REQUIRED**; the hosted response
was **incomplete**, not successful.
Caller context was present; only hash
`mKrIBlHocOMv/SMjeOXrB0XdUJ7qkPPLsXAgh9BA4UQ=` was exported.

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1`.
Exact captured request, with baggage redacted:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-b251bf4d699666940e36dfed6368f0ed-7915c5a6cf3f4066-01","baggage":"<baggage-redacted>"}}}
```

Exact captured response, with the opaque consent URL redacted:

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

Configured destination remains
`https://abc-custom-mcp-e8383e4d.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp`.
The requested experiment was `523a09b5-d7a1-4923-b21d-1dab8f5c4a82`.
**No validated delegated query/result was observed for it**; neither old console
events nor `/healthz` are evidence for this run.
The platform returned an actual `oauth_consent_request`. Its opaque link/session
state is excluded from exported/public evidence.

An initial `store=false` attempt returned
`OAuth consent continuation requires store=true.` The subsequent real
`store=true` attempts reached the consent requirement on both SDK versions;
only nonsensitive demo prompts were stored. No consent action was performed,
and **no OAuth connection, client secret or C authorization policy was changed**.
Completing authorized user/admin consent is an external prerequisite, not an
excuse to replace `OAuth2` with application identity or a manual OBO workaround.

```powershell
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario c-custom --action replay
python .\replay_observability.py --config $configPath --custom-config $customPath --scenario c-custom --action collect
python .\collect_mcp_exchanges.py --custom-config $customPath
```

Safe evidence: `evidence\observability-c-custom.json`,
`evidence\observability-c-custom-apim.json`; the earlier real consent attempt is
retained in `evidence\observability-c-custom-consent-stable.json`.

</details>


### Hosted responses and downstream log evidence

These snapshots are persisted hosted service responses, not runtime console logs.
Runtime console logs were not captured for these invocations.

<details>
<summary>Hosted service snapshot — c-custom</summary>

```json
{
  "source": "evidence/observability-c-custom.json#agentResponse",
  "responseId": "caresp_0e598557b0fd826500eyTu4cSImPK6LmQUAFaFfxlrEfcszgjG",
  "status": "incomplete",
  "error": null,
  "events": [
    {
      "type": "oauth_consent_request"
    }
  ],
  "runtimeConsoleLog": "NOT_CAPTURED",
  "limitation": "Hosted service response snapshot; not a runtime console log. No new invocation or telemetry retrieval performed."
}
```

</details>

---

# Compare results and troubleshoot

## Record one selected track

### Six-path evidence matrix (historical optional upstream APIM run)

The agent code, Toolbox/connection configuration and service/backend contract are
shown in each corresponding A/B/C section above. The six **Real logged exchange**
foldables contain the correlated APIM request/response bodies and timestamps.
Configuration is not proof that a downstream request occurred.

| Path | Agent → Toolbox identity | Backend contract | APIM result | Hosted snapshot | Downstream MCP log |
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

Snapshots in the corresponding scenario are extracted from the persisted hosted service responses, not
runtime console logs. Runtime console logs were **NOT_CAPTURED** for these six
selected invocations. No fresh invocation or Azure telemetry retrieval was
performed for these excerpts; missing logs are not evidence of no execution.
Safe source responses and the application MCP events are retained in
[`evidence/observability-real-exchanges.json`](evidence/observability-real-exchanges.json)
and [`evidence/observability-mcp-exchanges.json`](evidence/observability-mcp-exchanges.json).
Response IDs bind each snapshot to its scenario source; the source run records
also bind agent/version, experiment ID, timestamps and APIM correlation.


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
python .\compile_observability_evidence.py
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
  has new IDs/timestamps: re-check and update historical workshop excerpts rather
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
