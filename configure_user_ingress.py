"""Add a C user-facing agent gateway without proxying Toolbox's managed Search tokens."""

import argparse
from urllib.parse import urlsplit

import common as cm


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    config = cm.load_config()
    cohort = next(item for item in config["cohorts"] if item["label"] == "c")
    base = cm.standard_apim_id(config)
    name = "abc-c-agent-ingress"
    api_id = base + "/apis/" + name
    parts = urlsplit(cohort["project"]["endpoint"])
    cm.arm(config, "PUT", api_id, {"properties": {
        "displayName": "ABC C user-authenticated agent ingress",
        "path": name, "protocols": ["https"], "subscriptionRequired": False,
        "serviceUrl": f"{parts.scheme}://{parts.netloc}",
    }}, version="2024-05-01")
    for kind, path in (
        ("prompt", parts.path + "/openai/v1/responses"),
        ("hosted", parts.path + "/agents/hosted-c/endpoint/protocols/openai/responses"),
    ):
        cm.arm(config, "PUT", api_id + "/operations/" + kind, {"properties": {
            "displayName": kind, "method": "POST", "urlTemplate": "/" + kind,
            "responses": [{"statusCode": 200}],
        }}, version="2024-05-01")
        policy = f"""<policies><inbound>
<validate-azure-ad-token tenant-id="{config['tenantId']}" header-name="Authorization" output-token-variable-name="caller">
<audiences><audience>https://ai.azure.com</audience><audience>https://ai.azure.com/</audience></audiences>
</validate-azure-ad-token>
<choose><when condition="@(!((Jwt)context.Variables[&quot;caller&quot;]).Claims.ContainsKey(&quot;scp&quot;))">
<return-response><set-status code="403" reason="Delegated user token required" />
<set-body>{{"error":{{"code":"delegated_user_required"}}}}</set-body></return-response>
</when></choose>
<rewrite-uri template="{path}" copy-unmatched-params="true" />
<set-header name="Host" exists-action="override"><value>{parts.netloc}</value></set-header>
<trace source="abc-user-ingress" severity="information">
<message>User-authenticated agent request; downstream Toolbox authentication remains native.</message>
<metadata name="mcp_server_id" value="@(context.Api.Id)" />
<metadata name="user_oid" value="@(String.Join(&quot;,&quot;, ((Jwt)context.Variables[&quot;caller&quot;]).Claims.GetValueOrDefault(&quot;oid&quot;, new string[0])))" />
<metadata name="client_request_id" value="@(context.Request.Headers.GetValueOrDefault(&quot;x-client-request-id&quot;, &quot;&quot;))" />
<metadata name="apim_request_id" value="@(context.RequestId.ToString())" />
<metadata name="agent_kind" value="{kind}" />
</trace></inbound><backend><forward-request timeout="180" buffer-response="false" /></backend>
<outbound><trace source="abc-user-ingress" severity="information"><message>Agent ingress response.</message>
<metadata name="mcp_server_id" value="@(context.Api.Id)" />
<metadata name="apim_request_id" value="@(context.RequestId.ToString())" />
<metadata name="backend_status" value="@(context.Response.StatusCode.ToString())" />
</trace></outbound><on-error><trace source="abc-user-ingress" severity="error">
<message>@(context.LastError.Message)</message></trace></on-error></policies>"""
        cm.arm(config, "PUT", api_id + "/operations/" + kind + "/policies/policy", {
            "properties": {"format": "rawxml", "value": policy},
        }, version="2024-05-01")
    diagnostic = cm.arm(config, "GET", cohort["apimApiId"] + "/diagnostics/applicationinsights",
                        version="2025-09-01-preview")["properties"]
    cm.arm(config, "PUT", api_id + "/diagnostics/applicationinsights",
           {"properties": diagnostic}, version="2024-05-01")
    endpoint = cm.arm(config, "GET", base, version="2024-05-01")["properties"]["gatewayUrl"] + "/" + name
    cohort["userIngress"] = {"apiId": api_id, "endpoint": endpoint,
                             "downstreamRoute": "toolbox", "searchTokenExchange": False}
    cm.save_config(config, "c")
    print("Added isolated user -> APIM -> C agent ingress; downstream managed Entra connections unchanged.")


if __name__ == "__main__":
    main()
