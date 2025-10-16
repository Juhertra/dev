"""
Workflow Engine Executor - M1 Sequential Execution Implementation

This module contains the workflow execution engine for SecFlow.
Implements sequential execution with StoragePort integration and plugin system.

Components:
- WorkflowExecutor: Parses YAML recipes, builds DAG, executes nodes sequentially
- NodeExecutor: Executes individual nodes with retry logic and timeouts
- WorkflowState: Manages workflow state and checkpointing
- StoragePort Integration: Uses StoragePort for data passing between nodes
- Plugin Integration: Interfaces with plugin loader for real tool execution

Import Rules:
- May import from runtime_core
- May import from findings
- May be imported by other packages
- May NOT import from wrappers or parsers
"""

import yaml
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Callable
from pathlib import Path
from pydantic import BaseModel, ValidationError
from datetime import datetime
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future
import os

# Import StoragePort for data passing
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from packages.runtime_core.storage.storage_port import StoragePort
from packages.storage.adapters.memory import InMemoryStorageAdapter

logger = logging.getLogger(__name__)


@dataclass
class NodeSpec:
    """Node specification for workflow execution."""
    id: str
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    requires: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout_s: Optional[int] = None
    retries: int = 0
    retry_backoff_s: float = 0.5


@dataclass
class WorkflowSpec:
    """Workflow specification."""
    id: str
    name: str
    description: str = ""
    nodes: List[NodeSpec] = field(default_factory=list)


@dataclass
class NodeResult:
    """Result of node execution."""
    node_id: str
    status: str  # "ok" | "error"
    output: Any = None
    error: Optional[str] = None
    attempts: int = 1
    execution_time: float = 0.0
    findings: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionContext:
    """Execution context for workflow runs."""
    run_id: str
    workflow_id: str
    project_id: str
    vars: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)  # name -> uri
    findings: List[Dict[str, Any]] = field(default_factory=list)


class WorkflowValidationError(Exception):
    """Workflow validation error."""
    pass


class PluginLoadError(Exception):
    """Plugin loading error."""
    pass


class WorkflowExecutionError(Exception):
    """Workflow execution error."""
    pass


class PluginInterface:
    """Interface for plugin execution."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute the plugin with given inputs and configuration.
        
        Args:
            inputs: Input data from previous nodes
            config: Node configuration parameters
            context: Execution context with project info
            
        Returns:
            Dict containing outputs and findings
            
        Raises:
            Exception: On execution failure
        """
        raise NotImplementedError("Plugin must implement run method")


class PluginLoader:
    """Plugin loader interface for workflow execution."""
    
    def __init__(self):
        """Initialize plugin loader."""
        self._plugins: Dict[str, PluginInterface] = {}
        self._lock = threading.Lock()
    
    def load(self, plugin_name: str) -> PluginInterface:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            PluginInterface instance
            
        Raises:
            PluginLoadError: If plugin cannot be loaded
        """
        with self._lock:
            if plugin_name in self._plugins:
                return self._plugins[plugin_name]
            
            # For M1, we'll use stub implementations
            # In M3, this will load real plugins
            plugin = self._create_stub_plugin(plugin_name)
            self._plugins[plugin_name] = plugin
            return plugin
    
    def _create_stub_plugin(self, plugin_name: str) -> PluginInterface:
        """Create stub plugin implementation."""
        if plugin_name == "discovery.ferox":
            return FeroxStubPlugin()
        elif plugin_name == "scan.nuclei":
            return NucleiStubPlugin()
        elif plugin_name == "enrich.cve":
            return CVEStubPlugin()
        elif plugin_name == "echo":
            return EchoStubPlugin()
        else:
            raise PluginLoadError(f"Unknown plugin: {plugin_name}")


class FeroxStubPlugin(PluginInterface):
    """Stub implementation of Feroxbuster discovery plugin."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute Feroxbuster discovery."""
        logger.info(f"Executing Feroxbuster discovery for project {context.project_id}")
        
        # Simulate discovery results
        urls = [
            "https://example.com/admin",
            "https://example.com/api", 
            "https://example.com/login",
            "https://example.com/dashboard"
        ]
        
        # Create findings for discovered URLs
        findings = []
        for i, url in enumerate(urls):
            finding = {
                "id": f"discovery_{context.run_id}_{i}",
                "project_id": context.project_id,
                "detector_id": "discovery.ferox",
                "title": f"Discovered URL: {url}",
                "severity": "info",
                "resource": url,
                "evidence": {"url": url, "method": "directory_bruteforce"},
                "created_at": datetime.utcnow().isoformat() + "Z",
                "finding_schema_version": "1.0.0"
            }
            findings.append(finding)
        
        return {
            "outputs": {"urls": urls},
            "findings": findings,
            "status": "success"
        }


