---
published: true
type: workshop
title: Choose your Foundry agent identity with Toolbox and AI Gateway
short_title: Foundry identity lab
description: Deploy a shared lab foundation, then independently explore project identity, agent identity, managed user access, or custom OAuth with real authorization evidence.
level: advanced
authors:
  - Yael El Ghali
contacts:
  - https://github.com/yelghali
duration_minutes: 150
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
  - Evidence and optional gateway extension
  - Cleanup and next steps
---

# Welcome: choose the identity your workload needs

Build a Microsoft Foundry hosted agent that calls tools through Toolbox. Your
goal is not simply a plausible answer: demonstrate **which principal is authorized
at the data boundary**, and prove that an unauthorized principal cannot retrieve it.

This workshop uses the [implementation repository](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway).
Clone it locally for commands; MOAW is the reading experience, not an execution environment.
The sample folders are independently copyable and do not import the root lab.

## Learning outcomes

- Separate the invoking user, hosting identity, connection identity and data principal.
- Deploy and inspect Search, Foundry projects and telemetry without overwriting an unrelated lab.
- Provision one connection type, publish a hosted agent, and invoke a pinned Active version.
- Collect allow/deny evidence without confusing a marker, consent challenge or health check with authorization.
- Explain why delegated identity does not by itself prove a JWT-bearer OBO exchange.

## Pick one independent track

| Need | Track | Data principal | Budget after setup |
| --- | --- | --- | --- |
| All agents in a project share a trusted KB | A | Project managed identity | 45 minutes |
| Each agent has separate data access | B | Calling agent instance identity | 60 minutes |
| Search access must follow the signed-in user | C native | User via managed `UserEntraToken` | 60 minutes |
| A custom API uses delegated OAuth scopes | C custom | User completing OAuth connection consent | 75 minutes |

Allow approximately 60–90 minutes for shared setup and evidence/cleanup, plus Azure
deployment and RBAC propagation. The 150-minute estimate is **one track**, not all four.
You may use existing project/KB infrastructure and skip foundation deployment if it meets
your track's prerequisites. C custom requires no Search KB. Tracks are alternatives,
not sequential exercises.

**Checkpoint:** write down your chosen track, expected data principal, token
audience and a negative test before creating any resources.

---

# Architecture: where authorization actually happens

![Toolbox identity and gateway boundaries](assets/workshop-architecture.svg)

1. The local caller signs into Entra and invokes an agent using an
   `https://ai.azure.com/.default` token.
2. The hosted runtime uses `FoundryChatClient` for the model and `FoundryToolbox`
   for tools; `ResponsesHostServer` supplies hosted context.
3. Toolbox selects the connection's authentication mechanism. An ARM token used
   to provision that connection is **not** the downstream data token.
4. Search or your custom API validates the downstream token and authorization.
5. APIM can mediate ingress or downstream calls, but a gateway is not a replacement
   for correct audience, identity and backend permissions.

| Track | Connection authentication | Downstream audience | Boundary |
| --- | --- | --- | --- |
| A | `ProjectManagedIdentity` | `https://search.azure.com` | Search service RBAC |
| B | `AgenticIdentityToken` | `https://search.azure.com` | Calling agent's Search RBAC |
| C native | `UserEntraToken` | `https://search.azure.com` | User's Search RBAC |
| C custom | OAuth2 authorization code + refresh | Custom API v2 audience | Delegated scope and API validation |

**User OBO terminology:** the native trusted-KB path uses platform-managed user
context. These samples do not implement or capture a token exchange. The custom
OAuth path uses authorization code and `offline_access`, not demonstrated
JWT-bearer OBO. A user `oid` proves delegated identity, not grant type.

The full [reference architecture](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/architecture.svg)
also includes prompt agents, raw Search tools and gateway routes. Those are extensions,
not requirements for the independent hosted tracks.

**Exercise:** explain why granting the invoking developer Search access does not
fix B when the calling agent lacks its data role.

---

# Prerequisites, permissions and safety

Use a dedicated learning environment in your own tenant/subscription. Do not use
production indexes, real customer prompts or shared production APIM instances.
Preview support, regions and quotas can change; verify availability before starting.

## Workstation and Azure

