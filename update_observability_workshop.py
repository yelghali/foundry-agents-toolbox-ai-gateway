"""Render concise evidence stages from captured strings, with full secondary payloads."""

import json
import re

from replay_observability import ROOT


def block(value, language="json"):
    text = value if isinstance(value, str) else json.dumps(value, indent=2)
    return f"\n```{language}\n{text.strip()}\n```\n"


def scenario_section(capture):
    scenario = capture["scenario"]
    exchange = capture["selectedApimExchange"]
    response = capture["agentResponse"]
    request = json.loads(exchange["requestBody"]) if exchange else {}
    body = json.loads(exchange["responseBody"]) if exchange else {}
    lines = [
        f"### Live replay — {scenario}: {capture['verdict']}",
        f"Agent `{capture['agent']}` v{capture['agentVersion']}; Toolbox v{capture['toolboxVersion']}. "
        f"UTC `{capture['startedAt']}` → `{capture['completedAt']}`. "
        f"Experiment `{capture['experimentId']}`.",
        "**1. User input → actual hosted response**",
        "Exact submitted user prompt (not the generated MCP arguments):",
        block(capture["input"], "text"),
        f"Hosted HTTP **{capture['hostedHttpStatus']}**; response `{response.get('id')}`; "
        f"status **{response.get('status')}**.",
    ]
    messages = [
        content["text"] for event in response.get("output", []) if event.get("type") == "message"
        for content in event.get("content", []) if "text" in content
    ]
    if messages:
        lines += ["Actual hosted answer (model text; verify against the tool evidence below):",
                  block("\n".join(messages), "text")]
    elif response.get("error"):
        lines += ["Actual hosted error excerpt (full error in secondary capture):",
                  block(response["error"].get("message", "")[:450], "text")]
    else:
        lines += ["No hosted answer/tool output; returned event types:",
                  block([item.get("type") for item in response.get("output", [])])]
    lines += ["**2. APIM → Toolbox: observed MCP request/response**"]
    if exchange:
        method = request.get("method")
        lines += [
            f"`{method}`; request `{exchange['apimRequestId']}`; backend HTTP "
            f"**{exchange.get('backendStatus', 'NOT_CAPTURED')}**.",
            f"UTC request `{exchange['requestTimestamp']}`; response `{exchange['responseTimestamp']}`.",
        ]
        if method == "tools/call":
            lines += [f"Actual generated tool `{request['params']['name']}` arguments:",
                      block(request["params"]["arguments"])]
        else:
            lines += [
                "**No `tools/call` query was produced.** The observed `tools/list` request "
                "is discovery, not a user search or tool query.",
                "Exact discovery parameters:", block(request.get("params", {})),
            ]
        result = body.get("result", {})
        if body.get("error"):
            lines += ["Actual MCP error excerpt (unmodified substring; full below):",
                      block(body["error"].get("message", "")[:450], "text")]
        elif result.get("structuredContent") is not None:
            lines += ["Actual MCP result:", block(result["structuredContent"])]
        elif result.get("content"):
            lines += ["Actual MCP response content:", block(result["content"])]
        else:
            lines += ["Actual MCP response:", block(body)]
    else:
        lines += ["No correlated APIM exchange retrieved; no generated query can be asserted."]
    lines += ["**3. Downstream MCP/runtime logs: what was actually observed**"]
    events = capture["mcpValidatedQueryResultEvents"]
    if events:
        lines += ["Custom MCP console `tools/call` query/result is correlated by the experiment UUID; "
                  "its returned result equals the APIM result.",
                  *[block(event) for event in events]]
    elif scenario.endswith("native") and request.get("method") == "tools/call":
        lines += ["Native Search MCP response is observed through APIM. Search's internal query/fan-out "
                  "and service-owned console logs are **NOT_OBSERVED**; no internal query is reconstructed."]
    elif request.get("method") == "tools/call":
        lines += ["APIM captured the tool query, but no correlated downstream console query/result "
                  "was retrieved. Missing console evidence is not a successful API validation."]
    else:
        lines += ["No correlated downstream `tools/call` query/result console event was retrieved. "
                  "The observed error/consent blocks this captured route before a tool query; "
                  "missing logs alone do not prove no execution."]
    runtime = capture["hostedRuntimeLogQuery"]
    lines += [f"Pinned hosted console query: **{runtime['status']}** "
              f"(queried `{runtime.get('queriedAt', 'NOT_QUERIED')}`). "
              "Hosted service responses are not runtime console logs."]
    if runtime.get("selectedLines"):
        lines += ["Actual runtime console excerpts (full selected log lines in secondary capture):"]
        preferred = [event for event in runtime["selectedLines"] if any(
            word in event["line"] for word in (
                "Function name:", "succeeded.", "Hosted Responses failure",
                "Consent URL for tool", "Failed to prepare agent", "mcp.shared.exceptions.McpError",
            )
        )]
        for event in (preferred or runtime["selectedLines"])[:2]:
            lines += [f"UTC `{event.get('timestamp', 'NOT_CAPTURED')}`.",
                      block(event["line"][:450], "text")]
    lines += [
        "<details>", f"<summary>Real logged exchange — {scenario}: full secondary capture</summary>",
        f"POST URL: `{capture['apimEndpoint']}`. Configured downstream target: "
        f"`{capture['configuredMcpDestination']}` (configuration is not execution evidence).",
    ]
    if exchange:
        lines += [f"Caller-context SHA-256: `{exchange.get('callerContextHash', 'NOT_CAPTURED')}`.",
                  "Exact captured request (only sensitive baggage redacted):",
                  block(exchange["requestBody"]), "Exact captured response:", block(exchange["responseBody"])]
    lines += ["All APIM exchanges for this invocation:",
              block(json.loads((ROOT / "evidence" / f"observability-{scenario}.json").read_text()).get("apimExchanges", [])),
              "Actual hosted response (sensitive consent/session identifiers redacted):",
              block(response), "Runtime query result:", block(runtime),
              f"Local full sources: `evidence\\observability-{scenario}.json`, "
              f"`evidence\\observability-{scenario}-apim.json`.", "</details>",
              "<details>", f"<summary>Hosted service snapshot — {scenario}</summary>",
              block(capture["hostedAgentSnapshot"]), "</details>"]
    return "\n\n".join(lines)


