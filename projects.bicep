param foundryAccountName string
param location string
param deployerPrincipalId string
param labels array
param searchPrincipalIds array

var userRole = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var modelRole = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource projects 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = [for label in labels: {
  parent: foundry
  name: 'abc-${label}'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {}
}]

resource users 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (label, i) in labels: {
  name: guid(projects[i].id, deployerPrincipalId, userRole)
  scope: projects[i]
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', userRole)
  }
}]

resource planners 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (label, i) in labels: {
  name: guid(foundry.id, 'abc-search-${label}', modelRole)
  scope: foundry
  properties: {
    principalId: searchPrincipalIds[i]
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', modelRole)
  }
}]

output details array = [for (label, i) in labels: {
  label: label
  name: projects[i].name
  id: projects[i].id
  principalId: projects[i].identity.principalId
  endpoint: 'https://${foundry.name}.services.ai.azure.com/api/projects/${projects[i].name}'
}]
