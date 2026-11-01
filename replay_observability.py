"""Additive Agent -> APIM -> Toolbox replays; never changes original agent defaults.

Only synthetic public workshop prompts are allowed. Sanitized trace metadata persists
up to 8192 bytes of prompts/results in Azure Monitor; raw diagnostic body logging is
disabled. No authorization/caller headers are logged. OAuth connections are not edited.
"""

import argparse
import json
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CodeConfiguration, HostedAgentDefinition, MCPToolboxTool,
    ProtocolVersionRecord, VersionRefIndicator,
)

import common as cm
from token_evidence import token_observation

ROOT = Path(__file__).parent
STATE = ROOT / "evidence" / "observability-deployment.json"


def safe(value):
    if isinstance(value, dict):
        return {key: ("<redacted>" if key.lower() in (
                "token", "jwt", "bearer", "consent_state", "oauth_state",
                "x-agent-foundry-call-id", "callercontext", "caller_context",
                ) or any(word in key.lower() for word in
                ("authorization", "secret", "access_token", "refresh_token", "session_id", "baggage"))
                else safe(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, str):
        if value.startswith("oacr_"):
            return "<oauth-request-id-redacted>"
        value = re.sub(r'("baggage"\s*:\s*")(?:\\.|[^"\\])*(")',
                       r'\1<baggage-redacted>\2', value)
        value = re.sub(r'(\\"baggage\\"\s*:\s*\\")[^"]*(\\")',
                       r'\1<baggage-redacted>\2', value)
        value = re.sub(r"https://[^\s\"<>\\]*consent[^\s\"<>\\]*", "<consent-url-redacted>", value)
        value = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "<jwt-redacted>", value)
        value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]+", "Bearer <redacted>", value)
    return value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(value), indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def render_policy(config, direct):
    parts = urlsplit(direct)
    policy = (ROOT / "policies" / "toolbox-proxy-policy.xml").read_text()
    for key, value in (("{tenant-id}", config["tenantId"]), ("{toolbox-host}", parts.netloc),
                       ("{toolbox-endpoint}", direct)):
        policy = policy.replace(key, value)
    policy = policy.replace("<inbound>", f'<inbound><rewrite-uri template="{parts.path}" />')
    policy = policy.replace('buffer-response="false"', 'buffer-response="true"')
    request_trace = """<trace source="isolated-observed-body" severity="information">
      <message>isolated MCP POST request body</message>
      <metadata name="apim_request_id" value="@(context.RequestId.ToString())" />
      <metadata name="api" value="@(context.Api.Id)" />
      <metadata name="body" value="@{
        if (context.Request.Body == null) { return &quot;&lt;empty-body&gt;&quot;; }
        var body = context.Request.Body.As&lt;string&gt;(preserveContent: true) ?? &quot;&quot;;
        if (body.Length == 0) { return &quot;&lt;empty-body&gt;&quot;; }
        try {
          var parsed = JObject.Parse(body);
          foreach (var baggage in parsed.SelectTokens(&quot;$..baggage&quot;).ToList()) {
            baggage.Replace(new JValue(&quot;&lt;baggage-redacted&gt;&quot;));
          }
          body = parsed.ToString(Newtonsoft.Json.Formatting.None);
        } catch { }
        body = System.Text.RegularExpressions.Regex.Replace(body, &quot;eyJ[A-Za-z0-9_-]+\\\\.[A-Za-z0-9_-]+\\\\.[A-Za-z0-9_-]+&quot;, &quot;&lt;jwt-redacted&gt;&quot;);
        body = System.Text.RegularExpressions.Regex.Replace(body, &quot;(?i)Bearer\\\\s+[A-Za-z0-9._~+/-]+&quot;, &quot;&lt;bearer-redacted&gt;&quot;);
        var cursor = 0;
        while ((cursor = body.IndexOf(&quot;https:&quot; + &quot;/&quot; + &quot;/&quot;, cursor, StringComparison.OrdinalIgnoreCase)) &gt;= 0) {
          var end = cursor;
          while (end &lt; body.Length &amp;&amp; !Char.IsWhiteSpace(body[end]) &amp;&amp; body[end] != (char)34 &amp;&amp; body[end] != (char)92 &amp;&amp; body[end] != (char)60 &amp;&amp; body[end] != (char)62) { end++; }
          var url = body.Substring(cursor, end - cursor);
          if (url.IndexOf(&quot;consent&quot;, StringComparison.OrdinalIgnoreCase) &gt;= 0) {
            body = body.Substring(0, cursor) + &quot;&lt;consent-url-redacted&gt;&quot; + body.Substring(end);
            cursor += &quot;&lt;consent-url-redacted&gt;&quot;.Length;
          } else { cursor = end; }
        }
        body = System.Text.RegularExpressions.Regex.Replace(body, &quot;oacr_[A-Za-z0-9_-]+&quot;, &quot;&lt;oauth-request-id-redacted&gt;&quot;);
        return body.Length &gt; 8192 ? body.Substring(0,8192) : body;
      }" />
    </trace>"""
    response_trace = request_trace.replace("POST request", "response").replace(
        "context.Request.Body", "context.Response.Body")
    policy = policy.replace('name="error_reason"', 'name="api" value="@(context.Api.Id)" />\n      <metadata name="error_reason"')
    policy = policy.replace("</inbound>", request_trace + "</inbound>")
    return policy.replace("<outbound>", "<outbound>" + response_trace)


