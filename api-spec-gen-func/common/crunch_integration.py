import os
import json
import tempfile
import subprocess
import logging
import pathlib
import yaml
from typing import Dict, Any, Tuple, List
from .spec_generator import build_kv, gen_with_azure_openai, gen_with_claude, ensure_yaml

logger = logging.getLogger(__name__)

class CrunchProcessor:
    def __init__(self):
        self.crunch_config = pathlib.Path(__file__).parents[2] / "security" / "42c-conf-enhanced.yaml"
        self.ensure_42crunch_installed()
    
    def ensure_42crunch_installed(self):
        """Ensure 42Crunch CLI is available"""
        try:
            result = subprocess.run(["42c", "--version"], capture_output=True, text=True)
            logger.info(f"42Crunch CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            # Install 42Crunch CLI if not available
            logger.info("Installing 42Crunch CLI...")
            subprocess.run(["npm", "install", "-g", "@42crunch/api-security-audit"], check=True)
    
    def run_42crunch_audit(self, spec_content: str) -> Dict[str, Any]:
        """Run 42Crunch audit on OpenAPI spec"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_spec:
            temp_spec.write(spec_content)
            temp_spec_path = temp_spec.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        try:
            # Run 42Crunch audit
            cmd = [
                "42c", "audit",
                "--config", str(self.crunch_config),
                "--format", "json",
                "--output-file", temp_output_path,
                temp_spec_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            # Read the audit results
            if os.path.exists(temp_output_path):
                with open(temp_output_path, 'r') as f:
                    audit_results = json.load(f)
            else:
                # Fallback: parse from stdout if file not created
                try:
                    audit_results = json.loads(result.stdout)
                except json.JSONDecodeError:
                    audit_results = {
                        "score": 0,
                        "issues": [{"severity": "HIGH", "title": "42Crunch audit failed", "description": result.stderr}]
                    }
            
            logger.info(f"42Crunch audit completed. Score: {audit_results.get('score', 'N/A')}")
            return audit_results
            
        except subprocess.TimeoutExpired:
            logger.error("42Crunch audit timed out")
            return {"score": 0, "issues": [{"severity": "HIGH", "title": "Audit timeout"}]}
        except Exception as e:
            logger.error(f"42Crunch audit failed: {e}")
            return {"score": 0, "issues": [{"severity": "HIGH", "title": "Audit error", "description": str(e)}]}
        finally:
            # Cleanup temp files
            for temp_path in [temp_spec_path, temp_output_path]:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    def generate_improvement_prompt(self, original_prompt: str, spec_content: str, audit_results: Dict[str, Any]) -> str:
        """Generate LLM prompt for improving the spec based on 42Crunch results"""
        issues = audit_results.get("issues", [])
        score = audit_results.get("score", 0)
        
        # Filter and prioritize issues
        critical_issues = [issue for issue in issues if issue.get("severity") == "CRITICAL"]
        high_issues = [issue for issue in issues if issue.get("severity") == "HIGH"]
        medium_issues = [issue for issue in issues if issue.get("severity") == "MEDIUM"]
        
        # Build improvement instructions
        improvement_instructions = []
        
        if critical_issues:
            improvement_instructions.append("CRITICAL SECURITY ISSUES (Must Fix):")
            for issue in critical_issues[:5]:  # Limit to top 5
                improvement_instructions.append(f"- {issue.get('title', 'Unknown issue')}: {issue.get('description', '')}")
        
        if high_issues:
            improvement_instructions.append("\nHIGH PRIORITY ISSUES:")
            for issue in high_issues[:5]:  # Limit to top 5  
                improvement_instructions.append(f"- {issue.get('title', 'Unknown issue')}: {issue.get('description', '')}")
        
        if medium_issues and score < 85:
            improvement_instructions.append("\nMEDIUM PRIORITY ISSUES:")
            for issue in medium_issues[:3]:  # Limit to top 3
                improvement_instructions.append(f"- {issue.get('title', 'Unknown issue')}: {issue.get('description', '')}")
        
        # Add specific customer standards
        customer_standards = [
            "- Include comprehensive security schemes (API key + OAuth2)",
            "- Add detailed error response schemas for 4xx and 5xx status codes", 
            "- Ensure all operations have detailed descriptions and examples",
            "- Include rate limiting and throttling considerations",
            "- Add proper data validation schemas with format constraints",
            "- Include contact information and license in info section",
            "- Use HTTPS-only servers with proper security headers",
            "- Avoid exposing sensitive data in examples or descriptions"
        ]
        
        prompt = f"""You are an expert API security architect. Improve this OpenAPI 3.0.3 specification to meet enterprise security standards.

CURRENT SECURITY SCORE: {score}/100 (Target: 90+)

ORIGINAL REQUEST: {original_prompt}

SECURITY ISSUES TO ADDRESS:
{chr(10).join(improvement_instructions)}

CUSTOMER SECURITY STANDARDS (Must Include):
{chr(10).join(customer_standards)}

CURRENT SPECIFICATION:
{spec_content}

REQUIREMENTS:
1. Fix ALL critical and high-severity security issues
2. Improve the specification to achieve 90+ security score
3. Maintain the original API functionality and structure
4. Follow OWASP API Security Top 10 guidelines
5. Include comprehensive examples that don't expose sensitive data
6. Add proper authentication and authorization schemes
7. Include detailed error handling with proper status codes
8. Add rate limiting and throttling documentation

OUTPUT: Return ONLY the improved OpenAPI 3.0.3 YAML specification with no additional text or comments."""

        return prompt
    
    def improve_spec_with_llm(self, original_prompt: str, current_spec: str, audit_results: Dict[str, Any], use_azure_openai: bool = True) -> str:
        """Use LLM to improve the spec based on 42Crunch feedback"""
        improvement_prompt = self.generate_improvement_prompt(original_prompt, current_spec, audit_results)
        
        try:
            kv = build_kv()
            if use_azure_openai:
                improved_spec = gen_with_azure_openai(kv, improvement_prompt)
            else:
                improved_spec = gen_with_claude(kv, improvement_prompt)
            
            # Ensure it's valid YAML
            improved_spec = ensure_yaml(improved_spec)
            logger.info("LLM spec improvement completed")
            return improved_spec
            
        except Exception as e:
            logger.error(f"LLM improvement failed: {e}")
            return current_spec  # Return original if improvement fails
    
    def process_spec_with_iterations(self, initial_spec: str, max_iterations: int = 3, target_score: int = 90, use_azure_openai: bool = True, original_prompt: str = "") -> Tuple[str, Dict[str, Any]]:
        """Process spec through multiple 42Crunch iterations until target score is achieved"""
        current_spec = initial_spec
        iteration_history = []
        
        for iteration in range(max_iterations):
            logger.info(f"42Crunch iteration {iteration + 1}/{max_iterations}")
            
            # Run 42Crunch audit
            audit_results = self.run_42crunch_audit(current_spec)
            current_score = audit_results.get("score", 0)
            
            iteration_info = {
                "iteration": iteration + 1,
                "score": current_score,
                "issues_count": len(audit_results.get("issues", [])),
                "critical_issues": len([i for i in audit_results.get("issues", []) if i.get("severity") == "CRITICAL"]),
                "high_issues": len([i for i in audit_results.get("issues", []) if i.get("severity") == "HIGH"])
            }
            iteration_history.append(iteration_info)
            
            logger.info(f"Current score: {current_score}, Target: {target_score}")
            
            # Check if we've achieved the target score
            if current_score >= target_score:
                logger.info(f"Target score achieved in {iteration + 1} iterations")
                break
            
            # Check if this is the last iteration
            if iteration == max_iterations - 1:
                logger.warning(f"Max iterations reached. Final score: {current_score}")
                break
            
            # Improve the spec using LLM
            logger.info("Applying LLM improvements based on 42Crunch feedback...")
            improved_spec = self.improve_spec_with_llm(
                original_prompt, 
                current_spec, 
                audit_results, 
                use_azure_openai
            )
            
            # Validate the improved spec
            try:
                ensure_yaml(improved_spec)  # Validate YAML format
                current_spec = improved_spec
                logger.info("Improved spec validated and applied")
            except Exception as e:
                logger.error(f"Improved spec validation failed: {e}. Using previous version.")
                break
        
        # Final audit for the report
        final_audit = self.run_42crunch_audit(current_spec)
        
        analysis_report = {
            "iterations": len(iteration_history),
            "initial_score": iteration_history[0]["score"] if iteration_history else 0,
            "final_score": final_audit.get("score", 0),
            "target_achieved": final_audit.get("score", 0) >= target_score,
            "iteration_history": iteration_history,
            "final_audit": final_audit,
            "improvements": self.summarize_improvements(iteration_history)
        }
        
        return current_spec, analysis_report
    
    def summarize_improvements(self, iteration_history: List[Dict[str, Any]]) -> List[str]:
        """Summarize the improvements made during iterations"""
        if len(iteration_history) < 2:
            return ["Initial generation completed"]
        
        improvements = []
        initial = iteration_history[0]
        final = iteration_history[-1]
        
        score_improvement = final["score"] - initial["score"]
        if score_improvement > 0:
            improvements.append(f"Security score improved by {score_improvement} points")
        
        critical_reduction = initial["critical_issues"] - final["critical_issues"]
        if critical_reduction > 0:
            improvements.append(f"Resolved {critical_reduction} critical security issues")
        
        high_reduction = initial["high_issues"] - final["high_issues"] 
        if high_reduction > 0:
            improvements.append(f"Resolved {high_reduction} high-priority security issues")
        
        total_issues_reduction = initial["issues_count"] - final["issues_count"]
        if total_issues_reduction > 0:
            improvements.append(f"Reduced total issues by {total_issues_reduction}")
        
        if not improvements:
            improvements.append("Specification maintained security standards")
        
        return improvements
