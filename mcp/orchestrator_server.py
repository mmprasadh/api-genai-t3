import os, tempfile, subprocess, json, yaml, requests
from fastmcp import FastMCP, tool
from openapi_spec_validator import validate_spec
RG=os.environ.get("RG"); APIM=os.environ.get("APIM"); API_PATH=os.environ.get("API_PATH","procurement"); API_ID=os.environ.get("API_ID","procurement-api")
FUNC_URL=os.environ.get("FUNC_URL"); FUNC_CODE=os.environ.get("FUNC_CODE")
DOCS_FUNC_URL=os.environ.get("DOCS_FUNC_URL"); DOCS_FUNC_CODE=os.environ.get("DOCS_FUNC_CODE")
SUB_KEY=os.environ.get("APIM_SUBSCRIPTION_KEY")
mcp = FastMCP("GenAI API Orchestrator")
def _az(*args): r=subprocess.run(["az",*args],check=True,capture_output=True,text=True); return r.stdout.strip()
def _tmp(text,suffix=".yaml"):
    fd,path=tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd,"w",encoding="utf-8") as f: f.write(text)
    return path
@tool
def generate_openapi(prompt:str,use_azure_openai:bool=True)->str:
    if not FUNC_URL or not FUNC_CODE: return "ERROR: FUNC_URL/FUNC_CODE not set."
    r=requests.post(f"{FUNC_URL}?code={FUNC_CODE}",json={"use_azure_openai":use_azure_openai,"prompt_override":prompt},timeout=180); r.raise_for_status(); return r.text
@tool
def validate_openapi(yaml_text:str)->dict:
    spec=yaml.safe_load(yaml_text); validate_spec(spec); return {"ok":True,"message":"Spec is valid."}
@tool
def import_to_apim(yaml_text:str,api_path:str=None,api_id:str=None)->str:
    if not RG or not APIM: return "ERROR: Set RG/APIM env vars."
    api_path=api_path or API_PATH; api_id=api_id or API_ID; p=_tmp(yaml_text,".yaml")
    _az("apim","api","import","--resource-group",RG,"--service-name",APIM,"--path",api_path,"--api-id",api_id,"--specification-format","OpenApi","--specification-path",p)
    return f"Imported to APIM: https://{APIM}.azure-api.net/{api_path}"
@tool
def enable_mock(api_id:str=None)->str:
    if not RG or not APIM: return "ERROR: Set RG/APIM env vars."
    api_id=api_id or API_ID
    policy='''<policies><inbound><base /><mock-response /></inbound><backend><base /></backend><outbound><base /></outbound><on-error><base /></on-error></policies>'''
    p=_tmp(policy,".xml")
    _az("apim","api","policy","create","--resource-group",RG,"--service-name",APIM,"--api-id",api_id,"--xml-content",f"@{p}")
    return "Mock policy enabled."
@tool
def generate_docs_md(yaml_text:str,use_azure_openai:bool=True)->str:
    if not DOCS_FUNC_URL or not DOCS_FUNC_CODE: return "ERROR: DOCS_FUNC_URL/DOCS_FUNC_CODE not set."
    r=requests.post(f"{DOCS_FUNC_URL}?code={DOCS_FUNC_CODE}",json={"format":"markdown","use_azure_openai":use_azure_openai,"openapi_yaml":yaml_text},timeout=180)
    r.raise_for_status(); return r.text
@tool
def generate_docs_html(yaml_text:str,use_azure_openai:bool=True)->str:
    if not DOCS_FUNC_URL or not DOCS_FUNC_CODE: return "ERROR: DOCS_FUNC_URL/DOCS_FUNC_CODE not set."
    r=requests.post(f"{DOCS_FUNC_URL}?code={DOCS_FUNC_CODE}",json={"format":"html","use_azure_openai":use_azure_openai,"openapi_yaml":yaml_text},timeout=180)
    r.raise_for_status(); return r.text
@tool
def call_apim_get(url_suffix:str)->dict:
    base=f"https://{APIM}.azure-api.net"; url=f"{base}/{url_suffix.lstrip('/')}"; h={}
    if SUB_KEY: h["Ocp-Apim-Subscription-Key"]=SUB_KEY
    r=requests.get(url,headers=h,timeout=30); return {"status":r.status_code,"body":r.text,"headers":dict(r.headers)}
if __name__=="__main__": mcp.run()
