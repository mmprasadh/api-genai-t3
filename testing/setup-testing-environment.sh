#!/bin/bash
# testing/setup-testing-environment.sh
set -euo pipefail

echo "🚀 Setting up GenAI API Testing Environment"

# Check prerequisites
echo "🔍 Checking prerequisites..."
command -v az >/dev/null 2>&1 || { echo "❌ Azure CLI required. Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.9+ required"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "❌ curl required"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm required for 42Crunch CLI"; exit 1; }

echo "✅ Prerequisites check passed"

# Verify Azure login
if ! az account show >/dev/null 2>&1; then
    echo "🔐 Azure login required"
    az login --use-device-code
fi

# Get current subscription
CURRENT_SUB=$(az account show --query id -o tsv)
echo "📋 Current Azure subscription: $CURRENT_SUB"

# Set up environment variables
SUFFIX=$(date +%s | tail -c 6)
cat > .env.testing <<EOF
# Azure Configuration
export SUB="$CURRENT_SUB"
export LOC="eastus2"
export SUFFIX="$SUFFIX"
export RG="GenAI-APILifecycle-Test-$SUFFIX"
export KV="genai-test-kv-$SUFFIX"
export AOAI_NAME="genai-test-aoai-$SUFFIX"
export ST="sapitest$SUFFIX"
export FUNCAPP="func-api-test-$SUFFIX"
export KV_NAME="\$KV"

# Testing Configuration
export API_PATH="test-api"
export API_ID="test-api"
export TEST_PROMPT="Design a simple User Management API with CRUD operations for users. Include authentication endpoints."
EOF

echo "✅ Environment configured in .env.testing"
echo "🎯 Resource Group: GenAI-APILifecycle-Test-$SUFFIX"
echo ""
echo "Next steps:"
echo "   1. Run: source .env.testing"
echo "   2. Run: ./testing/quick-deploy-functions.sh"
echo "   3. Install 42Crunch: npm install -g @42crunch/api-security-audit"