"""Isolated hosted SDK route; trusted caller context is forwarded by FoundryToolbox."""

import asyncio
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential


def create_agent():
    credential = DefaultAzureCredential()
    return Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            credential=credential,
        ),
        tools=FoundryToolbox(credential, name="observed", url=os.environ["TOOLBOX_ENDPOINT"]),
        instructions=(
            "Use exactly the requested tool and arguments. Return its actual result unchanged. "
            "Never invent a marker, authorization outcome or successful call. Report actual errors."
        ),
        default_options={"store": False},
    )


async def main():
    await ResponsesHostServer(create_agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
