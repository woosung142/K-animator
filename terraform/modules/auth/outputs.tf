#----------------------------------------------------
# Database Outputs
#----------------------------------------------------
output "db_fqdn" {
  description = "The fully qualified domain name of the PostgreSQL Flexible Server."
  value       = azurerm_postgresql_flexible_server.auth_db.fqdn
  
}
#----------------------------------------------------
# Redis Outputs
#----------------------------------------------------
output "redis_hostname" {
  description = "The hostname of the Azure Cache for Redis instance."   
  value       = azurerm_redis_cache.auth_redis.hostname
}
output "redis_primary_key" {
  description = "The primary access key for the Azure Cache for Redis instance."
  value       = azurerm_redis_cache.auth_redis.primary_access_key
  sensitive   = true
}