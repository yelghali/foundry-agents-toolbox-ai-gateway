# B — Calling agent identity

Copy this entire folder; its provisioner, hosted agent, caller and requirements
are independently usable. `provision_toolbox.py` always uses `AgenticIdentityToken`
and the Search audience `https://search.azure.com`, with no mode switch.

For a runnable **custom FastMCP target instead of Search**, use
`provision_custom_toolbox.py` and `custom_server.py`. The original provisioner,
hosted agent and caller are unchanged.

## Custom application-token target (B)

**Offline contract verified; LIVE custom audience token acquisition is UNVERIFIED.**
The [Toolbox authentication documentation](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/tool-authentication)
documents agentic connections with configurable target/audience and explicitly
rejects user tokens. This establishes the connection mechanism, not successful
custom audience issuance for your hosted agent. There is no manual OBO.

Register a single-tenant Entra API application and create its enterprise
application/service principal. Set manifest `api.requestedAccessTokenVersion=2`.
Use its **application/client ID GUID** for `CUSTOM_MCP_AUDIENCE`: the v2 token's
`aud` is that GUID, not the `api://...` identifier URI. The connection requests
that resource identifier; do not append `/.default` or reuse C's delegated setup.
The [official claims reference](https://learn.microsoft.com/entra/identity-platform/access-token-claims-reference)
defines the v2 audience/issuer contract.

This sample uses [application ACL authorization](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-client-creds-grant-flow#access-control-lists):
keep enterprise-app **Assignment required? = No** to permit role-less app tokens.
The explicit service-principal `oid` allowlist is the API access grant. There is
no delegated scope, secret, consent or Search RBAC. If policy requires roles,
define an application-only `Mcp.Invoke` app role, assign it to each real agent
identity through enterprise-app/Graph appRoleAssignment with admin permissions,
and extend validation to require that role plus the allowlist. This sample
deliberately does not enforce a role.

After the standard local setup in this copied folder:

```powershell
$env:CUSTOM_MCP_AUDIENCE = "<API-application-client-ID-GUID>"
$env:CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS = "<calling-agent-instance-object-ID>"
python .\custom_server.py
```

Use the real calling agent instance's Entra **service-principal object ID**, not
its blueprint/client ID, project MI or setup user. Agent identity creation and
access must precede the call. For several allowed instances, comma-separate
their explicit IDs; prefer one per test. Do not add a project MI to make B pass.
The server code is identical to A's small standalone server so either folder can
be copied independently, without lab imports.

The server exposes `/healthz` at local port 8000 and authenticated streamable MCP
at `/mcp`. Put it behind reachable HTTPS for Foundry; local HTTP is test-only.
Keep token/body logging off and use nonsensitive experiment UUIDs. In another
configured shell:

```powershell
$env:CUSTOM_MCP_SERVER_URL = "https://<your-custom-host>/mcp"
$env:CUSTOM_MCP_AUDIENCE = "<same-API-client-ID-GUID>"
$env:CONNECTION_NAME = "my-agent-custom"
$env:TOOLBOX_NAME = "my-agent-custom-tools"
python .\provision_custom_toolbox.py
```

The provisioner always creates `AgenticIdentityToken`. Publish a separate hosted
version with the unchanged `hosted_agent.py` and printed `TOOLBOX_ENDPOINT`, then
use the unchanged caller with
`QUESTION="Call identity_probe with experiment_id <UUID>"` and
`EXPECTED_TEXT="CUSTOM_MCP_APPLICATION_VALIDATED"`. Do not repoint a native version.

**Live verification gate:** require a successful tool result with validated
`oid` matching the actual agent instance, tenant, exact v2 issuer/audience;
also require rejection of a different application principal and delegated user
token. RS256 signature, expiry, issued/not-before times and required claims are
checked. Every `scp` claim (even empty) and user `idtyp` is rejected. Only safe
validated identifier claims are returned. HTTP 200, ARM writes or synthetic JWTs
are not evidence of live custom token acquisition. Preserve acquisition errors,
check tenant/resource/agent access and label live support unverified rather than
substituting user tokens. Clean up only the newly created test resources.

## Prerequisites and role mapping

- Foundry project with hosted-agent/Toolbox preview, deployed chat model and
  Python 3.13 hosted runtime; Azure CLI signed into the correct tenant.
- Existing trusted Search knowledge-base MCP endpoint backed by your index.
- Setup caller needs project connection write/Toolbox create/update permissions;
  invocation caller needs Azure AI User/project and agent access.
- Hosted runtime needs model and Toolbox access. Configure the calling agent's
  agentic identity using the project's supported hosting identity workflow.
- **Data principal: each calling agent instance's Entra object ID.** The project
  owner, project managed identity and caller user are not substitutes.
  The agent identity must exist before its data role can be assigned. Obtain its
  real object ID from the agent identity configuration, not its name/version,
  blueprint/client ID or project resource ID.

Provisioning does not create identities, indexes or role assignments. Confirm the
project endpoint and ARM resource ID describe the same project.

## Local setup (PowerShell, in this copied folder)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant <tenant-id>
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview"
$env:CONNECTION_NAME = "my-agent-kb"
$env:TOOLBOX_NAME = "my-agent-tools"
python .\provision_toolbox.py
```

Choose fresh names: the script upserts a connection and publishes a Toolbox default
version. The local setup caller gets an ARM token, not the downstream agent token.

## Hosted runtime and data authorization

Package `hosted_agent.py` plus `requirements.txt` for Foundry Python 3.13 remote
build, entry point `python hosted_agent.py`, Responses protocol `2.0.0`.
Configure:

```text
FOUNDRY_PROJECT_ENDPOINT=<your project endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<your model deployment>
TOOLBOX_ENDPOINT=<printed Toolbox endpoint>
```

Follow the [official hosted publishing workflow](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent).
`FoundryChatClient` supplies model access; `FoundryToolbox` is the managed tool
client; `ResponsesHostServer` supplies the calling context. There is no manual
token exchange. `DefaultAzureCredential` alone does not grant roles.
Running this hosted entry point locally does not reproduce an agent instance.

Once the actual calling identity exists, grant Search Index Data Reader:

```powershell
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = "<calling-agent-instance-object-id>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type ServicePrincipal --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

This command requires RBAC write permission; wait for propagation. Repeat for
each independent agent instance needing data access. Per-user downstream OAuth
consent is not required for this connection type.

## Invoke locally

An existing Active version configured for this Toolbox can be invoked without
redeployment:

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <nonsensitive test document>."
$env:EXPECTED_TEXT = "<known document marker>"
python .\invoke_hosted.py
```

The Azure CLI caller uses `https://ai.azure.com/.default`, not the agent's data
token. It creates/verifies a version-pinned session, leaves the agent default
unchanged and disables storage. HTTP, session, response, tool or consent failures
are errors, not successful retrieval. Unexpected consent requires inspecting the
Foundry connection then retrying. A marker is optional and cannot by itself prove
agent identity: compare downstream authorization/audit evidence. Use nonsensitive
questions; results print locally and diagnostics may log service bodies.
