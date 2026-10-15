"""Verify project telemetry isolation, real data denials, peer invocation and question-only confidentiality."""

import argparse
import json
import time
from datetime import datetime, timezone

import requests
from azure.ai.projects import AIProjectClient

import common as cm


def query(config: dict, cohort: dict, text: str) -> dict:
    response = requests.post(
        f"https://api.loganalytics.azure.com/v1/workspaces/{cohort['telemetry']['workspaceId']}/query",
        headers={"Authorization": "Bearer " + cm.credential(config).get_token("https://api.loganalytics.io/.default").token},
        json={"query": text},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--privacy", action="store_true")
    parser.add_argument("--store-request", action="store_true")
    parser.add_argument("--audits", action="store_true")
    parser.add_argument("--gateway", action="store_true")
    parser.add_argument("--user-ingress", action="store_true")
    args = parser.parse_args()
    config = cm.load_config()
    checks = {}
    results = {}
    for cohort in config["cohorts"]:
        project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
        actual = project.telemetry.get_application_insights_connection_string()
        checks[f"{cohort['label']}_telemetry_binding"] = actual == cohort["telemetrySettings"]["connectionString"]
        if args.audits:
            expected = cohort["project"]["name"]
            text = f"""
AppEvents
| where TimeGenerated > ago(24h)
| where Name startswith "abc_"
| extend p=todynamic(Properties)
| summarize OwnEvents=countif(tostring(p["project"]) == "{expected}"),
    ForeignProjectEvents=countif(isnotempty(tostring(p["project"])) and tostring(p["project"]) != "{expected}")
"""
            table = query(config, cohort, text)["tables"][0]
            own, foreign = table["rows"][0]
            checks[f"{cohort['label']}_custom_audits_present"] = own > 0
            checks[f"{cohort['label']}_custom_audits_separate"] = foreign == 0
            results[f"{cohort['label']}_audits"] = {"own_event_count": own, "foreign_project_event_count": foreign}
    if args.gateway:
        cohort = config["cohorts"][1]
        observed = {}
        for agent in ("prompt-b", "hosted-b"):
            for kind in ("raw", "iq"):
                record = json.loads((cm.ROOT / "evidence" / f"{agent}-data-gateway-{kind}.json").read_text())
                if record["status"] != "PASS":
                    raise RuntimeError("Gateway retrieval must pass before checking its principal.")
                path = (f"/indexes/{cohort['indexName']}/docs/search" if kind == "raw" else
                        f"/knowledgebases/{cohort['knowledgeBaseName']}/mcp")
                principal = cohort["agents"][agent]["principalId"]
                text = f"""
let events=AppTraces
| where TimeGenerated between (datetime({record['started_at']}) .. datetime({record['completed_at']}))
| extend p=todynamic(Properties)
| where tostring(p.mcp_server_id) == "abc-b-search-data";
let requests=events
| where Message == "Search data request; original agent bearer forwarded."
| project RequestId=tostring(p.apim_request_id), Principal=tostring(p.data_principal_oid),
    Path=tostring(p.observed_operation_path);
let responses=events
| where Message == "Search data response."
| where tostring(p.backend_status) == "200"
| project RequestId=tostring(p.apim_request_id);
requests | join kind=inner responses on RequestId
| where Principal == "{principal}" and Path == "{path}"
| project RequestId, Principal, Path
"""
                table = query(config, cohort, text)["tables"][0]
                rows = table["rows"]
                checks[f"{agent}_{kind}_gateway_principal"] = bool(rows)
                observed[f"{agent}/{kind}"] = rows
        results["gateway_actual_principals"] = observed
    if args.user_ingress:
        cohort = config["cohorts"][2]
        observed = {}
        for agent in ("prompt-c", "hosted-c"):
            record = json.loads((cm.ROOT / "evidence" / f"{agent}-user-ingress-iq.json").read_text())
            if record["status"] != "PASS":
                raise RuntimeError("The managed-user ingress retrieval must pass before checking its audit.")
            text = f"""
let events=AppTraces
| where TimeGenerated between (datetime({record['started_at']}) .. datetime({record['completed_at']}))
| extend p=todynamic(Properties)
| where tostring(p.mcp_server_id) == "abc-c-agent-ingress";
let calls=events
| where tostring(p.client_request_id) == "{record['correlation_id']}"
| where tostring(p.user_oid) == "{record['user_oid']}"
| project RequestId=tostring(p.apim_request_id), UserOid=tostring(p.user_oid),
    Kind=tostring(p.agent_kind), Correlation=tostring(p.client_request_id);
let responses=events
| where Message == "Agent ingress response." and tostring(p.backend_status) == "200"
| project RequestId=tostring(p.apim_request_id);
calls | join kind=inner responses on RequestId
| project RequestId, UserOid, Kind, Correlation
"""
            rows = query(config, cohort, text)["tables"][0]["rows"]
            checks[f"{agent}_ingress_user_correlated"] = bool(rows)
            observed[agent] = rows
        assignments = cm.arm(
            config, "GET", cohort["searchId"] + "/providers/Microsoft.Authorization/roleAssignments",
            version="2022-04-01",
        )["value"]
        forbidden = {cohort["project"]["principalId"], *(
            item["principalId"] for item in cohort["agents"].values()
        )}
        application_data_grants = [
            item["id"] for item in assignments
            if item["properties"]["principalId"] in forbidden
            and item["properties"]["roleDefinitionId"].split("/")[-1] in (
                cm.SEARCH_INDEX_DATA_READER_ROLE_ID, "8ebe5a00-799e-43f5-93ac-243d3dce84a7",
            )
        ]
        checks["c_no_project_or_agent_search_data_grants"] = not application_data_grants
        primary = cm.arm(config, "GET", cohort["kbConnectionId"])["properties"]
        checks["c_downstream_managed_user_auth"] = (
            primary["authType"] == "UserEntraToken" and primary["target"] == cohort["kbEndpoint"]
        )
        results["user_ingress"] = {"observed_users": observed, "application_data_grants": application_data_grants,
                                   "apim_search_obo": False, "toolbox_auth": primary["authType"]}
        unauthenticated = requests.post(
            cohort["userIngress"]["endpoint"] + "/prompt",
            json={"input": "Unauthenticated ingress probe"}, timeout=60,
        )
        checks["c_unauthenticated_ingress_rejected"] = unauthenticated.status_code == 401
        results["user_ingress"]["unauthenticated_http_status"] = unauthenticated.status_code
    if args.privacy:
        cohort = config["cohorts"][1]
        canary = cohort["confidentialAnswerCanary"]
        filename = "b-confidential-direct-raw" + ("-store-request" if args.store_request else "") + ".json"
        record = json.loads((cm.ROOT / "evidence" / filename).read_text())
        if record["status"] != "PASS":
            raise RuntimeError("The confidential retrieval must pass before checking telemetry.")
        since = record["started_at"]
        question_phrase = "This question is the confidentiality audit for project B"
        canary_query = f"""
union isfuzzy=true AppEvents, AppTraces, AppRequests, AppDependencies, AppExceptions, AppGenAIContent
| where TimeGenerated >= datetime({since})
| where tostring(pack_all()) contains "{canary}"
| summarize AnswerCanaryRows=count()
"""
        question_query = f"""
AppEvents
| where TimeGenerated >= datetime({since})
| where Name == "abc_agent_request"
| extend p=todynamic(Properties)
| where tostring(p.agent) == "b-confidential"
| where tostring(p.question) contains "{question_phrase}"
| project TimeGenerated, UserOid=tostring(p.user_oid), Phase=tostring(p.phase),
    Question=tostring(p.question)
"""
        deadline = time.monotonic() + 300
        while True:
            answers = query(config, cohort, canary_query)
            questions = query(config, cohort, question_query)
            answer_count = answers["tables"][0]["rows"][0][0]
            question_rows = questions["tables"][0]["rows"]
            if answer_count:
                raise RuntimeError("The confidential answer canary was found in project B telemetry.")
            if question_rows:
                break
            if time.monotonic() + 20 > deadline:
                raise RuntimeError("Confidential input-only question audit was not observed.")
            print("Waiting for question-only telemetry ingestion...", flush=True)
            time.sleep(20)
        checks["confidential_question_logged"] = bool(question_rows)
        checks["confidential_answer_absent_from_telemetry"] = answer_count == 0
        checks["confidential_answer_returned_to_caller"] = record["marker_found"]
        token = cm.credential(config).get_token("https://ai.azure.com/.default").token
        base = cohort["project"]["endpoint"]
        urls = [
            f"{base}/agents/b-confidential/endpoint/protocols/openai/responses/{record['response_id']}?api-version=v1",
            f"{base}/openai/v1/responses/{record['response_id']}",
        ]
        retrieval = []
        for url in urls:
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
            retrieval.append({
                "url": url, "http_status": response.status_code,
                "answer_canary_present": canary in response.text,
            })
        checks["hosted_response_retrieval_not_found"] = (
            retrieval[0]["http_status"] == 404 and not retrieval[0]["answer_canary_present"]
        )
        results["privacy"] = {
            "question_rows": question_rows, "answer_canary_rows": answer_count,
            "response_retrieval": retrieval,
            "telemetry_tables_scanned": ["AppEvents", "AppTraces", "AppRequests", "AppDependencies", "AppExceptions", "AppGenAIContent"],
            "telemetry_scan_since": since,
            "provider_internal_retention_proven_disabled": False,
            "response_storage_control": "Caller store:false; confidential ASGI middleware also forces store:false.",
            "caller_requested_storage": record["requested_store"],
            "generic_project_response_probe_is_not_storage_proof": True,
        }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks, "results": results,
        "all_resources_retained": True,
    }
    (cm.ROOT / "evidence" / "showcase-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks}, indent=2))
    if result["status"] != "PASS":
        raise RuntimeError("ABC showcase assertions failed.")


if __name__ == "__main__":
    main()
