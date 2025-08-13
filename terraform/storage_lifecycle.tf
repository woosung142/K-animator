resource "azurerm_storage_management_policy" "loki_archive_policy" {
    storage_account_id = azurerm_storage_account.Loki.id

    rule {
        name    = "archive-old-loki-logs"
        enabled = true

        filters {
            blob_types = ["blockBlob"]
        }

        actions {
            base_blob {
                tier_to_archive_after_days_since_modification_greater_than = 30
                delete_after_days_since_modification_greater_than = 365
            }
        }
    }
}