- Windows, PowerShell, Git, Azure CLI with Bicep.
- Python 3.12 for root lab tooling; Python 3.13 for hosted sample builds.
- A Foundry account, a deployed chat model (default name `gpt-4o-mini`), hosted-agent
  and Toolbox preview access, and sufficient model/hosting quota.
- The Bicep foundation also requires an existing **APIM Standard v2** service.
  `deploy.ps1` explicitly rejects other SKUs. Dedicated `AIGateway` is a different,
  optional Terraform/portal path.
- C custom additionally requires Azure Developer CLI with
  `azd ai connection create`, two Entra apps and an HTTPS-reachable FastMCP host.

If you have no Foundry account, use the repository's
[modular Terraform guide](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/terraform/README.md)
to create a reviewed environment, or provision it through your organization's Azure process.
Do not run Terraform and Bicep against the same lab resources without deciding ownership.

## Permission checklist

| Actor | Permission required |
| --- | --- |
| Infrastructure deployer | Resource deployment in lab/Foundry groups; RBAC assignment write at the affected Search/Foundry scopes (for example scoped Contributor plus Role Based Access Control Administrator) |
| Connection provisioner | Project connection write and Toolbox create/update |
| Invoking user | Azure AI User/project-agent access, plus tenant sign-in policy |
| Hosted runtime | Model and Toolbox access; B needs an actual configured agent identity |
| Downstream principal | Search Index Data Reader for A/B/C native; delegated API scope for C custom |
| OAuth administrator | Ability to create/configure apps and grant consent where tenant policy requires it |

Do not assume Azure subscription ownership grants Entra application permissions.
Use actual Entra object IDs for RBAC, not project ARM IDs, client IDs or agent names.

## Who creates identities, assigns roles and approves consent?

| Track | App/identity creation owner | Project/runtime authorization owner | Data authorization owner | User/admin consent |
| --- | --- | --- | --- | --- |
| A | Azure resource owner enables the project's managed identity; **no custom OAuth app registration** | Project administrator grants the invoker and hosted runtime project/model/Toolbox access | Search RBAC administrator grants the **project MI object ID** Search Index Data Reader | No per-user downstream tool OAuth consent; ordinary tenant sign-in policies still apply |
| B | Foundry's supported agent identity workflow creates/configures the blueprint and calling instance; **not a manually registered OAuth client** | Project administrator grants the invoker and calling runtime project/model/Toolbox access | Search RBAC administrator grants **each calling instance object ID**, not the blueprint, Search Index Data Reader | No per-user downstream OAuth consent; tenant/preview administrators may need to enable the platform identity workflow |
| C native | Existing signed-in user and platform-managed trusted Search connection; **no customer custom OAuth app/secret** | Project administrator grants invoker/runtime project/model/Toolbox access and enables supported user context | Search RBAC administrator grants the **eventual invoking user object ID** Search Index Data Reader | User completes any platform connection authorization; tenant restrictions may require administrator approval |
| C custom | Entra application administrator/developer creates **API resource app + separate confidential OAuth client app** | Project administrator grants invoker/runtime project/model/Toolbox access; provisioner configures OAuth connection | API owner exposes `access_as_user` and enforces JWT/scope checks; Entra administrator approves permissions/assignment as needed | OAuth client requests delegated API permission; user authorizes the connection; admin consent is required where tenant policy or scope consent settings demand it |

**Project access is not data access.** Azure AI User on the project does not grant
Search Index Data Reader. An OAuth delegated scope is not a Search role. A blueprint
is an agent identity configuration, not the calling instance's RBAC principal.
The standalone provisioners create connections and Toolbox versions only: none
creates Entra apps, grants consent, assigns roles or deploys the hosted runtime.

## Costs and sensitive data

The foundation creates **three Basic Search services**, three projects and three
Log Analytics/Application Insights pairs even if you choose only one track. Model
tokens, hosted runtime, APIM, Search, log ingestion and custom hosting can incur
charges. Check your region's current pricing and set a budget before deployment;
this workshop promises no fixed cost or free tier.

Never commit `.config.json`, secrets, tokens, runtime keys or live evidence.
Use interactive secret entry in C custom, not a literal in shell history.
The supported azd command puts the secret in child-process arguments: use a trusted
workstation, avoid debug output and rotate it afterward. Logs containing validated
user claims are sensitive. `store=false` does not mean no diagnostic logging or
guaranteed zero provider retention.

