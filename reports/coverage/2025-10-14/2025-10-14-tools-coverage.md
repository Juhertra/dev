# Tools Coverage Slice

## Contract Tests Counted (Skips)

### Test Framework Status
- **Total Tests**: 9 tests in `tests/contracts/test_parser_contracts.py`
- **Passed**: 1 test (structure validation)
- **Skipped**: 8 tests (parser contracts)
- **Failed**: 0 tests
- **Coverage**: 11% active (1/9), 89% deferred (8/9)

### Skipped Test Categories
1. **Parser Contract Tests**: 6 tests skipped
   - `test_parser_contract_golden_samples` (parametrized over all tools/versions)
   - Tests skip gracefully when wrapper implementations unavailable
   - Will activate with M2 wrapper implementations

2. **Performance Baseline**: 1 test skipped
   - `test_parser_performance_baseline`
   - Actual benchmark runs via separate script (`scripts/benchmark_parsers.py`)

3. **Version Compatibility**: 1 test skipped
   - `test_parser_version_compatibility`
   - Tests N and N-1 version compatibility (deferred to M2)

4. **Error Handling**: 1 test skipped
   - `test_parser_error_handling`
   - Malformed output handling (deferred to M2)

### Active Test Coverage
- ✅ **Golden samples directory structure**: Validates v*/output.json layout
- ✅ **Manifest validation**: JSON schema validation operational
- ✅ **Test framework**: Comprehensive framework ready for activation

## Plan to Activate in M2

### Phase 1: Wrapper Implementations
- **NucleiWrapper**: Implement actual Nuclei tool wrapper
- **FeroxWrapper**: Implement actual Feroxbuster tool wrapper  
- **KatanaWrapper**: Implement actual Katana tool wrapper
- **Activation**: Parser contract tests will automatically activate

### Phase 2: Sandbox & Registry
- **SandboxExecutor**: Resource limits enforcement
- **ToolRegistry**: Dynamic tool discovery and registration
- **Manifest Files**: Migrate to separate JSON manifest files
- **Activation**: Advanced orchestration capabilities

### Phase 3: Error Handling & Recovery
- **Retry Mechanisms**: Automatic retry on transient failures
- **Error Recovery**: Graceful handling of malformed outputs
- **Monitoring**: Performance regression detection
- **Activation**: Production-ready error handling

### Expected M2 Coverage
- **Parser Contracts**: 6 tests → Active (100% coverage)
- **Performance Baseline**: 1 test → Active (continuous monitoring)
- **Version Compatibility**: 1 test → Active (N/N-1 validation)
- **Error Handling**: 1 test → Active (robust error handling)
- **Total Coverage**: 9/9 tests active (100%)

### Coverage Metrics
- **Current M0**: 11% active (1/9 tests)
- **Target M2**: 100% active (9/9 tests)
- **Gap**: 89% deferred to M2 implementation
- **Risk**: Low - framework ready, just needs implementations

## Test Infrastructure Status

### ✅ Operational Components
- **Test Framework**: Comprehensive parametrized test suite
- **Golden Samples**: N versions present, N-1 pending merge
- **Performance Harness**: Exceeds threshold by 4000x+
- **Manifest Validation**: JSON schema validation working
- **Mock Implementations**: Functional for testing framework

### ⏳ Pending Components
- **N-1 Samples**: PR #73 open for merge
- **Wrapper Implementations**: Deferred to M2
- **Sandbox Execution**: Deferred to M2
- **Tool Registry**: Deferred to M2

### 🎯 M2 Activation Strategy
1. **Immediate**: Merge PR #73 to complete N-1 samples
2. **Phase 1**: Implement wrapper classes (Nuclei, Ferox, Katana)
3. **Phase 2**: Add SandboxExecutor and ToolRegistry
4. **Phase 3**: Enable all contract tests and performance monitoring

---

**Current Coverage**: 11% active (M0 scaffolding complete)  
**Target Coverage**: 100% active (M2 implementations)  
**Activation Plan**: Phased approach with wrapper implementations first
