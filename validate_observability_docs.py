"""Verify workshop bodies/timestamps against persisted real APIM evidence."""

import json
import re
from replay_observability import ROOT, now, write
from compile_observability_evidence import hosted_snapshot
from update_observability_workshop import scenario_section, token_excerpt


def linked_evidence(workshop, expected, field, scenario):
    """Require a real link resolving to the exact retained JSON value, not just a filename."""
    from urllib.parse import unquote
    for target in re.findall(r"\]\((evidence/[^)]+)\)", workshop):
        filename, separator, pointer = target.partition("#")
        if not separator or not pointer.startswith("/") or not pointer.endswith("/" + field):
            continue
        path = (ROOT / unquote(filename)).resolve()
        if not path.is_relative_to((ROOT / "evidence").resolve()) or not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            owner = value
            for part in pointer[1:].split("/"):
                owner = value
                key = unquote(part).replace("~1", "/").replace("~0", "~")
                value = value[int(key)] if isinstance(value, list) else value[key]
            if owner.get("scenario") == scenario and value == expected:
                return True
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            continue
    return False


def main():
    captures = json.loads((ROOT / "evidence" / "observability-real-exchanges.json").read_text())["captures"]
    workshop = (ROOT / "workshop.md").read_text(encoding="utf-8")
    checks = {}
    for capture in captures:
        selected = capture["selectedApimExchange"]
        values = (
            selected["requestBody"].strip(), selected["responseBody"].strip(),
            selected["apimRequestId"], selected["requestTimestamp"], selected["responseTimestamp"],
            selected.get("callerContextHash", "NOT_CAPTURED"),
        ) if selected else ("No correlated APIM exchange retrieved",)
        checks[capture["scenario"]] = all(value in workshop for value in values)
        request = json.loads(selected["requestBody"]) if selected else {}
        if selected:
            json.loads(selected["responseBody"])
        snapshot = capture["hostedAgentSnapshot"]
        run = json.loads((ROOT / "evidence" / f"observability-{capture['scenario']}.json").read_text())
        checks[capture["scenario"] + "-hosted"] = (
            json.dumps(snapshot, indent=2) in workshop
            and snapshot["runtimeConsoleLog"] == "NOT_A_RUNTIME_LOG"
            and snapshot == hosted_snapshot(run)
        )
        checks[capture["scenario"] + "-boundaries"] = all(
            field in capture for field in (
                "configuredMcpDestination", "observedMcpDestination",
                "mcpValidatedQueryResultEvents", "searchInternalQueryVisibility",
            )
        )
        checks[capture["scenario"] + "-mcp"] = all(
            json.dumps(event, indent=2) in workshop
            for event in capture["mcpValidatedQueryResultEvents"]
        ) or linked_evidence(workshop, capture["mcpValidatedQueryResultEvents"],
                             "mcpValidatedQueryResultEvents", capture["scenario"])
        checks[capture["scenario"] + "-input"] = capture["input"] in workshop
        checks[capture["scenario"] + "-exact-current-section"] = scenario_section(capture) in workshop
        caller = capture["callerTokenObservation"]
        platform = (selected or {}).get("platformTokenObservation", {})
        checks[capture["scenario"] + "-identity-observations"] = (
            json.dumps(token_excerpt(caller), indent=2) in workshop
            and json.dumps(token_excerpt(platform), indent=2) in workshop
            and caller.get("validation") == "DECODED_ONLY_NOT_VALIDATED"
            and platform.get("validation") == "VALIDATED_AT_APIM_ENTRA_BOUNDARY"
            and platform.get("forwarding") == "UNCHANGED_BEARER_NO_APIM_EXCHANGE"
            and platform.get("claims", {}).get("oid")
            == capture["identityConfiguration"]["agentInstancePrincipalId"]
        )
        checks[capture["scenario"] + "-hosted-full"] = (
            json.dumps(capture["agentResponse"], indent=2) in workshop
            or linked_evidence(workshop, capture["agentResponse"], "agentResponse", capture["scenario"])
        )
        runtime = capture["hostedRuntimeLogQuery"]
        checks[capture["scenario"] + "-runtime"] = (
            (json.dumps(runtime, indent=2) in workshop
             or linked_evidence(workshop, runtime, "hostedRuntimeLogQuery", capture["scenario"]))
            and runtime.get("experimentId") == run["experimentId"]
            and runtime.get("responseId") == run["agentResponse"].get("id")
        )
        checks[capture["scenario"] + "-query"] = (
            json.dumps(request["params"]["arguments"], indent=2) in workshop
            if request.get("method") == "tools/call" else
            "**No `tools/call` query was produced.**" in workshop
            if selected else "No correlated APIM exchange retrieved" in workshop
        )
    checks["opaqueMetadataExcluded"] = all(
        forbidden not in workshop for forbidden in (
            "azure.ai.agentserver.session_id=", "user.id=", "login?data=", "Bearer eyJ",
        )
    )
    checks["sixFoldableRealExchanges"] = workshop.count("<summary>Real logged exchange") == 6
    checks["sixHostedSnapshots"] = workshop.count("<summary>Hosted service snapshot") == 6
    checks["sixIdentityHopLessons"] = workshop.count("**Identity-hop lesson (observations versus configuration)**") == 6
    checks["sixIdentityHopTables"] = all(workshop.count(hop) == 6 for hop in (
        "| User → agent |", "| Agent → APIM → Toolbox |", "| Toolbox → MCP |",
    ))
    checks["downstreamApplicationValidated"] = all(
        (json.dumps(token_excerpt(event["result"]["tokenObservation"]), indent=2) in workshop
         or linked_evidence(workshop, capture["mcpValidatedQueryResultEvents"],
                            "mcpValidatedQueryResultEvents", capture["scenario"]))
        and event["result"]["tokenObservation"]["validation"] == "VALIDATED_AT_MCP_BOUNDARY"
        for capture in captures if capture["scenario"] in ("a-custom", "b-custom")
        for event in capture["mcpValidatedQueryResultEvents"]
    )
    from compile_observability_evidence import delegated_evidence
    c_custom = next(c for c in captures if c["scenario"] == "c-custom")
    if c_custom["verdict"] == "PASS_VALIDATED_DELEGATED_MCP_QUERY_RESULT":
        run = json.loads((ROOT / "evidence" / "observability-c-custom.json").read_text())
        mcp = json.loads((ROOT / "evidence" / "observability-mcp-exchanges.json").read_text())
        selected = c_custom["selectedApimExchange"]
        result = json.loads(selected["responseBody"])["result"]["structuredContent"]
        events, observation, passed = delegated_evidence(run, selected, result, mcp["containers"]["delegated"])
        checks["downstreamDelegatedValidated"] = (
            passed and events == c_custom["mcpValidatedQueryResultEvents"]
            and observation == c_custom["mcpTokenObservation"]
            and json.dumps(token_excerpt(observation), indent=2) in workshop
            and "post-consent upstream C custom replay passed" in workshop
        )
    checks["threeStagesPerScenario"] = all(
        workshop.count(stage) == 6 for stage in (
            "**1. User input → actual hosted response**",
            "**2. APIM → Toolbox: observed MCP request/response**",
            "**3. Downstream MCP/runtime logs: what was actually observed**",
        )
    )
    pages = re.split(r"\n---\n", workshop)[1:]
    checks["tenCoherentPages"] = len(pages) == 10
    checks["cleanupLast"] = pages[-1].lstrip().startswith("# Cleanup and next steps")
    for index, scenarios in (
        (4, ("a-native", "a-custom")),
        (5, ("b-native", "b-custom")),
        (6, ("c-native",)),
        (7, ("c-custom",)),
    ):
        checks[f"scenarioPage{index + 1}OwnsEvidence"] = all(
            f"<summary>Hosted service snapshot — {scenario}</summary>" in pages[index]
            for scenario in scenarios
        ) and "<summary>Real logged exchange" in pages[index]
    checks["sixScenarioCoverage"] = {c["scenario"] for c in captures} == {
        "a-native", "a-custom", "b-native", "b-custom", "c-native", "c-custom",
    } and len(captures) == 6
    write(ROOT / "evidence" / "observability-workshop-validation.json", {"time": now(), "checks": checks})
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise RuntimeError("Workshop evidence validation failed")


if __name__ == "__main__":
    main()
