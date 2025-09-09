import os, markdown
from .spec_generator import build_kv, gen_with_azure_openai, gen_with_claude, ensure_yaml
from .openapi_validator import validate_openapi
def generate_spec(use_azure: bool, prompt: str) -> str:
    kv = build_kv()
    yaml_text = generate_with(kv, use_azure, prompt)
    yaml_text = ensure_yaml(yaml_text)
    return yaml_text
def generate_with(kv, use_azure: bool, prompt: str) -> str:
    if use_azure:
        return gen_with_azure_openai(kv, prompt)
    return gen_with_claude(kv, prompt)
def generate_docs_md(spec_yaml: str, use_azure: bool=True) -> str:
    md = ""
    try:
        if use_azure and os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_DEPLOYMENT"):
            from openai import AzureOpenAI
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
            client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version=api_version)
            sys_prompt = "You create excellent, concise developer documentation in Markdown for REST APIs."
            user_prompt = "Generate user-friendly API docs (Overview, Auth, Endpoints table, per operation: summary, params, examples). Use headings and code blocks.\n\nOpenAPI:\n" + spec_yaml
            resp = client.chat.completions.create(model=os.getenv("AZURE_OPENAI_DEPLOYMENT"), messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_prompt}], temperature=0.2)
            md = resp.choices[0].message.content
        elif os.getenv("ANTHROPIC_API_KEY"):
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
            sys_prompt = "You create excellent, concise developer documentation in Markdown for REST APIs."
            user_prompt = "Generate user-friendly API docs (Overview, Auth, Endpoints table, per operation: summary, params, examples). Use headings and code blocks.\n\nOpenAPI:\n" + spec_yaml
            r = client.messages.create(model=model, max_tokens=7000, temperature=0.2, system=sys_prompt, messages=[{"role":"user","content":user_prompt}])
            md = "".join([b.text for b in r.content if hasattr(b,"text")])
    except Exception:
        md = ""
    if not md.strip():
        import yaml as _yaml
        spec = _yaml.safe_load(spec_yaml)
        def det(spec: dict) -> str:
            title = spec.get("info",{}).get("title","API"); desc=spec.get("info",{}).get("description","")
            out=[f"# {title}","",desc,"","## Authentication","Header: `Ocp-Apim-Subscription-Key: <key>`","","## Endpoints"]
            for p,ops in spec.get("paths",{}).items():
                out.append(f"### `{p}`")
                for m,op in ops.items():
                    out.append(f"#### {m.upper()} — {op.get('summary','')}")
                    params=op.get("parameters",[])
                    if params:
                        out.append("**Parameters**")
                        for prm in params:
                            out.append(f"- `{prm.get('name')}` ({prm.get('in')}){' – required' if prm.get('required',False) else ''}")
                    if "requestBody" in op: out.append("**Request Body**\n```json\n{...}\n```")
                    resps=op.get("responses",{})
                    if resps:
                        out.append("**Responses**")
                        for code,r in resps.items(): out.append(f"- `{code}` {r.get('description','')}")
                    out.append("")
            return "\n".join(out)
        md = det(spec)
    return md
def md_to_html(md_text:str)->str:
    body = markdown.markdown(md_text, extensions=["fenced_code"])
    css="body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;line-height:1.6} pre{background:#f6f8fa;padding:12px;overflow:auto} code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace} h1,h2,h3{margin-top:1.4em} table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px}"
    return f"<!doctype html><meta charset='utf-8'><title>API Docs</title><style>{css}</style><div class='markdown-body'>{body}</div>"
