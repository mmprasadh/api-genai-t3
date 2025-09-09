#!/usr/bin/env bash
set -euo pipefail
: "${RG:?}"; : "${AOAI_NAME:?}"; : "${KV:?}"
DEPLOY=${1:-gpt4o-api}
MODEL=${2:-gpt-4o}
VERSION=${3:-"2024-08-06"}
SKU=${4:-Standard}
echo "Deploying model '$MODEL' version '$VERSION' as '$DEPLOY'…"
az cognitiveservices account deployment create \
  -g "$RG" -n "$AOAI_NAME" \
  --deployment-name "$DEPLOY" \
  --model-format OpenAI \
  --model-name "$MODEL" \
  --model-version "$VERSION" \
  --sku-name "$SKU" --sku-capacity 30
echo "Writing AZURE-OPENAI-DEPLOYMENT=$DEPLOY to Key Vault $KV"
az keyvault secret set --vault-name "$KV" --name AZURE-OPENAI-DEPLOYMENT --value "$DEPLOY" >/dev/null
echo "Done."
