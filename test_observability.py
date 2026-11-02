"""Offline privacy and isolated replay invariants; not live Azure evidence."""

import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import replay_observability as replay


class ObservabilityTests(unittest.TestCase):
    def test_linked_evidence_requires_exact_value_scenario_and_pointer(self):
        from validate_observability_docs import linked_evidence
        root, path = MagicMock(), MagicMock()
        root.__truediv__.return_value = path
        path.resolve.return_value = path
        path.is_relative_to.return_value = True
        path.is_file.return_value = True
        value = {"status": "completed", "output": []}
        path.read_text.return_value = json.dumps({"scenario": "a-native", "agentResponse": value})
        link = "[Full response](evidence/observability-a-native.json#/agentResponse)"
        with patch("validate_observability_docs.ROOT", root):
            self.assertTrue(linked_evidence(link, value, "agentResponse", "a-native"))
            self.assertFalse(linked_evidence(link, {}, "agentResponse", "a-native"))
            self.assertFalse(linked_evidence(link, value, "agentResponse", "b-native"))
            self.assertFalse(linked_evidence(link.replace("#/agentResponse", ""),
                                             value, "agentResponse", "a-native"))
            path.is_relative_to.return_value = False
            self.assertFalse(linked_evidence(link, value, "agentResponse", "a-native"))

    def test_delegated_evidence_requires_real_query_identity_and_exact_hosted_result(self):
        from copy import deepcopy
        from compile_observability_evidence import delegated_evidence
        claims = {"oid": "user", "tid": "tenant", "aud": "api",
                  "iss": "https://login.microsoftonline.com/tenant/v2.0",
                  "scp": "access_as_user", "azp": "oauth-client"}
        arguments = {"experiment_id": "experiment", "message": "oauth-toolbox", "count": 2}
        result = {"marker": "CUSTOM_MCP_ENTRA_VALIDATED", "arguments": arguments, "claims": claims}
        run = {"experimentId": "experiment",
               "callerTokenObservation": {"claims": {"oid": "user"}},
               "agentResponse": {"status": "completed", "output": [
                   {"type": "function_call_output", "output": json.dumps(result)}]}}
        selected = {"backendStatus": 200, "requestTimestamp": "2026-11-01T13:09:54Z",
                    "responseTimestamp": "2026-11-01T13:09:56Z",
                    "requestBody": json.dumps({"method": "tools/call", "params": {"arguments": arguments}}),
                    "responseBody": json.dumps({"result": {"structuredContent": result, "isError": False}})}
        container = {"validationConfiguration": {
            "tenantId": "tenant", "audience": "api", "scope": "access_as_user",
            "oauthClientId": "oauth-client"},
            "events": [
                {"event": "custom_mcp_auth_validated", "claims": claims,
                 "method": "POST", "path": "/mcp", "azureTimestamp": "2026-11-01T13:09:55Z"},
                {"event": "custom_mcp_tool", "claims": claims, "arguments": arguments,
                 "azureTimestamp": "2026-11-01T13:09:55.01Z"}]}
        events, observation, passed = delegated_evidence(run, selected, result, container)
        self.assertTrue(passed)
        self.assertEqual(events, container["events"])
        self.assertEqual(observation["claims"], claims)
        self.assertNotIn("header", observation)
        self.assertNotIn("result", events[1])
        for mutation in ("stale", "wrong-user", "wrong-client", "missing-auth", "wrong-hosted"):
            with self.subTest(mutation=mutation):
                changed_run, changed_container = deepcopy(run), deepcopy(container)
                if mutation == "stale":
                    changed_container["events"][1]["azureTimestamp"] = "2026-11-01T12:09:55Z"
                elif mutation == "wrong-user":
                    changed_run["callerTokenObservation"]["claims"]["oid"] = "other"
                elif mutation == "wrong-client":
                    changed_container["validationConfiguration"]["oauthClientId"] = "other"
                elif mutation == "missing-auth":
                    changed_container["events"] = changed_container["events"][1:]
                else:
                    changed_run["agentResponse"]["output"][0]["output"] = "{}"
                self.assertFalse(delegated_evidence(changed_run, selected, result, changed_container)[2])

    def test_scoped_mcp_collection_preserves_existing_application_events(self):
        import argparse
        import collect_mcp_exchanges as collector
        application = {"observedContainer": "application", "events": [{"event": "kept"}]}
        existing = {"containers": {"application": application}}
        custom = {"tenantId": "tenant", "apiAppId": "api", "scope": "api://api/access_as_user",
                  "oauthClientId": "client", "containerApp": "delegated", "resourceGroup": "rg"}
        config_path, root = MagicMock(), MagicMock()
        config_path.read_text.return_value = json.dumps(custom)
        root.__truediv__.return_value.__truediv__.return_value.read_text.return_value = json.dumps(existing)
        args = argparse.Namespace(custom_config=config_path, since="2026-11-01T13:00:00Z", kind="delegated")
        with patch.object(collector, "ROOT", root), \
                patch.object(collector.argparse.ArgumentParser, "parse_args", return_value=args), \
                patch.object(collector.subprocess, "run", return_value=MagicMock(returncode=0, stdout="")) as command, \
                patch.object(collector, "write") as write:
            collector.main()
        command.assert_called_once()
        self.assertEqual(write.call_args.args[1]["containers"]["application"], application)

    def test_token_excerpt_only_exports_safe_selected_claims(self):
        from update_observability_workshop import block, token_excerpt
        observation = {
            "validation": "DECODED_ONLY_NOT_VALIDATED",
            "header": {"alg": "RS256", "kid": "safe-kid", "jwk": "private-key"},
            "claims": {"oid": "principal", "aud": "audience", "scp": "read",
                       "exp": 100, "name": "private-name", "email": "private-email"},
            "rawToken": "private-token", "tokenSha256": "opaque-hash",
        }
        excerpt = token_excerpt(observation)
        self.assertEqual(excerpt["claims"], {"oid": "principal", "aud": "audience",
                                            "scp": "read", "exp": 100})
        self.assertEqual(excerpt["header"], {"alg": "RS256", "kid": "safe-kid"})
        self.assertNotIn("private", json.dumps(excerpt))
        self.assertNotIn("roles", excerpt["claims"])
        self.assertEqual(block("```json\n{}\n```", "text"),
                         "\n````text\n```json\n{}\n```\n````\n")

    def test_session_runtime_logs_match_sdk_datetime_and_exclude_session_metadata(self):
        from collect_hosted_runtime_logs import session_logs
        project = MagicMock()
        session = MagicMock()
        session.created_at = datetime(2026, 11, 1, 11, 30, 26, tzinfo=timezone.utc)
        session.version_indicator.agent_version = "2"
        session.agent_session_id = "private-session-value"
        project.agents.list_sessions.return_value = [session]
        response = MagicMock()
        messages = ["exact generated query/result", "session_id=private-session-value",
                    "private-session-value"]
        chunks = [("data: " + json.dumps({
            "timestamp": "2026-11-01T11:30:40Z", "stream": "stdout", "message": message,
        }) + "\n").encode() for message in messages]
        project.agents.get_session_log_stream.return_value = (response, iter(chunks))
        with patch("collect_hosted_runtime_logs.AIProjectClient", return_value=project), \
                patch("collect_hosted_runtime_logs.cm.credential"):
            result = session_logs({}, {"project": {"endpoint": "https://example.test"}},
                                  {"agent": "isolated", "version": "2"},
                                  {"startedAt": "2026-11-01T11:30:31+00:00",
                                   "completedAt": "2026-11-01T11:30:54+00:00"})
        self.assertEqual(result["status"], "CAPTURED_CORRELATED_LINES")
        self.assertEqual(len(result["selectedLines"]), 1)
        self.assertEqual(result["selectedLines"][0]["line"], messages[0])
        self.assertNotIn("private-session-value", json.dumps(result))
        response.close.assert_called_once()

    def test_three_stage_render_keeps_discovery_distinct_from_query(self):
        from update_observability_workshop import scenario_section
        capture = {
            "scenario": "b-custom", "verdict": "BLOCKED_AGENT_INSTANCE_CONTEXT",
            "agent": "isolated", "agentVersion": "3", "toolboxVersion": "2",
            "startedAt": "start", "completedAt": "end", "experimentId": "experiment",
            "input": "Call the requested tool.", "hostedHttpStatus": 200,
            "agentResponse": {"id": "response-test", "status": "failed",
                              "error": {"message": "actual AgentInstanceClientId error"}},
            "selectedApimExchange": {
                "apimRequestId": "request-test", "requestTimestamp": "request-time",
                "responseTimestamp": "response-time", "backendStatus": 200,
                "requestBody": '{"method":"tools/list","params":{},"id":1}',
                "responseBody": '{"error":{"message":"actual AgentInstanceClientId error"}}',
            },
            "mcpValidatedQueryResultEvents": [],
            "hostedRuntimeLogQuery": {"status": "NO_CORRELATED_RUNTIME_LINES"},
            "hostedAgentSnapshot": {"runtimeConsoleLog": "NOT_CAPTURED"},
            "apimEndpoint": "https://example.test/isolated",
            "configuredMcpDestination": "https://example.test/mcp",
        }
        root = MagicMock()
        root.__truediv__.return_value.__truediv__.return_value.read_text.return_value = '{"apimExchanges":[]}'
        with patch("update_observability_workshop.ROOT", root):
            rendered = scenario_section(capture)
        self.assertIn("**No `tools/call` query was produced.**", rendered)
        self.assertNotIn("Actual generated tool", rendered)
        self.assertIn(capture["input"], rendered)
        self.assertIn(capture["selectedApimExchange"]["requestBody"], rendered)
        self.assertIn(capture["selectedApimExchange"]["responseBody"], rendered)
        self.assertIn("actual AgentInstanceClientId error", rendered)
        self.assertIn("NO_CORRELATED_RUNTIME_LINES", rendered)
        self.assertIn("| User → agent |", rendered)
        self.assertIn("| Agent → APIM → Toolbox |", rendered)
        self.assertIn("| Toolbox → MCP | **NOT_OBSERVED** token", rendered)
        self.assertIn("Matching APIM `oid`", rendered)
        self.assertIn("Configured identities (not token observations)", rendered)
        capture["selectedApimExchange"]["requestBody"] = json.dumps({
            "method": "tools/call", "params": {"name": "actual_tool",
                                             "arguments": {"queries": ["exact generated query"]}},
        })
        with patch("update_observability_workshop.ROOT", root):
            rendered = scenario_section(capture)
        self.assertIn("Actual generated tool `actual_tool` arguments", rendered)
        self.assertIn(json.dumps({"queries": ["exact generated query"]}, indent=2), rendered)
        self.assertNotIn("**No `tools/call` query was produced.**", rendered)

    def test_hosted_snapshot_excludes_consent_payload_and_model_narrative(self):
        from compile_observability_evidence import hosted_snapshot
        snapshot = hosted_snapshot({
            "scenario": "c-custom",
            "agentResponse": {
                "id": "response-test", "status": "completed",
                "output": [
                    {"type": "oauth_consent_request", "consent_link": "private-url"},
                    {"type": "message", "content": "unverified model claim"},
                    {"type": "function_call", "call_id": "call-test",
                     "name": "observed___identity_probe", "arguments": "{}"},
                ],
            },
        })
        text = json.dumps(snapshot)
        self.assertNotIn("private-url", text)
        self.assertNotIn("unverified model claim", text)
        self.assertEqual(snapshot["events"][0], {"type": "oauth_consent_request"})
        self.assertEqual(snapshot["runtimeConsoleLog"], "NOT_A_RUNTIME_LOG")

    def test_sensitive_values_are_removed(self):
        value = {
            "Authorization": "Bearer secret",
            "agent_session_id": "opaque",
            "clientSecret": "secret",
            "text": "Bearer abc.def.ghi https://global.consent.azure-apim.net/login?data=opaque",
            "jwt": "eyJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJzZWNyZXQifQ.signature",
            "experiment_id": "safe-id",
            "body": '{"_meta":{"baggage":"azure.ai.agentserver.session_id=opaque,user.id=private"}}',
            "properties": '{"body":"{\\"_meta\\":{\\"baggage\\":\\"session=opaque\\"}}"}',
        }
        text = json.dumps(replay.safe(value))
        for forbidden in ("opaque", "secret", "abc.def.ghi", "eyJhbGci", "?data=", "user.id=private"):
            self.assertNotIn(forbidden, text)
        self.assertIn("safe-id", text)
        properties = json.loads(replay.safe(value)["properties"])
        self.assertEqual(json.loads(properties["body"])["_meta"]["baggage"], "<baggage-redacted>")

    def test_policy_only_hashes_caller_context(self):
        policy = (replay.ROOT / "policies" / "toolbox-proxy-policy.xml").read_text()
        self.assertIn("SHA256", policy)
        self.assertIn('name="caller_context_hash"', policy)
        self.assertNotIn('metadata name="Authorization"', policy)
        self.assertNotIn('metadata name="x-agent-foundry-call-id"', policy)
        self.assertIn('header-name="Authorization"', policy)
        self.assertIn("https://ai.azure.com", policy)

    def test_consent_redaction_preserves_nested_json(self):
        nested = json.dumps({"error": {"message": json.dumps({
            "message": "https://global.consent.azure-apim.net/login?data=opaque",
        })}})
        sanitized = replay.safe(nested)
        result = json.loads(sanitized)
        self.assertEqual(json.loads(result["error"]["message"])["message"], "<consent-url-redacted>")

    def test_azure_console_timestamps_are_timezone_aware(self):
        from collect_mcp_exchanges import azure_timestamp
        plain = azure_timestamp("2026-10-31T21:10:00")
        zoned = azure_timestamp("2026-10-31T21:10:00Z")
        self.assertEqual(plain, zoned)
        self.assertIsNotNone(plain.tzinfo)

    def test_opaque_oauth_request_id_is_not_exported(self):
        result = replay.safe({"id": "oacr_opaque-continuation-identifier"})
        self.assertEqual(result["id"], "<oauth-request-id-redacted>")

    def test_isolated_hosting_dependency_contract(self):
        requirements = (replay.ROOT / "hosted" / "observability-requirements.txt").read_text()
        self.assertIn("agent-framework-core==1.20.0", requirements)
        self.assertIn("mcp==1.27.2", requirements)
        source = Path(replay.__file__).read_text()
        self.assertIn("VersionRefIndicator(agent_version=record", source)
        self.assertNotIn("version_selector", source)
        self.assertNotIn("oauthPassword", source)

    def test_repair_renders_valid_xml_and_empty_bodies(self):
        with patch.object(replay.cm, "arm", return_value={"properties": {}}) as arm:
            replay.repair_policy({"tenantId": "tenant"}, {
                "apiId": "/isolated", "scenario": "a-native",
                "toolboxEndpoint": "https://example.test/toolboxes/isolated/mcp?api-version=v1",
            })
        saved = arm.call_args_list[0].args[3]["properties"]["value"]
        diagnostic = arm.call_args_list[-1].args[3]["properties"]
        for side in ("frontend", "backend"):
            self.assertEqual(diagnostic[side]["request"]["body"]["bytes"], 0)
            self.assertEqual(diagnostic[side]["response"]["body"]["bytes"], 0)
        self.assertIn("$..baggage", saved)
        self.assertIn("&lt;consent-url-redacted&gt;", saved)
        self.assertIn("context.Response.Body == null", saved)
        self.assertIn("body.Length == 0", saved)
        self.assertIn("&lt;empty-body&gt;", saved)
        import xml.etree.ElementTree as ET
        ET.fromstring(saved)


if __name__ == "__main__":
    unittest.main()
