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

![Identity and gateway boundaries](assets/workshop-architecture.svg)

- Choose **one independent track**, not four sequential exercises.
- Deploy one Active, pinned hosted agent; collect a real tool allow and deny.
- [Clone the repository](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway) for commands; MOAW is read-only.

## Choose one independent track

| Need | Track | Data principal | After setup |
| --- | --- | --- | --- |
| Shared Search KB / custom API | A | Project MI | 45 min |
| Per-agent Search KB / custom API | B | Calling agent instance | 60 min |
| Search follows user access | C native | Managed user context | 60 min |
| Delegated custom API | C custom | OAuth-authorizing user | 75 min |

- A/B: native Search **or** application-token FastMCP. C custom: delegated API, no KB.
- Allow 60–90 min for setup/evidence/cleanup, plus propagation; 150 min covers one track.
- Before deployment: record track, expected principal, audience and negative test.

---

# Architecture: where authorization actually happens

![Toolbox identity and gateway boundaries](assets/workshop-architecture.svg)

- Caller platform scope: `https://ai.azure.com/.default`.
- Hosted runtime: `FoundryChatClient` + `FoundryToolbox` + `ResponsesHostServer`.
- Connection selects **downstream** identity; ARM provisioning tokens are not data tokens.
- Search/API authorizes data access. APIM validates ingress and forwards the bearer unchanged.

| Track | Connection auth | Downstream audience | Data authorization |
| --- | --- | --- | --- |
| A native | `ProjectManagedIdentity` | `https://search.azure.com` | Project MI Search RBAC |
| A custom | `ProjectManagedIdentity` | Registered API audience | Validated project principal + ACL |
| B native | `AgenticIdentityToken` | `https://search.azure.com` | Calling instance Search RBAC |
| B custom | `AgenticIdentityToken` | Registered API audience | Validated calling principal + ACL; acquisition unverified here |
| C native | `UserEntraToken` | `https://search.azure.com` | User Search RBAC |
| C custom | OAuth2 authorization code + refresh | API v2 audience | JWT validation + delegated scope |

## Evidence legend — applies to all six captures

| Label | What it proves |
| --- | --- |
| Decoded only | Selected caller claims; **not locally validated** |
| APIM-validated | Calling agent instance token; unchanged forwarding, no APIM exchange |
| MCP-validated | Downstream boundary validated the token; correlate actual query/result |
| Configured / NOT_OBSERVED | Intended identity, not captured token claims or execution |
| Hosted snapshot | Service-returned events; **not runtime console logs**, not model proof |

- No raw JWT, bearer, signature or keys stored. Only allowlisted claims/header fields.
- Missing `scp`, `roles` or `idtyp` means absent from this observation, not failure; RBAC/ACL need not emit `roles`.
- Native user context **≠** custom OAuth. Authorization code/`offline_access` **≠** internal JWT-bearer OBO; no grant was traced.
- Accepted ARM `audience` **≠** acquired API token. Neither agent nor APIM exchanges data tokens.
- Six isolated upstream captures: November 1, 2026; five at 12:27 UTC, C custom at **13:09 UTC**.
  Public synthetic inputs only; body diagnostics 8192 bytes, no headers; original defaults unchanged.
  Sensitive consent/session baggage is redacted. Native Search internals remain **NOT_OBSERVED**.

[Full architecture](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/architecture.svg)
includes optional prompt-agent, raw Search and gateway paths.

---

# Prerequisites, permissions and safety

![Identity and gateway boundaries](assets/workshop-architecture.svg)

## Required before deployment

- Dedicated tenant/subscription lab resources; synthetic data only.
- Windows, PowerShell, Git, Azure CLI/Bicep; Python 3.12 root tooling / 3.13 hosted builds.
- Foundry account/project, chat deployment (default `gpt-4o-mini`), hosted/Toolbox preview access and quota.
- Optional Bicep replay: existing **APIM Standard v2**; dedicated `AIGateway` uses separate Terraform/portal setup.
- A/B custom: registered Entra API, reachable HTTPS application-token FastMCP, permission to authorize exact principals.
- C custom: azd with `ai connection create`, separate API/client registrations, HTTPS delegated FastMCP.
- [Terraform guide](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/terraform/README.md):
  agree resource ownership before mixing deployment tools.

## Permission owners

| Owner | Required authority |
| --- | --- |
| Infrastructure deployer | Resource deployment in lab/Foundry groups; RBAC assignment write at affected scopes (e.g. Contributor + scoped RBAC Administrator) |
| Project administrator/provisioner | Connection write, Toolbox create/update; invoker Azure AI User/project-agent access; runtime model/Toolbox access |
| Search RBAC administrator | Search Index Data Reader for the selected A/B/native data object ID |
| Entra application administrator/developer | Custom API/client registration, permissions and required tenant consent/assignment |
| Intended user | Tenant sign-in policy and any connection authorization |

- **Project access ≠ data access**; subscription ownership grants no Entra app permissions.
- Use Entra **object IDs**, not ARM/client IDs or names. Provisioners create connections/Toolboxes only.
- B needs supported calling identity; tenant/preview admins may need to enable it.

## Costs and secrets

- Foundation replay creates **three Basic Search services**, projects and telemetry pairs, even for one track.
  Budget hosting/model/APIM/Search/logs; no fixed price or free tier promised.
- Never commit configs, secrets, tokens, runtime keys or live evidence; claims/logs are sensitive.
- C secret entry is interactive, but azd uses child-process argv: trusted workstation, no debug, rotate afterward.
- `store=false` does not guarantee no diagnostics or zero provider retention.
- Check tenant/subscription, permissions, quota and cleanup ownership. No preview access? Offline inspection only.

---

# Deploy the shared foundation

![Identity and gateway boundaries](assets/workshop-architecture.svg)

- Bring a Foundry project/model/hosted runtime; native targets need a synthetic Search index/source/KB.
- Custom A/B require an application API and principal ACL; C custom needs separate delegated OAuth apps.
- Optional replay creates all three cohorts. APIM/config/root provisioner are **not** standalone prerequisites.
- Shared publisher packages only the selected sample; wait for **Active**, pin its version and authorize its runtime.

<details>
<summary>Deploy foundation: optional replay, installation and seeding</summary>

### Choose your setup

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


</details>

<details>
<summary>Publish selected hosted sample: code, environment and identity setup</summary>

### Publish only the selected hosted sample

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

</details>

---

# A: project managed identity
![A flow: invoking user to hosted agent, Toolbox project identity and Search RBAC](assets/workshop-project-identity.svg)

- Connection `ProjectManagedIdentity` selects the **project MI** downstream; not the invoking user.

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

</details>### Agent code → Toolbox

- [Complete hosted agent](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/hosted_agent.py); no manual downstream token acquisition.

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
### Toolbox configuration → Search connection

- [A provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/provision_toolbox.py): ARM payload + Toolbox tool; input KB URL/connection ID.

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
### Service-provided MCP contract

