# C custom — OAuth2 Toolbox to FastMCP

Copy this entire folder. It contains an independent OAuth provisioner, hosted
agent, caller, runtime requirements, `server.py` and `server-requirements.txt`.
No scenario switch or lab imports. The connection always uses OAuth2 through
`azd ai connection create`.

This is authorization code plus refresh (`offline_access`), **not proven
JWT-bearer OBO**. The server validates the token supplied by Toolbox; it neither
acquires nor exchanges tokens. User `oid` claims prove delegated identity only.

## Prerequisites and identity mapping

- Foundry project with hosted-agent/Toolbox preview, model deployment and Python
  3.13 hosting; Azure CLI and Azure Developer CLI supporting `azd ai connection create`.
- Setup caller: project connection write/Toolbox create-update permissions.
  Invocation caller: Azure AI User/project-agent access.
- Hosted runtime needs model/Toolbox access; this does not grant downstream data rights.
- Entra **API app** exposing delegated `access_as_user`, configured for v2 access
  tokens. `ENTRA_AUDIENCE` is its actual v2 audience (normally API client ID GUID).
- Separate **OAuth client app** with delegated permission to that API scope,
  a client secret and Web redirect URI (printed during provisioning).
- **Data principal:** user who completes the connection consent. Tenant policy may
  require admin consent/user assignment. There is no Search data role here.
  API client ID, OAuth client ID, user object ID and ARM project ID are different.

## Run the independent server

In one PowerShell terminal, in this folder:

```powershell
python -m venv .server-venv
.\.server-venv\Scripts\Activate.ps1
python -m pip install -r .\server-requirements.txt
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:ENTRA_AUDIENCE = "<API-application-client-id-GUID>"
python .\server.py
```

Publish port 8000's `/mcp` at your own HTTPS endpoint reachable from Foundry;
localhost is not reachable from hosting. `/healthz` is unauthenticated readiness,
not proof of authenticated tool access. `/mcp` verifies RS256 signature, issuer,
tenant, audience, expiry and delegated scope. It logs validated claims and
allowlisted demo arguments, never bearer tokens. Treat identity logs as sensitive.

## Provision locally

In a second terminal in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
az login --tenant <tenant-id>
azd auth login --tenant-id <tenant-id>
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_PROJECT_RESOURCE_ID = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>"
$env:MCP_SERVER_URL = "https://<your-custom-server>/mcp"
$env:CONNECTION_NAME = "my-custom-oauth"
$env:TOOLBOX_NAME = "my-custom-tools"
$env:OAUTH_CLIENT_ID = "<OAuth-client-application-id>"
$env:OAUTH_SCOPE = "api://<API-application-id>/access_as_user"
$secret = Read-Host "OAuth client secret" -AsSecureString
$env:OAUTH_CLIENT_SECRET = [System.Net.NetworkCredential]::new("", $secret).Password
try { python .\provision_toolbox.py }
finally { Remove-Item Env:\OAUTH_CLIENT_SECRET; $secret = $null }
```

Confirm both CLIs use the intended tenant/project and endpoint matches ARM ID.
Use fresh names: provisioning writes a connection and publishes a Toolbox default
version. It creates no app registrations, identities or consent grants.
azd's supported command passes the secret in child-process argv: use a trusted
workstation, never debug logging, and rotate credentials per policy. Diagnostics
are captured/redacted and timeouts do not export secret-bearing argv.

Register the printed callback **exactly** as a Web redirect URI on the OAuth
client app. Then complete Foundry's connection browser consent as the intended
user (admin approval if required). A consent challenge is not successful retrieval.

## Host and invoke

Package `hosted_agent.py` with `requirements.txt` for Python 3.13 remote build.
Entry point `python hosted_agent.py`, Responses protocol `2.0.0`. Configure:

```text
FOUNDRY_PROJECT_ENDPOINT=<your project endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<your model deployment>
TOOLBOX_ENDPOINT=<printed Toolbox endpoint>
```

Follow the [official hosted publishing workflow](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent).
`FoundryChatClient` calls the model, `FoundryToolbox` handles managed tool calls,
and `ResponsesHostServer` supplies hosted context. Local hosting is not a substitute.
The agent does not implement manual OAuth/OBO. Invoke an existing Active version
configured for this Toolbox without redeploying:

```powershell
$env:AGENT_NAME = "<hosted-agent-name>"
$env:AGENT_VERSION = "<active-version>"
$env:QUESTION = 'Call probe_echo with experiment_id "11111111-2222-4333-8444-555555555555", message "oauth-toolbox", count 1. Return the real result.'
$env:EXPECTED_TEXT = "CUSTOM_MCP_ENTRA_VALIDATED"
python .\invoke_hosted.py
```

The CLI caller uses `https://ai.azure.com/.default`, pins/verifies the session and
leaves agent defaults unchanged, with storage disabled. HTTP, session, response,
tool and consent failures raise errors; complete consent in Foundry and retry.
Compare returned arguments and validated `oid` with the consenting user, not the
OAuth client ID. An optional marker is not proof of grant type. Only nonsensitive
demo input: responses print, and service diagnostics may capture bodies.
