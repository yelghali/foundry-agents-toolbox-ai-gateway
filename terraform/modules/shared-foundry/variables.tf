variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$", var.name))
    error_message = "Use a 3-64 character lowercase account/custom-subdomain name."
  }
}
variable "resource_group_id" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "projects" {
  type    = map(string)
  default = {}
  validation {
    condition     = length(distinct(values(var.projects))) == length(var.projects)
    error_message = "Each project must have a unique name within the shared account."
  }
}
variable "model_deployments" {
  type = map(object({
    model_name    = string
    model_version = string
    sku_name      = optional(string, "GlobalStandard")
    capacity      = optional(number, 10)
  }))
  default = {}
  validation {
    condition     = alltrue([for model in values(var.model_deployments) : model.capacity > 0 && floor(model.capacity) == model.capacity])
    error_message = "Model capacity must be a positive integer; quota and region support are checked by Azure."
  }
}
variable "private_network" {
  type = object({
    virtual_network_id         = string
    private_endpoint_subnet_id = string
    private_dns_zone_ids       = optional(map(string), {})
    create_dns_vnet_links      = optional(bool, true)
  })
  default = null
  validation {
    condition = var.private_network == null ? true : (
      can(regex("(?i)^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.Network/virtualNetworks/[^/]+$", var.private_network.virtual_network_id)) &&
      startswith(lower(var.private_network.private_endpoint_subnet_id), "${lower(var.private_network.virtual_network_id)}/subnets/")
    )
    error_message = "Private Link requires an existing VNet ID and a subnet belonging to that VNet."
  }
  validation {
    condition = var.private_network == null ? true : (
      length(var.private_network.private_dns_zone_ids) == 0 ||
      toset(keys(var.private_network.private_dns_zone_ids)) == toset([
        "privatelink.cognitiveservices.azure.com",
        "privatelink.openai.azure.com",
        "privatelink.services.ai.azure.com"
      ])
    )
    error_message = "Supply all three existing Foundry DNS zone IDs keyed by zone name, or none to create all three."
  }
  validation {
    condition = var.private_network == null ? true : alltrue([
      for name, id in var.private_network.private_dns_zone_ids :
      can(regex("(?i)^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.Network/privateDnsZones/", id)) &&
      endswith(lower(id), "/privatednszones/${name}")
    ])
    error_message = "Each reused DNS zone must be a full ARM resource ID matching its zone-name key."
  }
}
variable "tags" {
  type    = map(string)
  default = {}
}
