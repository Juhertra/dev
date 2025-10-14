# Workflow Coverage Slice

## Current Tests (8 passing)

### TestWorkflowScaffolding
- **test_workflow_executor_import**: Validates WorkflowExecutor can be imported
- **test_recipe_validator_import**: Validates RecipeValidator can be imported
- **test_workflow_model_creation**: Tests Workflow and WorkflowNode model creation
- **test_executor_stub_methods**: Tests executor stub methods work
- **test_validator_stub_methods**: Tests validator stub methods work

### TestSampleWorkflow
- **test_sample_workflow_yaml**: Tests sample workflow YAML is valid
- **test_sample_workflow_dag**: Tests sample workflow DAG structure
- **test_sample_workflow_retry_state_config**: Tests retry and state configuration

## Next Test Targets (M3 Implementation)

### Parsing Tests
- **test_yaml_recipe_parsing**: Validate YAML recipe parsing with various formats
- **test_dag_cycle_detection**: Test cycle detection in workflow DAGs
- **test_input_output_validation**: Validate input/output dependency resolution
- **test_schema_validation**: Test recipe schema validation with invalid inputs

### Job Queue Tests
- **test_workflow_scheduler**: Test WorkflowScheduler DAG parsing and job submission
- **test_node_executor**: Test NodeExecutor subprocess wrapper management
- **test_job_queue_integration**: Test integration with Celery/RQ job queue
- **test_concurrent_execution**: Test parallel node execution where possible

### Retry Tests
- **test_retry_logic**: Test retry mechanism with exponential backoff
- **test_timeout_handling**: Test node timeout and process killing
- **test_failure_recovery**: Test workflow recovery from node failures
- **test_retry_configuration**: Test various retry configuration scenarios

### State Management Tests
- **test_checkpointing**: Test workflow checkpoint creation and restoration
- **test_resume_on_failure**: Test workflow resumption from failure points
- **test_intermediate_caching**: Test intermediate result caching between nodes
- **test_state_persistence**: Test workflow state persistence in database

### Event System Tests
- **test_event_publishing**: Test EventBus event publishing
- **test_event_subscription**: Test event subscription and handling
- **test_workflow_events**: Test workflow lifecycle events
- **test_node_events**: Test node execution events

### Integration Tests
- **test_tool_port_integration**: Test integration with ToolPort interface
- **test_findings_engine_integration**: Test integration with FindingsEngine
- **test_storage_integration**: Test integration with storage layer
- **test_ui_event_integration**: Test integration with UI event system

## Coverage Goals for M3

### Unit Test Coverage
- **Target**: 90%+ coverage for workflow engine components
- **Focus**: Core logic, error handling, edge cases
- **Tools**: pytest, coverage.py

### Integration Test Coverage
- **Target**: End-to-end workflow execution
- **Focus**: Tool integration, event flow, state management
- **Tools**: pytest, test containers, mock services

### Performance Test Coverage
- **Target**: Workflow execution performance benchmarks
- **Focus**: Large workflows, concurrent execution, memory usage
- **Tools**: pytest-benchmark, memory profiling

### Security Test Coverage
- **Target**: Workflow security and isolation
- **Focus**: Sandboxing, resource limits, input validation
- **Tools**: Security scanning, penetration testing

---
**Status**: M0 scaffolding complete, M3 test targets defined
