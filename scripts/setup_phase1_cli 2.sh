#!/usr/bin/env bash
set -euo pipefail

# Login guard (Cloud Shell sometimes lacks a token)
if ! az account show >/dev/null 2>&1; then
  echo "No Azure session; starting device-code login..."
  az login --use-device-code >/dev/null
fi

: "${SUB:?}"; : "${LOC:?}"; : "${RG:?}"; : "${KV:?}"; : "${AOAI_NAME:?}"; : "${ST:?}"; : "${PLAN:?}"; : "${FUNCAPP:?}"; : "${APIM:?}"

az account set --subscription "$SUB"

# Provider registrations (idempotent)
for rp in Microsoft.ApiManagement Microsoft.KeyVault Microsoft.Storage Microsoft.Web Microsoft.CognitiveServices; do
  az provider register --namespace "$rp" --wait >/dev/null
done

echo "Creating resource group: $RG"
az group create -n "$RG" -l "$LOC" >/dev/null

echo "Creating Key Vault: $KV"
if ! az keyvault show -g "$RG" -n "$KV" >/dev/null 2>&1; then
  az keyvault create -g "$RG" -n "$KV" -l "$LOC" >/dev/null
fi

echo "Creating Azure OpenAI resource: $AOAI_NAME"
# Create OR restore OR purge-create to avoid soft-delete conflicts
if ! az cognitiveservices account create -g "$RG" -n "$AOAI_NAME" -l "$LOC" --kind OpenAI --sku S0 >/dev/null 2>&1; then
  if ! az cognitiveservices account create -g "$RG" -n "$AOAI_NAME" -l "$LOC" --kind OpenAI --sku S0 --restore true >/dev/null 2>&1; then
    az cognitiveservices account purge --location "$LOC" --name "$AOAI_NAME" || true
    az cognitiveservices account create -g "$RG" -n "$AOAI_NAME" -l "$LOC" --kind OpenAI --sku S0 >/dev/null
  fi
fi

echo "Creating Storage account: $ST"
az storage account show -g "$RG" -n "$ST" >/dev/null 2>&1 || az storage account create -g "$RG" -n "$ST" -l "$LOC" --sku Standard_LRS >/dev/null

echo "Creating Linux Function App: $FUNCAPP"
# Ensure Linux Python Consumption
if az functionapp show -g "$RG" -n "$FUNCAPP" >/dev/null 2>&1; then
  KIND=$(az functionapp show -g "$RG" -n "$FUNCAPP" --query kind -o tsv)
  if [[ "$KIND" != *linux* ]]; then
    az functionapp delete -g "$RG" -n "$FUNCAPP"
  fi
fi
if ! az functionapp show -g "$RG" -n "$FUNCAPP" >/dev/null 2>&1; then
  az functionapp create -g "$RG" -n "$FUNCAPP" \
    --storage-account "$ST" --consumption-plan-location "$LOC" \
    --os-type Linux --runtime python --functions-version 4 >/dev/null
fi

# Baseline app settings
CONN=$(az storage account show-connection-string -g "$RG" -n "$ST" --query connectionString -o tsv)
az functionapp config appsettings set -g "$RG" -n "$FUNCAPP" --settings \
  AzureWebJobsStorage="$CONN" FUNCTIONS_WORKER_RUNTIME=python FUNCTIONS_EXTENSION_VERSION="~4" KV_NAME="$KV" >/dev/null

# Assign managed identity and grant Key Vault secrets read based on permission model
az functionapp identity assign -g "$RG" -n "$FUNCAPP" >/dev/null || true
FUNC_MI_PRINCIPAL_ID=$(az functionapp identity show -g "$RG" -n "$FUNCAPP" --query principalId -o tsv)
IS_RBAC=$(az keyvault show -g "$RG" -n "$KV" --query "properties.enableRbacAuthorization" -o tsv)

if [ "$IS_RBAC" = "true" ]; then
  echo "Key Vault is RBAC-enabled; assigning Key Vault Secrets User to Function identity"
  KV_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)
  az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee-object-id "$FUNC_MI_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --scope "$KV_ID" >/dev/null || true
else
  echo "Key Vault uses access policies; adding secret get/list policy"
  az keyvault set-policy -n "$KV" --object-id "$FUNC_MI_PRINCIPAL_ID" --secret-permissions get list >/dev/null
fi

echo "Creating APIM (Developer SKU): $APIM"
az apim show -g "$RG" -n "$APIM" >/dev/null 2>&1 || az apim create -g "$RG" -n "$APIM" --publisher-email you@example.com --publisher-name "You" --sku-name Developer >/dev/null

echo "✅ Provisioned resources."




  
  








  







  





  
    
    
  








  
  
    
  


  
    
    





  







  
  
  
    
    
    
    

  
  






