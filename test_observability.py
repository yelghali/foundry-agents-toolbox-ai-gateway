"""Offline privacy and isolated replay invariants; not live Azure evidence."""

import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import replay_observability as replay


class ObservabilityTests(unittest.TestCase):
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
        with patch.object(replay.cm, "arm", return_value={}) as arm:
            replay.repair_policy({"tenantId": "tenant"}, {
                "apiId": "/isolated", "scenario": "a-native",
                "toolboxEndpoint": "https://example.test/toolboxes/isolated/mcp?api-version=v1",
            })
        saved = arm.call_args.args[3]["properties"]["value"]
        self.assertIn("context.Response.Body == null", saved)
        self.assertIn("body.Length == 0", saved)
        self.assertIn("&lt;empty-body&gt;", saved)
        import xml.etree.ElementTree as ET
        ET.fromstring(saved)


if __name__ == "__main__":
    unittest.main()
