# Development Conventions

## Definition of Done (DoD) Checklist

### Code Quality
- [ ] All tests pass (`make test`)
- [ ] Code coverage meets current milestone threshold (see Coverage Ratchet below)
- [ ] No linting errors (`ruff`, `pyright`, `import-linter`)
- [ ] All imports properly organized and unused imports removed
- [ ] Code follows project style guidelines
- [ ] Type hints added for all public functions and classes

### Documentation
- [ ] Documentation updated for any API changes
- [ ] Docstrings added for new functions/classes
- [ ] README updated if installation/usage changed
- [ ] Docs health gates pass (`make health`)
- [ ] No broken internal links
- [ ] Mermaid diagrams render correctly (parity check)

### Testing
- [ ] Unit tests written for new functionality
- [ ] Integration tests updated if needed
- [ ] Contract tests pass
- [ ] E2E tests pass (if applicable)
- [ ] Test coverage doesn't drop below current threshold

### Security & Compliance
- [ ] No hardcoded secrets or credentials
- [ ] Security-sensitive code reviewed
- [ ] Dependencies updated and vulnerabilities checked
- [ ] Input validation implemented where needed

### Review Process
- [ ] PR description includes context and testing instructions
- [ ] PR size ≤400 LOC or requires 2 approvals
- [ ] All CI checks pass
- [ ] Code review completed by required reviewers
- [ ] Validation evidence pasted in PR comments

## SOD/EOD Rituals (Coordinator/DevEx Automation)

### Start of Day (SOD) - Automated by Coordinator
- **CI Status Check**: Automated scan of overnight CI results
- **Coverage Monitoring**: Automated coverage trend analysis
- **Dependency Alerts**: Automated security vulnerability scanning
- **Build Health**: Automated build failure notifications
- **Sprint Progress**: Automated sprint burn-down updates

### End of Day (EOD) - DevEx Automation
- **Health Gates**: Automated `make health` execution
- **Coverage Ratchet**: Automated coverage threshold validation
- **Documentation Sync**: Automated docs build and link validation
- **Metrics Collection**: Automated performance and quality metrics
- **Report Generation**: Automated EOD summary creation

### Report Locations
- **Daily Reports**: `reports/daily/YYYY-MM-DD.md` (auto-generated)
- **Sprint Reports**: `reports/sprints/sprint-N.md` (auto-updated)
- **Milestone Reports**: `reports/milestones/M{N}.md` (auto-compiled)
- **Health Reports**: `reports/health/YYYY-MM-DD-health.md` (auto-generated)

## Branch Naming & PR Rules

### Branch Naming Convention
- **Features**: `feat/description-of-feature`
- **Bug Fixes**: `fix/description-of-bug`
- **Documentation**: `docs/description-of-changes`
- **Refactoring**: `refactor/description-of-refactor`
- **Hotfixes**: `hotfix/description-of-fix`
- **Security**: `security/description-of-security-fix`

### PR Size Rule
- **Standard**: ≤400 LOC per PR
- **Large PRs**: >400 LOC requires 2 approvals minimum
- **Emergency**: Hotfixes may exceed limits with security team approval
- **Documentation**: Docs-only PRs have relaxed limits (≤1000 LOC)

### Security Review Rule
- **Mandatory Security Review**: All PRs touching security-sensitive code
- **Security Team**: `@security-lead` must approve security-related changes
- **Automated Scanning**: All PRs scanned for secrets and vulnerabilities
- **Dependency Updates**: Security updates get priority review queue

## CI Order (Fast-Fail)

The CI pipeline runs in strict fast-fail order:

### Phase 1: Code Quality (Fast-Fail)
1. **Ruff Linting** - Python code style and formatting
2. **Pyright Type Checking** - Static type analysis
3. **Import Linter** - Import organization and unused imports

### Phase 2: Testing (Fast-Fail)
4. **Unit Tests** - Core functionality testing
5. **Coverage Measurement** - Code coverage analysis
6. **Coverage Ratchet** - Threshold enforcement (fail if drop >2%)

