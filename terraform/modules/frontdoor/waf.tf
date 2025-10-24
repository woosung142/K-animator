resource "azurerm_cdn_frontdoor_firewall_policy" "k_animator_waf_policy" {
  name                = "${var.prefix}wafpolicy"
  resource_group_name = var.resource_group_name
  sku_name = azurerm_cdn_frontdoor_profile.main.sku_name
  enabled             = true
  mode                = "Prevention" 
  custom_block_response_status_code = 403
  custom_block_response_body = "PGh0bWw+CiAgPGhlYWQ+PHRpdGxlPjQwMyDsoJHqt7wg6rGw67aA65CoPC90aXRsZT48L2hlYWQ+CiAgPGJvZHkgc3R5bGU9ImZvbnQtZmFtaWx5OkFyaWFsOyB0ZXh0LWFsaWduOmNlbnRlcjsgcGFkZGluZzo0MHB4OyI+CiAgICA8aDEgc3R5bGU9ImNvbG9yOiNlNzRjM2M7Ij40MDMgLSDsoJHqt7zsnbQg6rGw67aA65CY7JeI7Iq164uI64ukPC9oMT4KICAgIDxwPuydtCDsmpTssq3snYAg67Cp7ZmU67K9KFdBRinsl5Ag7J2Y7ZW0IOywqOuLqOuQmOyXiOyKteuLiOuLpC48L3A+CiAgICA8cD7smKTtg5DsnLzroZwg7YyQ64uo65CY66m0IOq0gOumrOyekOyXkOqyjCDrrLjsnZjtlbTso7zshLjsmpQuPC9wPgogIDwvYm9keT4KPC9odG1sPg=="

  custom_rule {
    name       = "BlockPrivateIPs"
    enabled    = true
    priority   = 1
    type       = "MatchRule"
    action     = "Block"

    match_condition {
      match_variable     = "RemoteAddr"
      operator           = "IPMatch"
      negation_condition = false
      match_values       = ["10.0.0.0/8", "192.168.0.0/16"]
    }
  }
}
resource "azurerm_cdn_frontdoor_security_policy" "main" {
  name                     = "${var.prefix}-security-policy"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.k_animator_waf_policy.id
      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.main.id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}