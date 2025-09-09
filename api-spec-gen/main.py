import os, pathlib
from openapi_validator import validate_openapi
from spec_generator import build_kv, gen_with_azure_openai, gen_with_claude, ensure_yaml
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "true").lower() == "true"
def run(prompt_path="prompt.txt", out_path="openapi.yaml"):
    prompt = pathlib.Path(prompt_path).read_text(encoding="utf-8")
    kv = build_kv()
    yaml_text = gen_with_azure_openai(kv, prompt) if USE_AZURE_OPENAI else gen_with_claude(kv, prompt)
    yaml_text = ensure_yaml(yaml_text)
    pathlib.Path(out_path).write_text(yaml_text, encoding="utf-8")
    validate_openapi(out_path)
    print(f"✅ OpenAPI spec generated and validated → {out_path}")
if __name__ == "__main__": run()