### Phase 3: Integration (Fast-Fail)
7. **Contract Tests** - API contract validation
8. **Integration Tests** - Component interaction testing

### Phase 4: Documentation (Fast-Fail)
9. **Docs Health** - `make health` execution
10. **Mermaid Parity** - Diagram rendering validation
11. **ASCII Blocker** - ASCII diagram detection

### Phase 5: End-to-End (Fast-Fail)
12. **E2E Tests** - Full system testing
13. **Performance Tests** - Regression detection

## Coverage Ratchet Ladder

### Milestone Thresholds
- **M1**: 80% minimum coverage
- **M2**: 82% minimum coverage
- **M3**: 84% minimum coverage
- **M4**: 86% minimum coverage
- **M5**: 88% minimum coverage
- **M6**: 90% minimum coverage

### Failure Conditions
- Drop >2% from previous milestone
- Fall below current milestone threshold
- New code without corresponding tests
- Critical paths without test coverage

## Development Workflow

### Daily Development Loop
1. **Pull Latest**: `git pull origin main`
2. **Run Tests**: `make test` (full suite)
3. **Quick Iteration**: `make quick-test` (fast feedback)
4. **Health Check**: `make health` (before commit)
5. **Commit & Push**: Follow commit standards
6. **Create PR**: Include validation evidence

### Pre-Commit Checklist
- [ ] All tests pass locally
- [ ] Code coverage maintained
- [ ] Linting passes
- [ ] Documentation updated
- [ ] Security review completed (if applicable)

### PR Creation Process
1. **Branch from main**: `git checkout -b feat/description`
2. **Implement changes**: Follow DoD checklist
3. **Run validation**: `make test && make health`
4. **Create PR**: Include context and evidence
5. **Request reviews**: Assign appropriate reviewers
6. **Monitor CI**: Ensure all checks pass

## Tool Integration

### Development Tools
- **Poetry**: Dependency management
- **Ruff**: Code formatting and linting
- **Pyright**: Static type checking
- **Pytest**: Testing framework
- **MkDocs**: Documentation generation

### CI/CD Tools
- **GitHub Actions**: CI pipeline execution
- **Coverage.py**: Coverage measurement
- **Mermaid**: Diagram rendering
- **Link Checker**: Documentation validation

## Quality Gates

### Code Quality Gates
- **Linting**: Zero ruff/pyright errors
- **Type Safety**: Full type coverage for public APIs
- **Import Hygiene**: No unused imports
- **Style Consistency**: Automated formatting applied

### Testing Gates
- **Unit Coverage**: Minimum threshold per milestone
- **Integration Coverage**: Critical path coverage
- **Contract Validation**: API compatibility
- **Performance Regression**: No performance degradation

### Documentation Gates
- **Build Success**: MkDocs builds without errors
- **Link Validation**: No broken internal links
- **Mermaid Parity**: Diagrams render correctly
- **ASCII Blocker**: No ASCII diagrams allowed

## Emergency Procedures

### Hotfix Process
1. **Create hotfix branch**: `hotfix/critical-issue`
2. **Implement minimal fix**: Focus on stability
3. **Security review**: Mandatory for security issues
4. **Fast-track CI**: Expedited review process
5. **Deploy immediately**: After approval

### Rollback Process
1. **Identify issue**: Automated monitoring alerts
2. **Create rollback PR**: Revert problematic changes
3. **Emergency review**: Security team approval
4. **Deploy rollback**: Immediate deployment
5. **Post-mortem**: Document lessons learned

## Team Coordination

### Daily Standups
- **SOD Reports**: Automated CI status
- **Blockers**: Manual escalation process
- **Progress**: Sprint burn-down updates
- **Dependencies**: Cross-team coordination

### Weekly Reviews
- **Coverage Trends**: Automated analysis
- **Performance Metrics**: Automated collection
- **Security Updates**: Automated scanning
- **Process Improvements**: Team feedback integration

### Monthly Retrospectives
- **Process Effectiveness**: DoD checklist review
- **Tool Updates**: CI/CD pipeline improvements
- **Training Needs**: Skill gap identification
- **Process Refinement**: Continuous improvement
