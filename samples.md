# Toolbox identity samples

Copy **one** scenario folder. Each contains its own complete provisioner, hosted
agent, caller and pinned runtime requirements: no lab configuration, common
imports or authentication-mode switch.

A and B also include independently runnable `custom_server.py` and separately
named `provision_custom_toolbox.py` for a custom Entra application audience.
Native Search targets remain unchanged. Both custom servers validate application
tokens and explicit principal allowlists, rejecting C's delegated tokens.
See each scenario README for API registration, local server and verification gate.
**A custom acquisition was live observed** in the workshop's isolated APIM/MCP
exchange. **B remains blocked at upstream Toolbox agent-instance resolution**;
local tests are not live token-acquisition evidence.

| Scenario | Connection auth | Downstream data principal | Search data role |
| --- | --- | --- | --- |
| [A: project identity](./samples/project-identity/README.md) | `ProjectManagedIdentity` | Project managed identity | Project MI object ID |
| [B: agent identity](./samples/agent-identity/README.md) | `AgenticIdentityToken` | Calling agent instance | Agent instance object ID |
| [C: native trusted KB](./samples/user-identity/trusted-kb/README.md) | `UserEntraToken` | Signed-in user | User object ID |
| [C: custom FastMCP OAuth](./samples/user-identity/custom-oauth/README.md) | `OAuth2` | Consented user | No Search role; API delegated scope |

[C's overview](./samples/user-identity/README.md) explains the two distinct user
paths. Custom OAuth uses authorization code and refresh tokens; it is **not**
evidence of literal JWT-bearer OBO. The hosted agent does not perform token exchange.

The local setup/invocation client, hosted runtime, project owner and downstream
data principal are different concepts. Project resource IDs locate connections;
Entra object IDs receive roles; OAuth application/client IDs configure OAuth.
A caller appearing in A/B audit logs does not mean that caller accessed Search.

Provisioners write a connection and publish a Toolbox version: use fresh names.
Hosted scripts require Foundry hosting; running them locally does not reproduce
agent/user context. Callers can invoke existing Active hosted versions without
redeploying. HTTP 200 alone is not success; consent, tool and session errors fail.

For the unchanged deployed lab, see [reproduction and evidence](./README.md).
Independent samples do not import or modify its implementation.
For all six native/custom optional upstream routes, see the workshop's
[evidence matrix](./workshop.md#six-path-evidence-matrix-historical-optional-upstream-apim-run).
That historical experiment uses different probe agents/Toolboxes from the direct
sample invocations described below: A passed, B lacked agent context, C native
failed user-token resolution, and C custom remained consent-blocked.
Hosted service snapshots are not runtime console logs, and a configured Search
target does not establish observed Search internal queries.

Offline validation from the repository root:

```powershell
python -m unittest discover -s . -p test_standalone_samples.py -v
python -m unittest test_custom_application_samples -v
python -m compileall -q .\samples
```

## Validated scenario code (2026-10-31)

The A/B custom application samples have separate signed-JWT, HTTP MCP and mocked
ARM/SDK contract tests in `test_custom_application_samples.py`; no billable
deployment or live custom token acquisition was performed for these additions.
The combined local run using the existing isolated scenario-test environment
completed 45 tests: 40 passed, five identity-inapplicable skips, no failures/errors.
The five new test methods exercise both A and B with cryptographic and HTTP
subcases, including delegated-token denial and application-principal allow/deny.
The pre-existing live evidence below refers to native A/B targets, not these
new custom application targets.

[Safe test evidence](./evidence/scenario-sample-tests.json) records 40 contract
tests (35 passed, five identity-inapplicable skips), sample syntax checks and six
cryptographic/HTTP MCP tests against the standalone custom server. Missing runtime
dependencies were restored only in an isolated validation virtual environment.

Each scenario's actual `invoke_hosted.py` completed against existing version-pinned
agents: `hosted-a` v2, `hosted-b` v3, `hosted-c` v3 and
`hosted-c-custom-mcp-oauth` v1. Returned demo markers and custom-server tool logs
were checked. No standalone hosted runtime was deployed.

The A/B/native-C provisioners also created isolated connections and Toolbox
versions through real ARM/SDK calls. Auth types, targets and connection references
were read back; only those test resources were deleted and their absence verified.
Custom OAuth provisioning was contract-tested only: no reusable client secret was
persisted, and no credentials or consent were created, rotated or repeated.
