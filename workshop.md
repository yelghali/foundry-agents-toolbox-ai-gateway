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

Agent `obs-20261031-a-native` v2; Toolbox v2. UTC `2026-11-01T12:27:16.786462+00:00` → `2026-11-01T12:27:29.663493+00:00`. Experiment `3b65cb79-3fa3-4d25-9586-c15160702a09`.

**Identity-hop lesson (observations versus configuration)**

Control-plane source: `Azure agent control-plane identity and configured project`; observed UTC `2026-11-01T12:30:29.080398+00:00`. Configured agent instance principal `e50d19b6-0a5e-4689-b0d8-d2544f821c86`; project managed identity `42756227-4b4a-4a69-ab63-43c7f3e2b9fe`. Configuration alone is not token evidence.

| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |

|---|---|---|---|

| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance does not upgrade this capture to JWT validation evidence. |

| Agent → APIM → Toolbox | `e50d19b6-0a5e-4689-b0d8-d2544f821c86` | `https://ai.azure.com` | Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. APIM performs no token exchange. |

| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** token audience | Configured: Project managed identity; Search audience. No downstream JWT capture; do not substitute configured claims. |

Selected caller JWT header/claims (decoded-only):


```json
{
  "boundary": "selected Azure CLI credential -> hosted agent endpoint",
  "validation": "DECODED_ONLY_NOT_VALIDATED",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": "https://ai.azure.com",
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "scp": "user_impersonation",
    "idtyp": "user",
    "ver": "1.0",
    "exp": 1793540492,
    "iat": 1793535740
  }
}
```


Selected platform JWT header/claims (APIM-validated):


```json
{
  "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
  "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": [
      "https://ai.azure.com"
    ],
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "appid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "idtyp": "app",
    "ver": "1.0",
    "exp": "1793539642",
    "iat": "1793535742"
  }
}
```


Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` means absent from this observation, not an authorization failure. RBAC/application authorization need not appear as a `roles` claim.

**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, including track A; it is neither the initiating human nor A's project managed identity.

Search MCP returned the exact access marker below, but its backend JWT and internal Search queries are **NOT_OBSERVED**. Project MI/Search audience are configured, not decoded or MCP-validated token claims in this capture.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call retrieve_kb_a exactly once with arguments {"query": "Find the normal access record in cohort A"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ`; status **completed**.

Actual hosted answer (model text; verify against the tool evidence below):


```text
The normal access record for cohort A is **COHORT_A_ONLY_D900EADA82**.
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/call`; request `2bc7f489-e5b8-42dc-8c2f-c772235527e6`; backend HTTP **200**.

UTC request `2026-11-01T12:27:26.8259628Z`; response `2026-11-01T12:27:29.6123617Z`.

Actual generated tool `observed___knowledge_base_retrieve` arguments:


```json
{
  "queries": [
    "Find the normal access record in cohort A"
  ]
}
```


Actual MCP response text (exact captured content; full reference metadata below):


```text
The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.
```



```text
{"kind":"reference","ref_id":0,"uri":"mcp://searchindex/normal","mimeType":"application/json","sourceData":{"id":"normal","title":"Cohort A access record","content":"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim."}}
```


**3. Downstream MCP/runtime logs: what was actually observed**

Native Search MCP response is observed through APIM. Search's internal query/fan-out and service-owned console logs are **NOT_OBSERVED**; no internal query is reconstructed.

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T12:32:41.457822+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T12:27:26.778557797+00:00`.


```text
2026-11-01 12:27:26,778 INFO agent_framework: Function name: observed___knowledge_base_retrieve
```


UTC `2026-11-01T12:27:29.594289879+00:00`.


```text
2026-11-01 12:27:29,594 INFO agent_framework: Function observed___knowledge_base_retrieve succeeded.
```


<details>

<summary>Real logged exchange — a-native: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1`. Configured downstream target: `https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview` (configuration is not execution evidence).

Caller-context SHA-256: `sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=`.

Exact captured request (only sensitive baggage redacted):


```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-6d320155e104179f08bbdf8d685a8dfd-ed7f05be3bbbbc38-01","baggage":"<baggage-redacted>","generateCitations":true,"KnowledgeSourceMetadata":[{"name":"ks-a","type":"searchIndex"}],"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"name":"observed___knowledge_base_retrieve","arguments":{"queries":["Find the normal access record in cohort A"]}},"jsonrpc":"2.0","id":3}
```


Exact captured response:


```json
{"jsonrpc":"2.0","id":3,"result":{"_meta":{"agenticReasoningTokens":28,"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"content":[{"type":"text","text":"The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.","_meta":{"x-request-id":"9814ac59-6827-4613-8599-26065ea2f8bd"}},{"type":"text","text":"{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}","_meta":{"x-request-id":"9814ac59-6827-4613-8599-26065ea2f8bd","title":"Cohort A access record","preserveExactValue":false}}],"structuredContent":null}}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "dcf55ac7-e36c-45ef-8d05-543345a6d90d",
    "callerContextPresent": "True",
    "callerContextHash": "sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "appid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539642",
        "iat": "1793535742"
      },
      "tokenSha256": "57e7b33810040f5b45d0bc1fb42363220e1d93050c971c435177b69df4b1324d",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:22.635771Z",
    "requestBody": "{\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"sampling\":{}},\"clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"}},\"jsonrpc\":\"2.0\",\"id\":0}",
    "responseTimestamp": "2026-11-01T12:27:22.8412355Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":0,\"result\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"tools\":{},\"tasks\":{\"list\":{},\"cancel\":{},\"requests\":{\"tools\":{\"call\":{}}}},\"resources\":{\"listChanged\":false,\"subscribe\":false},\"extensions\":{\"io.modelcontextprotocol/skills\":{}}},\"serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "ec5d2522-ac6d-4c55-be95-e219dfbbad1a",
    "callerContextPresent": "True",
    "callerContextHash": "sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "appid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539642",
        "iat": "1793535742"
      },
      "tokenSha256": "57e7b33810040f5b45d0bc1fb42363220e1d93050c971c435177b69df4b1324d",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:22.8548061Z",
    "requestBody": "{\"method\":\"notifications/initialized\",\"jsonrpc\":\"2.0\"}",
    "responseTimestamp": "2026-11-01T12:27:22.8795377Z",
    "responseBody": "<empty-body>",
    "backendStatus": 204
  },
  {
    "apimRequestId": "55bde9ce-d3e4-4ee5-8a73-6031542c6a54",
    "callerContextPresent": "True",
    "callerContextHash": "sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "appid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539642",
        "iat": "1793535742"
      },
      "tokenSha256": "57e7b33810040f5b45d0bc1fb42363220e1d93050c971c435177b69df4b1324d",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:23.9615653Z",
    "requestBody": "{\"method\":\"ping\",\"jsonrpc\":\"2.0\",\"id\":1}",
    "responseTimestamp": "2026-11-01T12:27:24.0033439Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "82a2efa7-7724-4bbb-9aa7-621fb1471b16",
    "callerContextPresent": "True",
    "callerContextHash": "sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "appid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539642",
        "iat": "1793535742"
      },
      "tokenSha256": "57e7b33810040f5b45d0bc1fb42363220e1d93050c971c435177b69df4b1324d",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:24.0344006Z",
    "requestBody": "{\"method\":\"tools/list\",\"jsonrpc\":\"2.0\",\"id\":2}",
    "responseTimestamp": "2026-11-01T12:27:25.1283207Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"tools\":[{\"name\":\"observed___knowledge_base_retrieve\",\"description\":\"Use knowledge_base_retrieve to search for information or documents that must be authoritative and attributable to a source. This knowledge base is always relevant to the user and any organizations they're affiliated with. You may call this tool with ambiguous queries to retrieve relevant context before asking the user for further clarification. If a Knowledge Base Description is provided, use it to understand what content is included/excluded and to scope your retrieval.\\n\\nUse queries for exactly one complete, natural-language user question or request, not keyword searches, fragments, or rewritten search syntax. Copy the user's information need as a full natural-language question or request. Within that question, include VERBATIM every distinctive token from the user: proper nouns, acronyms (CIA, GDPR), multi-word organization or product names, alphanumeric identifiers (QX-9000, v2.1.4, L1997-00-0351), quoted phrases, version strings, exact filter terms (\\\"conference papers only\\\", \\\"non-paywalled\\\"), group/sort/include/exclude directives, and negation/limit directives (\\\"exclude contractors\\\", \\\"exclude news coverage\\\", \\\"no more than 10\\\", \\\"only include public companies\\\"). Ranges, dates, and numeric thresholds also stay as written. Query in the user's language; do not translate exact terms or quoted phrases. Preserve version strings and multi-word expressions such as tax deferred and official records as written. For temporal, as-of, date range, fiscal year, quarter, and recency constraints, preserve the exact time constraint in the query. The retrieval backend performs expansion. Do not split values of one unresolved constraint into parallel calls. Reserve parallel calls for independent information needs.\\n\\nExamples:\\n\\n\\t// User Query: Which vendor owned Project Helios between 2021 and 2024?\\n\\targuments: {\\\"queries\\\": [\\\"Which vendor owned Project Helios between 2021 and 2024?\\\"]}\\n\\n\\t// User Query: Find the QX-9000 price sheet; it may be called a rate card, quote sheet, or SKU list.\\n\\targuments: {\\\"queries\\\": [\\\"Find the QX-9000 price sheet; it may be called a rate card, quote sheet, or SKU list.\\\"]}\\n\\n\\t// User Query: Find official records about \\\"rate card\\\" changes, include public companies only, and exclude forum posts.\\n\\targuments: {\\\"queries\\\": [\\\"Find official records about \\\\\\\"rate card\\\\\\\" changes, include public companies only, and exclude forum posts.\\\"]}\\nKnowledge Base Description - Foundry IQ Toolbox RBAC live-test knowledge base.\\r\\n\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"queries\":{\"description\":\"Use queries for exactly one complete, natural-language user question or request (max 400 characters; ideally under 70 words), not keyword searches, fragments, or rewritten search syntax. Copy the user's information need as a full question/request using the user's own words and language, preserving entities, references, identifiers, ranges, aliases, filters, exact terms, quoted phrases, grouping directives, comparison directives, version strings, and multi-word expressions without translating them.\\n\\nAlways return a JSON array of strings, even when issuing a single query. Example: {\\\"queries\\\": [\\\"What was Contoso's fiscal year 2024 revenue?\\\"]}.\",\"type\":\"array\",\"items\":{\"type\":\"string\",\"maxLength\":400},\"minItems\":1,\"maxItems\":1}},\"required\":[\"queries\"],\"additionalProperties\":false,\"$schema\":\"https://json-schema.org/draft/2020-12/schema\"},\"_meta\":{\"generateCitations\":true,\"KnowledgeSourceMetadata\":[{\"name\":\"ks-a\",\"type\":\"searchIndex\"}],\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"retrieve_kb_a\",\"server_label\":\"observed\",\"server_url\":\"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary\",\"original_type\":\"mcp\"}},\"execution\":{\"taskSupport\":\"optional\"}}]}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "2bc7f489-e5b8-42dc-8c2f-c772235527e6",
    "callerContextPresent": "True",
    "callerContextHash": "sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=",
    "observedPlatformPrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "appid": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539642",
        "iat": "1793535742"
      },
      "tokenSha256": "57e7b33810040f5b45d0bc1fb42363220e1d93050c971c435177b69df4b1324d",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:26.8259628Z",
    "requestBody": "{\"method\":\"tools/call\",\"params\":{\"_meta\":{\"traceparent\":\"00-6d320155e104179f08bbdf8d685a8dfd-ed7f05be3bbbbc38-01\",\"baggage\":\"<baggage-redacted>\",\"generateCitations\":true,\"KnowledgeSourceMetadata\":[{\"name\":\"ks-a\",\"type\":\"searchIndex\"}],\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"retrieve_kb_a\",\"server_label\":\"observed\",\"server_url\":\"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary\",\"original_type\":\"mcp\"}},\"name\":\"observed___knowledge_base_retrieve\",\"arguments\":{\"queries\":[\"Find the normal access record in cohort A\"]}},\"jsonrpc\":\"2.0\",\"id\":3}",
    "responseTimestamp": "2026-11-01T12:27:29.6123617Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":3,\"result\":{\"_meta\":{\"agenticReasoningTokens\":28,\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"retrieve_kb_a\",\"server_label\":\"observed\",\"server_url\":\"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary\",\"original_type\":\"mcp\"}},\"content\":[{\"type\":\"text\",\"text\":\"The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.\",\"_meta\":{\"x-request-id\":\"9814ac59-6827-4613-8599-26065ea2f8bd\"}},{\"type\":\"text\",\"text\":\"{\\\"kind\\\":\\\"reference\\\",\\\"ref_id\\\":0,\\\"uri\\\":\\\"mcp://searchindex/normal\\\",\\\"mimeType\\\":\\\"application/json\\\",\\\"sourceData\\\":{\\\"id\\\":\\\"normal\\\",\\\"title\\\":\\\"Cohort A access record\\\",\\\"content\\\":\\\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\\\"}}\",\"_meta\":{\"x-request-id\":\"9814ac59-6827-4613-8599-26065ea2f8bd\",\"title\":\"Cohort A access record\",\"preserveExactValue\":false}}],\"structuredContent\":null}}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
  "object": "response",
  "output": [
    {
      "type": "function_call",
      "id": "fc_080649b5ca93875d00g5uBK1P2mfampsnwxTvlcAe7G8V80g0C",
      "call_id": "call_2EMQ6MvZ3SzkqLQ7Fc1Z0RbU",
      "name": "observed___knowledge_base_retrieve",
      "arguments": "{\"queries\":[\"Find the normal access record in cohort A\"]}",
      "status": "completed",
      "response_id": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
      "agent_reference": null
    },
    {
      "type": "function_call_output",
      "id": "fco_080649b5ca93875d00neC5H5UQg3h0xIFXPyIHN1sxdw5nyRQi",
      "call_id": "call_2EMQ6MvZ3SzkqLQ7Fc1Z0RbU",
      "output": "The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.\n{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}",
      "status": "completed",
      "response_id": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
      "agent_reference": null
    },
    {
      "type": "message",
      "id": "msg_080649b5ca93875d00ANNy0O7QV9CAx7giwj5w8RixU5XTHZYp",
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
      "response_id": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
      "agent_reference": null
    }
  ],
  "created_at": 1793536041,
  "parallel_tool_calls": false,
  "status": "completed",
  "completed_at": 1793536050,
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
  "response_id": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
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
  "experimentId": "3b65cb79-3fa3-4d25-9586-c15160702a09",
  "responseId": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
  "invocationStartedAt": "2026-11-01T12:27:16.786462+00:00",
  "invocationCompletedAt": "2026-11-01T12:27:29.663493+00:00",
  "queriedAt": "2026-11-01T12:32:41.457822+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:16.854998602+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:16.860661155+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.288551181+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,288 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.435438662+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,435 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,468 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.469311572+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.472241960+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,472 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.472413345+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,472 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.472869185+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,472 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.472966427+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,472 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.541366221+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,541 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.542139202+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,542 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.542376893+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,542 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.542448135+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,542 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.543872474+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,542 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.544382950+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 12:27:17 +0000] [35] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.544403751+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,544 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.708188706+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,707 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 7386cc7cba2a2b9575b3f7709cf93df2)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.709224065+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,709 INFO azure.ai.agentserver: 192.168.0.1:52926 \"GET /readiness 1.1\" 200 20 1334\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:17.709473559+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:17,709 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 1.0ms (trace-id: 7386cc7cba2a2b9575b3f7709cf93df2)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.924692560+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,924 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 6d320155e104179f08bbdf8d685a8dfd, x-ms-client-request-id: 8397e88a-4a50-491e-b7df-562794341b52, trace-id: 6d320155e104179f08bbdf8d685a8dfd)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.926866085+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,926 INFO azure.ai.agentserver: Creating response caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.927686691+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,927 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.305938714+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,305 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.810351776+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,810 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.817417394+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,811 INFO mcp.client.streamable_http: Negotiated protocol version: 2025-11-25"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.817417394+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,815 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.817417394+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,815 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.817417394+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,816 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.848403028+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,848 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 204 No Content\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.849287419+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,849 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.849459493+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,849 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.849564876+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,849 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.990791569+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,990 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.995582787+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,995 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.995785931+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,995 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.995894613+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,995 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.098588848+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,098 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.218811988+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,218 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.219090259+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,219 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.219197431+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,219 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.300805333+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,300 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.778557797+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,778 INFO agent_framework: Function name: observed___knowledge_base_retrieve"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.783904192+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,783 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.784187534+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,784 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.784283410+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,784 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.299307708+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,299 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.300580265+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,300 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.581298583+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,581 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:29.588568810+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:29,588 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:29.594289879+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:29,594 INFO agent_framework: Function observed___knowledge_base_retrieve succeeded."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:29.595383244+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:29,594 INFO agent_framework: Function duration: 2.815300s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.352495870+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,352 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.590677128+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,590 INFO azure.ai.agentserver: Response caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ completed: status=completed output_count=3"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.591370896+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,591 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.592292506+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,592 INFO azure.ai.agentserver: 192.168.0.1:52926 \"POST /responses 1.1\" 200 1997 8668314\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.592541572+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,592 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 8666.7ms (x-request-id: 6d320155e104179f08bbdf8d685a8dfd, x-ms-client-request-id: 8397e88a-4a50-491e-b7df-562794341b52, trace-id: 6d320155e104179f08bbdf8d685a8dfd)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.592699209+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,592 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.598146920+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,597 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.598946256+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,598 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:30.599036396+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:30,599 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential\n"
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
  "responseId": "caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___knowledge_base_retrieve",
      "call_id": "call_2EMQ6MvZ3SzkqLQ7Fc1Z0RbU",
      "arguments": "{\"queries\":[\"Find the normal access record in cohort A\"]}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_2EMQ6MvZ3SzkqLQ7Fc1Z0RbU",
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

Agent `obs-20261031-a-custom` v1; Toolbox v1. UTC `2026-11-01T12:27:45.261444+00:00` → `2026-11-01T12:27:56.744487+00:00`. Experiment `f43426d5-e764-475f-a405-81da227365b3`.

**Identity-hop lesson (observations versus configuration)**

Control-plane source: `Azure agent control-plane identity and configured project`; observed UTC `2026-11-01T12:30:33.207963+00:00`. Configured agent instance principal `e2284463-607a-4080-b430-3fc63c778516`; project managed identity `42756227-4b4a-4a69-ab63-43c7f3e2b9fe`. Configuration alone is not token evidence.

| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |

|---|---|---|---|

| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance does not upgrade this capture to JWT validation evidence. |

| Agent → APIM → Toolbox | `e2284463-607a-4080-b430-3fc63c778516` | `https://ai.azure.com` | Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. APIM performs no token exchange. |

