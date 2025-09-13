import logging
import json
import pathlib
import sys
import tempfile
import subprocess
import os
import time
import azure.functions as func

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from common.openapi_validator import validate_openapi
from common.spec_generator import ensure_yaml
from common.docs_logic import generate_spec
from common.crunch_integration import CrunchProcessor

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("GenerateOpenApi with 42Crunch triggered")
    
    try:
        body = req.get_json()
    except ValueError:
        body = {}
    
    use_azure = body.get("use_azure_openai", True)
    prompt = body.get("prompt_override") or (pathlib.Path(__file__).parent / "prompt.txt").read_text(encoding="utf-8")
    use_42crunch = body.get("use_42crunch", True)  # New parameter
    max_iterations = body.get("max_crunch_iterations", 3)  # Max correction attempts
    target_score = body.get("target_score", 90)  # Target 42Crunch score
    
    try:
        # Step 1: Generate initial API spec
        logging.info("Generating initial API specification...")
        yaml_text = generate_spec(use_azure, prompt)
        yaml_text = ensure_yaml(yaml_text)
        
        # Step 2: Basic OpenAPI validation
        tmp_file = pathlib.Path("/tmp/openapi_initial.yaml")
        tmp_file.write_text(yaml_text, encoding="utf-8")
        validate_openapi(str(tmp_file))
        
        # Step 3: 42Crunch processing (if enabled)
        if use_42crunch:
            logging.info("Processing with 42Crunch...")
            crunch_processor = CrunchProcessor()
            
            # Process through 42Crunch with iterative improvements
            final_spec, analysis_report = crunch_processor.process_spec_with_iterations(
                yaml_text,
                max_iterations=max_iterations,
                target_score=target_score,
                use_azure_openai=use_azure,
                original_prompt=prompt
            )
            
            # Return enhanced spec with analysis report
            response_data = {
                "openapi_spec": final_spec,
                "crunch_analysis": analysis_report,
                "iterations_used": analysis_report.get("iterations", 1),
                "final_score": analysis_report.get("final_score", 0),
                "improvements_made": analysis_report.get("improvements", [])
            }
            
            return func.HttpResponse(
                json.dumps(response_data),
                mimetype="application/json",
                status_code=200
            )
        else:
            # Return basic spec without 42Crunch processing
            return func.HttpResponse(yaml_text, mimetype="text/yaml", status_code=200)
            
    except Exception as e:
        logging.exception("Error in GenerateOpenApi with 42Crunch processing")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
