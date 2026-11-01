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
        if selected is None:
            raise RuntimeError("No real APIM exchange for " + capture["scenario"])
        values = (
            selected["requestBody"].strip(), selected["responseBody"].strip(),
            selected["apimRequestId"], selected["requestTimestamp"], selected["responseTimestamp"],
            selected["callerContextHash"],
        )
        checks[capture["scenario"]] = all(value in workshop for value in values)
        json.loads(selected["requestBody"])
        json.loads(selected["responseBody"])
        snapshot = capture["hostedAgentSnapshot"]
        run = json.loads((ROOT / "evidence" / f"observability-{capture['scenario']}.json").read_text())
        checks[capture["scenario"] + "-hosted"] = (
            json.dumps(snapshot, indent=2) in workshop
            and snapshot["runtimeConsoleLog"] == "NOT_CAPTURED"
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
    checks["opaqueMetadataExcluded"] = all(
        forbidden not in workshop for forbidden in (
            "azure.ai.agentserver.session_id=", "user.id=", "login?data=", "Bearer eyJ",
        )
    )
    checks["sixFoldableRealExchanges"] = workshop.count("<summary>Real logged exchange") == 6
    checks["sixHostedSnapshots"] = workshop.count("<summary>Hosted service snapshot") == 6
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
