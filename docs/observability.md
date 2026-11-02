# Logs, identity evidence and confidential mode

Each project has its own App Insights component and Log Analytics workspace. Queries below use workspace table names; select the appropriate project's workspace.

## User-aware custom events

```kusto
AppEvents
| where TimeGenerated > ago(2h)
| where Name startswith "abc_"
| extend p=todynamic(Properties)
| project TimeGenerated, Name, Project=tostring(p["project"]),
    Agent=tostring(p.agent), UserOid=tostring(p.user_oid),
    Tool=tostring(p.tool), Phase=tostring(p.phase),
    Status=tostring(p.status), Url=tostring(p.observed_url),
    DataPrincipal=tostring(p.data_principal_oid)
| order by TimeGenerated desc
```

Hosted middleware records request/tool lifecycle metadata and trusted caller context. Native prompt agents cannot run that Python middleware: the driver records user-aware invocation events, while APIM and native Foundry traces provide additional evidence. Do not call driver audit a custom server-side prompt-agent hook.

## Which principal APIM actually sees

```kusto
AppTraces
| where TimeGenerated > ago(2h)
| extend p=todynamic(Properties)
| where tostring(p.mcp_server_id) startswith "abc-"
| project TimeGenerated, Message, Api=tostring(p.mcp_server_id),
    UserOid=tostring(p.user_oid),
    AgentOrDataPrincipal=tostring(p.data_principal_oid),
    PlatformPrincipal=tostring(p.platform_principal_oid),
    Kind=tostring(p.agent_kind), ClientRequestId=tostring(p.client_request_id),
    CallerContextHash=tostring(p.caller_context_hash),
    ObservedPath=tostring(p.observed_operation_path),
    Tool=tostring(p.mcp_tool_name), BackendStatus=tostring(p.backend_status)
```

- The optional upstream Toolbox gateway sees the **calling agent instance's platform app token**, including A. Its APIM-validated `oid` matches that instance, not the caller or project MI. APIM forwards this bearer unchanged; it performs no token exchange. Correlate its opaque caller-context hash with hosted user audit.
- B downstream data gateway sees the original agent Search token. Its actual raw Search path identifies `index-b`; its KB path identifies `kb-b`, not the internal source queries.
- C agent ingress sees and validates the initiating user's delegated platform token. It logs user `oid`, request ID and response status while Search user tokens stay on trusted first-party hops.
- Original gateway diagnostics record zero request/response body bytes and no authorization headers.
  The optional six `obs-20261031-*` upstream APIs are deliberately separate:
  they capture at most 8192 body bytes and no headers. Do not apply their body
  capture settings to original or confidential routes.

## Six optional upstream captures