| Toolbox → MCP | `42756227-4b4a-4a69-ab63-43c7f3e2b9fe` | `c0135af3-d0d3-410f-a1ce-8f2470f5dd93` | **Validated at MCP** (signature, issuer, audience, allowed principal); actual query/result event. |

Selected caller JWT header/claims (decoded-only):


```json
{
  "boundary": "selected Azure CLI credential -> hosted agent endpoint",
  "validation": "DECODED_ONLY_NOT_VALIDATED",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": "https://ai.azure.com",
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "scp": "user_impersonation",
    "idtyp": "user",
    "ver": "1.0",
    "exp": 1793539972,
    "iat": 1793535768
  }
}
```


Selected platform JWT header/claims (APIM-validated):


```json
{
  "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
  "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": [
      "https://ai.azure.com"
    ],
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "e2284463-607a-4080-b430-3fc63c778516",
    "appid": "e2284463-607a-4080-b430-3fc63c778516",
    "idtyp": "app",
    "ver": "1.0",
    "exp": "1793539670",
    "iat": "1793535770"
  }
}
```


Selected downstream JWT header/claims (MCP-validated):


```json
{
  "boundary": "application MCP signature/issuer/audience/principal validation",
  "validation": "VALIDATED_AT_MCP_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
    "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
    "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
    "ver": "2.0",
    "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
    "exp": 1793566559,
    "iat": 1793479859
  }
}
```


Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` means absent from this observation, not an authorization failure. RBAC/application authorization need not appear as a `roles` claim.

**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, including track A; it is neither the initiating human nor A's project managed identity.

This capture proves an audience/principal transition: the agent's app token for `https://ai.azure.com` reaches APIM/Toolbox, while the downstream MCP validates the project managed identity for the custom API audience. Project MI is used **downstream in A custom**, not on agent → Toolbox. This is platform-managed downstream token acquisition; no internal token-endpoint grant was traced, so do not call it a captured JWT-bearer OBO exchange.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call identity_probe exactly once with arguments {"experiment_id": "f43426d5-e764-475f-a405-81da227365b3"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7`; status **completed**.

Actual hosted answer (model text; verify against the tool evidence below):


````text
```json
{
  "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
  "experiment_id": "f43426d5-e764-475f-a405-81da227365b3",
  "claims": {
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
    "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
    "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
    "ver": "2.0",
    "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
    "exp": 1793566559,
    "iat": 1793479859
  },
  "tokenObservation": {
    "boundary": "application MCP signature/issuer/audience/principal validation",
    "validation": "VALIDATED_AT_MCP_BOUNDARY",
    "header": {
      "alg": "RS256",
      "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
    },
    "claims": {
      "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
      "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
      "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
      "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
      "ver": "2.0",
      "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
      "exp": 1793566559,
      "iat": 1793479859
    },
    "tokenSha256": "a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394"
  }
}
```
````


**2. APIM → Toolbox: observed MCP request/response**

`tools/call`; request `f6b603a9-d6aa-4c9c-b1a0-3c78958e0f9a`; backend HTTP **200**.

UTC request `2026-11-01T12:27:52.3486869Z`; response `2026-11-01T12:27:52.538312Z`.

Actual generated tool `observed___identity_probe` arguments:


```json
{
  "experiment_id": "f43426d5-e764-475f-a405-81da227365b3"
}
```


Actual MCP result:


```json
{
  "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
  "experiment_id": "f43426d5-e764-475f-a405-81da227365b3",
  "claims": {
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
    "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
    "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
    "ver": "2.0",
    "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
    "exp": 1793566559,
    "iat": 1793479859
  },
  "tokenObservation": {
    "boundary": "application MCP signature/issuer/audience/principal validation",
    "validation": "VALIDATED_AT_MCP_BOUNDARY",
    "header": {
      "alg": "RS256",
      "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
    },
    "claims": {
      "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
      "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
      "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
      "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
      "ver": "2.0",
      "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
      "exp": 1793566559,
      "iat": 1793479859
    },
    "tokenSha256": "a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394"
  }
}
```


**3. Downstream MCP/runtime logs: what was actually observed**

Custom MCP console `tools/call` query/result is correlated by the experiment UUID; its returned result equals the APIM result.


```json
{
  "azureTimestamp": "2026-11-01T12:27:52.5269472+00:00",
  "event": "validated_mcp_exchange",
  "timestamp": "2026-11-01T12:27:52.526770+00:00",
  "method": "tools/call",
  "tool": "identity_probe",
  "query": {
    "experiment_id": "f43426d5-e764-475f-a405-81da227365b3"
  },
  "result": {
    "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
    "experiment_id": "f43426d5-e764-475f-a405-81da227365b3",
    "claims": {
      "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
      "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
      "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
      "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
      "ver": "2.0",
      "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
      "exp": 1793566559,
      "iat": 1793479859
    },
    "tokenObservation": {
      "boundary": "application MCP signature/issuer/audience/principal validation",
      "validation": "VALIDATED_AT_MCP_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
        "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
        "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
        "ver": "2.0",
        "azp": "b8f21615-3829-4bb9-9a18-b878b0c80e06",
        "exp": 1793566559,
        "iat": 1793479859
      },
      "tokenSha256": "a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394"
    }
  }
}
```


Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T12:33:20.964059+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T12:27:52.308447095+00:00`.


```text
2026-11-01 12:27:52,308 INFO agent_framework: Function name: observed___identity_probe
```


UTC `2026-11-01T12:27:52.514028510+00:00`.


```text
2026-11-01 12:27:52,513 INFO agent_framework: Function observed___identity_probe succeeded.
```


<details>

<summary>Real logged exchange — a-custom: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1`. Configured downstream target: `https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` (configuration is not execution evidence).

Caller-context SHA-256: `7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=`.

Exact captured request (only sensitive baggage redacted):


```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-be791ba3a8604ebe6418c9a2457392fa-af1c239dccbc50d6-01","baggage":"<baggage-redacted>","tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"name":"observed___identity_probe","arguments":{"experiment_id":"f43426d5-e764-475f-a405-81da227365b3"}},"jsonrpc":"2.0","id":3}
```


Exact captured response:


