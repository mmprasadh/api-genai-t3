import argparse, os, yaml, markdown
def try_llm_markdown(spec_yaml: str, use_azure_openai: bool=True) -> str:
    try:
        if use_azure_openai and os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_DEPLOYMENT"):
            from openai import AzureOpenAI
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
            client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version=api_version)
            sys_prompt = "You create excellent, concise developer documentation in Markdown for REST APIs."
            user_prompt = "Generate user-friendly API docs (Overview, Auth, Endpoints table, operation details with params & examples). Use headings and code blocks.\n\nOpenAPI:\n" + spec_yaml
            resp = client.chat.completions.create(model=os.getenv("AZURE_OPENAI_DEPLOYMENT"), messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_prompt}], temperature=0.2)
            return resp.choices[0].message.content
        elif os.getenv("ANTHROPIC_API_KEY"):
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
            sys_prompt = "You create excellent, concise developer documentation in Markdown for REST APIs."
            user_prompt = "Generate user-friendly API docs (Overview, Auth, Endpoints table, operation details with params & examples). Use headings and code blocks.\n\nOpenAPI:\n" + spec_yaml
            msg = client.messages.create(model=model, max_tokens=7000, temperature=0.2, system=sys_prompt, messages=[{"role":"user","content":user_prompt}])
            return "".join([b.text for b in msg.content if hasattr(b,"text")])
    except Exception as e:
        print("LLM docs failed; fallback. Error:", e)
    return ""
def deterministic_markdown(spec: dict) -> str:
    title = spec.get("info",{}).get("title","API"); desc = spec.get("info",{}).get("description","")
    md = [f"# {title}", "", desc, "", "## Authentication", "Header: `Ocp-Apim-Subscription-Key: <key>`", "", "## Endpoints"]
    paths = spec.get("paths",{})
    for p, ops in paths.items():
        md.append(f"### `{p}`")
        for method, op in ops.items():
            summary = op.get("summary",""); md.append(f"#### {method.upper()} — {summary}")
            params = op.get("parameters",[])
            if params:
                md.append("**Parameters**")
                for prm in params:
                    nm=prm.get("name"); loc=prm.get("in"); req=prm.get("required",False)
                    md.append(f"- `{nm}` ({loc}){' – required' if req else ''}")
            if "requestBody" in op: md.append("**Request Body**\n```json\n{...}\n```")
            resps = op.get("responses",{})
            if resps:
                md.append("**Responses**")
                for code, r in resps.items(): md.append(f"- `{code}` {r.get('description','')}")
            md.append("")
    return "\n".join(md)
def to_html(md_text: str) -> str:
    body = markdown.markdown(md_text, extensions=["fenced_code"])
    css = "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;line-height:1.6} pre{background:#f6f8fa;padding:12px;overflow:auto} code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace} h1,h2,h3{margin-top:1.4em} table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px}"
    return f"<!doctype html><meta charset='utf-8'><title>API Docs</title><style>{css}</style><div class='markdown-body'>{body}</div>"
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="../api-spec-gen/openapi.yaml")
    ap.add_argument("--out-md", default="../docs/docs.md")
    ap.add_argument("--out-html", default="../docs/docs.html")
    ap.add_argument("--use-azure-openai", default="true")
    args = ap.parse_args()
    yaml_text = open(args.spec,"r",encoding="utf-8").read()
    import yaml as _yaml; spec = _yaml.safe_load(yaml_text)
    md = ""
    if args.use_azure_openai.lower()=="true" or os.getenv("ANTHROPIC_API_KEY"):
        md = try_llm_markdown(yaml_text, use_azure_openai=(args.use_azure_openai.lower()=="true"))
    if not md.strip():
        md = deterministic_markdown(spec)
    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)
    open(args.out_md,"w",encoding="utf-8").write(md)
    open(args.out_html,"w",encoding="utf-8").write(to_html(md))
    print("Docs created:", args.out_md, "and", args.out_html)
if __name__ == "__main__": main()
