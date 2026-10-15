output "foundry" {
  value = {
    id                    = module.foundry.id
    project_endpoints     = module.foundry.projects
    openai_endpoint       = module.foundry.openai_endpoint
    public_network_access = module.foundry.public_network_access
    private_endpoint_id   = module.foundry.private_endpoint_id
  }
}

output "gateways" {
  value = { for name, gateway in module.gateways : name => {
    id           = gateway.id
    sku          = gateway.sku
    endpoint     = gateway.endpoint
    principal_id = gateway.principal_id
  } }
}

output "abc_config" {
  description = "Nonsecret foundation configuration for the Python provisioner. Export with export_config.ps1; AI Gateway and StandardV2 runtime paths are explicitly different."
  value       = var.enable_abc_lab ? module.abc[0].config : null
}
