import os
import json
import sys
import pathlib
import yaml
import re
import subprocess
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_json(path: str) -> Dict[str, Any]:
    """Load JSON file safely"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {path}: {e}")
        return {}

def read_text(path: str) -> str:
    """Read text file safely"""
    return pathlib.Path(path).read_text(encoding='utf-8')

def write_text(path: str, text: str):
    """Write text file safely"""
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(text, encoding='utf-8')

def sanitize_yaml(yaml_text: str) -> str:
    """Clean and validate YAML text"""
    yaml_text = yaml_text.strip()
    
    # Remove code blocks if present
    if yaml_text.startswith("```"):
        yaml_text = re.sub(r"^```(?:yaml|yml)?\s*", "", yaml_text)
        yaml_text = re.sub(r"\s*```$", "", yaml_text)
    
    # Validate and normalize YAML
    try:
        obj = yaml.safe_load(yaml_text)
        return yaml.dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

def run_42crunch_audit(spec_path: str, config_path: str = "security/42c-conf-enhanced.yaml") -> Dict[str, Any]:
    """Run 42Crunch audit and return results"""
    output_path = "security/out/42c-audit-autofix.json"
    
    try:
        # Ensure output directory exists
        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Run 42Crunch audit
        cmd = [
            "42c", "audit", 
            "--config", config_path,
            "--format", "json",
            "--output-file", output_path,
            spec_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if os.path.exists(output_path):
            return load_json(output_path)
        else:
            return {"score": 0, "issues": []}
            
    except subprocess.TimeoutExpired:
        logger.error("42Crunch audit timed out")
        return {"score": 0, "issues": []}
    except Exception as e:
        logger.error(f"42Crunch audit failed: {e}")
        return {"score": 0, "issues": []}

def deterministic_patches(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Apply deterministic security patches"""
    
    # Ensure OpenAPI version
    if spec.get("openapi") not in ("3.0.0", "3.0.1", "3.0.2", "3.0.3"):
        spec["openapi"] = "3.0.3"
    
    # Ensure HTTPS servers
    servers = spec.get("servers") or []
    if not servers:
        spec["servers"] = [{"url": "https://api.example.corp/v1"}]
    else:
        for server in servers:
            if "url" in server and isinstance(server["url"], str):
                if server["url"].startswith("http://"):
                    server["url"] = "https://" + server["url"][7:]
    
    # Ensure security schemes
    components = spec.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    
    # Add API Key authentication
    security_schemes.setdefault("apiKeyAuth", {
        "type": "apiKey",
        "in": "header", 
        "name": "X-API-Key",
        "description": "API key for authentication"
    })
    
    # Add OAuth2 authentication
    security_schemes.setdefault("oauth2Auth", {
        "type": "oauth2",
        "description": "OAuth2 authentication",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": "https://auth.example.corp/oauth/authorize",
                "tokenUrl": "https://auth.example.corp/oauth/token",
                "scopes": {
                    "read": "Read access",
                    "write": "Write access",
                    "admin": "Administrative access"
                }
            }
        }
    })
    
    # Apply global security
    spec.setdefault("security", [
        {"apiKeyAuth": []},
        {"oauth2Auth": ["read"]}
    ])
    
    # Ensure error schema
    schemas = components.setdefault("schemas", {})
    schemas.setdefault("Error", {
        "type": "object",
        "required": ["code", "message"],
        "properties": {
            "code": {
                "type": "string",
                "description": "Error code"
            },
            "message": {
                "type": "string", 
                "description": "Error message"
            },
            "details": {
                "type": "object",
                "description": "Additional error details"
            }
        },
        "example": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request parameters",
            "details": {}
        }
    })
    
    # Add rate limiting schema
    schemas.setdefault("RateLimitError", {
        "type": "object",
        "required": ["code", "message", "retry_after"],
        "properties": {
            "code": {"type": "string", "example": "RATE_LIMIT_EXCEEDED"},
            "message": {"type": "string", "example": "Rate limit exceeded"},
            "retry_after": {"type": "integer", "example": 60}
        }
    })
    
    # Ensure proper error responses for all operations
    for path, operations in (spec.get("paths") or {}).items():
        for method, operation in (operations or {}).items():
            if isinstance(operation, dict):
                responses = operation.setdefault("responses", {})
                
                # Add standard error responses
                responses.setdefault("400", {
                    "description": "Bad Request - Invalid request parameters",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                })
                
                responses.setdefault("401", {
                    "description": "Unauthorized - Invalid or missing authentication",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                })
                
                responses.setdefault("403", {
                    "description": "Forbidden - Insufficient permissions",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                })
                
                responses.setdefault("429", {
                    "description": "Too Many Requests - Rate limit exceeded",
                    "headers": {
                        "X-RateLimit-Limit": {
                            "description": "Request limit per time window",
                            "schema": {"type": "integer"}
                        },
                        "X-RateLimit-Remaining": {
                            "description": "Remaining requests in current window", 
                            "schema": {"type": "integer"}
                        },
                        "X-RateLimit-Reset": {
                            "description": "Time when rate limit resets",
                            "schema": {"type": "integer"}
                        }
                    },
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RateLimitError"}
                        }
                    }
                })
                
                responses.setdefault("500", {
                    "description": "Internal Server Error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                })
                
                # Ensure operation has required fields
                operation.setdefault("description", f"{method.upper()} operation for {path}")
                operation.setdefault("operationId", f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}")
                operation.setdefault("tags", [path.split('/')[1] if len(path.split('/')) > 1 else "default"])
                
                # Add security to operation if not present
                if "security" not in operation:
                    operation["security"] = [{"apiKeyAuth": []}]
    
    # Ensure info section has required fields
    info = spec.setdefault("info", {})
    info.setdefault("description", "API specification generated with security best practices")
    info.setdefault("contact", {
        "name": "API Support",
        "email": "api-support@example.corp",
        "url": "https://support.example.corp"
    })
    info.setdefault("license", {
        "name": "Proprietary",
        "url": "https://example.corp/license"
    })
    info.setdefault("termsOfService", "https://example.corp/terms")
    
    return spec

def build_comprehensive_prompt(original_yaml: str, spectral_json: Dict, crunch_json: Dict, previous_attempts: int = 0) -> str:
    """Build comprehensive prompt for LLM-based fixes"""
    
    issues = []
    
    # Process Spectral issues
    if isinstance(spectral_json, list):
        for item in spectral_json:
            severity = item.get("severity", 4)
            if severity <= 1:  # Error or warn level
                issues.append(f"SPECTRAL {item.get('code', 'unknown')}: {item.get('message', '')} @ {item.get('path', '')}")
    
    # Process 42Crunch issues with prioritization
    if isinstance(crunch_json, dict):
        score = crunch_json.get("score", 0)
        issues.append(f"42CRUNCH SECURITY SCORE: {score}/100 (Target: 90+)")
        
        crunch_issues = crunch_json.get("issues", [])
        
        # Prioritize issues by severity
        critical_issues = [i for i in crunch_issues if i.get("severity") == "CRITICAL"]
        high_issues = [i for i in crunch_issues if i.get("severity") == "HIGH"] 
        medium_issues = [i for i in crunch_issues if i.get("severity") == "MEDIUM"]
        
        # Add critical issues first
        for item in critical_issues[:5]:
            issues.append(f"42CRUNCH CRITICAL: {item.get('title', 'Unknown')} - {item.get('description', '')}")
        
        # Add high issues
        for item in high_issues[:5]:
            issues.append(f"42CRUNCH HIGH: {item.get('title', 'Unknown')} - {item.get('description', '')}")
        
        # Add medium issues if score is low
        if score < 80:
            for item in medium_issues[:3]:
                issues.append(f"42CRUNCH MEDIUM: {item.get('title', 'Unknown')} - {item.get('description', '')}")
    
    problems = "\n".join(issues) if issues else "Apply enterprise security best practices and improve overall API security posture."
    
    # Add context about previous attempts
    attempt_context = ""
    if previous_attempts > 0:
        attempt_context = f"""
PREVIOUS ATTEMPTS: {previous_attempts}
This specification has been through {previous_attempts} improvement attempts. Focus on the remaining issues and ensure all critical security requirements are addressed.
"""
    
    prompt = f"""You are an expert OpenAPI 3.0.3 security architect specializing in enterprise-grade API specifications.

TASK: Transform this OpenAPI specification to achieve 90+ security score and meet enterprise security standards.

{attempt_context}

SECURITY REQUIREMENTS TO ADDRESS:
{problems}

ENTERPRISE SECURITY STANDARDS (MANDATORY):
- Use HTTPS-only servers with proper base URLs
- Implement comprehensive authentication (API Key + OAuth2)  
- Include detailed security schemes for all operations
- Add complete error response schemas (400, 401, 403, 429, 500)
- Include rate limiting headers and documentation
- Ensure all operations have descriptions, operationIds, and tags
- Add proper contact information and licensing
- Include comprehensive examples without sensitive data
- Follow OWASP API Security Top 10 guidelines
- Implement data validation with proper schema constraints
- Add security headers and CORS documentation

COMPLIANCE REQUIREMENTS:
- GDPR: Data minimization and privacy considerations
- PCI-DSS: No sensitive payment data in examples
- SOX: Proper audit trail and access controls
- OWASP: Complete security scheme implementation

QUALITY REQUIREMENTS:
- All paths must have comprehensive documentation
- All responses must include proper schema definitions  
- All operations must have proper security requirements
- Include comprehensive parameter validation
- Add proper HTTP status code usage

CURRENT SPECIFICATION TO IMPROVE:
{original_yaml}

INSTRUCTIONS:
1. Maintain the original API functionality and structure
2. Fix ALL identified security issues
3. Apply all enterprise security standards listed above
4. Ensure the specification is valid OpenAPI 3.0.3
5. Include comprehensive but safe examples
6. Add detailed descriptions for all components
7. Implement proper error handling patterns
8. Include rate limiting and throttling considerations

OUTPUT: Return ONLY the complete improved OpenAPI 3.0.3 YAML specification. No explanations, no markdown formatting, no additional text - just the pure YAML."""

    return prompt

def use_azure_openai() -> bool:
    """Check if Azure OpenAI credentials are available"""
    required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    return all(os.getenv(var) for var in required_vars)

def llm_fix_with_iterations(yaml_text: str, spectral_json: Dict, crunch_json: Dict, max_iterations: int = 3) -> str:
    """Apply LLM fixes with iterative 42Crunch validation"""
    
    current_spec = yaml_text
    
    for iteration in range(max_iterations):
        logger.info(f"LLM improvement iteration {iteration + 1}/{max_iterations}")
        
        if use_azure_openai():
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], 
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
            )
            
            prompt = build_comprehensive_prompt(current_spec, spectral_json, crunch_json, iteration)
            
            response = client.chat.completions.create(
                model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                temperature=0.1,  # Lower temperature for more consistent fixes
                max_tokens=12000,
                messages=[
                    {"role": "system", "content": "You return only valid OpenAPI 3.0.3 YAML specifications with enterprise security standards applied. No explanations or additional text."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            improved_spec = sanitize_yaml(response.choices[0].message.content)
        else:
            # Fallback to deterministic patches
            logger.info("No LLM available, applying deterministic security patches")
            obj = yaml.safe_load(current_spec)
            obj = deterministic_patches(obj)
            improved_spec = yaml.dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False)
        
        # Validate improved spec with 42Crunch
        temp_spec_path = f"/tmp/improved_spec_iter_{iteration}.yaml"
        write_text(temp_spec_path, improved_spec)
        
        new_audit = run_42crunch_audit(temp_spec_path)
        new_score = new_audit.get("score", 0)
        
        logger.info(f"Iteration {iteration + 1} score: {new_score}")
        
        # Check if we've achieved target score
        if new_score >= 90:
            logger.info(f"Target score achieved in iteration {iteration + 1}")
            return improved_spec
        
        # Update for next iteration
        current_spec = improved_spec
        crunch_json = new_audit
    
    return current_spec

def main():
    """Main auto-fix execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-fix OpenAPI specs using Spectral and 42Crunch feedback")
    parser.add_argument("openapi_spec", help="Path to OpenAPI YAML file")
    parser.add_argument("spectral_report", nargs="?", default="spectral.json", help="Path to Spectral JSON report")
    parser.add_argument("crunch_report", nargs="?", default="security/out/42c-audit.json", help="Path to 42Crunch JSON report")
    parser.add_argument("output_path", nargs="?", default="openapi.fixed.yaml", help="Output path for fixed spec")
    parser.add_argument("--max-iterations", type=int, default=3, help="Maximum LLM improvement iterations")
    
    args = parser.parse_args()
    
    logger.info(f"Starting auto-fix process for {args.openapi_spec}")
    
    # Load input files
    original_yaml = read_text(args.openapi_spec)
    spectral_json = load_json(args.spectral_report) if os.path.exists(args.spectral_report) else {}
    crunch_json = load_json(args.crunch_report) if os.path.exists(args.crunch_report) else {}
    
    # If no 42Crunch report exists, run audit first
    if not crunch_json:
        logger.info("No 42Crunch report found, running audit...")
        crunch_json = run_42crunch_audit(args.openapi_spec)
    
    # Apply fixes with iterations
    fixed_yaml = llm_fix_with_iterations(
        original_yaml, 
        spectral_json, 
        crunch_json, 
        args.max_iterations
    )
    
    # Write output
    write_text(args.output_path, fixed_yaml)
    
    # Run final validation
    final_audit = run_42crunch_audit(args.output_path)
    final_score = final_audit.get("score", 0)
    
    logger.info(f"Auto-fix completed: {args.output_path}")
    logger.info(f"Final security score: {final_score}/100")
    
    if final_score >= 90:
        logger.info("✅ Target security score achieved!")
    else:
        logger.warning(f"⚠️ Target score not reached. Consider manual review.")

if __name__ == "__main__":
    main()
