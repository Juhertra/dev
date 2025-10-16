"""
Recipe Validator - Enhanced M1 Implementation

This module provides comprehensive validation for workflow recipes.
Implements schema validation, DAG validation, and reference consistency checks.

Import Rules:
- May import from runtime_core
- May import from findings
- May be imported by other packages
- May NOT import from wrappers or parsers
"""

import yaml
import logging
from typing import Dict, Any, List, Set, Optional
from pathlib import Path
from pydantic import BaseModel, ValidationError, Field
import jsonschema


logger = logging.getLogger(__name__)


class RecipeValidationError(Exception):
    """Recipe validation error."""
    pass


class NodeValidationError(RecipeValidationError):
    """Node-specific validation error."""
    pass


class DAGValidationError(RecipeValidationError):
    """DAG structure validation error."""
    pass


class ReferenceValidationError(RecipeValidationError):
    """Reference consistency validation error."""
    pass


class WorkflowNode(BaseModel):
    """Validated workflow node."""
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)


class RetryConfig(BaseModel):
    """Retry configuration validation."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0)
    base_delay: float = Field(default=5.0, ge=0.0, le=300.0)


class StateConfig(BaseModel):
    """State management configuration validation."""
    checkpoint_interval: int = Field(default=30, ge=0, le=3600)
    resume_on_failure: bool = Field(default=True)
    cache_intermediate: bool = Field(default=True)


class Workflow(BaseModel):
    """Validated workflow definition."""
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    nodes: List[WorkflowNode] = Field(..., min_length=1)
    retry: Optional[RetryConfig] = None
    state: Optional[StateConfig] = None


class RecipeValidator:
    """Comprehensive recipe validator with enhanced validation logic."""
    
    def __init__(self):
        """Initialize the recipe validator."""
        self.logger = logging.getLogger(__name__)
    
    def validate(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a workflow recipe comprehensively."""
        validation_results = {
            "ok": False,
            "errors": [],
            "warnings": [],
            "nodes": 0,
            "execution_order": [],
            "validation_details": {}
        }
        
        try:
            # Step 1: Schema validation
            self._validate_schema(recipe)
            validation_results["validation_details"]["schema"] = "passed"
            
            # Step 2: Pydantic model validation
            workflow = self._validate_pydantic_model(recipe)
            validation_results["nodes"] = len(workflow.nodes)
            validation_results["validation_details"]["pydantic"] = "passed"
            
            # Step 3: DAG structure validation
            execution_order = self._validate_dag_structure(workflow)
            validation_results["execution_order"] = execution_order
            validation_results["validation_details"]["dag"] = "passed"
            
            # Step 4: Reference consistency validation
            self._validate_references(workflow)
            validation_results["validation_details"]["references"] = "passed"
            
            # Step 5: Node type validation
            self._validate_node_types(workflow)
            validation_results["validation_details"]["node_types"] = "passed"
            
            # Step 6: Configuration validation
            self._validate_configurations(workflow)
            validation_results["validation_details"]["configurations"] = "passed"
            
            validation_results["ok"] = True
            validation_results["workflow_name"] = workflow.name
            
        except RecipeValidationError as e:
            validation_results["errors"].append(str(e))
            self.logger.error(f"Recipe validation failed: {e}")
            
        except Exception as e:
            validation_results["errors"].append(f"Unexpected validation error: {e}")
            self.logger.error(f"Unexpected validation error: {e}")
        
        return validation_results
    
    def validate_file(self, recipe_path: str) -> Dict[str, Any]:
        """Validate a recipe from a YAML file."""
        try:
            with open(recipe_path, 'r') as f:
                recipe_data = yaml.safe_load(f)
            
            result = self.validate(recipe_data)
            result["file_path"] = recipe_path
            return result
            
        except FileNotFoundError:
            return {
                "ok": False,
                "errors": [f"Recipe file not found: {recipe_path}"],
                "file_path": recipe_path
            }
        except yaml.YAMLError as e:
            return {
                "ok": False,
                "errors": [f"YAML parsing error: {e}"],
                "file_path": recipe_path
            }
        except Exception as e:
            return {
                "ok": False,
                "errors": [f"File reading error: {e}"],
                "file_path": recipe_path
            }
    
    def _validate_schema(self, recipe: Dict[str, Any]) -> None:
        """Validate basic schema structure."""
        required_fields = ["version", "name", "nodes"]
        missing_fields = [field for field in required_fields if field not in recipe]
        
        if missing_fields:
            raise RecipeValidationError(f"Missing required fields: {missing_fields}")
        
        if not isinstance(recipe["nodes"], list):
            raise RecipeValidationError("'nodes' must be a list")
        
        if len(recipe["nodes"]) == 0:
            raise RecipeValidationError("Workflow must have at least one node")
    
    def _validate_pydantic_model(self, recipe: Dict[str, Any]) -> Workflow:
        """Validate using Pydantic models."""
        try:
            workflow = Workflow(**recipe)
            return workflow
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"{field}: {message}")
            
            raise RecipeValidationError(f"Pydantic validation failed: {'; '.join(error_messages)}")
    
    def _validate_dag_structure(self, workflow: Workflow) -> List[str]:
        """Validate DAG structure and return execution order."""
        node_ids = {node.id for node in workflow.nodes}
        
        # Check for duplicate node IDs
        if len(node_ids) != len(workflow.nodes):
            raise DAGValidationError("Duplicate node IDs found")
        
        # Build dependency graph - inputs should reference outputs from other nodes
        graph: Dict[str, List[str]] = {}
        all_outputs: Set[str] = set()
        
        # Collect all outputs first
        for node in workflow.nodes:
            all_outputs.update(node.outputs)
        
        # Build graph based on input dependencies
        for node in workflow.nodes:
            # For each input, find which node produces it
            dependencies = []
            for input_name in node.inputs:
                # Find the node that produces this output
                for other_node in workflow.nodes:
                    if input_name in other_node.outputs:
                        dependencies.append(other_node.id)
                        break
                else:
                    # Input not found in any node's outputs
                    raise DAGValidationError(f"Node '{node.id}' depends on unknown output '{input_name}'")
            
            graph[node.id] = dependencies
        
        # Check for cycles using DFS
        temp: Set[str] = set()
        done: Set[str] = set()
        execution_order: List[str] = []
        
        def dfs(node_id: str) -> None:
            if node_id in done:
                return
            if node_id in temp:
                raise DAGValidationError(f"Cycle detected involving node '{node_id}'")
            
            temp.add(node_id)
            for dep in graph[node_id]:
                dfs(dep)
            temp.remove(node_id)
            done.add(node_id)
            execution_order.append(node_id)
        
        for node_id in graph:
            dfs(node_id)
        
        return execution_order
    
    def _validate_references(self, workflow: Workflow) -> None:
        """Validate input/output reference consistency."""
        # Collect all outputs
        all_outputs: Set[str] = set()
        for node in workflow.nodes:
            all_outputs.update(node.outputs)
        
        # Check that all inputs have corresponding outputs
        for node in workflow.nodes:
            missing_outputs = set(node.inputs) - all_outputs
            if missing_outputs:
                raise ReferenceValidationError(
                    f"Node '{node.id}' references non-existent outputs: {sorted(missing_outputs)}"
                )
        
        # Check for duplicate output names
        output_counts: Dict[str, int] = {}
        for node in workflow.nodes:
            for output in node.outputs:
                output_counts[output] = output_counts.get(output, 0) + 1
        
        duplicate_outputs = [output for output, count in output_counts.items() if count > 1]
        if duplicate_outputs:
            raise ReferenceValidationError(f"Duplicate output names found: {duplicate_outputs}")
    
    def _validate_node_types(self, workflow: Workflow) -> None:
        """Validate node types against known types."""
        known_types = {
            "discovery.ferox",
            "discovery.katana", 
            "scan.nuclei",
            "scan.nmap",
            "enrich.cve",
            "enrich.owasp",
            "filter.severity",
            "filter.false_positive",
            "analysis.correlation",
            "echo"
        }
        
        unknown_types = []
        for node in workflow.nodes:
            if node.type not in known_types:
                unknown_types.append(f"'{node.id}': {node.type}")
        
        if unknown_types:
            self.logger.warning(f"Unknown node types found: {unknown_types}")
            # Don't fail validation for unknown types in M1, just warn
    
    def _validate_configurations(self, workflow: Workflow) -> None:
        """Validate node configurations."""
        for node in workflow.nodes:
            # Validate discovery.ferox config
            if node.type == "discovery.ferox":
                self._validate_ferox_config(node)
            
            # Validate scan.nuclei config
            elif node.type == "scan.nuclei":
                self._validate_nuclei_config(node)
            
            # Validate enrich.cve config
            elif node.type == "enrich.cve":
                self._validate_cve_config(node)
    
    def _validate_ferox_config(self, node: WorkflowNode) -> None:
        """Validate feroxbuster configuration."""
        config = node.config
        
        # Check required fields
        if "wordlist" not in config:
            raise NodeValidationError(f"Node '{node.id}': feroxbuster requires 'wordlist' config")
        
        # Validate wordlist format
        wordlist = config["wordlist"]
        if not isinstance(wordlist, str):
            raise NodeValidationError(f"Node '{node.id}': 'wordlist' must be a string")
        
        # Validate optional fields
        if "threads" in config:
            threads = config["threads"]
            if not isinstance(threads, int) or threads < 1 or threads > 100:
                raise NodeValidationError(f"Node '{node.id}': 'threads' must be integer 1-100")
        
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
                raise NodeValidationError(f"Node '{node.id}': 'timeout' must be integer 1-3600")
    
    def _validate_nuclei_config(self, node: WorkflowNode) -> None:
        """Validate nuclei configuration."""
        config = node.config
        
        # Check required fields
        if "templates" not in config:
            raise NodeValidationError(f"Node '{node.id}': nuclei requires 'templates' config")
        
        # Validate templates format
        templates = config["templates"]
        if not isinstance(templates, str):
            raise NodeValidationError(f"Node '{node.id}': 'templates' must be a string")
        
        # Validate optional fields
        if "rate_limit" in config:
            rate_limit = config["rate_limit"]
            if not isinstance(rate_limit, int) or rate_limit < 1 or rate_limit > 1000:
                raise NodeValidationError(f"Node '{node.id}': 'rate_limit' must be integer 1-1000")
    
    def _validate_cve_config(self, node: WorkflowNode) -> None:
        """Validate CVE enrichment configuration."""
        config = node.config
        
        # Validate sources
        if "sources" in config:
            sources = config["sources"]
            if not isinstance(sources, list):
                raise NodeValidationError(f"Node '{node.id}': 'sources' must be a list")
            
            valid_sources = {"nvd", "osv", "exploitdb", "cve-mitre"}
            invalid_sources = set(sources) - valid_sources
            if invalid_sources:
                raise NodeValidationError(f"Node '{node.id}': invalid sources: {invalid_sources}")
    
    def create_test_recipe(self, recipe_type: str = "linear") -> Dict[str, Any]:
        """Create a test recipe for validation testing."""
        if recipe_type == "linear":
            return {
                "version": "1.0",
                "name": "Test Linear Workflow",
                "description": "Test workflow for validation",
                "nodes": [
                    {
                        "id": "discovery",
                        "type": "discovery.ferox",
                        "config": {
                            "wordlist": "res://wordlists/dirb:latest",
                            "threads": 50,
                            "timeout": 300
                        },
                        "outputs": ["urls"]
                    },
                    {
                        "id": "scan",
                        "type": "scan.nuclei",
                        "inputs": ["urls"],
                        "config": {
                            "templates": "res://templates/owasp-top10:latest",
                            "rate_limit": 150,
                            "timeout": 600
                        },
                        "outputs": ["findings"]
                    },
                    {
                        "id": "enrich",
                        "type": "enrich.cve",
                        "inputs": ["findings"],
                        "config": {
                            "sources": ["nvd", "osv", "exploitdb"],
                            "timeout": 120
                        },
                        "outputs": ["enriched_findings"]
                    }
                ],
                "retry": {
                    "max_attempts": 3,
                    "backoff_factor": 2.0,
                    "base_delay": 5.0
                },
                "state": {
                    "checkpoint_interval": 30,
                    "resume_on_failure": True,
                    "cache_intermediate": True
                }
            }
        elif recipe_type == "invalid":
            return {
                "version": "1.0",
                "name": "Invalid Test Workflow",
                "nodes": [
                    {
                        "id": "node1",
                        "type": "unknown.type",
                        "inputs": ["nonexistent_output"],
                        "outputs": ["output1"]
                    }
                ]
            }
        else:
            raise ValueError(f"Unknown recipe type: {recipe_type}")


# Legacy compatibility functions
def validate_recipe_file(recipe_path: str) -> bool:
    """Validate recipe file - convenience function."""
    validator = RecipeValidator()
    result = validator.validate_file(recipe_path)
    if not result["ok"]:
        raise RecipeValidationError("; ".join(result["errors"]))
    return result["ok"]