"""Render exact evidence excerpts; link repeated full captures instead of duplicating them."""

import json
import re

from replay_observability import ROOT


def block(value, language="json"):
    text = value if isinstance(value, str) else json.dumps(value, indent=2)
    fence = "`" * max(3, max((len(match) + 1 for match in re.findall(r"`+", text)), default=3))
    return f"\n{fence}{language}\n{text.strip()}\n{fence}\n"


def token_excerpt(observation):
    return {
        "boundary": observation.get("boundary", "NOT_OBSERVED"),
        "validation": observation.get("validation", "NOT_OBSERVED"),
        "header": {key: value for key, value in observation.get("header", {}).items()
                   if key in ("alg", "kid")},
        "claims": {key: value for key, value in observation.get("claims", {}).items()
                   if key in ("iss", "aud", "tid", "oid", "azp", "appid", "scp",
                              "roles", "idtyp", "ver", "iat", "nbf", "exp")},
    }


def capture_link(capture, field, label):
    index = ("a-native", "a-custom", "b-native", "b-custom", "c-native", "c-custom").index(capture["scenario"])
    return f"[{label}](evidence/observability-real-exchanges.json#/captures/{index}/{field})"


def identity_lesson(capture):
    scenario = capture["scenario"]
    configuration = capture.get("identityConfiguration", {})
    caller = token_excerpt(capture.get("callerTokenObservation", {}))
    platform = token_excerpt((capture.get("selectedApimExchange") or {}).get(
        "platformTokenObservation", {}))
    events = capture["mcpValidatedQueryResultEvents"]
    downstream = token_excerpt(capture.get("mcpTokenObservation") or
                               events[0].get("result", {}).get("tokenObservation", {})) if events else None

    def principal(observation):
        return f"`{observation['claims'].get('oid', 'NOT_OBSERVED')}`"

    def audience(observation):
        value = observation["claims"].get("aud", "NOT_OBSERVED")
        return f"`{', '.join(value) if isinstance(value, list) else value}`"

    configured = {
        "a-native": "Project MI / Search",
        "a-custom": "Project MI / custom API",
        "b-native": "Agent instance / Search",
        "b-custom": "Agent instance / custom API",
        "c-native": "Managed user / Search",
        "c-custom": "OAuth2 user / custom API",
    }[scenario]
    lessons = {
        "a-native": "Marker observed; backend JWT and Search internal queries **NOT_OBSERVED**.",
        "a-custom": "MCP validates project MI; APIM validates the **calling agent instance**, not the project MI.",
        "b-native": "APIM identity passes; Toolbox lacks `AgentInstanceClientId` context. No downstream query.",
        "b-custom": "Matching APIM `oid` does not supply required agent context. No downstream query.",
        "c-native": "`AADSTS500016` blocks discovery; caller `scp` is not a Search scope.",
        "c-custom": "**post-consent upstream C custom replay passed**: validated user `oid`, API `aud`, "
                    "`access_as_user` and OAuth client `azp` match; earlier direct/consent runs stay separate.",
    }
    if scenario == "c-custom" and capture["verdict"] != "PASS_VALIDATED_DELEGATED_MCP_QUERY_RESULT":
        lessons[scenario] = "Current upstream replay is blocked; configured OAuth is not a validated downstream token."
    lines = [
        "**Identity-hop lesson (observations versus configuration)**",
        "| Hop | Observed principal (`oid`) | Audience | Evidence |",
        "| --- | --- | --- | --- |",
        f"| User → agent | {principal(caller)} | {audience(caller)} | Decoded only |",
        f"| Agent → APIM → Toolbox | {principal(platform)} | {audience(platform)} | APIM-validated; unchanged bearer |",
        (f"| Toolbox → MCP | {principal(downstream)} | {audience(downstream)} | MCP-validated |"
         if downstream else
         f"| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** | Configured: {configured} |"),
        "- " + lessons[scenario],
        "<details>",
        f"<summary>Identity claims — {scenario}: decoded caller / validated APIM / downstream</summary>",
        "Caller — decoded only:", block(caller),
        "Agent platform token — APIM-validated:", block(platform),
    ]
    if downstream:
        lines += ["Downstream — MCP-validated:", block(downstream)]
        if capture.get("mcpTokenObservation", {}).get("limitation"):
            lines += [capture["mcpTokenObservation"]["limitation"]]
    lines += [
        "Configured identities (not token observations):",
        block(configuration),
        "</details>",
    ]
    return re.sub(r"(?<=\|)\n\n(?=\|)", "\n", "\n\n".join(lines))


