#!/usr/bin/env python3
"""
M1 Demo and Sample Usage Tools

This script provides demo functionality for M1 features including:
- Sample workflow execution
- Plugin demonstration
- End-to-end testing
- Performance benchmarking
"""

import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

class M1DemoTools:
    """M1 Demo and Sample Usage Tools."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.plugins_dir = self.project_root / "packages" / "plugins"
        self.workflows_dir = self.project_root / "packages" / "workflow_engine"
        self.demo_dir = self.project_root / "demos"
        
    def setup_demo_environment(self):
        """Set up demo environment with sample data."""
        print("🎬 Setting up M1 demo environment...")
        
        # Create demo directory
        self.demo_dir.mkdir(exist_ok=True)
        
        # Create sample plugins
        self._create_sample_plugins()
        
        # Create sample workflows
        self._create_sample_workflows()
        
        # Create sample data
        self._create_sample_data()
        
        print("✅ Demo environment setup complete!")
        print(f"📁 Demo directory: {self.demo_dir}")
    
    def _create_sample_plugins(self):
        """Create sample plugins for demo."""
        sample_plugins = {
            "http_scanner": {
                "description": "HTTP security scanner",
                "type": "scanner",
                "config": {"target": "https://example.com", "timeout": 30}
            },
            "vulnerability_enricher": {
                "description": "Vulnerability data enricher",
                "type": "enricher", 
                "config": {"cve_database": "nvd", "severity_threshold": "medium"}
            },
            "report_generator": {
                "description": "Security report generator",
                "type": "reporter",
                "config": {"format": "html", "template": "standard"}
            }
        }
        
        for plugin_name, plugin_info in sample_plugins.items():
            plugin_dir = self.plugins_dir / plugin_name
            plugin_dir.mkdir(parents=True, exist_ok=True)
            
            # Create plugin implementation
            plugin_code = f'''"""
{plugin_name.title()} Plugin - Demo Implementation

