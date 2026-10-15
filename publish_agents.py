"""Deploy the identity showcase and versioned direct/MCP/Toolbox/APIM prompt and hosted routes."""

import argparse
import json
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AISearchIndexResource, AgentVersionStatus, AzureAISearchTool, AzureAISearchToolResource,
    CodeConfiguration, HostedAgentDefinition, MCPTool, MCPToolboxTool, PromptAgentDefinition,
    ProtocolVersionRecord,
    OpenApiTool,
    OpenApiToolboxTool,
    A2AProtocolConfiguration, AgentCard, AgentCardSkill, AgentEndpointConfig,
    ProtocolConfiguration, ResponsesProtocolConfiguration,
    VersionSelector, FixedRatioVersionSelectionRule,
)

import common as cm


def wait(project, name, version):
    deadline = time.monotonic() + 900
    while version.status == AgentVersionStatus.CREATING:
        if time.monotonic() > deadline:
            raise TimeoutError(f"Hosted build for {name} exceeded 15 minutes.")
        time.sleep(15)
        version = project.agents.get_version(agent_name=name, agent_version=version.version)
        print(f"  {name}: {version.status}", flush=True)
    if version.status != AgentVersionStatus.ACTIVE:
        raise RuntimeError(f"Hosted build failed for {name} v{version.version}: {version.error}")
    return version


def relay(config: dict, cohort: dict, suffix: str = "toolbox"):
    base = config["apimResourceId"]
    name = f"abc-{cohort['label']}-{suffix}"
    logger_id = f"{base}/loggers/{name}"
    cm.arm(config, "PUT", logger_id, {"properties": {
        "loggerType": "applicationInsights", "resourceId": cohort["telemetry"]["appInsightsResourceId"],
        "credentials": {"instrumentationKey": cohort["telemetrySettings"]["instrumentationKey"]},
        "isBuffered": True,
    }}, version="2024-05-01")
    backend_name = f"{name}-backend"
    parts = urlsplit(cohort["toolboxEndpoint"])
    cm.arm(config, "PUT", f"{base}/backends/{backend_name}", {"properties": {
        "protocol": "http", "url": f"{parts.scheme}://{parts.netloc}",
    }}, version="2025-09-01-preview")
    api_id = f"{base}/apis/{name}"
    cm.arm(config, "PUT", api_id, {"properties": {
        "displayName": f"ABC project {cohort['label'].upper()} Toolbox MCP",
        "type": "mcp", "path": name, "protocols": ["https"], "subscriptionRequired": False,
        "backendId": backend_name,
        "mcpProperties": {"endpoints": {"mcp": {"uriTemplate": parts.path}}},
    }}, version="2025-09-01-preview")
    policy = (cm.ROOT / "policies" / "toolbox-proxy-policy.xml").read_text()
    for key, value in (("{tenant-id}", config["tenantId"]),
                       ("{toolbox-endpoint}", cohort["toolboxEndpoint"]),
                       ("{toolbox-host}", parts.netloc)):
        policy = policy.replace(key, value)
    cm.arm(config, "PUT", api_id + "/policies/policy", {"properties": {"format": "rawxml", "value": policy}},
           version="2025-09-01-preview")
    messages = {"request": {"body": {"bytes": 0}, "headers": ["traceparent"]},
                "response": {"body": {"bytes": 0}, "headers": []}}
    cm.arm(config, "PUT", api_id + "/diagnostics/applicationinsights", {"properties": {
        "loggerId": logger_id, "sampling": {"samplingType": "fixed", "percentage": 100},
        "alwaysLog": "allErrors", "verbosity": "information", "logClientIp": False,
        "frontend": messages, "backend": messages, "httpCorrelationProtocol": "W3C",
    }}, version="2025-09-01-preview")
    service = cm.arm(config, "GET", base, version="2024-05-01")
    cohort["apimEndpoint"] = f"{service['properties']['gatewayUrl']}/{name}{parts.path}?api-version=v1"
    cohort["apimApiId"] = api_id
    platform_auth = "ProjectManagedIdentity" if cohort["label"] == "a" else "AgenticIdentityToken"
    cohort["toolboxIngressConnectionId"] = cm.connection(
        config, cohort, f"abc-{cohort['label']}-{suffix}-ingress", cohort["toolboxEndpoint"],
        platform_auth, audience="https://ai.azure.com",
    )
    cohort["apimIngressConnectionId"] = cm.connection(
        config, cohort, f"abc-{cohort['label']}-{suffix}-apim-ingress", cohort["apimEndpoint"],
        platform_auth, audience="https://ai.azure.com",
    )
    cohort["indexIngressConnectionId"] = cm.connection(
        config, cohort, f"abc-{cohort['label']}-index-ingress", cohort["indexMcpEndpoint"],
        platform_auth, audience="https://ai.azure.com",
    )
    if cohort["label"] == "a":
        cm.grant(config, cohort["project"]["principalId"], cohort["project"]["id"], cm.FOUNDRY_USER_ROLE_ID)


