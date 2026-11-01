"""Verify workshop bodies/timestamps against persisted real APIM evidence."""

import json
import re
from replay_observability import ROOT, now, write
from compile_observability_evidence import hosted_snapshot


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
        )
        checks[capture["scenario"] + "-input"] = capture["input"] in workshop
        checks[capture["scenario"] + "-hosted-full"] = json.dumps(capture["agentResponse"], indent=2) in workshop
        runtime = capture["hostedRuntimeLogQuery"]
        checks[capture["scenario"] + "-runtime"] = (
            json.dumps(runtime, indent=2) in workshop
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
