# Coordinator Merge Train Coverage Report - 2025-10-15

**Generated**: $(date -u +%F) (UTC)  
**Coordinator**: M0-D1..D5 Merge Train Coverage  
**Train Order**: [72 → 73 → 68 → 67]

---

## 📊 **Coverage Status**

### **M0 Coverage Threshold**: ≥18%

### **Per-PR Coverage Status**

| PR | Title | Coverage % | Status | Notes |
|----|-------|------------|--------|-------|
| 72 | fix(workflow): make scaffold importable to unskip tests | ❓ | **UNKNOWN** | Cannot verify due to failing checks |
| 73 | feat: Add N-1 golden samples for Nuclei, Feroxbuster, Katana | ❓ | **UNKNOWN** | Not reached due to PR #72 stop |
| 68 | feat(runtime): implement StoragePort interface + finding schema v1.0.0 | ❓ | **UNKNOWN** | Not reached due to PR #72 stop |
| 67 | chore(devex): fix Python version to 3.11.9 for pytest compatibility | ❓ | **UNKNOWN** | Not reached due to PR #72 stop |

**Legend**: ✅ ≥18% | ❌ <18% | ❓ UNKNOWN

---

## 🎯 **Coverage Verification**

### **Required Coverage Gate**: ≥18% for M0

### **PR #72 Coverage Check**
- **Status**: ❌ **CANNOT VERIFY** (coverage job failing)
- **Reason**: PR #72 has failing checks (findings-contract-tests, test)
- **Action**: Must fix failing checks before coverage can be verified

---

## 🚧 **Coverage Blockers**

### **PR #72** - Workflow Scaffold
- **Owner**: @workflow-lead
- **Blocking Issue**: Coverage job cannot run due to failing checks
- **Required Fix**: Fix findings-contract-tests and test failures
- **Coverage Verification**: Pending after check fixes

---

## 📈 **Coverage Progress**

### **Completed**
- **PRs with Verified Coverage**: 0/4 (0%)
- **Coverage Threshold Met**: ❌ **UNKNOWN**

### **Blocked**
- **PRs Remaining**: 4/4 (100%)
- **Blocking Issue**: PR #72 failing checks prevents coverage verification
- **Next Action**: @workflow-lead must fix PR #72 checks

---

## 🔗 **Coverage Links**

- **PR #72**: https://github.com/Juhertra/dev/pull/72 (COVERAGE UNKNOWN)
- **PR #73**: https://github.com/Juhertra/dev/pull/73 (NOT REACHED)
- **PR #68**: https://github.com/Juhertra/dev/pull/68 (NOT REACHED)
- **PR #67**: https://github.com/Juhertra/dev/pull/67 (NOT REACHED)

---

## 🎯 **Coverage Verification Commands** (when PR #72 is green)

```bash
# Verify coverage for each PR in train
for pr in 72 73 68 67; do
  echo "== Checking PR #${pr} coverage =="
  gh run list --branch "$(gh pr view ${pr} --json headRefName -q .headRefName)" --limit 5
  # Look for "Coverage OK: X% >= 18%" in coverage job logs
done
```

---

## 📊 **M0 Coverage Status**

### **Current State**: ⚠️ **UNKNOWN**
- **Workflow Foundation**: ❓ Coverage unknown (PR #72 failing)
- **Tools Samples**: ❓ Coverage unknown (PR #73 not reached)
- **Runtime Foundation**: ❓ Coverage unknown (PR #68 not reached)
- **Python Version**: ❓ Coverage unknown (PR #67 not reached)

### **M0 Coverage Criteria**
- [ ] All 4 train PRs have coverage ≥18%
- [ ] Coverage verification successful for all PRs
- [ ] Coverage ratchet enforcement working
- [ ] Coverage reports generated for all PRs

---

**Report**: `reports/coverage/2025-10-15/2025-10-15-coordinator-merge-train.md`
