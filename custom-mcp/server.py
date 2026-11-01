"""No token acquisition or exchange: validate the token supplied by Toolbox."""

import contextvars
import json
import os
import uuid
from typing import Literal

import jwt
import uvicorn
from fastmcp import FastMCP
from starlette.responses import JSONResponse

TENANT = os.environ["ENTRA_TENANT_ID"]
AUDIENCE = os.environ["ENTRA_AUDIENCE"]
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
KEYS = jwt.PyJWKClient(
    f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys",
    cache_keys=True, lifespan=3600, timeout=15,
)
IDENTITY = contextvars.ContextVar("validated_identity", default=None)
# Toolbox rejects FastMCP 2.14's optional, unnamespaced "_fastmcp" metadata.
mcp = FastMCP("Direct Toolbox Entra experiment", include_fastmcp_meta=False)


def safe_event(event, **values):
    print(json.dumps({"event": event, **values}, separators=(",", ":")), flush=True)


def validate(token):
    key = KEYS.get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token, key, algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER,
        options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid", "scp"]},
        leeway=30,
    )
    if claims["tid"] != TENANT or "access_as_user" not in claims["scp"].split():
        raise jwt.InvalidTokenError("Required tenant or delegated scope missing")
    return {name: claims[name] for name in
            ("tid", "oid", "aud", "iss", "scp", "azp", "appid", "roles", "idtyp", "ver", "exp", "iat")
            if name in claims}


@mcp.tool
def probe_echo(
    experiment_id: str,
    message: Literal["hello-toolbox", "oauth-toolbox", "managed-toolbox"],
    count: int = 1,
) -> dict:
    """Echo only a nonsensitive experiment UUID, allowlisted message and count (1-3)."""
    experiment_id = str(uuid.UUID(experiment_id))
    if not 1 <= count <= 3:
        raise ValueError("count must be 1-3")
    identity = IDENTITY.get()
    if not identity:
        raise RuntimeError("Validated delegated identity required")
    args = {"experiment_id": experiment_id, "message": message, "count": count}
    safe_event("custom_mcp_tool", claims=identity, arguments=args)
    return {"marker": "CUSTOM_MCP_ENTRA_VALIDATED", "arguments": args, "claims": identity}


class EntraBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"] == "/healthz":
            return await JSONResponse({"status": "ready"})(scope, receive, send)
        headers = dict(scope["headers"])
        authorization = headers.get(b"authorization", b"").decode("ascii", errors="ignore")
        try:
            if not authorization.startswith("Bearer "):
                raise jwt.InvalidTokenError("Bearer required")
            identity = validate(authorization[7:])
        except Exception as error:
            safe_event("custom_mcp_auth_rejected", error_type=type(error).__name__)
            return await JSONResponse(
                {"error": "invalid_delegated_token"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
        safe_event("custom_mcp_auth_validated", claims=identity, method=scope["method"], path=scope["path"])
        handle = IDENTITY.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            IDENTITY.reset(handle)


if __name__ == "__main__":
    uvicorn.run(
        EntraBoundary(mcp.http_app(path="/mcp", stateless_http=True, json_response=True)),
        host="0.0.0.0", port=8000, access_log=False, log_level="warning",
    )