{plugin_info["description"]}
"""

import logging
import time
import random
from typing import Dict, List, Any
from packages.plugins.loader import PluginInterface

logger = logging.getLogger(__name__)

class {plugin_name.title()}Plugin(PluginInterface):
    """{plugin_info["description"]}."""
    
    def __init__(self):
        self.name = "{plugin_name}"
        self.version = "1.0.0"
        self.type = "{plugin_info["type"]}"
        self.description = "{plugin_info["description"]}"
        
    def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plugin with given configuration."""
        logger.info(f"Executing {{self.name}} plugin")
        
        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.5))
        
        # Generate sample findings
        findings = self._generate_sample_findings(config)
        
        result = {{
            "success": True,
            "findings": findings,
            "metadata": {{
                "plugin": self.name,
                "version": self.version,
                "type": self.type,
                "execution_time": time.time(),
                "config": config
            }}
        }}
        
        return result
    
    def _generate_sample_findings(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sample findings for demo."""
        findings = []
        
        if self.type == "scanner":
            findings = [
                {{
                    "id": "demo-finding-1",
                    "title": "Sample Security Finding",
                    "description": "This is a sample security finding for demo purposes",
                    "severity": "medium",
                    "category": "security",
                    "target": config.get("target", "unknown"),
                    "plugin": self.name
                }},
                {{
                    "id": "demo-finding-2", 
                    "title": "Another Sample Finding",
                    "description": "Another sample finding for demonstration",
                    "severity": "low",
                    "category": "configuration",
                    "target": config.get("target", "unknown"),
                    "plugin": self.name
                }}
            ]
        elif self.type == "enricher":
            findings = [
                {{
                    "id": "demo-enriched-1",
                    "title": "Enriched Vulnerability Data",
                    "description": "Sample enriched vulnerability information",
                    "severity": "high",
                    "category": "vulnerability",
                    "cve": "CVE-2023-1234",
                    "cvss_score": 7.5,
                    "plugin": self.name
                }}
            ]
        elif self.type == "reporter":
            findings = [
                {{
                    "id": "demo-report-1",
                    "title": "Generated Security Report",
                    "description": "Sample security report generated",
                    "severity": "info",
                    "category": "report",
                    "format": config.get("format", "html"),
                    "plugin": self.name
                }}
            ]
        
        return findings
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        return True
    
    def get_required_config(self) -> List[str]:
        """Get list of required configuration keys."""
        return []
'''
            
            with open(plugin_dir / f"{plugin_name}.py", 'w') as f:
                f.write(plugin_code)
            
            # Create plugin manifest
            manifest = {
                "name": plugin_name,
                "version": "1.0.0",
                "type": plugin_info["type"],
                "description": plugin_info["description"],
                "author": "Demo Team",
                "entrypoint": f"{plugin_name.title()}Plugin",
                "dependencies": ["requests", "pyyaml"],
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Target to process"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds"}
                    }
                }
            }
            
            with open(plugin_dir / "manifest.yaml", 'w') as f:
                import yaml
                yaml.dump(manifest, f, default_flow_style=False)
    
    def _create_sample_workflows(self):
        """Create sample workflows for demo."""
        sample_workflows = {
            "security_scan": {
                "description": "Complete security scanning workflow",
                "steps": [
                    {"name": "discovery", "plugin": "http_scanner", "config": {"target": "{{target}}", "timeout": 30}},
                    {"name": "enrichment", "plugin": "vulnerability_enricher", "config": {"cve_database": "nvd"}, "depends_on": ["discovery"]},
                    {"name": "reporting", "plugin": "report_generator", "config": {"format": "html"}, "depends_on": ["enrichment"]}
                ]
            },
            "quick_scan": {
                "description": "Quick security scan workflow",
                "steps": [
                    {"name": "scan", "plugin": "http_scanner", "config": {"target": "{{target}}", "timeout": 10}}
                ]
            }
        }
        
        for workflow_name, workflow_info in sample_workflows.items():
            workflow_file = self.demo_dir / f"{workflow_name}.yaml"
            
            workflow_yaml = f'''name: {workflow_name}
version: 1.0.0
description: {workflow_info["description"]}
author: Demo Team

steps:
'''
            
            for step in workflow_info["steps"]:
                workflow_yaml += f'''  - name: {step["name"]}
    plugin: {step["plugin"]}
    config:
'''
                for key, value in step["config"].items():
                    workflow_yaml += f'''      {key}: {value}
'''
                
                if "depends_on" in step:
                    workflow_yaml += f'''    depends_on: {step["depends_on"]}
'''
                
                workflow_yaml += "\n"
            
            workflow_yaml += '''metadata:
  tags: [demo, sample]
  category: security-scan
'''
            
            with open(workflow_file, 'w') as f:
                f.write(workflow_yaml)
    
    def _create_sample_data(self):
        """Create sample data for demo."""
        sample_data = {
            "targets": [
                "https://example.com",
                "https://httpbin.org",
                "https://jsonplaceholder.typicode.com"
            ],
            "configurations": {
                "security_scan": {
                    "target": "https://example.com",
                    "timeout": 30,
                    "severity_threshold": "medium"
                },
                "quick_scan": {
                    "target": "https://httpbin.org",
                    "timeout": 10
                }
            }
        }
        
        with open(self.demo_dir / "sample_data.json", 'w') as f:
            json.dump(sample_data, f, indent=2)
    
    def run_demo_workflow(self, workflow_name: str, target: str = "https://example.com"):
        """Run a demo workflow."""
        print(f"🎬 Running demo workflow: {workflow_name}")
        print(f"🎯 Target: {target}")
        
        workflow_file = self.demo_dir / f"{workflow_name}.yaml"
        if not workflow_file.exists():
            print(f"❌ Workflow file not found: {workflow_file}")
            return
        
        # Load workflow configuration
        with open(self.demo_dir / "sample_data.json", 'r') as f:
            sample_data = json.load(f)
        
        config = sample_data["configurations"].get(workflow_name, {})
        config["target"] = target
        
        print(f"📋 Configuration: {config}")
        
        # Simulate workflow execution
        print("\n🚀 Executing workflow steps...")
        
        try:
            # Import workflow executor
            sys.path.insert(0, str(self.project_root))
            from packages.workflow_engine.executor import WorkflowExecutor
            
            executor = WorkflowExecutor()
            
            # Execute workflow
            start_time = time.time()
            result = executor.execute_workflow(str(workflow_file), config)
            execution_time = time.time() - start_time
            
            print(f"\n✅ Workflow execution completed in {execution_time:.2f} seconds")
            print(f"📊 Result: {result}")
            
        except ImportError:
            print("⚠️  Workflow executor not available, simulating execution...")
            self._simulate_workflow_execution(workflow_name, config)
        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
    
    def _simulate_workflow_execution(self, workflow_name: str, config: Dict[str, Any]):
        """Simulate workflow execution for demo."""
        import yaml
        
        workflow_file = self.demo_dir / f"{workflow_name}.yaml"
        with open(workflow_file, 'r') as f:
            workflow = yaml.safe_load(f)
        
        print(f"📋 Workflow: {workflow['name']}")
        print(f"📝 Description: {workflow['description']}")
        
        for step in workflow['steps']:
            print(f"\n🔄 Executing step: {step['name']}")
            print(f"   Plugin: {step['plugin']}")
            print(f"   Config: {step['config']}")
            
            # Simulate step execution
            time.sleep(0.5)
            
            print(f"   ✅ Step completed")
        
        print(f"\n🎉 Workflow '{workflow_name}' completed successfully!")
    
    def run_plugin_demo(self, plugin_name: str, config: Optional[Dict[str, Any]] = None):
        """Run a plugin demo."""
        print(f"🔧 Running plugin demo: {plugin_name}")
        
        if config is None:
            config = {"target": "https://example.com", "timeout": 30}
        
        print(f"📋 Configuration: {config}")
        
        try:
            # Import plugin
            sys.path.insert(0, str(self.project_root))
            plugin_module = __import__(f"packages.plugins.{plugin_name}", fromlist=[f"{plugin_name.title()}Plugin"])
            plugin_class = getattr(plugin_module, f"{plugin_name.title()}Plugin")
            
            # Create and execute plugin
            plugin = plugin_class()
            start_time = time.time()
            result = plugin.execute(config)
            execution_time = time.time() - start_time
            
            print(f"\n✅ Plugin execution completed in {execution_time:.2f} seconds")
            print(f"📊 Result: {json.dumps(result, indent=2)}")
            
        except ImportError:
            print(f"⚠️  Plugin {plugin_name} not available, simulating execution...")
            self._simulate_plugin_execution(plugin_name, config)
        except Exception as e:
            print(f"❌ Plugin execution failed: {e}")
    
    def _simulate_plugin_execution(self, plugin_name: str, config: Dict[str, Any]):
        """Simulate plugin execution for demo."""
        print(f"🔄 Simulating {plugin_name} plugin execution...")
        
        # Simulate processing
        time.sleep(0.3)
        
        # Generate sample result
        result = {
            "success": True,
            "findings": [
                {
                    "id": f"demo-{plugin_name}-1",
                    "title": f"Sample finding from {plugin_name}",
                    "description": f"This is a sample finding generated by the {plugin_name} plugin",
                    "severity": "medium",
                    "target": config.get("target", "unknown"),
                    "plugin": plugin_name
                }
            ],
            "metadata": {
                "plugin": plugin_name,
                "execution_time": time.time(),
                "config": config
            }
        }
        
        print(f"✅ Plugin simulation completed")
        print(f"📊 Result: {json.dumps(result, indent=2)}")
    
    def run_performance_benchmark(self):
        """Run performance benchmark."""
        print("⚡ Running M1 performance benchmark...")
        
        benchmarks = {
            "plugin_execution": self._benchmark_plugin_execution,
            "workflow_execution": self._benchmark_workflow_execution,
            "coverage_analysis": self._benchmark_coverage_analysis
        }
        
        results = {}
        
        for benchmark_name, benchmark_func in benchmarks.items():
            print(f"\n🔬 Running {benchmark_name} benchmark...")
            try:
                result = benchmark_func()
                results[benchmark_name] = result
                print(f"   ✅ {benchmark_name}: {result}")
            except Exception as e:
                print(f"   ❌ {benchmark_name} failed: {e}")
                results[benchmark_name] = {"error": str(e)}
        
        # Save benchmark results
        benchmark_file = self.demo_dir / "benchmark_results.json"
        with open(benchmark_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Benchmark results saved to: {benchmark_file}")
        return results
    
    def _benchmark_plugin_execution(self) -> Dict[str, float]:
        """Benchmark plugin execution performance."""
        import time
        
        # Simulate plugin execution timing
        start_time = time.time()
        time.sleep(0.1)  # Simulate plugin work
        execution_time = time.time() - start_time
        
        return {
            "execution_time": execution_time,
            "throughput": 1.0 / execution_time if execution_time > 0 else 0
        }
    
    def _benchmark_workflow_execution(self) -> Dict[str, float]:
        """Benchmark workflow execution performance."""
        import time
        
        # Simulate workflow execution timing
        start_time = time.time()
        time.sleep(0.5)  # Simulate workflow work
        execution_time = time.time() - start_time
        
        return {
            "execution_time": execution_time,
            "throughput": 1.0 / execution_time if execution_time > 0 else 0
        }
    
    def _benchmark_coverage_analysis(self) -> Dict[str, float]:
        """Benchmark coverage analysis performance."""
        import time
        
        # Simulate coverage analysis timing
        start_time = time.time()
        time.sleep(0.2)  # Simulate coverage work
        execution_time = time.time() - start_time
        
        return {
            "analysis_time": execution_time,
            "throughput": 1.0 / execution_time if execution_time > 0 else 0
        }
    
    def show_demo_menu(self):
        """Show interactive demo menu."""
        print("\n🎬 M1 Demo Menu")
        print("=" * 40)
        print("1. Setup demo environment")
        print("2. Run security scan workflow")
        print("3. Run quick scan workflow")
        print("4. Run plugin demos")
        print("5. Run performance benchmark")
        print("6. Show demo status")
        print("0. Exit")
        print("=" * 40)
        
        while True:
            try:
                choice = input("\nEnter your choice (0-6): ").strip()
                
                if choice == "0":
                    print("👋 Goodbye!")
                    break
                elif choice == "1":
                    self.setup_demo_environment()
                elif choice == "2":
                    target = input("Enter target URL (default: https://example.com): ").strip()
                    if not target:
                        target = "https://example.com"
                    self.run_demo_workflow("security_scan", target)
                elif choice == "3":
                    target = input("Enter target URL (default: https://httpbin.org): ").strip()
                    if not target:
                        target = "https://httpbin.org"
                    self.run_demo_workflow("quick_scan", target)
                elif choice == "4":
                    print("\nAvailable plugins:")
                    print("1. http_scanner")
                    print("2. vulnerability_enricher")
                    print("3. report_generator")
                    
                    plugin_choice = input("Select plugin (1-3): ").strip()
                    plugins = ["http_scanner", "vulnerability_enricher", "report_generator"]
                    
                    if plugin_choice in ["1", "2", "3"]:
                        plugin_name = plugins[int(plugin_choice) - 1]
                        self.run_plugin_demo(plugin_name)
                    else:
                        print("Invalid choice")
                elif choice == "5":
                    self.run_performance_benchmark()
                elif choice == "6":
                    self.show_demo_status()
                else:
                    print("Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_demo_status(self):
        """Show demo status."""
        print("\n📊 Demo Status")
        print("=" * 30)
        
        # Check demo directory
        if self.demo_dir.exists():
            print(f"✅ Demo directory: {self.demo_dir}")
            
            # List demo files
            demo_files = list(self.demo_dir.glob("*"))
            if demo_files:
                print("📁 Demo files:")
                for file_path in demo_files:
                    print(f"   • {file_path.name}")
            else:
                print("📁 No demo files found")
        else:
            print("❌ Demo directory not found")
        
        # Check sample plugins
        sample_plugins = ["http_scanner", "vulnerability_enricher", "report_generator"]
        print("\n🔧 Sample plugins:")
        for plugin_name in sample_plugins:
            plugin_dir = self.plugins_dir / plugin_name
            if plugin_dir.exists():
                print(f"   ✅ {plugin_name}")
            else:
                print(f"   ❌ {plugin_name}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="M1 Demo and Sample Usage Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up demo environment")
    
    # Workflow commands
    workflow_parser = subparsers.add_parser("workflow", help="Run demo workflow")
    workflow_parser.add_argument("name", help="Workflow name")
    workflow_parser.add_argument("--target", default="https://example.com", help="Target URL")
    
    # Plugin commands
    plugin_parser = subparsers.add_parser("plugin", help="Run plugin demo")
    plugin_parser.add_argument("name", help="Plugin name")
    plugin_parser.add_argument("--config", help="Plugin configuration (JSON)")
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser("benchmark", help="Run performance benchmark")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show demo status")
    
    # Menu command
    menu_parser = subparsers.add_parser("menu", help="Show interactive demo menu")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    demo = M1DemoTools()
    
    if args.command == "setup":
        demo.setup_demo_environment()
    elif args.command == "workflow":
        demo.run_demo_workflow(args.name, args.target)
    elif args.command == "plugin":
        config = json.loads(args.config) if args.config else None
        demo.run_plugin_demo(args.name, config)
    elif args.command == "benchmark":
        demo.run_performance_benchmark()
    elif args.command == "status":
        demo.show_demo_status()
    elif args.command == "menu":
        demo.show_demo_menu()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
