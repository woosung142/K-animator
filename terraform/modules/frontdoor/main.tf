resource "azurerm_cdn_frontdoor_profile" "main" {
  name = "${var.prefix}-fd-profile"
  resource_group_name = var.resource_group_name
  sku_name = "Standard_AzureFrontDoor"
}
resource "azurerm_cdn_frontdoor_endpoint" "main" {
  name                     = "${var.prefix}-fd-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
}

resource "azurerm_cdn_frontdoor_origin_group" "main" {
  name                     = "${var.prefix}-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  session_affinity_enabled = true # 사용자가 동일한 백엔드와 계속 통신하도록 설정

  health_probe {
    path                = "/health" # APIM의 기본 상태 검사 경로
    protocol            = "Https"
    interval_in_seconds = 100
  }
  load_balancing {
    additional_latency_in_milliseconds = 0
    sample_size                        = 16
    successful_samples_required        = 3
  }
}

resource "azurerm_cdn_frontdoor_origin" "apim" {
  name                          = "${var.prefix}-apim-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  enabled                       = true

  certificate_name_check_enabled = true

  # 백엔드 APIM 게이트웨이와 연결되는 가장 중요한 부분
  host_name                     = var.backend_host_name
  http_port                     = 80
  https_port                    = 443
  origin_host_header            = var.backend_host_name # 백엔드로 원본 호스트 헤더를 전달
  priority           = 1
  weight             = 1
}
resource "azurerm_cdn_frontdoor_custom_domain" "main" {
  name = "${var.prefix}-custom-domain"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  host_name = "fd.prtest.shop"

  tls {
    certificate_type    = "ManagedCertificate" # Azure 관리형 무료 인증서
    minimum_tls_version = "TLS12"
  }
}

# 퍼블릭 엔드포인트와 원본 그룹을 연결합니다.
resource "azurerm_cdn_frontdoor_route" "main" {
  name                          = "${var.prefix}-default-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.apim.id]

  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.main.id]
  
  supported_protocols           = ["Http", "Https"]
  patterns_to_match             = ["/*"]
  forwarding_protocol           = "HttpsOnly" # 모든 트래픽을 HTTPS로만 전달
  https_redirect_enabled        = true
}