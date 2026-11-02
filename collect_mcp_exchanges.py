"""Export only known safe validation/probe events from authorized Azure containers."""

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from replay_observability import ROOT, now, write


def azure_timestamp(value):
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--custom-config", type=Path, required=True)
    parser.add_argument("--since", help="UTC ISO timestamp; defaults to the last two hours")
    parser.add_argument("--kind", choices=("application", "delegated"),
                        help="Refresh only this container, preserving other captures")
    args = parser.parse_args()
    custom = json.loads(args.custom_config.read_text(encoding="utf-8-sig"))
    since = (azure_timestamp(args.since) if args.since
             else datetime.now(timezone.utc) - timedelta(hours=2))
    output = ROOT / "evidence" / "observability-mcp-exchanges.json"
    previous = json.loads(output.read_text()) if args.kind and output.exists() else {}
    events = previous.get("containers", {})
    for kind, name in (
        ("application", "obs-application-mcp-20261031"),
        ("delegated", custom["containerApp"]),
    ):
        if args.kind and kind != args.kind:
            continue
        result = subprocess.run(
            ["az.cmd", "containerapp", "logs", "show", "-g", custom["resourceGroup"],
             "-n", name, "--type", "console", "--tail", "300", "--format", "json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        if result.returncode:
            if kind not in events:
                events[kind] = {"container": name, "error": "Azure console log query failed"}
            continue
        selected = []
        for line in result.stdout.splitlines():
            try:
                outer = json.loads(line)
                timestamp = azure_timestamp(outer["TimeStamp"])
                if timestamp < since:
                    continue
                text = outer.get("Log", "")
                body = json.loads(text[text.index("{"):])
            except (ValueError, KeyError):
                continue
            if body.get("event") not in (
                "validated_mcp_exchange", "custom_mcp_tool",
                "application_mcp_auth_validated",
                "custom_mcp_auth_validated", "custom_mcp_auth_rejected",
            ):
                continue
            selected.append({"azureTimestamp": outer.get("TimeStamp"), **body})
        existing = events.get(kind, {}).get("events", []) if args.kind else []
        combined = {json.dumps(event, sort_keys=True): event for event in existing + selected}
        events[kind] = {"observedContainer": name, "events": list(combined.values()),
                        "collectedAt": now(), "since": since.isoformat()}
        if kind == "delegated":
            events[kind]["validationConfiguration"] = {
                "source": "selected custom MCP config; configuration is not token evidence",
                "tenantId": custom["tenantId"], "audience": custom["apiAppId"],
                "scope": custom["scope"].rsplit("/", 1)[-1],
                "oauthClientId": custom["oauthClientId"],
            }
    evidence = {"collectedAt": now(), "since": since.isoformat(), "containers": events}
    write(ROOT / "evidence" / "observability-mcp-exchanges.json", evidence)
    print("Safe MCP events:", {kind: len(value.get("events", [])) for kind, value in events.items()})


if __name__ == "__main__":
    main()
