"""
Workflow Executor - FEAT-044/045/046 Implementation

This module implements the sequential workflow execution engine that takes a validated
workflow recipe (YAML) and runs it step by step, managing state between nodes and
handling errors gracefully.

Key Features:
- FEAT-044: Sequential Workflow Execution Engine
- FEAT-045: State Management Implementation  
- FEAT-046: Error Handling & Recovery

Components:
- WorkflowExecutor: Core execution engine with sequential node execution
- WorkflowState: State management for data passing between nodes
- ExecutionResult: Result object with status and state information
- Error Handling: Graceful error handling with proper cleanup
"""

import yaml
import time
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

# Import existing components
from packages.workflow_engine.executor import (
    PluginLoader, PluginInterface, ExecutionContext, NodeSpec, WorkflowSpec,
    PluginLoadError, WorkflowExecutionError, WorkflowValidationError
)
from packages.storage.adapters.memory import InMemoryStorageAdapter
from packages.runtime_core.storage.storage_port import StoragePort

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """
    State management for workflow execution.
    
    Maintains in-memory state to pass data between workflow nodes.
    Designed to be extensible for future state persistence.
    """
    workflow_id: str
    run_id: str
    project_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in state."""
        self.data[key] = value
        logger.debug(f"State updated: {key} = {type(value).__name__}")
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple values in state."""
        self.data.update(data)
        logger.debug(f"State updated with {len(data)} values")
    
    def has(self, key: str) -> bool:
        """Check if key exists in state."""
        return key in self.data
    
    def keys(self) -> List[str]:
        """Get all state keys."""
        return list(self.data.keys())
    
    def clear(self) -> None:
        """Clear all state data."""
        self.data.clear()
        logger.debug("State cleared")


@dataclass
class ExecutionResult:
    """Result object for workflow execution."""
    status: str  # "success", "error", "partial"
    workflow_id: str
    run_id: str
    state: Optional[WorkflowState] = None
    error: Optional[str] = None
    failed_node: Optional[str] = None
    completed_nodes: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == "success"
    
    @property
    def is_error(self) -> bool:
        """Check if execution failed."""
        return self.status == "error"
    
    @property
    def is_partial(self) -> bool:
        """Check if execution was partially successful."""
        return self.status == "partial"


