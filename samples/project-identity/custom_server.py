"""Standalone application-token MCP target; never acquires or exchanges tokens."""

import contextvars
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

import jwt
import uvicorn
from fastmcp import FastMCP
from starlette.responses import JSONResponse

IDENTITY = contextvars.ContextVar("application_identity", default=None)
TOKEN_OBSERVATION = contextvars.ContextVar("validated_token_observation", default=None)
mcp = FastMCP("Application identity probe", include_fastmcp_meta=False)


class ApplicationTokenValidator:
    def __init__(self, tenant, audience, expected_principals, signing_keys=None):
        self.tenant = str(uuid.UUID(tenant))
        self.audience = audience
        self.expected_principals = {str(uuid.UUID(value)) for value in expected_principals}
        if not audience or not self.expected_principals:
            raise ValueError("Audience and explicit principal allowlist are required")
        self.issuer = f"https://login.microsoftonline.com/{self.tenant}/v2.0"
        self.keys = signing_keys or jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{self.tenant}/discovery/v2.0/keys",
            cache_keys=True, lifespan=3600, timeout=15,
        )

    def validate(self, token):
        key = self.keys.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=self.audience, issuer=self.issuer,
            options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid", "ver"]},
        )
        if (claims["tid"] != self.tenant or claims["aud"] != self.audience
                or claims["ver"] != "2.0" or not isinstance(claims["oid"], str)
                or "scp" in claims or claims.get("idtyp") == "user"
                or claims["oid"] not in self.expected_principals):
            raise jwt.InvalidTokenError("Application principal not authorized")
        # Only validated identifiers are returned; no token, user PII or arbitrary claims.
        return {name: claims[name] for name in
                ("tid", "oid", "aud", "iss", "ver", "appid", "azp", "roles", "idtyp", "exp", "iat")
                if name in claims}


@mcp.tool
def identity_probe(experiment_id: str) -> dict:
    """Return validated application identifiers for a nonsensitive experiment UUID."""
    experiment_id = str(uuid.UUID(experiment_id))
    identity = IDENTITY.get()
    if identity is None:
        raise RuntimeError("Validated application identity required")
    result = {
        "marker": "CUSTOM_MCP_APPLICATION_VALIDATED",
        "experiment_id": experiment_id,
        "claims": identity,
        "tokenObservation": TOKEN_OBSERVATION.get(),
    }
    print(json.dumps({
        "event": "validated_mcp_exchange",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": "tools/call", "tool": "identity_probe",
        "query": {"experiment_id": experiment_id}, "result": result,
    }), flush=True)
    return result


class EntraBoundary:
    def __init__(self, app, validator):
        self.app = app
        self.validator = validator

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"] == "/healthz":
            return await JSONResponse({"status": "ready"})(scope, receive, send)
        authorization = dict(scope["headers"]).get(b"authorization", b"")
        try:
            scheme, token = authorization.decode("ascii").split(" ", 1)
            if scheme.lower() != "bearer" or not token:
                raise jwt.InvalidTokenError("Bearer required")
            identity = self.validator.validate(token)
        except (jwt.PyJWTError, ValueError, UnicodeError):
            return await JSONResponse(
                {"error": "invalid_application_token"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
        header = jwt.get_unverified_header(token)
        observation = {
            "boundary": "application MCP signature/issuer/audience/principal validation",
            "validation": "VALIDATED_AT_MCP_BOUNDARY",
            "header": {name: header[name] for name in ("alg", "kid") if name in header},
            "claims": identity,
            "tokenSha256": hashlib.sha256(token.encode()).hexdigest(),
        }
        print(json.dumps({
            "event": "application_mcp_auth_validated", "tokenObservation": observation,
            "method": scope["method"], "path": scope["path"],
        }), flush=True)
        handle = IDENTITY.set(identity)
        token_handle = TOKEN_OBSERVATION.set(observation)
        try:
            await self.app(scope, receive, send)
        finally:
            IDENTITY.reset(handle)
            TOKEN_OBSERVATION.reset(token_handle)


def create_app(validator):
    return EntraBoundary(
        mcp.http_app(path="/mcp", stateless_http=True, json_response=True), validator,
    )


if __name__ == "__main__":
    validator = ApplicationTokenValidator(
        os.environ["AZURE_TENANT_ID"],
        os.environ["CUSTOM_MCP_AUDIENCE"],
        [value.strip() for value in os.environ["CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS"].split(",")],
    )
    uvicorn.run(
        create_app(validator), host="0.0.0.0", port=8000,
        access_log=False, log_level="warning",
    )
