# M1 Developer Experience Improvements Plan

## 🎯 **M1 DevEx Strategy**

With M0-D6 foundation complete, M1 focuses on **scaling developer productivity** as the system grows with plugins, workflows, and advanced features.

## 🚀 **Priority 1: Dev Environment Parity**

### **Goal**: Maintain "local = CI" parity as system complexity grows

#### **Plugin System Environment**
```bash
# Ensure plugin development doesn't break parity
make setup-plugin-env
# - Sets up plugin development environment
# - Installs plugin dependencies
# - Configures plugin paths
# - Validates plugin manifest schema
```

#### **Workflow Engine Environment**
```bash
# Ensure workflow development maintains parity
make setup-workflow-env
# - Sets up workflow development environment
# - Installs workflow dependencies
# - Configures workflow paths
# - Validates workflow schema
```

#### **Environment Variables Management**
```bash
# Standardized environment setup
.env.example          # Template for required variables
.env.local           # Local development overrides
.env.test            # Test environment configuration
```

**Implementation**:
- Create environment setup scripts
- Document all required environment variables
- Ensure CI uses same environment configuration
- Add environment validation to pre-commit hooks

## 🛠️ **Priority 2: Plugin Development Tooling**

### **Goal**: Streamline plugin creation and development

#### **Plugin Scaffolding**
```bash
# Create new plugin from template
make scaffold-plugin PLUGIN_NAME=my-plugin PLUGIN_TYPE=scanner

# Generates:
# plugins/my-plugin/
# ├── __init__.py
# ├── manifest.yaml
# ├── scanner.py
# ├── tests/
# │   └── test_scanner.py
# └── README.md
```

#### **Plugin Development Tools**
```bash
# Plugin-specific commands
make plugin-test PLUGIN_NAME=my-plugin    # Test specific plugin
make plugin-lint PLUGIN_NAME=my-plugin     # Lint specific plugin
make plugin-validate PLUGIN_NAME=my-plugin # Validate plugin manifest
```

#### **Plugin Template System**
```yaml
# templates/plugin-scanner.yaml
name: "{{PLUGIN_NAME}}"
version: "1.0.0"
type: "scanner"
description: "{{PLUGIN_DESCRIPTION}}"
author: "{{AUTHOR_NAME}}"
dependencies:
  - "requests"
  - "pyyaml"
```

**Implementation**:
- Create cookiecutter templates for different plugin types
- Add plugin-specific Makefile targets
- Implement plugin validation tools
- Create plugin development documentation

## 📚 **Priority 3: Internal Documentation**

### **Goal**: Comprehensive developer guides for M1 features

#### **Plugin Developer Guide**
```markdown
# docs/developer-guides/plugin-development.md
## Plugin Architecture
## Security Policy
## Testing Guidelines
## Deployment Process
```

#### **Workflow Developer Guide**
```markdown
# docs/developer-guides/workflow-development.md
## Workflow Engine Design
## Linear v1 Implementation
## Integration Patterns
## Testing Strategies
```

#### **Integration Developer Guide**
```markdown
# docs/developer-guides/integration-development.md
## Tool Integration Patterns
## Parser Development
## Contract Testing
## Performance Considerations
```

**Implementation**:
- Collaborate with Security Lead on plugin security docs
- Work with Tools Lead on integration patterns
- Create comprehensive developer guides
- Establish documentation review process

## 🧪 **Priority 4: Extended Testing Infrastructure**

### **Goal**: Higher-level testing for M1 architecture

#### **Contract Tests Directory**
```bash
# Create missing contract tests structure
mkdir -p tests/contracts/
touch tests/contracts/__init__.py
touch tests/contracts/test_plugin_contracts.py
touch tests/contracts/test_workflow_contracts.py
```

#### **Integration Test Framework**
```python
# tests/integration/test_plugin_workflow_integration.py
def test_plugin_workflow_end_to_end():
    """Test plugin execution within workflow engine."""
    workflow = WorkflowEngine.load("test-workflow.yaml")
    plugin = PluginLoader.load("test-plugin")
    
    result = workflow.execute(plugin)
    assert result.status == "success"
    assert len(result.findings) > 0
```

#### **Sample Integration Test**
```python
# tests/integration/test_basic_workflow.py
def test_basic_workflow_execution():
    """Test basic workflow execution with dummy plugin."""
    # Create dummy plugin
    plugin = DummyPlugin(name="test-scanner")
    
    # Create simple workflow
    workflow = LinearWorkflow()
    workflow.add_step(plugin)
    
    # Execute workflow
    result = workflow.execute(target="http://example.com")
    
    # Verify results
    assert result.completed
    assert result.findings_count > 0
```

