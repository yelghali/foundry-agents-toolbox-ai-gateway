@description('Globally unique name for an optional new APIM instance. The lab can also reuse an existing Standard v2 service.')
param apimName string
param location string = resourceGroup().location
param publisherEmail string
param publisherName string

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: apimName
  location: location
  sku: { name: 'StandardV2', capacity: 1 }
  identity: { type: 'SystemAssigned' }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    publicNetworkAccess: 'Enabled'
  }
}

output apimResourceId string = apim.id
output apimSku string = apim.sku.name
