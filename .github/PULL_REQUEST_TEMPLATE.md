# SecFlow Pull Request

**Type:** feat / fix / chore / docs  
**Area:** runtime | wrappers/parsers | workflow | plugins | observability | docs/devex | schemas | qa

## Summary
- What does this change do? Why now?

## Changes
- 

## Definition of Done (check all)
Please review and complete the [Engineering Standards DoD checklist](governance/engineering-standards.md#definition-of-done-dod-checklist).

### Code Quality
- [ ] Conventional commit (e.g., `feat(wrapper): add nuclei parser`)
- [ ] Branch name follows rules (`feat/<issue>-<slug>` etc.)
- [ ] `ruff --fix` clean (no new warnings)
- [ ] `pyright --warnings` clean (no new errors)
- [ ] `pytest` green locally
- [ ] Coverage ≥ current ratchet (M0: baseline only)
- [ ] Import rules (`import-linter`) green

### Documentation & Testing
- [ ] **If docs touched**: `make health` (Mermaid parity + ASCII blocker) green
- [ ] Contract tests green (finding invariants / parser / port) — if applicable
- [ ] Public APIs have docstrings + examples (or ADR updated if contracts changed)

### Security
- [ ] **Security considerations addressed?** (Y/N) - See [Security Review Guidelines](docs/security/security-review-guidelines.md)
- [ ] **YAML parsing uses `yaml.safe_load()`** (if applicable)
- [ ] **No hardcoded secrets or credentials** (if applicable)
- [ ] **Input validation implemented** (if applicable)
- [ ] **Plugin security policy compliance** (if applicable)
- [ ] **Dependency security audit passed** (if new dependencies added)

### Review Process
- [ ] PR size ≤400 LOC or requires 2 approvals
- [ ] All CI checks pass
- [ ] Code review completed by required reviewers
- [ ] **Security review completed** (if security-sensitive changes)

## Risk & Rollback
- Risks:
- Rollback plan:

## Links
- Issue: FEAT-###  
- Docs pages read/updated: …

## Validation Evidence
Paste output from:
- `make test`
- `make health` 
- Coverage report
