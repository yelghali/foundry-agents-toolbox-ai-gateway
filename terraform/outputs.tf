output "foundry" {
  value = {
    id                    = module.foundry.id
    project_endpoints     = module.foundry.projects
    model_deployments     = { for name, deployment in var.model_deployments : name => deployment.model_name }
    openai_endpoint       = module.foundry.openai_endpoint
    public_network_access = module.foundry.public_network_access
    private_endpoint_id   = module.foundry.private_endpoint_id
  }
}

output "gateways" {
  value = { for name, gateway in module.gateways : name => {
    id                     = gateway.id
    sku                    = gateway.sku
    endpoint               = gateway.endpoint
    models                 = gateway.models_endpoint
    models_openai_base_url = gateway.models_openai_base_url
    toolservers            = gateway.toolservers_endpoint
    principal_id           = gateway.principal_id
  } }
}

output "gateway_onboarding" {
  description = "Nonsecret handoff for the supported portal onboarding and optional post-deploy verifier. Preview runtime keys are gateway-scoped and are never output."
  value = { for name, gateway in module.gateways : name => {
    gateway_resource_id    = gateway.id
    gateway_endpoint       = gateway.endpoint
    models_endpoint        = gateway.models_endpoint
    models_openai_base_url = gateway.models_openai_base_url
    toolservers_endpoint   = gateway.toolservers_endpoint
    foundry_resource_id    = module.foundry.id
    model_deployments      = keys(var.model_deployments)
    backend_identity = {
      type               = "SystemAssigned"
      principal_id       = gateway.principal_id
      required_role      = "Foundry User"
      role_definition_id = "53ca6127-db72-4b80-b1b0-d745d6d5456d"
    }
    asset_configuration = "Portal workflow: import Foundry models, assign exact model aliases, publish MCP servers, create a runtime key, and configure telemetry before test traffic."
    admin_connected_model = {
      template           = "../admin-model-connection.bicep"
      category           = "ModelGateway"
      gateway_base_url   = gateway.models_openai_base_url
      model_aliases      = keys(var.model_deployments)
      agent_model_format = "<connection-name>/<gateway-model-alias>"
    }
    runtime_key_scope = "All published models and tools in this gateway during preview; per-asset scoping is unavailable."
  } }
}

output "abc_config" {
  description = "Nonsecret foundation configuration for the Python provisioner. Export with export_config.ps1; AI Gateway and StandardV2 runtime paths are explicitly different."
  value       = var.enable_abc_lab ? module.abc[0].config : null
}
