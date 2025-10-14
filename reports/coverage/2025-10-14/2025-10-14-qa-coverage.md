# QA Coverage Snapshot

## Total statements / missed / %
- **Total Statements:** 11,256
- **Missed:** 9,246  
- **Coverage:** 18%

## Trend vs yesterday
- **Previous:** 18% (11,284 statements, 9,298 missed)
- **Current:** 18% (11,256 statements, 9,246 missed)
- **Change:** 0% (28 fewer statements, 52 fewer missed)
- **Trend:** Stable coverage with slight code reduction

## Suites to lift next
- **High Priority:** Fix jsonschema dependency (blocks manifest validation)
- **Medium Priority:** Resolve Flask dependency in CI (blocks multiple test files)
- **Low Priority:** Implement parser contract tests (8 skips planned for M1)
- **Long-term:** Security scanning gates (pip-audit/Trivy) not implemented
- **Coverage Target:** Need 72% improvement to reach >90% Quality Gate threshold
