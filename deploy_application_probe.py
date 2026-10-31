"""Deploy a separate strict application-token server; never edits C's OAuth server."""

import argparse
import json
import subprocess
from pathlib import Path

import requests
from azure.ai.projects import AIProjectClient

import common as cm
from replay_observability import ROOT, STATE, now, safe, write

NAME = "obs-application-mcp-20261031"
IMAGE = "observability-application-mcp:20261031-v2"


def az(*arguments, cwd=ROOT):
    result = subprocess.run(
        ["az.cmd", *arguments, "-o", "json"], cwd=cwd, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    if result.returncode:
        raise RuntimeError(safe(result.stderr[-3000:]))
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--custom-config", type=Path, required=True)
    parser.add_argument("--action", choices=("build", "deploy", "allowlist", "check"), required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    custom = json.loads(args.custom_config.read_text(encoding="utf-8-sig"))
    group, registry, identity = custom["resourceGroup"], custom["registry"], custom["identityId"]
    if args.action == "build":
        result = az("acr", "build", "-r", registry, "-t", IMAGE, "-f", ".\\Dockerfile",
                    ".", "--no-logs", cwd=ROOT / "samples" / "project-identity")
        write(ROOT / "evidence" / "application-probe-build.json", {
            "runId": result["runId"], "status": result["status"], "time": now(),
        })
        return
    principals = [next(x for x in config["cohorts"] if x["label"] == "a")["project"]["principalId"]]
    if STATE.exists():
        state = json.loads(STATE.read_text())
        record = state["scenarios"].get("b-custom")
        if record:
            cohort = next(x for x in config["cohorts"] if x["label"] == "b")
            project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
            agent = project.agents.get_version(agent_name=record["agent"], agent_version=record["version"])
            instance = agent.instance_identity or project.agents.get(agent_name=record["agent"]).instance_identity
            principals.append(instance.principal_id)
    variables = [
        "AZURE_TENANT_ID=" + config["tenantId"],
        "CUSTOM_MCP_AUDIENCE=" + custom["apiAppId"],
        "CUSTOM_MCP_EXPECTED_PRINCIPAL_IDS=" + ",".join(principals),
    ]
    if args.action == "deploy":
        original = az("containerapp", "show", "-g", group, "-n", custom["containerApp"])
        result = az(
            "containerapp", "create", "-g", group, "-n", NAME,
            "--environment", original["properties"]["managedEnvironmentId"],
            "--image", registry + ".azurecr.io/" + IMAGE,
            "--user-assigned", identity, "--registry-server", registry + ".azurecr.io",
            "--registry-identity", identity, "--ingress", "external",
            "--target-port", "8000", "--transport", "auto", "--min-replicas", "1",
            "--max-replicas", "1", "--cpu", "0.5", "--memory", "1Gi",
            "--env-vars", *variables,
        )
    elif args.action == "allowlist":
        result = az("containerapp", "update", "-g", group, "-n", NAME,
                    "--image", registry + ".azurecr.io/" + IMAGE, "--set-env-vars", *variables)
    else:
        result = az("containerapp", "show", "-g", group, "-n", NAME)
    endpoint = "https://" + result["properties"]["configuration"]["ingress"]["fqdn"]
    evidence = {
        "time": now(), "resourceId": result["id"], "image": registry + ".azurecr.io/" + IMAGE,
        "endpoint": endpoint + "/mcp", "expectedApplicationPrincipalIds": principals,
        "audience": custom["apiAppId"], "existingOAuthServerModified": False,
    }
    if args.action == "check":
        evidence["httpProbes"] = []
        for method, path in (("GET", "/healthz"), ("POST", "/mcp")):
            try:
                response = requests.request(
                    method, endpoint + path, timeout=30,
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"} if method == "POST" else None,
                )
                evidence["httpProbes"].append({
                    "method": method, "path": path, "status": response.status_code,
                    "response": response.text,
                })
            except requests.RequestException as error:
                evidence["httpProbes"].append({"method": method, "error": type(error).__name__})
    write(ROOT / "evidence" / ("application-probe-" + args.action + ".json"), evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