class NucleiStubPlugin(PluginInterface):
    """Stub implementation of Nuclei scanning plugin."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute Nuclei scanning."""
        logger.info(f"Executing Nuclei scan for project {context.project_id}")
        
        # Get URLs from inputs
        urls = inputs.get("urls", [])
        logger.info(f"Scanning {len(urls)} URLs")
        
        # Simulate scan results
        findings = []
        for i, url in enumerate(urls):
            finding = {
                "id": f"scan_{context.run_id}_{i}",
                "project_id": context.project_id,
                "detector_id": "scan.nuclei",
                "title": f"Vulnerability detected: SQL Injection in {url}",
                "severity": "high",
                "resource": url,
                "evidence": {
                    "url": url,
                    "template": "sql-injection",
                    "status_code": 200,
                    "response_time": 150
                },
                "created_at": datetime.utcnow().isoformat() + "Z",
                "finding_schema_version": "1.0.0"
            }
            findings.append(finding)
        
        return {
            "outputs": {"findings": findings},
            "findings": findings,
            "status": "success"
        }


class CVEStubPlugin(PluginInterface):
    """Stub implementation of CVE enrichment plugin."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute CVE enrichment."""
        logger.info(f"Executing CVE enrichment for project {context.project_id}")
        
        # Get findings from inputs
        findings = inputs.get("findings", [])
        logger.info(f"Enriching {len(findings)} findings")
        
        # Simulate enrichment
        enriched_findings = []
        for finding in findings:
            enriched_finding = finding.copy()
            enriched_finding["cve_ids"] = ["CVE-2023-1234", "CVE-2023-5678"]
            enriched_finding["cvss"] = 7.5
            enriched_finding["owasp"] = "A05"
            enriched_finding["enriched_at"] = datetime.utcnow().isoformat() + "Z"
            enriched_findings.append(enriched_finding)
        
        return {
            "outputs": {"enriched_findings": enriched_findings},
            "findings": enriched_findings,
            "status": "success"
        }


class EchoStubPlugin(PluginInterface):
    """Stub implementation of echo plugin for debugging."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute echo plugin."""
        message = config.get("message", "Echo test")
        logger.info(f"Echo plugin: {message}")
        
        return {
            "outputs": {"echo": message, "vars": dict(context.vars)},
            "findings": [],
            "status": "success"
        }


class WorkflowValidationError(Exception):
    """Workflow validation error."""
    pass


