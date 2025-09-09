#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv && source .venv/bin/activate
pip install -r docs-gen/requirements.txt
python docs-gen/docs_generator.py --spec api-spec-gen/openapi.yaml --out-md docs/docs.md --out-html docs/docs.html --use-azure-openai false