**Checkpoint:** verify tenant, subscription, region/quota, permission scopes and
cleanup ownership with your administrator. If preview access is unavailable, inspect
the code offline; do not call that a live authorization success.

---

# Deploy the shared foundation

## Choose your own-tenant setup or replay the repository lab

**Reusable setup:** use your own Foundry account/project, chat model and supported
hosted runtime. For A/B/C native, first create a Search index with synthetic data,
knowledge source and trusted knowledge base through your approved Search process.
Record the project ARM ID, project endpoint, Search service ARM ID and actual KB
MCP URL. Follow only the selected standalone runbook; `.config.json`, three cohorts,
APIM and `provision.py` are **not** prerequisites. C custom instead needs the two
Entra apps and HTTPS API described in its track; it needs no Search resources.

**Repository lab replay:** the commands below create the existing multi-cohort
foundation and its marker data. They are optional, not an independent sample's
deployment command, and must target your own reviewed subscription/resources.

Run from a fresh clone on your workstation:

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

Confirm that the displayed subscription and tenant are yours. Choose a new lab
resource group; fixed project names `abc-a`, `abc-b`, `abc-c` must not collide with
existing work. Review [infra.bicep](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/infra.bicep)
and [projects.bicep](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/projects.bicep)
before running:

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

This uses existing Foundry/APIM resources. It does not create a model deployment.
It writes local `.config.json`, including project endpoints/IDs and Search names.
It creates Search and telemetry in the new group but projects and role assignments
also live in the **existing Foundry group/account**.

For A/B/C native, seed only the selected cohort:

```powershell
# Choose a, b or c. Do not run all three just to complete one track.
python .\provision.py --cohort a
```

`provision.py` creates the cohort's index, synthetic marker document, knowledge
source, KB and root-lab tool resources. It writes `evidence\foundation.json`.
For B/C it removes the project's Search reader role if present; do not run it on
a shared project. It is not a passive read-only check.

Inspect the selected cohort locally:

```powershell
$config = Get-Content .\.config.json -Raw | ConvertFrom-Json
$cohort = $config.cohorts | Where-Object label -eq "a" # or b/c
$cohort.project | Format-List
$cohort | Select-Object searchId, searchEndpoint, knowledgeBaseName, marker
```

Build the sample's MCP URL from that Search endpoint and KB name using the exact
format in its README. Keep the cohort's marker for the retrieval check. These
resource IDs are configuration, not credentials, but do not publish environment
details indiscriminately.

**Do not use `setup.ps1` for a single track:** it calls deployment, provisions all
cohorts, publishes multiple agents and configures gateway routes. It is the optional
full showcase, not a shortcut that leaves unrelated tracks untouched.

**Checkpoint:** locate the selected project, Search index/KB and marker. A deployment
success is not proof that hosted retrieval or downstream authorization works.
Now jump directly to your selected track.

## Explicit hosted deployment for any selected standalone sample

Run this **from the selected sample folder**, after its provisioner has printed
`TOOLBOX_ENDPOINT` and its venv is active. Provisioning a Toolbox is not publishing
an agent. Set these values locally for deployment (local environment variables are
not automatically forwarded to a remote runtime):

```powershell
$env:TOOLBOX_ENDPOINT = "<endpoint printed by this sample provisioner>"
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = "<existing chat model deployment>"
$env:AGENT_NAME = "<new hosted agent name in your project>"
```

The following copyable publishing code uses the same
`create_version_from_code`, `HostedAgentDefinition` and `CodeConfiguration` API
as [the repository publisher](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/publish_agents.py).
It packages **only this sample**, uploads source and requests a Python 3.13 remote
build. It does not run the root multi-agent publisher or deploy infrastructure.
Save as `publish_hosted.py` in your copied sample folder, then run
`python .\publish_hosted.py`:

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

In Foundry **Agents**, select this agent/version, check build/start diagnostics
and wait for **Active**. A returned version number is not readiness. Select
**Identity** to obtain the actual calling instance's Entra object ID; the project
administrator must grant its required project/model/Toolbox permissions (the lab
publisher grants Azure AI User at the project scope). B additionally needs its
instance's Search data role. Do not silently substitute a different managed identity.
Review the [official hosting workflow](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent)
if your preview uses different deployment/identity configuration. Its `azd deploy`
requires that quickstart's manifests; do not run it in these bare sample folders
or run its provisioning hooks against your existing KB.

