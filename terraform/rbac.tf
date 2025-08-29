resource "kubectl_manifest" "csi_secret_creator_role" {
    yaml_body = <<-EOT
        apiVersion: rbac.authorization.k8s.io/v1
        kind: Role
        metadata:
            name: secret-creator
            namespace: loki
        rules:
        - apiGroups: [""]
          resources: ["secrets"]
          verbs: ["create", "get", "update", "patch"]
    EOT  
}

resource "kubectl_manifest" "csi_secret_creator_rolebinding" {
  yaml_body = <<-EOT
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: csi-secrets-creator-binding
      namespace: loki
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: Role
      name: secrets-creator
    subjects:
    - kind: ServiceAccount
      name: csi-secrets-store-provider-azure
      namespace: kube-system
  EOT
}