import logging, json, pathlib, sys
import azure.functions as func
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from common.openapi_validator import validate_openapi
from common.spec_generator import ensure_yaml
from common.docs_logic import generate_spec
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("GenerateOpenApi triggered")
    try: body = req.get_json()
    except ValueError: body = {}
    use_azure = body.get("use_azure_openai", True)
    prompt = body.get("prompt_override") or (pathlib.Path(__file__).parent / "prompt.txt").read_text(encoding="utf-8")
    try:
        yaml_text = generate_spec(use_azure, prompt)
        yaml_text = ensure_yaml(yaml_text)
        tmp = pathlib.Path("/tmp/openapi.yaml"); tmp.write_text(yaml_text, encoding="utf-8")
        validate_openapi(str(tmp))
        return func.HttpResponse(yaml_text, mimetype="text/yaml", status_code=200)
    except Exception as e:
        logging.exception("Error generating OpenAPI")
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)
