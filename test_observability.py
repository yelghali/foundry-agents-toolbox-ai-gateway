"""Offline privacy and isolated replay invariants; not live Azure evidence."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import replay_observability as replay


class ObservabilityTests(unittest.TestCase):
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
