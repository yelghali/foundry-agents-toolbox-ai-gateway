variable "subscription_id" {
  type        = string
  description = "Subscription for the new resources and existing VNet/subnets."
}

variable "resource_group_name" {
  type        = string
  description = "New resource group managed by this state."
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "foundry_name" {
  type        = string
  description = "Globally unique shared Foundry account name and custom subdomain."
}

variable "projects" {
  type        = map(string)
  default     = {}
  description = "Project key -> project name. With enable_abc_lab, a/b/c are added automatically."
}

variable "model_deployments" {
  type = map(object({
    model_name    = string
    model_version = string
    sku_name      = optional(string, "GlobalStandard")
    capacity      = optional(number, 10)
  }))
  default     = {}
  description = "Optional OpenAI deployments; empty means no model quota consumed by Terraform."
}

variable "private_network" {
  type = object({
    virtual_network_id         = string
    private_endpoint_subnet_id = string
    private_dns_zone_ids       = optional(map(string), {})
    create_dns_vnet_links      = optional(bool, true)
  })
  default     = null
  description = "Existing VNet/subnet for Foundry Private Link. Setting this disables public Foundry data-plane access."
}

variable "gateways" {
  type = map(object({
    location          = optional(string)
    backend_subnet_id = optional(string)
  }))
  default     = {}
  description = "New dedicated AIGateway resources, keyed by globally unique 3-24 character name. No StandardV2 gateway is created."
  validation {
    condition = var.private_network == null ? true : alltrue([
      for gateway in values(var.gateways) :
      gateway.backend_subnet_id == null ? false :
      startswith(lower(gateway.backend_subnet_id), "${lower(var.private_network.virtual_network_id)}/subnets/") &&
      lower(gateway.backend_subnet_id) != lower(var.private_network.private_endpoint_subnet_id)
    ])
    error_message = "With private Foundry, each gateway requires a separate delegated backend subnet in the same existing VNet; never reuse the private-endpoint subnet."
  }
}

variable "enable_abc_lab" {
  type        = bool
  default     = false
  description = "Add three Search services, telemetry pairs, and the original A/B/C foundation. Does not publish gateway tools or agents."
  validation {
    condition     = !var.enable_abc_lab || var.private_network == null
    error_message = "The ABC Search/telemetry foundation is a public-endpoint lab. Use Foundry-only private mode, or separately design private Search/Monitor and hosted-agent egress."
  }
}

variable "deployer_object_id" {
  type        = string
  default     = null
  description = "Object ID of the user/SP running the optional ABC data-plane provisioner."
  validation {
    condition     = !var.enable_abc_lab || var.deployer_object_id != null
    error_message = "The ABC lab requires an explicit deployer_object_id for its project/Search grants."
  }
}

variable "search_location" {
  type    = string
  default = "swedencentral"
}

variable "abc_model_deployment_name" {
  type    = string
  default = "gpt-4o-mini"
  validation {
    condition     = !var.enable_abc_lab || try(var.model_deployments[var.abc_model_deployment_name].model_name == "gpt-4o-mini", false)
    error_message = "The ABC IQ fixtures require an explicitly configured gpt-4o-mini deployment with the matching abc_model_deployment_name."
  }
}

variable "existing_standard_apim_resource_id" {
  type        = string
  default     = null
  description = "Optional existing StandardV2 APIM for the original XML/MCP policies. Dedicated AIGateway IDs are deliberately not accepted."
  validation {
    condition = var.existing_standard_apim_resource_id == null ? true : can(regex(
      "(?i)^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.ApiManagement/service/[^/]+$",
      var.existing_standard_apim_resource_id
    ))
    error_message = "Use an existing Microsoft.ApiManagement/service ID, not an aigateways ID. Its actual SKU must be StandardV2."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
