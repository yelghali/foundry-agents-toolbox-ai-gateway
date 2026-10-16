"""Run real ABC agent/tool calls and record user-aware audit without exporting answers."""

import argparse
import json
import re
import time
import uuid
from datetime import datetime, timezone

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import VersionRefIndicator, VersionSelector, FixedRatioVersionSelectionRule
from openai import APIStatusError

import common as cm


def consent_challenge(error) -> dict | None:
    text = json.dumps(error)
    if "CONSENT_REQUIRED" not in text:
        return None
    match = re.search(
        r"https://[A-Za-z0-9.-]+\.consent\.azure-(?:apim|apihub)\.net/login\?data=[A-Za-z0-9_%+/=-]+",
        text,
    )
    if match:
        return {"type": "oauth_consent_request", "consent_link": match.group()}
    raise RuntimeError("The broker requires consent but did not return a recognized Microsoft consent URL.")


def backend_error(result: dict):
    if result.get("error"):
        return result["error"]
    for item in result.get("output", []):
        if item.get("type") in ("mcp_call", "function_call", "azure_ai_search_call", "openapi_call"):
            if item.get("error"):
                return item["error"]
        output = item.get("output")
        if item.get("type") != "function_call_output" or not isinstance(output, str):
            continue
        if output.startswith("Error:"):
            return {"tool_error": output}
        try:
            structured = json.loads(output)
        except json.JSONDecodeError:
            continue
        if isinstance(structured, dict) and isinstance(structured.get("error"), dict):
            error = structured["error"]
            if error.get("code") == "authorization_denied" and error.get("http_status") in (401, 403):
                return error
            if error.get("code") == "HostedAgentNotSupported" and error.get("backend_error"):
                return error
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", choices=("a", "b", "c"), required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--route", default="direct")
    parser.add_argument("--tool", choices=("raw", "iq", "peer"), default="iq")
    parser.add_argument("--question")
    parser.add_argument("--expect-denied", action="store_true")
    parser.add_argument("--expect-unsupported", action="store_true")
    parser.add_argument("--confidential", action="store_true")
    parser.add_argument("--request-store", action="store_true",
                        help="Initialize ordinary OAuth continuation or challenge confidential no-store enforcement.")
    args = parser.parse_args()
    config = cm.load_config()
    cohort = next(c for c in config["cohorts"] if c["label"] == args.cohort)
    agent = cohort["agents"][args.agent]
    if args.route == "user-ingress":
        if args.cohort != "c" or not cohort.get("userIngress"):
            parser.error("The user-ingress route requires the separate C ingress API.")
        version = agent["versions"][cohort["userIngress"]["downstreamRoute"]]
    else:
        version = agent["versions"][args.route]
    target = next(c for c in config["cohorts"] if c["label"] == agent["targetCohort"])
    token = cm.credential(config).get_token("https://ai.azure.com/.default").token
    user = cm.claims(token)["oid"]
    correlation = str(uuid.uuid4())
    question = args.question or (
        f"Use only the raw index search tool to find the exact normal access marker for cohort {target['label'].upper()}."
        if args.tool == "raw" else
        f"Use only the IQ knowledge-base retrieval tool to find the exact normal access marker for cohort {target['label'].upper()}."
    )
    metadata = {
        "project": cohort["project"]["name"], "agent": args.agent, "agent_version": version,
        "route": args.route, "tool": args.tool, "user_oid": user, "correlation_id": correlation,
        "identity_mode": cohort["identityMode"], "target_cohort": target["label"],
    }
    cm.audit(cohort["telemetrySettings"], "abc_client_invocation", {**metadata, "phase": "started"})
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    conversation_items_after = None
    if agent["kind"] == "prompt":
        project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
        endpoint = project.agents.get(agent_name=args.agent).agent_endpoint
        previous_selector = endpoint.version_selector
        endpoint.version_selector = VersionSelector(version_selection_rules=[
            FixedRatioVersionSelectionRule(agent_version=version, traffic_percentage=100),
        ])
        project.agents.update_details(agent_name=args.agent, agent_endpoint=endpoint)
        try:
            if args.route == "user-ingress":
                response = requests.post(
                    cohort["userIngress"]["endpoint"] + "/prompt",
                    headers={"Authorization": "Bearer " + token, "x-client-request-id": correlation},
                    json={"input": question, "store": args.request_store,
                          "agent_reference": {"name": args.agent, "version": version, "type": "agent_reference"}},
                    timeout=600,
                )
                response.raise_for_status()
                result, http_status = response.json(), response.status_code
            else:
                response = project.get_openai_client().responses.create(
                    input=question, store=args.request_store,
                    extra_headers={"x-client-request-id": correlation},
                    extra_body={"agent_reference": {"name": args.agent, "version": version, "type": "agent_reference"}},
                )
                result = response.model_dump(mode="json", warnings=False)
                http_status = 200
        except APIStatusError as error:
            consent = consent_challenge(error.body)
            if consent:
                result = {"status": "incomplete", "output": [consent]}
                http_status = error.status_code
            else:
                result = {"status": "failed", "error": error.body}
                http_status = error.status_code
        finally:
            endpoint.version_selector = previous_selector
            project.agents.update_details(agent_name=args.agent, agent_endpoint=endpoint)
    else:
        project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
        session = project.agents.create_session(
            agent_name=args.agent, version_indicator=VersionRefIndicator(agent_version=version),
        )
        url = (cohort["userIngress"]["endpoint"] + "/hosted?api-version=v1" if args.route == "user-ingress" else
               f"{cohort['project']['endpoint']}/agents/{args.agent}/endpoint/protocols/openai/responses?api-version=v1")
        conversations = project.get_openai_client().conversations if args.confidential else None
        conversation = conversations.create() if conversations else None
        payload = {
            "input": question, "stream": False, "store": args.request_store,
            "agent_session_id": session.agent_session_id,
        }
        if conversation:
            payload["conversation"] = conversation.id
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {token}", "x-client-request-id": correlation},
                json=payload,
                timeout=600,
            )
            response.raise_for_status()
            result = response.json()
            http_status = response.status_code
        finally:
            if conversation:
                conversation_items_after = len(list(conversations.items.list(conversation_id=conversation.id)))
                conversations.delete(conversation.id)
        pinned = project.agents.get_session(agent_name=args.agent, session_id=session.agent_session_id)
        if (
            pinned.version_indicator.agent_version != version
            or result.get("agent_session_id") != session.agent_session_id
        ):
            raise RuntimeError("The hosted endpoint did not bind to the verified route session.")
    text = json.dumps(result)
    consent = next((item for item in result.get("output", [])
                    if item.get("type") == "oauth_consent_request"), None)
    if not consent and result.get("error"):
        consent = consent_challenge(result["error"])
    if consent:
        (cm.ROOT / ".oauth-consent.json").write_text(json.dumps(consent, indent=2) + "\n", encoding="utf-8")
        cm.audit(cohort["telemetrySettings"], "abc_client_invocation", {
            **metadata, "phase": "consent_required", "answer_exported": False,
        })
        (cm.ROOT / "evidence" / "c-oauth-consent-status.json").write_text(json.dumps({
            "status": "CONSENT_REQUIRED", "agent": args.agent, "route": args.route,
            "tool": args.tool, "user_oid": user, "verified_at": datetime.now(timezone.utc).isoformat(),
            "challenge_saved_in_ignored_file": True, "consent_url_not_in_evidence": True,
        }, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError("Per-user OAuth consent is required; the link is in the ignored .oauth-consent.json.")
    calls = [item for item in result.get("output", []) if item.get("type") in (
        "mcp_call", "function_call", "azure_ai_search_call", "openapi_call",
    )]
    marker = target["confidentialAnswerCanary"] if args.confidential else target["marker"]
    actual_error = backend_error(result)
    denied = bool(actual_error) and any(word in json.dumps(actual_error).lower() for word in (
        "403", "forbidden", "unauthorized",
    ))
    unsupported = isinstance(actual_error, dict) and actual_error.get("code") == "HostedAgentNotSupported"
    passed = unsupported if args.expect_unsupported else denied if args.expect_denied else (
        result.get("status") == "completed" and bool(calls)
        and marker in text and not result.get("error")
        and (not args.confidential or conversation_items_after == 0)
    )
    cm.audit(cohort["telemetrySettings"], "abc_client_invocation", {
        **metadata, "phase": "completed", "status": result.get("status"),
        "http_status": http_status, "passed": passed, "elapsed_ms": round((time.monotonic() - start) * 1000),
        "response_id": result.get("id"), "answer_exported": False,
    })
    record = {
        **metadata, "started_at": started_at, "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "FAIL", "http_status": http_status,
        "response_id": result.get("id"), "resolved_agent_reference": result.get("agent_reference"),
        "actual_backend_denial": denied, "marker_found": marker in text,
        "actual_backend_unsupported": unsupported,
        "question": question if args.confidential else None,
        "response": None if args.confidential else result,
        "confidential": args.confidential, "requested_store": args.request_store,
        "response_store_flag": result.get("store"),
        "conversation_items_after": conversation_items_after,
    }
    directory = cm.ROOT / "evidence"
    directory.mkdir(exist_ok=True)
    suffix = "-store-request" if args.request_store else "-unsupported" if args.expect_unsupported else ""
    filename = f"{args.agent}-{args.route}-{args.tool}" + suffix + ".json"
    (directory / filename).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"{record['status']}: {args.agent} v{version} {args.route}/{args.tool}; marker={marker in text}; denial={denied}")
    if not passed:
        raise RuntimeError(f"Agent route did not satisfy the assertion: {json.dumps(actual_error)[:2000]}")


if __name__ == "__main__":
    main()
