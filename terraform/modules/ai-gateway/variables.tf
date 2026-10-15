variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,22}[a-z0-9]$", var.name))
    error_message = "The dedicated AI Gateway schema requires a 3-24 character lowercase name."
  }
}
variable "resource_group_id" { type = string }
variable "location" {
  type = string
  validation {
    condition     = contains(["eastus2", "swedencentral"], lower(var.location))
    error_message = "The documented dedicated AI Gateway preview regions are eastus2 and swedencentral."
  }
}
variable "backend_subnet_id" {
  type        = string
  default     = null
  description = "Optional dedicated existing subnet for private backends. Pinned 2026-09-01-preview ARM schema requires Microsoft.App/environments delegation."
  validation {
    condition     = var.backend_subnet_id == null ? true : can(regex("(?i)^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.Network/virtualNetworks/[^/]+/subnets/[^/]+$", var.backend_subnet_id))
    error_message = "Use the full existing delegated backend subnet ARM ID."
  }
}
variable "tags" {
  type    = map(string)
  default = {}
}