def disable_raw_body_logging(config, record):
    resource = record["apiId"] + "/diagnostics/applicationinsights"
    diagnostic = cm.arm(config, "GET", resource, version="2024-05-01")["properties"]
    for side in ("frontend", "backend"):
        diagnostic[side] = {
            "request": {"headers": [], "body": {"bytes": 0}},
            "response": {"headers": [], "body": {"bytes": 0}},
        }
    diagnostic["logClientIp"] = False
    cm.arm(config, "PUT", resource, {"properties": diagnostic}, version="2024-05-01")


def deploy(config, scenario, custom, custom_endpoint, republish=False, requirements=None):
    label, kind = scenario.split("-")
    cohort = next(item for item in config["cohorts"] if item["label"] == label)
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
    name = "obs-20261031-" + scenario
    state = json.loads(STATE.read_text()) if STATE.exists() else {"scenarios": {}}
    if scenario in state["scenarios"] and not republish:
        return state["scenarios"][scenario]
    auth = {"a": "ProjectManagedIdentity", "b": "AgenticIdentityToken", "c": "UserEntraToken"}[label]
    if kind == "native":
        target, connection = cohort["kbEndpoint"], cohort["kbConnectionId"]
        tool_name = "retrieve_kb_" + label
    elif label == "c":
        target, connection = custom["endpoint"], custom["oauthConnectionId"]
        tool_name = "probe_echo"
    else:
        if not custom_endpoint:
            raise ValueError("--custom-endpoint required for application-token scenarios")
        target = custom_endpoint
        connection = cm.connection(config, cohort, name + "-data", target, auth,
                                   audience="api://" + custom["apiAppId"])
        tool_name = "identity_probe"
    toolbox = project.toolboxes.create_version(name=name, tools=[
        MCPToolboxTool(name=tool_name, server_label="observed", server_url=target,
                       project_connection_id=connection, require_approval="never"),
    ])
    # This isolated Toolbox has one version; no existing/default Toolbox is changed.
    project.toolboxes.update(name=name, default_version=toolbox.version)
    direct = cohort["project"]["endpoint"] + f"/toolboxes/{name}/mcp?api-version=v1"
    base = cohort["apimApiId"].split("/apis/")[0]
    api_id = base + "/apis/" + name
    parts = urlsplit(direct)
    cm.arm(config, "PUT", api_id, {"properties": {
        "displayName": name + " OPTIONAL body logging", "path": name,
        "protocols": ["https"], "subscriptionRequired": False,
        "serviceUrl": f"{parts.scheme}://{parts.netloc}",
    }}, version="2024-05-01")
    for method in ("GET", "POST", "DELETE"):
        cm.arm(config, "PUT", api_id + "/operations/" + method.lower(), {"properties": {
            "displayName": method, "method": method, "urlTemplate": "/",
            "responses": [{"statusCode": 200}],
        }}, version="2024-05-01")
    policy = render_policy(config, direct)
    cm.arm(config, "PUT", api_id + "/policies/policy", {
        "properties": {"format": "rawxml", "value": policy},
    }, version="2024-05-01")
    diagnostic = cm.arm(config, "GET", cohort["apimApiId"] + "/diagnostics/applicationinsights",
                        version="2025-09-01-preview")["properties"]
    for side in ("frontend", "backend"):
        diagnostic[side] = {
            "request": {"headers": [], "body": {"bytes": 0}},
            "response": {"headers": [], "body": {"bytes": 0}},
        }
    diagnostic["logClientIp"] = False
    cm.arm(config, "PUT", api_id + "/diagnostics/applicationinsights",
           {"properties": diagnostic}, version="2024-05-01")
    endpoint = cm.arm(config, "GET", base, version="2024-05-01")["properties"]["gatewayUrl"]
    endpoint += "/" + name + "/?api-version=v1"
    archive = ROOT / "build" / (name + ".zip")
    archive.parent.mkdir(exist_ok=True)
    try:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(ROOT / "hosted" / "observability_probe.py", "main.py")
            requirement_file = (requirements or ROOT / "hosted" / "observability-requirements.txt").resolve()
            if not requirement_file.is_relative_to(ROOT.resolve()):
                raise ValueError("Only repository-owned hosted requirement files may be uploaded")
            bundle.write(requirement_file, "requirements.txt")
        with archive.open("rb") as code:
            agent = project.agents.create_version_from_code(
                agent_name=name, code=code, definition=HostedAgentDefinition(
                    cpu="0.5", memory="1Gi",
                    code_configuration=CodeConfiguration(
                        runtime="python_3_13", entry_point=["python", "main.py"],
                        dependency_resolution="remote_build",
                    ),
                    protocol_versions=[ProtocolVersionRecord(protocol="responses", version="2.0.0")],
                    environment_variables={
                        "TOOLBOX_ENDPOINT": endpoint,
                        "AZURE_AI_MODEL_DEPLOYMENT_NAME": config["modelDeploymentName"],
                        "ENABLE_SENSITIVE_DATA": "false",
                        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false",
                        "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED": "false",
                    },
                ),
            )
    finally:
        archive.unlink(missing_ok=True)
    record = {
        "scenario": scenario, "createdAt": now(), "apiId": api_id, "apimEndpoint": endpoint,
        "toolboxEndpoint": direct, "toolboxVersion": toolbox.version,
        "configuredMcpDestination": target, "downstreamConnectionId": connection,
        "downstreamAuth": "OAuth2" if scenario == "c-custom" else auth,
        "agent": name, "version": agent.version, "tool": tool_name,
        "originalDefaultsModified": False, "authFallback": False,
        "requirementsFile": str(requirement_file.relative_to(ROOT.resolve())),
    }
    state["scenarios"][scenario] = record
    write(STATE, state)
    return record


