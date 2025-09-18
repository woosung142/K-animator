# ----------------------------------------------------
# Aks Cluster
# ----------------------------------------------------
resource "azurerm_resource_group" "aks_rg" {
  name     = var.aks_cluster_resource_group_name
  location = var.location
}

resource "azurerm_kubernetes_cluster" "aks_cluster" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.aks_rg.location
  resource_group_name = azurerm_resource_group.aks_rg.name
  dns_prefix          = "${var.aks_cluster_name}-dns"

  oidc_issuer_enabled = true
  workload_identity_enabled = true

  default_node_pool {
    name           = "default"
    enable_auto_scaling = true  # 자동 스케일링 활성화
    min_count     = 1
    max_count     = 3
    vm_size        = "Standard_D2as_v5"
    vnet_subnet_id = data.azurerm_subnet.existing_subnet.id
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }

  tags = {
    Environment = "Production"
    Project     = "Webtoon-Generator-New" # 새로운 프로젝트임을 명시
  }
}
# ----------------------------------------------------
# Loki module
# ----------------------------------------------------
module "loki_stack" {
  source = "./modules/loki"

  aks_oidc_issuer_url     = azurerm_kubernetes_cluster.aks_cluster.oidc_issuer_url
  location                = azurerm_resource_group.aks_rg.location
  resource_group_name     = azurerm_resource_group.aks_rg.name

  storage_account_name    = var.storage_account_name
  storage_container_name  = var.storage_container_name
  
}
# ----------------------------------------------------
# Key Vault - prod
# ----------------------------------------------------
module "auth_stack_prod" {
  source = "./modules/auth"

  aks_oidc_issuer_url     = azurerm_kubernetes_cluster.aks_cluster.oidc_issuer_url
  location                = azurerm_resource_group.aks_rg.location
  resource_group_name     = azurerm_resource_group.aks_rg.name

  key_vault_id            = azurerm_key_vault.prod.id
  
  # 운영용 key vault 시크릿
  k8s_namespace            = "default"
  k8s_service_account_name = "auth-sa-prod"

  depends_on = [
    azurerm_role_assignment.terraform_user_kv_prod_admin  #Key Vault Secrets Officer 역할 할당이 완료된 후에 Key Vault Secrets User 역할 할당이 진행되도록 설정
  ]
}
# ----------------------------------------------------
# Key Vault - dev
# ----------------------------------------------------
module "auth_stack" {
  source = "./modules/auth"

  aks_oidc_issuer_url     = azurerm_kubernetes_cluster.aks_cluster.oidc_issuer_url
  location                = azurerm_resource_group.aks_rg.location
  resource_group_name     = azurerm_resource_group.aks_rg.name

  key_vault_id            = azurerm_key_vault.dev.id
  
  # 개발용 key vault 시크릿
  k8s_namespace            = "development"
  k8s_service_account_name = "auth-sa-dev"

  depends_on = [
    azurerm_role_assignment.terraform_user_kv_dev_admin   #Key Vault Secrets Officer 역할 할당이 완료된 후에 Key Vault Secrets User 역할 할당이 진행되도록 설정
  ]
}