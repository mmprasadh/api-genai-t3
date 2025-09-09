import os, yaml
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
def _kv_client(vault_name: str):
    cred = DefaultAzureCredential()
    return SecretClient(vault_url=f"https://{vault_name}.vault.azure.net/", credential=cred)
def _kv_get(kv, name): return kv.get_secret(name).value
def gen_with_azure_openai(kv, prompt: str) -> str:
    from openai import AzureOpenAI
    endpoint = _kv_get(kv, "AZURE-OPENAI-ENDPOINT")
    deployment = _kv_get(kv, "AZURE-OPENAI-DEPLOYMENT")
    key = _kv_get(kv, "AZURE-OPENAI-API-KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    client = AzureOpenAI(api_key=key, api_version=api_version, azure_endpoint=endpoint)
    msg = [{"role":"system","content":"You are an expert API architect. Output valid OpenAPI 3.0.3 YAML only, no commentary."},
           {"role":"user","content":prompt}]
    resp = client.chat.completions.create(model=deployment, messages=msg, temperature=0.2)
    return resp.choices[0].message.content
def gen_with_claude(kv, prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=_kv_get(kv, "ANTHROPIC-API-KEY"))
    model = _kv_get(kv, "ANTHROPOPIC-MODEL") if _kv_get else os.getenv("ANTHROPIC_MODEL","claude-3-5-sonnet-20240620")
    msg = client.messages.create(model=model, max_tokens=8000, temperature=0.2,
        system="You are an expert API architect. Output valid OpenAPI 3.0.3 YAML only, no commentary.",
        messages=[{"role":"user","content":prompt}],)
    text = "".join([b.text for b in msg.content if hasattr(b, "text")])
    return text.replace("```yaml","").replace("```","").strip()
def ensure_yaml(yaml_text: str) -> str:
    obj = yaml.safe_load(yaml_text)
    return yaml.dump(obj, sort_keys=False, allow_unicode=True)
def build_kv(vault_name_env="KV_NAME", vault_name_value=None):
    name = vault_name_value or os.environ.get(vault_name_env)
    if not name: raise RuntimeError("Key Vault name not set. Set env KV_NAME or pass vault_name_value.")
    return _kv_client(name)
