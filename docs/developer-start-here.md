# Developer Start Here

## Quick Setup

- Clone repo, install Poetry, `poetry install --no-root`
- Branching: trunk-based; feature branches `feat/...`; PR ≤400 LOC or 2 approvals
- Run locally: `make test` ; fast loop: `make quick-test`
- Docs: `mkdocs serve` (local), `make health` before committing docs
- Read: `docs/architecture/00-index.md`, storage contracts, finding schema
- DoD checklist is in PR template; paste validation evidence in PRs

## Essential Reading

> **Read this first: [Governance & Engineering Standards](governance/engineering-standards.md)**

This page contains the complete Definition of Done checklist, branching rules, CI pipeline order, coverage requirements, and documentation health gates that all contributors must follow.

> **Development Practices: [Development Conventions](governance/development-conventions.md)**

This page covers daily development workflows, SOD/EOD rituals, branch naming conventions, PR rules, and CI fast-fail order that every developer needs to follow.

## Getting Started

### Prerequisites

1. **Poetry**: Install Poetry for dependency management
2. **Git**: For version control and branching
3. **Make**: For running build commands

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd secflow

# Install dependencies (without root package)
poetry install --no-root
```

### Development Workflow

#### Branching Strategy
- **Trunk-based development**: Main branch is the source of truth
- **Feature branches**: Use `feat/...` prefix for new features
- **Pull Request limits**: ≤400 LOC or require 2 approvals

#### Testing
- **Full test suite**: `make test`
- **Quick iteration**: `make quick-test` for faster feedback

#### Documentation
- **Local development**: `mkdocs serve` to preview docs locally
- **Health checks**: Run `make health` before committing documentation changes

### Essential Reading

1. **Architecture Overview**: Start with `docs/architecture/00-index.md`
2. **Storage Contracts**: Understand data persistence patterns
3. **Finding Schema**: Review the findings data model

### Definition of Done

The DoD checklist is available in the PR template. Always paste validation evidence in your pull requests to demonstrate compliance.

## Next Steps

After completing the setup, explore the architecture documentation to understand the system design and begin contributing to the project.
