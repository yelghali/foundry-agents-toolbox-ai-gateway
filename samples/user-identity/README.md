# C — User identity: two different paths

- [Native trusted Search KB](./trusted-kb/README.md): `UserEntraToken`, Search
  audience, signed-in user's Search data role. Hosting propagates user context.
- [Custom FastMCP](./custom-oauth/README.md): `OAuth2`, Entra API delegated scope,
  explicit connection consent and authorization-code/refresh flow.

Copy one child folder: each includes a full independent provisioner, hosted
agent, caller and requirements. Custom OAuth also includes its own MCP server.
An arbitrary custom endpoint is not a trusted native UserEntraToken destination.
The OAuth experiment does **not** establish literal JWT-bearer OBO; validated
user claims prove delegated identity, not the internal grant type.
