"""Direct hosted agent to Toolbox; hosting supplies caller context, no manual OBO."""

import asyncio
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential


async def main():
    credential = DefaultAzureCredential()
    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"], credential=credential,
        ),
        tools=FoundryToolbox(credential, name="custom_probe", url=os.environ["CUSTOM_TOOLBOX_ENDPOINT"]),
        instructions=(
            "Call probe_echo once with the exact experiment_id, message and count supplied by the user. "
            "Return the exact tool result. Never invent a marker or identity; report real tool errors."
        ),
        default_options={"store": False},
    )
    await ResponsesHostServer(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
