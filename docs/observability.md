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

- A upstream Toolbox gateway sees the platform/project token. Correlate its opaque caller-context hash with hosted user audit; the token's `oid` is not automatically a human.
- B downstream data gateway sees the original agent Search token. Its actual raw Search path identifies `index-b`; its KB path identifies `kb-b`, not the internal source queries.
- C agent ingress sees and validates the initiating user's delegated platform token. It logs user `oid`, request ID and response status while Search user tokens stay on trusted first-party hops.
- Gateway diagnostics record zero request/response body bytes and no authorization headers.

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
