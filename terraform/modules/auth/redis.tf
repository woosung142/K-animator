resource "azurerm_redis_cache" "auth_redis" {
    name                = "redis-${var.aks_cluster_name}-${var.k8s_namespace}"
    location            = var.location
    resource_group_name = var.resource_group_name
    capacity            = 0     # C0 등급 250MB (개발용) 운영시 C1 등급 이상으로 변경 고려
    family              = "C"
    sku_name            = "Basic"  # 운영시 "Standard"으로 변경 고려  
    minimum_tls_version = "1.2"
    non_ssl_port_enabled = false   # 암호화되지 않은 평문 통신을 허용하지 않겠다는 거임
    
    public_network_access_enabled = false  # 퍼블릭 액세스 비활성화
    redis_configuration{}
}

# ----------------------------------------------------
# Redis 프라이빗 엔드포인트 생성
# ----------------------------------------------------
resource "azurerm_private_endpoint" "redis_pe" {
  name = "pe-redis-${var.aks_cluster_name}-${var.k8s_namespace}"
  location = var.location
  resource_group_name = var.resource_group_name
  subnet_id = var.pe_subnet_id

  private_dns_zone_group {
    name = "default"
    private_dns_zone_ids = [var.redis_private_dns_zone_id]
  }

  private_service_connection {
    name = "psc-redis-${var.aks_cluster_name}-${var.k8s_namespace}"
    is_manual_connection = false
    private_connection_resource_id = azurerm_redis_cache.auth_redis.id
    subresource_names = ["redisCache"]
  }
}