def main():
    captures = json.loads((ROOT / "evidence" / "observability-real-exchanges.json").read_text())["captures"]
    workshop_path = ROOT / "workshop.md"
    workshop = workshop_path.read_text(encoding="utf-8")
    groups = (
        ("A native and custom MCP", ("a-native", "a-custom")),
        ("B native and custom MCP", ("b-native", "b-custom")),
        ("C native MCP", ("c-native",)),
        ("C custom MCP", ("c-custom",)),
    )
    for title, scenarios in groups:
        section = f"## Optional APIM evidence: {title}\n\n"
        section += ("Fresh Azure hosted-agent executions on **November 1, 2026**, on the existing "
                    "pinned `obs-20261031-*` routes. Original defaults are unchanged; "
                    "no direct-route success is mixed into these results. Only public synthetic data "
                    "was submitted. Body diagnostics are isolated (8192 bytes; no headers). "
                    "Authorization/tokens, opaque consent identifiers/URLs and SDK session baggage "
                    "are excluded from exports; nonsensitive queries/results are preserved.\n\n")
        section += "\n\n".join(scenario_section(c) for c in captures if c["scenario"] in scenarios)
        pattern = rf"## Optional APIM evidence: {re.escape(title)}\n.*?(?=\n---\n)"
        workshop, count = re.subn(pattern, lambda _: section + "\n", workshop, flags=re.S)
        if count != 1:
            raise RuntimeError("Expected one evidence section: " + title)
    workshop = workshop.replace("Six-path evidence matrix (historical optional upstream APIM run)",
                                "Six-path evidence matrix (fresh November 1 upstream APIM replay)")
    workshop = workshop.replace("| Path | Agent → Toolbox identity |",
                                "| Path | Toolbox → MCP configured identity |")
    start = workshop.index(
        "Snapshots in the corresponding scenario" if "Snapshots in the corresponding scenario" in workshop
        else "The three numbered stages in each scenario"
    )
    end = workshop.index("\n\n| Item | Local evidence |", start)
    workshop = workshop[:start] + (
        "The three numbered stages in each scenario distinguish the exact user prompt, actual "
        "hosted response, generated MCP arguments (or blocked discovery), APIM result and downstream "
        "console evidence. Full sanitized bodies are secondary foldables. Fresh pinned hosted console "
        "queries are saved in `evidence\\observability-hosted-runtime.json`; their explicit statuses "
        "distinguish unavailable or uncorrelated logs from service response snapshots. Native Search "
        "internal queries remain not observed. All six new invocation records and telemetry are "
        "retained locally in ignored `evidence\\observability-real-exchanges.json` and per-scenario "
        "files; historical UUID-named records remain separate."
    ) + workshop[end:]
    workshop = workshop.replace("re-check and update historical workshop excerpts", "recompile and refresh workshop excerpts")
    workshop = workshop.replace("rather\n  than treating", "rather\n  than treating")
    if "python .\\update_observability_workshop.py" not in workshop:
        workshop = workshop.replace("python .\\compile_observability_evidence.py",
                                    "python .\\collect_hosted_runtime_logs.py --config $configPath\n"
                                    "python .\\compile_observability_evidence.py\n"
                                    "python .\\update_observability_workshop.py")
    workshop_path.write_text(workshop, encoding="utf-8")


if __name__ == "__main__":
    main()
