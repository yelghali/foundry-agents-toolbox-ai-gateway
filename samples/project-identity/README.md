# A — Project managed identity

Copy this entire folder; all three Python files and `requirements.txt` are
independent. There is no mode selection. `provision_toolbox.py` always creates
`ProjectManagedIdentity`, with Search audience `https://search.azure.com`.

## Prerequisites and role mapping

- Foundry project supporting hosted agents/Toolbox preview, deployed chat model,
  Python 3.13 hosted runtime, Azure CLI signed into your tenant.
- Existing trusted Search knowledge-base MCP endpoint backed by your index.
  This is not an arbitrary custom MCP URL.
- Setup caller: project connection write and Toolbox create/update permissions.
  Invocation caller: Azure AI User/project and agent access.
- Hosted runtime: model and Toolbox access under your hosting identity setup.
- **Data principal: project managed identity**, not the setup caller, asking user
  or hosted agent name. Obtain the project's actual Entra principal/object ID
  from its identity configuration. Grant Search Index Data Reader on the Search
  service to that object ID. Provisioning does not create identities or roles.

The ARM project resource ID below locates the connection; it is not a role
assignment principal. Confirm it and the project endpoint refer to the same project.

## Local setup (PowerShell, in the copied folder)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant <tenant-id>
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<search>.search.windows.net/knowledgebases/<kb>/mcp?api-version=2026-05-01-preview"
$env:CONNECTION_NAME = "my-project-kb"
$env:TOOLBOX_NAME = "my-project-tools"
python .\provision_toolbox.py
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = "<project-managed-identity-object-id>"
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type ServicePrincipal --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

Choose fresh names: setup upserts the connection and publishes a Toolbox default
version. Role assignment requires separate RBAC write permission; allow propagation.
The setup client uses the ARM token scope, not a Search token.

## Host the agent

Package `hosted_agent.py` and `requirements.txt` for a Python 3.13 remote build.
Entry point: `python hosted_agent.py`; Responses protocol: `2.0.0`.
Set hosted environment:

```text
FOUNDRY_PROJECT_ENDPOINT=<your project endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<your chat model deployment>
TOOLBOX_ENDPOINT=<endpoint printed by provision_toolbox.py>
```

Follow the [official publishing workflow](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent).
`FoundryChatClient` calls the model, `FoundryToolbox` uses the connection,
and `ResponsesHostServer` supplies hosted context. `DefaultAzureCredential`
does not grant permissions. A local hosting process is not the hosted identity test.
No per-user downstream OAuth consent is needed for project managed identity.

## Invoke locally

Use an existing Active agent version configured for this Toolbox; no redeploy is
needed to use the caller.

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <nonsensitive test document>."
$env:EXPECTED_TEXT = "<known document marker>"
python .\invoke_hosted.py
```

The caller uses your CLI `https://ai.azure.com/.default` token, pins/verifies the
session version without changing the agent default, and disables storage.
HTTP, response, tool and consent failures raise errors. `EXPECTED_TEXT` is optional
but strengthens retrieval checks; it is not proof of the principal used.
Inspect Search authorization/audit evidence for that. Use nonsensitive input:
responses are printed and service diagnostics may capture bodies. Unexpected
consent challenges fail: review the connection in Foundry before retrying.
