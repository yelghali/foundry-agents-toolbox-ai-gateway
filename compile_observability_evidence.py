"""Compile verdicts only from real correlated APIM and validated MCP evidence."""

import json
from datetime import datetime
from replay_observability import ROOT, now, safe, write


def hosted_snapshot(run):
    """Keep service-returned tool events, not model narrative or consent payloads."""
    response = run["agentResponse"]
    events = []
    for event in response.get("output", []):
        kind = event.get("type")
        if kind not in ("function_call", "function_call_output", "oauth_consent_request"):
            continue
        fields = ("type", "name", "call_id", "arguments", "output", "status")
        events.append({key: event[key] for key in fields if key in event})
    error = response.get("error")
    if error and len(error.get("message", "")) > 240:
        error = {
            "code": error.get("code"),
            "messageExcerpt": error["message"][:240],
            "observedErrorCodes": [
                code for code in ("AADSTS500016", "AgentInstanceClientId")
                if code in error["message"]
            ],
            "fullError": f"evidence/observability-{run['scenario']}.json#agentResponse.error",
        }
    return safe({
        "source": f"evidence/observability-{run['scenario']}.json#agentResponse",
        "responseId": response.get("id"),
        "status": response.get("status"),
        "error": error,
        "events": events,
        "runtimeConsoleLog": "NOT_A_RUNTIME_LOG",
        "limitation": "Hosted service response snapshot; not a runtime console log. "
                      "Runtime console retrieval is recorded separately; model text is not tool evidence.",
    })


