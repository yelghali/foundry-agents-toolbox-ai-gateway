# B — Calling agent identity

Copy this entire folder; its provisioner, hosted agent, caller and requirements
are independently usable. `provision_toolbox.py` always uses `AgenticIdentityToken`
and the Search audience `https://search.azure.com`, with no mode switch.

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