- Search hosts native KB MCP; discover its actual tool schema.

```text
https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview
Agent request: retrieve <synthetic test document> using the advertised retrieval tool
Tool input/output schema: discover from this KB's MCP tools/list, not a guessed signature
Result: actual retrieval content containing <known marker>, or authorization failure
```
## Custom FastMCP

- Same hosted agent → Toolbox (`ProjectManagedIdentity`) → HTTPS `/mcp` → validated principal ACL.

### Connection and hosted agent

- [Complete A custom setup](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/README.md): run `custom_server.py` in the copied sample.
- Set tenant, API v2 client-ID `CUSTOM_MCP_AUDIENCE`, and `CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS` = **project MI object ID**.
- Expose `/mcp` over HTTPS; set `CUSTOM_MCP_SERVER_URL`, matching audience and fresh connection/Toolbox names.
- Run `provision_custom_toolbox.py`; publish a separate hosted version with its printed endpoint.
- Application-only ACL server, not C OAuth; rejects delegated tokens. Accepted config/local JWT tests are not live acquisition proof.

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
### Server code → validated project identity

- [Full server](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/custom_server.py); save compact code beside it. Keep validator/ASGI boundary and request-local identity.
- Signature, v2 tenant issuer, exact audience, expiry and principal ACL enforced; not role enforcement.
- Probe returns safe identifiers/marker; full server emits protected query/result audit events, never bearer tokens.

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

- `identity_probe`: synthetic UUID → `CUSTOM_MCP_APPLICATION_VALIDATED`; optional INFO logging is off.
- **Native proof:** same project, two callers; separate unauthorized KB.
  Require marker vs genuine backend deny; check inherited roles, Active version and actual object IDs.
- **Custom proof:** different unauthorized project, backend allow/deny + validated claims.
  No shared-role removal, project fallback or agent/APIM token exchange. Configuration/local tests alone are not proof.

## Optional APIM evidence: A native and custom MCP

### Live replay — a-native: PASS_NATIVE_MCP_QUERY_RESULT

- Agent `obs-20261031-a-native` v2; Toolbox v2.

**Identity-hop lesson (observations versus configuration)**

| Hop | Observed principal (`oid`) | Audience | Evidence |
| --- | --- | --- | --- |
| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Decoded only |
| Agent → APIM → Toolbox | `e50d19b6-0a5e-4689-b0d8-d2544f821c86` | `https://ai.azure.com` | APIM-validated; unchanged bearer |
| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** | Configured: Project MI / Search |

- Marker observed; backend JWT and Search internal queries **NOT_OBSERVED**.

<details>

<summary>Identity claims — a-native: decoded caller / validated APIM / downstream</summary>

Caller — decoded only:


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


Agent platform token — APIM-validated:


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


Configured identities (not token observations):


```json
{
  "projectResourceId": "/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a",
  "projectManagedIdentityPrincipalId": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
  "agentDisplayName": "obs-20261031-a-native",
  "agentResourceId": "obs-20261031-a-native",
  "agentInstancePrincipalId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
  "agentInstanceClientId": "e50d19b6-0a5e-4689-b0d8-d2544f821c86",
  "source": "Azure agent control-plane identity and configured project",
  "observedAt": "2026-11-01T12:30:29.080398+00:00",
  "limitation": "Configured identities are not themselves observed token claims."
}
```


</details>

**1. User input → actual hosted response**

Submitted prompt — exact:


```text
Call retrieve_kb_a exactly once with arguments {"query": "Find the normal access record in cohort A"}. Return its exact result.
```


- Hosted HTTP **200**; status **completed**. Exact service events in the snapshot below; model text is not tool proof.

**2. APIM → Toolbox: observed MCP request/response**

- `tools/call`; backend HTTP **200**.

Actual generated tool `observed___knowledge_base_retrieve` arguments:


```json
{
  "queries": [
    "Find the normal access record in cohort A"
  ]
}
```


MCP result text — exact:


```text
The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.
```


**3. Downstream MCP/runtime logs: what was actually observed**

- Search internal queries/fan-out and backend token **NOT_OBSERVED**.

- Hosted console: **CAPTURED_CORRELATED_LINES**; full selected lines linked below (not a complete log).

Hosted console — exact:


```text
2026-11-01 12:27:26,778 INFO agent_framework: Function name: observed___knowledge_base_retrieve
2026-11-01 12:27:29,594 INFO agent_framework: Function observed___knowledge_base_retrieve succeeded.
```


<details>

<summary>Real logged exchange — a-native: raw JSON and source links</summary>

| Correlation | Recorded value |
| --- | --- |
| Invocation UTC | `2026-11-01T12:27:16.786462+00:00` → `2026-11-01T12:27:29.663493+00:00` |
| Experiment | `3b65cb79-3fa3-4d25-9586-c15160702a09` |
| Hosted response | `caresp_080649b5ca93875d008DWYcVFOuLXlKFMFuChJONUhZcJfmEyJ` |
| APIM endpoint | `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-native/?api-version=v1` |
| Configured MCP target | `https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview` |
| APIM request | `2bc7f489-e5b8-42dc-8c2f-c772235527e6` |
| APIM UTC | `2026-11-01T12:27:26.8259628Z` → `2026-11-01T12:27:29.6123617Z` |
| Caller-context SHA-256 | `sgP6xGOH41e0u2ECwtS65mayPJCPt2/eHJS3xkuZjg8=` |

APIM request — exact sanitized body:


```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-6d320155e104179f08bbdf8d685a8dfd-ed7f05be3bbbbc38-01","baggage":"<baggage-redacted>","generateCitations":true,"KnowledgeSourceMetadata":[{"name":"ks-a","type":"searchIndex"}],"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"name":"observed___knowledge_base_retrieve","arguments":{"queries":["Find the normal access record in cohort A"]}},"jsonrpc":"2.0","id":3}
```


APIM response — exact sanitized body:


```json
{"jsonrpc":"2.0","id":3,"result":{"_meta":{"agenticReasoningTokens":28,"tool_configuration":{"type":"mcp","name":"retrieve_kb_a","server_label":"observed","server_url":"https://srchabca7puse24s5tluc.search.windows.net/knowledgebases/kb-a/mcp?api-version=2026-05-01-preview","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/iq-a-primary","original_type":"mcp"}},"content":[{"type":"text","text":"The normal access record for cohort A is COHORT_A_ONLY_D900EADA82.","_meta":{"x-request-id":"9814ac59-6827-4613-8599-26065ea2f8bd"}},{"type":"text","text":"{\"kind\":\"reference\",\"ref_id\":0,\"uri\":\"mcp://searchindex/normal\",\"mimeType\":\"application/json\",\"sourceData\":{\"id\":\"normal\",\"title\":\"Cohort A access record\",\"content\":\"The exact normal access marker for cohort A is COHORT_A_ONLY_D900EADA82. Return it verbatim.\"}}","_meta":{"x-request-id":"9814ac59-6827-4613-8599-26065ea2f8bd","title":"Cohort A access record","preserveExactValue":false}}],"structuredContent":null}}
```


