param foundryAccountName string
param foundryResourceGroup string
param apimName string
param apimResourceGroup string
param foundryLocation string = 'eastus2'
param searchLocation string = 'swedencentral'
param deployerPrincipalId string
param modelDeployment string = 'gpt-4o-mini'

var labels = [ 'a', 'b', 'c' ]
var suffix = uniqueString(subscription().id, resourceGroup().id)
var contributorRole = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var dataContributorRole = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var readerRole = '1407120a-92aa-4202-b7e9-c0e197c71c8f'

resource apim 'Microsoft.ApiManagement/service@2024-05-01' existing = {
  name: apimName
  scope: resourceGroup(apimResourceGroup)
}

resource search 'Microsoft.Search/searchServices@2025-05-01' = [for label in labels: {
  name: 'srchabc${label}${suffix}'
  location: searchLocation
  identity: { type: 'SystemAssigned' }
  sku: { name: 'basic' }
  properties: {
    disableLocalAuth: true
    hostingMode: 'Default'
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: 'enabled'
    networkRuleSet: { ipRules: [] }
    semanticSearch: 'free'
  }
}]

module projectModule 'projects.bicep' = {
  name: 'abc-projects'
  scope: resourceGroup(foundryResourceGroup)
  params: {
    foundryAccountName: foundryAccountName
    location: foundryLocation
    deployerPrincipalId: deployerPrincipalId
    labels: labels
    searchPrincipalIds: [for (label, i) in labels: search[i].identity.principalId]
  }
}

resource admin 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (label, i) in labels: {
  scope: search[i]
  name: guid(search[i].id, deployerPrincipalId, contributorRole)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRole)
  }
}]

resource writer 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (label, i) in labels: {
  scope: search[i]
  name: guid(search[i].id, deployerPrincipalId, dataContributorRole)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', dataContributorRole)
  }
}]

resource projectReaders 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (label, i) in labels: if (label == 'a') {
  scope: search[i]
  name: guid(search[i].id, 'abc-project-${label}', readerRole)
  properties: {
    principalId: projectModule.outputs.details[i].principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', readerRole)
  }
}]

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = [for label in labels: {
  name: label == 'a' ? 'log-foundry-abc' : 'log-foundry-abc-${label}'
  location: foundryLocation
  tags: { project: 'abc-${label}' }
  properties: {
    retentionInDays: 30
    sku: { name: 'PerGB2018' }
  }
}]

resource insights 'Microsoft.Insights/components@2020-02-02' = [for (label, i) in labels: {
  name: label == 'a' ? 'appi-foundry-abc' : 'appi-foundry-abc-${label}'
  location: foundryLocation
  kind: 'web'
  tags: { project: 'abc-${label}' }
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace[i].id
    IngestionMode: 'LogAnalytics'
  }
}]

output subscriptionId string = subscription().subscriptionId
output tenantId string = subscription().tenantId
output foundryAccountName string = foundryAccountName
output apimResourceId string = apim.id
output apimSku string = apim.sku.name
output foundryOpenAIEndpoint string = 'https://${foundryAccountName}.openai.azure.com'
output modelDeploymentName string = modelDeployment
output workspaceId string = workspace[0].properties.customerId
output workspaceResourceId string = workspace[0].id
output appInsightsResourceId string = insights[0].id
output cohorts array = [for (label, i) in labels: {
  label: label
  project: projectModule.outputs.details[i]
  searchName: search[i].name
  searchId: search[i].id
  searchEndpoint: 'https://${search[i].name}.search.windows.net'
  indexName: 'index-${label}'
  knowledgeSourceName: 'ks-${label}'
  knowledgeBaseName: 'kb-${label}'
  identityMode: ['project', 'agent', 'user'][i]
  telemetry: {
    appInsightsResourceId: insights[i].id
    workspaceResourceId: workspace[i].id
    workspaceId: workspace[i].properties.customerId
  }
}]
