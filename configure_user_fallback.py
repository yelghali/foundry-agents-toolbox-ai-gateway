"""Add isolated Entra OAuth connections and Toolboxes; retain C's working managed-user path."""

import hashlib
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPToolboxTool, OpenApiToolboxTool

import common as cm
from publish_agents import http_relay


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    config = cm.load_config()
    cm.standard_apim_id(config)
    cohort = next(item for item in config["cohorts"] if item["label"] == "c")
    azd = shutil.which("azd")
    if not azd:
        raise RuntimeError("Azure Developer CLI is required for OAuth connection creation.")
    credential = cm.credential(config)
    headers = {"Authorization": "Bearer " + credential.get_token("https://graph.microsoft.com/.default").token}

    def graph(method, resource, **kwargs):
        response = requests.request(
            method, f"https://graph.microsoft.com/v1.0/{resource}", headers=headers, timeout=90, **kwargs,
        )
        response.raise_for_status()
        return response.json() if response.content else None

    name = "abc-c-search-oauth-" + hashlib.sha256(cohort["project"]["id"].encode()).hexdigest()[:8]
    apps = graph("GET", "applications", params={"$filter": f"displayName eq '{name}'"})["value"]
    if len(apps) > 1:
        raise RuntimeError("The isolated OAuth application name is ambiguous.")
    app = apps[0] if apps else graph("POST", "applications", json={
        "displayName": name, "signInAudience": "AzureADMyOrg",
    })
    search = graph("GET", "servicePrincipals", params={
        "$filter": "servicePrincipalNames/any(x:x eq 'https://search.azure.com')",
    })["value"]
    if len(search) != 1:
        raise RuntimeError("The Search resource service principal is ambiguous.")
    search = search[0]
    scope = next(item for item in search["oauth2PermissionScopes"] if item["value"] == "user_impersonation")
    graph("PATCH", f"applications/{app['id']}", json={"requiredResourceAccess": [{
        "resourceAppId": search["appId"], "resourceAccess": [{"id": scope["id"], "type": "Scope"}],
    }]})
    principals = graph("GET", "servicePrincipals", params={"$filter": f"appId eq '{app['appId']}'"})["value"]
    if len(principals) > 1:
        raise RuntimeError("The isolated OAuth service principal is ambiguous.")
    if not principals:
        graph("POST", "servicePrincipals", json={"appId": app["appId"]})
    fallback = cohort.setdefault("oauthFallback", {})
    fallback.update({"clientId": app["appId"], "applicationId": app["id"],
                     "scope": "https://search.azure.com/user_impersonation"})
    tenant_url = f"https://login.microsoftonline.com/{config['tenantId']}/oauth2/v2.0"
    for key, connection_name, endpoint in (
        ("indexConnectionId", "raw-c-oauth", cohort["searchEndpoint"]),
        ("kbConnectionId", "iq-c-oauth", cohort["kbEndpoint"]),
    ):
        if key in fallback:
            existing = cm.arm(config, "GET", fallback[key])["properties"]
            if existing["authType"] != "OAuth2" or existing["target"] != endpoint:
                raise RuntimeError("An existing fallback connection has unexpected authentication or target.")
            continue
        secret = graph("POST", f"applications/{app['id']}/addPassword", json={"passwordCredential": {
            "displayName": connection_name,
            "endDateTime": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }})
        try:
            result = subprocess.run([
                azd, "ai", "connection", "create", connection_name, "--kind", "remote-tool",
                "--target", endpoint, "--auth-type", "oauth2",
                "--authorization-url", tenant_url + "/authorize", "--token-url", tenant_url + "/token",
                "--refresh-url", tenant_url + "/token", "--client-id", app["appId"],
                "--client-secret", secret["secretText"], "--scopes", fallback["scope"] + " offline_access",
                "--project-endpoint", cohort["project"]["endpoint"], "--no-prompt", "--force",
            ], capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Creating the isolated OAuth connection timed out.") from None
        if result.returncode:
            raise RuntimeError(result.stderr.replace(secret["secretText"], "<redacted>"))
        fallback[key] = cohort["project"]["id"] + "/connections/" + connection_name
        fallback.setdefault("passwordExpiry", {})[connection_name] = secret["endDateTime"]
        cm.save_config(config, "c")
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=credential)
    tools = [
        OpenApiToolboxTool(name="search_index_c", openapi=cm.raw_search_tool(cohort, fallback["indexConnectionId"])),
        MCPToolboxTool(name="retrieve_kb_c", server_label="iq_c", server_url=cohort["kbEndpoint"],
                      project_connection_id=fallback["kbConnectionId"], require_approval="never"),
    ]
    toolbox = project.toolboxes.create_version(name="cohort-tools-oauth", tools=tools)
    project.toolboxes.update(name="cohort-tools-oauth", default_version=toolbox.version)
    fallback["toolboxEndpoint"] = cohort["project"]["endpoint"] + "/toolboxes/cohort-tools-oauth/mcp?api-version=v1"
    fallback["toolboxIngressConnectionId"] = cm.connection(
        config, cohort, "abc-c-toolbox-oauth-ingress", fallback["toolboxEndpoint"],
        "AgenticIdentityToken", audience="https://ai.azure.com",
    )
    cm.save_config(config, "c")
    copy = {**cohort, **fallback}
    http_relay(config, copy, suffix="toolbox-oauth-http")
    fallback["apimEndpoint"] = copy["httpRelayEndpoint"]
    fallback["apimIngressConnectionId"] = copy["httpRelayConnectionId"]
    fallback["apimApiId"] = copy["httpRelayApiId"]
    cm.save_config(config, "c")
    print("Added isolated C Entra OAuth fallback and APIM API. Managed connections were not changed.")
    print("No Search data role was assigned to the OAuth application, project C, or its agents.")
    print("Per-user browser consent is still required for each new OAuth connection.")


if __name__ == "__main__":
    main()
