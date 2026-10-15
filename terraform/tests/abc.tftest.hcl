mock_provider "azapi" {
  mock_data "azapi_resource" {
    defaults = { output = { sku = { name = "StandardV2" } } }
  }
}
mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = { tenant_id = "11111111-1111-1111-1111-111111111111" }
  }
}

variables {
  resource_group_name  = "lab"
  location             = "eastus2"
  foundry_account_id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/lab/providers/Microsoft.CognitiveServices/accounts/example-foundry"
  foundry_account_name = "example-foundry"
  deployer_object_id   = "22222222-2222-2222-2222-222222222222"
  projects = {
    a = {
      id           = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/lab/providers/Microsoft.CognitiveServices/accounts/example-foundry/projects/abc-a"
      name         = "abc-a"
      principal_id = "33333333-3333-3333-3333-333333333333"
      endpoint     = "https://example-foundry.services.ai.azure.com/api/projects/abc-a"
    }
    b = {
      id           = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/lab/providers/Microsoft.CognitiveServices/accounts/example-foundry/projects/abc-b"
      name         = "abc-b"
      principal_id = "44444444-4444-4444-4444-444444444444"
      endpoint     = "https://example-foundry.services.ai.azure.com/api/projects/abc-b"
    }
    c = {
      id           = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/lab/providers/Microsoft.CognitiveServices/accounts/example-foundry/projects/abc-c"
      name         = "abc-c"
      principal_id = "55555555-5555-5555-5555-555555555555"
      endpoint     = "https://example-foundry.services.ai.azure.com/api/projects/abc-c"
    }
  }
}

run "three_cohorts_only_a_project_reader" {
  command = plan
  module { source = "./modules/abc-foundation" }
  assert {
    condition     = length(azurerm_search_service.cohort) == 3 && length(azurerm_application_insights.cohort) == 3 && length(azurerm_log_analytics_workspace.cohort) == 3
    error_message = "The ABC foundation requires three isolated Search and telemetry pairs."
  }
  assert {
    condition     = keys(azurerm_role_assignment.project_reader) == ["a"]
    error_message = "Never grant B/C project identities data-reader access."
  }
  assert {
    condition     = alltrue([for search in values(azurerm_search_service.cohort) : !search.local_authentication_enabled])
    error_message = "Search must remain keyless."
  }
  assert {
    condition     = output.config.apimResourceId == null && output.config.cohorts[2].identityMode == "user"
    error_message = "The no-classic-APIM foundation must preserve C user auth and not invent an APIM service ID."
  }
}

run "explicit_existing_standard_bridge" {
  command = plan
  module { source = "./modules/abc-foundation" }
  variables {
    standard_apim_resource_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/gateway/providers/Microsoft.ApiManagement/service/existing-standard"
  }
  assert {
    condition     = output.config.apimSku == "StandardV2"
    error_message = "The bridge must verify the existing service's actual SKU."
  }
}

run "reject_nonstandard_legacy_bridge" {
  command = plan
  module { source = "./modules/abc-foundation" }
  variables {
    standard_apim_resource_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/gateway/providers/Microsoft.ApiManagement/service/existing-other"
  }
  override_data {
    target = data.azapi_resource.standard_apim[0]
    values = { output = { sku = { name = "Developer" } } }
  }
  expect_failures = [data.azapi_resource.standard_apim]
}
