"""Compile verdicts only from real correlated APIM and validated MCP evidence."""

import json
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
        "runtimeConsoleLog": "NOT_CAPTURED",
        "limitation": "Hosted service response snapshot; not a runtime console log. "
                      "No new invocation or telemetry retrieval performed.",
    })


def main():
    directory = ROOT / "evidence"
    mcp = json.loads((directory / "observability-mcp-exchanges.json").read_text())
    application = mcp["containers"]["application"].get("events", [])
    deployment = json.loads((directory / "application-probe-check.json").read_text())
    expected_principals = deployment["expectedApplicationPrincipalIds"]
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
            elif (scenario.endswith("custom") and matching
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
            "apimEndpoint": run["apimEndpoint"], "configuredMcpDestination": run["configuredMcpDestination"],
            "verdict": verdict, "selectedApimExchange": selected,
            "hostedAgentSnapshot": hosted_snapshot(run),
            "mcpValidatedQueryResultEvents": matching,
            "observedMcpDestination": (
                mcp["containers"]["application"]["observedContainer"] if matching else "NOT_OBSERVED"
            ),
            "searchInternalQueryVisibility": "NOT_OBSERVED",
            "redactions": ["authorization/tokens", "opaque consent URLs", "SDK baggage/session metadata"],
        })
    evidence = {"compiledAt": now(), "captures": captures}
    write(directory / "observability-real-exchanges.json", evidence)
    print(json.dumps({item["scenario"]: item["verdict"] for item in captures}, indent=2))


if __name__ == "__main__":
    main()
