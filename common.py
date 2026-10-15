"""Shared nonsecret configuration, Azure requests and explicit project-scoped audit events."""

import base64
import json
import msvcrt
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from azure.identity import AzureCliCredential
from azure.ai.projects.models import (
    OpenApiFunctionDefinition, OpenApiProjectConnectionAuthDetails, OpenApiProjectConnectionSecurityScheme,
)

ROOT = Path(__file__).parent
from search_resources import index_body, knowledge_base_body, knowledge_source_body

SEARCH_VERSION = "2026-05-01-preview"
ARM_VERSION = "2025-10-01-preview"
FOUNDRY_USER_ROLE_ID = "53ca6127-db72-4b80-b1b0-d745d6d5456d"
SEARCH_INDEX_DATA_READER_ROLE_ID = "1407120a-92aa-4202-b7e9-c0e197c71c8f"


def load_config() -> dict:
    return json.loads((ROOT / ".config.json").read_text(encoding="utf-8-sig"))


def save_config(config: dict, label: str) -> None:
    # Publishers run independently; preserve the other projects' latest state.
    with (ROOT / ".config.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            current = load_config()
            replacement = next(item for item in config["cohorts"] if item["label"] == label)
            current["cohorts"] = [
                replacement if item["label"] == label else item for item in current["cohorts"]
            ]
            temporary = ROOT / ".config.next.json"
            temporary.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
            for attempt in range(3):
                try:
                    os.replace(temporary, ROOT / ".config.json")
                    break
                except PermissionError as error:
                    if error.winerror not in (5, 32) or attempt == 2:
                        raise
                    print("Runtime config temporarily held open; retrying atomic replacement.", flush=True)
                    time.sleep(0.5 * (attempt + 1))
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def credential(config: dict) -> AzureCliCredential:
    return AzureCliCredential(subscription=config["subscriptionId"], process_timeout=120)


def claims(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def arm(config: dict, method: str, resource_id: str, body: dict | None = None, version: str = ARM_VERSION):
    for attempt in range(3):
        response = requests.request(
            method,
            f"https://management.azure.com{resource_id}?api-version={version}",
            headers={
                "Authorization": "Bearer " + credential(config).get_token("https://management.azure.com/.default").token,
                **({"If-Match": "*"} if method == "PUT" and "/Microsoft.ApiManagement/" in resource_id else {}),
            },
            json=body,
            timeout=120,
        )
        if method not in ("GET", "PUT") or response.status_code not in (429, 502, 503, 504) or attempt == 2:
            break
        print(f"Azure control-plane {response.status_code}; retrying {method} {resource_id}.", flush=True)
        time.sleep(5 * (attempt + 1))
    response.raise_for_status()
    if not response.content:
        return None
    text = response.content.decode("utf-8-sig")
    return json.loads(text) if text.lstrip().startswith(("{", "[")) else text


def connection(config: dict, cohort: dict, name: str, target: str, auth: str, category: str = "RemoteTool",
               audience: str = "https://search.azure.com") -> str:
    resource_id = f"{cohort['project']['id']}/connections/{name}"
    properties = {
        "category": category, "authType": auth, "target": target,
        "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
    }
    if auth in ("ProjectManagedIdentity", "AgenticIdentityToken", "UserEntraToken"):
        properties["audience"] = audience
    arm(config, "PUT", resource_id, {"properties": properties})
    return resource_id


def grant(config: dict, principal: str, scope: str, role: str) -> str:
    name = uuid.uuid5(uuid.NAMESPACE_URL, f"{scope.lower()}|{principal.lower()}|{role.lower()}")
    resource_id = f"{scope}/providers/Microsoft.Authorization/roleAssignments/{name}"
    arm(config, "PUT", resource_id, {"properties": {
        "principalId": principal, "principalType": "ServicePrincipal",
        "roleDefinitionId": f"/subscriptions/{config['subscriptionId']}/providers/Microsoft.Authorization/roleDefinitions/{role}",
    }}, version="2022-04-01")
    return resource_id


def raw_search_tool(cohort: dict, connection_id: str) -> OpenApiFunctionDefinition:
    spec = {
        "openapi": "3.0.3",
        "info": {"title": f"Cohort {cohort['label'].upper()} raw Search", "version": "1.0.0"},
        "servers": [{"url": cohort["searchEndpoint"]}],
        "paths": {f"/indexes/{cohort['indexName']}/docs/search": {"post": {
            "operationId": f"search_index_{cohort['label']}",
            "description": f"Search only the raw cohort {cohort['label'].upper()} index for its normal access record.",
            "parameters": [{"name": "api-version", "in": "query", "required": True,
                            "schema": {"type": "string", "enum": [SEARCH_VERSION], "default": SEARCH_VERSION}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "required": ["search"],
                "properties": {"search": {"type": "string"}, "top": {"type": "integer", "default": 1}},
            }}}},
            "responses": {"200": {"description": "Actual Search documents", "content": {
                "application/json": {"schema": {"type": "object", "properties": {
                    "value": {"type": "array", "items": {"type": "object", "properties": {
                        "id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"},
                    }}}
                }}}
            }}},
        }}},
    }
    return OpenApiFunctionDefinition(
        name=f"search_index_{cohort['label']}", description=f"Raw Search index {cohort['indexName']}; no IQ planner.",
        spec=spec, default_params=["api-version"], auth=OpenApiProjectConnectionAuthDetails(
            security_scheme=OpenApiProjectConnectionSecurityScheme(project_connection_id=connection_id),
        ),
    )


def telemetry_settings(config: dict, cohort: dict) -> dict:
    value = arm(config, "GET", cohort["telemetry"]["appInsightsResourceId"], version="2020-02-02")
    text = value["properties"]["ConnectionString"]
    parts = dict(part.split("=", 1) for part in text.split(";") if "=" in part)
    endpoint = parts["IngestionEndpoint"].rstrip("/") + "/v2/track"
    if urlsplit(endpoint).scheme != "https" or not urlsplit(endpoint).hostname.endswith(".applicationinsights.azure.com"):
        raise RuntimeError("Unexpected Azure Monitor ingestion endpoint.")
    return {"connectionString": text, "instrumentationKey": parts["InstrumentationKey"], "endpoint": endpoint}


def audit(settings: dict, name: str, properties: dict) -> None:
    response = requests.post(
        settings["endpoint"],
        json={
            "name": "Microsoft.ApplicationInsights.Event",
            "time": datetime.now(timezone.utc).isoformat(),
            "iKey": settings["instrumentationKey"],
            "data": {"baseType": "EventData", "baseData": {
                "ver": 2, "name": name,
                "properties": {key: str(value) for key, value in properties.items() if value is not None},
            }},
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("itemsAccepted") != 1:
        raise RuntimeError(f"Azure Monitor did not accept the audit event: {result}")