Set `AGENT_VERSION` to the Active version printed above before the selected
sample's invocation step. An existing correctly configured Active version can
skip publishing entirely.

---

# A: project managed identity

![A flow: invoking user to hosted agent, Toolbox project identity and Search RBAC](assets/workshop-project-identity.svg)

**Flow:** user token (`ai.azure.com`) invokes the hosted agent → runtime calls
Toolbox → `ProjectManagedIdentity` obtains the project's Search-audience token →
Search checks the project MI's data role → retrieval result returns to the caller.
The invoking user does not become the Search principal.

Use A when sharing data access across the project is intentional.
Open the [complete A runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/README.md)
and work in `samples\project-identity`. It contains all environment variables,
role assignment, hosting and invocation steps.

1. Create the sample venv and install its `requirements.txt`.
2. Set tenant, project endpoint/ARM ID and the trusted Search KB MCP URL.
   Use fresh connection/Toolbox names.
3. Run `python .\provision_toolbox.py`. Inspect the printed Toolbox endpoint.
4. Assign Search Index Data Reader to the project's actual managed identity.
   The root A foundation already grants this on A Search; verify rather than broaden it.
5. Use **Explicit hosted deployment** on the preceding page to publish
   `hosted_agent.py` with `requirements.txt` for Python 3.13,
   entry point `python hosted_agent.py`, Responses protocol `2.0.0`.
   Set the three hosted environment values from the runbook. Follow the linked
   official Foundry hosting workflow and wait for an **Active** version.
6. Set the hosted `AGENT_NAME` and Active `AGENT_VERSION`, ask for the synthetic
   document in `QUESTION`, set `EXPECTED_TEXT` to its known marker and run
   `python .\invoke_hosted.py`.

For steps 1–3, from your clone (replace every placeholder with your own values):

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

After steps 4–5 (data role, explicit remote publishing and Active status):

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <synthetic test document>."
$env:EXPECTED_TEXT = "<known marker in that document>"
python .\invoke_hosted.py
```

## Code walkthrough and experiment

This is the runnable runtime shape from
[A's hosted_agent.py](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/project-identity/hosted_agent.py).
Run only in the configured hosted environment for the identity test:

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
        instructions=(
            "Use the Toolbox tool requested by the user. Return its actual result. "
            "Never invent a result, marker or identity. Report actual tool errors."
        ),
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()

if __name__ == "__main__":
    asyncio.run(main())
```

The Search RBAC administrator runs this after verifying the project's object ID:

```powershell
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = "<project-managed-identity-object-id>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type ServicePrincipal --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

No custom OAuth app registration, callback, client secret or per-user tool consent
is required. Do not add custom OAuth merely to let a second user invoke A.

In `provision_toolbox.py`, find `ProjectManagedIdentity` and the Search audience.
In `hosted_agent.py`, trace `FoundryChatClient`, `FoundryToolbox` and
`ResponsesHostServer`. In `invoke_hosted.py`, find version-pinned session checks
and failure handling. There is no manual Search token acquisition in the agent.

**Exercise:** predict whether a second authorized invoking user changes the
downstream data principal. It should not: the connection uses project identity.

**Proof:** record the Active version, request time/correlation, tool success and
marker, plus role/audit evidence linking the project principal to Search.
For a negative control, point a fresh connection at a separate test KB where that
project principal has no data role. Do not remove roles from shared infrastructure.
An actual tool authorization denial is expected; a model saying “access denied”
is not enough. Document if service diagnostics cannot expose the principal;
do not label inferred identity as captured token evidence.

Continue to evidence and cleanup; B and C are optional.

---

# B: calling agent identity

![B flow: user invocation, hosted calling identity and instance-specific Search role](assets/workshop-agent-identity.svg)

**Flow:** invoking user reaches the hosted agent → hosted context identifies the
calling instance → Toolbox's `AgenticIdentityToken` uses that instance's token
(`search.azure.com`) → Search checks **that instance's** data role. Project
permission enables runtime access; it does not authorize Search retrieval.

Use B when agents in the same project must have different data privileges.
Follow the [complete B runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/README.md)
in `samples\agent-identity`.

1. Install the sample dependencies and configure tenant/project/KB values.
2. Provision fresh connection and Toolbox names with `python .\provision_toolbox.py`.
3. Use **Explicit hosted deployment** to publish the selected hosted package
   using the runbook's Python 3.13 entry point,
   Responses protocol and hosted environment. Configure the calling agent's
   agentic identity through the supported Foundry identity workflow.
4. Obtain the **calling agent instance's Entra object ID**, not a blueprint/client
   ID or agent version string. Grant it Search Index Data Reader on B Search.
5. After RBAC propagation and Active hosting, pin the version and invoke the caller
   with your synthetic marker.

For steps 1–2, from the clone root:

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

After steps 3–4 (publish, configure platform instance identity, grant roles):

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <synthetic test document>."
$env:EXPECTED_TEXT = "<known marker in that document>"
python .\invoke_hosted.py
```

