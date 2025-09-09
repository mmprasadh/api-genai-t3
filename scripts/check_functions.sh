#!/usr/bin/env bash
set -euo pipefail
: "${RG:?}"; : "${FUNCAPP:?}"

echo "App state:"
az functionapp show -g "$RG" -n "$FUNCAPP" --query "{state:state, kind:kind, linuxFxVersion:siteConfig.linuxFxVersion}" -o json

echo "Key app settings:"
az functionapp config appsettings list -g "$RG" -n "$FUNCAPP" \
  --query "[?name=='AzureWebJobsStorage' || name=='KV_NAME' || name=='WEBSITE_RUN_FROM_PACKAGE' || name=='FUNCTIONS_WORKER_RUNTIME' || name=='FUNCTIONS_EXTENSION_VERSION'].[name,value]" -o table

echo "Listing functions with retries…"
for i in {1..12}; do
  if az functionapp function list -g "$RG" -n "$FUNCAPP" -o table; then
    exit 0
  fi
  echo "Attempt $i failed; waiting…"
  sleep 10
done
echo "Still unable to list functions."
exit 1
