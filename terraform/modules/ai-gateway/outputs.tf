output "id" { value = azapi_resource.gateway.id }
output "sku" { value = azapi_resource.gateway.body.sku.name }
output "principal_id" { value = azapi_resource.gateway.output.identity.principalId }
output "endpoint" {
  value = "https://${azapi_resource.gateway.output.properties.frontend.defaultHostname}"
}
