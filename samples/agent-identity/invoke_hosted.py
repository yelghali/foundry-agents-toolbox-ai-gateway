"""Call an existing hosted agent, pin its session, and fail on HTTP/tool errors."""

import json
import os
import re
from urllib.parse import quote

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import VersionRefIndicator
from azure.identity import AzureCliCredential


def main():
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
    agent_name = os.environ["AGENT_NAME"]
    version = os.environ["AGENT_VERSION"]
    question = os.environ["QUESTION"]
    credential = AzureCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
    token = credential.get_token("https://ai.azure.com/.default").token
    with AIProjectClient(endpoint=endpoint, credential=credential) as project:
        session = project.agents.create_session(
            agent_name=agent_name, version_indicator=VersionRefIndicator(agent_version=version),
        )
        response = requests.post(
            endpoint + f"/agents/{quote(agent_name, safe='')}/endpoint/protocols/openai/responses?api-version=v1",
            headers={"Authorization": "Bearer " + token},
            json={"input": question, "stream": False, "store": False,
                  "agent_session_id": session.agent_session_id}, timeout=600,
        )
        response.raise_for_status()
        result = response.json()
        pinned = project.agents.get_session(agent_name=agent_name, session_id=session.agent_session_id)
        if (pinned.version_indicator.agent_version != version
                or result.get("agent_session_id") != session.agent_session_id):
            raise RuntimeError("Response/session did not bind to the requested hosted agent version")
    # Consent URLs carry opaque state. Surface the error without exporting that state.
    error_text = re.sub(
        r"https://[A-Za-z0-9.-]+\.consent\.azure-(?:apim|apihub)\.net/[^\s\"<>]+",
        "<consent-link-redacted>", json.dumps(result),
    )
    if result.get("error") or result.get("status") != "completed":
        raise RuntimeError("Agent response failed or requires consent: " + error_text)
    for item in result.get("output", []):
        if item.get("type") in ("oauth_consent_request", "mcp_approval_request"):
            raise RuntimeError("Complete tool consent/approval in Foundry, then retry: " + error_text)
        if (item.get("error") or item.get("is_error") or item.get("isError")
                or item.get("status") in ("failed", "incomplete", "cancelled")):
            raise RuntimeError("Tool failed: " + error_text)
        output = item.get("output")
        if isinstance(output, dict) and (output.get("error") or output.get("isError")):
            raise RuntimeError("Tool failed: " + error_text)
        if isinstance(output, str):
            if output.startswith("Error:"):
                raise RuntimeError("Tool failed: " + error_text)
            try:
                payload = json.loads(output)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and (payload.get("error") or payload.get("isError")):
                raise RuntimeError("Tool failed: " + error_text)
    expected = os.environ.get("EXPECTED_TEXT")
    if expected and expected not in json.dumps(result):
        raise RuntimeError("Completed response did not contain EXPECTED_TEXT")
    # Responses can contain confidential content: use nonsensitive demo input only.
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
