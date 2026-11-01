"""Render concise evidence stages from captured strings, with full secondary payloads."""

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


def identity_lesson(capture):
    scenario = capture["scenario"]
    configuration = capture.get("identityConfiguration", {})
    caller = token_excerpt(capture.get("callerTokenObservation", {}))
    platform = token_excerpt((capture.get("selectedApimExchange") or {}).get(
        "platformTokenObservation", {}))
    events = capture["mcpValidatedQueryResultEvents"]
    downstream = token_excerpt(events[0]["result"].get("tokenObservation", {})) if events else None

    def principal(observation):
        return f"`{observation['claims'].get('oid', 'NOT_OBSERVED')}`"

    def audience(observation):
        value = observation["claims"].get("aud", "NOT_OBSERVED")
        return f"`{', '.join(value) if isinstance(value, list) else value}`"

    configured = {
        "a-native": "Project managed identity; Search audience",
        "a-custom": "Project managed identity; custom application audience",
        "b-native": "Agent identity; Search audience",
        "b-custom": "Agent identity; custom application audience",
        "c-native": "Managed user identity; Search audience/scopes",
        "c-custom": "OAuth2 authorization code + refresh; delegated custom API scope",
    }[scenario]
    lines = [
        "**Identity-hop lesson (observations versus configuration)**",
        f"Control-plane source: `{configuration.get('source', 'NOT_OBSERVED')}`; observed UTC "
        f"`{configuration.get('observedAt', 'NOT_OBSERVED')}`. Configured agent instance principal "
        f"`{configuration.get('agentInstancePrincipalId', 'NOT_OBSERVED')}`; project managed identity "
        f"`{configuration.get('projectManagedIdentityPrincipalId', 'NOT_OBSERVED')}`. "
        "Configuration alone is not token evidence.",
        "| Hop | Observed principal (`oid`) | Audience | Evidence / interpretation |",
        "|---|---|---|---|",
        f"| User → agent | {principal(caller)} | {audience(caller)} | "
        "Caller credential decoded only; **not locally validated**. Hosted HTTP acceptance "
        "does not upgrade this capture to JWT validation evidence. |",
        f"| Agent → APIM → Toolbox | {principal(platform)} | {audience(platform)} | "
        "Entra token **validated at APIM**; same inbound bearer forwarded unchanged to Toolbox. "
        "APIM performs no token exchange. |",
        (f"| Toolbox → MCP | {principal(downstream)} | {audience(downstream)} | "
         "**Validated at MCP** (signature, issuer, audience, allowed principal); actual query/result event. |"
         if downstream else
         f"| Toolbox → MCP | **NOT_OBSERVED** token | **NOT_OBSERVED** token audience | "
         f"Configured: {configured}. No downstream JWT capture; do not substitute configured claims. |"),
        "Selected caller JWT header/claims (decoded-only):", block(caller),
        "Selected platform JWT header/claims (APIM-validated):", block(platform),
    ]
    if downstream:
        lines += ["Selected downstream JWT header/claims (MCP-validated):", block(downstream)]
    lines += [
        "Only `alg`, `kid` and the displayed allowlisted claims are included; no raw JWT, "
        "signature, key material or opaque JWT metadata. Missing `scp`, `roles` or `idtyp` "
        "means absent from this observation, not an authorization failure. "
        "RBAC/application authorization need not appear as a `roles` claim.",
        "**Conclusion:** APIM's inbound platform `oid` is this **calling agent instance**, "
        "including track A; it is neither the initiating human nor A's project managed identity.",
    ]
    if scenario == "a-custom":
        lines += [
            "This capture proves an audience/principal transition: the agent's app token for "
            "`https://ai.azure.com` reaches APIM/Toolbox, while the downstream MCP validates "
            "the project managed identity for the custom API audience. Project MI is used "
            "**downstream in A custom**, not on agent → Toolbox. This is platform-managed "
            "downstream token acquisition; no internal token-endpoint grant was traced, "
            "so do not call it a captured JWT-bearer OBO exchange.",
        ]
    elif scenario == "a-native":
        lines += ["Search MCP returned the exact access marker below, but its backend JWT and "
                  "internal Search queries are **NOT_OBSERVED**. Project MI/Search audience "
                  "are configured, not decoded or MCP-validated token claims in this capture."]
    elif scenario.startswith("b"):
        lines += ["The platform app token passes APIM validation, but Toolbox reports missing "
                  "`AgentInstanceClientId` context. An `oid` matching the configured agent does "
                  "not prove that Toolbox received all required agent-instance context. No "
                  "successful downstream agent token/query was observed on this upstream route. "
                  "Original B direct/native and its downstream Search gateway are distinct routes."]
    elif scenario == "c-native":
        lines += ["The caller's delegated `scp` is not a downstream Search scope. This replay "
                  "fails with `AADSTS500016` before a query; managed user token acquisition is "
                  "configured, but no backend user token or internal OBO grant is observed."]
    else:
        lines += ["Current upstream replay is **pending consent**, not OAuth success. The "
                  "configured delegated scope is not an observed token `scp`. The earlier "
                  "**direct C custom OAuth success** used authorization-code consent plus "
                  "refresh on a different invocation/route, without this upstream APIM hop; "
                  "it must not be relabelled as this run or as literal JWT-bearer OBO."]
    return "\n\n".join(lines)


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
        identity_lesson(capture),
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
            lines += ["Actual MCP response text (exact captured content; full reference metadata below):",
                      *[block(item["text"], "text") for item in result["content"] if "text" in item]]
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
