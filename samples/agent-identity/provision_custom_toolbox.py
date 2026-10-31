"""B: custom MCP audience, fixed calling agent identity authentication."""

import os
from urllib.parse import urlsplit

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPToolboxTool
from azure.identity import AzureCliCredential


def main():
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
    project_id = os.environ["FOUNDRY_PROJECT_RESOURCE_ID"].rstrip("/")
    name = os.environ["CONNECTION_NAME"]
    toolbox_name = os.environ["TOOLBOX_NAME"]
    target = os.environ["CUSTOM_MCP_SERVER_URL"]
    audience = os.environ["CUSTOM_MCP_AUDIENCE"]
    for url in (endpoint, target):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Project and MCP endpoints must use HTTPS without credentials")
    if not audience.strip() or audience != audience.strip() or audience.endswith("/.default"):
        raise ValueError("Use the API resource audience, not a /.default scope")
    if not name or not toolbox_name or "/" in name or "/" in toolbox_name:
        raise ValueError("Connection and Toolbox names must be nonempty and contain no '/'")
    connection_id = f"{project_id}/connections/{name}"
    credential = AzureCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
    token = credential.get_token("https://management.azure.com/.default").token
    response = requests.put(
        f"https://management.azure.com{connection_id}?api-version=2025-10-01-preview",
        headers={"Authorization": "Bearer " + token},
        json={"properties": {
            "category": "RemoteTool", "authType": "AgenticIdentityToken",
            "target": target, "audience": audience,
            "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
        }}, timeout=120,
    )
    response.raise_for_status()
    with AIProjectClient(endpoint=endpoint, credential=credential) as project:
        version = project.toolboxes.create_version(
            name=toolbox_name,
            tools=[MCPToolboxTool(
                name="identity_probe", server_label="identity", server_url=target,
                project_connection_id=connection_id, require_approval="never",
            )],
        )
        project.toolboxes.update(name=toolbox_name, default_version=version.version)
    print("Toolbox version:", version.version)
    print("TOOLBOX_ENDPOINT=" + endpoint + f"/toolboxes/{toolbox_name}/mcp?api-version=v1")


if __name__ == "__main__":
    main()