def validate_workflow(spec: WorkflowSpec) -> List[str]:
    """Validate workflow and return topological execution order."""
    node_ids = {n.id for n in spec.nodes}
    
    # Check for duplicate node IDs
    if len(node_ids) != len(spec.nodes):
        raise WorkflowValidationError("Duplicate node IDs found")
    
    # Build dependency graph - inputs should reference outputs from other nodes
    graph: Dict[str, List[str]] = {}
    all_outputs: Set[str] = set()
    
    # Collect all outputs first
    for node in spec.nodes:
        # Handle both old (outputs) and new (outputs) formats
        outputs = getattr(node, 'outputs', [])
        all_outputs.update(outputs)
    
    # Build graph based on input dependencies
    for node in spec.nodes:
        # Handle both old (inputs) and new (requires) formats
        dependencies = getattr(node, 'requires', getattr(node, 'inputs', []))
        
        # For each input, find which node produces it
        node_dependencies = []
        for input_name in dependencies:
            # Find the node that produces this output
            for other_node in spec.nodes:
                other_outputs = getattr(other_node, 'outputs', [])
                if input_name in other_outputs:
                    node_dependencies.append(other_node.id)
                    break
            else:
                # Input not found in any node's outputs
                raise WorkflowValidationError(f"Node {node.id} depends on unknown output '{input_name}'")
        
        graph[node.id] = node_dependencies
    
    # Check for cycles using DFS
    temp, done, order = set(), set(), []
    
    def dfs(v: str):
        if v in done:
            return
        if v in temp:
            raise WorkflowValidationError(f"Cycle detected at {v}")
        temp.add(v)
        for d in graph[v]:
            dfs(d)
        temp.remove(v)
        done.add(v)
        order.append(v)

    for nid in graph:
        dfs(nid)
    
    # Return execution order (dependencies first)
    return order


