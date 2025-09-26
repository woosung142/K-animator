data "azurerm_virtual_network" "existing_vnet" {
  name                = var.existing_vnet_name
  resource_group_name = var.existing_vnet_resource_group_name
}

data "azurerm_subnet" "existing_subnet" {
  name                 = var.existing_subnet_name
  virtual_network_name = data.azurerm_virtual_network.existing_vnet.name
  resource_group_name  = data.azurerm_virtual_network.existing_vnet.resource_group_name
}
# ----------------------------------------------------
# DB용 서브넷 (PostgreSQL Flexible Server 전용 서브넷)
# ----------------------------------------------------
resource "azurerm_subnet" "db_subnet" {
  name                 = "db-subnet"
  resource_group_name  = data.azurerm_virtual_network.existing_vnet.resource_group_name
  virtual_network_name = data.azurerm_virtual_network.existing_vnet.name
  address_prefixes     = ["10.12.2.0/24"]

# PostgreSQL DB 서브넷 위임
  delegation {
    name = "postgresql-delegation"
    
    service_delegation {
    name = "Microsoft.DBforPostgreSQL/flexibleServers"
    actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }  
  }
}
# ----------------------------------------------------
# Redis 서브넷 (Azure Cache for Redis 서브넷)
# ----------------------------------------------------
resource "azurerm_subnet" "pe_subnet" {
  name = "pe-subnet"
  resource_group_name = data.azurerm_virtual_network.existing_vnet.resource_group_name
  virtual_network_name = data.azurerm_virtual_network.existing_vnet.name
  address_prefixes = ["10.12.3.0/24"]

  private_endpoint_network_policies = "Disabled"
}
# ----------------------------------------------------
# 기존 vnet 정보 조회 (user16)
# ----------------------------------------------------
data "azurerm_virtual_network" "vm_vnet" {
  name = var.vm_vnet_name
  resource_group_name = var.vm_vnet_resource_group_name
}
# ----------------------------------------------------
# vnet peering (DB/Redis <-> vm)
# ----------------------------------------------------
# aks -> vm 연결
resource "azurerm_virtual_network_peering" "aks_to_vm" {
  name = "peering-to-${data.azurerm_virtual_network.vm_vnet.name}"
  resource_group_name = data.azurerm_virtual_network.existing_vnet.resource_group_name
  virtual_network_name = data.azurerm_virtual_network.existing_vnet.name
  remote_virtual_network_id = data.azurerm_virtual_network.vm_vnet.id

  allow_virtual_network_access = true
  allow_forwarded_traffic = true
  allow_gateway_transit = false
  use_remote_gateways = false
}

# vm -> aks 연결
resource "azurerm_virtual_network_peering" "vm_to_aks" {
  name = "peering-to-${data.azurerm_virtual_network.existing_vnet.name}"
  resource_group_name = data.azurerm_virtual_network.vm_vnet.resource_group_name
  virtual_network_name = data.azurerm_virtual_network.vm_vnet.name
  remote_virtual_network_id = data.azurerm_virtual_network.existing_vnet.id

  allow_virtual_network_access = true
  allow_forwarded_traffic = true
  allow_gateway_transit = false
  use_remote_gateways = false
}