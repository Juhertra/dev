## Definition of Done Checklist

### Code Quality
- [ ] All tests pass (`make test`)
- [ ] Code coverage meets current milestone threshold
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
