import logging, json, pathlib, sys
import azure.functions as func
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from common.docs_logic import generate_docs_md, md_to_html
from common.spec_generator import ensure_yaml
from common.openapi_validator import validate_openapi
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("GenerateDocsFromOpenApi triggered")
    try: body = req.get_json()
    except ValueError: body = {}
    fmt = (body.get("format") or "markdown").lower()
    use_azure = body.get("use_azure_openai", True)
    openapi_yaml = body.get("openapi_yaml")
    try:
        if not openapi_yaml:
            return func.HttpResponse(json.dumps({"error":"openapi_yaml missing"}), mimetype="application/json", status_code=400)
        y = ensure_yaml(openapi_yaml)
        tmp = pathlib.Path("/tmp/openapi.yaml"); tmp.write_text(y, encoding="utf-8")
        validate_openapi(str(tmp))
        md = generate_docs_md(openapi_yaml, use_azure)
        if fmt == "html": return func.HttpResponse(md_to_html(md), mimetype="text/html", status_code=200)
        return func.HttpResponse(md, mimetype="text/markdown", status_code=200)
    except Exception as e:
        logging.exception("Error generating docs")
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)