def scenario_section(capture):
    scenario = capture["scenario"]
    exchange = capture["selectedApimExchange"]
    response = capture["agentResponse"]
    request = json.loads(exchange["requestBody"]) if exchange else {}
    body = json.loads(exchange["responseBody"]) if exchange else {}
    lines = [
        f"### Live replay — {scenario}: {capture['verdict']}",
        f"- Agent `{capture['agent']}` v{capture['agentVersion']}; Toolbox v{capture['toolboxVersion']}.",
        identity_lesson(capture),
        "**1. User input → actual hosted response**",
        "Submitted prompt — exact:", block(capture["input"], "text"),
        f"- Hosted HTTP **{capture['hostedHttpStatus']}**; status **{response.get('status')}**. "
        "Exact service events in the snapshot below; model text is not tool proof.",
        "**2. APIM → Toolbox: observed MCP request/response**",
    ]
    if exchange:
        method = request.get("method")
        lines += [f"- `{method}`; backend HTTP **{exchange.get('backendStatus', 'NOT_CAPTURED')}**."]
        if method == "tools/call":
            lines += [f"Actual generated tool `{request['params']['name']}` arguments:",
                      block(request["params"]["arguments"])]
        else:
            lines += ["**No `tools/call` query was produced.** `tools/list` is discovery."]
        result = body.get("result", {})
        if body.get("error"):
            message = body["error"].get("message", "")
            if scenario.startswith("b"):
                start = message.index("requires ") if "requires " in message else 0
                excerpt = message[start:].split('"')[0]
            else:
                match = re.search(r"AADSTS500016:.*?Timestamp: [^\\\"]+", message)
                excerpt = match.group(0) if match else message[:450]
            lines += ["MCP error — exact substring (full JSON below):", block(excerpt, "text")]
        elif result.get("structuredContent") is not None:
            actual = result["structuredContent"]
            if scenario == "a-custom":
                actual = {key: value for key, value in actual.items() if key != "tokenObservation"}
            lines += ["MCP result — exact fields; token metadata folded below:", block(actual)]
        elif result.get("content"):
            lines += ["MCP result text — exact:",
                      *[block(item["text"], "text") for item in result["content"][:1] if "text" in item]]
        else:
            lines += ["MCP response — exact:", block(body)]
    else:
        lines += ["No correlated APIM exchange retrieved."]
    lines += ["**3. Downstream MCP/runtime logs: what was actually observed**"]
    events = capture["mcpValidatedQueryResultEvents"]
    runtime = capture["hostedRuntimeLogQuery"]
    if scenario == "c-custom" and events:
        lines += ["- Console UUID/arguments/validated claims match APIM; APIM full return equals hosted "
                  "`function_call_output`. Console does **not** log the full return or JWT header/times."]
    elif events:
        lines += ["- UUID-correlated MCP console query/result equals APIM; downstream identity validated."]
    elif scenario == "a-native":
        lines += ["- Search internal queries/fan-out and backend token **NOT_OBSERVED**."]
    else:
        lines += ["- Discovery blocked; no correlated downstream query/result. Missing logs alone are not proof."]
    lines += [f"- Hosted console: **{runtime['status']}**; full selected lines linked below (not a complete log)."]
    preferred = [event for event in runtime.get("selectedLines", []) if
                 "Function name:" in event["line"] or "succeeded." in event["line"]]
    if preferred:
        lines += ["Hosted console — exact:", block("\n".join(event["line"] for event in preferred[:2]), "text")]
    lines += [
        "<details>", f"<summary>Real logged exchange — {scenario}: raw JSON and source links</summary>",
        "| Correlation | Recorded value |", "| --- | --- |",
        f"| Invocation UTC | `{capture['startedAt']}` → `{capture['completedAt']}` |",
        f"| Experiment | `{capture['experimentId']}` |",
        f"| Hosted response | `{response.get('id')}` |",
        f"| APIM endpoint | `{capture['apimEndpoint']}` |",
        f"| Configured MCP target | `{capture['configuredMcpDestination']}` |",
    ]
    if exchange:
        lines += [
            f"| APIM request | `{exchange['apimRequestId']}` |",
            f"| APIM UTC | `{exchange['requestTimestamp']}` → `{exchange['responseTimestamp']}` |",
            f"| Caller-context SHA-256 | `{exchange.get('callerContextHash', 'NOT_CAPTURED')}` |",
            "APIM request — exact sanitized body:", block(exchange["requestBody"]),
            "APIM response — exact sanitized body:", block(exchange["responseBody"]),
        ]
    lines += [
        "Local retained sources (ignored exports; unavailable in a fresh public clone):",
        f"- [All APIM exchanges](evidence/observability-{scenario}.json#/apimExchanges)",
        f"- [Full hosted response, including model text](evidence/observability-{scenario}.json#/agentResponse)",
        "- " + capture_link(capture, "hostedRuntimeLogQuery", "Runtime query / all selected console lines"),
        "- " + capture_link(capture, "mcpValidatedQueryResultEvents", "Downstream console events"),
        "- " + capture_link(capture, "identityConfiguration", "Control-plane identity source"),
        "</details>",
        "<details>", f"<summary>Hosted service snapshot — {scenario}</summary>",
        block(capture["hostedAgentSnapshot"]), "</details>",
    ]
    return re.sub(r"(?<=\|)\n\n(?=\|)", "\n", "\n\n".join(lines))


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
        section += "\n\n".join(scenario_section(c) for c in captures if c["scenario"] in scenarios)
        pattern = rf"## Optional APIM evidence: {re.escape(title)}\n.*?(?=\n---\n)"
        workshop, count = re.subn(pattern, lambda _: section + "\n", workshop, flags=re.S)
        if count != 1:
            raise RuntimeError("Expected one evidence section: " + title)
    workshop = re.sub(r"\n+---\n+", "\n\n---\n\n", workshop)
    workshop_path.write_text(workshop, encoding="utf-8")


if __name__ == "__main__":
    main()
