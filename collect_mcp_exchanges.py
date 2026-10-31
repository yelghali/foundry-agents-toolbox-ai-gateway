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
    args = parser.parse_args()
    custom = json.loads(args.custom_config.read_text(encoding="utf-8-sig"))
    since = (azure_timestamp(args.since) if args.since
             else datetime.now(timezone.utc) - timedelta(hours=2))
    events = {}
    for kind, name in (
        ("application", "obs-application-mcp-20261031"),
        ("delegated", custom["containerApp"]),
    ):
        result = subprocess.run(
            ["az.cmd", "containerapp", "logs", "show", "-g", custom["resourceGroup"],
             "-n", name, "--type", "console", "--tail", "300", "--format", "json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        if result.returncode:
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
                "custom_mcp_auth_validated", "custom_mcp_auth_rejected",
            ):
                continue
            selected.append({"azureTimestamp": outer.get("TimeStamp"), **body})
        events[kind] = {"observedContainer": name, "events": selected}
    evidence = {"collectedAt": now(), "since": since.isoformat(), "containers": events}
    write(ROOT / "evidence" / "observability-mcp-exchanges.json", evidence)
    print("Safe MCP events:", {kind: len(value.get("events", [])) for kind, value in events.items()})


if __name__ == "__main__":
    main()