def delegated_evidence(run, selected, actual_result, container):
    """Correlate unchanged console arguments/claims with APIM and hosted tool output."""
    if not selected or not isinstance(actual_result, dict):
        return [], {}, False
    request = json.loads(selected.get("requestBody", "{}"))
    if request.get("method") != "tools/call":
        return [], {}, False
    args = request.get("params", {}).get("arguments")
    claims = actual_result.get("claims", {})
    config = container.get("validationConfiguration", {})
    caller = run.get("callerTokenObservation", {}).get("claims", {})
    if not config or not caller.get("oid"):
        return [], {}, False

    def timestamp(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

    start, end = timestamp(selected["requestTimestamp"]), timestamp(selected["responseTimestamp"])
    scoped = [event for event in container.get("events", [])
              if start <= timestamp(event["azureTimestamp"]) <= end]
    tools = [event for event in scoped if event.get("event") == "custom_mcp_tool"
             and event.get("arguments") == args == actual_result.get("arguments")
             and event.get("arguments", {}).get("experiment_id") == run["experimentId"]
             and event.get("claims") == claims]
    auth = [event for event in scoped if event.get("event") == "custom_mcp_auth_validated"
            and event.get("method") == "POST" and event.get("path") == "/mcp"
            and event.get("claims") == claims
            and tools and timestamp(event["azureTimestamp"]) <= timestamp(tools[0]["azureTimestamp"])]
    if len(tools) != 1 or not auth:
        return [], {}, False
    # This server logs arguments/validated claims, not its return or JWT header.
    observation = {
        "boundary": "delegated MCP signature/issuer/audience/tenant/scope validation",
        "validation": "VALIDATED_AT_MCP_BOUNDARY",
        "claims": claims,
        "source": "correlated custom_mcp_auth_validated and custom_mcp_tool console events",
        "limitation": "JWT header and validity times are NOT_OBSERVED in this server's logs. "
                      "Full return is captured at APIM and hosted function_call_output, not console.",
    }
    outputs = [event for event in run["agentResponse"].get("output", [])
               if event.get("type") == "function_call_output"]
    try:
        hosted_match = len(outputs) == 1 and json.loads(outputs[0]["output"]) == actual_result
    except (KeyError, ValueError, TypeError):
        hosted_match = False
    passed = (
        selected.get("backendStatus") == 200
        and run["agentResponse"].get("status") == "completed" and hosted_match
        and not json.loads(selected["responseBody"]).get("result", {}).get("isError", False)
        and actual_result.get("marker") == "CUSTOM_MCP_ENTRA_VALIDATED"
        and claims.get("oid") == caller["oid"]
        and claims.get("tid") == config["tenantId"]
        and claims.get("aud") == config["audience"]
        and claims.get("iss") == f"https://login.microsoftonline.com/{config['tenantId']}/v2.0"
        and config["scope"] in claims.get("scp", "").split()
        and claims.get("azp") == config["oauthClientId"]
    )
    return [auth[-1], tools[0]], observation, passed


def main():
    directory = ROOT / "evidence"
    mcp = json.loads((directory / "observability-mcp-exchanges.json").read_text())
    application = mcp["containers"]["application"].get("events", [])
    deployment = json.loads((directory / "application-probe-check.json").read_text())
    expected_principals = deployment["expectedApplicationPrincipalIds"]
    runtime_path = directory / "observability-hosted-runtime.json"
    runtime = {item["scenario"]: item for item in json.loads(runtime_path.read_text())["captures"]} if runtime_path.exists() else {}
    captures = []
    for scenario in ("a-native", "a-custom", "b-native", "b-custom", "c-native", "c-custom"):
        run = json.loads((directory / f"observability-{scenario}.json").read_text())
        exchanges = run.get("apimExchanges", [])
        selected = next((item for item in exchanges if '"tools/call"' in item.get("requestBody", "")), None)
        selected = selected or next(
            (item for item in exchanges if '"tools/list"' in item.get("requestBody", "")), None,
        )
        response_text = (selected or {}).get("responseBody", "")
        try:
            response_body = json.loads(response_text)
        except ValueError:
            response_body = {}
        actual_result = response_body.get("result", {}).get("structuredContent")
        if actual_result is None:
            content = response_body.get("result", {}).get("content", [])
            try:
                actual_result = json.loads(content[0]["text"]) if content else None
            except (ValueError, KeyError):
                actual_result = None
        errors = json.dumps(run["agentResponse"])
        matching = [event for event in application
                    if event.get("query", {}).get("experiment_id") == run["experimentId"]]
        mcp_observation = matching[0]["result"].get("tokenObservation", {}) if matching else {}
        observed_container = mcp["containers"]["application"].get("observedContainer") if matching else "NOT_OBSERVED"
        delegated_pass = False
        if scenario == "c-custom":
            container = mcp["containers"].get("delegated", {})
            matching, mcp_observation, delegated_pass = delegated_evidence(
                run, selected, actual_result, container,
            )
            observed_container = container.get("observedContainer") if matching else "NOT_OBSERVED"
        verdict = "UNVERIFIED_MISSING_CORRELATED_APIM_EXCHANGE"
        if selected:
            if "AgentInstanceClientId" in response_text:
                verdict = "BLOCKED_AGENT_INSTANCE_CONTEXT"
            elif "AADSTS500016" in response_text:
                verdict = "BLOCKED_PLATFORM_USER_TOKEN_FLOW"
            elif "oauth_consent_request" in errors or "consent" in response_text.lower():
                verdict = "BLOCKED_OAUTH_CONSENT_REQUIRED"
            elif (scenario.endswith("native") and selected.get("backendStatus") == 200
                  and response_body.get("result", {}).get("content")
                  and not response_body["result"].get("isError", False)
                  and not response_body.get("error")):
                verdict = "PASS_NATIVE_MCP_QUERY_RESULT"
            elif scenario == "c-custom" and delegated_pass:
                verdict = "PASS_VALIDATED_DELEGATED_MCP_QUERY_RESULT"
            elif (scenario in ("a-custom", "b-custom") and matching
                  and matching[0].get("result", {}).get("marker") == "CUSTOM_MCP_APPLICATION_VALIDATED"
                  and matching[0]["result"] == actual_result
                  and actual_result["claims"]["oid"] == expected_principals[0 if scenario[0] == "a" else 1]
                  and selected.get("backendStatus") == 200):
                verdict = "PASS_VALIDATED_APPLICATION_MCP_QUERY_RESULT"
            elif "error" in response_text.lower():
                verdict = "BLOCKED_MCP_ERROR"
        elif "oauth_consent_request" in errors:
            verdict = "BLOCKED_OAUTH_CONSENT_REQUIRED_NO_APIM_CAPTURE"
        elif run["agentResponse"].get("error"):
            verdict = "BLOCKED_BEFORE_MCP_TOOL_CALL"
        run["verdict"] = verdict
        write(directory / f"observability-{scenario}.json", run)
        captures.append({
            "scenario": scenario, "agent": run["agent"], "agentVersion": run["version"],
            "toolboxVersion": run["toolboxVersion"], "experimentId": run["experimentId"],
            "startedAt": run["startedAt"], "completedAt": run["completedAt"],
            "input": run["input"], "hostedHttpStatus": run["httpStatus"],
            "agentResponse": run["agentResponse"],
            "identityConfiguration": run.get("identityConfiguration", {}),
            "callerTokenObservation": run.get("callerTokenObservation", {}),
            "apimEndpoint": run["apimEndpoint"], "configuredMcpDestination": run["configuredMcpDestination"],
            "verdict": verdict, "selectedApimExchange": selected,
            "hostedAgentSnapshot": hosted_snapshot(run),
            "hostedRuntimeLogQuery": runtime.get(scenario, {"status": "NOT_QUERIED"}),
            "mcpValidatedQueryResultEvents": matching,
            "mcpTokenObservation": mcp_observation,
            "observedMcpDestination": observed_container,
            "searchInternalQueryVisibility": "NOT_OBSERVED",
            "redactions": ["authorization/tokens", "opaque consent URLs", "SDK baggage/session metadata"],
        })
    evidence = {"compiledAt": now(), "captures": captures}
    write(directory / "observability-real-exchanges.json", evidence)
    print(json.dumps({item["scenario"]: item["verdict"] for item in captures}, indent=2))


if __name__ == "__main__":
    main()