## Code walkthrough and experiment

These declarations are the B provisioner's connection payload and SDK tool
shape, with imports and environment context. They do not deploy a runtime or
assign roles; run the complete
[B provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/agent-identity/provision_toolbox.py)
for the authenticated ARM PUT and Toolbox create/update:

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

In Foundry **Agents → your agent → Identity**, obtain the calling instance object
ID after platform identity creation. A blueprint is not a manually registered
confidential OAuth app, and its client/blueprint ID is not the data principal.
The RBAC administrator then runs:

```powershell
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = "<calling-agent-instance-object-id>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type ServicePrincipal --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

Separately grant the runtime its required project/model/Toolbox access. No custom
OAuth client secret/callback or per-user downstream consent is needed for B.

Locate `AgenticIdentityToken` and `https://search.azure.com` in the provisioner.
The hosted/caller structure resembles A, but connection identity selection changes
the downstream boundary. The setup user's ARM token does not become the agent's
Search token.

**Exercise:** create a second test agent with a different agent instance identity
and the same Toolbox configuration but **no** Search data role. Predict which calls
should succeed, then invoke both under the same authorized user.

**Proof:** capture distinct actual identity object IDs and their role inventories.
The authorized agent must retrieve the marker; the unassigned agent must produce
a real backend/tool authorization failure. Confirm neither identity inherits broad
Search access from another scope. The project MI should not be the fallback reader.
Wait for propagation before interpreting a freshly granted role as a product defect.

If an identity cannot be created in your tenant/preview, report the blocker;
running `hosted_agent.py` locally is not an equivalent agent-instance identity test.

Continue to evidence and cleanup; user tracks are optional.

---

# C native: managed user context and a trusted Search KB

![C native flow: signed-in user context through Toolbox to trusted Search](assets/workshop-native-user.svg)

**Flow:** signed-in user's `ai.azure.com` caller token invokes the hosted agent →
`ResponsesHostServer` supplies user context → Toolbox's native `UserEntraToken`
connection targets the trusted Search KB → Search checks the **user's** Search
data role. No custom authorization/token endpoints are configured by this sample.

Use this path when Search authorization must follow the invoking user.
Follow the [complete native user runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/README.md)
in `samples\user-identity\trusted-kb`.

1. Configure the selected C project and its **trusted Search** KB MCP URL.
2. Run the standalone provisioner with fresh connection/Toolbox names.
3. Grant Search Index Data Reader to the intended **invoking user's Entra object ID**,
   not automatically the provisioning administrator.
4. Use **Explicit hosted deployment** to publish the Python 3.13 hosted package
   and set the runbook's model/project/Toolbox
   environment. The hosted runtime must support user context.
5. Complete any Foundry connection/user authorization challenge in the browser as
   the intended user. Tenant policy may require admin approval. Retry with a fresh
   invocation; do not programmatically follow consent URLs.
6. Invoke an Active pinned version and require the synthetic marker.

For steps 1–2, from the clone root:

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

After steps 3–5, sign in as the intended user, not the provisioning administrator:

```powershell
az login --tenant "<tenant-id>"
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <synthetic test document>."
$env:EXPECTED_TEXT = "<known marker in that document>"
python .\invoke_hosted.py
```

