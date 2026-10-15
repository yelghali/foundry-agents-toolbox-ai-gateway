"""Add a B Toolbox -> APIM -> Search comparison, preserving each caller's agent identity."""

import json
import argparse
from urllib.parse import urlsplit

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPToolboxTool, OpenApiToolboxTool

import common as cm


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    config = cm.load_config()
    cohort = next(item for item in config["cohorts"] if item["label"] == "b")
    base = cm.standard_apim_id(config)
    name = "abc-b-search-data"
    api_id = base + "/apis/" + name
    cm.arm(config, "PUT", api_id, {"properties": {
        "displayName": "ABC B agent-authenticated Search data gateway",
        "path": name, "protocols": ["https"], "subscriptionRequired": False,
        "serviceUrl": cohort["searchEndpoint"],
    }}, version="2024-05-01")
    for suffix, method, path in (
        ("raw-search", "POST", f"/indexes/{cohort['indexName']}/docs/search"),
        ("kb-post", "POST", f"/knowledgebases/{cohort['knowledgeBaseName']}/mcp"),
        ("kb-get", "GET", f"/knowledgebases/{cohort['knowledgeBaseName']}/mcp"),
        ("kb-delete", "DELETE", f"/knowledgebases/{cohort['knowledgeBaseName']}/mcp"),
    ):
        cm.arm(config, "PUT", api_id + "/operations/" + suffix, {"properties": {
            "displayName": suffix, "method": method, "urlTemplate": path,
            "responses": [{"statusCode": 200}],
        }}, version="2024-05-01")
    host = urlsplit(cohort["searchEndpoint"]).netloc
    policy = f"""<policies><inbound>
<validate-azure-ad-token tenant-id="{config['tenantId']}" header-name="Authorization" output-token-variable-name="data-caller">
<audiences><audience>https://search.azure.com</audience><audience>https://search.azure.com/</audience></audiences>
</validate-azure-ad-token>
<set-header name="Host" exists-action="override"><value>{host}</value></set-header>
<trace source="abc-data-gateway" severity="information">
<message>Search data request; original agent bearer forwarded.</message>
<metadata name="mcp_server_id" value="@(context.Api.Id)" />
<metadata name="data_principal_oid" value="@(String.Join(&quot;,&quot;, ((Jwt)context.Variables[&quot;data-caller&quot;]).Claims.GetValueOrDefault(&quot;oid&quot;, new string[0])))" />
<metadata name="observed_operation_path" value="@(context.Request.Url.Path)" />
<metadata name="apim_request_id" value="@(context.RequestId.ToString())" />
</trace></inbound><backend><forward-request timeout="180" buffer-response="false" /></backend>
<outbound><trace source="abc-data-gateway" severity="information"><message>Search data response.</message>
<metadata name="mcp_server_id" value="@(context.Api.Id)" />
<metadata name="apim_request_id" value="@(context.RequestId.ToString())" />
<metadata name="backend_status" value="@(context.Response.StatusCode.ToString())" />
</trace></outbound><on-error><trace source="abc-data-gateway" severity="error">
<message>@(context.LastError.Message)</message></trace></on-error></policies>"""
    cm.arm(config, "PUT", api_id + "/policies/policy", {
        "properties": {"format": "rawxml", "value": policy},
    }, version="2024-05-01")
    diagnostic = cm.arm(config, "GET", cohort["apimApiId"] + "/diagnostics/applicationinsights",
                        version="2025-09-01-preview")["properties"]
    cm.arm(config, "PUT", api_id + "/diagnostics/applicationinsights",
           {"properties": diagnostic}, version="2024-05-01")
    gateway = cm.arm(config, "GET", base, version="2024-05-01")["properties"]["gatewayUrl"] + "/" + name
    raw = cm.connection(config, cohort, "raw-b-data-gateway", gateway, "AgenticIdentityToken")
    kb = cm.connection(
        config, cohort, "iq-b-data-gateway",
        f"{gateway}/knowledgebases/{cohort['knowledgeBaseName']}/mcp?api-version={cm.SEARCH_VERSION}",
        "AgenticIdentityToken",
    )
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
    toolbox = project.toolboxes.create_version(name="cohort-tools-data-gateway", tools=[
        OpenApiToolboxTool(name="search_index_b", openapi=cm.raw_search_tool(
            {**cohort, "searchEndpoint": gateway}, raw,
        )),
        MCPToolboxTool(name="retrieve_kb_b", server_label="iq_b",
                      server_url=f"{gateway}/knowledgebases/{cohort['knowledgeBaseName']}/mcp?api-version={cm.SEARCH_VERSION}",
                      project_connection_id=kb, require_approval="never"),
    ])
    project.toolboxes.update(name="cohort-tools-data-gateway", default_version=toolbox.version)
    endpoint = cohort["project"]["endpoint"] + "/toolboxes/cohort-tools-data-gateway/mcp?api-version=v1"
    ingress = cm.connection(config, cohort, "abc-b-data-tools-ingress", endpoint,
                            "AgenticIdentityToken", audience="https://ai.azure.com")
    cohort["dataGateway"] = {"apiId": api_id, "gatewayEndpoint": gateway,
                             "toolboxEndpoint": endpoint, "toolboxIngressConnectionId": ingress,
                             "indexConnectionId": raw, "kbConnectionId": kb}
    cm.save_config(config, "b")
    print("Added B downstream data gateway; no new Search data roles or token exchanges.")


if __name__ == "__main__":
    main()