def http_relay(config: dict, cohort: dict, suffix: str = "toolbox-http") -> None:
    base = cohort["apimApiId"].split("/apis/")[0]
    name = f"abc-{cohort['label']}-{suffix}"
    api_id = f"{base}/apis/{name}"
    parts = urlsplit(cohort["toolboxEndpoint"])
    cm.arm(config, "PUT", api_id, {"properties": {
        "displayName": f"ABC {cohort['label'].upper()} Entra OAuth Toolbox HTTP relay",
        "path": name, "protocols": ["https"], "subscriptionRequired": False,
        "serviceUrl": f"{parts.scheme}://{parts.netloc}",
    }}, version="2024-05-01")
    for method in ("GET", "POST", "DELETE"):
        cm.arm(config, "PUT", api_id + f"/operations/{method.lower()}", {"properties": {
            "displayName": method, "method": method, "urlTemplate": "/",
            "responses": [{"statusCode": 200}],
        }}, version="2024-05-01")
    policy = (cm.ROOT / "policies" / "toolbox-proxy-policy.xml").read_text()
    for key, value in (("{tenant-id}", config["tenantId"]), ("{toolbox-host}", parts.netloc),
                       ("{toolbox-endpoint}", cohort["toolboxEndpoint"])):
        policy = policy.replace(key, value)
    policy = policy.replace("<inbound>", f'<inbound><rewrite-uri template="{parts.path}" />')
    cm.arm(config, "PUT", api_id + "/policies/policy", {
        "properties": {"format": "rawxml", "value": policy},
    }, version="2024-05-01")
    diagnostics = cm.arm(config, "GET", cohort["apimApiId"] + "/diagnostics/applicationinsights",
                         version="2025-09-01-preview")["properties"]
    cm.arm(config, "PUT", api_id + "/diagnostics/applicationinsights", {"properties": diagnostics},
           version="2024-05-01")
    service = cm.arm(config, "GET", base, version="2024-05-01")
    cohort["httpRelayEndpoint"] = f"{service['properties']['gatewayUrl']}/{name}/?api-version=v1"
    cohort["httpRelayConnectionId"] = cm.connection(
        config, cohort, f"abc-{cohort['label']}-{suffix}-http-ingress", cohort["httpRelayEndpoint"],
        "ProjectManagedIdentity" if cohort["label"] == "a" else "AgenticIdentityToken",
        audience="https://ai.azure.com",
    )
    cohort["httpRelayApiId"] = api_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", choices=("a", "b", "c"), required=True)
    parser.add_argument("--routes", nargs="+", choices=(
        "direct", "mcp", "toolbox", "apim", "apim-http", "toolbox-oauth", "apim-oauth", "data-gateway", "native-user",
    ),
                        default=["direct", "toolbox"])
    parser.add_argument("--showcase", action="store_true")
    parser.add_argument("--only-agent", help="Publish only one showcase agent or cohort agent.")
    args = parser.parse_args()
    config = cm.load_config()
    cohort = next(c for c in config["cohorts"] if c["label"] == args.cohort)
    label = cohort["label"]
    if any(route.endswith("-oauth") for route in args.routes):
        if label != "c" or not cohort.get("oauthFallback"):
            parser.error("OAuth routes require the isolated C fallback to be configured first.")
    if "data-gateway" in args.routes and (label != "b" or not cohort.get("dataGateway")):
        parser.error("The data-gateway route requires the isolated B gateway first.")
    if "native-user" in args.routes and (label != "c" or not cohort.get("nativeUserSearch")):
        parser.error("The native-user route requires the isolated C native source first.")
    allowed_agents = [f"prompt-{label}", f"hosted-{label}"]
    allowed_agents += {"a": ["agent-ab-denied", "a-orchestrator"],
                       "b": ["b-confidential", "agent-bc-denied"], "c": []}[label]
    if args.only_agent and args.only_agent not in allowed_agents:
        parser.error("--only-agent must belong to the selected cohort.")
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
    if not cohort.get("apimEndpoint"):
        relay(config, cohort)
    if "apim-http" in args.routes and not cohort.get("httpRelayEndpoint"):
        http_relay(config, cohort)
    cm.save_config(config, label)
    agents = cohort.setdefault("agents", {})

    def roles(name, version, data_reader):
        identity = version.instance_identity or project.agents.get(agent_name=name).instance_identity
        if identity is None:
            raise RuntimeError(f"No instance identity for {name}.")
        cm.grant(config, identity.principal_id, cohort["project"]["id"], cm.FOUNDRY_USER_ROLE_ID)
        if data_reader:
            cm.grant(config, identity.principal_id, cohort["searchId"], cm.SEARCH_INDEX_DATA_READER_ROLE_ID)
        if name == "hosted-a":
            project.agents.update_details(
                agent_name=name,
                agent_endpoint=AgentEndpointConfig(protocol_configuration=ProtocolConfiguration(
                    responses=ResponsesProtocolConfiguration(), a2a=A2AProtocolConfiguration(),
                )),
                agent_card=AgentCard(
                    version="1.0", description="Retrieve only cohort A evidence.",
                    skills=[AgentCardSkill(id="cohort-a", name="Cohort A evidence",
                                           description="Query index A or KB A with project A identity.")],
                ),
            )
        return identity.principal_id

    def record(name, route, version, principal, kind, target):
        item = agents.setdefault(name, {"kind": kind, "principalId": principal, "versions": {}})
        if item["principalId"] != principal:
            raise RuntimeError("An agent identity changed between route versions.")
        item["versions"][route] = str(version.version)
        item["targetCohort"] = target["label"]
        cm.save_config(config, label)

    def prompt(name, route, target=cohort):
        if route.endswith("-oauth"):
            target = {**target, **target["oauthFallback"]}
        if route == "data-gateway":
            target = {**target, **target["dataGateway"]}
        if route == "native-user":
            target = {**target, **target["nativeUserSearch"]}
        if route == "direct":
            tools = [
                MCPTool(server_label="raw_index", server_url=target["indexMcpEndpoint"],
                        project_connection_id=target["indexIngressConnectionId"], require_approval="never"),
                MCPTool(server_label="iq", server_url=target["kbEndpoint"],
                        project_connection_id=target["kbConnectionId"], require_approval="never"),
            ]
        else:
            url, conn = {
                "apim": (target["apimEndpoint"], target["apimIngressConnectionId"]),
                "apim-oauth": (target["apimEndpoint"], target["apimIngressConnectionId"]),
                "apim-http": (target.get("httpRelayEndpoint"), target.get("httpRelayConnectionId")),
            }.get(route, (target["toolboxEndpoint"], target["toolboxIngressConnectionId"]))
            tools = [MCPTool(server_label="cohort_tools", server_url=url,
                             project_connection_id=conn, require_approval="never")]
        version = project.agents.create_version(
            agent_name=name, definition=PromptAgentDefinition(
                model=config["modelDeploymentName"],
                instructions="Always use the requested index or IQ tool. Return the exact retrieved marker; never invent data or authorization outcomes.",
                tools=tools,
            ),
        )
        principal = roles(name, version, label == "b")
        record(name, route, version, principal, "prompt", target)
        print(f"  Published {name} {route}: v{version.version}", flush=True)

    def hosted(name, route, target=cohort, confidential=False):
        if route.endswith("-oauth"):
            target = {**target, **target["oauthFallback"]}
        if route == "data-gateway":
            target = {**target, **target["dataGateway"]}
        if route == "native-user":
            target = {**target, **target["nativeUserSearch"]}
        actual_route = "rest" if route == "direct" and label == "b" else (
            "mcp" if route in ("direct", "mcp") else route
        )
        if route == "orchestrator":
            actual_route = route
        server_config = {
            "project": cohort["project"]["name"], "agent": name,
            "route": actual_route, "identity_mode": cohort["identityMode"],
            "search_endpoint": target["searchEndpoint"], "index": target["indexName"],
            "kb": target["knowledgeBaseName"], "index_mcp": target["indexMcpEndpoint"],
            "iq_mcp": target["iqMcpEndpoint"],
            "toolbox_endpoint": (target["apimEndpoint"] if route in ("apim", "apim-oauth") else
                                 target["httpRelayEndpoint"] if route == "apim-http" else target["toolboxEndpoint"]),
            "telemetry": cohort["telemetrySettings"], "confidential": confidential,
            "model_endpoint": config["foundryOpenAIEndpoint"],
        }
        if actual_route == "orchestrator":
            server_config["peer_versions"] = {
                peer: agents[peer]["versions"]["direct"] for peer in ("prompt-a", "hosted-a")
            }
        with tempfile.TemporaryDirectory(prefix="abc-hosted-") as temp:
            archive = Path(temp) / "agent.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for filename in ("main.py", "requirements.txt"):
                    bundle.write(cm.ROOT / "hosted" / filename, filename)
            with archive.open("rb") as code:
                version = project.agents.create_version_from_code(
                    agent_name=name, code=code,
                    definition=HostedAgentDefinition(
                        cpu="0.5", memory="1Gi",
                        code_configuration=CodeConfiguration(
                            runtime="python_3_13", entry_point=["python", "main.py"],
                            dependency_resolution="remote_build",
                        ),
                        protocol_versions=[ProtocolVersionRecord(protocol="responses", version="2.0.0")],
                        environment_variables={
                            "AZURE_AI_MODEL_DEPLOYMENT_NAME": config["modelDeploymentName"],
                            "ABC_AGENT_CONFIG": json.dumps(server_config),
                            "APPLICATIONINSIGHTS_CONNECTION_STRING": cohort["telemetrySettings"]["connectionString"],
                            "ENABLE_SENSITIVE_DATA": "false",
                            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false",
                            "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED": "false",
                        },
                    ),
                )
        version = wait(project, name, version)
        principal = roles(name, version, label == "b")
        if confidential:
            account_scope = cohort["project"]["id"].split("/projects/")[0]
            cm.grant(config, principal, account_scope, "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd")
        record(name, route, version, principal, "hosted", target)
        print(f"  Published {name} {route}: v{version.version}", flush=True)

    for route in args.routes:
        if not args.only_agent or args.only_agent == f"prompt-{label}":
            prompt(f"prompt-{label}", route)
        if not args.only_agent or args.only_agent == f"hosted-{label}":
            hosted(f"hosted-{label}", route)
    if args.showcase and label == "a" and args.only_agent in (None, "agent-ab-denied"):
        target = next(c for c in config["cohorts"] if c["label"] == "b")
        kb_conn = cm.connection(config, cohort, "abc-a-deny-iq-b", target["kbEndpoint"], "ProjectManagedIdentity")
        index_conn = cm.connection(config, cohort, "abc-a-deny-index-b", target["searchEndpoint"],
                                   "ProjectManagedIdentity")
        denied_box = project.toolboxes.create_version(name="deny-b-index", tools=[
            OpenApiToolboxTool(name="search_index_b", openapi=cm.raw_search_tool(target, index_conn)),
        ])
        project.toolboxes.update(name="deny-b-index", default_version=denied_box.version)
        denied_endpoint = f"{cohort['project']['endpoint']}/toolboxes/deny-b-index/mcp?api-version=v1"
        ingress = cm.connection(config, cohort, "abc-a-deny-index-ingress", denied_endpoint,
                                "ProjectManagedIdentity", audience="https://ai.azure.com")
        prompt("agent-ab-denied", "direct", {
            **target, "kbConnectionId": kb_conn, "indexConnectionId": index_conn,
            "indexMcpEndpoint": denied_endpoint, "indexIngressConnectionId": ingress,
        })
    if args.showcase and label == "a" and args.only_agent in (None, "a-orchestrator"):
        hosted("a-orchestrator", "orchestrator")
    if args.showcase and label == "b":
        if args.only_agent in (None, "b-confidential"):
            hosted("b-confidential", "direct", confidential=True)
        if args.only_agent in (None, "agent-bc-denied"):
            target = next(c for c in config["cohorts"] if c["label"] == "c")
            hosted("agent-bc-denied", "direct", target)
    preferred_route = {"a": "apim", "b": "data-gateway", "c": "toolbox"}[label]
    if any(item["versions"].get(preferred_route) for item in agents.values()):
        for name, item in agents.items():
            if name not in (f"prompt-{label}", f"hosted-{label}"):
                continue
            version = item["versions"].get(preferred_route)
            if version:
                endpoint = project.agents.get(agent_name=name).agent_endpoint
                endpoint.version_selector = VersionSelector(version_selection_rules=[
                    FixedRatioVersionSelectionRule(agent_version=version, traffic_percentage=100),
                ])
                project.agents.update_details(agent_name=name, agent_endpoint=endpoint)
                item["defaultRoute"] = preferred_route
        cm.save_config(config, label)


if __name__ == "__main__":
    main()
