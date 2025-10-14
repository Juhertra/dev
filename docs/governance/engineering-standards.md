# Engineering Standards & Governance

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

## Branching & Commit Standards

### Branch Naming
- **Feature branches**: `feat/description-of-feature`
- **Bug fixes**: `fix/description-of-bug`
- **Documentation**: `docs/description-of-changes`
- **Refactoring**: `refactor/description-of-refactor`
- **Hotfixes**: `hotfix/description-of-fix`

### Commit Standards
- **Format**: `type(scope): description`
- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Squash**: All commits squashed before merge
- **Rebase**: Rebase on main before creating PR
- **Protected main**: Direct pushes to main are disabled

### Pull Request Rules
- **Size limit**: ≤400 LOC or requires 2 approvals
- **Description**: Must include context, testing instructions, and validation evidence
- **Reviewers**: Minimum 1 approval, 2 for large PRs
- **CI**: All checks must pass before merge

## CI Pipeline Order & Gates

The CI pipeline runs in strict order with gates that must pass:

1. **Code Quality Gates**
   - `ruff` - Python linting and formatting
   - `pyright` - Static type checking
   - `import-linter` - Import organization and unused import detection

2. **Testing Gates**
   - Unit tests + coverage measurement
   - Coverage ratchet enforcement (see below)
   - Contract tests
   - Integration tests

3. **Documentation Gates**
   - Docs health check (`make health`)
   - Mermaid parity validation
   - ASCII blocker check (no ASCII diagrams)
   - Internal link validation

4. **End-to-End Gates**
   - E2E test suite
   - Performance regression checks

## Coverage Ratchet Ladder

Coverage thresholds increase by milestone with strict enforcement:

- **M0**: 18% minimum coverage (baseline)
- **M1**: 80% minimum coverage
- **M2**: 82% minimum coverage
- **M3**: 84% minimum coverage
- **M4**: 86% minimum coverage
- **M5**: 88% minimum coverage
- **M6**: 90% minimum coverage

**Failure conditions**:
- Drop >2% from previous milestone
- Fall below current milestone threshold
- New code without tests

## Documentation Health Gates

### Mermaid Parity Check
- All diagrams must render identically in both Mermaid and ASCII
- ASCII diagrams are blocked (use `make health` to validate)
- Local Mermaid JS files only (no CDN dependencies)

### Superfences Configuration
- Use `pymdownx.superfences` for code blocks
- Mermaid diagrams use `mermaid` fence type
- Local JS files: `js/mermaid.min.js` and `js/mermaid-init.js`

### Fence Hygiene Tips
- Always specify language for code blocks
- Use proper fence types for diagrams
- Test rendering with `mkdocs serve`
- Validate with `make health` before commit

## SOD/EOD Rituals

### Start of Day (SOD)
- Review overnight CI results
- Check for any failed builds or coverage drops
- Update project status if needed
- Plan daily tasks based on current sprint goals

### End of Day (EOD)
- Run `make health` to validate docs
- Create EOD summary report
- Update project metrics and status
- Ensure all PRs have proper validation evidence

### Report Locations
- **Daily reports**: `reports/daily/YYYY-MM-DD.md`
- **Sprint reports**: `reports/sprints/sprint-N.md`
- **Milestone reports**: `reports/milestones/M{N}.md`

## ADR-Lite Process

### When ADR-Lite is Required
- Architecture decisions affecting multiple components
- Changes to CI/CD pipeline or tooling
- New dependencies or technology choices
- Security or compliance policy changes
- Breaking changes to APIs or data models

### ADR-Lite Template
Reference: `docs/adr/0000-adr-template.md`

**Required sections**:
- Status (Proposed/Accepted/Deprecated/Superseded)
- Context and Problem Statement
- Decision Drivers
- Considered Options
- Decision Outcome
- Consequences

## "Read → Run → Update" Loop

### Read Phase
1. Read relevant documentation
2. Understand current architecture
3. Review existing patterns and conventions
4. Check for related issues or PRs

### Run Phase
1. Set up local development environment
2. Run tests to understand current state
3. Experiment with changes locally
4. Validate with `make health` and `make test`

### Update Phase
1. Implement changes following DoD checklist
2. Update documentation as needed
3. Add tests for new functionality
4. Submit PR with validation evidence

## Adoption & Integration

### PR Template Integration
The DoD checklist should be referenced in all PR templates. Add this to your PR template:

```markdown
## DoD Checklist
Please review and complete the [Engineering Standards DoD checklist](governance/engineering-standards.md#definition-of-done-dod-checklist).

## Validation Evidence
Paste output from:
- `make test`
- `make health` 
- Coverage report
```

### Team Onboarding
- New team members must read this page before first PR
- Link from "Developer Start Here" page
- Include in team onboarding checklist
- Review quarterly for updates

### Continuous Improvement
- Monthly review of DoD effectiveness
- Quarterly updates to standards based on team feedback
- Annual review of CI pipeline and coverage thresholds
- Regular updates to tooling and best practices
