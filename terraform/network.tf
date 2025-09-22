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