```json
{"jsonrpc":"2.0","id":3,"result":{"_meta":{"tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"content":[{"type":"text","text":"{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"f43426d5-e764-475f-a405-81da227365b3\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\",\"azp\":\"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\"exp\":1793566559,\"iat\":1793479859},\"tokenObservation\":{\"boundary\":\"application MCP signature/issuer/audience/principal validation\",\"validation\":\"VALIDATED_AT_MCP_BOUNDARY\",\"header\":{\"alg\":\"RS256\",\"kid\":\"ryBx-65jNoxH4FQH_6zarNjaNf4\"},\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\",\"azp\":\"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\"exp\":1793566559,\"iat\":1793479859},\"tokenSha256\":\"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\"}}"}],"isError":false,"structuredContent":{"marker":"CUSTOM_MCP_APPLICATION_VALIDATED","experiment_id":"f43426d5-e764-475f-a405-81da227365b3","claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0","azp":"b8f21615-3829-4bb9-9a18-b878b0c80e06","exp":1793566559,"iat":1793479859},"tokenObservation":{"boundary":"application MCP signature/issuer/audience/principal validation","validation":"VALIDATED_AT_MCP_BOUNDARY","header":{"alg":"RS256","kid":"ryBx-65jNoxH4FQH_6zarNjaNf4"},"claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0","azp":"b8f21615-3829-4bb9-9a18-b878b0c80e06","exp":1793566559,"iat":1793479859},"tokenSha256":"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394"}}}}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "d19a4589-191a-4aec-b851-cb253b45a99d",
    "callerContextPresent": "True",
    "callerContextHash": "7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e2284463-607a-4080-b430-3fc63c778516",
        "appid": "e2284463-607a-4080-b430-3fc63c778516",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539670",
        "iat": "1793535770"
      },
      "tokenSha256": "58d356c2dac0c815955b4295a12fff2892359552eae05f28cc5dbb4cd6245df1",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:50.5732344Z",
    "requestBody": "{\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"sampling\":{}},\"clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"}},\"jsonrpc\":\"2.0\",\"id\":0}",
    "responseTimestamp": "2026-11-01T12:27:50.7715158Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":0,\"result\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"tools\":{},\"tasks\":{\"list\":{},\"cancel\":{},\"requests\":{\"tools\":{\"call\":{}}}},\"resources\":{\"listChanged\":false,\"subscribe\":false},\"extensions\":{\"io.modelcontextprotocol/skills\":{}}},\"serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "678e8f2e-0469-42e7-813e-deb57287addc",
    "callerContextPresent": "True",
    "callerContextHash": "7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e2284463-607a-4080-b430-3fc63c778516",
        "appid": "e2284463-607a-4080-b430-3fc63c778516",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539670",
        "iat": "1793535770"
      },
      "tokenSha256": "58d356c2dac0c815955b4295a12fff2892359552eae05f28cc5dbb4cd6245df1",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:50.789446Z",
    "requestBody": "{\"method\":\"notifications/initialized\",\"jsonrpc\":\"2.0\"}",
    "responseTimestamp": "2026-11-01T12:27:50.8196282Z",
    "responseBody": "<empty-body>",
    "backendStatus": 204
  },
  {
    "apimRequestId": "d82a1c49-0bfb-4683-ac39-9d8d36d1c200",
    "callerContextPresent": "True",
    "callerContextHash": "7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e2284463-607a-4080-b430-3fc63c778516",
        "appid": "e2284463-607a-4080-b430-3fc63c778516",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539670",
        "iat": "1793535770"
      },
      "tokenSha256": "58d356c2dac0c815955b4295a12fff2892359552eae05f28cc5dbb4cd6245df1",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:50.8600793Z",
    "requestBody": "{\"method\":\"ping\",\"jsonrpc\":\"2.0\",\"id\":1}",
    "responseTimestamp": "2026-11-01T12:27:50.9131835Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "cdd6d312-0547-47a2-b064-2d558ae6ae20",
    "callerContextPresent": "True",
    "callerContextHash": "7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e2284463-607a-4080-b430-3fc63c778516",
        "appid": "e2284463-607a-4080-b430-3fc63c778516",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539670",
        "iat": "1793535770"
      },
      "tokenSha256": "58d356c2dac0c815955b4295a12fff2892359552eae05f28cc5dbb4cd6245df1",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:50.9235648Z",
    "requestBody": "{\"method\":\"tools/list\",\"jsonrpc\":\"2.0\",\"id\":2}",
    "responseTimestamp": "2026-11-01T12:27:51.1727957Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"tools\":[{\"name\":\"observed___identity_probe\",\"description\":\"Return validated application identifiers for a nonsensitive experiment UUID.\",\"inputSchema\":{\"properties\":{\"experiment_id\":{\"type\":\"string\"}},\"required\":[\"experiment_id\"],\"type\":\"object\",\"$schema\":\"https://json-schema.org/draft/2020-12/schema\"},\"outputSchema\":{\"additionalProperties\":true,\"type\":\"object\",\"$schema\":\"https://json-schema.org/draft/2020-12/schema\"},\"_meta\":{\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"identity_probe\",\"server_label\":\"observed\",\"server_url\":\"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data\",\"original_type\":\"mcp\"}}}]}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "f6b603a9-d6aa-4c9c-b1a0-3c78958e0f9a",
    "callerContextPresent": "True",
    "callerContextHash": "7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=",
    "observedPlatformPrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "e2284463-607a-4080-b430-3fc63c778516",
        "appid": "e2284463-607a-4080-b430-3fc63c778516",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539670",
        "iat": "1793535770"
      },
      "tokenSha256": "58d356c2dac0c815955b4295a12fff2892359552eae05f28cc5dbb4cd6245df1",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:52.3486869Z",
    "requestBody": "{\"method\":\"tools/call\",\"params\":{\"_meta\":{\"traceparent\":\"00-be791ba3a8604ebe6418c9a2457392fa-af1c239dccbc50d6-01\",\"baggage\":\"<baggage-redacted>\",\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"identity_probe\",\"server_label\":\"observed\",\"server_url\":\"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data\",\"original_type\":\"mcp\"}},\"name\":\"observed___identity_probe\",\"arguments\":{\"experiment_id\":\"f43426d5-e764-475f-a405-81da227365b3\"}},\"jsonrpc\":\"2.0\",\"id\":3}",
    "responseTimestamp": "2026-11-01T12:27:52.538312Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":3,\"result\":{\"_meta\":{\"tool_configuration\":{\"type\":\"mcp\",\"name\":\"identity_probe\",\"server_label\":\"observed\",\"server_url\":\"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp\",\"require_approval\":\"never\",\"project_connection_id\":\"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data\",\"original_type\":\"mcp\"}},\"content\":[{\"type\":\"text\",\"text\":\"{\\\"marker\\\":\\\"CUSTOM_MCP_APPLICATION_VALIDATED\\\",\\\"experiment_id\\\":\\\"f43426d5-e764-475f-a405-81da227365b3\\\",\\\"claims\\\":{\\\"tid\\\":\\\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\\\",\\\"oid\\\":\\\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\\\",\\\"aud\\\":\\\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\\\",\\\"iss\\\":\\\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\\\",\\\"ver\\\":\\\"2.0\\\",\\\"azp\\\":\\\"b8f21615-3829-4bb9-9a18-b878b0c80e06\\\",\\\"exp\\\":1793566559,\\\"iat\\\":1793479859},\\\"tokenObservation\\\":{\\\"boundary\\\":\\\"application MCP signature/issuer/audience/principal validation\\\",\\\"validation\\\":\\\"VALIDATED_AT_MCP_BOUNDARY\\\",\\\"header\\\":{\\\"alg\\\":\\\"RS256\\\",\\\"kid\\\":\\\"ryBx-65jNoxH4FQH_6zarNjaNf4\\\"},\\\"claims\\\":{\\\"tid\\\":\\\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\\\",\\\"oid\\\":\\\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\\\",\\\"aud\\\":\\\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\\\",\\\"iss\\\":\\\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\\\",\\\"ver\\\":\\\"2.0\\\",\\\"azp\\\":\\\"b8f21615-3829-4bb9-9a18-b878b0c80e06\\\",\\\"exp\\\":1793566559,\\\"iat\\\":1793479859},\\\"tokenSha256\\\":\\\"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\\\"}}\"}],\"isError\":false,\"structuredContent\":{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"f43426d5-e764-475f-a405-81da227365b3\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\",\"azp\":\"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\"exp\":1793566559,\"iat\":1793479859},\"tokenObservation\":{\"boundary\":\"application MCP signature/issuer/audience/principal validation\",\"validation\":\"VALIDATED_AT_MCP_BOUNDARY\",\"header\":{\"alg\":\"RS256\",\"kid\":\"ryBx-65jNoxH4FQH_6zarNjaNf4\"},\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\",\"azp\":\"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\"exp\":1793566559,\"iat\":1793479859},\"tokenSha256\":\"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\"}}}}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


````json
{
  "id": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
  "object": "response",
  "output": [
    {
      "type": "function_call",
      "id": "fc_0ee21261ad95b4c500UNyS5z7pxKTAOimjYUw47ZKllsutxxSY",
      "call_id": "call_lsBxbAnBrwmmcVl6Pw90SLJE",
      "name": "observed___identity_probe",
      "arguments": "{\"experiment_id\":\"f43426d5-e764-475f-a405-81da227365b3\"}",
      "status": "completed",
      "response_id": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
      "agent_reference": null
    },
    {
      "type": "function_call_output",
      "id": "fco_0ee21261ad95b4c500uMwmAFElE8z0bkfrzKRgT5h6T6cdDYzX",
      "call_id": "call_lsBxbAnBrwmmcVl6Pw90SLJE",
      "output": "{\"marker\": \"CUSTOM_MCP_APPLICATION_VALIDATED\", \"experiment_id\": \"f43426d5-e764-475f-a405-81da227365b3\", \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\", \"azp\": \"b8f21615-3829-4bb9-9a18-b878b0c80e06\", \"exp\": 1793566559, \"iat\": 1793479859}, \"tokenObservation\": {\"boundary\": \"application MCP signature/issuer/audience/principal validation\", \"validation\": \"VALIDATED_AT_MCP_BOUNDARY\", \"header\": {\"alg\": \"RS256\", \"kid\": \"ryBx-65jNoxH4FQH_6zarNjaNf4\"}, \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\", \"azp\": \"b8f21615-3829-4bb9-9a18-b878b0c80e06\", \"exp\": 1793566559, \"iat\": 1793479859}, \"tokenSha256\": \"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\"}}",
      "status": "completed",
      "response_id": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
      "agent_reference": null
    },
    {
      "type": "message",
      "id": "msg_0ee21261ad95b4c500BkALQ6KjMv2s4CyjznlAogyyJ1dYk05W",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "```json\n{\n  \"marker\": \"CUSTOM_MCP_APPLICATION_VALIDATED\",\n  \"experiment_id\": \"f43426d5-e764-475f-a405-81da227365b3\",\n  \"claims\": {\n    \"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\n    \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\n    \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\n    \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\n    \"ver\": \"2.0\",\n    \"azp\": \"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\n    \"exp\": 1793566559,\n    \"iat\": 1793479859\n  },\n  \"tokenObservation\": {\n    \"boundary\": \"application MCP signature/issuer/audience/principal validation\",\n    \"validation\": \"VALIDATED_AT_MCP_BOUNDARY\",\n    \"header\": {\n      \"alg\": \"RS256\",\n      \"kid\": \"ryBx-65jNoxH4FQH_6zarNjaNf4\"\n    },\n    \"claims\": {\n      \"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\n      \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\n      \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\n      \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\n      \"ver\": \"2.0\",\n      \"azp\": \"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\n      \"exp\": 1793566559,\n      \"iat\": 1793479859\n    },\n    \"tokenSha256\": \"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\"\n  }\n}\n```",
          "annotations": [],
          "logprobs": []
        }
      ],
      "status": "completed",
      "response_id": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
      "agent_reference": null
    }
  ],
  "created_at": 1793536069,
  "parallel_tool_calls": false,
  "status": "completed",
  "completed_at": 1793536077,
  "usage": {
    "input_tokens": 792,
    "input_tokens_details": {
      "cached_tokens": 0,
      "cache_write_tokens": 0
    },
    "output_tokens": 599,
    "output_tokens_details": {
      "reasoning_tokens": 0
    },
    "total_tokens": 1391
  },
  "response_id": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
  "agent_reference": {
    "type": "agent_reference",
    "name": "obs-20261031-a-custom",
    "version": "1"
  },
  "model": "",
  "agent_session_id": "<redacted>",
  "background": false
}
````


Runtime query result:


