"""Offline tests: claims are allowlisted and spoofed decoding is never validation."""

import json
import unittest

import jwt

from replay_observability import safe
from token_evidence import token_observation


class TokenEvidenceTests(unittest.TestCase):
    def test_decoding_spoof_is_explicit_and_never_saves_jwt(self):
        token = jwt.encode({
            "oid": "spoofed-user", "aud": "https://ai.azure.com",
            "name": "private name", "email": "private@example.test",
            "access_token": "opaque-credential", "roles": ["observed-role"],
        }, "test-key-not-a-credential", algorithm="HS256", headers={"kid": "test"})
        result = token_observation(token, boundary="offline caller")
        self.assertEqual(result["validation"], "DECODED_ONLY_NOT_VALIDATED")
        self.assertEqual(result["claims"], {
            "oid": "spoofed-user", "aud": "https://ai.azure.com", "roles": ["observed-role"],
        })
        serialized = json.dumps(safe(result))
        for value in (token, token.split(".")[2], "private name", "private@example.test",
                      "opaque-credential", "test-key-not-a-credential"):
            self.assertNotIn(value, serialized)

    def test_validated_selection_uses_boundary_supplied_claims(self):
        token = jwt.encode({"oid": "untrusted"}, "test-key", algorithm="HS256")
        result = token_observation(token, boundary="offline verified boundary",
                                   validated=True, claims={"oid": "verified", "name": "private"})
        self.assertEqual(result["claims"], {"oid": "verified"})
        self.assertEqual(result["validation"], "VALIDATED_AT_BOUNDARY")
        self.assertNotIn("roles", result["claims"])

    def test_invalid_input_has_no_token_metadata(self):
        self.assertEqual(token_observation("opaque-context", boundary="caller"), {
            "boundary": "caller", "validation": "NOT_OBSERVED_JWT",
        })

    def test_opaque_credentials_context_and_consent_state_are_redacted(self):
        value = safe({
            "token": "opaque-token", "jwt": "opaque-jwt", "bearer": "opaque-bearer",
            "x-agent-foundry-call-id": "opaque-context",
            "consent_state": "opaque-state", "oauth_state": "opaque-state",
            "caller_context_hash": "allowed-hash", "tokenSha256": "allowed-fingerprint",
        })
        self.assertNotIn("opaque", json.dumps(value))
        self.assertEqual(value["caller_context_hash"], "allowed-hash")
        self.assertEqual(value["tokenSha256"], "allowed-fingerprint")

    def test_apim_metadata_is_after_token_validation_and_not_input_headers(self):
        from replay_observability import ROOT
        policy = (ROOT / "policies" / "toolbox-proxy-policy.xml").read_text()
        self.assertLess(policy.index("</validate-azure-ad-token>"),
                        policy.index('name="selected_token_claims"'))
        self.assertIn('context.Variables[&quot;toolbox-caller&quot;]', policy)
        self.assertNotIn('Headers.GetValueOrDefault(&quot;selected_token_claims&quot;', policy)
        self.assertIn("UNCHANGED_BEARER_NO_APIM_EXCHANGE", policy)


if __name__ == "__main__":
    unittest.main()
