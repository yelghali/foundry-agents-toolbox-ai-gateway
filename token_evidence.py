"""Allowlisted token observations; decoding never implies signature validation."""

import base64
import hashlib
import json

CLAIMS = ("iss", "aud", "tid", "oid", "azp", "appid", "scp", "roles", "idtyp",
          "ver", "exp", "iat")
HEADERS = ("alg", "kid")


def selected_claims(claims):
    return {name: claims[name] for name in CLAIMS if name in claims}


def token_observation(token, *, boundary, validated=False, claims=None):
    """Only a boundary that already verified the JWT may mark it validated."""
    header = {}
    if claims is None:
        claims = {}
    try:
        parts = token.split(".")
        header = json.loads(base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4)))
        if not validated:
            claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except (ValueError, IndexError, UnicodeError):
        return {"boundary": boundary, "validation": "NOT_OBSERVED_JWT"}
    return {
        "boundary": boundary,
        "validation": "VALIDATED_AT_BOUNDARY" if validated else "DECODED_ONLY_NOT_VALIDATED",
        "header": {name: header[name] for name in HEADERS if name in header},
        "claims": selected_claims(claims),
        "tokenSha256": hashlib.sha256(token.encode()).hexdigest(),
    }
