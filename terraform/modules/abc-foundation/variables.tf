variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "search_location" {
  type    = string
  default = "swedencentral"
}
variable "foundry_account_id" { type = string }
variable "foundry_account_name" { type = string }
variable "projects" {
  type = map(object({
    id           = string
    name         = string
    principal_id = string
    endpoint     = string
  }))
  validation {
    condition     = toset(keys(var.projects)) == toset(["a", "b", "c"])
    error_message = "Provide exactly projects a, b and c, usually from shared-foundry.projects."
  }
}
variable "deployer_object_id" {
  type     = string
  nullable = false
}
variable "model_deployment_name" {
  type    = string
  default = "gpt-4o-mini"
}
variable "standard_apim_resource_id" {
  type    = string
  default = null
}
variable "tags" {
  type    = map(string)
  default = {}
}
