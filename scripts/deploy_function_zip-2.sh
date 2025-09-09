#!/usr/bin/env bash
set -euo pipefail
: "${RG:?}"; : "${FUNCAPP:?}"; : "${KV_NAME:?}"; : "${ST:?}"

# Build zip (must have host.json at root)
ZIP="$HOME/func-deploy.zip"; rm -f "$ZIP"
(cd api-spec-gen-func && zip -r "$ZIP" . -x ".venv/*" "__pycache__/*" "local.settings.json")

# Ensure KV_NAME is visible to the app
az functionapp config appsettings set -g "$RG" -n "$FUNCAPP" --settings KV_NAME="$KV_NAME" >/dev/null

# Primary: zip deploy
if az functionapp deployment source config-zip -g "$RG" -n "$FUNCAPP" --src "$ZIP"; then
  echo "Zip deploy succeeded."
else
  echo "Zip deploy failed; switching to Run-From-Package via Blob SAS…"
  CONTAINER=function-releases
  az storage container create --name $CONTAINER --account-name "$ST" >/dev/null || true
  KEY=$(az storage account keys list -g "$RG" -n "$ST" --query "[0].value" -o tsv)
  NAME="func-deploy-$(date +%s).zip"
  az storage blob upload --account-name "$ST" --account-key "$KEY" \
    --container-name $CONTAINER --name "$NAME" --file "$ZIP" --overwrite true >/dev/null
  EXP=$(date -u -d "+7 days" '+%Y-%m-%dT%H:%MZ' 2>/dev/null || python - <<'PY'
  import datetime
  print((datetime.datetime.utcnow()+datetime.timedelta(days=7)).strftime('%Y-%m-%dT%H:%MZ'))
  PY
  )
  SAS=$(az storage blob generate-sas --account-name "$ST" --account-key "$KEY" \
    --container-name $CONTAINER --name "$NAME" --permissions r --expiry "$EXP" -o tsv)
  URL="https://${ST}.blob.core.windows.net/${CONTAINER}/${NAME}?${SAS}"
  az functionapp config appsettings set -g "$RG" -n "$FUNCAPP" \
    --settings WEBSITE_RUN_FROM_PACKAGE="$URL" >/dev/null
fi

# Sync triggers (or restart as fallback)
az functionapp sync-function-triggers -g "$RG" -n "$FUNCAPP" >/dev/null 2>&1 || \
az functionapp restart -g "$RG" -n "$FUNCAPP"

# Print useful info
for FN in GenerateOpenApi GenerateDocsFromOpenApi; do
  echo "Function: $FN"
  FUNC_URL=$(az functionapp function show -g "$RG" -n "$FUNCAPP" --function-name "$FN" --query "invoke_url_template" -o tsv || echo "")
  KEY_JSON=$(az functionapp function keys list -g "$RG" -n "$FUNCAPP" --function-name "$FN" -o json || echo "{}")
  echo "Invoke URL: $FUNC_URL"
  # Key extraction via Python (robust)
  FUNC_CODE=$(python3 -c "import json; import sys; d=json.loads('''$KEY_JSON'''); print(d.get('default',''))")
  echo "Function code: $FUNC_CODE"
done



