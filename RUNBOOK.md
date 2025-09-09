# Runbook (Beginner‑friendly)

> ✅ **Where to run what**
> | Task | Where |
> |---|---|
> | Provision Azure + deploy Functions (Part 1) | **Azure Cloud Shell (Bash)** |
> | Generate spec/docs via Functions (curl) | **Cloud Shell** or local terminal |
> | MCP Orchestrator (required) | **Your laptop** |
> | Full CI (Spectral, 42Crunch, Auto‑Fix, API Center, Blob publish) | **Azure DevOps pipeline** |

---

## Part 0 — One‑time: sign in & select subscription (Cloud Shell)
```bash
az account clear || true
az login --use-device-code
az account list -o table
export SUB="<your-subscription-guid>"
az account set --subscription "$SUB"
```

---

## Part 1 — Provision & Deploy Functions (Cloud Shell)

### 1.1 Unzip and set variables
```bash
unzip api-spec-poc-orchestrated-v5.4.3-fullfat-rev2.zip
cd api-spec-poc-orchestrated-v5.4.3-fullfat-rev2

# === customize these 3 ===
export SUB="<subscription-guid>"
export LOC="eastus2"                # pick a supported region for your models
export SUFFIX=$RANDOM$RANDOM        # uniqueness

# === names derived from SUFFIX ===
export RG="GenAI-APILifecycle-RG"
export KV="genai-apilifecycle-kv-$SUFFIX"
export AOAI_NAME="genai-apilifecycle-aoai-$SUFFIX"
export ST="stapispec$SUFFIX"
export PLAN="plan-api-spec-poc-$SUFFIX"
export FUNCAPP="func-api-spec-poc-$SUFFIX"
export APIM="apim-api-spec-poc-$SUFFIX"
export API_PATH="procurement"
export API_ID="procurement-api"
export KV_NAME=$KV
```

### 1.2 Provision resources (RBAC‑aware, restore/purge‑aware)
```bash
chmod +x scripts/setup_phase1_cli.sh
bash scripts/setup_phase1_cli.sh
```

If you see **“Function app created but not active until content is published”**, that’s normal.

### 1.3 Deploy model (optional helper)
If you haven’t deployed a model on your Azure OpenAI resource:
```bash
chmod +x scripts/aoai_deploy_model.sh
bash scripts/aoai_deploy_model.sh gpt4o-api gpt-4o "2024-08-06"
# writes AZURE-OPENAI-DEPLOYMENT secret into Key Vault for you
```

### 1.4 Add secrets to Key Vault
```bash
# Azure OpenAI (example)
az keyvault secret set --vault-name $KV --name AZURE-OPENAI-ENDPOINT   --value "https://$AOAI_NAME.openai.azure.com/"
az keyvault secret set --vault-name $KV --name AZURE-OPENAI-DEPLOYMENT --value "gpt4o-api"
az keyvault secret set --vault-name $KV --name AZURE-OPENAI-API-KEY    --value "$(az cognitiveservices account keys list -g $RG -n $AOAI_NAME --query key1 -o tsv)"
```

> **Key Vault is RBAC?** This repo *automatically* assigns **Key Vault Secrets User** to the Function’s identity. If you need to re‑grant: `bash scripts/kv_rbac_grant.sh`.

### 1.5 Deploy the Functions code (Run‑From‑Package fallback built‑in)
```bash
chmod +x scripts/deploy_function_zip.sh
bash scripts/deploy_function_zip.sh
```

The script prints **Invoke URL** and **function key** for both functions. Save them.

### 1.6 Health check (retries, correct queries)
```bash
chmod +x scripts/check_functions.sh
bash scripts/check_functions.sh
```

### 1.7 Persist your environment for tomorrow
```bash
bash scripts/env_persist.sh  # creates ./env.sh with your current variables
# Next day: source env.sh to restore env
```

---

## Part 2 — Generate OpenAPI, Import to APIM, Generate Docs

> **Prereqs if you are running on the next day**  
> 1) Re‑authenticate: `az login --use-device-code && az account set --subscription "$SUB"`  
> 2) Restore variables: `source env.sh` (created in Part 1.7). If you lost it, re‑export vars exactly as in Part 1.1.  
> 3) Confirm Functions are live: `bash scripts/check_functions.sh`.

### 2.1 Generate OpenAPI from a prompt (via Function)
```bash
FUNC_URL=$(az functionapp function show -g "$RG" -n "$FUNCAPP" --function-name GenerateOpenApi --query "invoke_url_template" -o tsv)
FUNC_CODE=$(az functionapp function keys list -g "$RG" -n "$FUNCAPP" --function-name GenerateOpenApi --query "default" -o tsv)

read -r -d '' PROMPT <<'EOF'
Design a Construction Procurement API (Vendor, Material, PurchaseOrder+items, Delivery).
CRUD for each; approve/cancel for PurchaseOrder; pagination, filtering; error schema.
OpenAPI 3.0.3 YAML only (no commentary); include examples.
EOF

curl -s -X POST "${FUNC_URL}?code=${FUNC_CODE}"   -H "Content-Type: application/json"   -d "{"use_azure_openai": true, "prompt_override": ${PROMPT@Q} }" | tee api-spec-gen/openapi.yaml
```

### 2.2 Import into APIM
```bash
az apim api import --resource-group $RG --service-name $APIM   --path $API_PATH --api-id $API_ID   --specification-format OpenApi --specification-path ./api-spec-gen/openapi.yaml
```

### 2.3 Generate developer docs (HTML locally / Function also supports MD/HTML)
```bash
bash scripts/generate_docs_local.sh
# outputs: docs/docs.md and docs/docs.html
```

> **CI/CD path**: commit/push and run the Azure DevOps pipeline to execute **Spectral → 42Crunch → Auto‑Fix → Re‑check → Import → API Center → publish docs to Blob (SAS URL).**

---

## MCP Orchestrator (required)
On your laptop:
```bash
cd mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export RG="$RG"
export APIM="$APIM"
export API_PATH="$API_PATH"
export API_ID="$API_ID"
export FUNC_URL="<GenerateOpenApi URL>"
export FUNC_CODE="<code>"
export DOCS_FUNC_URL="<GenerateDocs URL>"
export DOCS_FUNC_CODE="<code>"

python orchestrator_server.py
# Use your MCP client to call: generate_openapi, validate_openapi, import_to_apim, generate_docs_md/html
```

---

## Troubleshooting quickies
- **400 Bad Request** on `function list` → run `scripts/deploy_function_zip.sh` (falls back to Run‑From‑Package) and `scripts/check_functions.sh`.
- **KV RBAC error** → run `scripts/kv_rbac_grant.sh`.
- **AOAI model SKU not supported in region** → deploy a different model/version or change `$LOC` in Part 1.1 and rerun.
