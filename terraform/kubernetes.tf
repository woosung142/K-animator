resource "kubernetes_namespace" "loki" {
    metadata {
        name        = "loki"
    }
}

resource "kubectl_manifest" "loki_spc" {
  yaml_body = templatefile("${path.module}/../k8s/charts/Loki/secret-provider-class.yaml.tftpl", {
    client_id = azurerm_kubernetes_cluster.aks_cluster.kubelet_identity[0].client_id
    tenant_id = data.azurerm_client_config.current.tenant_id
  })

    depends_on = [
        kubernetes_namespace.loki,
        azurerm_role_assignment.aks_kubelet_kv_reader
    ]
}