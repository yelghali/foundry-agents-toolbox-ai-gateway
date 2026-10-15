"""Publish an isolated native Search Toolbox source with explicit managed user authentication."""

import argparse

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AISearchIndexResource, AzureAISearchToolResource, AzureAISearchToolboxTool, MCPToolboxTool

import common as cm


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    config = cm.load_config()
    cohort = next(item for item in config["cohorts"] if item["label"] == "c")
    connection = cm.connection(
        config, cohort, "raw-c-native-user", cohort["searchEndpoint"],
        "UserEntraToken", category="CognitiveSearch",
    )
    project = AIProjectClient(endpoint=cohort["project"]["endpoint"], credential=cm.credential(config))
    version = project.toolboxes.create_version(name="cohort-tools-native-user", tools=[
        AzureAISearchToolboxTool(
            name="search_index_c",
            azure_ai_search=AzureAISearchToolResource(indexes=[
                AISearchIndexResource(project_connection_id=connection, index_name=cohort["indexName"],
                                      query_type="simple", top_k=1),
            ]),
        ),
        MCPToolboxTool(name="retrieve_kb_c", server_label="iq_c", server_url=cohort["kbEndpoint"],
                      project_connection_id=cohort["kbConnectionId"], require_approval="never"),
    ])
    project.toolboxes.update(name="cohort-tools-native-user", default_version=version.version)
    endpoint = cohort["project"]["endpoint"] + "/toolboxes/cohort-tools-native-user/mcp?api-version=v1"
    ingress = cm.connection(config, cohort, "abc-c-native-user-ingress", endpoint,
                            "AgenticIdentityToken", audience="https://ai.azure.com")
    cohort["nativeUserSearch"] = {
        "toolboxEndpoint": endpoint, "toolboxIngressConnectionId": ingress, "indexConnectionId": connection,
    }
    cm.save_config(config, "c")
    print("Published a separate native Search user-auth probe; no Search application roles were added.")


if __name__ == "__main__":
    main()