The [workshop evidence matrix](../workshop.md#six-path-evidence-matrix-fresh-november-1-upstream-apim-replay)
separates APIM bodies, hosted service response snapshots and actual validated MCP
events for A/B/C native/custom. The persisted
[consolidated evidence](../evidence/observability-real-exchanges.json) records
configured destinations separately from observed destinations.

A native, A custom and the post-consent C custom replay passed this optional run.
Both B paths lack agent instance context; C native failed with `AADSTS500016`.
C custom's new success is the upstream APIM route, not the earlier direct-route success.
The six paths were invoked again on November 1, 2026 using existing pinned hosted
versions and fresh sessions, without redeploying or changing original defaults.
Each scenario now presents three stages: exact user prompt and actual hosted
response; generated MCP `tools/call` arguments or blocked `tools/list` discovery;
and observed MCP/runtime logs. Selected sanitized raw bodies and service snapshots
are folded; repeated all-exchange arrays, full hosted responses and runtime/MCP logs
are linked using JSON Pointers into retained local ignored evidence. Those links
are unavailable in a fresh public clone. The validator resolves the linked JSON
and checks the exact scenario/value instead of requiring repeated inline dumps.
Hosted response snapshots are **not runtime console logs**. The read-only
`collect_hosted_runtime_logs.py --config <ignored-config>` command queries the
last 300 console lines of each pinned hosted version. If that CLI stream is
unavailable, it uses the supported SDK session SSE stream, selecting only a
unique version/time-matched session and filtering lines to the invocation window.
Session identifiers remain memory-only. `--session-only` avoids retrying a known
unavailable CLI endpoint. `--scenario c-custom` refreshes only that runtime capture,
preserving the other five. `collect_mcp_exchanges.py --kind delegated --since <UTC>`
merges fresh delegated events while preserving application evidence.
Availability/correlation is recorded in
`evidence\observability-hosted-runtime.json`; uncorrelated errors are not
attributed to the new replay. Native Search internal queries and
fan-out remain `NOT_OBSERVED`; successful MCP responses through APIM are observed.
In the November 1 replay, the CLI container stream was unavailable, but the SDK
session stream returned time-correlated console lines for all six invocations.
Runtime logs alone do not turn blocked tool paths into successes.

Five selected invocations remain the **12:27 UTC November 1** captures.
Only C custom was replayed after consent: **13:09:39.229822–13:09:57.035724 UTC**,
experiment `f4fe017e-d8db-44a9-aa6c-36207d916e7c`.
Each workshop scenario now has a three-hop identity table and exact selected JWT
header/claim observations. Caller credentials are **decoded only, not locally
validated**; platform credentials are **APIM-validated**; A custom's correlated
application token and C custom's delegated claims are **MCP-validated**. Only available
`alg`, `kid`, issuer, audience,
tenant/principal/client IDs, scopes/roles, identity/version and validity times
are shown. Raw JWTs, signatures, keys and opaque token metadata are excluded.

A custom proves the downstream transition from the agent instance/platform
audience to the **project managed identity/custom API audience**. This is
platform-managed acquisition, not a traced internal JWT-bearer OBO grant.
A native's successful Search response does not expose its backend token:
configured project MI/Search audience remain **NOT_OBSERVED** token claims.
The blocked B/C-native paths likewise have no observed backend token. Missing `roles`
does not imply failure. Post-consent C custom now observes user `oid`
`c6982fed-3a65-46cb-a80f-d5093b79e3e4`, custom API `aud`
`c0135af3-d0d3-410f-a1ce-8f2470f5dd93`, `scp: access_as_user` and OAuth client
`azp: bd0cc73c-e7ec-4fb5-9b74-3c2fdc5b37af`. APIM-validated platform `oid`
`114281a8-d2fe-407c-a1cf-28461136d9af` is the calling agent instance, not that user.
The exact APIM `structuredContent` equals hosted `function_call_output`;
the UUID-correlated `custom_mcp_tool` console event matches its arguments and claims,
with a matching authentication event within the APIM request/response window.
This delegated server logs neither the full return nor JWT header/validity times:
do not synthesize those fields. Signature, issuer, audience, tenant and scope are
validated by the deployed MCP boundary; caller `oid` and configured OAuth `azp`
are checked during evidence compilation. This existing authorization-code/refresh
connection is not a traced JWT-bearer OBO grant.
Earlier direct C custom and pre-consent UUID captures remain separate; original B
direct and downstream-gateway results must also remain separately labelled.

For fresh telemetry, scope the query to the selected run's UTC start/end and
recorded APIM request ID rather than the entire project. Allow ingestion delay;
an expired or empty result is unavailable evidence, not proof of no execution.
Do not export Authorization, raw caller context, JWTs or consent URLs. The
historical UUID-named captures remain separate from the fresh selected run.
After collecting APIM/MCP/runtime logs, run `compile_observability_evidence.py`,
`update_observability_workshop.py` and `validate_observability_docs.py` to refresh
and verify exact embedded strings and linked JSON values. Never substitute expected/synthesized queries.

## Actual KB source activity

Non-confidential B direct REST IQ calls request `includeActivity:true`. They export observed source/count/time metadata:

```kusto
AppEvents
| where Name == "abc_source_activity"
| extend p=todynamic(Properties)
| project TimeGenerated, Agent=tostring(p.agent), UserOid=tostring(p.user_oid),
    Source=tostring(p.source), Count=tostring(p.count),
    ElapsedMs=tostring(p.elapsed_ms), QueryTime=tostring(p.query_time)
```

The full REST activity result and the metadata event are different surfaces. The event does not export every generated subquery. Configured source/index fields on a tool audit are labelled configured metadata, not inferred backend activity.

## Confidential agent

The corrected `b-confidential`:

1. Uses the direct Azure OpenAI v1 model endpoint instead of the Foundry project model endpoint whose server-side spans initially captured answers despite container flags.
2. Uses its agent identity for Search B and a model-only account-level grant for inference.
3. Disables MAF/OTel sensitive content recording and writes an explicit question audit, not an answer/tool-result audit.
4. Forces outer `store:false`, overrides a caller's `store:true`, removes the Playground conversation reference, and sends model calls with storage disabled. Explicit previous-response chaining remains unsupported because responses aren't stored.
5. Was tested with an answer canary returned to the caller but absent across six telemetry tables after the corrected test start. Hosted response GET returned 404; a generic project GET returning 403 was **not** treated as storage proof.

Question audit:

```kusto
AppEvents
| where Name == "abc_agent_request"
| extend p=todynamic(Properties)
| where tostring(p.agent) == "b-confidential" and tostring(p.phase) == "started"
| project TimeGenerated, UserOid=tostring(p.user_oid),
    Session=tostring(p.session_id), Question=tostring(p.question)
```

`verify_showcase.py --privacy --store-request` uses the confidential test evidence's start time. It checks question presence and scans `AppEvents`, `AppTraces`, `AppRequests`, `AppDependencies`, `AppExceptions` and `AppGenAIContent`, including property bags.

**This is not a guarantee that answers are never retained anywhere.** Questions are deliberately stored and can themselves be sensitive. The synthetic answer fixture remains in Search. Historical experimental traces were not deleted. Provider processing, internal retention and abuse-monitoring controls are separate; no shared account policy was altered. See [Microsoft's privacy guidance](https://learn.microsoft.com/azure/foundry/responsible-ai/openai/data-privacy).
