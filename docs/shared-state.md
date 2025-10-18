---
title: "SecFlow Shared-State v1.0"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-14"
---

# SecFlow Shared-State v1.0

## 🧭 Overview

The **Shared-State System** provides a standardized way for all SecFlow team members to log daily activities, decisions, and handoffs. This system ensures transparency, accountability, and continuity across all roles and responsibilities.

**Key Components**:
- **Journals**: Individual role-based activity logs
- **Reports**: Daily compiled status reports
- **Contract**: Configuration and validation rules
- **Events**: Standardized event types for different activities

---

## 📁 File Structure

### Journals
```
/control/journal/agents/<role>/<YYYY-MM>/<role>-<YYYY-MM-DD>.ndjson
```

**Examples**:
- `/control/journal/agents/docs-lead/2025-10/docs-lead-2025-10-14.ndjson`
- `/control/journal/agents/workflow-lead/2025-10/workflow-lead-2025-10-14.ndjson`
- `/control/journal/agents/security-lead/2025-10/security-lead-2025-10-14.ndjson`

### Reports
```
/reports/daily/YYYY/MM/DD/compiled.md
```

**Examples**:
- `/reports/daily/2025/10/14/compiled.md`
- `/reports/daily/2025/10/15/compiled.md`

### Contract Configuration
```
/control/config/shared_state.yaml
```

---

## 📝 Event Types

| Event Type | Purpose | When to Use |
|------------|---------|-------------|
| **sod** | Start of Day | Beginning of work session, objectives, priorities |
| **mid** | Mid-day Update | Progress check, blockers, adjustments |
| **eod** | End of Day | Completion summary, results, next steps |
| **note** | General Note | Important observations, discoveries, context |
| **handoff** | Work Transfer | Passing work to another role, dependencies |
| **decision** | Policy/Architecture Decision | Important decisions with rationale and artifacts |

---

## 🔧 How to Log Events

### Using the Journal Tool

```bash
# Log a Start of Day event
python tools/journal.py --event sod --period 2025-10-14 --title "M1 Documentation Update" --items "Update plugin system docs,expand workflow engine docs,create security documentation" --links "PR#123,FEAT-022"

# Log a Mid-day Update
python tools/journal.py --event mid --period 2025-10-14 --title "Plugin docs completed" --items "Plugin system docs updated with M1 implementation,security framework documented,storage integration added" --links "PR#123"

# Log an End of Day event
python tools/journal.py --event eod --period 2025-10-14 --title "M1 docs complete" --items "All M1 features documented,health gates passing,navigation updated" --links "PR#123,FEAT-022"

# Log a Handoff event
python tools/journal.py --event handoff --period 2025-10-14 --title "Handoff to Integration Lead" --items "Documentation ready for review,test workflow execution,validate plugin integration" --links "PR#123" --handoff-to "@integration-lead"

# Log a Decision event
python tools/journal.py --event decision --period 2025-10-14 --title "M1 Documentation Strategy" --items "Comprehensive M1 docs created,security model documented,observability framework added" --links "PR#123,FEAT-022"
```

### Event Format

Each event follows this structure:

```json
{
  "timestamp": "2025-10-14T10:30:00Z",
  "event": "sod|mid|eod|note|handoff|decision",
  "period": "2025-10-14",
  "title": "Concise action/result",
  "items": [
    "Concrete bullet point 1",
    "Concrete bullet point 2",
    "Concrete bullet point 3"
  ],
  "links": [
    "PR#123",
    "FEAT-022",
    "https://github.com/org/repo/commit/abc123"
  ],
  "handoff_to": "@role-name (for handoff events only)"
}
```

---

## 📖 How to Read Daily Status

### 1. Navigate to Daily Report

Open the compiled daily report:
```
/reports/daily/YYYY/MM/DD/compiled.md
```

**Example**: `/reports/daily/2025/10/14/compiled.md`

### 2. Report Structure

Daily reports are organized in chronological order:

```markdown
# Daily Status Report - 2025-10-14

## SOD (Start of Day)
- **docs-lead**: M1 Documentation Update
  - Update plugin system docs
  - Expand workflow engine docs
  - Create security documentation
  - Links: [PR#123](link), [FEAT-022](link)

## MID (Mid-day Updates)
- **docs-lead**: Plugin docs completed
  - Plugin system docs updated with M1 implementation
  - Security framework documented
  - Storage integration added
  - Links: [PR#123](link)

## NOTES
- **workflow-lead**: Sequential execution working
  - All nodes execute in topological order
  - Retry logic functioning correctly
  - Links: [PR#124](link)

## HANDOFFS
- **docs-lead** → **@integration-lead**: Documentation ready for review
  - Test workflow execution
  - Validate plugin integration
  - Links: [PR#123](link)

## DECISIONS
- **docs-lead**: M1 Documentation Strategy
  - Comprehensive M1 docs created
  - Security model documented
  - Observability framework added
  - Links: [PR#123](link), [FEAT-022](link)

## EOD (End of Day)
- **docs-lead**: M1 docs complete
  - All M1 features documented
  - Health gates passing
  - Navigation updated
  - Links: [PR#123](link), [FEAT-022](link)
```

### 3. Reading Tips