**Implementation**:
- Create contract tests directory structure
- Write sample integration tests
- Establish integration test patterns
- Coordinate with QA Lead on test strategies

## 📊 **Priority 5: Observability Integration**

### **Goal**: Seamless logging and metrics in development

#### **Test Logging Configuration**
```python
# tests/conftest.py
import logging
import pytest

@pytest.fixture(autouse=True)
def configure_test_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise in tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
```

#### **Development Metrics**
```python
# scripts/dev-metrics.py
def collect_dev_metrics():
    """Collect development metrics."""
    metrics = {
        'test_coverage': get_coverage_percentage(),
        'lint_errors': get_lint_error_count(),
        'type_errors': get_type_error_count(),
        'plugin_count': get_plugin_count(),
        'workflow_count': get_workflow_count()
    }
    return metrics
```

**Implementation**:
- Work with Observability Lead on logging standards
- Implement test logging configuration
- Create development metrics collection
- Establish observability patterns for M1

## 🔧 **Priority 6: Development Tools**

### **Goal**: Enhanced developer productivity tools

#### **Development Dashboard**
```bash
# Local development status
make dev-status
# Shows:
# - Test coverage
# - Lint status
# - Type check status
# - Plugin status
# - Workflow status
```

#### **Quick Development Commands**
```bash
# Plugin development shortcuts
make plugin-dev PLUGIN_NAME=my-plugin    # Start plugin development mode
make plugin-watch PLUGIN_NAME=my-plugin  # Watch plugin for changes

# Workflow development shortcuts
make workflow-dev WORKFLOW_NAME=my-workflow    # Start workflow development mode
make workflow-test WORKFLOW_NAME=my-workflow   # Test workflow execution
```

#### **Development Utilities**
```python
# scripts/dev-utils.py
def validate_plugin_manifest(manifest_path):
    """Validate plugin manifest against schema."""
    # Implementation

def generate_plugin_tests(plugin_path):
    """Generate test skeleton for plugin."""
    # Implementation

def check_workflow_syntax(workflow_path):
    """Check workflow syntax and dependencies."""
    # Implementation
```

**Implementation**:
- Create development dashboard
- Implement plugin/workflow development shortcuts
- Build development utilities
- Establish development tool patterns

## 📋 **Implementation Timeline**

### **Week 1-2: Foundation**
- [ ] Create plugin scaffolding system
- [ ] Implement environment parity tools
- [ ] Set up contract tests directory

### **Week 3-4: Documentation**
- [ ] Write plugin developer guide
- [ ] Create workflow developer guide
- [ ] Establish documentation review process

### **Week 5-6: Testing**
- [ ] Implement integration test framework
- [ ] Write sample integration tests
- [ ] Establish testing patterns

### **Week 7-8: Tooling**
- [ ] Create development dashboard
- [ ] Implement development utilities
- [ ] Establish observability patterns

## 🎯 **Success Metrics**

### **M1 DevEx KPIs**
- **Plugin Development Time**: < 2 hours from idea to working plugin
- **Environment Parity**: 100% local-CI parity maintained
- **Documentation Coverage**: 100% of M1 features documented
- **Test Coverage**: Maintain or improve from M0 baseline
- **Developer Satisfaction**: Positive feedback on M1 tooling

### **Quality Gates**
- **Plugin Validation**: All plugins pass validation
- **Workflow Testing**: All workflows have integration tests
- **Documentation**: All new features documented
- **Performance**: No regression in development speed

## 🚀 **M1 DevEx Deliverables**

### **Tools**
- [ ] Plugin scaffolding system
- [ ] Development dashboard
- [ ] Environment parity tools
- [ ] Development utilities

### **Documentation**
- [ ] Plugin developer guide
- [ ] Workflow developer guide
- [ ] Integration developer guide
- [ ] M1 onboarding updates

### **Testing**
- [ ] Contract tests framework
- [ ] Integration test patterns
- [ ] Sample integration tests
- [ ] Testing guidelines

### **Infrastructure**
- [ ] Environment management
- [ ] Observability integration
- [ ] Development tooling
- [ ] Quality gates

## 📞 **Coordination Points**

### **Security Lead**
- Plugin security policy documentation
- Security testing guidelines
- Plugin validation requirements

### **Tools Lead**
- Tool integration patterns
- Parser development guidelines
- Integration testing strategies

### **QA Lead**
- Testing framework design
- Test automation patterns
- Quality assurance processes

### **Observability Lead**
- Logging standards
- Metrics collection
- Monitoring integration

---

**M1 DevEx Mission**: Scale developer productivity while maintaining quality and governance standards established in M0-D6.

*Plan created by DevEx Lead - 2025-10-15*