```json
{
  "scenario": "a-custom",
  "agent": "obs-20261031-a-custom",
  "version": "1",
  "experimentId": "f43426d5-e764-475f-a405-81da227365b3",
  "responseId": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
  "invocationStartedAt": "2026-11-01T12:27:45.261444+00:00",
  "invocationCompletedAt": "2026-11-01T12:27:56.744487+00:00",
  "queriedAt": "2026-11-01T12:33:20.964059+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.046351234+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.052680767+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.468780058+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,468 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.602252154+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,602 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,636 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.637063942+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.639945772+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,639 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.640116689+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,640 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.640556779+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,640 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.640651297+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,640 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.710616671+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,710 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.711411462+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,711 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.711646629+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,711 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.711715719+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,711 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.712988439+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,711 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.713650327+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 12:27:45 +0000] [44] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:45.713682223+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:45,713 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:46.193514600+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:46,193 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 19d8c94fa67a09f3353bb77adbe228f2)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:46.194457723+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:46,194 INFO azure.ai.agentserver: 192.168.0.1:45138 \"GET /readiness 1.1\" 200 20 1282\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:46.194646868+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:46,194 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.9ms (trace-id: 19d8c94fa67a09f3353bb77adbe228f2)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.903601887+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,903 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: be791ba3a8604ebe6418c9a2457392fa, x-ms-client-request-id: 9abac633-2ca1-4b2d-b963-33892492769a, trace-id: be791ba3a8604ebe6418c9a2457392fa)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.904897675+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,904 INFO azure.ai.agentserver: Creating response caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.905230320+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,905 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.425934418+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,425 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.742960165+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,742 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.745731791+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,745 INFO mcp.client.streamable_http: Negotiated protocol version: 2025-11-25"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.750742098+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,750 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.751540665+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,750 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.751673303+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,751 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.791369997+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,791 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 204 No Content\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.792330467+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,792 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.792472248+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,792 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.792558995+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,792 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.883152640+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,883 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.886412468+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,886 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.886566407+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,886 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.887030546+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,886 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:51.143900663+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:51,143 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:51.266200990+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:51,266 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:51.266463947+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:51,266 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token_info succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:51.266570762+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:51,266 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:51.971986187+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:51,971 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.308447095+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,308 INFO agent_framework: Function name: observed___identity_probe"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.310999924+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,310 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.311188694+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,311 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.311280658+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,311 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.509024490+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,508 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.514028510+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,513 INFO agent_framework: Function observed___identity_probe succeeded."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.515008446+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,514 INFO agent_framework: Function duration: 0.205277s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:53.344328195+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:53,344 INFO httpx2: HTTP Request: POST https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com/api/projects/abc-a/openai/v1/responses \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:57.667866485+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:57,667 INFO azure.ai.agentserver: Response caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7 completed: status=completed output_count=3"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:57.669660305+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:57,668 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:57.669660305+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:57,669 INFO azure.ai.agentserver: 192.168.0.1:45140 \"POST /responses 1.1\" 200 4074 7766692\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:57.669660305+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:57,669 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 7765.0ms (x-request-id: be791ba3a8604ebe6418c9a2457392fa, x-ms-client-request-id: 9abac633-2ca1-4b2d-b963-33892492769a, trace-id: be791ba3a8604ebe6418c9a2457392fa)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:57.669660305+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:57,669 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
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
  "responseId": "caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___identity_probe",
      "call_id": "call_lsBxbAnBrwmmcVl6Pw90SLJE",
      "arguments": "{\"experiment_id\":\"f43426d5-e764-475f-a405-81da227365b3\"}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_lsBxbAnBrwmmcVl6Pw90SLJE",
      "output": "{\"marker\": \"CUSTOM_MCP_APPLICATION_VALIDATED\", \"experiment_id\": \"f43426d5-e764-475f-a405-81da227365b3\", \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\", \"azp\": \"b8f21615-3829-4bb9-9a18-b878b0c80e06\", \"exp\": 1793566559, \"iat\": 1793479859}, \"tokenObservation\": {\"boundary\": \"application MCP signature/issuer/audience/principal validation\", \"validation\": \"VALIDATED_AT_MCP_BOUNDARY\", \"header\": {\"alg\": \"RS256\", \"kid\": \"ryBx-65jNoxH4FQH_6zarNjaNf4\"}, \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"ver\": \"2.0\", \"azp\": \"b8f21615-3829-4bb9-9a18-b878b0c80e06\", \"exp\": 1793566559, \"iat\": 1793479859}, \"tokenSha256\": \"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\"}}",
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

Agent `obs-20261031-b-native` v3; Toolbox v3. UTC `2026-11-01T12:27:21.137372+00:00` → `2026-11-01T12:27:26.396389+00:00`. Experiment `c7f8806d-7c48-4b5f-94a8-87f5e0c44ea8`.

**Identity-hop lesson (observations versus configuration)**

Control-plane source: `Azure agent control-plane identity and configured project`; observed UTC `2026-11-01T12:30:28.922658+00:00`. Configured agent instance principal `1f430487-d7ab-4b08-b99d-4e157099ab53`; project managed identity `a4c50f03-8b79-4946-8b6c-a6071f991eef`. Configuration alone is not token evidence.

| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |

|---|---|---|---|

| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance does not upgrade this capture to JWT validation evidence. |

| Agent → APIM → Toolbox | `1f430487-d7ab-4b08-b99d-4e157099ab53` | `https://ai.azure.com` | Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. APIM performs no token exchange. |

| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** token audience | Configured: Agent identity; Search audience. No downstream JWT capture; do not substitute configured claims. |

Selected caller JWT header/claims (decoded-only):


```json
{
  "boundary": "selected Azure CLI credential -> hosted agent endpoint",
  "validation": "DECODED_ONLY_NOT_VALIDATED",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": "https://ai.azure.com",
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "scp": "user_impersonation",
    "idtyp": "user",
    "ver": "1.0",
    "exp": 1793541117,
    "iat": 1793535744
  }
}
```


Selected platform JWT header/claims (APIM-validated):


```json
{
  "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
  "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": [
      "https://ai.azure.com"
    ],
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "1f430487-d7ab-4b08-b99d-4e157099ab53",
    "appid": "1f430487-d7ab-4b08-b99d-4e157099ab53",
    "idtyp": "app",
    "ver": "1.0",
    "exp": "1793539646",
    "iat": "1793535746"
  }
}
```


Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` means absent from this observation, not an authorization failure. RBAC/application authorization need not appear as a `roles` claim.

**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, including track A; it is neither the initiating human nor A's project managed identity.

The platform app token passes APIM validation, but Toolbox reports missing `AgentInstanceClientId` context. An `oid` matching the configured agent does not prove that Toolbox received all required agent-instance context. No successful downstream agent token/query was observed on this upstream route. Original B direct/native and its downstream Search gateway are distinct routes.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call retrieve_kb_b exactly once with arguments {"query": "Find the normal access record in cohort B"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r`; status **failed**.

Actual hosted error excerpt (full error in secondary capture):


```text
An internal server error occurred.
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `f0c51840-6fd9-477c-aaa7-caa126240bca`; backend HTTP **200**.

UTC request `2026-11-01T12:27:27.0988403Z`; response `2026-11-01T12:27:27.352825Z`.

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
    "traceparent": "00-3b0969ceba94c205102e8d2490c8c368-727aced811966255-01",
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

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T12:32:50.649657+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T12:27:27.338476750+00:00`.


```text
2026-11-01 12:27:27,337 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r, error_type=ToolExecutionException).
```


<details>

<summary>Real logged exchange — b-native: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1`. Configured downstream target: `https://srchabcb7puse24s5tluc.search.windows.net/knowledgebases/kb-b/mcp?api-version=2026-05-01-preview` (configuration is not execution evidence).

Caller-context SHA-256: `TEixmZ4Nl1s3hKvaBXe1KYYMr/8tjfRwnpkRaLv5ikU=`.

Exact captured request (only sensitive baggage redacted):


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-3b0969ceba94c205102e8d2490c8c368-727aced811966255-01","baggage":"<baggage-redacted>"}}}
```


Exact captured response:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32007,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/iq-b-primary'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'iq-b-primary' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\"}}]}"}}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "76c25019-6984-4c5c-b0a7-f371fc2f5af3",
    "callerContextPresent": "True",
    "callerContextHash": "TEixmZ4Nl1s3hKvaBXe1KYYMr/8tjfRwnpkRaLv5ikU=",
    "observedPlatformPrincipalId": "1f430487-d7ab-4b08-b99d-4e157099ab53",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "1f430487-d7ab-4b08-b99d-4e157099ab53",
        "appid": "1f430487-d7ab-4b08-b99d-4e157099ab53",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539646",
        "iat": "1793535746"
      },
      "tokenSha256": "4727c09ffabebd0ad469d60ac70148315deccdd99ba5c1a8e500e35f8c5ca96c",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:26.7373934Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-3b0969ceba94c205102e8d2490c8c368-8200784fec247cc9-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T12:27:26.9251402Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"resultType\":\"complete\",\"supportedVersions\":[\"2025-11-25\",\"2026-07-28\"],\"capabilities\":{\"tools\":{},\"resources\":{},\"extensions\":{\"io.modelcontextprotocol/skills\":{},\"io.modelcontextprotocol/tasks\":{}}},\"_meta\":{\"io.modelcontextprotocol/serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}},\"instructions\":\"This server exposes tools configured in the requested Foundry toolbox. Use tools/list to enumerate available tools and tools/call to invoke them.\",\"ttlMs\":300000,\"cacheScope\":\"private\"}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "f0c51840-6fd9-477c-aaa7-caa126240bca",
    "callerContextPresent": "True",
    "callerContextHash": "TEixmZ4Nl1s3hKvaBXe1KYYMr/8tjfRwnpkRaLv5ikU=",
    "observedPlatformPrincipalId": "1f430487-d7ab-4b08-b99d-4e157099ab53",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "1f430487-d7ab-4b08-b99d-4e157099ab53",
        "appid": "1f430487-d7ab-4b08-b99d-4e157099ab53",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539646",
        "iat": "1793535746"
      },
      "tokenSha256": "4727c09ffabebd0ad469d60ac70148315deccdd99ba5c1a8e500e35f8c5ca96c",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:27.0988403Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-3b0969ceba94c205102e8d2490c8c368-727aced811966255-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T12:27:27.352825Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"error\":{\"code\":-32007,\"message\":\"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"HTTP_400\\\",\\\"message\\\":\\\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/iq-b-primary'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'iq-b-primary' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\\\"}}]}\"}}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r",
  "object": "response",
  "output": [],
  "created_at": 1793536045,
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "parallel_tool_calls": false,
  "status": "failed",
  "response_id": "caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r",
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
  "experimentId": "c7f8806d-7c48-4b5f-94a8-87f5e0c44ea8",
  "responseId": "caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r",
  "invocationStartedAt": "2026-11-01T12:27:21.137372+00:00",
  "invocationCompletedAt": "2026-11-01T12:27:26.396389+00:00",
  "queriedAt": "2026-11-01T12:32:50.649657+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.173934308+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.181677856+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.599721436+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,599 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.735003402+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,734 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,768 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.768901885+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.771787084+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,771 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.771953030+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,771 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.772377613+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,772 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.772471153+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,772 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.937272754+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,937 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.938176482+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,938 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.938431283+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,938 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.938501009+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,938 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.939755060+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,938 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.940265441+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 12:27:21 +0000] [42] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:21.940288628+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:21,940 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.081747647+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,081 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 921b2094f58bef598c99ed544f1078c0)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.082571844+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,082 INFO azure.ai.agentserver: 192.168.0.1:47384 \"GET /readiness 1.1\" 200 20 988\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.082761467+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,082 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.8ms (trace-id: 921b2094f58bef598c99ed544f1078c0)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.698111860+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,697 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 3b0969ceba94c205102e8d2490c8c368, x-ms-client-request-id: 1ce0c194-3c05-4288-99bb-78aed4c41ded, trace-id: 3b0969ceba94c205102e8d2490c8c368)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.699018204+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,698 INFO azure.ai.agentserver: Creating response caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.699331391+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,699 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.700232507+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,700 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:25.700655484+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:25,700 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.352843076+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,352 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.915263992+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,914 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.947840190+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,947 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.950311527+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,948 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:26.950558006+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:26,950 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.334203205+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,334 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.338476750+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,337 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r, error_type=ToolExecutionException)."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.339158171+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,339 INFO azure.ai.agentserver: Response caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r completed: status=failed output_count=0"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.342196035+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,341 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.343028252+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,342 INFO azure.ai.agentserver: 192.168.0.1:47388 \"POST /responses 1.1\" 200 513 1645303\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.343296427+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,343 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 1644.9ms (x-request-id: 3b0969ceba94c205102e8d2490c8c368, x-ms-client-request-id: 1ce0c194-3c05-4288-99bb-78aed4c41ded, trace-id: 3b0969ceba94c205102e8d2490c8c368)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:27.343480450+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:27,343 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
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
  "responseId": "caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r",
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

Agent `obs-20261031-b-custom` v2; Toolbox v2. UTC `2026-11-01T12:27:47.370569+00:00` → `2026-11-01T12:27:53.310103+00:00`. Experiment `f9291499-7021-47d1-b81f-f8bd7a6e6af2`.

**Identity-hop lesson (observations versus configuration)**

Control-plane source: `Azure agent control-plane identity and configured project`; observed UTC `2026-11-01T12:30:33.173298+00:00`. Configured agent instance principal `d6fb1ff2-6587-4169-b279-20103b371ab7`; project managed identity `a4c50f03-8b79-4946-8b6c-a6071f991eef`. Configuration alone is not token evidence.

| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |

|---|---|---|---|

| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance does not upgrade this capture to JWT validation evidence. |

| Agent → APIM → Toolbox | `d6fb1ff2-6587-4169-b279-20103b371ab7` | `https://ai.azure.com` | Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. APIM performs no token exchange. |

| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** token audience | Configured: Agent identity; custom application audience. No downstream JWT capture; do not substitute configured claims. |

Selected caller JWT header/claims (decoded-only):


```json
{
  "boundary": "selected Azure CLI credential -> hosted agent endpoint",
  "validation": "DECODED_ONLY_NOT_VALIDATED",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": "https://ai.azure.com",
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "scp": "user_impersonation",
    "idtyp": "user",
    "ver": "1.0",
    "exp": 1793540182,
    "iat": 1793535771
  }
}
```


Selected platform JWT header/claims (APIM-validated):


```json
{
  "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
  "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": [
      "https://ai.azure.com"
    ],
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "d6fb1ff2-6587-4169-b279-20103b371ab7",
    "appid": "d6fb1ff2-6587-4169-b279-20103b371ab7",
    "idtyp": "app",
    "ver": "1.0",
    "exp": "1793539673",
    "iat": "1793535773"
  }
}
```


Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` means absent from this observation, not an authorization failure. RBAC/application authorization need not appear as a `roles` claim.

**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, including track A; it is neither the initiating human nor A's project managed identity.

The platform app token passes APIM validation, but Toolbox reports missing `AgentInstanceClientId` context. An `oid` matching the configured agent does not prove that Toolbox received all required agent-instance context. No successful downstream agent token/query was observed on this upstream route. Original B direct/native and its downstream Search gateway are distinct routes.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call identity_probe exactly once with arguments {"experiment_id": "f9291499-7021-47d1-b81f-f8bd7a6e6af2"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg`; status **failed**.

Actual hosted error excerpt (full error in secondary capture):


```text
An internal server error occurred.
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `a18e7b60-c912-4cba-8a7d-29b8423fa123`; backend HTTP **200**.

UTC request `2026-11-01T12:27:54.0329453Z`; response `2026-11-01T12:27:54.264263Z`.

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
    "traceparent": "00-826510e64f100d661561e52df6798df9-90910c1c750a647c-01",
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

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T12:33:30.544850+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T12:27:54.241027981+00:00`.


```text
2026-11-01 12:27:54,240 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg, error_type=ToolExecutionException).
```


<details>

<summary>Real logged exchange — b-custom: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1`. Configured downstream target: `https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` (configuration is not execution evidence).

Caller-context SHA-256: `1/Vs/816eT2TQGo/UzJvhgTSirt0zRd3xeUhzQNsgd8=`.

Exact captured request (only sensitive baggage redacted):


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-826510e64f100d661561e52df6798df9-90910c1c750a647c-01","baggage":"<baggage-redacted>"}}}
```


Exact captured response:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32007,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/obs-20261031-b-custom-data'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'obs-20261031-b-custom-data' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\"}}]}"}}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "df5bc0ff-51f5-486c-bb20-f5b310563a4b",
    "callerContextPresent": "True",
    "callerContextHash": "1/Vs/816eT2TQGo/UzJvhgTSirt0zRd3xeUhzQNsgd8=",
    "observedPlatformPrincipalId": "d6fb1ff2-6587-4169-b279-20103b371ab7",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "d6fb1ff2-6587-4169-b279-20103b371ab7",
        "appid": "d6fb1ff2-6587-4169-b279-20103b371ab7",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539673",
        "iat": "1793535773"
      },
      "tokenSha256": "067d5d4c719c3a89513885cb71126c33751f1b8e533159245d18fc2cebb891d0",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:53.7852485Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-826510e64f100d661561e52df6798df9-1a704eee0107ee9f-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T12:27:53.9941511Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"resultType\":\"complete\",\"supportedVersions\":[\"2025-11-25\",\"2026-07-28\"],\"capabilities\":{\"tools\":{},\"resources\":{},\"extensions\":{\"io.modelcontextprotocol/skills\":{},\"io.modelcontextprotocol/tasks\":{}}},\"_meta\":{\"io.modelcontextprotocol/serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}},\"instructions\":\"This server exposes tools configured in the requested Foundry toolbox. Use tools/list to enumerate available tools and tools/call to invoke them.\",\"ttlMs\":300000,\"cacheScope\":\"private\"}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "a18e7b60-c912-4cba-8a7d-29b8423fa123",
    "callerContextPresent": "True",
    "callerContextHash": "1/Vs/816eT2TQGo/UzJvhgTSirt0zRd3xeUhzQNsgd8=",
    "observedPlatformPrincipalId": "d6fb1ff2-6587-4169-b279-20103b371ab7",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "d6fb1ff2-6587-4169-b279-20103b371ab7",
        "appid": "d6fb1ff2-6587-4169-b279-20103b371ab7",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539673",
        "iat": "1793535773"
      },
      "tokenSha256": "067d5d4c719c3a89513885cb71126c33751f1b8e533159245d18fc2cebb891d0",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:54.0329453Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-826510e64f100d661561e52df6798df9-90910c1c750a647c-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T12:27:54.264263Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"error\":{\"code\":-32007,\"message\":\"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"HTTP_400\\\",\\\"message\\\":\\\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/obs-20261031-b-custom-data'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'obs-20261031-b-custom-data' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\\\"}}]}\"}}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg",
  "object": "response",
  "output": [],
  "created_at": 1793536072,
  "error": {
    "code": "server_error",
    "message": "An internal server error occurred."
  },
  "parallel_tool_calls": false,
  "status": "failed",
  "response_id": "caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg",
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
  "experimentId": "f9291499-7021-47d1-b81f-f8bd7a6e6af2",
  "responseId": "caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg",
  "invocationStartedAt": "2026-11-01T12:27:47.370569+00:00",
  "invocationCompletedAt": "2026-11-01T12:27:53.310103+00:00",
  "queriedAt": "2026-11-01T12:33:30.544850+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.205076627+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.213004615+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.619905932+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,619 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.759232890+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,759 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,792 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.793848126+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.796742151+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,796 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.796917500+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,796 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.797397351+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,797 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.797534514+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,797 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.961703386+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,961 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.962621297+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,962 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.962869041+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,962 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.962939726+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,962 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.964328732+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,963 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.964954611+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 12:27:47 +0000] [44] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.964984976+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,964 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.302906543+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,302 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 080158efe8ca6d9942a5bbef488b4aea)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.303895972+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,303 INFO azure.ai.agentserver: 192.168.0.1:40314 \"GET /readiness 1.1\" 200 20 1307\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.304096268+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,304 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.9ms (trace-id: 080158efe8ca6d9942a5bbef488b4aea)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.712409612+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,712 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 826510e64f100d661561e52df6798df9, x-ms-client-request-id: 1e3ec5f4-1caa-4262-bb9c-05cd780875b1, trace-id: 826510e64f100d661561e52df6798df9)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.713784797+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,713 INFO azure.ai.agentserver: Creating response caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.714181261+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,714 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.714786803+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,714 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:52.715259032+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:52,715 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:53.605693369+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:53,605 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:53.969341025+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:53,969 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:53.994664189+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:53,991 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:53.994664189+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:53,991 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:53.994664189+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:53,993 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.235676613+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,235 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.241027981+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,240 ERROR agent_framework_foundry_hosting._responses: Hosted Responses failure (phase=agent initialization, response_id=caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg, error_type=ToolExecutionException)."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.241841480+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,241 INFO azure.ai.agentserver: Response caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg completed: status=failed output_count=0"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.244909999+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,244 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.245818537+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,245 INFO azure.ai.agentserver: 192.168.0.1:40330 \"POST /responses 1.1\" 200 513 1533887\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.246102969+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,246 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 1533.0ms (x-request-id: 826510e64f100d661561e52df6798df9, x-ms-client-request-id: 1e3ec5f4-1caa-4262-bb9c-05cd780875b1, trace-id: 826510e64f100d661561e52df6798df9)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.246277151+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,246 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:54.254793019+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:54,254 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported."
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
  "responseId": "caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg",
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

Agent `obs-20261031-c-native` v2; Toolbox v2. UTC `2026-11-01T12:27:15.187455+00:00` → `2026-11-01T12:27:23.902184+00:00`. Experiment `d791f5ca-24a5-4d8f-ab04-dffc0f08c50e`.

**Identity-hop lesson (observations versus configuration)**

Control-plane source: `Azure agent control-plane identity and configured project`; observed UTC `2026-11-01T12:30:29.187732+00:00`. Configured agent instance principal `8c2d2573-9c63-42cd-86c0-ce807db9edcf`; project managed identity `1a04abde-08e9-4949-b975-b2520119ca1d`. Configuration alone is not token evidence.

| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |

|---|---|---|---|

| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance does not upgrade this capture to JWT validation evidence. |

| Agent → APIM → Toolbox | `8c2d2573-9c63-42cd-86c0-ce807db9edcf` | `https://ai.azure.com` | Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. APIM performs no token exchange. |

| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** token audience | Configured: Managed user identity; Search audience/scopes. No downstream JWT capture; do not substitute configured claims. |

Selected caller JWT header/claims (decoded-only):


```json
{
  "boundary": "selected Azure CLI credential -> hosted agent endpoint",
  "validation": "DECODED_ONLY_NOT_VALIDATED",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": "https://ai.azure.com",
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "scp": "user_impersonation",
    "idtyp": "user",
    "ver": "1.0",
    "exp": 1793540065,
    "iat": 1793535738
  }
}
```


Selected platform JWT header/claims (APIM-validated):


```json
{
  "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
  "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": [
      "https://ai.azure.com"
    ],
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "appid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "idtyp": "app",
    "ver": "1.0",
    "exp": "1793539640",
    "iat": "1793535740"
  }
}
```


Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` means absent from this observation, not an authorization failure. RBAC/application authorization need not appear as a `roles` claim.

**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, including track A; it is neither the initiating human nor A's project managed identity.

The caller's delegated `scp` is not a downstream Search scope. This replay fails with `AADSTS500016` before a query; managed user token acquisition is configured, but no backend user token or internal OBO grant is observed.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call retrieve_kb_c exactly once with arguments {"query": "Find the normal access record in cohort C"}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO`; status **failed**.

Actual hosted error excerpt (full error in secondary capture):


```text
('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for \'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\'. HTTP s
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `245344ed-e243-488f-a0bf-8834466df825`; backend HTTP **200**.

UTC request `2026-11-01T12:27:24.0730473Z`; response `2026-11-01T12:27:24.8556212Z`.

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

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T12:33:00.437513+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T12:27:24.839939773+00:00`.


```text
2026-11-01 12:27:24,835 ERROR agent_framework_foundry_hosting._responses: Failed to prepare agent: ('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for \'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.Cog
```


UTC `2026-11-01T12:27:24.839939773+00:00`.


```text
mcp.shared.exceptions.McpError: tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {"errors":[{"name":"observed","type":"mcp","error":{"code":"HTTP_400","message":"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest
```


<details>

<summary>Real logged exchange — c-native: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1`. Configured downstream target: `https://srchabcc7puse24s5tluc.search.windows.net/knowledgebases/kb-c/mcp?api-version=2026-05-01-preview` (configuration is not execution evidence).

Caller-context SHA-256: `tn7gPnZWYb419FaVa9pB65nplSWvNnjYCwExRSDn/Jg=`.

Exact captured request (only sensitive baggage redacted):


```json
{"method":"tools/list","jsonrpc":"2.0","id":2}
```


