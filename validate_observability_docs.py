"""Verify workshop bodies/timestamps against persisted real APIM evidence."""

import json
from replay_observability import ROOT, now, write


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
    checks["opaqueMetadataExcluded"] = all(
        forbidden not in workshop for forbidden in (
            "azure.ai.agentserver.session_id=", "user.id=", "login?data=", "Bearer eyJ",
        )
    )
    checks["sixFoldableRealExchanges"] = workshop.count("<summary>Real logged exchange") == 6
    write(ROOT / "evidence" / "observability-workshop-validation.json", {"time": now(), "checks": checks})
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise RuntimeError("Workshop evidence validation failed")


if __name__ == "__main__":
    main()
