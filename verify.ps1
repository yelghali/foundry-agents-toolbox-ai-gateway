[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    function Invoke-LabTest {
        param([Parameter(ValueFromRemainingArguments)][string[]]$Arguments)
        & python test_routes.py @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Live assertion failed: $($Arguments -join ' ')" }
    }
    foreach ($kind in @("raw", "iq")) {
        foreach ($agent in @("prompt-a", "hosted-a")) {
            Invoke-LabTest --cohort a --agent $agent --route apim --tool $kind
        }
        foreach ($agent in @("prompt-b", "hosted-b")) {
            Invoke-LabTest --cohort b --agent $agent --route data-gateway --tool $kind
        }
        Invoke-LabTest --cohort a --agent agent-ab-denied --tool $kind --expect-denied
        Invoke-LabTest --cohort b --agent agent-bc-denied --tool $kind --expect-denied
    }
    foreach ($agent in @("prompt-c", "hosted-c")) {
        Invoke-LabTest --cohort c --agent $agent --route user-ingress --tool iq
    }
    Invoke-LabTest --cohort a --agent a-orchestrator --route orchestrator --tool peer `
        --question "Use ask_agent_a to call prompt-a and retrieve the normal cohort A marker using its raw index tool."
    Invoke-LabTest --cohort a --agent a-orchestrator --route orchestrator --tool peer --expect-unsupported `
        --question "Use ask_agent_a to call hosted-a and report the actual backend outcome."
    Invoke-LabTest --cohort b --agent b-confidential --tool raw --confidential --request-store `
        --question "Use the raw index tool with search text exactly 'confidential test answer'. Return the actual answer. This question is the confidentiality audit for project B; do not add that sentence to the search text."
    & python verify_showcase.py --privacy --store-request --audits --gateway --user-ingress
    if ($LASTEXITCODE -ne 0) { throw "Telemetry verification failed. If ingestion is delayed, rerun the verifier after 2-5 minutes; do not treat this run as passed." }
}
finally {
    Pop-Location
}
