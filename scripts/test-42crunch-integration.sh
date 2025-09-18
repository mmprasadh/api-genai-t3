#!/bin/bash
# Test 42Crunch integration end-to-end
set -euo pipefail

echo "🧪 Testing 42Crunch Integration"

# Install 42Crunch CLI if needed
if ! command -v 42c &> /dev/null; then
    echo "Installing 42Crunch CLI..."
    npm install -g @42crunch/api-security-audit
fi

# Test with sample spec
echo "Creating test specification..."
cat > test-spec.yaml <<'EOF'
openapi: 3.0.3
info:
  title: Test API
  version: 1.0.0
  description: Test API for 42Crunch integration
servers:
  - url: http://api.example.com/v1
paths:
  /users:
    get:
      summary: Get users
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
EOF

# Run 42Crunch audit
echo "Running 42Crunch audit..."
mkdir -p security/specs security/out
cp test-spec.yaml security/specs/openapi.yaml

42c audit \
    --config security/42c-conf-enhanced.yaml \
    --format json \
    --output-file security/out/test-audit.json \
    security/specs/openapi.yaml

# Check results
SCORE=$(jq '.score' security/out/test-audit.json)
echo "Initial security score: $SCORE/100"

# Run auto-fix
echo "Running auto-fix with 42Crunch integration..."
python3 tools/autofix_from_reports.py \
    test-spec.yaml \
    /dev/null \
    security/out/test-audit.json \
    test-spec-fixed.yaml

# Re-audit fixed spec
42c audit \
    --format json \
    --output-file security/out/test-audit-fixed.json \
    test-spec-fixed.yaml

FIXED_SCORE=$(jq '.score' security/out/test-audit-fixed.json)
echo "Fixed security score: $FIXED_SCORE/100"

# Results
IMPROVEMENT=$((FIXED_SCORE - SCORE))
echo ""
echo "🔒 42Crunch Integration Test Results:"
echo "   Original Score: $SCORE/100"  
echo "   Fixed Score: $FIXED_SCORE/100"
echo "   Improvement: +$IMPROVEMENT points"
echo "   Status: $([[ $FIXED_SCORE -ge 90 ]] && echo "✅ PASSED" || echo "⚠️ NEEDS WORK")"

# Cleanup
rm -f test-spec.yaml test-spec-fixed.yaml
rm -rf security/out/test-audit*

echo "✅ 42Crunch integration test complete"
