# GenAI API Lifecycle Management

This package implements **complete API lifecycle management** with AI-powered generation, security validation, and documentation automation.

## 🎯 **Core Use Cases**

### **Use Case 1: Secure API Generation** ⭐ *Enhanced with 42Crunch*
**English Input → LLM → Security Analysis → Corrected API Spec**
- Generate OpenAPI 3.0.3 specifications from natural language
- **Automatic 42Crunch security analysis and corrections**
- **Iterative LLM improvements until 90+ security score**
- Enterprise security standards compliance (OWASP, GDPR, PCI-DSS)

### **Use Case 2: Intelligent Documentation**
**API Spec → LLM → User-Friendly Documentation**
- Generate comprehensive API documentation (Markdown + HTML)
- Developer-friendly format with examples and guides
- Multi-format output support

## 🏗️ **Architecture Components**

### **Azure Functions**
- `GenerateOpenApi` - AI-powered spec generation **with 42Crunch integration**
- `GenerateDocsFromOpenApi` - Intelligent documentation generation

### **Security Integration** 🔒
- **42Crunch Security Analysis** - Automated vulnerability scanning
- **Auto-Fix Engine** - LLM-powered security issue resolution
- **Iterative Improvement** - Continuous refinement until target score
- **Enterprise Rulesets** - Custom security standards enforcement

### **MCP Orchestrator** (Model Context Protocol)
- Complete API lifecycle orchestration
- Tool integration (generate/validate/import/docs)
- Azure CLI integration for resource management

### **CI/CD Pipeline**
- **Spectral** → **42Crunch** → **Auto-Fix** → **Re-check** → Import → API Center → Docs
- Automated security gates and quality assurance
- Multi-environment deployment support

## ⚡ **Quick Start**

### **Immediate Testing (15 minutes)**
```bash
# 1. Setup testing environment
./testing/setup-testing-environment.sh
source .env.testing

# 2. Deploy Azure Functions
./testing/quick-deploy-functions.sh

# 3. Install 42Crunch CLI
npm install -g @42crunch/api-security-audit

# 4. Test everything
./testing/test-functions.sh

# 5. Run complete Use Case 1
./scripts/use-case-1-complete.sh "Create a Banking API with account management, transactions, and security features"