## Code walkthrough and experiment

The following is the native provisioner's connection/tool configuration, not a
manual user-token exchange. Use the complete
[native provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/trusted-kb/provision_toolbox.py)
to submit it and publish the Toolbox:

```python
import os
from azure.ai.projects.models import MCPToolboxTool

target = os.environ["MCP_SERVER_URL"]  # Trusted Search KB MCP URL
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

Sign in as the eventual invocation user and obtain their object ID. A separately
authorized Search RBAC administrator assigns this role; do not accidentally grant
the provisioning administrator's identity:

```powershell
az login --tenant "<tenant-id>"
az ad signed-in-user show --query id -o tsv
$env:DATA_PRINCIPAL_OBJECT_ID = "<intended-invoking-user-object-id>"
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type User --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

No customer custom OAuth API/client registration, secret or callback is required.
This does **not** promise unrestricted tenant consent: platform connection
authorization and sign-in restrictions may require an administrator's approval.
Complete the intended user's challenge through Foundry, then invoke afresh.

Locate `UserEntraToken` and Search audience in `provision_toolbox.py`.
The hosted agent does not implement OAuth exchange. `DefaultAzureCredential`
provides runtime credentials; it does not grant the user a Search role.

**Exercise:** use two users authorized to invoke the same agent, one with Search
data access and one without. Sign in separately in the correct tenant, complete
necessary consent and retry. A consent challenge is inconclusive, not the deny proof.

**Proof:** record invoking user object IDs, connection type, role scopes and actual
tool outcomes. Only the authorized user should retrieve the marker. Correlate
available downstream authorization evidence. Check inherited roles before interpreting
an unexpected allow. Service-level Search RBAC is not document-level isolation:
production per-document security requires additional ACL/filter enforcement.

This path needs no custom OAuth client secret or arbitrary API audience. Do not
substitute a FastMCP URL. Describe it as managed native user access; claim an exact
OBO grant only if you independently have verifiable exchange evidence.

Continue to evidence and cleanup; custom OAuth is an alternative, not the next step.

---

# C custom: OAuth2 Toolbox to your FastMCP API

![C custom flow: browser authorization code and refresh to a JWT-validating API](assets/workshop-custom-oauth.svg)

**Flow:** user authorizes the connection in the browser → Entra issues an
authorization code to Toolbox's registered callback → Toolbox exchanges it using
the confidential client's credentials and may refresh with `offline_access` →
Toolbox calls HTTPS `/mcp` with an API-audience delegated token → FastMCP's boundary
validates the token before executing `probe_echo`. The agent/server implements
neither a manual JWT-bearer OBO exchange nor an OAuth authorization server.

Use this path for a custom API with delegated authorization, not for replacing
the native Search connection. Follow the [complete custom OAuth runbook](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/README.md)
in `samples\user-identity\custom-oauth`.

1. An authorized Entra application developer/admin creates two single-tenant
   registrations in **Entra ID → App registrations → New registration**:
   - **API resource app:** record its Application (client) ID. In its manifest,
     set `api.requestedAccessTokenVersion` to `2`. Under **Expose an API**, set
     `api://<API-application-id>` and add the delegated scope `access_as_user`;
     choose who may consent according to tenant policy.
   - **Confidential OAuth client app:** record its distinct Application (client)
     ID. Under **API permissions → Add a permission → My APIs**, select the API
     app and delegated `access_as_user`. Under **Certificates & secrets**, create
     a short-lived client secret and securely retain the **value**, not secret ID.
     Do not guess a redirect URI yet; provisioning discovers the platform callback.
   - An authorized tenant admin grants consent where required by tenant policy
     or the API scope's consent setting, and configures user assignment if required.
     Admin permission consent and the intended user's connection authorization
     are separate checks; an Azure subscription role does not grant either.
2. In a separate server venv, install `server-requirements.txt`, set
   `ENTRA_TENANT_ID` and the actual v2 `ENTRA_AUDIENCE` (normally the API client ID
   GUID), then run `python .\server.py`.
3. Publish its port 8000 `/mcp` behind an HTTPS endpoint reachable from Foundry.
   Localhost is not reachable. Hosting/domain/TLS provisioning is your responsibility;
   no cloud host is created by the sample.
