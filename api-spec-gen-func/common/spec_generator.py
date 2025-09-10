import os, yaml
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def _kv_client(vault_name: str):
    """Create Key Vault client with DefaultAzureCredential"""
    cred = DefaultAzureCredential()
    return SecretClient(vault_url=f"https://{vault_name}.vault.azure.net/", credential=cred)

def _kv_get(kv, name): 
    """Safely retrieve secret from Key Vault"""
    try:
        return kv.get_secret(name).value
    except Exception as e:
        print(f"Warning: Could not retrieve secret {name}: {e}")
        return None

def gen_with_azure_openai(kv, prompt: str) -> str:
    """Generate OpenAPI spec using Azure OpenAI"""
    from openai import AzureOpenAI
    
    endpoint = _kv_get(kv, "AZURE-OPENAI-ENDPOINT")
    deployment = _kv_get(kv, "AZURE-OPENAI-DEPLOYMENT")
    key = _kv_get(kv, "AZURE-OPENAI-API-KEY")
    
    if not all([endpoint, deployment, key]):
        raise ValueError("Missing required Azure OpenAI configuration in Key Vault")
    
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    client = AzureOpenAI(api_key=key, api_version=api_version, azure_endpoint=endpoint)
    
    msg = [
        {"role": "system", "content": "You are an expert API architect. Output valid OpenAPI 3.0.3 YAML only, no commentary."},
        {"role": "user", "content": prompt}
    ]
    
    resp = client.chat.completions.create(
        model=deployment, 
        messages=msg, 
        temperature=0.2,
        max_tokens=8000
    )
    return resp.choices[0].message.content

def gen_with_claude(kv, prompt: str) -> str:
    """Generate OpenAPI spec using Claude (Anthropic)"""
    import anthropic
    
    api_key = _kv_get(kv, "ANTHROPIC-API-KEY")
    if not api_key:
        raise ValueError("ANTHROPIC-API-KEY not found in Key Vault")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # FIXED: Corrected typo and added proper fallback
    model = _kv_get(kv, "ANTHROPIC-MODEL") or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    
    msg = client.messages.create(
        model=model, 
        max_tokens=8000, 
        temperature=0.2,
        system="You are an expert API architect. Output valid OpenAPI 3.0.3 YAML only, no commentary.",
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = "".join([b.text for b in msg.content if hasattr(b, "text")])
    return text.replace("```yaml", "").replace("```", "").strip()

def ensure_yaml(yaml_text: str) -> str:
    """Validate and normalize YAML text"""
    try:
        obj = yaml.safe_load(yaml_text)
        return yaml.dump(obj, sort_keys=False, allow_unicode=True)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

def build_kv(vault_name_env="KV_NAME", vault_name_value=None):
    """Build Key Vault client with proper error handling"""
    name = vault_name_value or os.environ.get(vault_name_env)
    if not name: 
        raise RuntimeError("Key Vault name not set. Set env KV_NAME or pass vault_name_value.")
    return _kv_client(name)
