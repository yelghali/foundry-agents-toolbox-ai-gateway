"""Search index and local Foundry IQ source/KB definitions used by this lab."""

SEMANTIC_CONFIGURATION = "default-semantic-config"


def index_body(name: str) -> dict:
    return {
        "name": name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
        ],
        "semantic": {"configurations": [{
            "name": SEMANTIC_CONFIGURATION,
            "prioritizedFields": {"titleField": {"fieldName": "title"},
                                  "prioritizedContentFields": [{"fieldName": "content"}]},
        }]},
    }


def knowledge_source_body(name: str, index_name: str) -> dict:
    return {
        "name": name, "kind": "searchIndex",
        "searchIndexParameters": {
            "searchIndexName": index_name, "semanticConfigurationName": SEMANTIC_CONFIGURATION,
            "sourceDataFields": [{"name": "title"}, {"name": "content"}], "searchFields": [],
        },
    }


def knowledge_base_body(name: str, source_names: list[str], config: dict) -> dict:
    return {
        "name": name, "description": "Foundry agents, Toolbox and APIM identity showcase.",
        "knowledgeSources": [{"name": source} for source in source_names],
        "outputMode": "answerSynthesis", "retrievalReasoningEffort": {"kind": "low"},
        "models": [{
            "kind": "azureOpenAI", "azureOpenAIParameters": {
                "resourceUri": config["foundryOpenAIEndpoint"].rstrip("/"),
                "deploymentId": config["modelDeploymentName"], "modelName": "gpt-4o-mini",
            },
        }],
    }