4. In the caller venv, install `requirements.txt`, sign in with Azure CLI and azd,
   and set the project, HTTPS MCP URL, OAuth client ID and
   `api://<API-application-id>/access_as_user` scope.
5. Use the runbook's secure interactive secret entry and `try/finally` cleanup,
   then run `python .\provision_toolbox.py`. Register the **printed callback exactly**
   as a Web redirect URI on the OAuth client app.
6. In Foundry, open this connection's user authorization/consent flow as the
   intended user; verify the client, API and requested permissions before approval.
   Complete administrator approval if required. Use **Explicit hosted deployment**
   for the agent package (not `server.py`), wait for Active, and invoke `probe_echo` with the runbook's
   nonsensitive UUID/message/count experiment and expected validation marker.

For steps 2–3, in the selected folder's separate server terminal:

```powershell
Set-Location .\samples\user-identity\custom-oauth
python -m venv .server-venv
.\.server-venv\Scripts\Activate.ps1
python -m pip install -r .\server-requirements.txt
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:ENTRA_AUDIENCE = "<API-application-client-id-GUID>"
python .\server.py
```

Keep this process running for the test or deploy those server files to your
approved HTTPS host with the same server environment. Foundry must reach
`https://<your-custom-server>/mcp`; a local terminal alone does not provide it.

For steps 4–5, in a second terminal, from the same sample folder:

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

After exact callback registration, connection authorization and hosted publishing:

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = 'Call probe_echo with experiment_id "11111111-2222-4333-8444-555555555555", message "oauth-toolbox", count 1. Return the real result.'
$env:EXPECTED_TEXT = "CUSTOM_MCP_ENTRA_VALIDATED"
python .\invoke_hosted.py
```

## Code walkthrough and experiment

The provider endpoints are explicitly configured by the
[custom provisioner](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/provision_toolbox.py):

```python
import os