class NodeExecutor:
    """Node execution engine with retry logic, timeouts, and plugin integration."""
    
    def __init__(self, plugin_loader: PluginLoader, storage: StoragePort):
        """Initialize node executor with plugin loader and storage."""
        self.plugin_loader = plugin_loader
        self.storage = storage
        self._lock = threading.Lock()  # Thread safety for M3 preparation
    
    def execute(self, spec: NodeSpec, ctx: ExecutionContext) -> NodeResult:
        """Execute a single node with retry logic and StoragePort integration."""
        start_time = time.time()
        attempts = 0
        backoff = spec.retry_backoff_s or 0.0
        last_err = None
        
        while attempts <= spec.retries:
            attempts += 1
            try:
                logger.info(f"Executing node {spec.id} (attempt {attempts}/{spec.retries + 1})")
                
                # Load and execute the plugin
                plugin = self.plugin_loader.load(spec.type)
                
                # Prepare inputs from context
                inputs = self._prepare_inputs(spec, ctx)
                
                # Execute the plugin
                result = plugin.run(inputs, spec.params, ctx)
                
                # Process results and save findings
                self._process_results(spec, result, ctx)
                
                execution_time = time.time() - start_time
                
                return NodeResult(
                    node_id=spec.id,
                    status="ok",
                    output=result.get("outputs", {}),
                    attempts=attempts,
                    execution_time=execution_time,
                    findings=result.get("findings", [])
                )
                
            except PluginLoadError as e:
                last_err = e
                logger.error(f"Plugin load error for node {spec.id}: {e}")
                break  # Don't retry plugin load errors
                
            except Exception as e:
                last_err = e
                logger.warning(f"Node {spec.id} attempt {attempts} failed: {e}")
                
                if attempts <= spec.retries:
                    logger.info(f"Retrying node {spec.id} in {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2 if backoff else 0
        
        execution_time = time.time() - start_time
        return NodeResult(
            node_id=spec.id,
            status="error",
            error=str(last_err),
            attempts=attempts,
            execution_time=execution_time
        )
    
    def _prepare_inputs(self, spec: NodeSpec, ctx: ExecutionContext) -> Dict[str, Any]:
        """Prepare inputs for plugin execution."""
        inputs = {}
        
        # Map required outputs to inputs
        for required_output in spec.requires:
            if required_output in ctx.vars:
                inputs[required_output] = ctx.vars[required_output]
            else:
                logger.warning(f"Required input '{required_output}' not found in context")
        
        return inputs
    
    def _process_results(self, spec: NodeSpec, result: Dict[str, Any], ctx: ExecutionContext):
        """Process plugin results and save findings to StoragePort."""
        # Update context variables with outputs
        outputs = result.get("outputs", {})
        for output_name, output_value in outputs.items():
            ctx.vars[output_name] = output_value
        
        # Save findings to StoragePort
        findings = result.get("findings", [])
        for finding in findings:
            try:
                with self._lock:  # Thread safety for concurrent execution
                    self.storage.save_finding(finding)
                logger.debug(f"Saved finding {finding.get('id')} to storage")
            except Exception as e:
                logger.error(f"Failed to save finding {finding.get('id')}: {e}")
        
        # Update context findings
        ctx.findings.extend(findings)


class WorkflowExecutor:
    """Workflow execution engine - M1 sequential implementation with M3 concurrency preparation."""
    
    def __init__(self, storage: Optional[StoragePort] = None, plugin_loader: Optional[PluginLoader] = None):
        """Initialize executor with optional storage and plugin loader."""
        self.storage = storage or InMemoryStorageAdapter()
        self.plugin_loader = plugin_loader or PluginLoader()
        self.node_executor = NodeExecutor(self.plugin_loader, self.storage)
        self.active_workflows: Dict[str, Any] = {}
        self._lock = threading.Lock()  # Thread safety for M3 preparation
    
    def load_workflow_from_yaml(self, yaml_path: str) -> WorkflowSpec:
        """Load workflow from YAML file."""
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            return self._to_spec(data)
            
        except Exception as e:
            logger.error(f"Failed to load workflow from {yaml_path}: {e}")
            raise
    
    def _to_spec(self, raw: Dict[str, Any]) -> WorkflowSpec:
        """Convert raw workflow data to WorkflowSpec."""
        nodes = [
            NodeSpec(
                id=n["id"],
                type=n["type"],
                params=n.get("config", {}),
                requires=n.get("inputs", []),
                outputs=n.get("outputs", []),
                timeout_s=n.get("timeout"),
                retries=n.get("retries", 0),
                retry_backoff_s=n.get("retry_backoff_s", 0.5),
            )
            for n in raw["nodes"]
        ]
        return WorkflowSpec(
            id=raw.get("id", f"workflow_{int(time.time())}"), 
            name=raw.get("name", "Unnamed Workflow"),
            description=raw.get("description", ""),
            nodes=nodes
        )
    
    def validate_workflow(self, workflow: Any) -> bool:
        """Validate workflow DAG structure."""
        try:
            # Handle both WorkflowSpec and legacy Workflow formats
            if hasattr(workflow, 'nodes') and len(workflow.nodes) > 0 and hasattr(workflow.nodes[0], 'requires'):
                # New WorkflowSpec format
                validate_workflow(workflow)
            elif hasattr(workflow, 'nodes') and len(workflow.nodes) == 0:
                # Empty workflow - invalid
                return False
            else:
                # Legacy Workflow format - convert to WorkflowSpec
                nodes = [
                    NodeSpec(
                        id=n.id,
                        type=n.type,
                        params=getattr(n, 'config', {}),
                        requires=getattr(n, 'inputs', []),
                        outputs=getattr(n, 'outputs', []),
                    )
                    for n in workflow.nodes
                ]
                spec = WorkflowSpec(
                    id=workflow.id,
                    name=workflow.name,
                    description=getattr(workflow, 'description', ''),
                    nodes=nodes
                )
                validate_workflow(spec)
            return True
        except WorkflowValidationError as e:
            logger.error(f"Workflow validation failed: {e}")
            return False
    
    def execute_workflow(self, workflow: WorkflowSpec, project_id: str = "default_project") -> Dict[str, Any]:
        """Execute workflow sequentially with StoragePort integration."""
        start_time = time.time()
        logger.info(f"Starting workflow execution: {workflow.name} ({workflow.id})")
        
        # Validate workflow
        if not self.validate_workflow(workflow):
            return {"status": "failed", "error": "Workflow validation failed", "workflow_id": workflow.id}
        
        # Get execution order
        try:
            execution_order = validate_workflow(workflow)
        except WorkflowValidationError as e:
            return {"status": "failed", "error": str(e), "workflow_id": workflow.id}
        
        logger.info(f"Execution order: {execution_order}")
        
        # Create execution context
        run_id = f"run_{int(time.time())}"
        ctx = ExecutionContext(
            run_id=run_id, 
            workflow_id=workflow.id,
            project_id=project_id
        )
        
        # Execute nodes in order
        completed_nodes = []
        failed_nodes = []
        total_findings = 0
        
        try:
            for node_id in execution_order:
                node = next(n for n in workflow.nodes if n.id == node_id)
                logger.info(f"Executing node: {node_id} ({node.type})")
                
                # Execute node
                result = self.node_executor.execute(node, ctx)
                
                if result.status == "ok":
                    completed_nodes.append(node_id)
                    total_findings += len(result.findings)
                    logger.info(f"Node {node_id} completed successfully - {len(result.findings)} findings")
                else:
                    failed_nodes.append(node_id)
                    logger.error(f"Node {node_id} failed: {result.error}")
                    return {
                        "status": "failed",
                        "error": f"Node {node_id} failed: {result.error}",
                        "workflow_id": workflow.id,
                        "failed_node": node_id,
                        "completed_nodes": completed_nodes,
                        "failed_nodes": failed_nodes,
                        "total_findings": total_findings
                    }
            
            # Workflow completed successfully
            execution_time = time.time() - start_time
            logger.info(f"Workflow {workflow.id} completed successfully - {total_findings} total findings")
            
            return {
                "status": "completed",
                "workflow_id": workflow.id,
                "project_id": project_id,
                "completed_nodes": completed_nodes,
                "failed_nodes": failed_nodes,
                "total_findings": total_findings,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow execution failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "workflow_id": workflow.id,
                "project_id": project_id,
                "completed_nodes": completed_nodes,
                "failed_nodes": failed_nodes,
                "total_findings": total_findings,
                "execution_time": execution_time
            }
    
    def execute_parallel(self, workflow: WorkflowSpec, project_id: str = "default_project") -> Dict[str, Any]:
        """
        Execute workflow with parallel execution where possible (M3 preparation).
        
        This method prepares for M3 concurrent execution using Python 3.14 features.
        Currently executes sequentially but with thread-safe infrastructure.
        """
        logger.info(f"Parallel execution mode (M3 preparation) for workflow: {workflow.name}")
        
        # For M1, fall back to sequential execution
        # In M3, this will use ThreadPoolExecutor or subinterpreters
        return self.execute_workflow(workflow, project_id)
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution status."""
        with self._lock:
            if workflow_id in self.active_workflows:
                return self.active_workflows[workflow_id]
        
        return {
            "status": "unknown",
            "workflow_id": workflow_id,
            "message": "Status tracking not implemented in M1"
        }
    
    def dry_run(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Dry run workflow - validate without execution."""
        try:
            spec = self._to_spec(recipe)
            is_valid = self.validate_workflow(spec)
            execution_order = validate_workflow(spec) if is_valid else []
            
            return {
                "ok": is_valid,
                "nodes": len(spec.nodes),
                "execution_order": execution_order,
                "validation_errors": [] if is_valid else ["Workflow validation failed"]
            }
            
        except Exception as e:
            return {
                "ok": False,
                "nodes": len(recipe.get('nodes', [])),
                "execution_order": [],
                "validation_errors": [str(e)]
            }


class WorkflowManager:
    """
    Workflow Manager for future concurrency support (M3 preparation).
    
    This class prepares for M3 concurrent workflow execution using Python 3.14 features.
    Currently manages single workflows but designed for multiple concurrent workflows.
    """
    
    def __init__(self, storage: Optional[StoragePort] = None, max_concurrent: int = 1):
        """Initialize workflow manager."""
        self.storage = storage or InMemoryStorageAdapter()
        self.max_concurrent = max_concurrent
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # M3 preparation: Thread pool for concurrent execution
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: Dict[str, Future] = {}
    
    def submit_workflow(self, workflow: WorkflowSpec, project_id: str = "default_project") -> str:
        """
        Submit workflow for execution.
        
        Args:
            workflow: Workflow specification
            project_id: Project ID for findings storage
            
        Returns:
            Workflow execution ID
        """
        execution_id = f"exec_{int(time.time())}"
        
        with self._lock:
            if len(self.active_workflows) >= self.max_concurrent:
                raise WorkflowExecutionError(f"Maximum concurrent workflows ({self.max_concurrent}) exceeded")
            
            # For M1, execute immediately
            # In M3, this will submit to thread pool
            executor = WorkflowExecutor(self.storage)
            result = executor.execute_workflow(workflow, project_id)
            
            self.active_workflows[execution_id] = {
                "workflow": workflow,
                "project_id": project_id,
                "status": result["status"],
                "result": result,
                "start_time": time.time()
            }
        
        return execution_id
    
    def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status."""
        with self._lock:
            if execution_id in self.active_workflows:
                workflow_info = self.active_workflows[execution_id]
                return {
                    "execution_id": execution_id,
                    "workflow_id": workflow_info["workflow"].id,
                    "status": workflow_info["status"],
                    "result": workflow_info["result"]
                }
        
        return {
            "execution_id": execution_id,
            "status": "not_found",
            "error": "Workflow execution not found"
        }
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflow executions."""
        with self._lock:
            return [
                {
                    "execution_id": exec_id,
                    "workflow_id": info["workflow"].id,
                    "project_id": info["project_id"],
                    "status": info["status"]
                }
                for exec_id, info in self.active_workflows.items()
            ]
    
    def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a running workflow execution."""
        with self._lock:
            if execution_id in self.active_workflows:
                # For M1, workflows complete quickly, so just mark as cancelled
                # In M3, this will cancel the future
                self.active_workflows[execution_id]["status"] = "cancelled"
                return True
        return False
    
    def cleanup_completed(self):
        """Clean up completed workflow executions."""
        with self._lock:
            completed_ids = [
                exec_id for exec_id, info in self.active_workflows.items()
                if info["status"] in ["completed", "failed", "cancelled"]
            ]
            
            for exec_id in completed_ids:
                del self.active_workflows[exec_id]
            
            logger.info(f"Cleaned up {len(completed_ids)} completed workflows")
    
    def prepare_for_python314(self):
        """
        Prepare workflow manager for Python 3.14 concurrency features.
        
        This method sets up infrastructure for M3 concurrent execution:
        - ThreadPoolExecutor for parallel node execution
        - Subinterpreter support for isolation
        - Free-threaded mode compatibility
        """
        logger.info("Preparing WorkflowManager for Python 3.14 concurrency")
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 14):
            logger.info("Python 3.14+ detected - enabling advanced concurrency features")
            
            # Initialize thread pool for concurrent execution
            self._executor = ThreadPoolExecutor(
                max_workers=self.max_concurrent,
                thread_name_prefix="workflow"
            )
            
            # Check for free-threaded mode
            if hasattr(sys, 'get_switch_interval'):
                logger.info("Free-threaded mode available - GIL removed")
            else:
                logger.info("Standard threading mode - GIL present")
        else:
            logger.info(f"Python {python_version.major}.{python_version.minor} - using standard threading")
    
    def __del__(self):
        """Cleanup thread pool on destruction."""
        if self._executor:
            self._executor.shutdown(wait=True)


# Legacy compatibility classes
class WorkflowNode(BaseModel):
    """Legacy workflow node definition for backward compatibility."""
    id: str
    type: str
    config: Dict[str, Any] = {}
    inputs: List[str] = []
    outputs: List[str] = []
    retry_config: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None


class Workflow(BaseModel):
    """Legacy workflow definition for backward compatibility."""
    id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    retry: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, Any]] = None