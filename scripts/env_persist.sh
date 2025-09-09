#!/usr/bin/env bash
set -euo pipefail
OUT=./env.sh

# FIXED: Removed quotes from heredoc delimiter to allow variable substitution
cat > "$OUT" <<EOF
# Restore environment for this POC
export SUB="$SUB"
export LOC="$LOC"
export SUFFIX="$SUFFIX"
export RG="$RG"
export KV="$KV"
export AOAI_NAME="$AOAI_NAME"
export ST="$ST"
export PLAN="$PLAN"
export FUNCAPP="$FUNCAPP"
export APIM="$APIM"
export API_PATH="$API_PATH"
export API_ID="$API_ID"
export KV_NAME="$KV_NAME"
EOF

echo "Wrote $OUT — next time, run:  source env.sh"
