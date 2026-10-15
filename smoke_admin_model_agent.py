"""Create and invoke a prompt agent through a Foundry Admin-connected model."""

import argparse
import uuid

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import AzureCliCredential


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--model", default="aigw-admin-models/gpt-4o-mini")
    parser.add_argument("--agent-name", default="byom-aigw-smoke")
    parser.add_argument("--marker", default="BYOM_AIGW_READY")
    parser.add_argument("--correlation-id")
    args = parser.parse_args()
    correlation_id = args.correlation_id or f"byom-{uuid.uuid4()}"

    credential = AzureCliCredential(subscription=args.subscription_id, process_timeout=120)
    with AIProjectClient(endpoint=args.project_endpoint, credential=credential) as project:
        version = project.agents.create_version(
            agent_name=args.agent_name,
            definition=PromptAgentDefinition(
                model=args.model,
                instructions=(
                    "Follow the user's formatting instruction exactly. "
                    "Do not call tools or add explanatory text."
                ),
            ),
        )
        response = project.get_openai_client().responses.create(
            input=f"Reply with exactly this marker and nothing else: {args.marker}",
            store=False,
            extra_headers={"x-correlation-id": correlation_id},
            extra_body={
                "agent_reference": {
                    "name": args.agent_name,
                    "version": version.version,
                    "type": "agent_reference",
                }
            },
        )

    if args.marker not in response.output_text:
        raise RuntimeError("The Admin-connected model response did not contain the expected marker.")

    print(
        f"Admin-connected model smoke test passed: agent={args.agent_name}, "
        f"version={version.version}, response_id={response.id}, correlation_id={correlation_id}. "
        "Response content was validated but not printed."
    )


if __name__ == "__main__":
    main()
