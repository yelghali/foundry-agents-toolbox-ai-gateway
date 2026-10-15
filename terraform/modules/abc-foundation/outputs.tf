output "config" {
  value = {
    subscriptionId        = local.subscription_id
    tenantId              = data.azurerm_client_config.current.tenant_id
    foundryAccountName    = var.foundry_account_name
    foundryOpenAIEndpoint = "https://${var.foundry_account_name}.openai.azure.com"
    modelDeploymentName   = var.model_deployment_name
    apimResourceId        = var.standard_apim_resource_id
    apimSku               = var.standard_apim_resource_id == null ? null : data.azapi_resource.standard_apim[0].output.sku.name
    cohorts = [for label in ["a", "b", "c"] : {
      label = label
      project = {
        name        = var.projects[label].name
        id          = var.projects[label].id
        principalId = var.projects[label].principal_id
        endpoint    = var.projects[label].endpoint
      }
      searchName          = azurerm_search_service.cohort[label].name
      searchId            = azurerm_search_service.cohort[label].id
      searchEndpoint      = "https://${azurerm_search_service.cohort[label].name}.search.windows.net"
      indexName           = "index-${label}"
      knowledgeSourceName = "ks-${label}"
      knowledgeBaseName   = "kb-${label}"
      identityMode        = { a = "project", b = "agent", c = "user" }[label]
      telemetry = {
        appInsightsResourceId = azurerm_application_insights.cohort[label].id
        workspaceResourceId   = azurerm_log_analytics_workspace.cohort[label].id
        workspaceId           = azurerm_log_analytics_workspace.cohort[label].workspace_id
      }
    }]
  }
}
