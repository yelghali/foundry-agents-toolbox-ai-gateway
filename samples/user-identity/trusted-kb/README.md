# C native — UserEntraToken with a trusted Search KB

Copy this folder; the three Python files and requirements are standalone.
`provision_toolbox.py` always uses `UserEntraToken`, Search audience
`https://search.azure.com`. Do not substitute a custom API audience or FastMCP URL.

## Prerequisites and role mapping

- Foundry project supporting hosted-agent/Toolbox preview, deployed chat model,
  Python 3.13 hosted runtime; Azure CLI login in your tenant.
- Existing trusted Search knowledge-base MCP endpoint and indexed test data.
- Setup caller: project connection write and Toolbox create/update permissions.
  Invocation caller: Azure AI User/project and agent access.
- Hosted runtime: model/Toolbox access and hosting support for user context.
- **Data principal: signed-in user Entra object ID.** Grant that user Search Index
  Data Reader on the Search service. Project MI/agent identity roles do not replace
  the user's role. Project resource IDs locate connections; they are not principals.

The scripts do not create data, identities or roles. Confirm the ARM project ID
and endpoint identify the same project.

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
$env:CONNECTION_NAME = "my-user-kb"
$env:TOOLBOX_NAME = "my-user-tools"
python .\provision_toolbox.py
$env:SEARCH_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search>"
$env:DATA_PRINCIPAL_OBJECT_ID = az ad signed-in-user show --query id -o tsv
az role assignment create --assignee-object-id $env:DATA_PRINCIPAL_OBJECT_ID --assignee-principal-type User --role "Search Index Data Reader" --scope $env:SEARCH_RESOURCE_ID
```

Role assignment requires RBAC write permission and propagation time. If a
different administrator provisions, assign the eventual invocation user's role,
not automatically the administrator's. Fresh connection/Toolbox names avoid
changing existing resources. Setup uses an ARM token to upsert the connection
and publish the Toolbox default version; it does not implement user token exchange.

## Hosted agent and consent

Package `hosted_agent.py` and `requirements.txt` for Python 3.13 Foundry remote
build. Entry point `python hosted_agent.py`; Responses protocol `2.0.0`.
Hosted environment:

```text
FOUNDRY_PROJECT_ENDPOINT=<your project endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<your model deployment>
TOOLBOX_ENDPOINT=<printed Toolbox endpoint>
```

Use the [official hosted publishing workflow](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent).
`FoundryChatClient` calls the model; `FoundryToolbox` is the managed client;
`ResponsesHostServer` receives hosted user context. `DefaultAzureCredential` does
not grant permissions. A local hosted process cannot reproduce this user path.

Complete any connection/user authorization challenge in the Foundry browser as
the intended user; tenant policy can require administrator approval. Retry with a
fresh invocation after consent. Do not automatically fetch consent links.
This native trusted path does not require the custom OAuth app/secret configuration.
The agent itself does not acquire/exchange a downstream user token.

## Invoke locally

Use an existing Active hosted version configured for this Toolbox (no redeploy):

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = "Use the knowledge-base retrieval tool to find <nonsensitive test document>."
$env:EXPECTED_TEXT = "<known document marker>"
python .\invoke_hosted.py
```

The caller uses your CLI `https://ai.azure.com/.default` token, pins/verifies a
session without changing agent defaults and disables storage. Consent, HTTP,
session and tool errors fail. `EXPECTED_TEXT` is optional; a marker alone does not
prove user authorization. Compare downstream audit/authorization evidence and,
if appropriate, a user without the Search data role. Use nonsensitive inputs:
responses print and service diagnostics may log bodies; consent state is redacted.