class WorkflowExecutor:
    """
    Sequential Workflow Execution Engine - FEAT-044 Implementation.
    
    Executes workflow nodes in the defined order, managing state between nodes
    and handling errors gracefully.
    """
    
    def __init__(self, plugin_loader: Optional[PluginLoader] = None, 
                 storage: Optional[StoragePort] = None):
        """Initialize workflow executor."""
        self.plugin_loader = plugin_loader or PluginLoader()
        self.storage = storage or InMemoryStorageAdapter()
        self._execution_history: List[Dict[str, Any]] = []
    
    def execute(self, workflow: Union[WorkflowSpec, Dict[str, Any]], 
                project_id: str = "default_project",
                resume_from: Optional[str] = None) -> ExecutionResult:
        """
        Execute workflow sequentially - FEAT-044 implementation.
        
        Args:
            workflow: Workflow specification or raw workflow data
            project_id: Project ID for findings storage
            resume_from: Node ID to resume from (future feature)
            
        Returns:
            ExecutionResult with status, state, and metadata
        """
        start_time = time.time()
        
        # Convert to WorkflowSpec if needed
        if isinstance(workflow, dict):
            workflow_spec = self._to_workflow_spec(workflow)
        else:
            workflow_spec = workflow
        
        logger.info(f"Starting workflow execution: {workflow_spec.name} ({workflow_spec.id})")
        
        # Initialize state management - FEAT-045
        run_id = f"run_{int(time.time())}"
        state = WorkflowState(
            workflow_id=workflow_spec.id,
            run_id=run_id,
            project_id=project_id
        )
        
        # Get execution order (topological sort)
        try:
            from packages.workflow_engine.executor import validate_workflow
            execution_order = validate_workflow(workflow_spec)
        except WorkflowValidationError as e:
            logger.error(f"Workflow validation failed: {e}")
            return ExecutionResult(
                status="error",
                workflow_id=workflow_spec.id,
                run_id=run_id,
                error=f"Workflow validation failed: {e}",
                execution_time=time.time() - start_time
            )
        
        logger.info(f"Execution order: {execution_order}")
        
        # Execute nodes sequentially - FEAT-044 core loop
        completed_nodes = []
        failed_node = None
        
        try:
            for node_id in execution_order:
                node = next(n for n in workflow_spec.nodes if n.id == node_id)
                
                logger.info(f"Executing node: {node_id} ({node.type})")
                
                # Execute node with error handling - FEAT-046
                result = self._execute_node(node, state, project_id)
                
                if result["status"] == "success":
                    completed_nodes.append(node_id)
                    logger.info(f"Node {node_id} completed successfully")
                else:
                    failed_node = node_id
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Node {node_id} failed: {error_msg}")
                    
                    # Return error result - FEAT-046 error handling
                    return ExecutionResult(
                        status="error",
                        workflow_id=workflow_spec.id,
                        run_id=run_id,
                        state=state,
                        error=error_msg,
                        failed_node=failed_node,
                        completed_nodes=completed_nodes,
                        execution_time=time.time() - start_time
                    )
            
            # Workflow completed successfully
            execution_time = time.time() - start_time
            logger.info(f"Workflow {workflow_spec.id} completed successfully in {execution_time:.2f}s")
            
            return ExecutionResult(
                status="success",
                workflow_id=workflow_spec.id,
                run_id=run_id,
                state=state,
                completed_nodes=completed_nodes,
                execution_time=execution_time,
                metadata={
                    "total_nodes": len(workflow_spec.nodes),
                    "completed_nodes": len(completed_nodes),
                    "final_state_keys": state.keys()
                }
            )
            
        except Exception as e:
            # Unexpected error - FEAT-046 error handling
            execution_time = time.time() - start_time
            logger.error(f"Unexpected workflow execution error: {e}")
            
            return ExecutionResult(
                status="error",
                workflow_id=workflow_spec.id,
                run_id=run_id,
                state=state,
                error=f"Unexpected error: {e}",
                failed_node=failed_node,
                completed_nodes=completed_nodes,
                execution_time=execution_time
            )
    
    def _execute_node(self, node: NodeSpec, state: WorkflowState, 
                     project_id: str) -> Dict[str, Any]:
        """
        Execute a single workflow node - FEAT-044 implementation.
        
        This method implements the core execution logic:
        1. Load plugin using PluginLoader
        2. Prepare inputs from state
        3. Execute plugin
        4. Store outputs in state
        """
        try:
            # Load plugin using PluginLoader - FEAT-044
            plugin = self.plugin_loader.load(node.type)
            
            # Prepare inputs from state - FEAT-045 state management
            inputs = {}
            for input_name in node.requires:
                if state.has(input_name):
                    inputs[input_name] = state.get(input_name)
                    logger.debug(f"Node {node.id} input '{input_name}': {type(inputs[input_name]).__name__}")
                else:
                    logger.warning(f"Node {node.id} missing input '{input_name}'")
                    # For M1, we'll continue with missing inputs
                    # In M2+, this could be an error or default value
            
            # Create execution context
            context = ExecutionContext(
                run_id=state.run_id,
                workflow_id=state.workflow_id,
                project_id=project_id
            )
            
            # Execute plugin - FEAT-044 core execution
            logger.info(f"Executing plugin {node.type} for node {node.id}")
            result = plugin.run(inputs, node.params, context)
            
            # Store outputs in state - FEAT-045 state management
            outputs = result.get("outputs", {})
            for output_name in node.outputs:
                if output_name in outputs:
                    state.set(output_name, outputs[output_name])
                    logger.debug(f"Node {node.id} output '{output_name}': {type(outputs[output_name]).__name__}")
                else:
                    logger.warning(f"Node {node.id} missing output '{output_name}'")
            
            # Save findings to storage
            findings = result.get("findings", [])
            for finding in findings:
                try:
                    self.storage.save_finding(finding)
                    logger.debug(f"Saved finding {finding.get('id')} to storage")
                except Exception as e:
                    logger.error(f"Failed to save finding {finding.get('id')}: {e}")
            
            return {
                "status": "success",
                "outputs": outputs,
                "findings": findings
            }
            
        except PluginLoadError as e:
            logger.error(f"Plugin load error for node {node.id}: {e}")
            return {
                "status": "error",
                "error": f"Plugin load error: {e}"
            }
            
        except Exception as e:
            logger.error(f"Plugin execution error for node {node.id}: {e}")
            return {
                "status": "error",
                "error": f"Plugin execution error: {e}"
            }
    
    def _to_workflow_spec(self, workflow_data: Dict[str, Any]) -> WorkflowSpec:
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
            for n in workflow_data["nodes"]
        ]
        return WorkflowSpec(
            id=workflow_data.get("id", f"workflow_{int(time.time())}"),
            name=workflow_data.get("name", "Unnamed Workflow"),
            description=workflow_data.get("description", ""),
            nodes=nodes
        )
    
    def load_workflow_from_yaml(self, yaml_path: str) -> WorkflowSpec:
        """Load workflow from YAML file."""
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            return self._to_workflow_spec(data)
        except Exception as e:
            logger.error(f"Failed to load workflow from {yaml_path}: {e}")
            raise
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history for debugging/monitoring."""
        return self._execution_history.copy()
    
    def clear_execution_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    executor = WorkflowExecutor()
    
    # Load sample workflow
    try:
        workflow = executor.load_workflow_from_yaml("workflows/sample-linear.yaml")
        print(f"Loaded workflow: {workflow.name}")
        
        # Execute workflow
        result = executor.execute(workflow, project_id="test_project")
        
        print(f"Execution result: {result.status}")
        if result.is_success:
            print(f"Completed nodes: {result.completed_nodes}")
            print(f"Final state keys: {result.state.keys()}")
            print(f"Execution time: {result.execution_time:.2f}s")
        else:
            print(f"Error: {result.error}")
            print(f"Failed at node: {result.failed_node}")
            
    except Exception as e:
        print(f"Error: {e}")
