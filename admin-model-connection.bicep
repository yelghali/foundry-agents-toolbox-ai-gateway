targetScope = 'resourceGroup'

@description('Resource ID of the existing Foundry project that receives the Admin-connected model.')
param projectResourceId string

@description('OpenAI-compatible gateway base URL ending at /openai/v1.')
param gatewayModelsBaseUrl string

@secure()
@description('Gateway runtime key. It is stored only in the Foundry connection credential.')
param gatewayRuntimeKey string

@description('Connection prefix used by agents as <connectionName>/<modelName>.')
param connectionName string = 'ai-gateway'

@description('Exact gateway model alias sent in the request body. Dedicated AI Gateway routes by alias, not backend deployment name.')
param modelName string

@description('Model version shown in the Foundry Admin-connected models catalog.')
param modelVersion string

@description('Model format shown in the Foundry Admin-connected models catalog.')
param modelFormat string = 'OpenAI'

@allowed([
  'ModelGateway'
  'ApiManagement'
])
@description('Use ModelGateway for the dedicated AI Gateway tier; use ApiManagement for a classic APIM API.')
param connectionCategory string = 'ModelGateway'

@description('HTTP header carrying the gateway runtime or subscription key.')
param authHeaderName string = 'api-key'

@description('Whether every project under the Foundry account can discover the connection.')
param isSharedToAll bool = true

@description('Set true only when the gateway route contains deployments/{deploymentName}.')
param deploymentInPath bool = false

var accountName = split(projectResourceId, '/')[8]
var projectName = split(projectResourceId, '/')[10]
var staticModels = [
  {
    name: modelName
    properties: {
      model: {
        name: modelName
        version: modelVersion
        format: modelFormat
      }
    }
  }
]

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: account
  name: projectName
}

resource connection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: connectionName
  properties: {
    category: connectionCategory
    target: gatewayModelsBaseUrl
    authType: 'ApiKey'
    isSharedToAll: isSharedToAll
    credentials: {
      key: gatewayRuntimeKey
    }
    metadata: {
      models: string(staticModels)
      deploymentInPath: string(deploymentInPath)
      authHeaderName: authHeaderName
      authHeaderFormat: '{api_key}'
      customHeaders: '{}'
    }
  }
}

output connectionId string = connection.id
output connectionName string = connection.name
output modelReference string = '${connection.name}/${modelName}'
