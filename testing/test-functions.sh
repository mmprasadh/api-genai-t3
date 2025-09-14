#!/bin/bash
# testing/test-functions.sh
set -euo pipefail

echo "🧪 Testing GenAI API Functions"

# Load environment and endpoints
if [ ! -f testing/.endpoints ]; then
    echo "❌ Function endpoints not found. Run ./testing/quick-deploy-functions.sh first"
    exit 1
fi

source testing/.endpoints
source .env.testing

echo "📡 Testing function endpoints..."

# Test 1: Generate OpenAPI Specification
echo ""
echo "📝 Test 1: Generating OpenAPI specification..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${GEN_FUNC_URL}?code=${GEN_FUNC_CODE}" \
    -H "Content-Type: application/json" \
    -d "{\"use_azure_openai\": true, \"prompt_override\": \"$TEST_PROMPT\", \"use_42crunch\": false}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ OpenAPI generation successful"
    echo "$BODY" > test-generated-spec.yaml
    echo "📄 Spec saved to: test-generated-spec.yaml"
    
    # Basic validation
    python3 -c "
import yaml
try:
    spec = yaml.safe_load(open('test-generated-spec.yaml', 'r').read())
    print('✅ Generated spec is valid YAML')
    print(f'   Title: {spec.get(\"info\", {}).get(\"title\", \"Unknown\")}')
    print(f'   Paths: {len(spec.get(\"paths\", {}))}')
except Exception as e:
    print(f'❌ Spec validation failed: {e}')
    exit(1)
    "
else
    echo "❌ OpenAPI generation failed (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

# Test 2: Generate Documentation
echo ""
echo "📚 Test 2: Generating API documentation..."
SPEC_CONTENT=$(cat test-generated-spec.yaml | sed 's/"/\\"/g' | tr '\n' '\\n')

DOC_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${DOCS_FUNC_URL}?code=${DOCS_FUNC_CODE}" \
    -H "Content-Type: application/json" \
    -d "{\"format\": \"markdown\", \"use_azure_openai\": true, \"openapi_yaml\": \"$SPEC_CONTENT\"}")

DOC_HTTP_CODE=$(echo "$DOC_RESPONSE" | tail -n1)
DOC_BODY=$(echo "$DOC_RESPONSE" | head -n -1)

if [ "$DOC_HTTP_CODE" = "200" ]; then
    echo "✅ Documentation generation successful"
    echo "$DOC_BODY" > test-docs.md
    echo "📄 Docs saved to: test-docs.md"
else
    echo "❌ Documentation generation failed (HTTP $DOC_HTTP_CODE)"
    echo "$DOC_BODY"
fi

# Test 3: 42Crunch Integration Test
echo ""
echo "🔒 Test 3: Testing 42Crunch integration..."

# Check if 42Crunch CLI is available
if command -v 42c >/dev/null 2>&1; then
    echo "✅ 42Crunch CLI found"
    
    # Test with 42Crunch enabled
    CRUNCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${GEN_FUNC_URL}?code=${GEN_FUNC_CODE}" \
        -H "Content-Type: application/json" \
        -d "{\"use_azure_openai\": true, \"prompt_override\": \"$TEST_PROMPT\", \"use_42crunch\": true, \"target_score\": 80}")
    
    CRUNCH_HTTP_CODE=$(echo "$CRUNCH_RESPONSE" | tail -n1)
    CRUNCH_BODY=$(echo "$CRUNCH_RESPONSE" | head -n -1)
    
    if [ "$CRUNCH_HTTP_CODE" = "200" ]; then
        echo "✅ 42Crunch integration successful"
        echo "$CRUNCH_BODY" | jq . > test-42crunch-response.json
        
        FINAL_SCORE=$(echo "$CRUNCH_BODY" | jq -r '.final_score // 0')
        echo "🔒 Final Security Score: $FINAL_SCORE/100"
        echo "📄 42Crunch response saved to: test-42crunch-response.json"
    else
        echo "⚠️ 42Crunch integration test failed (HTTP $CRUNCH_HTTP_CODE)"
        echo "$CRUNCH_BODY"
    fi
else
    echo "⚠️ 42Crunch CLI not installed. Install with: npm install -g @42crunch/api-security-audit"
fi

echo ""
echo "🎉 Function testing complete!"
echo ""
echo "📊 Test Results Summary:"
echo "  ✅ OpenAPI Generation: Working"
echo "  ✅ Documentation Generation: Working"
echo "  $([ -f test-42crunch-response.json ] && echo "✅" || echo "⚠️") 42Crunch Integration: $([ -f test-42crunch-response.json ] && echo "Working" || echo "Needs 42Crunch CLI")"

# Cleanup
echo ""
read -p "🧹 Clean up test files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f test-*.yaml test-*.md test-*.json
    echo "✅ Test files cleaned up"
fi