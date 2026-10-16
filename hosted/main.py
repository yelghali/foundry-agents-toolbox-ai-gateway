"""Identity-selected ABC hosted agent, caller-aware audit and input-only confidential mode."""

import os

os.environ["ENABLE_SENSITIVE_DATA"] = "false"
os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "false"
os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "false"

import asyncio
import base64
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

import httpx
from agent_framework import Agent, AgentContext, AgentMiddleware, FunctionInvocationContext, FunctionMiddleware, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework.openai import OpenAIChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.ai.agentserver.core import get_request_context
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from starlette.responses import JSONResponse

CONFIG = json.loads(os.environ["ABC_AGENT_CONFIG"])
credential = DefaultAzureCredential()


async def event(name: str, properties: dict) -> None:
    caller = get_request_context()
    payload = {
        "project": CONFIG["project"], "agent": CONFIG["agent"], "route": CONFIG["route"],
        "identity_mode": CONFIG["identity_mode"], "user_oid": caller.user_id,
        "session_id": caller.session_id,
        "caller_context_hash": base64.b64encode(hashlib.sha256(
            (caller.call_id or "").encode()
        ).digest()).decode() if caller.call_id else None,
        **properties,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(CONFIG["telemetry"]["endpoint"], json={
            "name": "Microsoft.ApplicationInsights.Event",
            "time": datetime.now(timezone.utc).isoformat(),
            "iKey": CONFIG["telemetry"]["instrumentationKey"],
            "data": {"baseType": "EventData", "baseData": {
                "ver": 2, "name": name,
                "properties": {key: str(value) for key, value in payload.items() if value is not None},
            }},
        })
        response.raise_for_status()
        if response.json().get("itemsAccepted") != 1:
            raise RuntimeError("ABC audit telemetry was not accepted.")


class RequestAudit(AgentMiddleware):
    async def process(self, context: AgentContext, call_next):
        user = get_request_context().user_id
        if not user:
            raise RuntimeError("The platform request has no user identity for audit attribution.")
        started = time.monotonic()
        values = {"phase": "started"}
        if CONFIG.get("confidential"):
            values["question"] = "\n".join(
                message.text for message in context.messages if message.role == "user" and message.text
            )
            context.options["store"] = False
        await event("abc_agent_request", values)
        try:
            await call_next()
        except Exception as error:
            await event("abc_agent_request", {"phase": "failed", "error_type": type(error).__name__})
            raise
        await event("abc_agent_request", {
            "phase": "completed", "elapsed_ms": round((time.monotonic() - started) * 1000),
            "answer_exported": False,
        })


class ToolAudit(FunctionMiddleware):
    async def process(self, context: FunctionInvocationContext, call_next):
        await event("abc_tool_call", {"tool": context.function.name, "phase": "started",
                                     "configured_search": CONFIG["search_endpoint"],
                                     "configured_index": CONFIG["index"], "configured_kb": CONFIG["kb"]})
        try:
            await call_next()
        except Exception as error:
            await event("abc_tool_call", {"tool": context.function.name, "phase": "failed",
                                         "error_type": type(error).__name__})
            raise
        await event("abc_tool_call", {"tool": context.function.name, "phase": "returned"})


async def retrieve(query: str, kind: str) -> str:
    token = credential.get_token("https://search.azure.com/.default").token
    encoded = token.split(".")[1]
    identity = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    path = f"indexes/{CONFIG['index']}/docs/search" if kind == "raw" else f"knowledgebases/{CONFIG['kb']}/retrieve"
    body = {"search": query, "top": 1} if kind == "raw" else {
        "messages": [{"role": "user", "content": [{"type": "text", "text": query}]}],
        "includeActivity": True,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{CONFIG['search_endpoint']}/{path}?api-version=2026-05-01-preview",
            headers={"Authorization": f"Bearer {token}", "x-ms-client-request-id": str(uuid.uuid4())},
            json=body,
        )
    await event("abc_data_call", {
        "kind": kind, "observed_url": str(response.url), "status": response.status_code,
        "data_principal_oid": identity["oid"], "data_audience": identity["aud"],
    })
    if response.status_code in (401, 403):
        return json.dumps({"error": {
            "code": "authorization_denied", "http_status": response.status_code,
            "observed_url": str(response.url), "data_principal_oid": identity["oid"],
        }})
    response.raise_for_status()
    result = response.json()
    if not CONFIG.get("confidential"):
        for activity in result.get("activity", []):
            if activity["type"] == "searchIndex":
                await event("abc_source_activity", {
                    "source": activity["knowledgeSourceName"], "count": activity.get("count"),
                    "elapsed_ms": activity.get("elapsedMs"),
                    "query_time": activity.get("queryTime"),
                    "source_activity_observed": True,
                })
    return json.dumps(result["value"] if kind == "raw" else result["response"])


@tool
async def search_index(query: str) -> str:
    """Query the configured cohort's raw Search index, without IQ planning."""
    return await retrieve(query, "raw")


@tool
async def retrieve_knowledge(query: str) -> str:
    """Query the configured cohort's IQ knowledge base."""
    return await retrieve(query, "iq")


@tool
async def ask_agent_a(target: str, question: str) -> str:
    """Invoke approved agent prompt-a or hosted-a in project A."""
    if target not in ("prompt-a", "hosted-a"):
        raise ValueError("The orchestrator may invoke only the two approved project-A peers.")
    parent = get_request_context()
    project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential)
    if target == "hosted-a":
        if not parent.call_id:
            raise RuntimeError("A hosted peer invocation requires the platform's trusted caller context.")
        token = credential.get_token("https://ai.azure.com/.default").token
        async with httpx.AsyncClient(timeout=600) as client:
            result = await client.post(
                f"{os.environ['FOUNDRY_PROJECT_ENDPOINT']}/agents/{target}/endpoint/protocols/a2a",
                headers={"Authorization": "Bearer " + token, "x-agent-foundry-call-id": parent.call_id,
                         "A2A-Version": "0.3"},
                json={"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "message/send",
                      "params": {"message": {"messageId": str(uuid.uuid4()), "role": "user",
                                           "parts": [{"kind": "text", "text": question}]},
                                 "configuration": {"blocking": True}}},
            )
            result.raise_for_status()
        child = result.json()
        if child.get("error"):
            code = (child["error"].get("data") or {}).get("code")
            await event("abc_agent_peer_call", {
                "target_agent": target, "phase": "unsupported" if code == "HostedAgentNotSupported" else "failed",
                "error_code": code, "initiating_user_oid": parent.user_id,
            })
            if code == "HostedAgentNotSupported":
                return json.dumps({"error": {"code": code, "backend_error": child["error"]}})
            raise RuntimeError(f"A2A peer failed: {json.dumps(child['error'])}")
        child = child["result"]
        answer = "\n".join(
            part["text"] for artifact in child.get("artifacts", [])
            for part in artifact.get("parts", []) if part.get("kind") == "text"
        )
        child_id = child["id"]
        status = "completed" if child["status"]["state"] == "completed" else child["status"]["state"]
        if status != "completed":
            await event("abc_agent_peer_call", {
                "target_agent": target, "child_response_id": child_id, "phase": "failed",
                "status": status, "error_code": (child.get("error") or {}).get("code"),
            })
            raise RuntimeError(f"Hosted peer did not complete: status={status}")
    else:
        response = project.get_openai_client().responses.create(
            input=question, store=False,
            extra_body={"agent_reference": {"name": target, "version": CONFIG["peer_versions"][target],
                                           "type": "agent_reference"}},
        )
        answer, child_id, status = response.output_text, response.id, response.status
    if status != "completed" or not answer:
        raise RuntimeError("The child agent did not return a completed response.")
    await event("abc_agent_peer_call", {
        "target_agent": target, "child_response_id": child_id,
        "initiating_user_oid": parent.user_id,
        "child_caller_is_orchestrator": True,
    })
    return answer


