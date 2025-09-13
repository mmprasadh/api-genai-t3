#!/bin/bash
# Complete Use Case 1: English Input → LLM → 42Crunch → Corrected API Spec
set -euo pipefail

echo "🚀 Use Case 1: Complete API Spec Generation with 42Crunch Integration"

# Configuration
INPUT_PROMPT="${1:-Create a comprehensive E-commerce API with products, orders, users, and payments. Include proper authentication and error handling.}"
OUTPUT_DIR="use-case-1-output"
MAX_ITERATIONS=3
TARGET_SCORE=80

# Setup
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo "📝 Input: $INPUT_PROMPT"
echo "🎯 Target Security Score: $TARGET_SCORE/100"
echo "🔄 Max Iterations: $MAX_ITERATIONS"

# Step 1: Generate initial API spec using Azure Function
echo ""
echo "Step 1: Generating initial API specification..."
source ../testing/.endpoints 2>/dev/null || {
    echo "❌ Function endpoints not found. Please run quick deployment first:"
    echo "   ./testing/quick-deploy-functions.sh"
    exit 1
}

# Call function with 42Crunch integration enabled
RESPONSE=$(curl -s -X POST "${GEN_FUNC_URL}?code=${GEN_FUNC_CODE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"use_azure_openai\": true,
        \"prompt_override\": \"$INPUT_PROMPT\",
        \"use_42crunch\": true,
        \"max_crunch_iterations\": $MAX_ITERATIONS,
        \"target_score\": $TARGET_SCORE
    }")

echo "$RESPONSE" | jq . > generation-response.json

# Check if generation was successful
if echo "$RESPONSE" | jq -e '.error' >/dev/null; then
    echo "❌ API generation failed:"
    echo "$RESPONSE" | jq -r '.error'
    exit 1
fi

# Extract the final spec and analysis
echo "$RESPONSE" | jq -r '.openapi_spec' > final-api-spec.yaml
echo "$RESPONSE" | jq '.crunch_analysis' > crunch-analysis.json

# Display results
FINAL_SCORE=$(echo "$RESPONSE" | jq -r '.final_score')
ITERATIONS_USED=$(echo "$RESPONSE" | jq -r '.iterations_used')
IMPROVEMENTS=$(echo "$RESPONSE" | jq -r '.improvements_made[]')

echo ""
echo "✅ API Specification Generation Complete!"
echo ""
echo "📊 Results Summary:"
echo "   🎯 Final Security Score: $FINAL_SCORE/100"
echo "   🔄 Iterations Used: $ITERATIONS_USED"
echo "   📈 Improvements Made:"
while IFS= read -r improvement; do
    echo "      • $improvement"
done <<< "$IMPROVEMENTS"

# Validate final spec
echo ""
echo "🔍 Validating final specification..."
python3 -c "
import yaml
from openapi_spec_validator import validate_spec
try:
    with open('final-api-spec.yaml', 'r') as f:
        spec = yaml.safe_load(f)
    validate_spec(spec)
    print('✅ Final specification is valid OpenAPI 3.0.3')
    print(f'   Title: {spec.get(\"info\", {}).get(\"title\", \"Unknown\")}')
    print(f'   Version: {spec.get(\"info\", {}).get(\"version\", \"Unknown\")}')
    print(f'   Endpoints: {len(spec.get(\"paths\", {}))}')
except Exception as e:
    print(f'❌ Specification validation failed: {e}')
    exit(1)
"

# Generate documentation
echo ""
echo "📚 Generating API documentation..."
SPEC_CONTENT=$(cat final-api-spec.yaml | sed 's/"/\\"/g' | tr '\n' '\\n')

curl -s -X POST "${DOCS_FUNC_URL}?code=${DOCS_FUNC_CODE}" \
    -H "Content-Type: application/json" \
    -d "{\"format\": \"html\", \"use_azure_openai\": true, \"openapi_yaml\": \"$SPEC_CONTENT\"}" \
    > api-documentation.html

curl -s -X POST "${DOCS_FUNC_URL}?code=${DOCS_FUNC_CODE}" \
    -H "Content-Type: application/json" \
    -d "{\"format\": \"markdown\", \"use_azure_openai\": true, \"openapi_yaml\": \"$SPEC_CONTENT\"}" \
    > api-documentation.md

echo ""
echo "🎉 Use Case 1 Complete!"
echo ""
echo "📁 Generated Files:"
echo "   📄 final-api-spec.yaml - Final OpenAPI specification"
echo "   🌐 api-documentation.html - HTML documentation"
echo "   📝 api-documentation.md - Markdown documentation"
echo "   📊 crunch-analysis.json - Security analysis report"
echo "   📋 generation-response.json - Complete generation response"
echo ""
echo "🔗 Quick Access:"
echo "   API Spec: $(pwd)/final-api-spec.yaml"
echo "   Documentation: file://$(pwd)/api-documentation.html"
echo ""

# Performance summary
if [ "$FINAL_SCORE" -ge "$TARGET_SCORE" ]; then
    echo "✅ SUCCESS: Target security score achieved!"
else
    echo "⚠️  WARNING: Target score not reached (${FINAL_SCORE}/${TARGET_SCORE})"
    echo "   Consider running additional iterations or manual review."
fi

# Display security summary
echo ""
echo "🔒 Security Summary:"
echo "   Score: $FINAL_SCORE/100"
echo "   Status: $([[ $FINAL_SCORE -ge 80 ]] && echo "✅ Enterprise Ready" || echo "⚠️ Needs Review")"
echo "   Iterations: $ITERATIONS_USED/$MAX_ITERATIONS"

cd ..
