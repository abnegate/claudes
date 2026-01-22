---
name: investigate
description: Deep investigation of bugs, performance issues, or unexpected behavior
argument-hint: "<issue-to-investigate>"
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Task, WebFetch
---

# Deep Investigation

Thorough investigation of issues with root cause analysis and recommendations.

**OUTPUT: Detailed report with findings, root cause, and recommendations.**

## Arguments

- `$ARGUMENTS` - Issue description, error message, or area to investigate

## Phase 1: Define the Problem

### 1.1 Gather Information

Collect all available data:
- Error messages and stack traces
- Steps to reproduce
- When it started happening
- What changed recently
- Affected users/environments

### 1.2 Form Initial Hypotheses

List possible causes:
1. [Hypothesis 1]
2. [Hypothesis 2]
3. [Hypothesis 3]

## Phase 2: Evidence Collection

### 2.1 Code Analysis

Use **Explore** agent to understand:
- Code paths involved
- Recent changes to affected areas
- Dependencies and integrations

```bash
# Find recent changes
git log --oneline -30 -- path/to/affected/

# Find related code
# Use Grep to search for patterns
```

### 2.2 Log Analysis

If logs available:
- Search for error patterns
- Correlate timestamps
- Identify sequences of events

### 2.3 Test Behavior

Write exploratory tests:
```bash
# Create test that reproduces issue
./gradlew test --tests "*ExploratoryTest*"
```

### 2.4 Check External Factors

- Database state
- Third-party services
- Configuration differences
- Environment variables

## Phase 3: Root Cause Analysis

### 3.1 Narrow Down

For each hypothesis:
- What evidence supports it?
- What evidence contradicts it?
- Can we prove/disprove it?

### 3.2 Trace Execution

Follow the code path:
- Entry point
- Data transformations
- Decision points
- Exit/error point

### 3.3 Identify Root Cause

Distinguish between:
- **Proximate cause**: The immediate trigger
- **Root cause**: The underlying issue
- **Contributing factors**: Things that made it worse

## Phase 4: Document Findings

Create investigation report:

```markdown
# Investigation Report: [Issue Title]

**Date:** [date]
**Investigator:** Claude Code
**Status:** [In Progress / Complete]

## Summary
[One paragraph summary]

## Problem Statement
[What was reported/observed]

## Investigation Steps

### Step 1: [What was checked]
**Finding:** [What was discovered]

### Step 2: [What was checked]
**Finding:** [What was discovered]

...

## Root Cause
[Detailed explanation of the root cause]

## Evidence
- [Evidence 1]
- [Evidence 2]
- [Code references: file:line]

## Contributing Factors
- [Factor 1]
- [Factor 2]

## Recommendations

### Immediate Fix
[What to do now]

### Long-term Fix
[What to do to prevent recurrence]

### Process Improvements
[Changes to prevent similar issues]

## Appendix

### Code References
- `file1.kt:123` - [description]
- `file2.kt:456` - [description]

### Timeline
- [timestamp] - [event]
- [timestamp] - [event]
```

## Phase 5: Recommendations

### 5.1 Prioritized Actions

1. **Critical** - Must do immediately
2. **Important** - Should do soon
3. **Nice to have** - Consider for future

### 5.2 Prevention

How to prevent this class of issue:
- Better testing
- Monitoring/alerting
- Code review focus areas
- Documentation

## Investigation Techniques

### Binary Search (Git Bisect)
```bash
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
# Test each commit until culprit found
```

### Trace Logging
Add temporary logging to trace execution.

### Minimal Reproduction
Create smallest possible test case that reproduces the issue.

### Compare Working vs Broken
Diff configurations, code versions, environments.

## Test Failure Policy

**IMPORTANT:** If any tests fail during investigation, they must be fixed. There is no such thing as a "pre-existing" test failure - all test failures must be resolved before the task is considered complete. The task always completes with completely passing tests.

## Completion Criteria

- [ ] Problem clearly defined
- [ ] Evidence collected
- [ ] Root cause identified
- [ ] Report written
- [ ] Recommendations provided
- [ ] ALL tests pass (no exceptions for "pre-existing" failures)