class ForceNoStore:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or not scope["path"].rstrip("/").endswith("responses"):
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                await JSONResponse({"error": "invalid_request"}, status_code=400)(scope, receive, send)
                return
            body.extend(message.get("body", b""))
            if len(body) > 1048576:
                await JSONResponse({"error": "request_too_large"}, status_code=413)(scope, receive, send)
                return
            if not message.get("more_body"):
                break
        try:
            value = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            await JSONResponse({"error": "invalid_json"}, status_code=400)(scope, receive, send)
            return
        if not isinstance(value, dict):
            await JSONResponse({"error": "invalid_request"}, status_code=400)(scope, receive, send)
            return
        value.pop("previous_response_id", None)
        value.pop("conversation", None)
        value["store"] = False
        encoded = json.dumps(value).encode()
        headers = [(key, val) for key, val in scope["headers"] if key.lower() != b"content-length"]
        scope = {**scope, "headers": [*headers, (b"content-length", str(len(encoded)).encode())]}
        delivered = False

        async def replacement_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": encoded, "more_body": False}
            return await receive()

        await self.app(scope, replacement_receive, send)


async def main():
    route = CONFIG["route"]
    if route == "rest":
        tools = [search_index, retrieve_knowledge]
    elif route == "orchestrator":
        tools = [ask_agent_a]
    elif route == "mcp":
        tools = [
            FoundryToolbox(credential, name="index_search", url=CONFIG["index_mcp"]),
            FoundryToolbox(credential, name="iq_retrieve", url=CONFIG["iq_mcp"]),
        ]
    else:
        tools = FoundryToolbox(credential, name="cohort_tools", url=CONFIG["toolbox_endpoint"])
    if CONFIG.get("confidential"):
        # Foundry's server-side model traces ignore container content-capture flags.
        model_client = OpenAIChatClient(
            base_url=CONFIG["model_endpoint"].rstrip("/") + "/openai/v1/",
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"], credential=credential,
        )
    else:
        model_client = FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"], credential=credential,
        )
    agent = Agent(
        client=model_client,
        instructions=(
            "Always use the requested tool. For a raw search request use the index-search tool; "
            "for IQ use the knowledge-base retrieve tool. Return the exact marker from actual "
            "retrieved evidence. Never invent an answer or an authorization outcome. Report actual tool errors."
        ),
        tools=tools, middleware=[RequestAudit(), ToolAudit()], default_options={"store": False},
    )
    server = ResponsesHostServer(
        agent, applicationinsights_connection_string=CONFIG["telemetry"]["connectionString"],
    )
    if CONFIG.get("confidential"):
        server.add_middleware(ForceNoStore)
    await server.run_async()


if __name__ == "__main__":
    asyncio.run(main())