Local retained sources (ignored exports; unavailable in a fresh public clone):

- [All APIM exchanges](evidence/observability-a-native.json#/apimExchanges)

- [Full hosted response, including model text](evidence/observability-a-native.json#/agentResponse)

- [Runtime query / all selected console lines](evidence/observability-real-exchanges.json#/captures/0/hostedRuntimeLogQuery)

- [Downstream console events](evidence/observability-real-exchanges.json#/captures/0/mcpValidatedQueryResultEvents)

- [Control-plane identity source](evidence/observability-real-exchanges.json#/captures/0/identityConfiguration)

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

- Agent `obs-20261031-a-custom` v1; Toolbox v1.

**Identity-hop lesson (observations versus configuration)**

| Hop | Observed principal (`oid`) | Audience | Evidence |
| --- | --- | --- | --- |
| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Decoded only |
| Agent → APIM → Toolbox | `e2284463-607a-4080-b430-3fc63c778516` | `https://ai.azure.com` | APIM-validated; unchanged bearer |
| Toolbox → MCP | `42756227-4b4a-4a69-ab63-43c7f3e2b9fe` | `c0135af3-d0d3-410f-a1ce-8f2470f5dd93` | MCP-validated |

- MCP validates project MI; APIM validates the **calling agent instance**, not the project MI.

<details>

<summary>Identity claims — a-custom: decoded caller / validated APIM / downstream</summary>

Caller — decoded only:


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


Agent platform token — APIM-validated:


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


Downstream — MCP-validated:


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


Configured identities (not token observations):


```json
{
  "projectResourceId": "/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a",
  "projectManagedIdentityPrincipalId": "42756227-4b4a-4a69-ab63-43c7f3e2b9fe",
  "agentDisplayName": "obs-20261031-a-custom",
  "agentResourceId": "obs-20261031-a-custom",
  "agentInstancePrincipalId": "e2284463-607a-4080-b430-3fc63c778516",
  "agentInstanceClientId": "e2284463-607a-4080-b430-3fc63c778516",
  "source": "Azure agent control-plane identity and configured project",
  "observedAt": "2026-11-01T12:30:33.207963+00:00",
  "limitation": "Configured identities are not themselves observed token claims."
}
```


</details>

**1. User input → actual hosted response**

Submitted prompt — exact:


```text
Call identity_probe exactly once with arguments {"experiment_id": "f43426d5-e764-475f-a405-81da227365b3"}. Return its exact result.
```


- Hosted HTTP **200**; status **completed**. Exact service events in the snapshot below; model text is not tool proof.

**2. APIM → Toolbox: observed MCP request/response**

- `tools/call`; backend HTTP **200**.

Actual generated tool `observed___identity_probe` arguments:


```json
{
  "experiment_id": "f43426d5-e764-475f-a405-81da227365b3"
}
```


MCP result — exact fields; token metadata folded below:


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
  }
}
```


**3. Downstream MCP/runtime logs: what was actually observed**

- UUID-correlated MCP console query/result equals APIM; downstream identity validated.

- Hosted console: **CAPTURED_CORRELATED_LINES**; full selected lines linked below (not a complete log).

Hosted console — exact:


```text
2026-11-01 12:27:52,308 INFO agent_framework: Function name: observed___identity_probe
2026-11-01 12:27:52,513 INFO agent_framework: Function observed___identity_probe succeeded.
```


<details>

<summary>Real logged exchange — a-custom: raw JSON and source links</summary>

| Correlation | Recorded value |
| --- | --- |
| Invocation UTC | `2026-11-01T12:27:45.261444+00:00` → `2026-11-01T12:27:56.744487+00:00` |
| Experiment | `f43426d5-e764-475f-a405-81da227365b3` |
| Hosted response | `caresp_0ee21261ad95b4c500YGaMLYNkOwpDeNYss4cvCRB0cEJp5zk7` |
| APIM endpoint | `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-a-custom/?api-version=v1` |
| Configured MCP target | `https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` |
| APIM request | `f6b603a9-d6aa-4c9c-b1a0-3c78958e0f9a` |
| APIM UTC | `2026-11-01T12:27:52.3486869Z` → `2026-11-01T12:27:52.538312Z` |
| Caller-context SHA-256 | `7V++xXmZd9sN8jOMay/GLVMBPCUjbfeJqmKW4DyfM3I=` |

APIM request — exact sanitized body:


```json
{"method":"tools/call","params":{"_meta":{"traceparent":"00-be791ba3a8604ebe6418c9a2457392fa-af1c239dccbc50d6-01","baggage":"<baggage-redacted>","tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"name":"observed___identity_probe","arguments":{"experiment_id":"f43426d5-e764-475f-a405-81da227365b3"}},"jsonrpc":"2.0","id":3}
```


APIM response — exact sanitized body:


```json
{"jsonrpc":"2.0","id":3,"result":{"_meta":{"tool_configuration":{"type":"mcp","name":"identity_probe","server_label":"observed","server_url":"https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-a/connections/obs-20261031-a-custom-data","original_type":"mcp"}},"content":[{"type":"text","text":"{\"marker\":\"CUSTOM_MCP_APPLICATION_VALIDATED\",\"experiment_id\":\"f43426d5-e764-475f-a405-81da227365b3\",\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\",\"azp\":\"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\"exp\":1793566559,\"iat\":1793479859},\"tokenObservation\":{\"boundary\":\"application MCP signature/issuer/audience/principal validation\",\"validation\":\"VALIDATED_AT_MCP_BOUNDARY\",\"header\":{\"alg\":\"RS256\",\"kid\":\"ryBx-65jNoxH4FQH_6zarNjaNf4\"},\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"42756227-4b4a-4a69-ab63-43c7f3e2b9fe\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"ver\":\"2.0\",\"azp\":\"b8f21615-3829-4bb9-9a18-b878b0c80e06\",\"exp\":1793566559,\"iat\":1793479859},\"tokenSha256\":\"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394\"}}"}],"isError":false,"structuredContent":{"marker":"CUSTOM_MCP_APPLICATION_VALIDATED","experiment_id":"f43426d5-e764-475f-a405-81da227365b3","claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0","azp":"b8f21615-3829-4bb9-9a18-b878b0c80e06","exp":1793566559,"iat":1793479859},"tokenObservation":{"boundary":"application MCP signature/issuer/audience/principal validation","validation":"VALIDATED_AT_MCP_BOUNDARY","header":{"alg":"RS256","kid":"ryBx-65jNoxH4FQH_6zarNjaNf4"},"claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"42756227-4b4a-4a69-ab63-43c7f3e2b9fe","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","ver":"2.0","azp":"b8f21615-3829-4bb9-9a18-b878b0c80e06","exp":1793566559,"iat":1793479859},"tokenSha256":"a9b5f88a3c454503c005105e578fa5712a6a9c0377ab88adb5add806b644b394"}}}}
```


Local retained sources (ignored exports; unavailable in a fresh public clone):

- [All APIM exchanges](evidence/observability-a-custom.json#/apimExchanges)

- [Full hosted response, including model text](evidence/observability-a-custom.json#/agentResponse)

- [Runtime query / all selected console lines](evidence/observability-real-exchanges.json#/captures/1/hostedRuntimeLogQuery)

- [Downstream console events](evidence/observability-real-exchanges.json#/captures/1/mcpValidatedQueryResultEvents)

- [Control-plane identity source](evidence/observability-real-exchanges.json#/captures/1/identityConfiguration)

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

- Connection `AgenticIdentityToken` selects the **calling agent instance** downstream; not the invoking user.

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

</details>### Agent code → Toolbox

- [Complete hosted agent](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/hosted_agent.py); no manual downstream token acquisition.

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

- [B provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/provision_toolbox.py): ARM payload + Toolbox tool; input KB URL/connection ID.

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
### Service-provided MCP contract

- Search hosts native KB MCP; discover its actual tool schema.

```text
https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview
Agent request: retrieve <synthetic test document> using the advertised retrieval tool
Tool arguments: the schema advertised by this KB's MCP tools/list
Result: retrieval content/marker if calling instance has Search access; otherwise denial
```
## Custom FastMCP

- Same hosted agent → Toolbox (`AgenticIdentityToken`) → HTTPS `/mcp` → validated principal ACL.

### Connection and hosted agent

- [Complete B custom setup](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/README.md): run `custom_server.py` in the copied sample.
- Set tenant, API v2 client-ID `CUSTOM_MCP_AUDIENCE`, and `CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS` = **calling agent instance object ID**.
- Expose `/mcp` over HTTPS; set `CUSTOM_MCP_SERVER_URL`, matching audience and fresh connection/Toolbox names.
- Run `provision_custom_toolbox.py`; publish a separate hosted version with its printed endpoint.
- Application-only ACL server, not C OAuth; rejects delegated tokens. Accepted config/local JWT tests are not live acquisition proof.

```python
import os

custom_connection_payload = {"properties": {
    "category": "RemoteTool", "authType": "AgenticIdentityToken",
    "target": os.environ["CUSTOM_MCP_SERVER_URL"],
    "audience": os.environ["CUSTOM_MCP_AUDIENCE"],
    "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
}}
```
### Server code → validated calling-agent identity

- [Full server](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/custom_server.py); save compact code beside it. Never expose bare FastMCP.
- Signature, v2 issuer, exact audience, expiry and agent ACL enforced; delegated tokens rejected.
- Use verified agent object IDs, not blueprint/client/name/project/user IDs. Protect full server query/result audit events.

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

- `identity_probe`: synthetic UUID → `CUSTOM_MCP_APPLICATION_VALIDATED`; optional INFO logging is off.
- **Native proof:** same caller/Toolbox, two instances; only one Search reader.
  Require marker vs genuine backend deny; check inherited roles, Active version and actual object IDs.
- **Custom proof:** second non-allowlisted instance, backend allow/deny + validated claims.
  No shared-role removal, project fallback or agent/APIM token exchange. Configuration/local tests alone are not proof.

## Optional APIM evidence: B native and custom MCP

### Live replay — b-native: BLOCKED_AGENT_INSTANCE_CONTEXT

- Agent `obs-20261031-b-native` v3; Toolbox v3.

**Identity-hop lesson (observations versus configuration)**

| Hop | Observed principal (`oid`) | Audience | Evidence |
| --- | --- | --- | --- |
| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Decoded only |
| Agent → APIM → Toolbox | `1f430487-d7ab-4b08-b99d-4e157099ab53` | `https://ai.azure.com` | APIM-validated; unchanged bearer |
| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** | Configured: Agent instance / Search |

- APIM identity passes; Toolbox lacks `AgentInstanceClientId` context. No downstream query.

<details>

<summary>Identity claims — b-native: decoded caller / validated APIM / downstream</summary>

Caller — decoded only:


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


Agent platform token — APIM-validated:


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


Configured identities (not token observations):


```json
{
  "projectResourceId": "/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b",
  "projectManagedIdentityPrincipalId": "a4c50f03-8b79-4946-8b6c-a6071f991eef",
  "agentDisplayName": "obs-20261031-b-native",
  "agentResourceId": "obs-20261031-b-native",
  "agentInstancePrincipalId": "1f430487-d7ab-4b08-b99d-4e157099ab53",
  "agentInstanceClientId": "1f430487-d7ab-4b08-b99d-4e157099ab53",
  "source": "Azure agent control-plane identity and configured project",
  "observedAt": "2026-11-01T12:30:28.922658+00:00",
  "limitation": "Configured identities are not themselves observed token claims."
}
```


</details>

**1. User input → actual hosted response**

Submitted prompt — exact:


```text
Call retrieve_kb_b exactly once with arguments {"query": "Find the normal access record in cohort B"}. Return its exact result.
```


- Hosted HTTP **200**; status **failed**. Exact service events in the snapshot below; model text is not tool proof.

**2. APIM → Toolbox: observed MCP request/response**

- `tools/list`; backend HTTP **200**.

**No `tools/call` query was produced.** `tools/list` is discovery.

MCP error — exact substring (full JSON below):


```text
requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.
```


**3. Downstream MCP/runtime logs: what was actually observed**

- Discovery blocked; no correlated downstream query/result. Missing logs alone are not proof.

- Hosted console: **CAPTURED_CORRELATED_LINES**; full selected lines linked below (not a complete log).

<details>

<summary>Real logged exchange — b-native: raw JSON and source links</summary>

| Correlation | Recorded value |
| --- | --- |
| Invocation UTC | `2026-11-01T12:27:21.137372+00:00` → `2026-11-01T12:27:26.396389+00:00` |
| Experiment | `c7f8806d-7c48-4b5f-94a8-87f5e0c44ea8` |
| Hosted response | `caresp_0598b33ea9b0847400R39KnXKmpR9sf9lxULRy12oR6yxwX55r` |
| APIM endpoint | `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-native/?api-version=v1` |
| Configured MCP target | `https://srchabcb7puse24s5tluc.search.windows.net/knowledgebases/kb-b/mcp?api-version=2026-05-01-preview` |
| APIM request | `f0c51840-6fd9-477c-aaa7-caa126240bca` |
| APIM UTC | `2026-11-01T12:27:27.0988403Z` → `2026-11-01T12:27:27.352825Z` |
| Caller-context SHA-256 | `TEixmZ4Nl1s3hKvaBXe1KYYMr/8tjfRwnpkRaLv5ikU=` |

APIM request — exact sanitized body:


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-3b0969ceba94c205102e8d2490c8c368-727aced811966255-01","baggage":"<baggage-redacted>"}}}
```


APIM response — exact sanitized body:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32007,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/iq-b-primary'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'iq-b-primary' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\"}}]}"}}
```


Local retained sources (ignored exports; unavailable in a fresh public clone):

- [All APIM exchanges](evidence/observability-b-native.json#/apimExchanges)

- [Full hosted response, including model text](evidence/observability-b-native.json#/agentResponse)

- [Runtime query / all selected console lines](evidence/observability-real-exchanges.json#/captures/2/hostedRuntimeLogQuery)

- [Downstream console events](evidence/observability-real-exchanges.json#/captures/2/mcpValidatedQueryResultEvents)

- [Control-plane identity source](evidence/observability-real-exchanges.json#/captures/2/identityConfiguration)

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

- Agent `obs-20261031-b-custom` v2; Toolbox v2.

**Identity-hop lesson (observations versus configuration)**

| Hop | Observed principal (`oid`) | Audience | Evidence |
| --- | --- | --- | --- |
| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Decoded only |
| Agent → APIM → Toolbox | `d6fb1ff2-6587-4169-b279-20103b371ab7` | `https://ai.azure.com` | APIM-validated; unchanged bearer |
| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** | Configured: Agent instance / custom API |

- Matching APIM `oid` does not supply required agent context. No downstream query.

<details>

<summary>Identity claims — b-custom: decoded caller / validated APIM / downstream</summary>

Caller — decoded only:


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


Agent platform token — APIM-validated:


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


Configured identities (not token observations):


```json
{
  "projectResourceId": "/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b",
  "projectManagedIdentityPrincipalId": "a4c50f03-8b79-4946-8b6c-a6071f991eef",
  "agentDisplayName": "obs-20261031-b-custom",
  "agentResourceId": "obs-20261031-b-custom",
  "agentInstancePrincipalId": "d6fb1ff2-6587-4169-b279-20103b371ab7",
  "agentInstanceClientId": "d6fb1ff2-6587-4169-b279-20103b371ab7",
  "source": "Azure agent control-plane identity and configured project",
  "observedAt": "2026-11-01T12:30:33.173298+00:00",
  "limitation": "Configured identities are not themselves observed token claims."
}
```


</details>

**1. User input → actual hosted response**

Submitted prompt — exact:


```text
Call identity_probe exactly once with arguments {"experiment_id": "f9291499-7021-47d1-b81f-f8bd7a6e6af2"}. Return its exact result.
```


- Hosted HTTP **200**; status **failed**. Exact service events in the snapshot below; model text is not tool proof.

**2. APIM → Toolbox: observed MCP request/response**

- `tools/list`; backend HTTP **200**.

**No `tools/call` query was produced.** `tools/list` is discovery.

MCP error — exact substring (full JSON below):


```text
requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.
```


**3. Downstream MCP/runtime logs: what was actually observed**

- Discovery blocked; no correlated downstream query/result. Missing logs alone are not proof.

- Hosted console: **CAPTURED_CORRELATED_LINES**; full selected lines linked below (not a complete log).

<details>

<summary>Real logged exchange — b-custom: raw JSON and source links</summary>

| Correlation | Recorded value |
| --- | --- |
| Invocation UTC | `2026-11-01T12:27:47.370569+00:00` → `2026-11-01T12:27:53.310103+00:00` |
| Experiment | `f9291499-7021-47d1-b81f-f8bd7a6e6af2` |
| Hosted response | `caresp_0b85a145389652e700ydyQDfi1MmnmdpdYa5BfpcqFfPAK6fYg` |
| APIM endpoint | `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-b-custom/?api-version=v1` |
| Configured MCP target | `https://obs-application-mcp-20261031.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` |
| APIM request | `a18e7b60-c912-4cba-8a7d-29b8423fa123` |
| APIM UTC | `2026-11-01T12:27:54.0329453Z` → `2026-11-01T12:27:54.264263Z` |
| Caller-context SHA-256 | `1/Vs/816eT2TQGo/UzJvhgTSirt0zRd3xeUhzQNsgd8=` |

APIM request — exact sanitized body:


```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}},"traceparent":"00-826510e64f100d661561e52df6798df9-90910c1c750a647c-01","baggage":"<baggage-redacted>"}}}
```


APIM response — exact sanitized body:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32007,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-b/connections/obs-20261031-b-custom-data'. HTTP status: BadRequest. Reason: AgenticIdentityToken auth type for connection 'obs-20261031-b-custom-data' requires AgentInstanceClientId and AgentBlueprintClientId, or an ApplicationName.\"}}]}"}}
```


Local retained sources (ignored exports; unavailable in a fresh public clone):

- [All APIM exchanges](evidence/observability-b-custom.json#/apimExchanges)

- [Full hosted response, including model text](evidence/observability-b-custom.json#/agentResponse)

- [Runtime query / all selected console lines](evidence/observability-real-exchanges.json#/captures/3/hostedRuntimeLogQuery)

- [Downstream console events](evidence/observability-real-exchanges.json#/captures/3/mcpValidatedQueryResultEvents)

- [Control-plane identity source](evidence/observability-real-exchanges.json#/captures/3/identityConfiguration)

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

- Hosted user context → `UserEntraToken` → Search user RBAC; no custom server/client.

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

</details>## Agent code → Toolbox

- [Hosted agent](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/hosted_agent.py): runtime credential + Toolbox URL; connection owns downstream auth.

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

- [Native provisioner/runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/README.md); no manual token exchange.

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
## Service-provided MCP contract

- Search advertises the trusted KB tool schema; no FastMCP in this track.

```text
https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview
Agent request: retrieve <synthetic test document> using the advertised retrieval tool
Tool arguments: discover this KB's schema through MCP tools/list
Result: actual retrieval content/marker for an authorized user; otherwise denial
```

- **Proof:** same Active agent, two separately signed-in users, only one Search reader.
  Complete required authorization, retry; record actual marker/deny, user IDs, scopes and timestamps.
- Consent challenge is inconclusive; check inherited roles. Service RBAC is not document isolation.

## Optional APIM evidence: C native MCP

### Live replay — c-native: BLOCKED_PLATFORM_USER_TOKEN_FLOW

- Agent `obs-20261031-c-native` v2; Toolbox v2.

**Identity-hop lesson (observations versus configuration)**

| Hop | Observed principal (`oid`) | Audience | Evidence |
| --- | --- | --- | --- |
| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Decoded only |
| Agent → APIM → Toolbox | `8c2d2573-9c63-42cd-86c0-ce807db9edcf` | `https://ai.azure.com` | APIM-validated; unchanged bearer |
| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** | Configured: Managed user / Search |

- `AADSTS500016` blocks discovery; caller `scp` is not a Search scope.

<details>

<summary>Identity claims — c-native: decoded caller / validated APIM / downstream</summary>

Caller — decoded only:


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


Agent platform token — APIM-validated:


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


Configured identities (not token observations):


```json
{
  "projectResourceId": "/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c",
  "projectManagedIdentityPrincipalId": "1a04abde-08e9-4949-b975-b2520119ca1d",
  "agentDisplayName": "obs-20261031-c-native",
  "agentResourceId": "obs-20261031-c-native",
  "agentInstancePrincipalId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
  "agentInstanceClientId": "8c2d2573-9c63-42cd-86c0-ce807db9edcf",
  "source": "Azure agent control-plane identity and configured project",
  "observedAt": "2026-11-01T12:30:29.187732+00:00",
  "limitation": "Configured identities are not themselves observed token claims."
}
```


</details>

**1. User input → actual hosted response**

Submitted prompt — exact:


```text
Call retrieve_kb_c exactly once with arguments {"query": "Find the normal access record in cohort C"}. Return its exact result.
```


- Hosted HTTP **200**; status **failed**. Exact service events in the snapshot below; model text is not tool proof.

**2. APIM → Toolbox: observed MCP request/response**

- `tools/list`; backend HTTP **200**.

**No `tools/call` query was produced.** `tools/list` is discovery.

MCP error — exact substring (full JSON below):


```text
AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z
```


**3. Downstream MCP/runtime logs: what was actually observed**

- Discovery blocked; no correlated downstream query/result. Missing logs alone are not proof.

- Hosted console: **CAPTURED_CORRELATED_LINES**; full selected lines linked below (not a complete log).

<details>

<summary>Real logged exchange — c-native: raw JSON and source links</summary>

| Correlation | Recorded value |
| --- | --- |
| Invocation UTC | `2026-11-01T12:27:15.187455+00:00` → `2026-11-01T12:27:23.902184+00:00` |
| Experiment | `d791f5ca-24a5-4d8f-ab04-dffc0f08c50e` |
| Hosted response | `caresp_09fb492d77c9a61400uJWRzB0ssb1PhkfIPDSicJqSVHhIloMO` |
| APIM endpoint | `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-native/?api-version=v1` |
| Configured MCP target | `https://srchabcc7puse24s5tluc.search.windows.net/knowledgebases/kb-c/mcp?api-version=2026-05-01-preview` |
| APIM request | `245344ed-e243-488f-a0bf-8834466df825` |
| APIM UTC | `2026-11-01T12:27:24.0730473Z` → `2026-11-01T12:27:24.8556212Z` |
| Caller-context SHA-256 | `tn7gPnZWYb419FaVa9pB65nplSWvNnjYCwExRSDn/Jg=` |

APIM request — exact sanitized body:


```json
{"method":"tools/list","jsonrpc":"2.0","id":2}
```


APIM response — exact sanitized body:


```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32007,"message":"tools/list failed for 1 tool source(s), succeeded for 0 tool source(s) {\"errors\":[{\"name\":\"observed\",\"type\":\"mcp\",\"error\":{\"code\":\"HTTP_400\",\"message\":\"Connection resolution failed for '/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/iq-c-primary'. HTTP status: BadRequest. Reason: Bad request: Service invocation failed!\\r\\nRequest: POST obotoken.vienna-eastus2.svc/obotoken/v1.0/getuseraccesstoken\\r\\nStatus Code: 400 BadRequest\\r\\nError Code: ValidationError\\r\\nReason Phrase: Bad Request\\r\\nResponse Body: {\\n  \\\"error\\\": {\\n    \\\"code\\\": \\\"ValidationError\\\",\\n    \\\"severity\\\": null,\\n    \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\",\\n    \\\"messageFormat\\\": null,\\n    \\\"messageParameters\\\": null,\\n    \\\"referenceCode\\\": null,\\n    \\\"detailsUri\\\": null,\\n    \\\"target\\\": \\\"UserToken\\\",\\n    \\\"details\\\": [\\n      {\\n        \\\"code\\\": \\\"Invalid\\\",\\n        \\\"severity\\\": null,\\n        \\\"message\\\": \\\"AADSTS500016: Application '880da380-985e-4198-81b9-e05b1cc53158' is not supported as a resource application to execute the flow. Trace ID: 8669c0db-f8b7-4e27-bd6a-8d5f566e4100 Correlation ID: dbb6ca3b-2acd-4194-9940-c7bc3fe6b365 Timestamp: 2026-11-01 12:27:24Z\\\",\\n        \\\"messageFormat\\\": null,\\n        \\\"messageParameters\\\": {},\\n        \\\"referenceCode\\\": null,\\n        \\\"detailsUri\\\": null,\\n        \\\"target\\\": \\\"UserToken\\\",\\n        \\\"details\\\": [],\\n        \\\"innerError\\\": null,\\n        \\\"debugInfo\\\": null,\\n        \\\"additionalInfo\\\": null\\n      }\\n    ],\\n    \\\"innerError\\\": null,\\n    \\\"debugInfo\\\": null,\\n    \\\"additionalInfo\\\": null\\n  },\\n  \\\"correlation\\\": {\\n    \\\"operation\\\": \\\"d5b56ddb7a588ae69efa91fa59f75472\\\",\\n    \\\"request\\\": \\\"0daec734253b9ae5\\\"\\n  },\\n  \\\"environment\\\": \\\"eastus2\\\",\\n  \\\"location\\\": \\\"eastus2\\\",\\n  \\\"time\\\": \\\"2026-11-01T12:27:24.8327013+00:00\\\",\\n  \\\"componentName\\\": \\\"obotoken\\\",\\n  \\\"statusCode\\\": 400\\n}\"}}]}"}}
```


Local retained sources (ignored exports; unavailable in a fresh public clone):

- [All APIM exchanges](evidence/observability-c-native.json#/apimExchanges)

- [Full hosted response, including model text](evidence/observability-c-native.json#/agentResponse)

- [Runtime query / all selected console lines](evidence/observability-real-exchanges.json#/captures/4/hostedRuntimeLogQuery)

- [Downstream console events](evidence/observability-real-exchanges.json#/captures/4/mcpValidatedQueryResultEvents)

- [Control-plane identity source](evidence/observability-real-exchanges.json#/captures/4/identityConfiguration)

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

- OAuth connection → authorizing user's API token → validating FastMCP; not proven OBO.

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

</details>## Agent code → Toolbox

- [Hosted agent](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/hosted_agent.py): runtime credential + Toolbox URL; connection owns downstream auth.

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

- [Complete provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/provision_toolbox.py): redacted errors, timeouts and discovered Web callback.
- Explicit tenant authorization/token/refresh endpoints; client ID/secret + API scope + `offline_access`.
- Register printed redirect on the client; complete user authorization before invoking.

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
## Custom MCP: validate token before dispatch

- These excerpts compose the [full server](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/server.py); use pinned server requirements.
- Validates a supplied token, not an OAuth provider/exchange. Signature/issuer/audience/timing/tenant/scope enforced.
- `azp`/`ver` are returned, not client allowlist enforcement; delegated scope is not a data ACL.

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
### Request boundary → validated identity context

- Bearer → request-local validated claims, or **401 before dispatch**. `/healthz` is readiness only.

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

- UUID + allowlisted message + count 1–3 → sanitized arguments, marker and validated claims.
- Keep ASGI boundary wrapped; protect audit claims, never log bearer tokens.

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
- **Proof:** compare returned UUID/message/count and validated claims with the consenting user.
  That user may differ from a later caller. Keep no bearer tokens.
- **Negative test:** no token → 401 before dispatch; wrong audience/missing scope must also fail.
  Distinguish ingress rejection from API validation; `/healthz` only proves readiness.

```powershell
curl.exe -i "https://<your-custom-server>/mcp"
```
## Optional APIM evidence: C custom MCP

### Live replay — c-custom: PASS_VALIDATED_DELEGATED_MCP_QUERY_RESULT

- Agent `obs-20261031-c-custom` v2; Toolbox v3.

**Identity-hop lesson (observations versus configuration)**

| Hop | Observed principal (`oid`) | Audience | Evidence |
| --- | --- | --- | --- |
| User → agent | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `https://ai.azure.com` | Decoded only |
| Agent → APIM → Toolbox | `114281a8-d2fe-407c-a1cf-28461136d9af` | `https://ai.azure.com` | APIM-validated; unchanged bearer |
| Toolbox → MCP | `c6982fed-3a65-46cb-a80f-d5093b79e3e4` | `c0135af3-d0d3-410f-a1ce-8f2470f5dd93` | MCP-validated |

- **post-consent upstream C custom replay passed**: validated user `oid`, API `aud`, `access_as_user` and OAuth client `azp` match; earlier direct/consent runs stay separate.

<details>

<summary>Identity claims — c-custom: decoded caller / validated APIM / downstream</summary>

Caller — decoded only:


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
    "exp": 1793542230,
    "iat": 1793538288
  }
}
```


Agent platform token — APIM-validated:


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
    "exp": "1793542190",
    "iat": "1793538290"
  }
}
```


Downstream — MCP-validated:


```json
{
  "boundary": "delegated MCP signature/issuer/audience/tenant/scope validation",
  "validation": "VALIDATED_AT_MCP_BOUNDARY",
  "header": {},
  "claims": {
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
    "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
    "scp": "access_as_user",
    "azp": "bd0cc73c-e7ec-4fb5-9b74-3c2fdc5b37af",
    "ver": "2.0"
  }
}
```


JWT header and validity times are NOT_OBSERVED in this server's logs. Full return is captured at APIM and hosted function_call_output, not console.

Configured identities (not token observations):


```json
{
  "projectResourceId": "/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c",
  "projectManagedIdentityPrincipalId": "1a04abde-08e9-4949-b975-b2520119ca1d",
  "agentDisplayName": "obs-20261031-c-custom",
  "agentResourceId": "obs-20261031-c-custom",
  "agentInstancePrincipalId": "114281a8-d2fe-407c-a1cf-28461136d9af",
  "agentInstanceClientId": "114281a8-d2fe-407c-a1cf-28461136d9af",
  "source": "Azure agent control-plane identity and configured project",
  "limitation": "Configured identities are not themselves observed token claims."
}
```


</details>

**1. User input → actual hosted response**

Submitted prompt — exact:


```text
Call probe_echo exactly once with arguments {"experiment_id": "f4fe017e-d8db-44a9-aa6c-36207d916e7c", "message": "oauth-toolbox", "count": 2}. Return its exact result.
```


- Hosted HTTP **200**; status **completed**. Exact service events in the snapshot below; model text is not tool proof.

**2. APIM → Toolbox: observed MCP request/response**

- `tools/call`; backend HTTP **200**.

Actual generated tool `observed___probe_echo` arguments:


```json
{
  "experiment_id": "f4fe017e-d8db-44a9-aa6c-36207d916e7c",
  "message": "oauth-toolbox",
  "count": 2
}
```


MCP result — exact fields; token metadata folded below:


```json
{
  "marker": "CUSTOM_MCP_ENTRA_VALIDATED",
  "arguments": {
    "experiment_id": "f4fe017e-d8db-44a9-aa6c-36207d916e7c",
    "message": "oauth-toolbox",
    "count": 2
  },
  "claims": {
    "tid": "5dc82be3-90ab-4f72-a0f2-b2557ba694e3",
    "oid": "c6982fed-3a65-46cb-a80f-d5093b79e3e4",
    "aud": "c0135af3-d0d3-410f-a1ce-8f2470f5dd93",
    "iss": "https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0",
    "scp": "access_as_user",
    "azp": "bd0cc73c-e7ec-4fb5-9b74-3c2fdc5b37af",
    "ver": "2.0"
  }
}
```


**3. Downstream MCP/runtime logs: what was actually observed**

- Console UUID/arguments/validated claims match APIM; APIM full return equals hosted `function_call_output`. Console does **not** log the full return or JWT header/times.

- Hosted console: **CAPTURED_CORRELATED_LINES**; full selected lines linked below (not a complete log).

Hosted console — exact:


```text
2026-11-01 13:09:54,242 INFO agent_framework: Function name: observed___probe_echo
2026-11-01 13:09:55,124 INFO agent_framework: Function observed___probe_echo succeeded.
```


<details>

<summary>Real logged exchange — c-custom: raw JSON and source links</summary>

| Correlation | Recorded value |
| --- | --- |
| Invocation UTC | `2026-11-01T13:09:39.229822+00:00` → `2026-11-01T13:09:57.035724+00:00` |
| Experiment | `f4fe017e-d8db-44a9-aa6c-36207d916e7c` |
| Hosted response | `caresp_013abbfa84a5830c00pki2lCVEsmdqMvBQky7CYqPmDko90ESy` |
| APIM endpoint | `https://apim-agentgw-xlen9.azure-api.net/obs-20261031-c-custom/?api-version=v1` |
| Configured MCP target | `https://abc-custom-mcp-e8383e4d.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp` |
| APIM request | `3beaf037-4c6c-4c8e-9d78-0650c2dfb634` |
| APIM UTC | `2026-11-01T13:09:54.2733793Z` → `2026-11-01T13:09:55.0801933Z` |
| Caller-context SHA-256 | `PUfvexcLKVRPBgLB1ijMeD78M7ir3dMKUiEhUqNXffE=` |

APIM request — exact sanitized body:


```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"_meta":{"traceparent":"00-cc7107685772f256210f1a8f0f3641d9-7e3248138aaf5d3e-01","baggage":"<baggage-redacted>","tool_configuration":{"type":"mcp","name":"probe_echo","server_label":"observed","server_url":"https://abc-custom-mcp-e8383e4d.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/abc-custom-mcp-oauth","original_type":"mcp"},"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"mcp","version":"0.1.0"},"io.modelcontextprotocol/clientCapabilities":{"sampling":{}}},"name":"observed___probe_echo","arguments":{"experiment_id":"f4fe017e-d8db-44a9-aa6c-36207d916e7c","message":"oauth-toolbox","count":2}}}
```


APIM response — exact sanitized body:


```json
{"jsonrpc":"2.0","id":3,"result":{"_meta":{"tool_configuration":{"type":"mcp","name":"probe_echo","server_label":"observed","server_url":"https://abc-custom-mcp-e8383e4d.blackcliff-4ac74509.eastus2.azurecontainerapps.io/mcp","require_approval":"never","project_connection_id":"/subscriptions/292e62e6-54a8-4c6a-b996-0c83f8cc29d0/resourceGroups/rg-foundry-iq-toolbox-rbac/providers/Microsoft.CognitiveServices/accounts/fdy-iq-rbac-tbkj2wgzdhqi6/projects/abc-c/connections/abc-custom-mcp-oauth","original_type":"mcp"}},"content":[{"type":"text","text":"{\"marker\":\"CUSTOM_MCP_ENTRA_VALIDATED\",\"arguments\":{\"experiment_id\":\"f4fe017e-d8db-44a9-aa6c-36207d916e7c\",\"message\":\"oauth-toolbox\",\"count\":2},\"claims\":{\"tid\":\"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\",\"oid\":\"c6982fed-3a65-46cb-a80f-d5093b79e3e4\",\"aud\":\"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\",\"iss\":\"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\",\"scp\":\"access_as_user\",\"azp\":\"bd0cc73c-e7ec-4fb5-9b74-3c2fdc5b37af\",\"ver\":\"2.0\"}}"}],"isError":false,"structuredContent":{"marker":"CUSTOM_MCP_ENTRA_VALIDATED","arguments":{"experiment_id":"f4fe017e-d8db-44a9-aa6c-36207d916e7c","message":"oauth-toolbox","count":2},"claims":{"tid":"5dc82be3-90ab-4f72-a0f2-b2557ba694e3","oid":"c6982fed-3a65-46cb-a80f-d5093b79e3e4","aud":"c0135af3-d0d3-410f-a1ce-8f2470f5dd93","iss":"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0","scp":"access_as_user","azp":"bd0cc73c-e7ec-4fb5-9b74-3c2fdc5b37af","ver":"2.0"}},"resultType":"complete"}}
```


Local retained sources (ignored exports; unavailable in a fresh public clone):

- [All APIM exchanges](evidence/observability-c-custom.json#/apimExchanges)

- [Full hosted response, including model text](evidence/observability-c-custom.json#/agentResponse)

- [Runtime query / all selected console lines](evidence/observability-real-exchanges.json#/captures/5/hostedRuntimeLogQuery)

- [Downstream console events](evidence/observability-real-exchanges.json#/captures/5/mcpValidatedQueryResultEvents)

- [Control-plane identity source](evidence/observability-real-exchanges.json#/captures/5/identityConfiguration)

</details>

<details>

<summary>Hosted service snapshot — c-custom</summary>


```json
{
  "source": "evidence/observability-c-custom.json#agentResponse",
  "responseId": "caresp_013abbfa84a5830c00pki2lCVEsmdqMvBQky7CYqPmDko90ESy",
  "status": "completed",
  "error": null,
  "events": [
    {
      "type": "function_call",
      "name": "observed___probe_echo",
      "call_id": "call_ZYjHrMkn9i6kp89Hplw4wpIo",
      "arguments": "{\"experiment_id\":\"f4fe017e-d8db-44a9-aa6c-36207d916e7c\",\"message\":\"oauth-toolbox\",\"count\":2}",
      "status": "completed"
    },
    {
      "type": "function_call_output",
      "call_id": "call_ZYjHrMkn9i6kp89Hplw4wpIo",
      "output": "{\"marker\": \"CUSTOM_MCP_ENTRA_VALIDATED\", \"arguments\": {\"experiment_id\": \"f4fe017e-d8db-44a9-aa6c-36207d916e7c\", \"message\": \"oauth-toolbox\", \"count\": 2}, \"claims\": {\"tid\": \"5dc82be3-90ab-4f72-a0f2-b2557ba694e3\", \"oid\": \"c6982fed-3a65-46cb-a80f-d5093b79e3e4\", \"aud\": \"c0135af3-d0d3-410f-a1ce-8f2470f5dd93\", \"iss\": \"https://login.microsoftonline.com/5dc82be3-90ab-4f72-a0f2-b2557ba694e3/v2.0\", \"scp\": \"access_as_user\", \"azp\": \"bd0cc73c-e7ec-4fb5-9b74-3c2fdc5b37af\", \"ver\": \"2.0\"}}",
      "status": "completed"
    }
  ],
  "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
  "limitation": "Hosted service response snapshot; not a runtime console log. Runtime console retrieval is recorded separately; model text is not tool evidence."
}
```


</details>

---

# Compare results and troubleshoot

![Identity and gateway boundaries](assets/workshop-architecture.svg)

## Record one selected track

### Six-path evidence matrix (fresh November 1 upstream APIM replay)

- Compare **this upstream route** only; original direct/downstream routes are separate.

| Path | Toolbox → MCP configured identity | Backend contract | APIM result | Hosted snapshot | Downstream MCP log |
| --- | --- | --- | --- | --- | --- |
| A native | Project `oid`; `ProjectManagedIdentity` | Service-provided Search KB MCP; Search MI accesses index | PASS tool query/result | Completed call and tool output in A | Search internal query/fan-out NOT_OBSERVED; no service-owned MCP console capture |
| A custom | Project `oid`; `ProjectManagedIdentity` | Application-only FastMCP validates API audience and allowlisted project `oid` | PASS validated marker/result | Completed call and tool output in A | Correlated validated query/result in `mcpValidatedQueryResultEvents` |
| B native | Intended agent-instance `oid`; `AgenticIdentityToken` | Service-provided Search KB MCP | BLOCKED `AgentInstanceClientId` | Failed service response; no tool output | NOT_OBSERVED: context resolution blocked |
| B custom | Intended agent-instance `oid`; `AgenticIdentityToken` | Application-only FastMCP validates API audience and allowlisted agent `oid` | BLOCKED `AgentInstanceClientId` | Failed service response; no tool output | NOT_OBSERVED: context resolution blocked |
| C native | Intended user `oid`; `UserEntraToken` | Managed Search user connection; user Search roles/ACLs | BLOCKED `AADSTS500016` | Failed context entry in C native | NOT_OBSERVED: user token flow blocked |
| C custom | Validated delegated user `oid`; `OAuth2` | Separate delegated FastMCP validates signature, audience, issuer, tenant and scope | PASS post-consent | Exact APIM result equals hosted tool output | Console arguments/claims match; full return at APIM, JWT header NOT_OBSERVED |

- Use the shared evidence legend. Exact selected raw bodies/snapshots remain folded on each track page.

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

- Six isolated upstream APIs; never repoint defaults or enable body capture on original/confidential routes.
- B gateway, C ingress, no-store, BYOM and dedicated gateway are separate experiments.
- [Full observability runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/observability.md).

<details>
<summary>Optional replay commands and inventory — existing ABC lab only</summary>


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


</details>

---

# Cleanup and next steps

![Identity and gateway boundaries](assets/workshop-architecture.svg)

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