def wait(config, record):
    cohort = next(item for item in config["cohorts"] if item["label"] == record["scenario"][0])
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
    deadline = time.monotonic() + 1200
    while True:
        agent = project.agents.get_version(agent_name=record["agent"], agent_version=record["version"])
        if "ACTIVE" in str(agent.status):
            resource = project.agents.get(agent_name=record["agent"])
            identity = agent.instance_identity or resource.instance_identity
            record["principalId"] = str(identity.principal_id)
            record["identityConfiguration"] = {
                "projectResourceId": cohort["project"]["id"],
                "projectManagedIdentityPrincipalId": cohort["project"]["principalId"],
                "agentDisplayName": record["agent"],
                "agentResourceId": resource.id,
                "agentInstancePrincipalId": str(identity.principal_id),
                "agentInstanceClientId": str(identity.client_id),
                "source": "Azure agent control-plane identity and configured project",
                "limitation": "Configured identities are not themselves observed token claims.",
            }
            cm.grant(config, record["principalId"], cohort["project"]["id"], cm.FOUNDRY_USER_ROLE_ID)
            if record["scenario"] == "b-native":
                cm.grant(config, record["principalId"], cohort["searchId"], cm.SEARCH_INDEX_DATA_READER_ROLE_ID)
            return project
        if "CREATING" not in str(agent.status) or time.monotonic() > deadline:
            raise RuntimeError(f"Hosted status {agent.status}: {safe(str(agent.error))}")
        print(record["scenario"], agent.status, flush=True)
        time.sleep(20)


