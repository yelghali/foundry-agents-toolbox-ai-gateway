data "azurerm_client_config" "current" {}

data "azapi_resource" "standard_apim" {
  count                  = var.standard_apim_resource_id == null ? 0 : 1
  type                   = "Microsoft.ApiManagement/service@2024-05-01"
  resource_id            = var.standard_apim_resource_id
  response_export_values = ["sku.name"]
  lifecycle {
    postcondition {
      condition     = self.output.sku.name == "StandardV2"
      error_message = "The optional legacy-policy bridge requires an existing StandardV2 service."
    }
  }
}

locals {
  labels          = toset(["a", "b", "c"])
  subscription_id = split("/", var.foundry_account_id)[2]
  suffix          = substr(md5(var.foundry_account_id), 0, 6)
  role_scope      = "/subscriptions/${local.subscription_id}/providers/Microsoft.Authorization/roleDefinitions"
}

resource "azurerm_search_service" "cohort" {
  for_each                      = local.labels
  name                          = "srch${substr(replace(var.foundry_account_name, "-", ""), 0, 32)}${each.key}${local.suffix}"
  resource_group_name           = var.resource_group_name
  location                      = var.search_location
  sku                           = "basic"
  replica_count                 = 1
  partition_count               = 1
  local_authentication_enabled  = false
  authentication_failure_mode   = "http403"
  public_network_access_enabled = true
  semantic_search_sku           = "free"
  identity { type = "SystemAssigned" }
  tags = merge(var.tags, { project = var.projects[each.key].name })
}

resource "azurerm_log_analytics_workspace" "cohort" {
  for_each            = local.labels
  name                = "log-${var.foundry_account_name}-${each.key}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = merge(var.tags, { project = var.projects[each.key].name })
}

resource "azurerm_application_insights" "cohort" {
  for_each            = local.labels
  name                = "appi-${var.foundry_account_name}-${each.key}"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.cohort[each.key].id
  application_type    = "web"
  tags                = merge(var.tags, { project = var.projects[each.key].name })
}

resource "azurerm_role_assignment" "project_user" {
  for_each           = local.labels
  scope              = var.projects[each.key].id
  role_definition_id = "${local.role_scope}/53ca6127-db72-4b80-b1b0-d745d6d5456d"
  principal_id       = var.deployer_object_id
}

resource "azurerm_role_assignment" "search_admin" {
  for_each           = local.labels
  scope              = azurerm_search_service.cohort[each.key].id
  role_definition_id = "${local.role_scope}/7ca78c08-252a-4471-8644-bb5ff32d4ba0"
  principal_id       = var.deployer_object_id
}

resource "azurerm_role_assignment" "search_writer" {
  for_each           = local.labels
  scope              = azurerm_search_service.cohort[each.key].id
  role_definition_id = "${local.role_scope}/8ebe5a00-799e-43f5-93ac-243d3dce84a7"
  principal_id       = var.deployer_object_id
}

resource "azurerm_role_assignment" "project_reader" {
  for_each                         = { a = var.projects["a"] }
  scope                            = azurerm_search_service.cohort[each.key].id
  role_definition_id               = "${local.role_scope}/1407120a-92aa-4202-b7e9-c0e197c71c8f"
  principal_id                     = each.value.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "search_planner_model" {
  for_each                         = local.labels
  scope                            = var.foundry_account_id
  role_definition_id               = "${local.role_scope}/a97b65f3-24c7-4388-baec-2e87135dc908"
  principal_id                     = azurerm_search_service.cohort[each.key].identity[0].principal_id
  skip_service_principal_aad_check = true
}
