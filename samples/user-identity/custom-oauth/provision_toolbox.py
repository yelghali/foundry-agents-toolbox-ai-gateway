"""C custom: provision an OAuth2 Toolbox; authorization code/refresh, not JWT OBO."""

import os
import shutil
import subprocess

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPToolboxTool
from azure.identity import AzureCliCredential


def main():
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
    project_id = os.environ["FOUNDRY_PROJECT_RESOURCE_ID"].rstrip("/")
    name = os.environ["CONNECTION_NAME"]
    toolbox_name = os.environ["TOOLBOX_NAME"]
    target = os.environ["MCP_SERVER_URL"]
    if not endpoint.startswith("https://") or not target.startswith("https://"):
        raise ValueError("Project and MCP endpoints must use HTTPS")
    if "/" in name or "/" in toolbox_name:
        raise ValueError("Connection and Toolbox names must not contain '/'")
    connection_id = f"{project_id}/connections/{name}"
    credential = AzureCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
    token = credential.get_token("https://management.azure.com/.default").token
    azd = shutil.which("azd")
    if azd is None:
        raise RuntimeError("Install Azure Developer CLI with 'azd ai connection create' support")
    base = f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/"
    secret = os.environ["OAUTH_CLIENT_SECRET"]
    # azd takes the secret in argv. Redact diagnostics and suppress secret-bearing exceptions.
    try:
        result = subprocess.run([
            azd, "ai", "connection", "create", name, "--kind", "remote-tool",
            "--target", target, "--auth-type", "oauth2",
            "--authorization-url", base + "authorize", "--token-url", base + "token",
            "--refresh-url", base + "token", "--client-id", os.environ["OAUTH_CLIENT_ID"],
            "--client-secret", secret, "--scopes", os.environ["OAUTH_SCOPE"] + " offline_access",
            "--project-endpoint", endpoint, "--no-prompt", "--force",
        ], capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        raise RuntimeError("OAuth connection creation timed out; inspect its state in Foundry before retrying") from None
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr).replace(secret, "<redacted>"))
    response = requests.get(
        f"https://management.azure.com{connection_id}?api-version=2025-10-01-preview",
        headers={"Authorization": "Bearer " + token}, timeout=120,
    )
    response.raise_for_status()
    print("Register this exact Web redirect URI on your OAuth client app:",
          response.json()["properties"]["redirectUrl"])
    print("Complete the user's connection consent in Foundry before invoking the agent.")
    with AIProjectClient(endpoint=endpoint, credential=credential) as project:
        version = project.toolboxes.create_version(
            name=toolbox_name,
            tools=[MCPToolboxTool(
                name="retrieve", server_label="custom_probe", server_url=target,
                project_connection_id=connection_id, require_approval="never",
            )],
        )
        project.toolboxes.update(name=toolbox_name, default_version=version.version)
    print("Toolbox version:", version.version)
    print("TOOLBOX_ENDPOINT=" + endpoint + f"/toolboxes/{toolbox_name}/mcp?api-version=v1")


if __name__ == "__main__":
    main()
