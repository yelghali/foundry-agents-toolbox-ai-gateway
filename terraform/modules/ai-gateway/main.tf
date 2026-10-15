data "azapi_resource" "backend_subnet" {
  count                  = var.backend_subnet_id == null ? 0 : 1
  type                   = "Microsoft.Network/virtualNetworks/subnets@2024-05-01"
  resource_id            = var.backend_subnet_id
  response_export_values = ["properties.delegations"]
}

data "azurerm_virtual_network" "backend" {
  count               = var.backend_subnet_id == null ? 0 : 1
  name                = split("/", var.backend_subnet_id)[8]
  resource_group_name = split("/", var.backend_subnet_id)[4]
}

resource "terraform_data" "backend" {
  triggers_replace = var.backend_subnet_id
}

resource "azapi_resource" "gateway" {
  type      = "Microsoft.ApiManagement/aigateways@2026-09-01-preview"
  name      = var.name
  parent_id = var.resource_group_id
  location  = var.location
  tags      = var.tags
  identity { type = "SystemAssigned" }
  body = {
    sku = { name = "AIGateway" }
    properties = var.backend_subnet_id == null ? {} : {
      backend = { subnet = { id = var.backend_subnet_id } }
    }
  }
  # The dedicated preview RP schema is newer than the AzAPI schema bundle.
  schema_validation_enabled = false
  response_export_values    = ["identity.principalId", "properties.frontend.defaultHostname"]
  lifecycle {
    replace_triggered_by = [terraform_data.backend]
    precondition {
      condition = var.backend_subnet_id == null ? true : anytrue([
        for delegation in data.azapi_resource.backend_subnet[0].output.properties.delegations :
        delegation.properties.serviceName == "Microsoft.App/environments"
      ])
      error_message = "The pinned AI Gateway ARM API requires a dedicated subnet delegated to Microsoft.App/environments. Existing subnets are never modified by this module."
    }
    precondition {
      condition     = var.backend_subnet_id == null ? true : lower(data.azurerm_virtual_network.backend[0].location) == lower(var.location)
      error_message = "The gateway and delegated backend subnet's VNet must be in the same region."
    }
  }
}
