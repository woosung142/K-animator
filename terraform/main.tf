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

    # 무중단 서비스
    upgrade_settings {  #새 노드 1개가 추가되어 총 4개가 된 상태에서 순차적으로 기존 노드를 교체
      max_surge = "10%"
    }
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
# Aks Cluster - GPU Node Pool
# ----------------------------------------------------
resource "azurerm_kubernetes_cluster_node_pool" "gpu_nodepool" {
  name =  "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks_cluster.id
  vm_size = "Standard_NV36ads_A10_v5"

  enable_auto_scaling = true # 자동 스케일링 활성화
  min_count = 0
  max_count = 2
  vnet_subnet_id = data.azurerm_subnet.existing_subnet.id
  mode = "User"

  node_taints = ["sku=gpu:NoSchedule"]

  tags = {
    Environment = "Production"
    PoolType    = "GPU"
  }
}
# ----------------------------------------------------
# PostgreSQL DNS Vnet Link
# ----------------------------------------------------
resource "azurerm_private_dns_zone" "pg_dns_zone" {
  name = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_kubernetes_cluster.aks_cluster.resource_group_name
}
resource "azurerm_private_dns_zone_virtual_network_link" "pg_dns_zone_link" {
  name                  = "pg-dns-zone-link"
  resource_group_name   = azurerm_kubernetes_cluster.aks_cluster.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.pg_dns_zone.name
  virtual_network_id    = data.azurerm_virtual_network.existing_vnet.id
}
# ----------------------------------------------------
# Redis DNS Vnet Link
# ----------------------------------------------------
resource "azurerm_private_dns_zone" "redis_dns_zone" {
  name = "privatelink.redis.cache.windows.net"
  resource_group_name = azurerm_kubernetes_cluster.aks_cluster.resource_group_name
}
resource "azurerm_private_dns_zone_virtual_network_link" "resis_dns_zone_link" {
  name                  = "redis-dns-zone-link"
  resource_group_name   = azurerm_kubernetes_cluster.aks_cluster.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.redis_dns_zone.name
  virtual_network_id    = data.azurerm_virtual_network.existing_vnet.id
  
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

  # 운영용 database 관련 변수 값
  private_dns_zone_id = azurerm_private_dns_zone.pg_dns_zone.id
  subnet_id      = azurerm_subnet.db_subnet.id
  aks_cluster_name         = azurerm_kubernetes_cluster.aks_cluster.name

  # 운영용 Redis 관련 변수 값
  pe_subnet_id = azurerm_subnet.pe_subnet.id
  redis_private_dns_zone_id = azurerm_private_dns_zone.redis_dns_zone.id

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

  # 개발용 database 관련 변수 값
  private_dns_zone_id = azurerm_private_dns_zone.pg_dns_zone.id
  subnet_id      = azurerm_subnet.db_subnet.id
  aks_cluster_name         = azurerm_kubernetes_cluster.aks_cluster.name

  # 개발용 Redis 관련 변수 값
  pe_subnet_id = azurerm_subnet.pe_subnet.id
  redis_private_dns_zone_id = azurerm_private_dns_zone.redis_dns_zone.id

  depends_on = [
    azurerm_role_assignment.terraform_user_kv_dev_admin   #Key Vault Secrets Officer 역할 할당이 완료된 후에 Key Vault Secrets User 역할 할당이 진행되도록 설정
  ]
}
# ----------------------------------------------------
# API Management module - API Gateway
# ----------------------------------------------------
module "api_gateway" {
  source = "./modules/api_gateway"

  location                = azurerm_resource_group.aks_rg.location
  resource_group_name     = azurerm_resource_group.aks_rg.name

  apim_name               = var.apim_name
  auth_url                = var.backend_auth_url
  model_api_url           = var.backend_model_api_url
  util_url                = var.backend_util_url
  gpt_url                 = var.backend_gpt_url
}
# ----------------------------------------------------
# SD Storage module
# ----------------------------------------------------
module "sd_storage" {
  source = "./modules/sd_storage"

  prefix                 = "kanimator"
  location                = azurerm_resource_group.aks_rg.location
  resource_group_name     = azurerm_resource_group.aks_rg.name
  tags                    = azurerm_kubernetes_cluster_node_pool.gpu_nodepool.tags
}
# ----------------------------------------------------
# frontdoor module
# ----------------------------------------------------
module "frontdoor" {
  source = "./modules/frontdoor"

  resource_group_name     = azurerm_resource_group.aks_rg.name

  prefix = "kanimatorprod"
  backend_host_name = "api.prtest.shop"
}