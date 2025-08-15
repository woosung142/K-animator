resource "azurerm_resource_group" "aks_rg" {
  name     = var.aks_cluster_resource_group_name
  location = var.location
}

resource "azurerm_kubernetes_cluster" "aks_cluster" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.aks_rg.location
  resource_group_name = azurerm_resource_group.aks_rg.name
  dns_prefix          = "${var.aks_cluster_name}-dns"

  default_node_pool {
    name           = "default"
    node_count     = 2
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

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }
}