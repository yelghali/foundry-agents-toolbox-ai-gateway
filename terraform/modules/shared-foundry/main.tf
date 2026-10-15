locals {
  private = var.private_network != null
  dns_names = toset([
    "privatelink.cognitiveservices.azure.com",
    "privatelink.openai.azure.com",
    "privatelink.services.ai.azure.com"
  ])
  existing_dns = local.private ? var.private_network.private_dns_zone_ids : {}
  dns_zone_ids = !local.private ? {} : length(local.existing_dns) > 0 ? local.existing_dns : {
    for name, zone in azurerm_private_dns_zone.foundry : name => zone.id
  }
}

data "azurerm_virtual_network" "private" {
  count               = local.private ? 1 : 0
  name                = split("/", var.private_network.virtual_network_id)[8]
  resource_group_name = split("/", var.private_network.virtual_network_id)[4]
}

resource "azapi_resource" "account" {
  type      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name      = var.name
  parent_id = var.resource_group_id
  location  = var.location
  tags      = var.tags
  identity { type = "SystemAssigned" }
  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = var.name
      disableLocalAuth       = true
      publicNetworkAccess    = local.private ? "Disabled" : "Enabled"
      networkAcls = {
        defaultAction       = local.private ? "Deny" : "Allow"
        ipRules             = []
        virtualNetworkRules = []
      }
    }
  }
  response_export_values = ["identity.principalId"]
}

resource "azapi_resource" "project" {
  for_each  = var.projects
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = each.value
  parent_id = azapi_resource.account.id
  location  = var.location
  tags      = var.tags
  identity { type = "SystemAssigned" }
  body                   = { properties = {} }
  response_export_values = ["identity.principalId"]
  depends_on             = [azapi_resource.model]
}

resource "azapi_resource" "model" {
  for_each  = var.model_deployments
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = each.key
  parent_id = azapi_resource.account.id
  body = {
    sku = { name = each.value.sku_name, capacity = each.value.capacity }
    properties = {
      model                = { format = "OpenAI", name = each.value.model_name, version = each.value.model_version }
      versionUpgradeOption = "NoAutoUpgrade"
    }
  }
}

resource "azurerm_private_dns_zone" "foundry" {
  for_each            = local.private && length(local.existing_dns) == 0 ? local.dns_names : toset([])
  name                = each.value
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "foundry" {
  for_each             = local.private ? (var.private_network.create_dns_vnet_links ? local.dns_names : toset([])) : toset([])
  name                 = "${var.name}-link"
  private_dns_zone_id  = local.dns_zone_ids[each.key]
  virtual_network_id   = var.private_network.virtual_network_id
  registration_enabled = false
  tags                 = var.tags
  depends_on           = [azurerm_private_dns_zone.foundry]
}

resource "azurerm_private_endpoint" "foundry" {
  count               = local.private ? 1 : 0
  name                = "${var.name}-pe"
  location            = data.azurerm_virtual_network.private[0].location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_network.private_endpoint_subnet_id
  tags                = var.tags
  private_service_connection {
    name                           = "${var.name}-account"
    private_connection_resource_id = azapi_resource.account.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "foundry"
    private_dns_zone_ids = values(local.dns_zone_ids)
  }
}