Exact captured response:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32007,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\r\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\r\\nStatus Code: 400 BadRequest\\r\\nError Code: ValidationError\\r\\nReason Phrase: Bad Request\\r\\nResponse Body: {\\n  \\\"error\\\": {\\n    \\\"code\\\": \\\"ValidationError\\\",\\n    \\\"severity\\\": null,\\n    \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\",\\n    \\\"messageFormat\\\": null,\\n    \\\"messageParameters\\\": null,\\n    \\\"referenceCode\\\": null,\\n    \\\"detailsUri\\\": null,\\n    \\\"target\\\": \\\"UserToken\\\",\\n    \\\"details\\\": [\\n      {\\n        \\\"code\\\": \\\"Invalid\\\",\\n        \\\"severity\\\": null,\\n        \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\",\\n        \\\"messageFormat\\\": null,\\n        \\\"messageParameters\\\": {},\\n        \\\"referenceCode\\\": null,\\n        \\\"detailsUri\\\": null,\\n        \\\"target\\\": \\\"UserToken\\\",\\n        \\\"details\\\": [],\\n        \\\"innerError\\\": null,\\n        \\\"debugInfo\\\": null,\\n        \\\"additionalInfo\\\": null\\n      }\\n    ],\\n    \\\"innerError\\\": null,\\n    \\\"debugInfo\\\": null,\\n    \\\"additionalInfo\\\": null\\n  },\\n  \\\"correlation\\\": {\\n    \\\"operation\\\": \\\"d5b56ddb7a588ae69efa91fa59f75472\\\",\\n    \\\"request\\\": \\\"0daec734253b9ae5\\\"\\n  },\\n  \\\"environment\\\": \\\"eastus2\\\",\\n  \\\"location\\\": \\\"eastus2\\\",\\n  \\\"time\\\": \\\"2026-11-01T12:27:24.8327013+00:00\\\",\\n  \\\"componentName\\\": \\\"obotoken\\\",\\n  \\\"statusCode\\\": 400\\n}\"}}]}"}}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "677a0b63-cf4f-4d6d-8937-0dfdb0bc5dfe",
    "callerContextPresent": "True",
    "callerContextHash": "tn7gPnZWYb419FaVa9pB65nplSWvNnjYCwExRSDn/Jg=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "appid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539640",
        "iat": "1793535740"
      },
      "tokenSha256": "b47eb9071811cdd8a9834a30a38d950ecc9728860b221283718838ea58b5b9e3",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:21.8348223Z",
    "requestBody": "{\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"sampling\":{}},\"clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"}},\"jsonrpc\":\"2.0\",\"id\":0}",
    "responseTimestamp": "2026-11-01T12:27:22.0285627Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":0,\"result\":{\"protocolVersion\":\"2025-11-25\",\"capabilities\":{\"tools\":{},\"tasks\":{\"list\":{},\"cancel\":{},\"requests\":{\"tools\":{\"call\":{}}}},\"resources\":{\"listChanged\":false,\"subscribe\":false},\"extensions\":{\"io.modelcontextprotocol/skills\":{}}},\"serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "38912a3e-3b8c-4a3f-80c2-7f4069c59a7b",
    "callerContextPresent": "True",
    "callerContextHash": "tn7gPnZWYb419FaVa9pB65nplSWvNnjYCwExRSDn/Jg=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "appid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539640",
        "iat": "1793535740"
      },
      "tokenSha256": "b47eb9071811cdd8a9834a30a38d950ecc9728860b221283718838ea58b5b9e3",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:23.9074328Z",
    "requestBody": "{\"method\":\"notifications/initialized\",\"jsonrpc\":\"2.0\"}",
    "responseTimestamp": "2026-11-01T12:27:23.9730027Z",
    "responseBody": "<empty-body>",
    "backendStatus": 204
  },
  {
    "apimRequestId": "c069d0f8-faf8-4e40-baa1-1b69642b5f75",
    "callerContextPresent": "True",
    "callerContextHash": "tn7gPnZWYb419FaVa9pB65nplSWvNnjYCwExRSDn/Jg=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "appid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539640",
        "iat": "1793535740"
      },
      "tokenSha256": "b47eb9071811cdd8a9834a30a38d950ecc9728860b221283718838ea58b5b9e3",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:24.0252802Z",
    "requestBody": "{\"method\":\"ping\",\"jsonrpc\":\"2.0\",\"id\":1}",
    "responseTimestamp": "2026-11-01T12:27:24.0601535Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "245344ed-e243-488f-a0bf-8834466df825",
    "callerContextPresent": "True",
    "callerContextHash": "tn7gPnZWYb419FaVa9pB65nplSWvNnjYCwExRSDn/Jg=",
    "observedPlatformPrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "appid": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539640",
        "iat": "1793535740"
      },
      "tokenSha256": "b47eb9071811cdd8a9834a30a38d950ecc9728860b221283718838ea58b5b9e3",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:24.0730473Z",
    "requestBody": "{\"method\":\"tools/list\",\"jsonrpc\":\"2.0\",\"id\":2}",
    "responseTimestamp": "2026-11-01T12:27:24.8556212Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"error\":{\"code\":-32007,\"message\":\"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"HTTP_400\\\",\\\"message\\\":\\\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\\\"error\\\\\\\": {\\\\n    \\\\\\\"code\\\\\\\": \\\\\\\"ValidationError\\\\\\\",\\\\n    \\\\\\\"severity\\\\\\\": null,\\\\n    \\\\\\\"message\\\\\\\": \\\\\\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\\\",\\\\n    \\\\\\\"messageFormat\\\\\\\": null,\\\\n    \\\\\\\"messageParameters\\\\\\\": null,\\\\n    \\\\\\\"referenceCode\\\\\\\": null,\\\\n    \\\\\\\"detailsUri\\\\\\\": null,\\\\n    \\\\\\\"target\\\\\\\": \\\\\\\"UserToken\\\\\\\",\\\\n    \\\\\\\"details\\\\\\\": [\\\\n      {\\\\n        \\\\\\\"code\\\\\\\": \\\\\\\"Invalid\\\\\\\",\\\\n        \\\\\\\"severity\\\\\\\": null,\\\\n        \\\\\\\"message\\\\\\\": \\\\\\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\\\",\\\\n        \\\\\\\"messageFormat\\\\\\\": null,\\\\n        \\\\\\\"messageParameters\\\\\\\": {},\\\\n        \\\\\\\"referenceCode\\\\\\\": null,\\\\n        \\\\\\\"detailsUri\\\\\\\": null,\\\\n        \\\\\\\"target\\\\\\\": \\\\\\\"UserToken\\\\\\\",\\\\n        \\\\\\\"details\\\\\\\": [],\\\\n        \\\\\\\"innerError\\\\\\\": null,\\\\n        \\\\\\\"debugInfo\\\\\\\": null,\\\\n        \\\\\\\"additionalInfo\\\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\\\"innerError\\\\\\\": null,\\\\n    \\\\\\\"debugInfo\\\\\\\": null,\\\\n    \\\\\\\"additionalInfo\\\\\\\": null\\\\n  },\\\\n  \\\\\\\"correlation\\\\\\\": {\\\\n    \\\\\\\"operation\\\\\\\": \\\\\\\"d5b56ddb7a588ae69efa91fa59f75472\\\\\\\",\\\\n    \\\\\\\"request\\\\\\\": \\\\\\\"0daec734253b9ae5\\\\\\\"\\\\n  },\\\\n  \\\\\\\"environment\\\\\\\": \\\\\\\"eastus2\\\\\\\",\\\\n  \\\\\\\"location\\\\\\\": \\\\\\\"eastus2\\\\\\\",\\\\n  \\\\\\\"time\\\\\\\": \\\\\\\"2026-11-01T12:27:24.8327013+00:00\\\\\\\",\\\\n  \\\\\\\"componentName\\\\\\\": \\\\\\\"obotoken\\\\\\\",\\\\n  \\\\\\\"statusCode\\\\\\\": 400\\\\n}\\\"}}]}\"}}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO",
  "object": "response",
  "output": [],
  "created_at": 1793536039,
  "error": {
    "code": "server_error",
    "message": "('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for \\'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\\'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\"error\\\\\": {\\\\n    \\\\\"code\\\\\": \\\\\"ValidationError\\\\\",\\\\n    \\\\\"severity\\\\\": null,\\\\n    \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\",\\\\n    \\\\\"messageFormat\\\\\": null,\\\\n    \\\\\"messageParameters\\\\\": null,\\\\n    \\\\\"referenceCode\\\\\": null,\\\\n    \\\\\"detailsUri\\\\\": null,\\\\n    \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n    \\\\\"details\\\\\": [\\\\n      {\\\\n        \\\\\"code\\\\\": \\\\\"Invalid\\\\\",\\\\n        \\\\\"severity\\\\\": null,\\\\n        \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\",\\\\n        \\\\\"messageFormat\\\\\": null,\\\\n        \\\\\"messageParameters\\\\\": {},\\\\n        \\\\\"referenceCode\\\\\": null,\\\\n        \\\\\"detailsUri\\\\\": null,\\\\n        \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n        \\\\\"details\\\\\": [],\\\\n        \\\\\"innerError\\\\\": null,\\\\n        \\\\\"debugInfo\\\\\": null,\\\\n        \\\\\"additionalInfo\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\"innerError\\\\\": null,\\\\n    \\\\\"debugInfo\\\\\": null,\\\\n    \\\\\"additionalInfo\\\\\": null\\\\n  },\\\\n  \\\\\"correlation\\\\\": {\\\\n    \\\\\"operation\\\\\": \\\\\"d5b56ddb7a588ae69efa91fa59f75472\\\\\",\\\\n    \\\\\"request\\\\\": \\\\\"0daec734253b9ae5\\\\\"\\\\n  },\\\\n  \\\\\"environment\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"location\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"time\\\\\": \\\\\"2026-11-01T12:27:24.8327013+00:00\\\\\",\\\\n  \\\\\"componentName\\\\\": \\\\\"obotoken\\\\\",\\\\n  \\\\\"statusCode\\\\\": 400\\\\n}\"}}]}'))"
  },
  "parallel_tool_calls": false,
  "status": "failed",
  "response_id": "caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO",
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
  "experimentId": "d791f5ca-24a5-4d8f-ab04-dffc0f08c50e",
  "responseId": "caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO",
  "invocationStartedAt": "2026-11-01T12:27:15.187455+00:00",
  "invocationCompletedAt": "2026-11-01T12:27:23.902184+00:00",
  "queriedAt": "2026-11-01T12:33:00.437513+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.213594764+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.218545878+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.599161309+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,599 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.731809266+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,731 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,763 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.764088758+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.766767078+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,766 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.766915937+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,766 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.767322643+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,767 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.767414212+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,767 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.832743986+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,832 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.833652530+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,833 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.833905019+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,833 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.833976200+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,833 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.835047749+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,834 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.835495020+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 12:27:15 +0000] [44] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:15.835517382+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:15,835 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:16.122726418+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:16,122 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 9c784db0d93fee07b67ce490018c2f1f)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:16.123477236+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:16,123 INFO azure.ai.agentserver: 192.168.0.1:56432 \"GET /readiness 1.1\" 200 20 969\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:16.123653738+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:16,123 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.7ms (trace-id: 9c784db0d93fee07b67ce490018c2f1f)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:19.710814063+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:19,710 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 009447de86428bf922ca8a7a61ac1eb6, x-ms-client-request-id: b8718776-29bb-4fbe-80f4-08217b53fbc0, trace-id: 009447de86428bf922ca8a7a61ac1eb6)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:19.713094941+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:19,712 INFO azure.ai.agentserver: Creating response caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO: streaming=False background=False store=False model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:19.713874225+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:19,713 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:20.154008497+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:20,153 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.003781659+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,003 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.005534357+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,005 INFO mcp.client.streamable_http: Negotiated protocol version: 2025-11-25"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.008711481+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,008 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.009512370+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,008 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:22.009667247+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:22,009 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.950965322+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,950 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 204 No Content\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.954704839+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,954 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.954941719+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,954 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:23.955050863+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:23,955 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.034558101+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,034 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.040031029+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,039 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.040205548+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,040 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.040625910+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,040 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.830759850+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,830 INFO httpx: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,835 ERROR agent_framework_foundry_hosting._responses: Failed to prepare agent: ('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for \\'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\\'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\"error\\\\\": {\\\\n    \\\\\"code\\\\\": \\\\\"ValidationError\\\\\",\\\\n    \\\\\"severity\\\\\": null,\\\\n    \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\",\\\\n    \\\\\"messageFormat\\\\\": null,\\\\n    \\\\\"messageParameters\\\\\": null,\\\\n    \\\\\"referenceCode\\\\\": null,\\\\n    \\\\\"detailsUri\\\\\": null,\\\\n    \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n    \\\\\"details\\\\\": [\\\\n      {\\\\n        \\\\\"code\\\\\": \\\\\"Invalid\\\\\",\\\\n        \\\\\"severity\\\\\": null,\\\\n        \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\",\\\\n        \\\\\"messageFormat\\\\\": null,\\\\n        \\\\\"messageParameters\\\\\": {},\\\\n        \\\\\"referenceCode\\\\\": null,\\\\n        \\\\\"detailsUri\\\\\": null,\\\\n        \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n        \\\\\"details\\\\\": [],\\\\n        \\\\\"innerError\\\\\": null,\\\\n        \\\\\"debugInfo\\\\\": null,\\\\n        \\\\\"additionalInfo\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\"innerError\\\\\": null,\\\\n    \\\\\"debugInfo\\\\\": null,\\\\n    \\\\\"additionalInfo\\\\\": null\\\\n  },\\\\n  \\\\\"correlation\\\\\": {\\\\n    \\\\\"operation\\\\\": \\\\\"d5b56ddb7a588ae69efa91fa59f75472\\\\\",\\\\n    \\\\\"request\\\\\": \\\\\"0daec734253b9ae5\\\\\"\\\\n  },\\\\n  \\\\\"environment\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"location\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"time\\\\\": \\\\\"2026-11-01T12:27:24.8327013+00:00\\\\\",\\\\n  \\\\\"componentName\\\\\": \\\\\"obotoken\\\\\",\\\\n  \\\\\"statusCode\\\\\": 400\\\\n}\"}}]}'))"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 3488, in __aenter__"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self.connect()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework_foundry_hosting/_toolbox.py\", line 267, in connect"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await super().connect(reset=reset)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 1932, in connect"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self._run_on_lifecycle_owner(\"connect\", reset=reset)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 1828, in _run_on_lifecycle_owner"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await future"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 1728, in _run_lifecycle_owner"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self._connect_on_owner("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    ...<3 lines>..."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 2071, in _connect_on_owner"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self.load_tools()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 2536, in load_tools"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self._load_tools_locked()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 2574, in _load_tools_locked"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    tool_list = await self.session.list_tools(params=params)  # type: ignore[union-attr]"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/mcp/client/session.py\", line 529, in list_tools"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    result = await self.send_request("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "             ^^^^^^^^^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    ...<2 lines>..."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    ^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/mcp/shared/session.py\", line 306, in send_request"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    raise McpError(response_or_error.error)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "mcp.shared.exceptions.McpError: tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\r\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\r\\nStatus Code: 400 BadRequest\\r\\nError Code: ValidationError\\r\\nReason Phrase: Bad Request\\r\\nResponse Body: {\\n  \\\"error\\\": {\\n    \\\"code\\\": \\\"ValidationError\\\",\\n    \\\"severity\\\": null,\\n    \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\",\\n    \\\"messageFormat\\\": null,\\n    \\\"messageParameters\\\": null,\\n    \\\"referenceCode\\\": null,\\n    \\\"detailsUri\\\": null,\\n    \\\"target\\\": \\\"UserToken\\\",\\n    \\\"details\\\": [\\n      {\\n        \\\"code\\\": \\\"Invalid\\\",\\n        \\\"severity\\\": null,\\n        \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\",\\n        \\\"messageFormat\\\": null,\\n        \\\"messageParameters\\\": {},\\n        \\\"referenceCode\\\": null,\\n        \\\"detailsUri\\\": null,\\n        \\\"target\\\": \\\"UserToken\\\",\\n        \\\"details\\\": [],\\n        \\\"innerError\\\": null,\\n        \\\"debugInfo\\\": null,\\n        \\\"additionalInfo\\\": null\\n      }\\n    ],\\n    \\\"innerError\\\": null,\\n    \\\"debugInfo\\\": null,\\n    \\\"additionalInfo\\\": null\\n  },\\n  \\\"correlation\\\": {\\n    \\\"operation\\\": \\\"d5b56ddb7a588ae69efa91fa59f75472\\\",\\n    \\\"request\\\": \\\"0daec734253b9ae5\\\"\\n  },\\n  \\\"environment\\\": \\\"eastus2\\\",\\n  \\\"location\\\": \\\"eastus2\\\",\\n  \\\"time\\\": \\\"2026-11-01T12:27:24.8327013+00:00\\\",\\n  \\\"componentName\\\": \\\"obotoken\\\",\\n  \\\"statusCode\\\": 400\\n}\"}}]}"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": ""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "The above exception was the direct cause of the following exception:"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": ""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework_foundry_hosting/_responses.py\", line 1044, in _handle_prepared_response"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self._ensure_agent_ready()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework_foundry_hosting/_responses.py\", line 940, in _ensure_agent_ready"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await stack.enter_async_context(cast(AbstractAsyncContextManager[Any], agent))"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/opt/python/3.13.17/lib/python3.13/contextlib.py\", line 668, in enter_async_context"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    result = await _enter(cm)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "             ^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_agents.py\", line 1085, in __aenter__"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    return await self.open()"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "           ^^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_agents.py\", line 1077, in open"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    await self._async_exit_stack.enter_async_context(context_manager)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/opt/python/3.13.17/lib/python3.13/contextlib.py\", line 668, in enter_async_context"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    result = await _enter(cm)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "             ^^^^^^^^^^^^^^^^"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/agent_framework/_mcp.py\", line 3494, in __aenter__"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "    raise ToolExecutionException(\"Failed to enter context manager.\", inner_exception=ex) from ex"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839939773+00:00",
      "stream": "stderr",
      "line": "agent_framework.exceptions.ToolExecutionException: ('Failed to enter context manager.', McpError('tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution faile"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.839998921+00:00",
      "stream": "stderr",
      "line": "d for \\'/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary\\'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\\\r\\\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\\\r\\\\nStatus Code: 400 BadRequest\\\\r\\\\nError Code: ValidationError\\\\r\\\\nReason Phrase: Bad Request\\\\r\\\\nResponse Body: {\\\\n  \\\\\"error\\\\\": {\\\\n    \\\\\"code\\\\\": \\\\\"ValidationError\\\\\",\\\\n    \\\\\"severity\\\\\": null,\\\\n    \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\",\\\\n    \\\\\"messageFormat\\\\\": null,\\\\n    \\\\\"messageParameters\\\\\": null,\\\\n    \\\\\"referenceCode\\\\\": null,\\\\n    \\\\\"detailsUri\\\\\": null,\\\\n    \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n    \\\\\"details\\\\\": [\\\\n      {\\\\n        \\\\\"code\\\\\": \\\\\"Invalid\\\\\",\\\\n        \\\\\"severity\\\\\": null,\\\\n        \\\\\"message\\\\\": \\\\\"AADSTS500016: Application \\'880da380-985e-4198-81b9-e05b1cc53158\\' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\\\",\\\\n        \\\\\"messageFormat\\\\\": null,\\\\n        \\\\\"messageParameters\\\\\": {},\\\\n        \\\\\"referenceCode\\\\\": null,\\\\n        \\\\\"detailsUri\\\\\": null,\\\\n        \\\\\"target\\\\\": \\\\\"UserToken\\\\\",\\\\n        \\\\\"details\\\\\": [],\\\\n        \\\\\"innerError\\\\\": null,\\\\n        \\\\\"debugInfo\\\\\": null,\\\\n        \\\\\"additionalInfo\\\\\": null\\\\n      }\\\\n    ],\\\\n    \\\\\"innerError\\\\\": null,\\\\n    \\\\\"debugInfo\\\\\": null,\\\\n    \\\\\"additionalInfo\\\\\": null\\\\n  },\\\\n  \\\\\"correlation\\\\\": {\\\\n    \\\\\"operation\\\\\": \\\\\"d5b56ddb7a588ae69efa91fa59f75472\\\\\",\\\\n    \\\\\"request\\\\\": \\\\\"0daec734253b9ae5\\\\\"\\\\n  },\\\\n  \\\\\"environment\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"location\\\\\": \\\\\"eastus2\\\\\",\\\\n  \\\\\"time\\\\\": \\\\\"2026-11-01T12:27:24.8327013+00:00\\\\\",\\\\n  \\\\\"componentName\\\\\": \\\\\"obotoken\\\\\",\\\\n  \\\\\"statusCode\\\\\": 400\\\\n}\"}}]}'))"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.841849981+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,841 INFO azure.ai.agentserver: Response caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO completed: status=failed output_count=0"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.842193544+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,842 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.842953281+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,842 INFO azure.ai.agentserver: 192.168.0.1:56432 \"POST /responses 1.1\" 200 3322 5133669\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.843186013+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,843 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 5131.7ms (x-request-id: 009447de86428bf922ca8a7a61ac1eb6, x-ms-client-request-id: b8718776-29bb-4fbe-80f4-08217b53fbc0, trace-id: 009447de86428bf922ca8a7a61ac1eb6)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:24.843330936+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:24,843 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:28.230387878+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:28,230 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported.\n"
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
  "responseId": "caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO",
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

Agent `obs-20261031-c-custom` v2; Toolbox v3. UTC `2026-11-01T12:27:42.424710+00:00` → `2026-11-01T12:27:49.582437+00:00`. Experiment `9826a721-f60a-4e1e-b13d-51c3ed0dcd73`.

**Identity-hop lesson (observations versus configuration)**

Control-plane source: `Azure agent control-plane identity and configured project`; observed UTC `2026-11-01T12:30:33.407081+00:00`. Configured agent instance principal `114281a8-d2fe-407c-a1cf-28461136d9af`; project managed identity `1a04abde-08e9-4949-b975-b2520119ca1d`. Configuration alone is not token evidence.

| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |

|---|---|---|---|

| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance does not upgrade this capture to JWT validation evidence. |

| Agent → APIM → Toolbox | `114281a8-d2fe-407c-a1cf-28461136d9af` | `https://ai.azure.com` | Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. APIM performs no token exchange. |

| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** token audience | Configured: OAuth2 authorization code + refresh; delegated custom API scope. No downstream JWT capture; do not substitute configured claims. |

Selected caller JWT header/claims (decoded-only):


```json
{
  "boundary": "selected Azure CLI credential -> hosted agent endpoint",
  "validation": "DECODED_ONLY_NOT_VALIDATED",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": "https://ai.azure.com",
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    "scp": "user_impersonation",
    "idtyp": "user",
    "ver": "1.0",
    "exp": 1793540362,
    "iat": 1793535765
  }
}
```


Selected platform JWT header/claims (APIM-validated):


```json
{
  "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
  "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
  "header": {
    "alg": "RS256",
    "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
  },
  "claims": {
    "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
    "aud": [
      "https://ai.azure.com"
    ],
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "114281a8-d2fe-407c-a1cf-28461136d9af",
    "appid": "114281a8-d2fe-407c-a1cf-28461136d9af",
    "idtyp": "app",
    "ver": "1.0",
    "exp": "1793539667",
    "iat": "1793535767"
  }
}
```


Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` means absent from this observation, not an authorization failure. RBAC/application authorization need not appear as a `roles` claim.

**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, including track A; it is neither the initiating human nor A's project managed identity.

Current upstream replay is **pending consent**, not OAuth success. The configured delegated scope is not an observed token `scp`. The earlier **direct C custom OAuth success** used authorization-code consent plus refresh on a different invocation/route, without this upstream APIM hop; it must not be relabelled as this run or as literal JWT-bearer OBO.

**1. User input → actual hosted response**

Exact submitted user prompt (not the generated MCP arguments):


```text
Call probe_echo exactly once with arguments {"experiment_id": "9826a721-f60a-4e1e-b13d-51c3ed0dcd73", "message": "oauth-toolbox", "count": 2}. Return its exact result.
```


Hosted HTTP **200**; response `caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9`; status **incomplete**.

No hosted answer/tool output; returned event types:


```json
[
  "oauth_consent_request"
]
```


**2. APIM → Toolbox: observed MCP request/response**

`tools/list`; request `99d8874d-2998-41df-81a0-d2889599363c`; backend HTTP **200**.

UTC request `2026-11-01T12:27:49.2057958Z`; response `2026-11-01T12:27:50.1604481Z`.

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
    "traceparent": "00-356efd4bb89e604f05fd0aa3bbe289ec-30a6cef9f2b59d2f-01",
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

Pinned hosted console query: **CAPTURED_CORRELATED_LINES** (queried `2026-11-01T12:33:11.062321+00:00`). Hosted service responses are not runtime console logs.

Actual runtime console excerpts (full selected log lines in secondary capture):

UTC `2026-11-01T12:27:50.418330069+00:00`.


```text
2026-11-01 12:27:50,418 WARNING agent_framework_foundry_hosting._responses: Consent URL for tool 'observed': <consent-url-redacted>
```


<details>

<summary>Real logged exchange — c-custom: full secondary capture</summary>

POST URL: `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1`. Configured downstream target: `https://abc-custom-mcp-e8383e4d.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` (configuration is not execution evidence).

Caller-context SHA-256: `+0E+xZan/ZrSsqZae2II0b8Sz5KSJmLv3FSkWfreTTY=`.

Exact captured request (only sensitive baggage redacted):


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-356efd4bb89e604f05fd0aa3bbe289ec-30a6cef9f2b59d2f-01","baggage":"<baggage-redacted>"}}}
```


Exact captured response:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32006,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"CONSENT_REQUIRED\",\"message\":\"<consent-url-redacted>\"}}]}"}}
```


All APIM exchanges for this invocation:


```json
[
  {
    "apimRequestId": "129dfb25-646c-4a66-a9a4-fc18247d8ef2",
    "callerContextPresent": "True",
    "callerContextHash": "+0E+xZan/ZrSsqZae2II0b8Sz5KSJmLv3FSkWfreTTY=",
    "observedPlatformPrincipalId": "114281a8-d2fe-407c-a1cf-28461136d9af",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "114281a8-d2fe-407c-a1cf-28461136d9af",
        "appid": "114281a8-d2fe-407c-a1cf-28461136d9af",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539667",
        "iat": "1793535767"
      },
      "tokenSha256": "2e73cbf7ed11a5a1398508249990c81232e322ea6148ea62ca08fcca567e8588",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:48.8392866Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-356efd4bb89e604f05fd0aa3bbe289ec-d46042d630608a3c-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T12:27:49.0553247Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"resultType\":\"complete\",\"supportedVersions\":[\"2025-11-25\",\"2026-07-28\"],\"capabilities\":{\"tools\":{},\"resources\":{},\"extensions\":{\"io.modelcontextprotocol/skills\":{},\"io.modelcontextprotocol/tasks\":{}}},\"_meta\":{\"io.modelcontextprotocol/serverInfo\":{\"name\":\"Foundry Toolbox MCP\",\"version\":\"1.0.0\"}},\"instructions\":\"This server exposes tools configured in the requested Foundry toolbox. Use tools/list to enumerate available tools and tools/call to invoke them.\",\"ttlMs\":300000,\"cacheScope\":\"private\"}}",
    "backendStatus": 200
  },
  {
    "apimRequestId": "99d8874d-2998-41df-81a0-d2889599363c",
    "callerContextPresent": "True",
    "callerContextHash": "+0E+xZan/ZrSsqZae2II0b8Sz5KSJmLv3FSkWfreTTY=",
    "observedPlatformPrincipalId": "114281a8-d2fe-407c-a1cf-28461136d9af",
    "platformTokenObservation": {
      "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
      "validation": "VALIDATED_AT_APIM_ENTRA_BOUNDARY",
      "header": {
        "alg": "RS256",
        "kid": "ryBx-65jNoxH4FQH_6zarNjaNf4"
      },
      "claims": {
        "iss": "https://sts.windows.net/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/",
        "aud": [
          "https://ai.azure.com"
        ],
        "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
        "oid": "114281a8-d2fe-407c-a1cf-28461136d9af",
        "appid": "114281a8-d2fe-407c-a1cf-28461136d9af",
        "idtyp": "app",
        "ver": "1.0",
        "exp": "1793539667",
        "iat": "1793535767"
      },
      "tokenSha256": "2e73cbf7ed11a5a1398508249990c81232e322ea6148ea62ca08fcca567e8588",
      "forwarding": "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
    },
    "requestTimestamp": "2026-11-01T12:27:49.2057958Z",
    "requestBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"2026-07-28\",\"io.modelcontextprotocol/clientInfo\":{\"name\":\"mcp\",\"version\":\"0.1.0\"},\"io.modelcontextprotocol/clientCapabilities\":{\"sampling\":{}},\"traceparent\":\"00-356efd4bb89e604f05fd0aa3bbe289ec-30a6cef9f2b59d2f-01\",\"baggage\":\"<baggage-redacted>\"}}}",
    "responseTimestamp": "2026-11-01T12:27:50.1604481Z",
    "responseBody": "{\"jsonrpc\":\"2.0\",\"id\":2,\"error\":{\"code\":-32006,\"message\":\"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\\\"errors\\\":[{\\\"name\\\":\\\"observed\\\",\\\"type\\\":\\\"mcp\\\",\\\"error\\\":{\\\"code\\\":\\\"CONSENT_REQUIRED\\\",\\\"message\\\":\\\"<consent-url-redacted>\\\"}}]}\"}}",
    "backendStatus": 200
  }
]
```


Actual hosted response (sensitive consent/session identifiers redacted):


```json
{
  "id": "caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9",
  "object": "response",
  "output": [
    {
      "id": "<oauth-request-id-redacted>",
      "response_id": "caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9",
      "type": "oauth_consent_request",
      "consent_link": "<consent-url-redacted>",
      "server_label": "observed",
      "agent_reference": null
    }
  ],
  "created_at": 1793536067,
  "parallel_tool_calls": false,
  "status": "incomplete",
  "response_id": "caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9",
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
  "experimentId": "9826a721-f60a-4e1e-b13d-51c3ed0dcd73",
  "responseId": "caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9",
  "invocationStartedAt": "2026-11-01T12:27:42.424710+00:00",
  "invocationCompletedAt": "2026-11-01T12:27:49.582437+00:00",
  "queriedAt": "2026-11-01T12:33:11.062321+00:00",
  "exitCode": 1,
  "errorHttpStatus": null,
  "returnedLineCount": 0,
  "selectedLines": [
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.157112288+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_settings.FoundryStorageSettings: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.164660683+00:00",
      "stream": "stderr",
      "line": "Class azure.ai.agentserver.responses.store._foundry_provider.FoundryStorageProvider: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.559642653+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,559 INFO microsoft.opentelemetry.a365.core.exporters.utils: FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.688824242+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,688 INFO microsoft.opentelemetry._utils: Azure Monitor configured via azure-monitor-opentelemetry package"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,719 WARNING microsoft.opentelemetry._distro: Failed to set up A365 OpenAI Agents instrumentation."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "Traceback (most recent call last):"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_distro.py\", line 866, in _setup_a365_openai_agents_instrumentation"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "    from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import ("
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "        A365OpenAIAgentsInstrumentor,"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "    )"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_instrumentor.py\", line 26, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "    from ._trace_processor import OpenAIAgentsTraceProcessor"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "  File \"/app/pythonenv3.13/lib/python3.13/site-packages/microsoft/opentelemetry/_genai/_openai_agents/_trace_processor.py\", line 15, in <module>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "    from agents import MCPListToolsSpanData"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.720491990+00:00",
      "stream": "stderr",
      "line": "ModuleNotFoundError: No module named 'agents'"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.723214069+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,723 INFO microsoft.opentelemetry._distro: Azure Monitor enabled."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.723365524+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,723 INFO azure.ai.agentserver: Tracing configured successfully via microsoft-opentelemetry distro."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.723776327+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,723 INFO azure.ai.agentserver: Responses protocol: storage_provider=FoundryStorageProvider, default_model=(not set), default_fetch_history_count=-1, shutdown_grace_period=10s"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.723870283+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,723 WARNING azure.ai.agentserver: Responses resilience: DISABLED - store=true responses run in-process and are NOT durable across an ungraceful crash: a response in-flight when the process is hard-killed stays in_progress on a later GET (no mark-failed/recovery). Enable the Responses task runtime with resilient_background or steerable_conversations."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.881279623+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,881 INFO azure.ai.agentserver: AgentServerHost starting on 0.0.0.0:8088 (async)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.882040793+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,881 INFO azure.ai.agentserver: AgentServerHost started"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.882274604+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,882 INFO azure.ai.agentserver: Connectivity: project_endpoint=https://fdy-iq-rbac-tbkj2wgzdhqi6.services.ai.azure.com, otlp_endpoint=(not set), appinsights_configured=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.882389692+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,882 INFO azure.ai.agentserver: Host options: shutdown_timeout=30s, protocols=azure-ai-agentserver-core/2.3.0 (python/3.13), azure-ai-agentserver-responses/2.4.0 (python/3.13)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.883522026+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,882 INFO azure.ai.agentserver: TaskManager NOT initialized (no protocol requested task execution). Durable tasks and crash recovery are inactive; store=true work degrades to non-durable execution. tasks_declared=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.884017857+00:00",
      "stream": "stderr",
      "line": "[2026-11-01 12:27:42 +0000] [40] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:42.884046088+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:42,883 INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:43.355704390+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:43,355 INFO azure.ai.agentserver: Inbound GET /readiness started (trace-id: 2f5df6469b1bdaa3fbf8bd3dd7188e2a)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:43.356854890+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:43,356 INFO azure.ai.agentserver: 192.168.0.1:56334 \"GET /readiness 1.1\" 200 20 1145\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:43.356854890+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:43,356 INFO azure.ai.agentserver: Inbound GET /readiness completed with status 200 in 0.8ms (trace-id: 2f5df6469b1bdaa3fbf8bd3dd7188e2a)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.020606296+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,020 INFO azure.ai.agentserver: Inbound POST /responses started (x-request-id: 356efd4bb89e604f05fd0aa3bbe289ec, x-ms-client-request-id: 7fc76328-0e21-45e4-9202-fc2c9cae6f7d, trace-id: 356efd4bb89e604f05fd0aa3bbe289ec)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.026354637+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,021 INFO azure.ai.agentserver: Creating response caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9: streaming=False background=False store=True model= conversation_id=None previous_response_id=None has_user_id=True has_call_id=True"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:47.026354637+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:47,021 INFO azure.ai.agentserver: Invoking handler ResponsesAgentServerHost._dispatch_create for response caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.116863387+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,116 INFO azure.identity.aio._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.292830424+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,292 INFO azure.ai.agentserver: Foundry storage POST ***/storage/responses?api-version=v1 -> 201 (174.5ms, x-ms-client-request-id=a532cf18-d5ef-11f1-ab08-2ecb50edf33a, traceparent=, x-request-id=db249af521dea0c7d56763b212a111ba, apim-request-id=79567d54-460d-40f8-8aa8-ab37aab1b07a, has_call_id=True)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.294020623+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,293 INFO azure.identity._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.294524098+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,294 INFO azure.identity._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:48.500165209+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:48,500 INFO azure.identity._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.030879301+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,030 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.053091794+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,053 INFO azure.identity._internal.msal_managed_identity_client: AppServiceCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.058440780+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,054 INFO azure.identity._internal.decorators: ManagedIdentityCredential.get_token succeeded"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:49.058642235+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:49,058 INFO azure.identity._credentials.default: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.135550257+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,135 INFO httpx2: HTTP Request: POST https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1 \"HTTP/1.1 200 OK\""
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.139759245+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,139 WARNING azure.ai.agentserver.core._experimental: Class azure.ai.agentserver.core.storage._state.FoundryStateStore: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.140066493+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,140 INFO azure.identity.aio._credentials.environment: No environment configuration found."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.140429371+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,140 INFO azure.identity.aio._credentials.managed_identity: ManagedIdentityCredential will use App Service managed identity"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.190030760+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,189 INFO azure.identity.aio._credentials.chained: DefaultAzureCredential acquired a token from ManagedIdentityCredential"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.284479350+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,284 WARNING azure.ai.agentserver.core: Foundry storage GET ***/storage/state_stores/*?api-version=v1 -> 404 (94.1ms, x-ms-client-request-id=a707e616-d5ef-11f1-ab08-2ecb50edf33a, traceparent=, x-request-id=fde35450cd08f698d51816f14f83f829, apim-request-id=4fc99d86-5c87-49a7-bf38-ca7db4466dd8)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.284838254+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,284 WARNING azure.ai.agentserver.core._experimental: Class azure.ai.agentserver.core.storage._errors.FoundryStorageNotFoundError: This is an experimental class, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.350654857+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,350 INFO azure.ai.agentserver.core: Foundry storage POST ***/storage/state_stores?api-version=v1 -> 201 (64.8ms, x-ms-client-request-id=a71dfca8-d5ef-11f1-ab08-2ecb50edf33a, traceparent=, x-request-id=fde35450cd08f698d51816f14f83f829, apim-request-id=f62937fc-0267-47df-b725-6c3755bbe74d)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.417060506+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,416 INFO azure.ai.agentserver.core: Foundry storage POST ***/storage/state_stores/*/items?api-version=v1 -> 201 (65.6ms, x-ms-client-request-id=a727ff82-d5ef-11f1-ab08-2ecb50edf33a, traceparent=, x-request-id=fde35450cd08f698d51816f14f83f829, apim-request-id=2538fd78-96d5-4af6-84bf-07d24152dc8e)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.418330069+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,418 WARNING agent_framework_foundry_hosting._responses: Consent URL for tool 'observed': <consent-url-redacted>"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.520563865+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,520 INFO azure.ai.agentserver: Foundry storage POST ***/storage/responses/caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9?api-version=v1 -> 200 (101.3ms, x-ms-client-request-id=a73258e2-d5ef-11f1-ab08-2ecb50edf33a, traceparent=, x-request-id=db249af521dea0c7d56763b212a111ba, apim-request-id=c7b51602-2bb9-47ec-bc56-584c8cb46f33, has_call_id=True)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.520885518+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,520 INFO azure.ai.agentserver: Response caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9 completed: status=incomplete output_count=1"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.521155208+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,521 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.schedule_flush_spans: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.521762660+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,521 INFO azure.ai.agentserver: 192.168.0.1:54366 \"POST /responses 1.1\" 200 3081 3501667\u03bcs"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.521968299+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,521 INFO azure.ai.agentserver: Inbound POST /responses completed with status 200 in 3501.1ms (x-request-id: 356efd4bb89e604f05fd0aa3bbe289ec, x-ms-client-request-id: 7fc76328-0e21-45e4-9202-fc2c9cae6f7d, trace-id: 356efd4bb89e604f05fd0aa3bbe289ec)"
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.522109961+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,522 WARNING azure.ai.agentserver.core._experimental: Method azure.ai.agentserver.core._tracing.flush_spans_async: This is an experimental method, and may change at any time."
    },
    {
      "correlatedBySessionAndTime": true,
      "timestamp": "2026-11-01T12:27:50.530120090+00:00",
      "stream": "stderr",
      "line": "2026-11-01 12:27:50,530 INFO microsoft.opentelemetry.a365.core.exporters.agent365_exporter: No eligible genAI spans to export; nothing exported.\n"
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
  "responseId": "caresp_0538193c78226294008EDcTB6DBWq6mbnBKvqnIn60ejknFyr9",
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
