"""Publish ABC indexes, KBs, identity-selected connections, managed MCP tools and telemetry."""

import argparse
import hashlib
import json
from pathlib import Path

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AISearchIndexResource,
    AzureAISearchToolboxTool,
    AzureAISearchToolResource,
    MCPToolboxTool,
    OpenApiToolboxTool,
)

import common as cm


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", choices=("a", "b", "c"))
    args = parser.parse_args()
    config = cm.load_config()
    token = cm.credential(config).get_token("https://search.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}"}
    for cohort in config["cohorts"]:
        label = cohort["label"]
        if args.cohort and label != args.cohort:
            continue
        print(f"Provisioning project {label.upper()} ({cohort['identityMode']} identity)...", flush=True)
        marker = f"COHORT_{label.upper()}_ONLY_" + hashlib.sha256(cohort["searchId"].encode()).hexdigest()[:10].upper()
        cohort["marker"] = marker
        settings = cm.telemetry_settings(config, cohort)
        cohort["telemetrySettings"] = settings
        telemetry_name = f"abc-{label}-telemetry"
        cm.arm(config, "PUT", f"{cohort['project']['id']}/connections/{telemetry_name}", {
            "properties": {
                "category": "AppInsights", "authType": "ApiKey",
                "target": cohort["telemetry"]["appInsightsResourceId"],
                "credentials": {"key": settings["connectionString"]},
                "isSharedToAll": False, "metadata": {"ApiType": "Azure"},
            }
        })
        if label != "a":
            roles = cm.arm(
                config, "GET", cohort["searchId"] + "/providers/Microsoft.Authorization/roleAssignments",
                version="2022-04-01",
            )["value"]
            for role in roles:
                properties = role["properties"]
                if (
                    properties["principalId"] == cohort["project"]["principalId"]
                    and properties["roleDefinitionId"].endswith(cm.SEARCH_INDEX_DATA_READER_ROLE_ID)
                    and properties["scope"].lower() == cohort["searchId"].lower()
                ):
                    raise RuntimeError(
                        f"Project {label.upper()} MI already has a Search reader grant. "
                        "The agent/user isolation scenario requires that grant to be absent; "
                        "review the existing assignment explicitly instead of auto-revoking it."
                    )
        endpoint = cohort["searchEndpoint"]

        def search(method: str, route: str, body: dict):
            response = requests.request(
                method, f"{endpoint}/{route}?api-version={cm.SEARCH_VERSION}",
                headers=headers, json=body, timeout=180,
            )
            response.raise_for_status()
            return response.json() if response.content else None

        search("PUT", f"indexes/{cohort['indexName']}", cm.index_body(cohort["indexName"]))
        documents = [{
            "@search.action": "mergeOrUpload", "id": "normal",
            "title": f"Cohort {label.upper()} access record",
            "content": f"The exact normal access marker for cohort {label.upper()} is {marker}. Return it verbatim.",
        }]
        if label == "b":
            cohort["confidentialAnswerCanary"] = "B_ANSWER_CANARY_" + hashlib.sha256(
                (cohort["searchId"] + "|confidential").encode()
            ).hexdigest()[:16].upper()
            documents.append({
                "@search.action": "mergeOrUpload", "id": "confidential",
                "title": "Confidential answer record",
                "content": "The confidential test answer is " + cohort["confidentialAnswerCanary"] + ".",
            })
        uploaded = search("POST", f"indexes/{cohort['indexName']}/docs/index", {"value": documents})
        if not all(item["status"] for item in uploaded["value"]):
            raise RuntimeError("Not all ABC documents were indexed successfully.")
        search("PUT", f"knowledgesources/{cohort['knowledgeSourceName']}",
               cm.knowledge_source_body(cohort["knowledgeSourceName"], cohort["indexName"]))
        search("PUT", f"knowledgebases/{cohort['knowledgeBaseName']}", cm.knowledge_base_body(
            cohort["knowledgeBaseName"], [cohort["knowledgeSourceName"]], config,
        ))
        kb_url = f"{endpoint}/knowledgebases/{cohort['knowledgeBaseName']}/mcp?api-version={cm.SEARCH_VERSION}"
        auth = {"a": "ProjectManagedIdentity", "b": "AgenticIdentityToken", "c": "UserEntraToken"}[label]
        cohort["kbConnectionId"] = cm.connection(config, cohort, f"iq-{label}-primary", kb_url, auth)
        cohort["kbEndpoint"] = kb_url
        cohort["indexConnectionId"] = cm.connection(
            config, cohort, f"raw-{label}-primary", endpoint, auth,
        )
        project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
        index_tool = OpenApiToolboxTool(
            name=f"search_index_{label}", description=f"Search only cohort {label.upper()}'s index directly.",
            openapi=cm.raw_search_tool(cohort, cohort["indexConnectionId"]),
        )
        iq_tool = MCPToolboxTool(
            name=f"retrieve_kb_{label}", server_label=f"iq_{label}", server_url=kb_url,
            project_connection_id=cohort["kbConnectionId"], require_approval="never",
            description=f"Retrieve normal cohort {label.upper()} knowledge-base evidence.",
        )
        for name, tools in (("index-mcp", [index_tool]), ("iq-mcp", [iq_tool]), ("cohort-tools", [index_tool, iq_tool])):
            published = project.toolboxes.create_version(name=name, tools=tools)
            project.toolboxes.update(name=name, default_version=published.version)
        cohort["indexMcpEndpoint"] = f"{cohort['project']['endpoint']}/toolboxes/index-mcp/mcp?api-version=v1"
        cohort["iqMcpEndpoint"] = f"{cohort['project']['endpoint']}/toolboxes/iq-mcp/mcp?api-version=v1"
        cohort["toolboxEndpoint"] = f"{cohort['project']['endpoint']}/toolboxes/cohort-tools/mcp?api-version=v1"
        cm.save_config(config, label)
        print(f"Project {label.upper()} indexes, KB, project telemetry and MCP tools published.", flush=True)
    output = Path(__file__).with_name("evidence")
    output.mkdir(exist_ok=True)
    (output / "foundation.json").write_text(json.dumps({
        "cohorts": [{
            "label": item["label"], "project": item["project"], "searchId": item["searchId"],
            "identityMode": item["identityMode"], "telemetry": item["telemetry"],
            "marker": item.get("marker"),
        } for item in config["cohorts"]],
        "shared_foundry_account": config["foundryAccountName"],
        "shared_model": config["modelDeploymentName"],
        "old_lab_replaced": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