def replay(config, record):
    project = wait(config, record)
    cohort = next(item for item in config["cohorts"] if item["label"] == record["scenario"][0])
    experiment = str(uuid.uuid4())
    if record["scenario"].endswith("native"):
        args = {"query": f"Find the normal access record in cohort {record['scenario'][0].upper()}"}
    elif record["scenario"] == "c-custom":
        args = {"experiment_id": experiment, "message": "oauth-toolbox", "count": 2}
    else:
        args = {"experiment_id": experiment}
    prompt = f"Call {record['tool']} exactly once with arguments {json.dumps(args)}. Return its exact result."
    session = project.agents.create_session(
        agent_name=record["agent"], version_indicator=VersionRefIndicator(agent_version=record["version"]),
    )
    started = now()
    caller_token = cm.credential(config).get_token("https://ai.azure.com/.default").token
    caller_observation = token_observation(
        caller_token, boundary="selected Azure CLI credential -> hosted agent endpoint",
    )
    response = requests.post(
        cohort["project"]["endpoint"] + f"/agents/{record['agent']}/endpoint/protocols/openai/responses?api-version=v1",
        headers={"Authorization": "Bearer " + caller_token,
                 "x-client-request-id": experiment},
        json={"input": prompt, "stream": False, "store": record["scenario"] == "c-custom",
              "agent_session_id": session.agent_session_id}, timeout=600,
    )
    try:
        body = response.json()
    except ValueError:
        body = response.text
    evidence = {**record, "experimentId": experiment, "startedAt": started,
                "completedAt": now(), "httpStatus": response.status_code,
                "store": record["scenario"] == "c-custom",
                "callerTokenObservation": caller_observation,
                "input": prompt, "agentResponse": safe(body),
                "verdict": "UNVERIFIED_UNTIL_APIM_AND_MCP_LOG_CORRELATION"}
    write(ROOT / "evidence" / ("observability-" + record["scenario"] + ".json"), evidence)
    write(ROOT / "evidence" / ("observability-" + record["scenario"] + "-" + experiment + ".json"), evidence)
    print(record["scenario"], "HTTP", response.status_code, flush=True)


