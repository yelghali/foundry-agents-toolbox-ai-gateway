output "id" { value = azapi_resource.account.id }
output "principal_id" { value = azapi_resource.account.output.identity.principalId }
output "openai_endpoint" { value = "https://${var.name}.openai.azure.com" }
output "public_network_access" { value = azapi_resource.account.body.properties.publicNetworkAccess }
output "private_endpoint_id" { value = one(azurerm_private_endpoint.foundry[*].id) }
output "projects" {
  value = { for key, project in azapi_resource.project : key => {
    id           = project.id
    name         = var.projects[key]
    principal_id = project.output.identity.principalId
    endpoint     = "https://${var.name}.services.ai.azure.com/api/projects/${var.projects[key]}"
  } }
}
