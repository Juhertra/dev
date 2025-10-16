# Developer Onboarding Guide - SecFlow

## 🚀 **Welcome to SecFlow Development**

This guide will help you get up and running with the SecFlow security testing platform. Our development environment is designed for **perfect local-CI parity** - what works locally will work in CI.

## 📋 **Prerequisites**

- **Python 3.11.9** (exact version required)
- **Git** with GitHub access
- **GitHub CLI** (`gh`) for repository operations
- **Make** for standardized commands

## 🛠️ **Initial Setup**

### **1. Clone and Setup Environment**
```bash
# Clone the repository
git clone https://github.com/Juhertra/dev.git
cd dev

# Install dependencies
make setup
# This runs: pip install -e ".[dev]"

# Verify installation
python --version  # Should show 3.11.9
```

### **2. Install Pre-commit Hooks**
```bash
# Install pre-commit hooks for automated quality gates
pre-commit install

# Test the hooks
pre-commit run --all-files
```

**Pre-commit hooks include**:
- **ruff**: Python linting and formatting
- **pyright**: Static type checking
- **pytest**: Quick test execution
- **docs-health**: Documentation validation

## ✅ **Development Workflow**

### **Daily Development Loop**
```bash
# Run all quality gates before committing
make lint && make type && make imports && pytest -q

# Expected output:
# ✅ All checks passed! (ruff)
# ✅ 0 errors, 0 warnings, 0 informations (pyright)  
# ✅ Contracts: 1 kept, 0 broken (imports)
# ✅ 126 tests passing (pytest)
```

### **Individual Commands**
```bash
# Code quality
make lint          # ruff check . (linting + formatting)
make type          # pyright (static type checking)
make imports       # lint-imports (import architecture)

# Testing
make unit          # pytest -q (unit tests)
make coverage      # coverage run -m pytest -q && coverage report -m

# Documentation
make health        # Documentation health checks
```

## 🔄 **Git Workflow**

### **Branch Naming Convention**
```bash
# Feature branches
feat/<issue-number>-<slug>
# Example: feat/123-add-plugin-support

# Bug fixes
fix/<issue-number>-<slug>
# Example: fix/456-resolve-memory-leak

# DevEx improvements
devex/<description>
# Example: devex/improve-ci-performance

# Documentation
docs/<description>
# Example: docs/update-api-docs
```

### **Pull Request Process**

#### **1. Create Issue First**
- Use **Bug Report** template for bugs
- Use **Feature Request** template for features
- Link to appropriate milestone (M1, M2, etc.)

#### **2. Create Branch and PR**
```bash
# Create feature branch
git checkout -b feat/123-add-plugin-support

# Make changes and commit
git add .
git commit -m "feat(plugin): add plugin support framework"

# Push and create PR
git push -u origin feat/123-add-plugin-support
gh pr create --title "feat(plugin): add plugin support framework"
```

#### **3. PR Template Requirements**
Every PR must include:
- ✅ **Issue Link**: `Fixes #123` or `Closes #123`
- ✅ **DoD Checklist**: Complete all required items
- ✅ **Validation Evidence**: Paste test/coverage output
- ✅ **Risk Assessment**: Identify risks and rollback plan

#### **4. Code Review Process**
- **Required Reviewers**: Based on CODEOWNERS mapping
- **Size Limits**: ≤400 LOC or requires 2 approvals
- **CI Checks**: All 7 checks must pass
- **Coverage**: Must maintain or improve coverage

## 📚 **Repository Governance**

### **Code Ownership (CODEOWNERS)**
```
# Core & runtime
/secflow/core/**         @runtime-lead @security-lead
/secflow/storage/**      @runtime-lead
/secflow/workflow/**     @workflow-lead @runtime-lead

# Tools & parsers  
/secflow/tools/**        @tools-lead @findings-lead

# Schemas
/schemas/**              @findings-lead @runtime-lead

# Plugins & policies
/plugins/**              @security-lead

# Observability & devex
/ops/**                  @observability-lead @devex-lead
/scripts/**              @devex-lead

# Docs
/docs/**                 @devex-lead

# Root config
/*                       @devex-lead
```

