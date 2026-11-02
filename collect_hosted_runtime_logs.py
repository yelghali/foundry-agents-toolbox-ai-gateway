"""Read pinned hosted console logs; export only correlated or known-error lines."""

import argparse
import json
import re
import subprocess
import time
from datetime import datetime
from itertools import islice
from pathlib import Path
from urllib.parse import urlsplit
from azure.ai.projects import AIProjectClient

from replay_observability import ROOT, STATE, now, safe, write
import common as cm


def session_logs(config, cohort, record, run):
    """Select only the uniquely time/version-matched session; never export its ID."""
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
    start = datetime.fromisoformat(run["startedAt"]).timestamp()
    end = datetime.fromisoformat(run["completedAt"]).timestamp()
    response = None
    try:
        sessions = list(islice(project.agents.list_sessions(
            record["agent"], limit=3, order="desc"), 3))
        matching = [item for item in sessions
                    if start - 120 <= (item.created_at.timestamp() if isinstance(item.created_at, datetime)
                                      else float(item.created_at)) <= start + 2
                    and item.version_indicator.agent_version == record["version"]]
        if len(matching) != 1:
            return {"status": "NO_UNIQUE_REPLAY_SESSION", "selectedLines": []}
        response, stream = project.agents.get_session_log_stream(
            record["agent"], record["version"], matching[0].agent_session_id,
            cls=lambda pipeline, data, headers: (pipeline.http_response, data),
            connection_timeout=10, read_timeout=5, retry_total=0,
        )
        selected, buffer, deadline = [], b"", time.monotonic() + 10
        try:
            for chunk in stream:
                if time.monotonic() > deadline:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.startswith(b"data:"):
                        continue
                    try:
                        event = json.loads(line[5:].decode("utf-8"))
                        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
                        message = event["message"]
                    except (ValueError, KeyError, TypeError):
                        continue
                    if not start - 5 <= timestamp <= end + 5:
                        continue
                    if any(word in message.lower() for word in (
                        "session_id", "sessionid", "user.id=", "authorization", "access_token",
                        "refresh_token", "baggage", "secret", "oacr_", "caller_context",
                    )):
                        continue
                    if matching[0].agent_session_id in message:
                        continue
                    selected.append({"correlatedBySessionAndTime": True,
                                     "timestamp": event["timestamp"], "stream": event.get("stream"),
                                     "line": safe(message)})
        except Exception:
            # A bounded read timeout closes this intentionally unending SSE stream.
            if not selected:
                return {"status": "NO_CORRELATED_RUNTIME_LINES", "selectedLines": []}
        return {"status": "CAPTURED_CORRELATED_LINES" if selected else "NO_CORRELATED_RUNTIME_LINES",
                "selectedLines": selected}
    except Exception as error:
        return {"status": "SESSION_RUNTIME_LOG_QUERY_FAILED", "selectedLines": [],
                "errorType": type(error).__name__,
                "errorHttpStatus": getattr(error, "status_code", None)}
    finally:
        if response is not None:
            response.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--session-only", action="store_true",
                        help="Use the scoped SDK session log stream after an unavailable CLI endpoint")
    parser.add_argument("--scenario", choices=("a-native", "a-custom", "b-native", "b-custom",
                                              "c-native", "c-custom"),
                        help="Refresh only this scenario, preserving the other selected captures")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    output = ROOT / "evidence" / "observability-hosted-runtime.json"
    captures = (json.loads(output.read_text())["captures"]
                if args.scenario and output.exists() else [])
    for scenario, record in json.loads(STATE.read_text())["scenarios"].items():
        if args.scenario and scenario != args.scenario:
            continue
        cohort = next(item for item in config["cohorts"] if item["label"] == scenario[0])
        endpoint = urlsplit(cohort["project"]["endpoint"])
        run = json.loads((ROOT / "evidence" / f"observability-{scenario}.json").read_text())
        command = [
            "az.cmd", "cognitiveservices", "agent", "logs", "show",
            "--account-name", endpoint.hostname.split(".")[0],
            "--project-name", endpoint.path.rstrip("/").split("/")[-1],
            "--name", record["agent"], "--agent-version", record["version"],
            "--type", "console", "--tail", "300", "--only-show-errors",
            "--subscription", config["subscriptionId"],
        ]
        try:
            result = (subprocess.CompletedProcess(command, 1, "", "") if args.session_only else
                      subprocess.run(command, capture_output=True, text=True,
                                     encoding="utf-8", errors="replace", timeout=120))
            lines = result.stdout.splitlines()
            ids = [run["experimentId"], run["agentResponse"].get("id")]
            selected = []
            for line in lines:
                correlated = any(value and value in line for value in ids)
                known_error = any(value in line for value in ("AADSTS500016", "AgentInstanceClientId"))
                if not correlated and not known_error:
                    continue
                if any(value in line.lower() for value in (
                    "session_id", "user.id=", "authorization", "access_token", "refresh_token",
                    "baggage", "secret", "oacr_",
                )):
                    continue
                selected.append({"correlatedById": correlated, "line": safe(line)})
            capture = {
                "scenario": scenario, "agent": record["agent"], "version": record["version"],
                "experimentId": run["experimentId"], "responseId": run["agentResponse"].get("id"),
                "invocationStartedAt": run["startedAt"], "invocationCompletedAt": run["completedAt"],
                "queriedAt": now(), "exitCode": result.returncode,
                "errorHttpStatus": next(iter(re.findall(r"HTTP (\d{3})", result.stderr)), None),
                "returnedLineCount": len(lines), "selectedLines": selected,
                "status": ("CAPTURED_CORRELATED_LINES" if any(x["correlatedById"] for x in selected)
                           else "NO_CORRELATED_RUNTIME_LINES" if result.returncode == 0
                           else "RUNTIME_LOG_QUERY_FAILED"),
                "limitation": "Last 300 console lines from this pinned version, not a complete "
                              "invocation log. Uncorrelated errors are not attributed to this replay. "
                              "Sensitive/session-bearing and unrelated lines are not exported.",
            }
            if result.returncode:
                capture["cliStatus"] = "NOT_RETRIED" if args.session_only else "RUNTIME_LOG_QUERY_FAILED"
                capture.update(session_logs(config, cohort, record, run))
                capture["source"] = "SDK get_session_log_stream; unique version/time-matched session"
                capture["limitation"] = ("Bounded console SSE read, filtered to this pinned session's "
                                        "invocation time window. Sensitive and unrelated lines excluded; "
                                        "session IDs remain memory-only. Not a complete invocation log.")
        except subprocess.TimeoutExpired:
            capture = {"scenario": scenario, "queriedAt": now(), "status": "RUNTIME_LOG_QUERY_TIMEOUT"}
        captures = [item for item in captures if item["scenario"] != scenario]
        captures.append(capture)
        print(scenario, capture["status"], flush=True)
    write(ROOT / "evidence" / "observability-hosted-runtime.json",
          {"collectedAt": now(), "captures": captures})


if __name__ == "__main__":
    main()
