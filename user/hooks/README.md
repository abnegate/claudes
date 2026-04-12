# Claude Code Hooks Reference

Docs: https://docs.anthropic.com/en/docs/claude-code/hooks

## Hook Events

### Session
| Event | Matcher matches | Description |
|---|---|---|
| `SessionStart` | How session started (`startup`, `resume`, `clear`, `compact`) | Session begins or resumes |
| `SessionEnd` | How session ended (`clear`, `resume`, `logout`) | Session terminates |

### Turn
| Event | Matcher matches | Description |
|---|---|---|
| `UserPromptSubmit` | *(no matcher)* | Before Claude processes a prompt |
| `Stop` | *(no matcher)* | Claude finishes responding |
| `StopFailure` | Error type (`rate_limit`, `authentication_failed`, `billing_error`) | Turn ends due to API error |

### Tool (most useful)
| Event | Matcher matches | Description |
|---|---|---|
| `PreToolUse` | Tool name | Before tool executes — **can block (exit 2) or modify input** |
| `PostToolUse` | Tool name | After tool succeeds |
| `PostToolUseFailure` | Tool name | After tool fails |
| `PermissionRequest` | Tool name | When permission dialog appears |
| `PermissionDenied` | Tool name | When auto-mode classifier denied a tool |

### Subagent / Task
| Event | Matcher matches | Description |
|---|---|---|
| `SubagentStart` | Agent type | Subagent spawned |
| `SubagentStop` | Agent type | Subagent finished |
| `TaskCreated` | *(no matcher)* | Task created |
| `TaskCompleted` | *(no matcher)* | Task marked complete |

### File / Config
| Event | Matcher matches | Description |
|---|---|---|
| `FileChanged` | Literal filenames (pipe-separated, NOT regex) | Watched file changes on disk |
| `ConfigChange` | Config source (`user_settings`, `project_settings`, etc.) | Config file changes |
| `CwdChanged` | *(no matcher)* | Working directory changes |
| `InstructionsLoaded` | Load reason (`session_start`, `compact`, etc.) | CLAUDE.md loaded |

### Context
| Event | Matcher matches | Description |
|---|---|---|
| `PreCompact` | Compaction trigger (`manual`, `auto`) | Before context compaction |
| `PostCompact` | Compaction trigger | After context compaction |

### Other
| Event | Matcher matches | Description |
|---|---|---|
| `Notification` | Notification type | Claude Code sends a notification |
| `Elicitation` | MCP server name | MCP server requests user input |
| `WorktreeCreate` | *(no matcher)* | Worktree being created |
| `WorktreeRemove` | *(no matcher)* | Worktree being removed |

## Matcher Syntax

Tool-level matchers match against the **tool name** (regex):

```
"Bash"                    — exact tool name
"Write|Edit"              — alternation
"mcp__github__.*"         — regex
```

Use `if` field for **argument filtering** (permission rule syntax, more efficient — prevents process spawn):

```json
{"matcher": "Bash", "if": "Bash(git commit*)"}
{"matcher": "Write", "if": "Write(*.php)"}
```

## Hook Types

```json
{"type": "command", "command": "/path/to/script.sh"}
{"type": "command", "command": "bash -c 'inline command'"}
{"type": "http", "url": "https://endpoint/hook"}
{"type": "prompt", "prompt": "Is this tool call safe?"}
{"type": "agent", "prompt": "Review this change"}
```

## Output

**Exit codes:**
| Code | Effect |
|---|---|
| `0` | Action proceeds. JSON stdout processed. |
| `2` | **Action blocked.** stderr shown to Claude. |
| Other | Action proceeds with warning. |

**JSON output (exit 0):**
```json
{
  "additionalContext": "Injected as system reminder to Claude",
  "systemMessage": "Warning shown to user in UI",
  "continue": false,
  "stopReason": "Message shown when stopping",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny|allow|ask",
    "permissionDecisionReason": "Reason",
    "updatedInput": {"command": "modified command"}
  }
}
```

## Environment

Hooks receive JSON on **stdin** with:
```json
{
  "session_id": "...",
  "cwd": "...",
  "hook_event_name": "PostToolUse",
  "tool_name": "Bash",
  "tool_input": {"command": "npm test"},
  "tool_output": "..."
}
```

Available env vars: `$CLAUDE_PROJECT_DIR`, `$CLAUDE_PLUGIN_ROOT` (plugins only), `$CLAUDE_PLUGIN_DATA` (plugins only), `$CLAUDE_ENV_FILE`.

## Installed Hooks

| Event | Script | Purpose |
|---|---|---|
| `PreToolUse` (git commit) | `pre-commit.sh` | Format staged PHP, JS/TS, Kotlin, Rust files before commit |
| `PostToolUse` (Write/Edit) | `format.sh` | Auto-format file after edit based on extension |
| `PostToolUse` (Bash) | `detect-failure.sh` | Detect test/build/lint failures, inject fix directive |
| `SessionStart` | (superpowerd) | Rotation capture |