- **SOD → EOD Flow**: Follow the natural progression of work throughout the day
- **Handoffs**: Look for `@role-name` mentions to understand work transfers
- **Decisions**: Important architectural or policy changes are logged here
- **Links**: Click through to PRs, FEATs, and commits for detailed context
- **Cross-Role Dependencies**: Use handoffs to understand blocking relationships

---

## 🔍 Shared-State Contract

### Core Rules

1. **Append Only**: Never edit existing journal entries
2. **Event Types**: Use only the 6 defined event types
3. **Period Format**: Always use `YYYY-MM-DD` format
4. **Concrete Items**: Write specific, actionable bullet points
5. **Link Everything**: Include PRs, FEATs, commits, and build URLs
6. **Handoff Protocol**: Use `@role-name` for work transfers

### Validation Rules

- **Required Fields**: timestamp, event, period, title, items
- **Event Validation**: Must be one of: sod, mid, eod, note, handoff, decision
- **Period Format**: Must match `YYYY-MM-DD` pattern
- **Links Format**: Must be valid URLs or PR/FEAT references
- **Handoff Requirement**: handoff events must include `handoff_to` field

### CI Integration

- **Daily Compilation**: CI automatically generates daily reports
- **Validation**: Journal entries are validated against the contract
- **Error Reporting**: Invalid entries are flagged in CI logs
- **Archive**: Historical reports are preserved for reference

---

## 🛠️ Tools and Commands

### Journal Tool Usage

```bash
# Basic event logging
python tools/journal.py --event <event_type> --period <YYYY-MM-DD> --title "<title>" --items "<item1>,<item2>,<item3>" --links "<link1>,<link2>"

# Handoff with specific role
python tools/journal.py --event handoff --period 2025-10-14 --title "Work transfer" --items "Task completed,ready for review" --links "PR#123" --handoff-to "@integration-lead"

# Decision with rationale
python tools/journal.py --event decision --period 2025-10-14 --title "Architecture decision" --items "Chose sequential execution for M1,parallel execution planned for M3" --links "PR#123,FEAT-020"
```

### Reading Commands

```bash
# View today's journal
cat /control/journal/agents/docs-lead/2025-10/docs-lead-2025-10-14.ndjson

# View compiled daily report
cat /reports/daily/2025/10/14/compiled.md

# Search for specific events
grep -r "handoff" /control/journal/agents/*/2025-10/

# Find decisions by role
grep -r "decision" /control/journal/agents/docs-lead/2025-10/
```

---

## 📚 Best Practices

### For All Roles

1. **Daily Logging**: Log SOD, MID, and EOD events consistently
2. **Concrete Items**: Write specific, measurable outcomes
3. **Link Everything**: Include all relevant PRs, FEATs, and commits
4. **Clear Titles**: Use concise, descriptive titles
5. **Timely Updates**: Log events as they happen, not at end of day

### For Handoffs

1. **Clear Recipients**: Always use `@role-name` format
2. **Context Transfer**: Include all necessary context and links
3. **Dependencies**: Clearly state any blocking dependencies
4. **Timeline**: Include expected completion timelines
5. **Follow-up**: Specify when/how to follow up

### For Decisions

1. **Rationale**: Always include the reasoning behind decisions
2. **Artifacts**: Link to relevant documents, PRs, or discussions
3. **Impact**: Describe the impact on other roles/teams
4. **Reversibility**: Note if the decision can be reversed
5. **Documentation**: Update relevant documentation

---

## 🔗 Integration with Workflow

### Daily Standup Integration

- **SOD Events**: Use for standup preparation
- **MID Events**: Use for mid-day check-ins
- **EOD Events**: Use for end-of-day retrospectives

### PR Integration

- **Link PRs**: Always include PR numbers in relevant events
- **Status Updates**: Use events to track PR progress
- **Review Requests**: Use handoffs to request reviews

### FEAT Integration

- **FEAT Tracking**: Link FEAT numbers to track feature progress
- **Milestone Updates**: Use events to report milestone completion
- **Blockers**: Use handoffs to report FEAT blockers

---

## 🚨 Troubleshooting

### Common Issues

1. **Invalid Event Type**: Use only the 6 defined event types
2. **Wrong Period Format**: Use `YYYY-MM-DD` format
3. **Missing Links**: Always include relevant PRs/FEATs
4. **Handoff Format**: Use `@role-name` for handoffs
5. **CI Failures**: Check journal format against contract

### Debug Commands

```bash
# Validate journal format
python tools/journal.py --validate --file /control/journal/agents/docs-lead/2025-10/docs-lead-2025-10-14.ndjson

# Check contract compliance
python tools/journal.py --check-contract --period 2025-10-14

# View CI logs
cat /logs/ci/shared-state-validation.log
```

---

## 📈 Metrics and Reporting

### Daily Metrics

- **Events Logged**: Count of events per role per day
- **Handoffs**: Number of work transfers
- **Decisions**: Number of architectural decisions
- **Links**: Number of PRs/FEATs referenced

### Weekly Reports

- **Activity Summary**: Aggregate events by role
- **Handoff Analysis**: Track work flow between roles
- **Decision Impact**: Analyze decision frequency and impact
- **Collaboration Metrics**: Cross-role interaction patterns

---

**Next:** [Developer Start Here](developer-start-here.md) | [Governance](governance/engineering-standards.md)
