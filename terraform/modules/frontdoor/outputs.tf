output "endpoint_hostname" {
  description = "Front Door 엔드포인트의 기본 호스트 이름"
  value = azurerm_cdn_frontdoor_endpoint.main.host_name
}
output "endpoint_id" {
  description = "Front Door 엔드포인트의 ID"
  value = azurerm_cdn_frontdoor_endpoint.main.id
}
output "profile_id" {
  description = "Front Door 프로파일 iD"
  value = azurerm_cdn_frontdoor_profile.main.id
}
output "waf_policy_id" {
  description = "WAF 정책의 ID"
  value = azurerm_cdn_frontdoor_firewall_policy.k_animator_waf_policy.id
}