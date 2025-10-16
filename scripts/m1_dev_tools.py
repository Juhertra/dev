#!/usr/bin/env python3
"""
M1 Developer Workflow Tools

Enhanced developer tools for M1 development including:
- Development environment setup
- Plugin development tools
- Workflow testing tools
- Coverage analysis tools
- Debug mode utilities
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

class M1DevTools:
    """M1 Developer Tools."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.plugins_dir = self.project_root / "packages" / "plugins"
        self.workflows_dir = self.project_root / "packages" / "workflow_engine"
        
    def setup_dev_environment(self):
        """Set up M1 development environment."""
        print("🚀 Setting up M1 development environment...")
        
        # Install dependencies
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], 
                      cwd=self.project_root, check=True)
        
        # Install pre-commit hooks
        print("🔧 Installing pre-commit hooks...")
        subprocess.run(["pre-commit", "install"], cwd=self.project_root, check=True)
        
        # Create development directories
        print("📁 Creating development directories...")
        dirs_to_create = [
            "plugins/dev",
            "workflows/dev", 
            "tests/fixtures",
            "tests/mocks",
            "reports/coverage",
            "logs"
        ]
        
        for dir_path in dirs_to_create:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ {dir_path}")
        
        # Create .env.local template
        env_template = """# M1 Development Environment Variables
SECFLOW_DEBUG=1
SECFLOW_LOG_LEVEL=DEBUG
SECFLOW_PLUGIN_PATH=plugins/dev
SECFLOW_WORKFLOW_PATH=workflows/dev
SECFLOW_TEMP_DIR=tmp
SECFLOW_CACHE_DIR=cache
"""
        
        env_file = self.project_root / ".env.local"
        if not env_file.exists():
            with open(env_file, 'w') as f:
                f.write(env_template)
            print("   ✓ .env.local template created")
        
        print("✅ M1 development environment setup complete!")
    
    def scaffold_plugin(self, plugin_name: str, plugin_type: str = "scanner"):
        """Scaffold a new plugin."""
        print(f"🔧 Scaffolding {plugin_type} plugin: {plugin_name}")
        
        plugin_dir = self.plugins_dir / plugin_name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # Create plugin structure
        files_to_create = {
            "__init__.py": f'''"""
{plugin_name} Plugin

A {plugin_type} plugin for SecFlow M1.
"""

from .{plugin_name} import {plugin_name.title()}Plugin

__all__ = ["{plugin_name.title()}Plugin"]
''',
            f"{plugin_name}.py": f'''"""
{plugin_name.title()} Plugin Implementation

This module implements the {plugin_name} {plugin_type} plugin.
"""

import logging
from typing import Dict, List, Any, Optional
from packages.plugins.loader import PluginInterface

logger = logging.getLogger(__name__)

class {plugin_name.title()}Plugin(PluginInterface):
    """{plugin_name.title()} {plugin_type.title()} Plugin."""
    
    def __init__(self):
        self.name = "{plugin_name}"
        self.version = "1.0.0"
        self.type = "{plugin_type}"
        self.description = "A {plugin_type} plugin for {plugin_name}"
        
    def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plugin with given configuration."""
        logger.info(f"Executing {{self.name}} plugin")
        
        # TODO: Implement plugin logic
        result = {{
            "success": True,
            "findings": [],
            "metadata": {{
                "plugin": self.name,
                "version": self.version,
                "type": self.type
            }}
        }}
        
        return result
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        # TODO: Implement configuration validation
        return True
    
    def get_required_config(self) -> List[str]:
        """Get list of required configuration keys."""
        # TODO: Define required configuration
        return []
''',
            "manifest.yaml": f'''name: {plugin_name}
version: 1.0.0
type: {plugin_type}
description: A {plugin_type} plugin for {plugin_name}
author: Developer
entrypoint: {plugin_name.title()}Plugin
dependencies:
  - requests
  - pyyaml
config_schema:
  type: object
  properties:
    target:
      type: string
      description: Target to scan
  required:
    - target
''',
            "tests/__init__.py": "",
            f"tests/test_{plugin_name}.py": f'''"""
Tests for {plugin_name} plugin.
"""

import pytest
from {plugin_name} import {plugin_name.title()}Plugin

class Test{plugin_name.title()}Plugin:
    """Test {plugin_name.title()}Plugin."""
    
    def test_plugin_initialization(self):
        """Test plugin initialization."""
        plugin = {plugin_name.title()}Plugin()
        assert plugin.name == "{plugin_name}"
        assert plugin.version == "1.0.0"
        assert plugin.type == "{plugin_type}"
    
    def test_plugin_execution(self):
        """Test plugin execution."""
        plugin = {plugin_name.title()}Plugin()
        config = {{"target": "test.com"}}
        result = plugin.execute(config)
        
        assert result["success"] is True
        assert "findings" in result
        assert "metadata" in result
    
    def test_config_validation(self):
        """Test configuration validation."""
        plugin = {plugin_name.title()}Plugin()
        config = {{"target": "test.com"}}
        assert plugin.validate_config(config) is True
    
    def test_required_config(self):
        """Test required configuration."""
        plugin = {plugin_name.title()}Plugin()
        required = plugin.get_required_config()
        assert isinstance(required, list)
''',
            "README.md": f'''# {plugin_name.title()} Plugin

A {plugin_type} plugin for SecFlow M1.

## Description

This plugin provides {plugin_name} functionality for the SecFlow security testing platform.

## Configuration

### Required Parameters

- `target`: The target to scan

### Example Configuration

```yaml
target: "https://example.com"
```

## Usage

```python
from {plugin_name} import {plugin_name.title()}Plugin

plugin = {plugin_name.title()}Plugin()
config = {{"target": "https://example.com"}}
result = plugin.execute(config)
```

## Development

### Running Tests

```bash
pytest tests/test_{plugin_name}.py
```

### Plugin Development

1. Implement the `execute` method
2. Add configuration validation
3. Write tests
4. Update documentation
'''
        }
        
        for file_path, content in files_to_create.items():
            full_path = plugin_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            print(f"   ✓ {file_path}")
        
        print(f"✅ Plugin {plugin_name} scaffolded successfully!")
        print(f"📁 Plugin directory: {plugin_dir}")
        print(f"🧪 Run tests: pytest {plugin_dir}/tests/")
    
    def scaffold_workflow(self, workflow_name: str):
        """Scaffold a new workflow."""
        print(f"🔧 Scaffolding workflow: {workflow_name}")
        
        workflow_dir = self.workflows_dir / workflow_name
        workflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Create workflow structure
        files_to_create = {
            f"{workflow_name}.yaml": f'''name: {workflow_name}
version: 1.0.0
description: A workflow for {workflow_name}
author: Developer

steps:
  - name: step1
    plugin: example-plugin
    config:
      target: "{{{{ target }}}}"
    retries: 3
    timeout: 30
  
  - name: step2
    plugin: another-plugin
    config:
      input: "{{{{ step1.output }}}}"
    depends_on: [step1]

metadata:
  tags: [development, example]
  category: security-scan
''',
            f"tests/test_{workflow_name}.py": f'''"""
Tests for {workflow_name} workflow.
"""

import pytest
from packages.workflow_engine.executor import WorkflowExecutor

class Test{workflow_name.title()}Workflow:
    """Test {workflow_name.title()}Workflow."""
    
    def test_workflow_validation(self):
        """Test workflow validation."""
        workflow_path = "workflows/{workflow_name}.yaml"
        executor = WorkflowExecutor()
        
        # TODO: Implement workflow validation test
        assert True
    
    def test_workflow_execution(self):
        """Test workflow execution."""
        workflow_path = "workflows/{workflow_name}.yaml"
        executor = WorkflowExecutor()
        
        # TODO: Implement workflow execution test
        assert True
''',
            "README.md": f'''# {workflow_name.title()} Workflow

A workflow for {workflow_name} in SecFlow M1.

## Description

This workflow defines the steps for {workflow_name} processing.

## Steps

1. **step1**: Execute example-plugin
2. **step2**: Execute another-plugin (depends on step1)

## Usage

```bash
python tools/run_workflow.py workflows/{workflow_name}.yaml
```

## Development

### Running Tests

```bash
pytest tests/test_{workflow_name}.py
```

### Workflow Development

1. Define workflow steps in YAML
2. Configure plugin dependencies
3. Write tests
4. Update documentation
'''
        }
        
        for file_path, content in files_to_create.items():
            full_path = workflow_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            print(f"   ✓ {file_path}")
        
        print(f"✅ Workflow {workflow_name} scaffolded successfully!")
        print(f"📁 Workflow directory: {workflow_dir}")
        print(f"🧪 Run tests: pytest {workflow_dir}/tests/")
    
    def run_coverage_analysis(self, module: Optional[str] = None):
        """Run coverage analysis for specific module or entire project."""
        print("📊 Running coverage analysis...")
        
        cmd = ["pytest", "--cov=.", "--cov-report=term-missing", "--cov-report=xml", "-q"]
        
        if module:
            cmd.extend(["--cov", module])
            print(f"   Analyzing module: {module}")
        
        try:
            subprocess.run(cmd, cwd=self.project_root, check=True)
            
            # Generate dashboard
            subprocess.run([sys.executable, "scripts/coverage_dashboard.py"], 
                          cwd=self.project_root, check=True)
            
            print("✅ Coverage analysis complete!")
            print("📊 Dashboard generated in reports/coverage/")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Coverage analysis failed: {e}")
            sys.exit(1)
    
    def run_debug_mode(self, command: str):
        """Run command in debug mode."""
        print(f"🐛 Running in debug mode: {command}")
        
        env = os.environ.copy()
        env.update({
            "SECFLOW_DEBUG": "1",
            "SECFLOW_LOG_LEVEL": "DEBUG",
            "PYTHONPATH": str(self.project_root)
        })
        
        try:
            subprocess.run(command.split(), env=env, cwd=self.project_root, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            sys.exit(1)
    
    def dev_status(self):
        """Show development status."""
        print("📊 M1 Development Status")
        print("=" * 50)
        
        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"🐍 Python Version: {python_version}")
        
        # Check dependencies
        print("\n📦 Dependencies:")
        try:
            import pytest, coverage, ruff, pyright
            print("   ✓ pytest")
            print("   ✓ coverage")
            print("   ✓ ruff")
            print("   ✓ pyright")
        except ImportError as e:
            print(f"   ❌ Missing dependency: {e}")
        
        # Check test status
        print("\n🧪 Test Status:")
        try:
            result = subprocess.run(["pytest", "--collect-only", "-q"], 
                                  cwd=self.project_root, capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✓ Tests can be collected")
            else:
                print("   ❌ Test collection issues")
        except Exception as e:
            print(f"   ❌ Test check failed: {e}")
        
        # Check coverage
        print("\n📊 Coverage Status:")
        try:
            result = subprocess.run(["coverage", "report", "--show-missing"], 
                                  cwd=self.project_root, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                total_line = [line for line in lines if 'TOTAL' in line]
                if total_line:
                    print(f"   {total_line[0]}")
            else:
                print("   ❌ Coverage report failed")
        except Exception as e:
            print(f"   ❌ Coverage check failed: {e}")
        
        print("\n" + "=" * 50)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="M1 Developer Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up M1 development environment")
    
    # Plugin commands
    plugin_parser = subparsers.add_parser("plugin", help="Plugin development tools")
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_action")
    
    scaffold_plugin_parser = plugin_subparsers.add_parser("scaffold", help="Scaffold a new plugin")
    scaffold_plugin_parser.add_argument("name", help="Plugin name")
    scaffold_plugin_parser.add_argument("--type", default="scanner", help="Plugin type")
    
    # Workflow commands
    workflow_parser = subparsers.add_parser("workflow", help="Workflow development tools")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_action")
    
    scaffold_workflow_parser = workflow_subparsers.add_parser("scaffold", help="Scaffold a new workflow")
    scaffold_workflow_parser.add_argument("name", help="Workflow name")
    
    # Coverage command
    coverage_parser = subparsers.add_parser("coverage", help="Coverage analysis tools")
    coverage_parser.add_argument("--module", help="Specific module to analyze")
    
    # Debug command
    debug_parser = subparsers.add_parser("debug", help="Run command in debug mode")
    debug_parser.add_argument("command", help="Command to run")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show development status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tools = M1DevTools()
    
    if args.command == "setup":
        tools.setup_dev_environment()
    elif args.command == "plugin" and args.plugin_action == "scaffold":
        tools.scaffold_plugin(args.name, args.type)
    elif args.command == "workflow" and args.workflow_action == "scaffold":
        tools.scaffold_workflow(args.name)
    elif args.command == "coverage":
        tools.run_coverage_analysis(args.module)
    elif args.command == "debug":
        tools.run_debug_mode(args.command)
    elif args.command == "status":
        tools.dev_status()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
