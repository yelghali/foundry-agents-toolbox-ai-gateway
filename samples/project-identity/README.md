# A — Project managed identity

Copy this entire folder; its scripts and `requirements.txt` are independent.
There is no authentication-mode selection. `provision_toolbox.py` always creates
`ProjectManagedIdentity`, with Search audience `https://search.azure.com`.

For a runnable **custom FastMCP target instead of Search**, use
`provision_custom_toolbox.py` and `custom_server.py` below. The native provisioner
and original hosted agent/caller remain unchanged.

## Custom application-token target (A)

**Offline contract verified; LIVE custom audience token acquisition is UNVERIFIED.**
The [Toolbox authentication documentation](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/tool-authentication)
documents project identity connections with a configurable target and audience.
That is the supported connection mechanism, not proof that this tenant's hosted
runtime can acquire a token for this particular custom app. No manual OBO exists here.

1. Register a single-tenant Entra API application and create its enterprise
   application/service principal. Set `api.requestedAccessTokenVersion` to `2`
   in its manifest. Use the API **application/client ID GUID** for
   `CUSTOM_MCP_AUDIENCE`: v2 access tokens use this GUID as `aud`, not the
   `api://...` identifier URI. The connection requests this resource identifier;
   do not append `/.default` or copy C's delegated audience configuration.
   See the [official access-token claims reference](https://learn.microsoft.com/entra/identity-platform/access-token-claims-reference)
   for the v2 audience/issuer contract.
2. This server uses [application ACL authorization](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-client-creds-grant-flow#access-control-lists).
   Keep enterprise-app **Assignment required? = No** for this ACL-only sample,
   so role-less application tokens can be issued. The explicit `oid` allowlist
   grants access; no delegated scope, OAuth secret, consent, Search RBAC or
   client-ID-only permission is required. If your organization requires app
   roles/assignment, define an application-only role (for example `Mcp.Invoke`),
   assign it to the project MI via enterprise-app/Graph appRoleAssignment with
   admin permissions, and extend validation to require that role as well as
   the allowlist. This sample deliberately does not enforce a role.
3. Obtain the **project managed identity service-principal object ID**, not the
   API app/client ID or setup user's ID, and allow only it on this A server.

After the normal local setup, run in the copied scenario folder:

```powershell
$env:CUSTOM_MCP_AUDIENCE = "<API-application-client-ID-GUID>"
$env:CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS = "<project-MI-object-ID>"
python .\custom_server.py
```

It serves unauthenticated readiness at `http://localhost:8000/healthz` and
authenticated streamable HTTP at `/mcp`. Use a reachable HTTPS deployment or
trusted HTTPS ingress for Foundry; localhost is only for local tests. No token
is acquired by this server. Keep HTTP access/header logging off; use nonsensitive
UUIDs. The server emits a `validated_mcp_exchange` JSON event containing only the
validated application identifiers, UUID query and returned demo result. These
events persist in container logs; do not expand the probe to private data.
In a second configured shell, choose fresh connection/Toolbox names:

```powershell
$env:CUSTOM_MCP_SERVER_URL = "https://<your-custom-host>/mcp"
$env:CUSTOM_MCP_AUDIENCE = "<same-API-client-ID-GUID>"
$env:CONNECTION_NAME = "my-project-custom"
$env:TOOLBOX_NAME = "my-project-custom-tools"
python .\provision_custom_toolbox.py
```

This creates fixed `ProjectManagedIdentity` auth and custom audience. Publish a
separate hosted version using the unchanged `hosted_agent.py` and the printed
`TOOLBOX_ENDPOINT`; do not repoint an existing native version. Invoke using the
unchanged caller with `QUESTION="Call identity_probe with experiment_id <UUID>"`
and `EXPECTED_TEXT="CUSTOM_MCP_APPLICATION_VALIDATED"`.

**Live verification gate:** require a successful MCP tool result, validated
`tid`/`oid` matching the project MI, exact v2 issuer/audience, and negative tests
for a non-allowlisted application principal and a delegated user token. The server
checks RS256 signature, expiry, issued/not-before times and required claims,
rejects every `scp` claim (including empty) and user `idtyp`, and returns only safe
identifier claims. HTTP 200, connection creation or synthetic JWT tests do not
prove managed custom token acquisition. If acquisition fails, retain the error,
check resource audience/tenant/identity access, and label live support unverified;
never replace the flow with caller/user tokens. Clean up only your new resources.

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