base = f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/"
authorization_url = base + "authorize"
token_url = base + "token"
refresh_url = base + "token"
scopes = os.environ["OAUTH_SCOPE"] + " offline_access"
```

It passes these to `azd ai connection create --auth-type oauth2`, then reads
`properties.redirectUrl` from the created ARM connection. **Register that exact
discovered URI as a Web redirect on the OAuth client**, not on the API resource
app. This is callback discovery from the platform; the server does not implement
automatic OAuth provider discovery. Entra's issuer/JWKS URLs are tenant-specific,
and the sample explicitly configures the provider endpoints.

The server's validation core below is independently copyable with PyJWT from
`server-requirements.txt`; its caller is the middleware in
[server.py](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/samples/user-identity/custom-oauth/server.py),
which rejects missing/invalid tokens before entering the tool:

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

This verifies signature, issuer, audience, token timing, tenant and delegated
scope. `azp` and `ver` are returned claims, **not additional allowlist checks**;
do not describe this demo as enforcing a specific authorized client list.

In the provisioner, trace `azd ai connection create` and OAuth2 connection creation.
In `server.py`, trace signature/JWKS validation, issuer, tenant, audience, expiry
and delegated scope checks before tool execution. The API validates a token
supplied by Toolbox; it neither acquires nor exchanges that token.

**Proof:** compare the real returned arguments with your experiment, and correlate
validated server claims (`oid`, audience, scope) to the consenting user. Never log
or copy the bearer token. `/healthz` is only readiness.

**Negative exercise:** without any bearer token, request the published `/mcp` endpoint:

```powershell
curl.exe -i "https://<your-custom-server>/mcp"
```

Require authentication rejection (normally HTTP 401), not a tool result. Then,
using controlled test identities/tokens without printing them, verify wrong audience
or missing delegated scope is rejected before `probe_echo`. Retain only status and
sanitized validation reasons. If the host intercepts the request, establish whether
the rejection came from ingress or the FastMCP validator.

This is **authorization code plus refresh (`offline_access`)**, not proven
JWT-bearer OBO. The consenting user may differ from another later invocation caller;
test consent/user binding rather than assuming it. Delegated scope authorization
alone is not an application-specific row/document ACL.

---

# Evidence, troubleshooting and optional gateway extension

For your chosen track, produce a short local evidence record:

| Item | Record |
| --- | --- |
| Environment | Tenant/subscription, track, selected project and test backend |
| Hosted state | Active agent name/version, connection authentication, Toolbox endpoint |
| Expected identity | Actual object ID, audience, delegated scope or RBAC scope |
| Allow | Timestamp/correlation, genuine tool result and synthetic marker/arguments |
| Deny | Changed principal/boundary, actual HTTP/tool failure and sanitized reason |
| Limits | Whether identity came from backend audit, API validated claims or configuration inference |

Do not export tokens, secrets, personal prompts or complete production response bodies.
Use [observability.md](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/observability.md)
for the existing trace/log queries. Allow ingestion delay before checking absence.
The standalone folders do not install the root custom audit middleware: do not expect
root-only audit events from them automatically.

## Troubleshoot by boundary

- **Deployment fails:** confirm subscription, Standard v2 SKU, preview region/quota
  and RBAC write scopes. No infrastructure success is inferred after an error.
- **401:** inspect tenant, issuer, audience and expiration without printing tokens.
- **403/authorization denial:** identify the downstream principal and effective
  role/scope; allow propagation. Broadening every identity is not the fix.
- **Consent challenge:** finish browser approval and retry; challenge is not retrieval.
- **Tool unreachable:** verify the real HTTPS endpoint from the service's network,
  not only a localhost health endpoint.
- **No marker:** inspect actual tool output; model text is not proof the tool ran.
- **No logs:** confirm diagnostics and ingestion delay; absence in one table/time
  window does not prove nothing was stored anywhere.

## Optional: full gateway showcase

After completing an independent track, review the root README before choosing the
billable full `setup.ps1`/`verify.ps1` path. It provisions all A/B/C routes, identities
and gateway configuration. Do not run it merely to validate a copied sample.
`verify.ps1` assumes those full-showcase resources exist.

The B agent data gateway, C user ingress, confidential no-store route and BYOM/
dedicated AI Gateway path are distinct experiments. Standard v2 APIM is the verified
classic gateway environment; the dedicated gateway has separate Terraform and portal
prerequisites. Runtime keys are gateway-wide, so separate gateways are needed for
different strict model-access boundaries.

**Final exercise:** explain why no-store, log content capture, user authorization
and model-gateway access are four independent controls.

---

# Cleanup and next steps

Maintain an inventory of every newly created resource, role assignment, connection,
Toolbox, agent version and OAuth app. Do not delete pre-existing or shared resources.

1. Stop/delete workshop hosted deployments and your custom API hosting first.
2. Remove only workshop-created connections/Toolboxes/agents in the selected project,
   using Foundry's supported resource management workflow.
3. Delete the workshop `abc-*` projects **only if newly created and dedicated**.
   They are in the existing Foundry account, not the lab resource group.
4. Remove workshop role assignments on the existing Foundry account (including
   model roles assigned to the three Search managed identities) and any user/agent
   Search assignments you created. Save assignment IDs before deleting identities.
5. Delete the dedicated additive lab group after reviewing its contents:

```powershell
az resource list --resource-group "rg-foundry-identity-workshop" -o table
# Run only after confirming that every resource in this group belongs to this workshop.
az group delete --name "rg-foundry-identity-workshop" --yes
```

6. Keep reused Foundry/model/APIM resources. If you created a separate Terraform
   environment, review `terraform plan -destroy` in that environment before applying
   teardown; Bicep has no automatic inverse deployment.
7. Remove workshop OAuth consent grants/apps if dedicated; revoke/rotate the client
   secret and remove local environment variables. Stop the local server.
8. Delete local live evidence/configuration and sample venvs when no longer needed,
   according to your retention policy. Verify Azure resource inventory and billing;
   deleting only the Search group is not complete cleanup.

## Take it to production

Review the [secure target architecture](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/recommended-secure-architecture.svg).
Use least privilege, controlled user consent, appropriate document permissions,
private networking where supported and content-minimized correlated diagnostics.
Preview identity paths require validation in your own environment.

You have completed this workshop when one selected track has a working hosted allow
case, a genuine authorization deny case, clearly labeled evidence limitations and
verified cleanup—not when all optional scenarios have been run.

For MOAW publication and local preview, see
[the maintainer guide](https://github.com/yelghali/foundry-agents-toolbox-ai-gateway/blob/main/docs/moaw-publishing.md).