def collect(config, record):
    cohort = next(item for item in config["cohorts"] if item["label"] == record["scenario"][0])
    query = f"""
AppTraces
| where TimeGenerated > ago(2h)
| extend p=todynamic(Properties)
| where tostring(p.api) == "{record['agent']}" or tostring(p.mcp_server_id) == "{record['agent']}"
| project TimeGenerated, Message, Properties=p
| order by TimeGenerated asc
"""
    response = requests.post(
        f"https://api.loganalytics.azure.com/v1/workspaces/{cohort['telemetry']['workspaceId']}/query",
        headers={"Authorization": "Bearer " + cm.credential(config).get_token("https://api.loganalytics.io/.default").token},
        json={"query": query}, timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    latest = ROOT / "evidence" / ("observability-" + record["scenario"] + ".json")
    exchanges = {}
    if latest.exists():
        run = json.loads(latest.read_text())
        start = datetime.fromisoformat(run["startedAt"]).timestamp() - 2
        end = datetime.fromisoformat(run["completedAt"]).timestamp() + 2
        for timestamp, message, properties in data["tables"][0]["rows"]:
            if not start <= datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() <= end:
                continue
            p = json.loads(properties) if isinstance(properties, str) else properties
            request_id = p.get("apim_request_id")
            if not request_id:
                continue
            exchange = exchanges.setdefault(request_id, {"apimRequestId": request_id})
            if message == "isolated MCP POST request body":
                exchange.update(requestTimestamp=timestamp, requestBody=p["body"])
            elif message == "isolated MCP response body":
                exchange.update(responseTimestamp=timestamp, responseBody=p["body"])
            elif message == "Toolbox MCP backend response.":
                exchange["backendStatus"] = int(p["backend_status"])
            elif "caller_context_present" in p:
                exchange["callerContextPresent"] = p["caller_context_present"]
                exchange["callerContextHash"] = p["caller_context_hash"]
                exchange["observedPlatformPrincipalId"] = p["platform_principal_oid"]
                if p.get("token_validation") == "VALIDATED_AT_APIM_ENTRA_BOUNDARY":
                    exchange["platformTokenObservation"] = {
                        "boundary": "APIM validate-azure-ad-token (https://ai.azure.com)",
                        "validation": p["token_validation"],
                        "header": json.loads(p.get("selected_token_header", "{}")),
                        "claims": json.loads(p.get("selected_token_claims", "{}")),
                        "tokenSha256": p.get("token_sha256"),
                        "forwarding": p.get("token_forwarding"),
                    }
        data["exchangesForLatestRun"] = list(exchanges.values())
        run["apimExchanges"] = data["exchangesForLatestRun"]
        calls = [item for item in run["apimExchanges"] if '"tools/call"' in item.get("requestBody", "")]
        run["verdict"] = "BLOCKED_BEFORE_TOOL_CALL" if not calls else "TOOL_CALL_CAPTURED_REVIEW_ACTUAL_RESULT"
        run["searchDownstreamQueryVisibility"] = "NOT_OBSERVED_AT_UPSTREAM_APIM"
        write(latest, run)
        write(ROOT / "evidence" / f"observability-{record['scenario']}-{run['experimentId']}.json", run)
    write(ROOT / "evidence" / ("observability-" + record["scenario"] + "-apim.json"), data)
    print(record["scenario"], "APIM trace rows", len(response.json()["tables"][0]["rows"]))


def repair_policy(config, record):
    resource = record["apiId"] + "/policies/policy"
    policy = render_policy(config, record["toolboxEndpoint"])
    try:
        cm.arm(config, "PUT", resource, {"properties": {"format": "rawxml", "value": policy}},
               version="2024-05-01")
    except requests.HTTPError as error:
        write(ROOT / "evidence" / ("observability-" + record["scenario"] + "-policy-error.json"),
              {"time": now(), "error": safe(error.response.text)})
        print(safe(error.response.text))
        raise
    print(record["scenario"], "isolated empty-body-safe tracing applied")
    disable_raw_body_logging(config, record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--custom-config", type=Path, required=True)
    parser.add_argument("--custom-endpoint")
    parser.add_argument("--requirements", type=Path, help="Repository-owned isolated hosted dependency manifest")
    parser.add_argument("--republish", action="store_true", help="Create a new isolated probe version, preserving original defaults")
    parser.add_argument("--scenario", choices=("a-native", "a-custom", "b-native", "b-custom", "c-native", "c-custom"),
                        required=True)
    parser.add_argument("--action", choices=("deploy", "replay", "collect", "repair-policy"), required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    custom = json.loads(args.custom_config.read_text(encoding="utf-8-sig"))
    if args.action == "deploy":
        print(json.dumps(deploy(config, args.scenario, custom, args.custom_endpoint, args.republish, args.requirements), indent=2))
    else:
        record = json.loads(STATE.read_text())["scenarios"][args.scenario]
        {"replay": replay, "collect": collect, "repair-policy": repair_policy}[args.action](config, record)


if __name__ == "__main__":
    main()
