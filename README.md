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
```

### **Production Deployment**
See **[RUNBOOK_NEW.md](RUNBOOK_NEW.md)** for complete deployment guide.

## 🔒 **Security Standards**

### **Automated Compliance**
- **OWASP API Security Top 10** compliance
- **GDPR** data protection requirements
- **PCI-DSS** payment security standards
- **SOX** audit trail requirements

### **Security Features**
- **90+ Security Score** target with 42Crunch
- **Automatic vulnerability detection** and correction
- **Enterprise authentication schemes** (API Key + OAuth2)
- **Comprehensive error handling** with proper status codes
- **Rate limiting** and throttling documentation

## 🛠️ **Technologies Used**

- **Azure Functions** (Python 3.11) - Serverless compute
- **Azure OpenAI** - LLM integration
- **42Crunch** - API security analysis
- **Azure Key Vault** - Secrets management
- **Azure API Management** - API gateway
- **Spectral** - OpenAPI linting
- **FastMCP** - Model Context Protocol server

## 📋 **What's Included**

### **Core Components**
- Azure Functions with AI integration
- 42Crunch security analysis engine
- MCP orchestrator server
- Deployment and provisioning scripts
- Security rulesets and configurations

### **Enhanced Features** ⭐
- **Iterative 42Crunch integration** with automatic corrections
- **Enterprise security rulesets** (90+ score targeting)
- **Auto-fix engine** powered by LLM feedback
- **Comprehensive testing suite** with security validation
- **Multi-environment CI/CD** pipeline

## 🚀 **Advanced Usage**

### **Custom Security Rules**
Configure enterprise security standards in `security/42c-conf-enhanced.yaml`

### **MCP Integration**
```bash
cd mcp
python orchestrator_server.py
# Use MCP client to call: generate_openapi, validate_openapi, security_analyze
```

### **CI/CD Pipeline**
Automated pipeline with security gates:
1. **Generate** API spec from requirements
2. **Analyze** with 42Crunch for vulnerabilities  
3. **Auto-fix** security issues using LLM
4. **Re-validate** until security score achieved
5. **Deploy** to API Management
6. **Generate** and publish documentation

## 📚 **Documentation**

- **[RUNBOOK_NEW.md](RUNBOOK_NEW.md)** - Complete deployment guide
- **[Security Configuration](security/)** - 42Crunch rulesets
- **[Scripts](scripts/)** - Deployment and automation
- **[Testing](testing/)** - Test suites and validation

## 🎯 **Success Metrics**

- **Security Score**: 90+/100 (42Crunch)
- **Generation Time**: <60 seconds
- **API Standards**: OpenAPI 3.0.3 compliant
- **Documentation**: Auto-generated in Markdown/HTML
- **Deployment**: Fully automated with security gates
