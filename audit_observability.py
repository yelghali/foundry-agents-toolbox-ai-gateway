"""Read-only audit of original default traffic and isolated logging configuration."""

import argparse
import json
from pathlib import Path

from azure.ai.projects import AIProjectClient

import common as cm
from replay_observability import ROOT, STATE, now, safe, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    original = {}
    for cohort in config["cohorts"]:
        project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
        for name in cohort.get("agents", {}):
            agent = project.agents.get(agent_name=name)
            endpoint = agent.agent_endpoint
            original[cohort["label"] + "/" + name] = endpoint.as_dict() if endpoint else None
    original = json.loads(json.dumps(safe(original), default=str))
    baseline = ROOT / "evidence" / "observability-original-defaults-baseline.json"
    if args.baseline:
        if baseline.exists():
            raise RuntimeError("Refusing to overwrite an existing baseline")
        write(baseline, {"time": now(), "originalAgentEndpoints": original})
        print("Read-only baseline saved for", len(original), "original agents")
        return
    records = json.loads(STATE.read_text())["scenarios"]
    diagnostics = {}
    for scenario, record in records.items():
        properties = cm.arm(
            config, "GET", record["apiId"] + "/diagnostics/applicationinsights",
            version="2024-05-01",
        )["properties"]
        diagnostics[scenario] = all(
            properties[side][direction]["body"]["bytes"] == 8192
            and properties[side][direction]["headers"] == []
            for side in ("frontend", "backend") for direction in ("request", "response")
        )
    unchanged = json.loads(baseline.read_text())["originalAgentEndpoints"] == original
    evidence = {"time": now(), "originalDefaultsUnchangedAcrossReplays": unchanged,
                "isolated8192ByteBodyOnlyDiagnostics": diagnostics, "originalAgentEndpoints": original}
    write(ROOT / "evidence" / "observability-isolation-audit.json", evidence)
    print("Original default endpoints unchanged:", unchanged, "isolated diagnostics:", diagnostics)
    if not unchanged or not all(diagnostics.values()):
        raise RuntimeError("Isolation/diagnostic audit failed")


if __name__ == "__main__":
    main()
