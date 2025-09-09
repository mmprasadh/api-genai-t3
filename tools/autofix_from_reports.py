import os, json, sys, pathlib, yaml, re
def load_json(path):
    try: return json.load(open(path,"r",encoding="utf-8"))
    except Exception: return None
def read_text(path): return pathlib.Path(path).read_text(encoding="utf-8")
def write_text(path, text): pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True); pathlib.Path(path).write_text(text, encoding="utf-8")
def sanitize_yaml(yaml_text: str) -> str:
    yaml_text = yaml_text.strip()
    if yaml_text.startswith("```"):
        yaml_text = re.sub(r"^```(?:yaml|yml)?\s*", "", yaml_text); yaml_text = re.sub(r"\s*```$", "", yaml_text)
    obj = yaml.safe_load(yaml_text); return yaml.dump(obj, sort_keys=False, allow_unicode=True)
def deterministic_patches(spec: dict) -> dict:
    if spec.get("openapi") not in ("3.0.0","3.0.1","3.0.2","3.0.3"): spec["openapi"]="3.0.3"
    servers = spec.get("servers") or []
    if not servers: spec["servers"]=[{"url":"https://api.example.corp/v1"}]
    else:
        for s in servers:
            if "url" in s and isinstance(s["url"], str) and s["url"].startswith("http://"):
                s["url"]="https://"+s["url"][7:]
    comps = spec.setdefault("components", {}).setdefault("securitySchemes", {})
    comps.setdefault("apiKeyAuth", {"type":"apiKey","in":"header","name":"Ocp-Apim-Subscription-Key"})
    spec.setdefault("security",[{"apiKeyAuth": []}])
    schemas = spec.setdefault("components", {}).setdefault("schemas", {})
    schemas.setdefault("Error", {"type":"object","properties":{"code":{"type":"string"},"message":{"type":"string"}}, "required":["code","message"]})
    for path, ops in (spec.get("paths") or {}).items():
        for m, op in (ops or {}).items():
            for code, r in (op.get("responses") or {}).items():
                try: c = int(str(code)[:1])
                except: continue
                if c in (4,5):
                    content = r.setdefault("content", {}).setdefault("application/json", {})
                    content["schema"]={"$ref":"#/components/schemas/Error"}
    return spec
def build_prompt(original_yaml:str, spectral_json, x42c_json)->str:
    issues=[]
    if isinstance(spectral_json, list):
        for it in spectral_json:
            sev=it.get("severity")
            if sev==0 or str(sev).lower()=="error":
                issues.append(f"SPECTRAL {it.get('code')}: {it.get('message')} @ {it.get('path')}")
    if isinstance(x42c_json, dict):
        if x42c_json.get("score") is not None: issues.append(f"42CRUNCH SCORE: {x42c_json.get('score')}")
        for it in x42c_json.get("issues", []):
            if it.get("severity") in ("HIGH","CRITICAL"):
                issues.append(f"42CRUNCH {it.get('severity')}: {it.get('title')} @ {it.get('where','')}")
    problems="\\n".join(issues) if issues else "Harden spec to satisfy Spectral and 42Crunch best practices."
    return f\"\"\"You are an expert OpenAPI 3.0.3 security/style engineer.
Return a corrected OpenAPI YAML that passes Spectral (no error-severity) and meets 42Crunch best practices.
Use HTTPS servers under api.example.corp; include apiKey header Ocp-Apim-Subscription-Key; ensure $ref resolve; 4xx/5xx reuse Error schema.
Output only YAML, no comments.
Findings to address:
{problems}

--- ORIGINAL OPENAPI YAML ---
{original_yaml}
\"\"\"
def use_aoai(): return all(os.getenv(k) for k in ("AZURE_OPENAI_API_KEY","AZURE_OPENAI_ENDPOINT","AZURE_OPENAI_DEPLOYMENT"))
def llm_fix(yaml_text, spectral_json, x42c_json):
    if use_aoai():
        from openai import AzureOpenAI
        client = AzureOpenAI(api_key=os.environ["AZURE_OPENAI_API_KEY"], azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_version=os.getenv("AZURE_OPENAI_API_VERSION","2024-10-21"))
        prompt=build_prompt(yaml_text, spectral_json, x42c_json)
        resp=client.chat.completions.create(model=os.environ["AZURE_OPENAI_DEPLOYMENT"], temperature=0.2, messages=[
            {"role":"system","content":"You return only valid OpenAPI 3.0.3 YAML. No commentary."},
            {"role":"user","content":prompt}
        ])
        return sanitize_yaml(resp.choices[0].message.content)
    else:
        obj=yaml.safe_load(yaml_text); obj=deterministic_patches(obj); return yaml.dump(obj, sort_keys=False, allow_unicode=True)
def main():
    openapi_in = sys.argv[1] if len(sys.argv)>1 else "openapi.yaml"
    spectral_json_path = sys.argv[2] if len(sys.argv)>2 else "spectral.json"
    x42c_json_path = sys.argv[3] if len(sys.argv)>3 else "security/out/42c-audit.json"
    out_path = sys.argv[4] if len(sys.argv)>4 else "openapi.fixed.yaml"
    original = read_text(openapi_in)
    spectral_json = load_json(spectral_json_path)
    x42c_json = load_json(x42c_json_path)
    fixed_yaml = llm_fix(original, spectral_json, x42c_json)
    write_text(out_path, fixed_yaml)
    print(f"Wrote {out_path}")
if __name__ == "__main__": main()
