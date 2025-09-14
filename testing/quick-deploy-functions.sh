#!/bin/bash
# testing/quick-deploy-functions.sh
set -euo pipefail

echo "🚀 Quick Deploy Functions for Testing"

# Source environment if it exists
if [ -f .env.testing ]; then
    source .env.testing
    echo "✅ Loaded testing environment"
else
    echo "❌ No testing environment found. Run ./testing/setup-testing-environment.sh first"
    exit 1
fi

# Verify prerequisites
echo "🔍 Checking prerequisites..."
command -v az >/dev/null 2>&1 || { echo "❌ Azure CLI required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.9+ required"; exit 1; }

# Ensure logged in to Azure
if ! az account show >/dev/null 2>&1; then
    echo "🔐 Azure login required"
    az login --use-device-code
    az account set --subscription "$SUB"
fi

# Create resource group
echo "🏗️ Creating resource group: $RG"
az group create -n "$RG" -l "$LOC" >/dev/null

# Create Key Vault
echo "🔐 Creating Key Vault: $KV"
az keyvault create -g "$RG" -n "$KV" -l "$LOC" >/dev/null 2>&1 || true

# Create Azure OpenAI
echo "🤖 Creating Azure OpenAI: $AOAI_NAME"
az cognitiveservices account create -g "$RG" -n "$AOAI_NAME" -l "$LOC" \
  --kind OpenAI --sku S0 >/dev/null 2>&1 || true

# Create Storage Account
echo "💾 Creating Storage Account: $ST"
az storage account create -g "$RG" -n "$ST" -l "$LOC" --sku Standard_LRS >/dev/null 2>&1 || true

# Create Function App
echo "⚡ Creating Function App: $FUNCAPP"
az functionapp create -g "$RG" -n "$FUNCAPP" --storage-account "$ST" \
  --consumption-plan-location "$LOC" --os-type Linux --runtime python \
  --functions-version 4 >/dev/null 2>&1 || true

# Deploy GPT-4o model
echo "🚀 Deploying GPT-4o model..."
az cognitiveservices account deployment create \
  -g "$RG" -n "$AOAI_NAME" --deployment-name "gpt4o-test" \
  --model-format OpenAI --model-name "gpt-4o" --model-version "2024-08-06" \
  --sku-name "Standard" --sku-capacity 10 >/dev/null 2>&1 || true

# Configure Key Vault secrets
echo "🔑 Setting up Key Vault secrets..."
az keyvault secret set --vault-name "$KV" --name AZURE-OPENAI-ENDPOINT \
  --value "https://$AOAI_NAME.openai.azure.com/" >/dev/null
az keyvault secret set --vault-name "$KV" --name AZURE-OPENAI-DEPLOYMENT \
  --value "gpt4o-test" >/dev/null
az keyvault secret set --vault-name "$KV" --name AZURE-OPENAI-API-KEY \
  --value "$(az cognitiveservices account keys list -g $RG -n $AOAI_NAME --query key1 -o tsv)" >/dev/null

# Configure Function App identity and permissions
echo "🔐 Configuring Function App permissions..."
az functionapp identity assign -g "$RG" -n "$FUNCAPP" >/dev/null
FUNC_PRINCIPAL_ID=$(az functionapp identity show -g "$RG" -n "$FUNCAPP" --query principalId -o tsv)
KV_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)

az role assignment create --role "Key Vault Secrets User" \
  --assignee-object-id "$FUNC_PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --scope "$KV_ID" >/dev/null

# Configure Function App settings
CONN=$(az storage account show-connection-string -g "$RG" -n "$ST" --query connectionString -o tsv)
az functionapp config appsettings set -g "$RG" -n "$FUNCAPP" --settings \
  "AzureWebJobsStorage=$CONN" "KV_NAME=$KV" >/dev/null

# Deploy function code
echo "📦 Deploying function code..."
ZIP="/tmp/func-test-deploy.zip"
rm -f "$ZIP"
(cd api-spec-gen-func && zip -r "$ZIP" . -x ".venv/*" "__pycache__/*" "local.settings.json")

az functionapp deployment source config-zip -g "$RG" -n "$FUNCAPP" --src "$ZIP" >/dev/null

echo "⏳ Waiting for deployment to complete..."
sleep 45

# Get function URLs and codes
echo "📡 Retrieving function endpoints..."
GEN_URL=$(az functionapp function show -g "$RG" -n "$FUNCAPP" \
  --function-name GenerateOpenApi --query "invoke_url_template" -o tsv)
GEN_CODE=$(az functionapp function keys list -g "$RG" -n "$FUNCAPP" \
  --function-name GenerateOpenApi --query "default" -o tsv)

DOCS_URL=$(az functionapp function show -g "$RG" -n "$FUNCAPP" \
  --function-name GenerateDocsFromOpenApi --query "invoke_url_template" -o tsv)
DOCS_CODE=$(az functionapp function keys list -g "$RG" -n "$FUNCAPP" \
  --function-name GenerateDocsFromOpenApi --query "default" -o tsv)

# Save endpoints
mkdir -p testing
cat > testing/.endpoints <<EOF
export GEN_FUNC_URL="$GEN_URL"
export GEN_FUNC_CODE="$GEN_CODE"
export DOCS_FUNC_URL="$DOCS_URL"
export DOCS_FUNC_CODE="$DOCS_CODE"
EOF

echo "✅ Quick deployment complete!"
echo "📋 Function endpoints saved to testing/.endpoints"
echo ""
echo "🔗 Function URLs:"
echo "   GenerateOpenApi: $GEN_URL"
echo "   GenerateDocsFromOpenApi: $DOCS_URL"
echo ""
echo "Next steps:"
echo "   1. Install 42Crunch CLI: npm install -g @42crunch/api-security-audit"
echo "   2. Test functions: ./testing/test-functions.sh"
echo "   3. Run Use Case 1: ./scripts/use-case-1-complete.sh"