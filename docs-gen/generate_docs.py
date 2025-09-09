import os
import yaml
import markdown
from openai import AzureOpenAI
from openapi_spec_validator import validate_spec

def validate_openapi(spec_text):
    """Validate OpenAPI specification"""
    try:
        spec_dict = yaml.safe_load(spec_text)
        validate_spec(spec_dict)
        print("✅ OpenAPI spec is valid")
        return spec_dict
    except Exception as e:
        print(f"❌ OpenAPI validation failed: {e}")
        return None

def generate_docs_with_llm(spec_text):
    """Generate documentation using Azure OpenAI"""
    try:
        client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        )
        
        system_prompt = """You are an expert technical writer specializing in API documentation. 
        Create comprehensive, developer-friendly documentation that includes:
        - Clear overview and purpose
        - Authentication details
        - Endpoint descriptions with examples
        - Request/response schemas
        - Error handling
        Use clear markdown formatting with proper headers and code blocks."""
        
        user_prompt = f"""Generate user-friendly API documentation from this OpenAPI specification:

{spec_text}

Focus on clarity and practical examples that developers can immediately use."""

        response = client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        return None

def create_fallback_docs(spec_dict):
    """Create basic documentation if LLM fails"""
    info = spec_dict.get("info", {})
    title = info.get("title", "API Documentation")
    description = info.get("description", "")
    
    docs = [f"# {title}", ""]
    if description:
        docs.extend([description, ""])
    
    docs.extend([
        "## Authentication",
        "This API uses API key authentication via the `Ocp-Apim-Subscription-Key` header.",
        "",
        "## Endpoints"
    ])
    
    paths = spec_dict.get("paths", {})
    for path, methods in paths.items():
        docs.append(f"### {path}")
        for method, details in methods.items():
            summary = details.get("summary", "")
            docs.append(f"**{method.upper()}** - {summary}")
            
            # Add parameters if present
            params = details.get("parameters", [])
            if params:
                docs.append("Parameters:")
                for param in params:
                    name = param.get("name", "")
                    location = param.get("in", "")
                    required = " (required)" if param.get("required", False) else ""
                    docs.append(f"- `{name}` ({location}){required}")
            docs.append("")
    
    return "\n".join(docs)

def markdown_to_html(md_content):
    """Convert Markdown to HTML"""
    html_body = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
    
    css = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1000px; margin: 0 auto; padding: 40px 20px; line-height: 1.6; }
        h1, h2, h3 { color: #333; margin-top: 1.5em; }
        code { background: #f1f3f4; padding: 2px 6px; border-radius: 3px; 
               font-family: 'Monaco', 'Consolas', monospace; }
        pre { background: #f8f9fa; padding: 16px; border-radius: 6px; overflow-x: auto; }
        pre code { background: none; padding: 0; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f5f5f5; font-weight: 600; }
        .endpoint { background: #e8f4f8; padding: 10px; border-left: 4px solid #0066cc; margin: 10px 0; }
    </style>
    """
    
    return f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>API Documentation</title>{css}</head>
<body>{html_body}</body></html>"""

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate API documentation from OpenAPI spec')
    parser.add_argument('--spec', required=True, help='Path to OpenAPI YAML/JSON file')
    parser.add_argument('--output-md', default='api-docs.md', help='Output Markdown file')
    parser.add_argument('--output-html', default='api-docs.html', help='Output HTML file')
    parser.add_argument('--use-fallback', action='store_true', help='Force fallback documentation')
    
    args = parser.parse_args()
    
    # Read and validate OpenAPI spec
    print(f"📖 Reading OpenAPI spec from {args.spec}")
    try:
        with open(args.spec, 'r', encoding='utf-8') as f:
            spec_text = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {args.spec}")
        return
    
    spec_dict = validate_openapi(spec_text)
    if not spec_dict:
        return
    
    # Generate documentation
    if not args.use_fallback:
        print("🤖 Generating documentation with Azure OpenAI...")
        docs_markdown = generate_docs_with_llm(spec_text)
    else:
        docs_markdown = None
    
    # Fallback to deterministic generation if LLM fails
    if not docs_markdown or args.use_fallback:
        print("📝 Using fallback documentation generator...")
        docs_markdown = create_fallback_docs(spec_dict)
    
    # Write outputs
    print(f"💾 Writing Markdown documentation to {args.output_md}")
    with open(args.output_md, 'w', encoding='utf-8') as f:
        f.write(docs_markdown)
    
    print(f"🌐 Writing HTML documentation to {args.output_html}")
    html_content = markdown_to_html(docs_markdown)
    with open(args.output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Documentation generation completed!")
    print(f"   📄 Markdown: {args.output_md}")
    print(f"   🌐 HTML: {args.output_html}")

if __name__ == "__main__":
    main()