### **Engineering Standards**
- **Read**: `docs/governance/engineering-standards.md`
- **Follow**: Definition of Done checklist
- **Adhere**: Development conventions

### **Source of Truth Architecture**
- **Workflow Engine**: `docs/architecture/workflow-engine-design.md`
- **Plugin System**: `docs/architecture/plugin-architecture.md`
- **Storage Layer**: `docs/architecture/storage-design.md`

## 🧪 **Testing Guidelines**

### **Test Structure**
```
tests/
├── unit/                 # Unit tests
├── contracts/           # Contract tests (architecture compliance)
├── integration/         # Integration tests (future)
└── e2e/                # End-to-end tests (future)
```

### **Writing Tests**
```python
# Example unit test
def test_plugin_loading():
    """Test plugin loading functionality."""
    plugin = PluginLoader.load("test-plugin")
    assert plugin.name == "test-plugin"
    assert plugin.version == "1.0.0"
```

### **Running Tests**
```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_plugin.py

# With coverage
pytest --cov=. --cov-report=term-missing

# Contract tests only
pytest tests/contracts/
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **"Command not found" errors**
```bash
# Ensure you're in the project root
cd /path/to/dev

# Reinstall dependencies
make setup

# Check Python version
python --version  # Should be 3.11.9
```

#### **Pre-commit hook failures**
```bash
# Run hooks manually to see errors
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify -m "temp commit"
```

#### **CI failures**
```bash
# Run same commands locally
make lint && make type && make imports && pytest -q

# Check for dependency issues
pip list | grep -E "(ruff|pyright|pytest|flask)"
```

### **Getting Help**
- **DevEx Lead**: For development environment issues
- **Runtime Lead**: For core system questions
- **Tools Lead**: For tool integration questions
- **Security Lead**: For security policy questions

## 📈 **Quality Metrics**

### **Current Baseline (M0)**
- **Test Coverage**: 18% (M0 threshold)
- **Test Count**: 126 tests
- **Linting**: 0 errors, 0 warnings
- **Type Checking**: 0 errors, 0 warnings, 0 informations
- **Import Architecture**: 1 contract kept, 0 broken

### **Coverage Ratchet**
- **M0**: 18% (current baseline)
- **M1**: TBD (will be set higher)
- **Enforcement**: Coverage cannot decrease

## 🚀 **M1 Development Focus**

### **Plugin System Development**
- **Plugin Architecture**: Follow design docs
- **Security Policy**: Adhere to plugin security guidelines
- **Testing**: Write contract tests for plugin interfaces

### **Workflow Engine**
- **Linear v1**: Implement basic workflow execution
- **Integration**: Connect with plugin system
- **Testing**: End-to-end workflow tests

### **Observability**
- **Logging**: Structured logging for all components
- **Metrics**: Performance and usage metrics
- **Monitoring**: Health checks and alerts

## 📝 **Contributing Checklist**

Before submitting a PR:

- [ ] **Issue Created**: Linked to appropriate milestone
- [ ] **Branch Named**: Following convention
- [ ] **Pre-commit Passes**: `pre-commit run --all-files`
- [ ] **All Checks Pass**: `make lint && make type && make imports && pytest -q`
- [ ] **PR Template**: Complete DoD checklist
- [ ] **Validation Evidence**: Paste test/coverage output
- [ ] **Code Review**: Required reviewers assigned
- [ ] **Documentation**: Updated if needed

## 🎯 **Success Criteria**

You're successfully onboarded when you can:
- ✅ Run all quality gates locally (`make lint && make type && make imports && pytest -q`)
- ✅ Create a PR that passes all CI checks
- ✅ Follow the branch naming and PR template conventions
- ✅ Understand the code ownership structure
- ✅ Write tests that maintain or improve coverage

## 📞 **Support**

- **Documentation**: Check `docs/` directory first
- **Issues**: Create GitHub issues for bugs/questions
- **Discussions**: Use GitHub Discussions for general questions
- **Team Leads**: Contact appropriate lead for domain-specific questions

---

**Welcome to SecFlow development!** 🚀

*This guide is maintained by the DevEx team. Last updated: 2025-10-15*
