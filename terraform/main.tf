resource "azurerm_resource_group" "lab" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

module "foundry" {
  source              = "./modules/shared-foundry"
  name                = var.foundry_name
  resource_group_id   = azurerm_resource_group.lab.id
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.location
  projects = merge(var.projects, var.enable_abc_lab ? {
    a = "abc-a"
    b = "abc-b"
    c = "abc-c"
  } : {})
  model_deployments = var.model_deployments
  private_network   = var.private_network
  tags              = var.tags
}

module "gateways" {
  for_each          = var.gateways
  source            = "./modules/ai-gateway"
  name              = each.key
  resource_group_id = azurerm_resource_group.lab.id
  location          = coalesce(each.value.location, var.location)
  backend_subnet_id = each.value.backend_subnet_id
  tags              = var.tags
}

resource "azurerm_role_assignment" "gateway_model_user" {
  for_each                         = var.gateways
  scope                            = module.foundry.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = module.gateways[each.key].principal_id
  skip_service_principal_aad_check = true
}

module "abc" {
  count                     = var.enable_abc_lab ? 1 : 0
  source                    = "./modules/abc-foundation"
  resource_group_name       = azurerm_resource_group.lab.name
  location                  = var.location
  search_location           = var.search_location
  foundry_account_id        = module.foundry.id
  foundry_account_name      = var.foundry_name
  projects                  = { for label in ["a", "b", "c"] : label => module.foundry.projects[label] }
  deployer_object_id        = var.deployer_object_id
  model_deployment_name     = var.abc_model_deployment_name
  standard_apim_resource_id = var.existing_standard_apim_resource_id
  tags                      = var.tags
}
