output "id" { value = azapi_resource.gateway.id }
output "sku" { value = azapi_resource.gateway.body.sku.name }
output "principal_id" { value = azapi_resource.gateway.output.identity.principalId }
output "hostname" {
  value = azapi_resource.gateway.output.properties.frontend.defaultHostname
}
output "endpoint" {
  value = "https://${azapi_resource.gateway.output.properties.frontend.defaultHostname}"
}
output "models_endpoint" {
  value = "https://${azapi_resource.gateway.output.properties.frontend.defaultHostname}/default/models"
}
output "models_openai_base_url" {
  value = "https://${azapi_resource.gateway.output.properties.frontend.defaultHostname}/default/models/openai/v1"
}
output "toolservers_endpoint" {
  value = "https://${azapi_resource.gateway.output.properties.frontend.defaultHostname}/default/toolservers"
}
