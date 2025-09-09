#!/usr/bin/env bash
set -euo pipefail
: "${RG:?}"; : "${FUNCAPP:?}"; : "${KV:?}"
FUNC_MI_PRINCIPAL_ID=$(az functionapp identity show -g "$RG" -n "$FUNCAPP" --query principalId -o tsv)
KV_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)
az role assignment create --role "Key Vault Secrets User" \
  --assignee-object-id "$FUNC_MI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "$KV_ID"
echo "Granted Key Vault Secrets User to $FUNCAPP managed identity."
